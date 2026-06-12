<template>
  <div class="chat-input-area" :class="{ 'center-mode': centerMode }">
    <div class="input-glow" :class="{ active: isFocused }"></div>
    <div class="chat-input-wrapper">
      <div class="chat-input-box glass" :class="{ focused: isFocused, 'has-file': uploadedFileName }" @mousemove="onSpotlightMove">
        <!-- 已上传文件提示 -->
        <div v-if="uploadedFileName" class="uploaded-file-tag">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
          <span>{{ uploadedFileName }}</span>
          <button class="file-remove-btn" @click="removeUploadedFile" title="移除文件">&times;</button>
        </div>
        <!-- 文件上传按钮 -->
        <input
          ref="fileInputRef"
          type="file"
          accept=".docx,.doc"
          class="file-input-hidden"
          @change="handleFileSelected"
        />
        <button
          class="attach-btn"
          :class="{ uploading: isUploading }"
          :disabled="disabled || isUploading"
          @click="triggerFileSelect"
          title="上传Word文件"
        >
          <svg v-if="!isUploading" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
          </svg>
          <span v-else class="mini-spinner"></span>
        </button>
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
          :class="{ disabled: disabled || (!inputText.trim() && !uploadedFilePath) }"
          :disabled="disabled || (!inputText.trim() && !uploadedFilePath)"
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
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onUnmounted } from 'vue'
import { uploadWordFile } from '@/api/chat.js'

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
const fileInputRef = ref(null)
const isFocused = ref(false)

watch(isFocused, (focused) => {
  document.body.classList.toggle('input-focused', focused)
})

onUnmounted(() => {
  document.body.classList.remove('input-focused')
})

const isUploading = ref(false)
const uploadedFileName = ref('')
const uploadedFilePath = ref('')

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

function onSpotlightMove(e) {
  const box = e.currentTarget
  const rect = box.getBoundingClientRect()
  const x = ((e.clientX - rect.left) / rect.width) * 100
  const y = ((e.clientY - rect.top) / rect.height) * 100
  box.style.setProperty('--sx', `${x}%`)
  box.style.setProperty('--sy', `${y}%`)
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function triggerFileSelect() {
  fileInputRef.value?.click()
}

async function handleFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return

  isUploading.value = true
  try {
    const result = await uploadWordFile(file)
    uploadedFileName.value = result.original_name
    uploadedFilePath.value = result.server_path
  } catch (err) {
    alert('文件上传失败：' + err.message)
  } finally {
    isUploading.value = false
    // 重置 input 以便可以重复上传同一文件
    if (fileInputRef.value) {
      fileInputRef.value.value = ''
    }
  }
}

function removeUploadedFile() {
  uploadedFileName.value = ''
  uploadedFilePath.value = ''
}

function handleSend() {
  const text = inputText.value.trim()
  if ((!text && !uploadedFilePath.value) || props.disabled) return

  emit('send', text, uploadedFilePath.value)
  inputText.value = ''
  uploadedFileName.value = ''
  uploadedFilePath.value = ''
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
  flex-direction: column;
  border: 1px solid var(--border);
  background: var(--panel);
  box-shadow: 0 4px 18px var(--shadow-sm);
  overflow: hidden;
}

.chat-input-box::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0;
  background: radial-gradient(
    450px circle at var(--sx, 50%) var(--sy, 50%),
    rgba(var(--accent-rgb), 0.10),
    transparent 40%
  );
  transition: opacity 0.3s ease;
  z-index: -1;
}

.chat-input-box.focused::before {
  opacity: 1;
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
  color: var(--bg);
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

.send-btn:active:not(.disabled) {
  transform: scale(0.95);
}

.send-btn.disabled {
  background: var(--panel);
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

/* 文件上传相关样式 */
.file-input-hidden {
  display: none;
}

.attach-btn {
  position: absolute;
  left: 8px;
  bottom: 8px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  color: var(--text-muted);
  background: transparent;
  border: 1px solid var(--border);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
  z-index: 2;
}

.attach-btn:hover:not(:disabled) {
  color: var(--accent);
  border-color: var(--accent);
  background: rgba(var(--accent-rgb, 59, 130, 246), 0.08);
}

.attach-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.attach-btn.uploading {
  border-color: var(--accent);
  color: var(--accent);
}

.mini-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 调整 textarea 左侧 padding 以留出位置给附件按钮 */
.chat-input-box textarea {
  padding-left: 50px;
}

.uploaded-file-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  margin: 2px 6px 0 6px;
  background: rgba(var(--accent-rgb, 59, 130, 246), 0.06);
  border: 1px solid rgba(var(--accent-rgb, 59, 130, 246), 0.15);
  border-radius: 6px;
  font-size: 11px;
  color: var(--text);
  max-width: fit-content;
}

.uploaded-file-tag svg {
  flex-shrink: 0;
  color: var(--accent);
}

.uploaded-file-tag span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 0 2px;
  color: var(--text-muted);
  flex-shrink: 0;
  transition: color 0.2s;
}

.file-remove-btn:hover {
  color: #e74c3c;
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

@media (max-width: 767px) {
  .chat-input-area {
    padding: 8px 12px;
    padding-bottom: calc(8px + var(--safe-bottom));
    background: var(--panel);
    border-top: 0.5px solid var(--border-light);
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }

  .input-glow {
    display: none;
  }

  .chat-input-wrapper {
    max-width: 100%;
  }

  .chat-input-box {
    border-radius: 24px;
    border: 1px solid var(--border);
    background: var(--glass-light);
    box-shadow: none;
    align-items: center;
  }

  .chat-input-box.focused {
    border-color: var(--accent);
    background: var(--panel);
    box-shadow: 0 0 0 2px var(--accent-light);
  }

  .chat-input-box textarea {
    padding: 10px 44px 10px 16px;
    font-size: 15px;
    min-height: 40px;
    line-height: 1.4;
  }

  .chat-input-box textarea::placeholder {
    color: #999;
  }

  .send-btn {
    width: 30px;
    height: 30px;
    right: 5px;
    bottom: 5px;
    background: #07c160;
    box-shadow: none;
  }

  .send-btn.disabled {
    background: #ccc;
    border: none;
    opacity: 0.5;
  }

  .send-btn svg {
    width: 14px;
    height: 14px;
  }

  .chat-input-area.center-mode {
    padding: 0 12px;
    background: transparent;
    border: none;
  }

  .chat-input-area.center-mode .chat-input-box {
    border-radius: 24px;
    background: var(--panel);
    border: 1px solid var(--border);
    box-shadow: 0 1px 4px var(--shadow-sm);
  }

  .chat-input-area.center-mode .chat-input-box textarea {
    min-height: 44px;
    padding: 10px 44px 10px 16px;
    font-size: 15px;
  }
}
</style>
