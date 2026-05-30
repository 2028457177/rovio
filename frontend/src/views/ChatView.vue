<template>
  <div class="app-layout">
    <div class="animated-bg">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="orb orb-4"></div>
    </div>

    <aside class="sidebar glass-strong">
      <div class="sidebar-header">
        <div class="sidebar-logo">
          <img src="/agent-avatar.jpg" alt="助手" class="logo-img" />
          <div class="logo-glow"></div>
        </div>
        <div>
          <div class="sidebar-title">办公助手</div>
          <div class="sidebar-subtitle">AI 驱动 · 效率倍增</div>
        </div>
      </div>

      <button class="sidebar-new-chat" @click="onNewChat">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        新建对话
      </button>

      <div class="sidebar-section-title">历史对话</div>
      <ul class="sidebar-chat-list" v-if="conversations.length > 0">
        <li
          class="sidebar-chat-item"
          :class="{ active: conv.id === currentConversationId }"
          v-for="conv in conversations"
          :key="conv.id"
          @click="onSwitchConversation(conv.id)"
        >
          <span class="chat-item-icon">💬</span>
          <span class="chat-item-text" :title="conv.title">{{ conv.title }}</span>
          <span class="chat-item-time">{{ conv.time }}</span>
          <button
            class="chat-item-delete"
            @click.stop="onRemoveConversation(conv.id)"
            title="删除对话"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </li>
      </ul>
      <div v-else class="sidebar-empty-hint">
        暂无对话记录
      </div>

      <div class="sidebar-footer">
        <div class="sidebar-user" v-if="user">
          <img v-if="user.avatar" :src="user.avatar" class="user-avatar" />
          <span v-else class="user-avatar-placeholder">👤</span>
          <span class="user-name">{{ user.nickname || '微信用户' }}</span>
          <button class="user-logout-btn" @click="onLogout" title="退出登录">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
          </button>
        </div>
        <div class="sidebar-status">
          <span class="status-dot"></span>
          服务就绪 · 随时为您效劳
        </div>
      </div>
    </aside>

    <main class="main-content">
      <header class="chat-header glass">
        <div class="chat-header-left">
          <span class="chat-header-title">
            <span class="header-glow"></span>
            {{ currentConversation ? currentConversation.title : 'AI 对话' }}
          </span>
          <p v-if="showWelcome" class="chat-header-subtitle">基于 AI 的智能办公伴侣，请在下方输入你的需求</p>
        </div>
        <div class="chat-header-actions">
          <button class="chat-header-btn" @click="onClearChat">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
            清空对话
          </button>
        </div>
      </header>

      <Transition name="fade">
        <ErrorBanner
          v-if="error"
          :message="error"
          @dismiss="onDismissError"
        />
      </Transition>

      <div class="chat-messages" ref="chatContainer">
        <div v-if="showWelcome" class="welcome-center">
          <div class="welcome-suggestions-small">
            <button
              v-for="item in suggestions"
              :key="item.prompt"
              class="suggestion-chip"
              @click="onSendMessage(item.prompt)"
            >
              <span class="suggestion-chip-icon">{{ item.icon }}</span>
              <span>{{ item.label }}</span>
            </button>
          </div>
          <ChatInput
            :disabled="isStreaming"
            center-mode
            @send="onSendMessage"
          />
        </div>

        <TransitionGroup name="message-list" tag="div" class="messages-list">
          <MessageBubble
            v-for="msg in messages"
            :key="msg.id"
            :message="msg"
          />
        </TransitionGroup>

        <div v-if="isThinking && thinkingLines.length > 0 && !streamingContent" class="thinking-panel">
          <details open class="glass">
            <summary class="thinking-summary">
              <span class="thinking-spinner"></span>
              正在思考中...
            </summary>
            <div class="thinking-content">
              <div
                v-for="(line, idx) in thinkingLines"
                :key="idx"
                class="thinking-line"
              >
                {{ line }}
              </div>
            </div>
          </details>
        </div>

        <div v-if="isStreaming && streamingContent" class="message assistant">
          <div class="message-avatar assistant-avatar">
            <span class="avatar-pulse"></span>
            <img src="/agent-avatar.jpg" alt="助手" class="avatar-img" />
          </div>
          <div class="message-body">
            <div class="message-role">办公助手</div>
            <div class="message-text" v-html="renderMarkdown(streamingContent)"></div>
            <span class="typing-cursor">▊</span>
          </div>
        </div>

        <div v-if="isStreaming && !streamingContent && !isThinking" class="message assistant">
          <div class="message-avatar assistant-avatar"><img src="/agent-avatar.jpg" alt="助手" class="avatar-img" /></div>
          <div class="message-body">
            <div class="message-role">办公助手</div>
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <ChatInput
        v-if="!showWelcome"
        :disabled="isStreaming"
        @send="onSendMessage"
      />
    </main>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChat } from '@/composables/useChat.js'
import { useAuth } from '@/composables/useAuth.js'
import MessageBubble from '@/components/MessageBubble.vue'
import ChatInput from '@/components/ChatInput.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import { renderMarkdown } from '@/utils/markdown.js'

const router = useRouter()
const { user, isLoggedIn, checkAuth, logout } = useAuth()

const {
  messages,
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
} = useChat()

onMounted(async () => {
  const ok = await checkAuth()
  if (!ok) {
    router.replace('/login')
    return
  }
  loadConversations()
})

function onLogout() {
  logout()
  router.replace('/login')
}

const chatContainer = ref(null)

const suggestions = [
  { icon: '📄', label: '自动填写文档', prompt: '帮我自动填写Word模板文件' },
  { icon: '🌤️', label: '查询天气', prompt: '帮我查询今天的天气' },
  { icon: '📊', label: '生成工作报告', prompt: '帮我生成一份个人工作数据报告' },
  { icon: '🔍', label: '联网搜索', prompt: '帮我搜索最新的办公效率工具' },
]

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTo({
        top: chatContainer.value.scrollHeight,
        behavior: 'smooth'
      })
    }
  })
}

watch(messages, scrollToBottom, { deep: true })
watch(streamingContent, scrollToBottom)
watch(thinkingLines, scrollToBottom)

function onSendMessage(message) {
  sendMessage(message)
}

function onNewChat() {
  newChat()
}

function onSwitchConversation(conversationId) {
  switchToConversation(conversationId)
}

function onRemoveConversation(conversationId) {
  removeConversation(conversationId)
}

function onClearChat() {
  clearChat()
}

function onDismissError() {
  dismissError()
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100%;
  position: relative;
  z-index: 1;
}

.sidebar {
  width: 280px;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  padding: 20px;
  z-index: 10;
  border-radius: 0;
  border-right: 1px solid var(--border);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(240, 243, 247, 0.88)),
    var(--bg);
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-light);
  margin-bottom: 16px;
}

.sidebar-logo {
  position: relative;
  width: 42px;
  height: 42px;
  background: linear-gradient(180deg, #1f2329, var(--accent));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(8, 10, 14, 0.2);
  overflow: hidden;
}

.logo-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  position: relative;
  z-index: 1;
}

.logo-glow {
  position: absolute;
  inset: -5px;
  border-radius: 50%;
  background: rgba(8, 10, 14, 0.12);
  filter: blur(10px);
  z-index: -1;
  animation: pulse-glow 2.5s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.1); }
}

.sidebar-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.3px;
}

.sidebar-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.sidebar-new-chat {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  color: var(--text);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: transform var(--spring), box-shadow var(--spring), background var(--transition), border-color var(--transition);
  margin-bottom: 24px;
  width: 100%;
  font-family: inherit;
}

.sidebar-new-chat:hover {
  background: #fff;
  border-color: rgba(8, 9, 11, 0.28);
  color: var(--text);
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(8, 10, 14, 0.1);
}

.sidebar-section-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--text-muted);
  margin-bottom: 10px;
  font-weight: 600;
}

.sidebar-chat-list {
  flex: 1;
  overflow-y: auto;
  list-style: none;
}

.sidebar-chat-item {
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  margin-bottom: 4px;
  transition: transform var(--spring), background var(--transition), box-shadow var(--transition);
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
}

.sidebar-chat-item:hover {
  background: var(--glass-light);
  color: var(--text);
  transform: translateX(3px);
}

.sidebar-chat-item.active {
  background: #fff;
  color: var(--text);
  border: 1px solid var(--border);
  box-shadow: 0 4px 16px var(--shadow-sm);
}

.chat-item-icon {
  font-size: 14px;
}

.chat-item-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.chat-item-time {
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.chat-item-delete {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  opacity: 0;
  transition: var(--transition);
  flex-shrink: 0;
}

.sidebar-chat-item:hover .chat-item-delete {
  opacity: 1;
}

.chat-item-delete:hover {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
}

.sidebar-empty-hint {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  padding: 20px 0;
}

.sidebar-footer {
  border-top: 1px solid var(--border-light);
  padding-top: 14px;
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sidebar-user {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid var(--border);
}

.user-avatar-placeholder {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--glass-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.user-name {
  flex: 1;
  font-size: 13px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-logout-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  transition: var(--transition);
}

.user-logout-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.sidebar-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #22c55e;
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.4);
  animation: status-pulse 2s ease-in-out infinite;
}

@keyframes status-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  position: relative;
}

.chat-header {
  padding: 12px 24px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-shrink: 0;
  z-index: 5;
  border-radius: 0;
  border-top: none;
  border-left: none;
  border-right: none;
  border-bottom: 1px solid var(--border-light);
  background: var(--glass);
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
}

.chat-header-title {
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text);
}

.header-glow {
  width: 8px;
  height: 8px;
  background: var(--accent);
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(8, 10, 14, 0.18);
}

.chat-header-actions {
  display: flex;
  gap: 8px;
}

.chat-header-btn {
  padding: 8px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  transition: transform var(--spring-fast), box-shadow var(--spring-fast), background var(--transition), border-color var(--transition);
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: inherit;
}

.chat-header-btn:hover {
  background: #fff;
  color: var(--text);
  border-color: rgba(8, 9, 11, 0.28);
  transform: translateY(-1px);
  box-shadow: 0 4px 14px var(--shadow-sm);
}

.chat-header-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin: 2px 0 0;
  font-weight: 400;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  position: relative;
}

.welcome-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 20px;
  animation: welcome-fade 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes welcome-fade {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.welcome-suggestions-small {
  display: flex;
  gap: 8px;
  width: 100%;
  max-width: 620px;
  margin-bottom: 4px;
}

.suggestion-chip {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 8px 6px;
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 12px;
  font-family: inherit;
  color: var(--text-secondary);
  background: #fff;
  border: 1px solid var(--border);
  transition: transform var(--spring-fast), box-shadow var(--spring-fast), background var(--transition), border-color var(--transition), color var(--transition);
}

.suggestion-chip:hover {
  color: var(--text);
  border-color: rgba(8, 9, 11, 0.28);
  background: #fff;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--shadow-sm);
}

.suggestion-chip-icon {
  font-size: 13px;
}

.chat-input-area.center-mode {
  width: 100%;
  max-width: 620px;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  gap: 14px;
  max-width: 820px;
  width: 100%;
  margin: 0 auto;
  position: relative;
}

.message-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  flex-shrink: 0;
  position: relative;
}

.assistant-avatar {
  background: var(--glass);
  border: 1px solid var(--border-light);
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.avatar-pulse {
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  border: 2px solid var(--accent);
  opacity: 0.15;
  animation: avatar-ring 2s ease-out infinite;
}

@keyframes avatar-ring {
  0% { transform: scale(1); opacity: 0.4; }
  100% { transform: scale(1.4); opacity: 0; }
}

.message-body {
  flex: 1;
  min-width: 0;
}

.message-role {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
  color: var(--text-secondary);
}

.message-text {
  font-size: 14px;
  line-height: 1.75;
  color: var(--text);
  word-wrap: break-word;
}

.typing-cursor {
  display: inline-block;
  color: var(--accent);
  animation: cursor-blink 1s step-end infinite;
  font-weight: 100;
  margin-left: 2px;
}

@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.typing-indicator {
  display: flex;
  gap: 5px;
  padding: 6px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: var(--accent);
  border-radius: 50%;
  animation: typingBounce 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.thinking-panel {
  max-width: 820px;
  width: 100%;
  margin: 0 auto;
  position: relative;
}

.thinking-panel details {
  overflow: hidden;
  border-radius: var(--radius-sm);
}

.thinking-summary {
  padding: 10px 16px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  user-select: none;
}

.thinking-summary::-webkit-details-marker {
  display: none;
}

.thinking-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--accent-soft);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: think-spin 0.8s linear infinite;
}

@keyframes think-spin {
  to { transform: rotate(360deg); }
}

.thinking-content {
  padding: 0 16px 12px;
  border-top: 1px solid var(--border-light);
}

.thinking-line {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.6;
  padding: 4px 0;
  border-bottom: 1px solid var(--border-light);
}

.thinking-line:last-child {
  border-bottom: none;
}
</style>
