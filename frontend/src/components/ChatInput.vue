<template>
  <div class="chat-input-area" :class="{ 'center-mode': centerMode }">
    <div class="input-glow" :class="{ active: isFocused }"></div>
    <div class="chat-input-wrapper">
      <div class="chat-input-box glass" :class="{ focused: isFocused }">
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
    </div>
    <div class="input-tip" v-if="!centerMode">自动化办公助手可能存在错误，请核实重要信息。</div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false
  },
  centerMode: {
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
      const baseHeight = props.centerMode ? 80 : 48
      el.style.height = baseHeight + 'px'
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
      const baseHeight = props.centerMode ? 80 : 48
      inputRef.value.style.height = baseHeight + 'px'
    }
  })
}
</script>

<style scoped>
.chat-input-area {
  padding: 16px 24px 20px;
  background: var(--glass);
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  border-top: 1px solid var(--border-light);
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
  border-radius: var(--radius);
  transition: var(--transition);
  display: flex;
  align-items: flex-end;
  border: 1px solid var(--border);
  background: #fff;
  box-shadow: 0 4px 18px var(--shadow-sm);
}

.chat-input-box.focused {
  border-color: rgba(8, 9, 11, 0.35);
  box-shadow: 0 4px 24px var(--shadow);
}

.chat-input-box textarea {
  width: 100%;
  border: none;
  background: transparent;
  padding: 14px 52px 14px 18px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  outline: none;
  color: var(--text);
  line-height: 1.5;
  min-height: 48px;
  max-height: 200px;
}

.chat-input-box textarea::placeholder {
  color: var(--text-muted);
}

.chat-input-box textarea:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-btn {
  position: absolute;
  right: 8px;
  bottom: 8px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  color: #fff;
  background: linear-gradient(180deg, #1f2329, var(--accent));
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  flex-shrink: 0;
  box-shadow: 0 3px 12px rgba(8, 10, 14, 0.2);
  z-index: 2;
}

.send-btn:hover:not(.disabled) {
  transform: translateY(-2px) scale(1.08);
  box-shadow: 0 8px 28px rgba(8, 10, 14, 0.32);
}

.send-btn.disabled {
  background: #fff;
  border: 1px solid var(--border);
  box-shadow: 0 2px 8px var(--shadow-sm);
  cursor: not-allowed;
  opacity: 0.4;
  color: var(--text-muted);
}

.send-btn svg {
  width: 18px;
  height: 18px;
}

.input-tip {
  text-align: center;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 8px;
  max-width: 820px;
  margin-left: auto;
  margin-right: auto;
}

.chat-input-area.center-mode {
  padding: 0;
  background: transparent;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border-top: none;
}

.chat-input-area.center-mode .chat-input-box {
  box-shadow: 0 6px 28px var(--shadow);
}

.chat-input-area.center-mode .chat-input-box textarea {
  min-height: 80px;
}

.chat-input-area.center-mode .chat-input-box.focused {
  box-shadow: 0 8px 38px var(--shadow);
}
</style>
