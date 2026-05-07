<template>
  <div class="message-wrapper" :class="message.role">
    <div class="message-avatar" :class="`avatar-${message.role}`">
      {{ message.role === 'user' ? '👤' : '🤖' }}
    </div>
    <div class="message-body">
      <div class="message-role">{{ message.role === 'user' ? '你' : '办公助手' }}</div>
      <div class="message-text" v-html="renderMarkdown(message.content)"></div>
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
  background: linear-gradient(135deg, #6c5ce7, #a855f7);
  color: #fff;
  box-shadow: 0 4px 15px rgba(108, 92, 231, 0.3);
}

.avatar-assistant {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #a78bfa;
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
  color: var(--text-primary);
  word-wrap: break-word;
  background: var(--assistant-bubble);
  padding: 14px 18px;
  border-radius: 0 14px 14px 14px;
  border: 1px solid var(--border);
}

.user .message-text {
  background: linear-gradient(135deg, rgba(108, 92, 231, 0.15), rgba(168, 85, 247, 0.1));
  border: 1px solid rgba(108, 92, 231, 0.2);
  border-radius: 14px 0 14px 14px;
}

.message-text :deep(p) {
  margin-bottom: 8px;
}

.message-text :deep(p:last-child) {
  margin-bottom: 0;
}

.message-text :deep(code) {
  background: rgba(108, 92, 231, 0.15);
  padding: 2px 8px;
  border-radius: 5px;
  font-size: 13px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  color: #c4b5fd;
}

.message-text :deep(pre) {
  background: #0d0d24;
  color: #e8e8f0;
  padding: 16px 20px;
  border-radius: var(--radius-sm);
  overflow-x: auto;
  margin: 10px 0;
  font-size: 13px;
  border: 1px solid var(--border);
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
  color: #5c6280;
  margin-top: 6px;
  padding-left: 4px;
}
</style>
