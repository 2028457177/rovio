<template>
  <div
    class="message-row"
    :class="[message.role, { streaming: streaming }]"
    :style="{ '--msg-index': index }"
  >
    <div class="message-wrapper" :class="message.role">
      <div class="message-avatar" :class="`avatar-${message.role}`">
        <span v-if="streaming && message.role === 'assistant'" class="avatar-pulse"></span>
        <img v-if="message.role === 'assistant'" src="/agent-avatar.jpg" alt="助手" class="avatar-img" />
        <img v-else src="/user-avatar.jpg" alt="头像" class="avatar-img" />
      </div>
      <div class="message-body">
        <div class="message-role">{{ message.role === 'user' ? '你' : 'Rovio' }}</div>
        <template v-if="streaming && !message.content && thinkingContent">
          <div class="thinking-panel">
            <details :open="true" class="glass">
              <summary class="thinking-summary">
                <span class="thinking-spinner"></span>
                Thinking...
              </summary>
              <pre class="thinking-content">{{ thinkingContent }}</pre>
            </details>
          </div>
        </template>
        <template v-else>
          <div class="message-bubble" :class="`bubble-${message.role}`">
            <div v-if="streaming && !message.content" class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
            <div v-else class="message-text" v-html="renderMarkdown(message.content)"></div>
          </div>
          <div class="message-time">{{ message.time }}</div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { renderMarkdown } from '@/utils/markdown.js'

defineProps({
  message: {
    type: Object,
    required: true
  },
  index: {
    type: Number,
    default: 0
  },
  streaming: {
    type: Boolean,
    default: false
  },
  thinkingContent: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.message-row {
  display: flex;
  width: 100%;
  animation: msg-pop-in 0.42s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  animation-delay: calc(var(--msg-index, 0) * 60ms);
}

@keyframes msg-pop-in {
  from {
    opacity: 0;
    transform: translateY(18px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.message-row.user {
  justify-content: flex-end;
}

.message-wrapper {
  display: flex;
  gap: 14px;
  max-width: 520px;
  width: fit-content;
}

.message-wrapper.user {
  flex-direction: row-reverse;
  width: fit-content;
  max-width: 520px;
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
}

.avatar-assistant {
  background: var(--glass);
  border: 1px solid var(--border-light);
  overflow: hidden;
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
  opacity: 0.15;
  animation: avatar-ring 2s ease-out infinite;
  pointer-events: none;
}

@keyframes avatar-ring {
  0% { transform: scale(1); opacity: 0.4; }
  100% { transform: scale(1.4); opacity: 0; }
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
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--text-muted);
}

.message-bubble {
  overflow: hidden;
  width: 100%;
}

.bubble-assistant {
  border-radius: 0 1.2rem 1.2rem 1.2rem;
  background: var(--bg);
  border: 1px solid transparent;
  box-shadow: none;
  width: fit-content;
}

.bubble-user {
  border-radius: 1.2rem 0 1.2rem 1.2rem;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  width: fit-content;
}

[data-theme="dark"] .bubble-user {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.10);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
}

/* 流式状态：驻点消息立即出现，无弹出动画 */
.message-row.streaming {
  animation: none;
}

/* 流式时气泡带 shimmer 高光 */
.bubble-assistant.streaming {
  position: relative;
  overflow: hidden;
}

.bubble-assistant.streaming::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(150, 155, 165, 0.18) 50%,
    transparent 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.6s linear infinite;
  opacity: 0.5;
  pointer-events: none;
}

[data-theme="dark"] .bubble-assistant.streaming::after {
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.08) 50%,
    transparent 100%
  );
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.typing-indicator {
  display: flex;
  gap: 5px;
  padding: 8px 4px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: var(--accent);
  border-radius: 50%;
  animation: typing-bounce 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* 思考栏：显示在 streaming 气泡上方 */
.thinking-panel {
  margin-bottom: 8px;
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
  margin: 0;
  font-family: inherit;
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-text {
  font-size: 14px;
  line-height: 1.75;
  color: var(--text);
  word-wrap: break-word;
  overflow-wrap: break-word;
  padding: 14px 18px;
}

.message-text :deep(p) {
  margin-bottom: 8px;
}

.message-text :deep(p:last-child) {
  margin-bottom: 0;
}

.message-text :deep(code) {
  background: var(--accent-light);
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 13px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  color: var(--text-secondary);
}

.message-text :deep(pre) {
  background: rgba(8, 9, 11, 0.04);
  color: var(--text);
  padding: 16px 20px;
  border-radius: 12px;
  overflow-x: auto;
  margin: 10px 0;
  font-size: 13px;
  border: 1px solid var(--border-light);
}

.message-text :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}

.message-text :deep(ul),
.message-text :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.message-text :deep(li) {
  margin-bottom: 4px;
}

.message-text :deep(strong) {
  font-weight: 700;
  color: var(--text);
}

.message-time {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 6px;
  padding: 0 4px;
}

@media (max-width: 767px) {
  .message-row {
    padding: 0 4px;
  }

  .message-wrapper {
    max-width: 88%;
    gap: 8px;
  }

  .message-wrapper.user {
    max-width: 88%;
  }

  .message-avatar {
    width: 28px;
    height: 28px;
    font-size: 13px;
    flex-shrink: 0;
  }

  .avatar-pulse {
    display: none;
  }

  .thinking-summary {
    padding: 8px 12px;
    font-size: 12px;
  }

  .avatar-user {
    background: #07c160;
    box-shadow: none;
  }

  .avatar-assistant {
    border: none;
    background: transparent;
  }

  .message-role {
    display: none;
  }

  .bubble-assistant {
    border-radius: 4px 18px 18px 18px;
    background: var(--bg);
    border: none;
    box-shadow: none;
  }

  .bubble-user {
    border-radius: 18px 4px 18px 18px;
    background: #ffffff;
    border: 1px solid rgba(0, 0, 0, 0.06);
    box-shadow: none;
  }

  [data-theme="dark"] .bubble-user {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.10);
  }

  .message-wrapper.user .message-text {
     color: #1f2329;
   }

   [data-theme="dark"] .message-wrapper.user .message-text {
     color: var(--text);
   }

   .message-wrapper.user .message-text :deep(pre) {
     background: rgba(0,0,0,0.06);
     border: none;
     color: #1f2329;
   }

   [data-theme="dark"] .message-wrapper.user .message-text :deep(pre) {
     background: rgba(255,255,255,0.12);
     color: var(--text);
   }

   .message-wrapper.user .message-text :deep(code) {
     background: rgba(0,0,0,0.06);
     color: #1f2329;
   }

   [data-theme="dark"] .message-wrapper.user .message-text :deep(code) {
     background: rgba(255,255,255,0.12);
     color: var(--text);
   }

   .message-text {
    font-size: 15px;
    padding: 10px 14px;
    line-height: 1.55;
  }

  .message-time {
    font-size: 10px;
    margin-top: 4px;
  }

  .message-text :deep(pre) {
    padding: 10px 12px;
    font-size: 12px;
    border-radius: 10px;
    margin: 4px 0;
  }

  .message-text :deep(code) {
    font-size: 12px;
    padding: 1px 6px;
  }
}
</style>
