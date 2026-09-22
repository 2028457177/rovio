<template>
  <div class="options-panel" :class="{ answered: !!currentSelected }">
    <!-- 标题条 -->
    <div class="options-header">
      <span class="options-icon">›</span>
      <span class="options-title">选择一个方向继续</span>
      <span v-if="currentSelected" class="options-done">已选择</span>
      <span v-else-if="disabled" class="options-hint">已失效</span>
    </div>

    <!-- 选项按钮列表 -->
    <div class="options-list">
      <button
        v-for="opt in normalizedOptions"
        :key="opt.label"
        type="button"
        class="options-item"
        :class="{ selected: currentSelected === opt.value }"
        :disabled="disabled"
        @click="onPick(opt)"
      >
        <span class="options-item-label">{{ opt.label }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useChat } from '@/composables/useChat.js'

const props = defineProps({
  options: { type: Array, required: true },      // [{label, value}]
  messageId: { type: [Number, String], required: true },
  streaming: { type: Boolean, default: false },
  selected: { type: String, default: '' }        // 已选中的 option.value（持久化恢复）
})

const emit = defineEmits(['select'])

const { messages, sendMessage } = useChat()

const normalizedOptions = computed(() =>
  (Array.isArray(props.options) ? props.options : [])
    .filter(o => o && o.label && o.value)
    .slice(0, 6)
)

const localSelected = ref(props.selected || '')
watch(() => props.selected, (v) => {
  if (v) localSelected.value = v
})
const currentSelected = computed(() => localSelected.value || props.selected || '')

// 仅会话最后一条消息的面板可点击；历史消息上的面板只展示
const isLastMessage = computed(() => {
  const list = messages.value
  if (!list.length) return false
  return list[list.length - 1].id === props.messageId
})

const disabled = computed(() => props.streaming || !!currentSelected.value || !isLastMessage.value)

function onPick(opt) {
  if (disabled.value) return
  localSelected.value = opt.value
  emit('select', opt)
  // 把选项的完整表述作为用户消息发送，开启新一轮对话
  sendMessage(opt.value)
}
</script>

<style scoped>
.options-panel {
  margin: 10px 0 4px;
  max-width: 480px;
  border: 1px solid rgba(var(--accent-rgb), 0.35);
  border-radius: 14px;
  background: rgba(var(--accent-rgb), 0.045);
  overflow: hidden;
  animation: options-in 0.35s var(--ease-out-expo) both;
}

@keyframes options-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.options-panel.answered {
  border-color: var(--border-light);
  background: var(--panel);
  opacity: 0.85;
}

.options-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px 0;
}

.options-icon {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--accent);
  color: var(--accent-contrast);
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.options-title {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--accent);
  text-transform: uppercase;
}

.options-hint {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
}

.options-done {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.options-done::before {
  content: '✓';
  color: var(--accent);
  font-weight: 800;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 10px 12px 12px;
}

.options-item {
  display: flex;
  align-items: flex-start;
  width: 100%;
  text-align: left;
  padding: 9px 12px;
  border: 1px solid var(--border-light);
  border-radius: 10px;
  background: var(--panel);
  cursor: pointer;
  font-family: inherit;
  transition: border-color var(--transition), background var(--transition), transform var(--spring-fast);
}

.options-item:hover:not(:disabled) {
  border-color: rgba(var(--accent-rgb), 0.55);
  background: var(--accent-light, rgba(var(--accent-rgb), 0.07));
  transform: translateY(-1px);
}

.options-item:disabled {
  cursor: default;
}

.options-item.selected {
  border-color: var(--accent);
  background: rgba(var(--accent-rgb), 0.09);
}

.options-item-label {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.5;
}

@media (max-width: 767px) {
  .options-panel { max-width: 100%; }
}
</style>
