<template>
  <div class="admin-page">
    <div class="animated-bg">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="orb orb-4"></div>
    </div>

    <header class="admin-header glass">
      <div class="header-left">
        <h1 class="header-title">管理后台</h1>
        <span class="header-badge">管理员</span>
      </div>
      <div class="header-right">
        <span class="admin-name">{{ adminName }}</span>
        <button class="btn-logout" @click="onLogout">退出登录</button>
      </div>
    </header>

    <div class="admin-body">
      <!-- 用户列表 -->
      <aside class="user-panel glass-strong">
        <div class="panel-header">
          <h2>注册用户 ({{ users.length }})</h2>
          <button class="btn-refresh" @click="loadUsers" :disabled="loadingUsers">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              :class="{ spinning: loadingUsers }">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
          </button>
        </div>

        <div v-if="loadingUsers" class="panel-loading">加载中...</div>
        <div v-else-if="users.length === 0" class="panel-empty">暂无注册用户</div>
        <ul v-else class="user-list">
          <li
            v-for="user in users"
            :key="user.id"
            class="user-item"
            :class="{ active: selectedUser?.id === user.id }"
            @click="selectUser(user)"
          >
            <img src="/user-avatar.jpg" class="user-avatar" alt="头像" />
            <div class="user-info">
              <div class="user-name">
                {{ user.display_name || user.username }}
              </div>
              <div class="user-meta">@{{ user.username }} · {{ user.created_at }}</div>
            </div>
            <div class="user-actions">
              <button class="btn-action btn-reset" title="重置密码" @click.stop="openResetPwd(user)">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
              </button>
              <button class="btn-action btn-delete" title="注销用户" @click.stop="openDeleteConfirm(user)">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
              </button>
            </div>
          </li>
        </ul>
      </aside>

      <!-- 聊天内容 -->
      <main class="detail-panel glass-strong">
        <template v-if="!selectedUser">
          <div class="detail-empty">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
            <p>选择左侧用户查看聊天记录</p>
          </div>
        </template>

        <template v-else>
          <div class="detail-header">
            <div class="detail-user">
              <img src="/user-avatar.jpg" class="user-avatar large" alt="头像" />
              <div>
                <h3>{{ selectedUser.display_name || selectedUser.username }}</h3>
                <span class="user-meta">@{{ selectedUser.username }} · 共 {{ conversations.length }} 个会话</span>
              </div>
            </div>
          </div>

          <div v-if="loadingChats" class="detail-loading">加载中...</div>
          <div v-else-if="conversations.length === 0" class="detail-empty">
            <p>该用户暂无聊天记录</p>
          </div>
          <div v-else class="chat-list">
            <div
              v-for="conv in conversations"
              :key="conv.id"
              class="chat-card"
              :class="{ expanded: expandedConvId === conv.id }"
            >
              <div class="chat-card-header" @click="toggleConversation(conv.id)">
                <div class="chat-card-title">
                  <span class="chat-icon">💬</span>
                  <span>{{ conv.title || '未命名对话' }}</span>
                </div>
                <div class="chat-card-meta">
                  <span class="chat-time">{{ conv.time }}</span>
                  <span class="msg-count">{{ conv.messages?.length || 0 }} 条消息</span>
                  <svg class="chat-expand-icon" :class="{ rotated: expandedConvId === conv.id }" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="6 9 12 15 18 9"></polyline>
                  </svg>
                </div>
              </div>
              <div v-if="expandedConvId === conv.id" class="chat-messages">
                <div
                  v-for="(msg, idx) in conv.messages"
                  :key="idx"
                  class="chat-msg"
                  :class="msg.role"
                >
                  <div class="msg-role">{{ msg.role === 'user' ? '用户' : '助手' }}</div>
                  <div class="msg-content">{{ msg.content }}</div>
                  <div class="msg-time">{{ msg.time }}</div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </main>
    </div>

    <!-- 注销确认弹窗 -->
    <Teleport to="body">
      <div v-if="showDeleteModal" class="modal-overlay">
        <div class="modal-card">
          <div class="modal-icon danger">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>
          <h3 class="modal-title">确认注销用户</h3>
          <p class="modal-desc">
            即将注销用户 <strong>{{ deleteTarget?.display_name || deleteTarget?.username }}</strong>，该用户的所有聊天记录和数据将被<strong>永久删除</strong>，此操作不可撤销。
          </p>
          <div class="modal-actions">
            <button class="modal-btn modal-btn-cancel" @click="showDeleteModal = false" :disabled="deleting">取消</button>
            <button class="modal-btn modal-btn-danger" @click="confirmDelete" :disabled="deleting">
              <span v-if="deleting" class="btn-spinner"></span>
              <span v-else>确认注销</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 重置密码弹窗 -->
    <Teleport to="body">
      <div v-if="showResetModal" class="modal-overlay">
        <div class="modal-card">
          <div class="modal-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
            </svg>
          </div>
          <h3 class="modal-title">重置密码</h3>
          <p class="modal-desc">
            为用户 <strong>{{ resetTarget?.display_name || resetTarget?.username }}</strong> 设置新密码
          </p>
          <div class="modal-form">
            <label class="form-label">新密码</label>
            <input
              v-model="resetPassword"
              type="text"
              class="form-input"
              placeholder="默认密码 123456789"
              :disabled="resetting"
            />
          </div>
          <div v-if="resetError" class="form-error">{{ resetError }}</div>
          <div class="modal-actions">
            <button class="modal-btn modal-btn-cancel" @click="showResetModal = false" :disabled="resetting">取消</button>
            <button class="modal-btn modal-btn-primary" @click="confirmReset" :disabled="resetting">
              <span v-if="resetting" class="btn-spinner"></span>
              <span v-else>确认重置</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getToken, getUser, logout } from '@/api/auth.js'

const router = useRouter()
const API_BASE = '/api'

const adminName = ref('')
const users = ref([])
const selectedUser = ref(null)
const conversations = ref([])
const expandedConvId = ref(null)
const loadingUsers = ref(false)
const loadingChats = ref(false)

// 注销相关
const showDeleteModal = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

// 重置密码相关
const showResetModal = ref(false)
const resetTarget = ref(null)
const resetPassword = ref('123456789')
const resetError = ref('')
const resetting = ref(false)

const currentUser = getUser()
adminName.value = currentUser?.display_name || currentUser?.username || '管理员'

async function apiFetch(url, options = {}) {
  const token = getToken()
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (res.status === 401) {
    logout()
    router.push('/login')
    throw new Error('未授权')
  }
  if (res.status === 403) {
    router.push('/')
    throw new Error('无权限')
  }
  const data = await res.json()
  if (!res.ok) {
    throw new Error(data.error || '请求失败')
  }
  return data
}

async function loadUsers() {
  loadingUsers.value = true
  try {
    const data = await apiFetch(`${API_BASE}/admin/users`)
    users.value = data.users || []
  } catch (e) {
    console.error('加载用户列表失败:', e)
  } finally {
    loadingUsers.value = false
  }
}

async function selectUser(user) {
  if (selectedUser.value?.id === user.id) return
  selectedUser.value = user
  expandedConvId.value = null
  loadingChats.value = true
  try {
    const data = await apiFetch(`${API_BASE}/admin/users/${user.id}/conversations`)
    conversations.value = data.conversations || []
  } catch (e) {
    console.error('加载对话列表失败:', e)
    conversations.value = []
  } finally {
    loadingChats.value = false
  }
}

function toggleConversation(convId) {
  expandedConvId.value = expandedConvId.value === convId ? null : convId
}

// 注销用户
function openDeleteConfirm(user) {
  deleteTarget.value = user
  showDeleteModal.value = true
}

async function confirmDelete() {
  deleting.value = true
  try {
    await apiFetch(`${API_BASE}/admin/users/${deleteTarget.value.id}/delete`, { method: 'POST' })
    showDeleteModal.value = false
    // 如果被删除的用户正在查看中，清除选择
    if (selectedUser.value?.id === deleteTarget.value.id) {
      selectedUser.value = null
      conversations.value = []
    }
    await loadUsers()
  } catch (e) {
    console.error('注销用户失败:', e)
  } finally {
    deleting.value = false
  }
}

// 重置密码
function openResetPwd(user) {
  resetTarget.value = user
  resetPassword.value = '123456789'
  resetError.value = ''
  showResetModal.value = true
}

async function confirmReset() {
  const pwd = resetPassword.value.trim()
  if (pwd.length < 6) {
    resetError.value = '密码长度不能少于 6 个字符'
    return
  }
  resetting.value = true
  resetError.value = ''
  try {
    await apiFetch(`${API_BASE}/admin/users/${resetTarget.value.id}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ password: pwd }),
    })
    showResetModal.value = false
  } catch (e) {
    resetError.value = e.message
  } finally {
    resetting.value = false
  }
}

function onLogout() {
  logout()
  router.push('/login')
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.admin-page {
  width: 100%;
  height: 100vh;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
}

/* Header */
.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
}

.header-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  background: var(--accent);
  color: var(--bg);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.admin-name {
  font-size: 13px;
  color: var(--text-muted);
}

.btn-logout {
  padding: 6px 14px;
  font-size: 13px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition);
  font-family: inherit;
}

.btn-logout:hover {
  border-color: #ef4444;
  color: #ef4444;
}

/* Body */
.admin-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  padding: 16px;
  gap: 16px;
}

/* User Panel */
.user-panel {
  width: 380px;
  flex-shrink: 0;
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.panel-header h2 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.btn-refresh {
  width: 30px;
  height: 30px;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--panel);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition);
}

.btn-refresh:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.panel-loading,
.panel-empty {
  padding: 24px 0;
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
}

.user-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  flex: 1;
}

.user-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition);
}

.user-item:hover {
  background: var(--hover);
}

.user-item.active {
  background: var(--accent-light);
}

.user-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.user-avatar.large {
  width: 46px;
  height: 46px;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 6px;
}

.user-meta {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 用户操作按钮 */
.user-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity var(--transition);
}

.user-item:hover .user-actions {
  opacity: 1;
}

.btn-action {
  width: 28px;
  height: 28px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition);
}

.btn-reset:hover {
  color: #3b82f6;
  border-color: #3b82f6;
}

.btn-delete:hover {
  color: #ef4444;
  border-color: #ef4444;
}

/* Detail Panel */
.detail-panel {
  flex: 1;
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.detail-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 14px;
  gap: 12px;
}

.detail-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--text-muted);
}

.detail-header {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.detail-user {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-user h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 2px;
}

/* Chat List */
.chat-list {
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chat-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
  transition: border-color var(--transition);
}

.chat-card.expanded {
  border-color: var(--accent);
}

.chat-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  cursor: pointer;
  transition: background var(--transition);
}

.chat-card-header:hover {
  background: var(--hover);
}

.chat-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  min-width: 0;
}

.chat-card-title span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-icon {
  flex-shrink: 0;
}

.chat-card-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.chat-expand-icon {
  transition: transform 0.2s ease;
}

.chat-expand-icon.rotated {
  transform: rotate(180deg);
}

.chat-messages {
  border-top: 1px solid var(--border);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 400px;
  overflow-y: auto;
}

.chat-msg {
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--panel);
}

.chat-msg.user {
  border-left: 3px solid var(--accent);
}

.chat-msg.assistant {
  border-left: 3px solid #22c55e;
}

.msg-role {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 4px;
  text-transform: uppercase;
}

.msg-content {
  font-size: 13px;
  color: var(--text);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.msg-time {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 4px;
  text-align: right;
}

/* ========== 弹窗 ========== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.15s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 32px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: scaleIn 0.2s ease;
}

@keyframes scaleIn {
  from { transform: scale(0.95); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.modal-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  background: var(--accent-light);
  color: var(--accent);
}

.modal-icon.danger {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.modal-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  text-align: center;
  margin: 0 0 12px;
}

.modal-desc {
  font-size: 13px;
  color: var(--text-muted);
  text-align: center;
  line-height: 1.6;
  margin: 0 0 24px;
}

.modal-desc strong {
  color: var(--text);
}

.modal-form {
  margin-bottom: 16px;
}

.modal-form .form-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.modal-form .form-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: inherit;
  color: var(--text);
  background: var(--bg);
  outline: none;
  box-sizing: border-box;
  transition: border-color var(--transition);
}

.modal-form .form-input:focus {
  border-color: var(--accent);
}

.form-error {
  font-size: 12px;
  color: #ef4444;
  margin-bottom: 12px;
  text-align: center;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.modal-btn {
  padding: 10px 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all var(--transition);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 100px;
}

.modal-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.modal-btn-cancel {
  background: var(--panel);
  color: var(--text-secondary);
}

.modal-btn-cancel:hover:not(:disabled) {
  background: var(--hover);
}

.modal-btn-danger {
  background: #ef4444;
  color: #fff;
  border-color: #ef4444;
}

.modal-btn-danger:hover:not(:disabled) {
  background: #dc2626;
}

.modal-btn-primary {
  background: var(--accent);
  color: var(--bg);
  border-color: var(--accent);
}

.modal-btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  opacity: 0.8;
}
</style>
