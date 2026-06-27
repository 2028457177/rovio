<template>
  <div class="app-layout">
    <div class="animated-bg">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="orb orb-4"></div>
    </div>
    <div class="cursor-glow"></div>

    <!-- 移动端遮罩层 -->
    <div
      class="sidebar-overlay"
      :class="{ visible: sidebarOpen }"
      @click="onCloseSidebar"
    ></div>

    <aside class="sidebar glass-strong" :class="{ open: sidebarOpen }">
      <div class="sidebar-header">
        <div class="sidebar-logo">
          <img src="/favicon.png" alt="头像" class="logo-img" />
          <div class="logo-glow"></div>
        </div>
        <div>
          <div class="sidebar-title">Rovio</div>
          <div class="sidebar-subtitle">智能 AI 助手</div>
        </div>
      </div>

      <button class="sidebar-new-chat" @click="onMobileNewChat">
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
          v-for="(conv, index) in conversations"
          :key="conv.id"
          :style="{ '--i': index }"
          @click="onMobileSwitchConversation(conv.id)"
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

    </aside>

    <main class="main-content">
      <header class="chat-header glass">
        <button class="hamburger-btn" @click="onToggleSidebar" :aria-label="sidebarOpen ? '关闭菜单' : '打开菜单'">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <line v-if="!sidebarOpen" x1="3" y1="6" x2="21" y2="6"></line>
            <line v-if="!sidebarOpen" x1="3" y1="12" x2="21" y2="12"></line>
            <line v-if="!sidebarOpen" x1="3" y1="18" x2="21" y2="18"></line>
            <line v-if="sidebarOpen" x1="18" y1="6" x2="6" y2="18"></line>
            <line v-if="sidebarOpen" x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
        <div class="chat-header-left">
          <span class="chat-header-title">
            <span class="header-glow"></span>
            {{ currentConversation ? currentConversation.title : 'AI 对话' }}
          </span>
          <p v-if="showWelcome" class="chat-header-subtitle">基于 AI 的智能助手，请在下方输入你的需求</p>
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
          <div class="welcome-hero">
            <div class="welcome-hero-glow"></div>
            <h1 class="welcome-hero-title">
              <span class="welcome-text">欢迎来到</span>
              <span class="brand-text">Rovio</span>
            </h1>
            <p class="welcome-hero-subtitle">你的智能办公助手，随时为你效劳</p>
          </div>
          <div class="welcome-suggestions-small">
            <button
              v-for="(item, index) in suggestions"
              :key="item.prompt"
              class="suggestion-chip"
              :style="{ '--i': index }"
              @click="showTutorial(item)"
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

        <TransitionGroup name="message-list" tag="div" class="messages-list" :key="sessionId">
          <MessageBubble
            v-for="(msg, index) in messages"
            :key="msg.id"
            :message="msg"
            :index="index"
            :streaming="!!msg.streaming"
            :thinking-content="msg.streaming ? thinkingContent : ''"
          />
        </TransitionGroup>
      </div>

      <ChatInput
        v-if="!showWelcome"
        :disabled="isStreaming"
        @send="onSendMessage"
      />
    </main>

    <!-- 左下角折叠式用户面板 -->
    <div class="user-panel" ref="userPanelRef">
      <Transition name="panel-fade">
        <div v-if="userPanelOpen" class="user-dropdown glass-strong">
          <div class="user-dropdown-header">
            <img src="/user-avatar.jpg" class="user-dropdown-avatar" alt="头像" />
            <div class="user-dropdown-info">
              <div class="user-dropdown-name" :title="username">{{ username }}</div>
              <div class="user-dropdown-role">普通用户</div>
            </div>
          </div>

          <div class="user-dropdown-divider"></div>

          <button class="user-dropdown-item" @click="toggleTheme">
            <span class="user-dropdown-icon">
              <svg v-if="theme === 'dark'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="5"></circle>
                <line x1="12" y1="1" x2="12" y2="3"></line>
                <line x1="12" y1="21" x2="12" y2="23"></line>
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                <line x1="1" y1="12" x2="3" y2="12"></line>
                <line x1="21" y1="12" x2="23" y2="12"></line>
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
              </svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
              </svg>
            </span>
            <span class="user-dropdown-label">{{ theme === 'dark' ? '浅色主题' : '深色主题' }}</span>
            <span class="user-dropdown-arrow">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </span>
          </button>

          <div class="user-dropdown-divider"></div>

          <button class="user-dropdown-item user-dropdown-logout" @click="onLogout">
            <span class="user-dropdown-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                <polyline points="16 17 21 12 16 7"></polyline>
                <line x1="21" y1="12" x2="9" y2="12"></line>
              </svg>
            </span>
            <span class="user-dropdown-label">退出登录</span>
          </button>
        </div>
      </Transition>

      <button
        class="user-bar glass-strong"
        :class="{ expanded: userPanelOpen }"
        @click="onToggleUserPanel"
        aria-haspopup="true"
        :aria-expanded="userPanelOpen"
      >
        <img src="/user-avatar.jpg" class="user-bar-avatar" alt="头像" />
        <span class="user-bar-name" :title="username">{{ username }}</span>
        <svg
          class="user-bar-chevron"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        >
          <polyline points="18 15 12 9 6 15"></polyline>
        </svg>
      </button>
    </div>

    <!-- 教程弹窗 -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="tutorialModalOpen" class="tutorial-overlay" @click.self="closeTutorial">
          <div class="tutorial-modal glass-strong">
            <div class="tutorial-modal-header">
              <h2 class="tutorial-modal-title">{{ selectedTutorial?.title }}</h2>
              <button class="tutorial-modal-close" @click="closeTutorial">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div class="tutorial-modal-body">
              <p class="tutorial-intro">{{ selectedTutorial?.intro }}</p>
              <div class="tutorial-section">
                <h3 class="tutorial-section-title">
                  <span class="tutorial-section-icon">📋</span>
                  操作步骤
                </h3>
                <ol class="tutorial-step-list">
                  <li v-for="(step, i) in selectedTutorial?.steps" :key="i" class="tutorial-step-item">
                    <span class="tutorial-step-num">{{ i + 1 }}</span>
                    <span>{{ step }}</span>
                  </li>
                </ol>
              </div>
              <div class="tutorial-section">
                <h3 class="tutorial-section-title">
                  <span class="tutorial-section-icon">💡</span>
                  使用技巧
                </h3>
                <ul class="tutorial-tip-list">
                  <li v-for="(tip, i) in selectedTutorial?.tips" :key="i" class="tutorial-tip-item">{{ tip }}</li>
                </ul>
              </div>
            </div>
            <div class="tutorial-modal-footer">
              <button class="tutorial-btn-close" @click="closeTutorial">我知道了</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChat } from '@/composables/useChat.js'
import { useTheme } from '@/composables/useTheme.js'
import { getUser, logout } from '@/api/auth.js'
import MessageBubble from '@/components/MessageBubble.vue'
import ChatInput from '@/components/ChatInput.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'

const router = useRouter()
const { theme, toggle: toggleTheme } = useTheme()

const {
  messages,
  sessionId,
  isStreaming,
  error,
  streamingContent,
  thinkingContent,
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

const chatContainer = ref(null)
const userPanelRef = ref(null)
const userPanelOpen = ref(false)
const tutorialModalOpen = ref(false)
const selectedTutorial = ref(null)

function onToggleUserPanel() {
  userPanelOpen.value = !userPanelOpen.value
}

function closeUserPanel(e) {
  if (userPanelRef.value && !userPanelRef.value.contains(e.target)) {
    userPanelOpen.value = false
  }
}

// 用户信息
const user = getUser()
const username = computed(() => user ? (user.display_name || user.username) : '')
const userInitial = computed(() => username.value ? username.value.charAt(0).toUpperCase() : '?')

// 移动端侧边栏状态
const sidebarOpen = ref(false)

function onLogout() {
  logout()
  router.push('/login')
}

function onToggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}

function onCloseSidebar() {
  sidebarOpen.value = false
}

// 监听窗口大小变化，大屏时自动关闭移动端侧边栏
function onResize() {
  if (window.innerWidth >= 768) {
    sidebarOpen.value = false
  }
}

function updateMotion(e) {
  const cx = (e.clientX / window.innerWidth) * 100
  const cy = (e.clientY / window.innerHeight) * 100
  const mx = (e.clientX / window.innerWidth - 0.5) * 2
  const my = (e.clientY / window.innerHeight - 0.5) * 2
  const root = document.documentElement
  root.style.setProperty('--cx', `${cx}%`)
  root.style.setProperty('--cy', `${cy}%`)
  root.style.setProperty('--mx', mx)
  root.style.setProperty('--my', my)
}

onMounted(() => {
  window.addEventListener('resize', onResize)
  window.addEventListener('mousemove', updateMotion, { passive: true })
  document.addEventListener('click', closeUserPanel)
  loadConversations()
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('mousemove', updateMotion)
  document.removeEventListener('click', closeUserPanel)
})

const suggestions = [
  {
    icon: '📄',
    label: '自动填写文档',
    prompt: '帮我自动填写Word模板文件',
    tutorial: {
      title: '自动填写文档',
      intro: '上传一个 Word 模板文件，助手会根据你的需求自动填充模板中的占位内容，生成完整的文档。',
      steps: [
        '点击输入框旁的附件按钮，上传你的 Word 模板文件（.docx 格式）',
        '在输入框中描述你想填充的内容，例如："帮我填写这份合同，甲方是XX公司，金额10万元"',
        '发送后助手会自动读取模板结构并生成填写好的文档',
      ],
      tips: [
        '模板中建议用 {{变量名}} 标记需要填充的位置',
        '描述需求时尽量具体，包括关键信息和格式要求',
        '上传文件大小限制为 10MB',
      ],
    },
  },
  {
    icon: '🌤️',
    label: '查询天气',
    prompt: '帮我查询今天的天气',
    tutorial: {
      title: '查询天气',
      intro: '输入城市名称，助手会为你查询实时天气信息，包括温度、湿度、风力等详细数据。',
      steps: [
        '在输入框中输入你想查询天气的城市，例如："查询北京的天气"',
        '也可以指定日期，例如："查询杭州明天的天气"',
        '助手会自动获取最新的天气预报数据并返回给你',
      ],
      tips: [
        '支持查询国内主要城市的天气信息',
        '可以同时查询多个城市，用逗号分隔',
        '预报数据来源于权威气象平台，每日更新',
      ],
    },
  },
  {
    icon: '📊',
    label: '生成工作报告',
    prompt: '帮我生成一份个人工作数据报告',
    tutorial: {
      title: '生成工作报告',
      intro: '描述你的工作内容和需求，助手会帮你生成一份结构清晰、内容完整的工作报告。',
      steps: [
        '在输入框中描述你的工作内容和报告需求，例如："帮我写一份本周工作总结，包含项目进度、遇到的问题和下周计划"',
        '可以指定报告的格式和风格，如正式/轻松、简短/详细',
        '助手会生成一份包含标题、分点、数据汇总的完整报告',
      ],
      tips: [
        '提供更多具体信息可以让报告更加个性化',
        '可以分多次对话逐步完善报告内容',
        '生成的报告可以直接复制粘贴到文档软件中使用',
      ],
    },
  },
  {
    icon: '🔍',
    label: '联网搜索',
    prompt: '帮我搜索最新的办公效率工具',
    tutorial: {
      title: '联网搜索',
      intro: '助手可以帮你联网搜索最新的信息、资料和工具，实时获取互联网上的内容。',
      steps: [
        '在输入框中输入你想搜索的内容，例如："搜索2024年最流行的AI办公工具"',
        '助手会自动调用搜索引擎获取最新的相关信息',
        '搜索完成后会为你整理出清晰的结果和摘要',
      ],
      tips: [
        '搜索关键词越具体，结果越精准',
        '可以要求助手总结搜索结果的关键要点',
        '支持搜索新闻、技术、百科等多种类型的内容',
      ],
    },
  },
]

function showTutorial(item) {
  selectedTutorial.value = item.tutorial
  tutorialModalOpen.value = true
}

function closeTutorial() {
  tutorialModalOpen.value = false
  selectedTutorial.value = null
}

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
watch(thinkingContent, scrollToBottom)
watch(isStreaming, (streaming) => {
  document.body.classList.toggle('streaming-active', streaming)
})

onUnmounted(() => {
  document.body.classList.remove('streaming-active')
})

function onSendMessage(message, uploadedFilePath) {
  sendMessage(message, uploadedFilePath)
}

function onNewChat() {
  newChat()
}

function onMobileNewChat() {
  onNewChat()
  onCloseSidebar()
}

function onSwitchConversation(conversationId) {
  switchToConversation(conversationId)
}

function onMobileSwitchConversation(conversationId) {
  onSwitchConversation(conversationId)
  onCloseSidebar()
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
  padding: 20px 20px 90px;
  z-index: 10;
  border-radius: 0;
  border-right: 1px solid var(--border);
  background:
    linear-gradient(180deg, var(--panel), rgba(var(--accent-rgb), 0.05)),
    var(--bg);
  transition: background 0.35s ease, border-color 0.35s ease;
}

[data-theme="dark"] .sidebar {
  background:
    linear-gradient(180deg, rgba(30, 33, 40, 0.98), rgba(22, 25, 31, 0.95)),
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
  background: var(--panel);
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
  background: var(--panel);
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
  animation: sidebar-item-in 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  animation-delay: calc(var(--i, 0) * 40ms);
}

.sidebar-chat-item:hover {
  background: var(--glass-light);
  color: var(--text);
  transform: translateX(3px);
}

@keyframes sidebar-item-in {
  from {
    opacity: 0;
    transform: translateX(-12px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.sidebar-chat-item.active {
  background: var(--panel);
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

/* 左下角折叠式用户面板 */
.user-panel {
  position: fixed;
  bottom: 20px;
  left: 20px;
  z-index: 20;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.user-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border);
  box-shadow: 0 4px 20px var(--shadow-sm);
  background: var(--glass-strong);
  cursor: pointer;
  font-family: inherit;
  transition: background var(--transition), border-color var(--transition), box-shadow var(--transition);
}

.user-bar:hover {
  background: var(--panel);
  border-color: rgba(8, 9, 11, 0.28);
  box-shadow: 0 8px 24px var(--shadow);
}

.user-bar-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.user-bar-name {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-bar-chevron {
  color: var(--text-muted);
  flex-shrink: 0;
  transition: transform 0.25s ease;
}

.user-bar.expanded .user-bar-chevron {
  transform: rotate(180deg);
}

.user-bar.expanded {
  background: var(--panel);
}

/* 展开面板 */
.user-dropdown {
  width: 240px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  box-shadow: 0 12px 40px var(--shadow);
  overflow: hidden;
  padding: 8px 0;
  background: var(--glass-strong);
  transform-origin: bottom left;
}

.panel-fade-enter-active,
.panel-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.panel-fade-enter-from,
.panel-fade-leave-to {
  opacity: 0;
  transform: scale(0.96) translateY(10px);
}

.panel-fade-enter-to,
.panel-fade-leave-from {
  opacity: 1;
  transform: scale(1) translateY(0);
}

.user-dropdown-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
}

.user-dropdown-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.user-dropdown-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-dropdown-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-dropdown-role {
  font-size: 12px;
  color: var(--text-muted);
}

.user-dropdown-divider {
  height: 1px;
  background: var(--border-light);
  margin: 8px 12px;
}

.user-dropdown-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 16px;
  border: none;
  background: none;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  font-family: inherit;
  transition: background var(--transition), color var(--transition);
}

.user-dropdown-item:hover {
  background: var(--accent-light);
  color: var(--text);
}

.user-dropdown-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.user-dropdown-item:hover .user-dropdown-icon {
  color: var(--accent);
}

.user-dropdown-label {
  flex: 1;
  text-align: left;
}

.user-dropdown-arrow {
  display: flex;
  align-items: center;
  color: var(--text-muted);
  flex-shrink: 0;
}

.user-dropdown-logout {
  color: var(--text-secondary);
}

.user-dropdown-logout:hover {
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
}

.user-dropdown-logout:hover .user-dropdown-icon {
  color: #ef4444;
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
  background: var(--panel);
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
  background: var(--panel);
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

.welcome-hero {
  position: relative;
  text-align: center;
  margin-bottom: 8px;
  animation: hero-in 1s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}

@keyframes hero-in {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.welcome-hero-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 220px;
  height: 120px;
  transform: translate(-50%, -50%);
  background: radial-gradient(ellipse at center, rgba(8, 10, 14, 0.08), transparent 70%);
  filter: blur(24px);
  z-index: -1;
  animation: glow-breathe 4s ease-in-out infinite;
}

[data-theme="dark"] .welcome-hero-glow {
  background: radial-gradient(ellipse at center, rgba(255, 255, 255, 0.08), transparent 70%);
}

@keyframes glow-breathe {
  0%, 100% { opacity: 0.6; transform: translate(-50%, -50%) scale(1); }
  50% { opacity: 1; transform: translate(-50%, -50%) scale(1.08); }
}

.welcome-hero-title {
  font-size: 48px;
  font-weight: 700;
  line-height: 1.15;
  margin: 0 0 12px;
  letter-spacing: -1px;
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 14px;
  flex-wrap: wrap;
}

.welcome-text {
  color: var(--text);
  font-weight: 500;
  letter-spacing: 2px;
  animation: text-slide 1s cubic-bezier(0.4, 0, 0.2, 1) 0.2s both;
}

.brand-text {
  background: linear-gradient(135deg, #1f2329 0%, #4a5568 50%, #1f2329 100%);
  background-size: 200% auto;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 800;
  animation: text-slide 1s cubic-bezier(0.4, 0, 0.2, 1) 0.35s both, shine 4s linear infinite 1.2s;
}

[data-theme="dark"] .brand-text {
  background: linear-gradient(135deg, #f3f4f6 0%, #9ca3af 50%, #f3f4f6 100%);
  background-size: 200% auto;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

@keyframes text-slide {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes shine {
  to { background-position: 200% center; }
}

.welcome-hero-subtitle {
  font-size: 15px;
  color: var(--text-secondary);
  margin: 0;
  letter-spacing: 0.5px;
  animation: text-slide 1s cubic-bezier(0.4, 0, 0.2, 1) 0.5s both;
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
  background: var(--panel);
  border: 1px solid var(--border);
  transition: transform var(--spring-fast), box-shadow var(--spring-fast), background var(--transition), border-color var(--transition), color var(--transition);
  animation: chip-in 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  animation-delay: calc(var(--i, 0) * 70ms);
}

.suggestion-chip:hover {
  color: var(--text);
  border-color: rgba(8, 9, 11, 0.28);
  background: var(--panel);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--shadow-sm);
}

@keyframes chip-in {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
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

/* ========== 移动端适配 ========== */
.hamburger-btn {
  display: none;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  flex-shrink: 0;
  transition: background var(--transition);
}

.hamburger-btn:hover {
  background: var(--accent-light);
}

.sidebar-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 9;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.sidebar-overlay.visible {
  opacity: 1;
  pointer-events: auto;
}

@media (max-width: 767px) {
  .hamburger-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    margin-right: 4px;
    color: var(--text);
  }

  .sidebar-overlay {
    display: block;
  }

  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: 280px;
    z-index: 10;
    transform: translateX(-100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border-radius: 0;
    border-right: 1px solid var(--border);
    padding: calc(var(--safe-top) + 16px) 20px 90px;
  }

  .sidebar.open {
    transform: translateX(0);
    box-shadow: 0 0 40px var(--shadow);
  }

  .sidebar-logo {
    width: 36px;
    height: 36px;
  }

  .sidebar-title {
    font-size: 16px;
  }

  .sidebar-subtitle {
    font-size: 11px;
  }

  .main-content {
    padding-top: var(--safe-top);
  }

  .chat-header {
    padding: 8px 12px;
    align-items: center;
    flex-wrap: nowrap;
    background: var(--panel);
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
    border-bottom: 0.5px solid var(--border-light);
    min-height: 48px;
  }

  .chat-header-left {
    flex: 1;
    min-width: 0;
  }

  .chat-header-title {
    font-size: 16px;
    font-weight: 600;
  }

  .header-glow {
    display: none;
  }

  .chat-header-subtitle {
    display: none;
  }

  .chat-header-actions {
    flex-shrink: 0;
    width: auto;
    margin-top: 0;
    padding-left: 0;
  }

  .chat-header-btn {
    font-size: 12px;
    padding: 6px 10px;
    gap: 4px;
    border: none;
    background: transparent;
    color: var(--accent);
    font-weight: 500;
  }

  .chat-messages {
    padding: 8px 8px;
  }

  .welcome-center {
    padding: 0 20px;
    gap: 24px;
  }

  .welcome-hero-title {
    font-size: 34px;
    gap: 8px;
  }

  .welcome-hero-subtitle {
    font-size: 13px;
  }

  .welcome-suggestions-small {
    flex-direction: column;
    gap: 8px;
    max-width: 100%;
    width: 100%;
  }

  .suggestion-chip {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 16px;
    border-radius: 16px;
    font-size: 14px;
    flex: none;
    width: 100%;
    justify-content: flex-start;
    border: 1px solid var(--border-light);
    background: var(--panel);
    box-shadow: 0 1px 3px var(--shadow-sm);
  }

  .suggestion-chip:active {
    background: var(--glass-light);
    transform: scale(0.98);
  }

  .suggestion-chip-icon {
    display: block;
    font-size: 20px;
    width: 32px;
    text-align: center;
    flex-shrink: 0;
  }

  .messages-list {
    gap: 8px;
  }

  .chat-header,
  .chat-input-area {
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }

  .app-layout {
    background: var(--bg);
  }
}

/* ========== 教程弹窗 ========== */
.tutorial-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.tutorial-modal {
  width: 100%;
  max-width: 520px;
  max-height: 85vh;
  overflow-y: auto;
  border-radius: var(--radius-lg);
  background: var(--glass-strong);
  border: 1px solid var(--border);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
}

[data-theme="dark"] .tutorial-modal {
  background: rgba(22, 25, 31, 0.96);
}

.tutorial-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
}

.tutorial-modal-title {
  font-size: 20px;
  font-weight: 620;
  color: var(--text);
  margin: 0;
}

.tutorial-modal-close {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: var(--panel);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  transition: background var(--transition), color var(--transition);
  flex-shrink: 0;
}

.tutorial-modal-close:hover {
  background: var(--border);
  color: var(--text);
}

.tutorial-modal-body {
  padding: 16px 24px 8px;
  flex: 1;
  overflow-y: auto;
}

.tutorial-intro {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-secondary);
  margin: 0 0 20px;
}

.tutorial-section {
  margin-bottom: 20px;
}

.tutorial-section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 10px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tutorial-section-icon {
  font-size: 15px;
}

.tutorial-step-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tutorial-step-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text);
}

.tutorial-step-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

.tutorial-tip-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tutorial-tip-item {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
  padding-left: 16px;
  position: relative;
}

.tutorial-tip-item::before {
  content: '•';
  position: absolute;
  left: 4px;
  color: var(--accent);
  font-weight: bold;
}

.tutorial-modal-footer {
  padding: 12px 24px 20px;
  display: flex;
  justify-content: flex-end;
}

.tutorial-btn-close {
  padding: 8px 24px;
  border-radius: var(--radius);
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  transition: opacity var(--transition), transform var(--spring-fast);
}

.tutorial-btn-close:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.tutorial-btn-close:active {
  transform: translateY(0);
}

/* Modal transition */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}

.modal-fade-enter-active .tutorial-modal,
.modal-fade-leave-active .tutorial-modal {
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.25s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-from .tutorial-modal {
  transform: scale(0.92) translateY(20px);
  opacity: 0;
}

.modal-fade-leave-to .tutorial-modal {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}
</style>
