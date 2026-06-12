import { ref, computed, reactive, markRaw } from 'vue'
import {
  sendChatMessage,
  generateSessionId,
  loadConversationsApi,
  saveConversationApi,
  deleteConversationApi
} from '@/api/chat.js'

export function useChat() {
  const conversations = ref([])
  const currentConversationId = ref(null)
  const pendingStreams = ref(new Map())  // sessionId -> { controller, streamingContent, thinkingContent, isThinking, isStreaming }
  const error = ref('')
  const geoLocation = ref(null)  // { latitude, longitude }

  const currentConversation = computed(() => {
    if (!currentConversationId.value) return null
    return conversations.value.find(c => c.id === currentConversationId.value) || null
  })

  const messages = computed(() => {
    const conv = currentConversation.value
    return conv ? conv.messages : []
  })

  const sessionId = computed(() => {
    return currentConversation.value ? currentConversation.value.id : defaultSessionId.value
  })

  const defaultSessionId = ref(generateSessionId())
  const isStreaming = computed(() => {
    const conv = currentConversation.value
    if (!conv) return false
    const pending = pendingStreams.value.get(conv.id)
    return !!pending && pending.isStreaming
  })
  const streamingContent = computed(() => {
    const conv = currentConversation.value
    if (!conv) return ''
    const pending = pendingStreams.value.get(conv.id)
    return pending ? pending.streamingContent : ''
  })
  const thinkingContent = computed(() => {
    const conv = currentConversation.value
    if (!conv) return ''
    const pending = pendingStreams.value.get(conv.id)
    return pending ? pending.thinkingContent : ''
  })
  const isThinking = computed(() => {
    const conv = currentConversation.value
    if (!conv) return false
    const pending = pendingStreams.value.get(conv.id)
    return !!pending && pending.isThinking
  })

  const showWelcome = computed(() => messages.value.length === 0)

  function getOrCreateConversation(id) {
    let conv = conversations.value.find(c => c.id === id)
    if (!conv) {
      conv = {
        id,
        title: '新对话',
        messages: [],
        time: formatTime()
      }
      conversations.value.unshift(conv)
    }
    return conv
  }

  function updateTitleFromMessages(conv) {
    const firstUserMsg = conv.messages.find(m => m.role === 'user')
    if (firstUserMsg) {
      conv.title = firstUserMsg.content.slice(0, 30) + (firstUserMsg.content.length > 30 ? '...' : '')
    }
  }

  async function sendMessage(message, uploadedFilePath = '') {
    if (!message.trim() && !uploadedFilePath) return

    // 当前没有激活会话时，先用默认 sessionId 创建一个
    const requestSessionId = sessionId.value
    if (pendingStreams.value.has(requestSessionId)) return

    error.value = ''
    const conv = getOrCreateConversation(requestSessionId)
    // 如果是新对话，首次发送时激活它
    if (!currentConversationId.value) {
      currentConversationId.value = requestSessionId
    }

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: message,
      time: formatTime()
    }
    conv.messages.push(userMsg)
    updateTitleFromMessages(conv)

    // 创建占位的 assistant 消息：流式过程中直接更新它的 content，
    // 让消息气泡从一开始就存在于 messages 列表中，避免临时元素消失导致的视觉跳动
    const assistantMsg = reactive({
      id: Date.now() + 1,
      role: 'assistant',
      content: '',
      time: formatTime(),
      streaming: true
    })
    conv.messages.push(assistantMsg)

    const controller = markRaw(new AbortController())
    // 必须用 reactive 包裹：流式回调会直接修改 pending 的字段，
    // 只有响应式代理才能让 isThinking / streamingContent / thinkingContent 的变化被 Vue 追踪到。
    const pending = reactive({
      controller,
      streamingContent: '',
      thinkingContent: '',
      isThinking: true,
      isStreaming: true
    })
    pendingStreams.value.set(requestSessionId, pending)

    // 首次发消息时尝试获取浏览器定位
    if (geoLocation.value === null) {
      try {
        const pos = await new Promise((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,   // 桌面端尝试 WiFi 高精度定位
            timeout: 10000,
            maximumAge: 600000          // 10分钟缓存
          })
        })
        geoLocation.value = {
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude
        }
      } catch {
        geoLocation.value = false  // 标记已尝试，不再重试
      }
    }

    const lat = geoLocation.value ? geoLocation.value.latitude : null
    const lng = geoLocation.value ? geoLocation.value.longitude : null

    try {
      await sendChatMessage(
        message,
        requestSessionId,
        lat,
        lng,
        (thinkingContent) => {
          pending.isThinking = true
          pending.streamingContent = ''
          pending.thinkingContent += thinkingContent
        },
        (_delta, fullOutput) => {
          pending.isThinking = false
          pending.streamingContent = fullOutput
          // 直接把流式输出写入驻点 assistant 消息，气泡内容实时更新
          assistantMsg.content = fullOutput
        },
        () => {
          // thinking_end：不再清空，保留所有思考过程累积显示
        },
        (err) => {
          if (currentConversationId.value === requestSessionId) {
            error.value = err
          }
        },
        (finalContent) => {
          // 流式过程中 assistantMsg.content 已经实时更新，这里只做收尾
          assistantMsg.content = finalContent
          assistantMsg.streaming = false
          const finalConv = getOrCreateConversation(requestSessionId)
          updateTitleFromMessages(finalConv)
          saveConversationApi(finalConv).catch(() => {})
          pendingStreams.value.delete(requestSessionId)
        },
        uploadedFilePath,
        controller.signal
      )
    } catch (e) {
      assistantMsg.streaming = false
      // 流式失败且占位消息没有任何内容时，移除它避免遗留空气泡
      if (!assistantMsg.content) {
        const failedConv = getOrCreateConversation(requestSessionId)
        const idx = failedConv.messages.indexOf(assistantMsg)
        if (idx > -1) failedConv.messages.splice(idx, 1)
      }
      pendingStreams.value.delete(requestSessionId)
    }
  }

  function saveCurrentConversation() {
    const conv = currentConversation.value
    if (!conv || conv.messages.length === 0) return
    saveConversationApi(conv).catch(() => {})
  }

  function newChat() {
    saveCurrentConversation()
    currentConversationId.value = null
    defaultSessionId.value = generateSessionId()
    error.value = ''
  }

  function switchToConversation(conversationId) {
    const conv = conversations.value.find(c => c.id === conversationId)
    if (!conv) return
    saveCurrentConversation()
    currentConversationId.value = conversationId
    error.value = ''
  }

  async function loadConversations() {
    try {
      const data = await loadConversationsApi()
      conversations.value = data
    } catch {
      conversations.value = []
    }
  }

  async function removeConversation(conversationId) {
    conversations.value = conversations.value.filter(c => c.id !== conversationId)
    if (currentConversationId.value === conversationId) {
      currentConversationId.value = null
      defaultSessionId.value = generateSessionId()
    }
    deleteConversationApi(conversationId).catch(() => {})
  }

  function clearChat() {
    const conv = currentConversation.value
    if (conv) {
      conv.messages = []
    }
    error.value = ''
  }

  function dismissError() {
    error.value = ''
  }

  return {
    messages,
    sessionId,
    isStreaming,
    error,
    streamingContent,
    thinkingContent,
    isThinking,
    showWelcome,
    conversations,
    currentConversationId,
    currentConversation,
    sendMessage,
    newChat,
    loadConversations,
    switchToConversation,
    removeConversation,
    clearChat,
    dismissError
  }
}

function formatTime() {
  const now = new Date()
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  return `${hours}:${minutes}`
}
