import { ref, computed } from 'vue'
import { sendChatMessage, generateSessionId } from '@/api/chat.js'

export function useChat() {
  const messages = ref([])
  const sessionId = ref(generateSessionId())
  const isStreaming = ref(false)
  const error = ref('')
  const streamingContent = ref('')
  const thinkingLines = ref([])
  const isThinking = ref(false)

  const showWelcome = computed(() => messages.value.length === 0)

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
        (outputContent) => {
          if (isThinking.value) {
            thinkingLines.value = []
            isThinking.value = false
          }
          streamingContent.value = outputContent
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

  function newChat() {
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
    sendMessage,
    newChat,
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
