<template>
  <div class="error-banner" :class="{ show: message }">
    <div class="error-content">
      <span class="error-icon">⚠️</span>
      <span class="error-text">{{ message }}</span>
    </div>
    <button class="error-close" @click="$emit('dismiss')">✕</button>
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
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 0;
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  backdrop-filter: blur(10px);
}

.error-content {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #fca5a5;
}

.error-icon {
  font-size: 15px;
}

.error-close {
  background: none;
  border: none;
  color: #fca5a5;
  cursor: pointer;
  font-size: 16px;
  padding: 4px 8px;
  border-radius: 6px;
  transition: var(--transition);
  font-family: inherit;
}

.error-close:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #fff;
}
</style>
