<template>
  <div class="chat-input-area">
    <div class="input-glow" :class="{ active: isFocused }"></div>
    <div class="chat-input-wrapper">
      <div class="chat-input-box" :class="{ focused: isFocused }">
        <textarea
          ref="inputRef"
          v-model="inputText"
          :disabled="disabled"
          placeholder="输入你的问题，按 Enter 发送（Shift+Enter 换行）..."
          rows="1"
          @input="autoResize"
          @keydown="handleKeydown"
          @focus="isFocused = true"
          @blur="isFocused = false"
        ></textarea>
      </div>
      <button
        class="send-btn"
        :class="{ disabled: disabled || !inputText.trim() }"
        :disabled="disabled || !inputText.trim()"
        @click="handleSend"
        title="发送消息"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="22" y1="2" x2="11" y2="13"></line>
          <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
        </svg>
      </button>
    </div>
    <div class="input-tip">自动化办公助手可能存在错误，请核实重要信息。</div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['send'])

const inputText = ref('')
const inputRef = ref(null)
const isFocused = ref(false)

function autoResize() {
  nextTick(() => {
    const el = inputRef.value
    if (el) {
      el.style.height = '48px'
      el.style.height = Math.min(el.scrollHeight, 200) + 'px'
    }
  })
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function handleSend() {
  const text = inputText.value.trim()
  if (!text || props.disabled) return

  emit('send', text)
  inputText.value = ''
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.style.height = '48px'
    }
  })
}
</script>

<style scoped>
.chat-input-area {
  padding: 16px 24px 20px;
  background: rgba(15, 15, 40, 0.7);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--border);
  flex-shrink: 0;
  position: relative;
}

.input-glow {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  transition: width 0.4s ease;
}

.input-glow.active {
  width: 60%;
}

.chat-input-wrapper {
  max-width: 820px;
  margin: 0 auto;
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.chat-input-box {
  flex: 1;
  position: relative;
  background: var(--bg-input);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  transition: var(--transition);
  display: flex;
  align-items: flex-end;
}

.chat-input-box.focused {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.1), 0 0 20px rgba(108, 92, 231, 0.1);
}

.chat-input-box textarea {
  width: 100%;
  border: none;
  background: transparent;
  padding: 14px 18px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  outline: none;
  color: var(--text-primary);
  line-height: 1.5;
  min-height: 48px;
  max-height: 200px;
}

.chat-input-box textarea::placeholder {
  color: #5c6280;
}

.chat-input-box textarea:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), #a855f7);
  color: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition);
  flex-shrink: 0;
  box-shadow: 0 4px 15px rgba(108, 92, 231, 0.3);
}

.send-btn:hover:not(.disabled) {
  transform: scale(1.08);
  box-shadow: 0 6px 24px rgba(108, 92, 231, 0.5);
}

.send-btn.disabled {
  background: rgba(255, 255, 255, 0.06);
  box-shadow: none;
  cursor: not-allowed;
  opacity: 0.4;
}

.send-btn svg {
  width: 20px;
  height: 20px;
}

.input-tip {
  text-align: center;
  font-size: 11px;
  color: #5c6280;
  margin-top: 8px;
  max-width: 820px;
  margin-left: auto;
  margin-right: auto;
}
</style>
