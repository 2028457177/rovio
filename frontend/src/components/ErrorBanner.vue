<template>
  <div class="error-banner" :class="{ show: message }">
    <div class="error-content">
      <span class="error-icon">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
      </span>
      <div class="error-text-wrap">
        <span class="error-text">{{ message }}</span>
        <span v-if="hint" class="error-hint">{{ hint }}</span>
      </div>
    </div>
    <div class="error-actions">
      <button v-if="canRetry" class="error-retry-btn" :disabled="retrying" @click="onRetry">
        <svg v-if="!retrying" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 4 23 10 17 10"></polyline>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
        </svg>
        <span v-else class="mini-spinner"></span>
        <span>{{ retrying ? '重试中…' : '重试' }}</span>
      </button>
      <button class="error-close" @click="$emit('dismiss')" title="关闭">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  message: { type: String, default: '' },
  hint: { type: String, default: '' },
  canRetry: { type: Boolean, default: false }
})

const emit = defineEmits(['dismiss', 'retry'])

const retrying = ref(false)

async function onRetry() {
  if (retrying.value) return
  retrying.value = true
  try {
    await emit('retry')
  } finally {
    // 由父组件控制 dismiss；这里只做短延迟以让用户看到反馈
    setTimeout(() => { retrying.value = false }, 600)
  }
}
</script>

<style scoped>
.error-banner {
  background: var(--danger-soft);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--danger-border);
  padding: 10px 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  animation: banner-in 0.4s var(--ease-out-expo) both;
  gap: 12px;
}

@keyframes banner-in {
  from { opacity: 0; transform: translateY(-100%); }
  to { opacity: 1; transform: translateY(0); }
}

.error-content {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 13px;
  color: var(--danger);
  min-width: 0;
  flex: 1;
}

.error-icon {
  display: flex;
  align-items: center;
  animation: icon-pop 0.5s var(--ease-out-expo) 0.15s both;
  flex-shrink: 0;
}

@keyframes icon-pop {
  from { opacity: 0; transform: scale(0.4); }
  to { opacity: 1; transform: scale(1); }
}

.error-text-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.error-text {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.error-hint {
  font-size: 11.5px;
  font-weight: 400;
  opacity: 0.75;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.error-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.error-retry-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--danger);
  color: #fff;
  border: 1px solid var(--danger);
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: transform var(--spring-fast), filter var(--transition), opacity var(--transition);
}

.error-retry-btn:hover:not(:disabled) {
  filter: brightness(1.08);
  transform: translateY(-1px);
}

.error-retry-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.mini-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.error-close {
  background: none;
  border: none;
  color: var(--danger);
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  transition: transform var(--spring-fast), background var(--transition), color var(--transition);
  display: flex;
  align-items: center;
}

.error-close:hover {
  background: var(--danger-soft);
  transform: rotate(90deg);
}
</style>
