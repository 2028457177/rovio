<template>
  <div class="message-row" :class="message.role">
    <div class="message-wrapper" :class="message.role">
      <div class="message-avatar" :class="`avatar-${message.role}`">
        <img v-if="message.role === 'assistant'" src="/agent-avatar.jpg" alt="助手" class="avatar-img" />
        <span v-else>👤</span>
      </div>
      <div class="message-body">
        <div class="message-role">{{ message.role === 'user' ? '你' : '办公助手' }}</div>
        <div class="message-bubble" :class="`bubble-${message.role}`">
          <div class="message-text" v-html="renderMarkdown(message.content)"></div>
        </div>
        <div class="message-time">{{ message.time }}</div>
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
  }
})
</script>

<style scoped>
.message-row {
  display: flex;
  width: 100%;
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
}

.avatar-user {
  background: linear-gradient(180deg, var(--accent), #1f2329);
  color: #fff;
  box-shadow: 0 4px 14px rgba(8, 10, 14, 0.18);
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
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.92), rgba(240, 243, 247, 0.8)),
    var(--glass);
  border: 1px solid var(--border);
  box-shadow: 0 8px 24px rgba(8, 10, 14, 0.08);
  width: fit-content;
}

.bubble-user {
  border-radius: 1.2rem 0 1.2rem 1.2rem;
  background:
    linear-gradient(145deg, rgba(99, 102, 241, 0.12), rgba(139, 92, 246, 0.08));
  border: 1px solid rgba(99, 102, 241, 0.2);
  box-shadow: 0 8px 28px var(--shadow);
  width: fit-content;
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
</style>
