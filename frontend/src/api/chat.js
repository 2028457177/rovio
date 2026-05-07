const API_BASE = '/api'

export async function sendChatMessage(message, sessionId, onThinking, onOutput, onThinkingEnd, onError, onDone) {
  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        stream: true
      })
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
            if (parsed.type === 'thinking' && parsed.content) {
              onThinking(parsed.content)
            } else if (parsed.type === 'thinking_end') {
              onThinkingEnd()
            } else if (parsed.type === 'output' && parsed.content) {
              fullOutput += parsed.content
              onOutput(fullOutput)
            }

            if (parsed.error) {
              onError(parsed.error)
            }
          } catch {
            if (data) {
              fullOutput += data
              onOutput(fullOutput)
            }
          }
        }
      }
    }

    onDone(fullOutput)
    return fullOutput
  } catch (error) {
    onError(`发送失败: ${error.message}`)
    throw error
  }
}

export function generateSessionId() {
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9)
}
