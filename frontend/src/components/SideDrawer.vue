<template>
  <Teleport to="body">
    <Transition name="drawer-fade">
      <div v-if="modelValue" class="drawer-overlay" @click.self="close">
        <Transition name="drawer-slide" appear>
          <aside
            v-if="modelValue"
            class="drawer-panel glass-strong"
            :style="{ '--drawer-width': width }"
            role="dialog"
            aria-modal="true"
            :aria-label="title"
          >
            <!-- 头部 -->
            <header class="drawer-header">
              <div class="drawer-header-left">
                <h2 class="drawer-title serif">{{ title }}</h2>
                <p v-if="subtitle" class="drawer-subtitle">{{ subtitle }}</p>
              </div>
              <button class="drawer-close" @click="close" title="关闭" aria-label="关闭">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </header>

            <!-- 内容区 -->
            <div class="drawer-body">
              <slot />
            </div>
          </aside>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  width: { type: String, default: '880px' }
})

const emit = defineEmits(['update:modelValue'])

function close() {
  emit('update:modelValue', false)
}

function onKeydown(e) {
  if (e.key === 'Escape' && props.modelValue) {
    close()
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (typeof document !== 'undefined') {
      document.body.style.overflow = open ? 'hidden' : ''
    }
  }
)

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  if (typeof document !== 'undefined') {
    document.body.style.overflow = ''
  }
})
</script>

<style scoped>
.drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 9000;
  background: rgba(0, 0, 0, 0.42);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: var(--drawer-width, 880px);
  max-width: 94vw;
  height: 100vh;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--border);
  box-shadow: -16px 0 48px rgba(0, 0, 0, 0.18);
  background: var(--glass-strong);
}

/* —— 头部 —— */
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 28px;
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
  z-index: 2;
}

.drawer-header-left {
  min-width: 0;
}

.drawer-title {
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: var(--text);
}

.drawer-subtitle {
  font-size: 12.5px;
  color: var(--text-muted);
  margin-top: 3px;
}

.drawer-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--panel);
  color: var(--text-secondary);
  cursor: pointer;
  flex-shrink: 0;
  transition: all var(--transition);
}

.drawer-close:hover {
  background: var(--danger-soft);
  color: var(--danger);
  border-color: var(--danger-border);
  transform: rotate(90deg);
}

/* —— 内容区 —— */
.drawer-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
}

/* —— 过渡动画 —— */
.drawer-fade-enter-active,
.drawer-fade-leave-active {
  transition: opacity 0.3s ease;
}

.drawer-fade-enter-from,
.drawer-fade-leave-to {
  opacity: 0;
}

.drawer-slide-enter-active,
.drawer-slide-leave-active {
  transition: transform 0.38s var(--ease-out-expo, cubic-bezier(0.16, 1, 0.3, 1));
}

.drawer-slide-enter-from,
.drawer-slide-leave-to {
  transform: translateX(100%);
}

/* —— 移动端 —— */
@media (max-width: 767px) {
  .drawer-panel {
    width: 100vw;
    max-width: 100vw;
  }

  .drawer-header {
    padding: 14px 18px;
  }
}
</style>
