import { ref, computed } from 'vue'
import {
  sendChatMessage,
  generateSessionId,
  loadConversationsApi,
  saveConversationApi,
  deleteConversationApi
} from '@/api/chat.js'

export function useChat() {
  const messages = ref([])
  const sessionId = ref(generateSessionId())
  const isStreaming = ref(false)
  const error = ref('')
  const streamingContent = ref('')
  const thinkingLines = ref([])
  const isThinking = ref(false)
  const conversations = ref([])
  const currentConversationId = ref(null)
  const currentConversation = computed(() => {
    if (!currentConversationId.value) return null
    return conversations.value.find(c => c.id === currentConversationId.value) || null
  })

  const showWelcome = computed(() => messages.value.length === 0 && !currentConversation.value)

  function addUserMessage(content) {
    messages.value.push({
      id: Date.now(),
      role: 'user',
      content,
      time: formatTime()
    })
  }

  function addAssistantMessage(content) {
    messages.value.push({
      id: Date.now(),
      role: 'assistant',
      content,
      time: formatTime()
    })
  }

  async function sendMessage(message) {
    if (!message.trim() || isStreaming.value) return

    error.value = ''
    addUserMessage(message)
    isStreaming.value = true
    streamingContent.value = ''
    thinkingLines.value = []
    isThinking.value = false

    try {
      await sendChatMessage(
        message,
        sessionId.value,
        (thinkingContent) => {
          isThinking.value = true
          thinkingLines.value.push(thinkingContent)
        },
        (_delta, fullOutput) => {
          if (isThinking.value) {
            thinkingLines.value = []
            isThinking.value = false
          }
          streamingContent.value = fullOutput
        },
        () => {
          thinkingLines.value = []
          isThinking.value = false
        },
        (err) => {
          error.value = err
        },
        (finalContent) => {
          addAssistantMessage(finalContent)
          streamingContent.value = ''
          thinkingLines.value = []
          isThinking.value = false
          isStreaming.value = false
        }
      )
    } catch (e) {
      isStreaming.value = false
      streamingContent.value = ''
      thinkingLines.value = []
      isThinking.value = false
    }
  }

  function saveCurrentConversation() {
    if (messages.value.length === 0) return
    const firstUserMsg = messages.value.find(m => m.role === 'user')
    const title = firstUserMsg
      ? firstUserMsg.content.slice(0, 30) + (firstUserMsg.content.length > 30 ? '...' : '')
      : '新对话'
    const conv = {
      id: sessionId.value,
      title,
      messages: JSON.parse(JSON.stringify(messages.value)),
      time: formatTime()
    }
    conversations.value.unshift(conv)
    saveConversationApi(conv).catch(() => {})
  }

  function newChat() {
    saveCurrentConversation()
    currentConversationId.value = null
    resetChatState()
  }

  function switchToConversation(conversationId) {
    const conv = conversations.value.find(c => c.id === conversationId)
    if (!conv) return
    saveCurrentConversation()
    currentConversationId.value = conversationId
    messages.value = JSON.parse(JSON.stringify(conv.messages))
    sessionId.value = conv.id
    error.value = ''
    streamingContent.value = ''
    thinkingLines.value = []
    isThinking.value = false
    isStreaming.value = false
    conversations.value = conversations.value.filter(c => c.id !== conversationId)
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
    }
    deleteConversationApi(conversationId).catch(() => {})
  }

  function resetChatState() {
    messages.value = []
    sessionId.value = generateSessionId()
    error.value = ''
    streamingContent.value = ''
    thinkingLines.value = []
    isThinking.value = false
    isStreaming.value = false
  }

  function clearChat() {
    messages.value = []
    error.value = ''
    streamingContent.value = ''
    thinkingLines.value = []
    isThinking.value = false
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
    thinkingLines,
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
