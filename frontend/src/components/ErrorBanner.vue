<template>
  <div class="error-banner" :class="{ show: message }">
    <div class="error-content">
      <span class="error-icon">⚠️</span>
      <span class="error-text">{{ message }}</span>
    </div>
    <button class="error-close" @click="$emit('dismiss')">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
    </button>
  </div>
</template>

<script setup>
defineProps({
  message: {
    type: String,
    default: ''
  }
})

defineEmits(['dismiss'])
</script>

<style scoped>
.error-banner {
  background: rgba(239, 68, 68, 0.06);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(239, 68, 68, 0.15);
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.error-content {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #dc2626;
}

.error-icon {
  font-size: 15px;
}

.error-text {
  font-weight: 500;
}

.error-close {
  background: none;
  border: none;
  color: #dc2626;
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  transition: transform var(--spring-fast), background var(--transition), color var(--transition);
  display: flex;
  align-items: center;
}

.error-close:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #b91c1c;
  transform: scale(1.15);
}
</style>
