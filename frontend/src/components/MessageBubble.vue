<template>
  <div
    class="message-row"
    :class="[message.role, { streaming: streaming, 'is-mine': message.role === 'user' }]"
    :style="{ '--msg-index': index }"
  >
    <div class="message-wrapper" :class="message.role">
      <div v-if="message.role !== 'user'" class="message-avatar" :class="`avatar-${message.role}`">
        <span v-if="streaming && message.role === 'assistant'" class="avatar-pulse"></span>
        <img v-if="message.role === 'assistant'" src="/agent-avatar.jpg" alt="助手" class="avatar-img" />
        <img v-else src="/user-avatar.jpg" alt="头像" class="avatar-img" />
      </div>
      <div class="message-body">
        <div v-if="message.role === 'assistant'" class="message-role">Rovio</div>

        <!-- 编辑模式（仅用户消息） -->
        <template v-if="editing && message.role === 'user'">
          <div class="edit-box">
            <textarea
              ref="editTextareaRef"
              v-model="editingText"
              class="edit-textarea"
              rows="2"
              @keydown.esc="cancelEdit"
              @keydown.enter.exact.prevent="commitEdit"
            ></textarea>
            <div class="edit-actions">
              <button class="edit-btn cancel" @click="cancelEdit">取消</button>
              <button class="edit-btn primary" @click="commitEdit">发送</button>
            </div>
          </div>
        </template>

        <!-- 思考面板 -->
        <template v-else-if="streaming && !message.content && thinkingContent">
          <div class="thinking-panel">
            <details :open="true" class="glass">
              <summary class="thinking-summary">
                <span class="thinking-spinner"></span>
                正在梳理思路…
              </summary>
              <div class="thinking-content" ref="thinkingContentRef">{{ thinkingContent }}</div>
            </details>
          </div>
        </template>

        <!-- 普通消息气泡 + Plan 面板 -->
        <template v-else>
          <!-- DeepAgent 执行计划面板（多步任务时显示，与消息气泡并列） -->
          <PlanPanel
            v-if="message.plan"
            :plan="message.plan"
            :steps="message.steps"
            :streaming="streaming"
          />

          <div class="message-bubble" :class="`bubble-${message.role}`">
            <div v-if="streaming && !message.content && !message.plan" class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
            <div
              v-else-if="message.content"
              class="message-text"
              v-html="renderedHtml"
              @click="onContentClick"
            ></div>
          </div>

          <!-- 消息操作栏 -->
          <div v-if="!streaming && message.content" class="message-meta">
            <span class="message-time">{{ message.time }}</span>

            <div class="message-actions">
              <!-- 复制 -->
              <button class="msg-action" :class="{ active: copied }" @click="onCopy" :title="copied ? '已复制' : '复制内容'">
                <svg v-if="!copied" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              </button>

              <!-- 用户消息：编辑后重发 -->
              <button
                v-if="message.role === 'user'"
                class="msg-action"
                @click="startEdit"
                title="编辑后重发"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 20h9"></path>
                  <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                </svg>
              </button>

              <!-- AI 消息：重新生成 -->
              <button
                v-if="message.role === 'assistant' && canRegenerate"
                class="msg-action"
                :disabled="regenerating"
                @click="onRegenerate"
                :title="regenerating ? '生成中' : '重新生成'"
              >
                <svg :class="{ spinning: regenerating }" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="23 4 23 10 17 10"></polyline>
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                </svg>
              </button>

              <!-- AI 消息：在此分叉 -->
              <button
                v-if="message.role === 'assistant' && canBranch"
                class="msg-action"
                :disabled="branching"
                @click="onBranch"
                :title="branching ? '分叉中' : '从此处分叉对话'"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="6" y1="3" x2="6" y2="15"></line>
                  <circle cx="18" cy="6" r="3"></circle>
                  <circle cx="6" cy="18" r="3"></circle>
                  <path d="M18 9a9 9 0 0 1-9 9"></path>
                </svg>
              </button>

              <!-- 流式中的 AI 消息：停止生成 -->
              <button
                v-if="streaming && message.role === 'assistant'"
                class="msg-action stop-btn"
                @click="onStop"
                title="停止生成"
              >
                <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
                  <rect x="6" y="6" width="12" height="12" rx="2"></rect>
                </svg>
              </button>

              <!-- AI 消息：点赞 -->
              <button
                v-if="message.role === 'assistant'"
                class="msg-action"
                :class="{ active: feedback === 'like' }"
                @click="onFeedback('like')"
                title="点赞"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" :fill="feedback === 'like' ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
                </svg>
              </button>

              <!-- AI 消息：踩 -->
              <button
                v-if="message.role === 'assistant'"
                class="msg-action"
                :class="{ active: feedback === 'dislike' }"
                @click="onFeedback('dislike')"
                title="踩"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" :fill="feedback === 'dislike' ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zM17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path>
                </svg>
              </button>
            </div>

            <span v-if="copied" class="action-hint">已复制</span>
            <span v-if="feedbackSaved" class="action-hint">已记录反馈</span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { renderMarkdown } from '@/utils/markdown.js'
import PlanPanel from '@/components/PlanPanel.vue'

const props = defineProps({
  message: { type: Object, required: true },
  index: { type: Number, default: 0 },
  streaming: { type: Boolean, default: false },
  thinkingContent: { type: String, default: '' },
  canRegenerate: { type: Boolean, default: true },
  canBranch: { type: Boolean, default: true }
})

const emit = defineEmits(['copy', 'regenerate', 'edit', 'stop', 'feedback', 'branch'])

const copied = ref(false)
const feedback = ref(props.message.feedback || '') // 'like' | 'dislike' | ''
const feedbackSaved = ref(false)
const regenerating = ref(false)
const branching = ref(false)
let copyTimer = null
let feedbackTimer = null

// 思考面板：内容更新时自动滚动到底部，让最新推理可见（面板高度受限）
const thinkingContentRef = ref(null)
watch(() => props.thinkingContent, () => {
  nextTick(() => {
    const el = thinkingContentRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
})

// 编辑模式
const editing = ref(false)
const editingText = ref('')
const editTextareaRef = ref(null)

const renderedHtml = computed(() => renderMarkdown(props.message.content))

function onContentClick(e) {
  // 代码块复制按钮（事件委托）
  const btn = e.target.closest('.code-copy-btn')
  if (btn) {
    const raw = btn.getAttribute('data-copy')
    if (raw) {
      copyToClipboard(decodeURIComponent(raw))
      const original = btn.textContent
      btn.textContent = '已复制'
      btn.classList.add('copied')
      setTimeout(() => {
        btn.textContent = original
        btn.classList.remove('copied')
      }, 1600)
    }
    return
  }
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    try { document.execCommand('copy') } catch {}
    document.body.removeChild(ta)
  }
}

async function onCopy() {
  await copyToClipboard(props.message.content)
  copied.value = true
  clearTimeout(copyTimer)
  copyTimer = setTimeout(() => { copied.value = false }, 1600)
  emit('copy', props.message)
}

function startEdit() {
  editing.value = true
  editingText.value = props.message.content
  nextTick(() => {
    if (editTextareaRef.value) {
      editTextareaRef.value.focus()
      const el = editTextareaRef.value
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 240) + 'px'
    }
  })
}

function cancelEdit() {
  editing.value = false
  editingText.value = ''
}

function commitEdit() {
  const text = editingText.value.trim()
  if (!text || text === props.message.content) {
    editing.value = false
    return
  }
  emit('edit', { message: props.message, newContent: text })
  editing.value = false
}

function onRegenerate() {
  if (regenerating.value) return
  regenerating.value = true
  emit('regenerate', props.message)
  // 由父组件切换 streaming 状态后会自动收起按钮
  setTimeout(() => { regenerating.value = false }, 1500)
}

function onBranch() {
  if (branching.value) return
  branching.value = true
  emit('branch', props.message)
  // 分叉是异步操作，给个兜底超时恢复（实际成功后父组件会切走本视图）
  setTimeout(() => { branching.value = false }, 2000)
}

function onStop() {
  emit('stop', props.message)
}

function onFeedback(type) {
  // 切换：再次点击同项则取消
  const next = feedback.value === type ? '' : type
  feedback.value = next
  feedbackSaved.value = true
  clearTimeout(feedbackTimer)
  feedbackTimer = setTimeout(() => { feedbackSaved.value = false }, 1400)
  emit('feedback', { message: props.message, feedback: next })
}

onUnmounted(() => {
  clearTimeout(copyTimer)
  clearTimeout(feedbackTimer)
})
</script>

<style scoped>
.message-row {
  display: flex;
  width: 100%;
  animation: msg-in 0.55s var(--ease-out-expo) both;
  animation-delay: calc(var(--msg-index, 0) * 55ms);
}

@keyframes msg-in {
  from { opacity: 0; transform: translateY(20px); filter: blur(3px); }
  to { opacity: 1; transform: translateY(0); filter: blur(0); }
}

.message-row.user { justify-content: flex-end; }

.message-wrapper {
  display: flex;
  gap: 14px;
  max-width: 100%;
  width: fit-content;
}

.message-wrapper.user {
  flex-direction: row-reverse;
  width: fit-content;
  max-width: 560px;
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

.avatar-user {
  overflow: hidden;
  box-shadow: 0 3px 10px var(--shadow-sm);
}

.avatar-assistant {
  overflow: hidden;
  border: 1.5px solid rgba(var(--accent-rgb), 0.25);
  box-shadow: 0 3px 12px rgba(var(--accent-rgb), 0.16);
}

.avatar-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  position: relative;
  z-index: 1;
}

.avatar-pulse {
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  border: 2px solid var(--accent);
  animation: avatar-ring 1.8s ease-out infinite;
  pointer-events: none;
}

@keyframes avatar-ring {
  0% { transform: scale(1); opacity: 0.45; }
  100% { transform: scale(1.45); opacity: 0; }
}

.message-body {
  flex: 0 1 auto;
  min-width: 0;
}

.message-wrapper.user .message-body {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex: 0 1 auto;
}

.message-role {
  font-size: 12.5px;
  font-weight: 700;
  letter-spacing: 1px;
  margin-bottom: 7px;
  color: var(--text-muted);
}

.message-bubble {
  overflow: hidden;
  width: 100%;
}

.bubble-assistant {
  border-radius: 4px 1.15rem 1.15rem 1.15rem;
  background: transparent;
  width: fit-content;
}

.bubble-user {
  border-radius: 1.15rem 4px 1.15rem 1.15rem;
  background: var(--panel);
  border: 1px solid var(--border-light);
  box-shadow: 0 4px 18px var(--shadow-sm);
  width: fit-content;
  transition: box-shadow var(--transition), transform var(--spring-fast);
}

.message-row.user:hover .bubble-user {
  box-shadow: 0 8px 26px var(--shadow-sm);
  transform: translateY(-1px);
}

.bubble-assistant .message-text { position: relative; }

.message-row.streaming .bubble-assistant .message-text::after {
  content: '';
  display: inline-block;
  width: 8px;
  height: 15px;
  margin-left: 3px;
  vertical-align: -2px;
  border-radius: 2px;
  background: var(--accent);
  animation: cursor-blink 0.85s steps(2, start) infinite;
}

@keyframes cursor-blink { to { visibility: hidden; } }

.typing-indicator {
  display: flex;
  gap: 5px;
  padding: 10px 6px;
}

.typing-indicator span {
  width: 7px;
  height: 7px;
  background: var(--accent);
  border-radius: 50%;
  animation: typing-bounce 1.3s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.18s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.36s; }

@keyframes typing-bounce {
  0%, 80%, 100% { transform: translateY(0) scale(0.7); opacity: 0.35; }
  40% { transform: translateY(-5px) scale(1); opacity: 1; }
}

/* 思考面板 */
.thinking-panel { margin-bottom: 8px; position: relative; }

.thinking-panel details {
  overflow: hidden;
  border-radius: var(--radius-sm);
}

.thinking-summary {
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 9px;
  user-select: none;
  transition: color var(--transition);
}

.thinking-summary:hover { color: var(--accent); }
.thinking-summary::-webkit-details-marker { display: none; }

.thinking-spinner {
  width: 13px;
  height: 13px;
  border: 2px solid var(--accent-soft);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: think-spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes think-spin { to { transform: rotate(360deg); } }

.thinking-content {
  display: block;
  box-sizing: border-box;
  padding: 2px 16px 13px;
  border-top: 1px solid var(--border-light);
  margin: 0;
  font-family: inherit;
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 180px !important;
  height: auto;
  overflow-y: auto !important;
  overflow-x: hidden;
  scroll-behavior: smooth;
}
.thinking-content::-webkit-scrollbar { width: 6px; }
.thinking-content::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 3px; }

.message-text {
  font-size: 14.5px;
  line-height: 1.8;
  color: var(--text);
  word-wrap: break-word;
  overflow-wrap: break-word;
  padding: 13px 18px;
}

.bubble-assistant .message-text { padding: 4px 6px; }

.message-text :deep(p) { margin-bottom: 9px; }
.message-text :deep(p:last-child) { margin-bottom: 0; }

.message-text :deep(h1),
.message-text :deep(h2),
.message-text :deep(h3),
.message-text :deep(h4),
.message-text :deep(h5),
.message-text :deep(h6) {
  font-weight: 800;
  margin: 14px 0 8px;
  line-height: 1.3;
  color: var(--text);
}
.message-text :deep(h1) { font-size: 22px; }
.message-text :deep(h2) { font-size: 19px; }
.message-text :deep(h3) { font-size: 16.5px; }
.message-text :deep(h4) { font-size: 15px; }
.message-text :deep(h5),
.message-text :deep(h6) { font-size: 14px; }

.message-text :deep(code) {
  background: rgba(var(--accent-rgb), 0.1);
  padding: 2px 7px;
  border-radius: 6px;
  font-size: 13px;
  font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace;
  color: var(--accent-hover);
}

[data-theme="dark"] .message-text :deep(code) { color: var(--accent); }

.message-text :deep(.code-block) {
  background: rgba(60, 45, 28, 0.05);
  color: var(--text);
  padding: 0;
  border-radius: 12px;
  overflow: hidden;
  margin: 10px 0;
  font-size: 13px;
  border: 1px solid var(--border-light);
}

[data-theme="dark"] .message-text :deep(.code-block) {
  background: rgba(0, 0, 0, 0.3);
}

.message-text :deep(.code-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 14px;
  background: rgba(var(--accent-rgb), 0.06);
  border-bottom: 1px solid var(--border-light);
  font-size: 11.5px;
}

.message-text :deep(.code-lang) {
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
  font-weight: 700;
}

.message-text :deep(.code-copy-btn) {
  background: none;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 11px;
  font-family: inherit;
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: all var(--transition);
}

.message-text :deep(.code-copy-btn:hover) {
  background: var(--accent);
  color: var(--accent-contrast);
  border-color: var(--accent);
}

.message-text :deep(.code-copy-btn.copied) {
  background: var(--accent);
  color: var(--accent-contrast);
  border-color: var(--accent);
}

.message-text :deep(.code-block code) {
  display: block;
  background: none;
  padding: 14px 16px;
  color: inherit;
  border-radius: 0;
  font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace;
  line-height: 1.65;
  white-space: pre;
  overflow-x: auto;
}

/* 表格 */
.message-text :deep(.md-table-wrap) {
  overflow-x: auto;
  margin: 10px 0;
  border-radius: 10px;
  border: 1px solid var(--border-light);
}

.message-text :deep(table) {
  border-collapse: collapse;
  width: 100%;
  font-size: 13px;
}

.message-text :deep(th),
.message-text :deep(td) {
  padding: 8px 14px;
  border-bottom: 1px solid var(--border-light);
  text-align: left;
}

.message-text :deep(th) {
  background: rgba(var(--accent-rgb), 0.05);
  font-weight: 700;
  color: var(--text);
}

.message-text :deep(tr:last-child td) { border-bottom: none; }

.message-text :deep(tbody tr:hover) { background: var(--hover); }

/* 数学公式 */
.message-text :deep(.math-block) {
  margin: 12px 0;
  padding: 10px 14px;
  text-align: center;
  font-family: 'Cambria Math', 'STIX', 'Latin Modern Math', serif;
  font-size: 15px;
  color: var(--text);
  background: rgba(var(--accent-rgb), 0.04);
  border-radius: 8px;
  overflow-x: auto;
}

.message-text :deep(.math-inline) {
  font-family: 'Cambria Math', 'STIX', 'Latin Modern Math', serif;
  padding: 0 2px;
}

.message-text :deep(.math-frac) {
  display: inline-flex;
  flex-direction: column;
  vertical-align: middle;
  margin: 0 4px;
  text-align: center;
}

.message-text :deep(.math-num) {
  border-bottom: 1px solid currentColor;
  padding: 0 4px;
}

.message-text :deep(.math-den) { padding: 0 4px; }

.message-text :deep(.math-sqrt) {
  position: relative;
  padding-left: 14px;
}

.message-text :deep(.math-sqrt::before) {
  content: '√';
  position: absolute;
  left: 0;
  top: 0;
}

.message-text :deep(.math-sqrt-inner) {
  border-top: 1px solid currentColor;
  padding: 0 3px;
}

.message-text :deep(ul),
.message-text :deep(ol) {
  padding-left: 22px;
  margin: 8px 0;
}

.message-text :deep(li) { margin-bottom: 5px; }
.message-text :deep(li)::marker { color: var(--accent); }

.message-text :deep(strong) { font-weight: 700; color: var(--text); }

.message-text :deep(a) {
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px solid rgba(var(--accent-rgb), 0.35);
  transition: border-color var(--transition), color var(--transition);
}

.message-text :deep(a:hover) {
  color: var(--accent-hover);
  border-bottom-color: var(--accent-hover);
}

.message-text :deep(blockquote) {
  border-left: 3px solid rgba(var(--accent-rgb), 0.4);
  padding: 4px 14px;
  margin: 10px 0;
  color: var(--text-secondary);
  background: rgba(var(--accent-rgb), 0.03);
  border-radius: 0 6px 6px 0;
}

.message-text :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-light);
  margin: 14px 0;
}

/* 时间与操作 */
.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  padding: 0 4px;
  min-height: 22px;
  flex-wrap: wrap;
}

.message-time {
  font-size: 11px;
  color: var(--text-muted);
}

.message-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  transform: translateY(2px);
  transition: opacity var(--transition), transform var(--spring-fast);
}

.message-row:hover .message-actions {
  opacity: 1;
  transform: translateY(0);
}

.msg-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  background: none;
  border: none;
  padding: 0;
  border-radius: 6px;
  font-family: inherit;
  color: var(--text-muted);
  cursor: pointer;
  transition: background var(--transition), color var(--transition), transform var(--spring-fast);
}

.msg-action:hover:not(:disabled) {
  background: var(--accent-light);
  color: var(--text);
  transform: translateY(-1px);
}

.msg-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.msg-action.active {
  color: var(--accent);
  background: var(--accent-light);
}

.msg-action.stop-btn:hover {
  background: var(--danger-soft);
  color: var(--danger);
}

.msg-action .spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.action-hint {
  font-size: 11px;
  color: var(--accent);
  font-weight: 600;
  animation: hint-in 0.25s ease both;
}

@keyframes hint-in {
  from { opacity: 0; transform: translateY(2px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 编辑模式 */
.edit-box {
  width: 100%;
  max-width: 560px;
  background: var(--panel);
  border: 1px solid rgba(var(--accent-rgb), 0.35);
  border-radius: 1.15rem;
  padding: 10px;
  box-shadow: 0 4px 18px var(--shadow-sm);
}

.edit-textarea {
  width: 100%;
  border: none;
  background: transparent;
  font-family: inherit;
  font-size: 14px;
  color: var(--text);
  resize: none;
  outline: none;
  line-height: 1.6;
  padding: 6px 8px;
  min-height: 48px;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 6px;
}

.edit-btn {
  padding: 5px 14px;
  border-radius: var(--radius-pill);
  font-size: 12.5px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  border: 1px solid var(--border);
  background: var(--panel);
  color: var(--text-secondary);
  transition: all var(--transition);
}

.edit-btn.cancel:hover {
  background: var(--hover);
  color: var(--text);
}

.edit-btn.primary {
  background: linear-gradient(180deg, var(--accent-hover), var(--accent));
  color: var(--accent-contrast);
  border-color: transparent;
}

.edit-btn.primary:hover { filter: brightness(1.08); }

@media (max-width: 767px) {
  .message-row { padding: 0 4px; }

  .message-wrapper,
  .message-wrapper.user {
    max-width: 88%;
    gap: 8px;
  }

  .message-avatar {
    width: 28px;
    height: 28px;
    font-size: 13px;
    flex-shrink: 0;
  }

  .avatar-pulse { display: none; }

  .thinking-summary { padding: 8px 12px; font-size: 12px; }
  .thinking-content { max-height: 140px !important; }

  .avatar-assistant { border: none; box-shadow: none; }

  .message-role { display: none; }

  .bubble-assistant { border-radius: 4px 16px 16px 16px; }

  .bubble-user {
    border-radius: 16px 4px 16px 16px;
    background: var(--panel);
    box-shadow: none;
  }

  .message-text { font-size: 15px; padding: 10px 14px; line-height: 1.6; }

  .bubble-assistant .message-text { padding: 4px 6px; }

  .message-time { font-size: 10px; }

  .message-actions { opacity: 1; transform: none; }

  .msg-action { width: 28px; height: 28px; }

  .message-text :deep(.code-block code) { padding: 10px 12px; font-size: 12px; }

  .message-text :deep(code) { font-size: 12px; padding: 1px 6px; }
}
</style>
