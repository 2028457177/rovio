<template>
  <div class="message-wrapper" :class="message.role">
    <div class="message-avatar" :class="`avatar-${message.role}`">
      {{ message.role === 'user' ? '👤' : '🤖' }}
    </div>
    <div class="message-body">
      <div class="message-role">{{ message.role === 'user' ? '你' : '办公助手' }}</div>
      <div class="message-bubble" :class="`bubble-${message.role}`">
        <div class="message-text" v-html="renderMarkdown(message.content)"></div>
      </div>
      <div class="message-time">{{ message.time }}</div>
    </div>
  </div>
</template>

<script setup>
import { renderMarkdown } from '@/utils/markdown.js'

defineProps({
  message: {
    type: Object,
    required: true
  }
})
</script>

<style scoped>
.message-wrapper {
  display: flex;
  gap: 14px;
  max-width: 820px;
  width: 100%;
  margin: 0 auto;
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
}

.avatar-user {
  background: linear-gradient(135deg, #7c6ff7, #a78bfa);
  color: #fff;
  box-shadow: 0 4px 16px rgba(124, 111, 247, 0.35);
}

.avatar-assistant {
  background: var(--glass-bg);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid var(--glass-border-strong);
  color: #a78bfa;
}

.message-body {
  flex: 1;
  min-width: 0;
}

.message-role {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--text-secondary);
}

.message-bubble {
  border-radius: 0 18px 18px 18px;
  overflow: hidden;
}

.bubble-assistant {
  background: var(--glass-bg);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--glass-border);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.bubble-user {
  background: linear-gradient(135deg, rgba(124, 111, 247, 0.2), rgba(167, 139, 250, 0.15));
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(124, 111, 247, 0.25);
  border-radius: 18px 0 18px 18px;
  box-shadow: 0 4px 20px rgba(124, 111, 247, 0.12);
}

.message-text {
  font-size: 14px;
  line-height: 1.75;
  color: var(--text-primary);
  word-wrap: break-word;
  padding: 14px 18px;
}

.message-text :deep(p) {
  margin-bottom: 8px;
}

.message-text :deep(p:last-child) {
  margin-bottom: 0;
}

.message-text :deep(code) {
  background: rgba(124, 111, 247, 0.15);
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 13px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  color: #c4b5fd;
}

.message-text :deep(pre) {
  background: rgba(0, 0, 0, 0.25);
  color: #e8eaf6;
  padding: 16px 20px;
  border-radius: 12px;
  overflow-x: auto;
  margin: 10px 0;
  font-size: 13px;
  border: 1px solid var(--glass-border);
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
  color: #c4b5fd;
}

.message-time {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 6px;
  padding-left: 4px;
}
</style>
