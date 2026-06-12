import { getToken } from './auth.js'

const API_BASE = '/api'

function authHeaders(extra = {}) {
  const token = getToken()
  const headers = { ...extra }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

export async function uploadWordFile(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/upload-word`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `上传失败: ${response.status}`)
  }

  return response.json()
}

export async function sendChatMessage(message, sessionId, latitude, longitude, onThinking, onOutput, onThinkingEnd, onError, onDone, uploadedFilePath = '', signal = null) {
  try {
    const body = {
      message,
      session_id: sessionId,
      stream: true
    }
    if (latitude != null && longitude != null) {
      body.latitude = latitude
      body.longitude = longitude
    }
    if (uploadedFilePath) {
      body.uploaded_file_path = uploadedFilePath
    }

    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
      signal
    })

    if (!response.ok) {
      throw new Error(`请求失败: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let fullOutput = ''
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.substring(6).trim()
          if (data === '[DONE]') continue

          try {
            const parsed = JSON.parse(data)
            // 思考栏只显示工具调用 + 模型推理（来自 react_agent 的 thinking 事件）
            // supervisor_thinking / supervisor_action 不再混入思考栏
            if (parsed.type === 'thinking' && parsed.content) {
              onThinking(parsed.content)
            } else if (parsed.type === 'thinking_end') {
              onThinkingEnd()
            } else if (parsed.type === 'output' && parsed.content) {
              fullOutput += parsed.content
              onOutput(parsed.content, fullOutput)
            }

            if (parsed.error) {
              onError(parsed.error)
            }
            } catch {
            if (data) {
              fullOutput += data
              onOutput(data, fullOutput)
            }
          }
        }
      }
    }

    onDone(fullOutput)
    return fullOutput
  } catch (error) {
    if (error.name === 'AbortError') {
      return ''
    }
    onError(`发送失败: ${error.message}`)
    throw error
  }
}

export function generateSessionId() {
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9)
}

export async function loadConversationsApi() {
  const response = await fetch(`${API_BASE}/conversations`, {
    headers: authHeaders(),
  })
  if (!response.ok) throw new Error(`加载对话失败: ${response.status}`)
  const data = await response.json()
  return data.conversations || []
}

export async function saveConversationApi(conversation) {
  await fetch(`${API_BASE}/conversations`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(conversation)
  })
}

export async function deleteConversationApi(conversationId) {
  await fetch(`${API_BASE}/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
}
