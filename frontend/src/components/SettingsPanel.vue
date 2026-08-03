<template>
  <div class="settings-panel">
    <main class="settings-main">
      <!-- 课表设置 -->
      <section class="settings-card glass-strong">
        <div class="card-header">
          <h2 class="card-title">课表设置</h2>
          <p class="card-subtitle">上传你的课表 Excel 并设置开学日期，AI 助手才能帮你查询课程安排</p>
        </div>

        <!-- 已上传状态展示 -->
        <div v-if="scheduleState.uploaded" class="schedule-info">
          <div class="info-row">
            <span class="info-label">当前课表：</span>
            <a :href="scheduleState.schedule_url" target="_blank" class="info-link">查看已上传文件</a>
          </div>
          <div class="info-row">
            <span class="info-label">上传时间：</span>
            <span>{{ scheduleState.uploaded_at || '未知' }}</span>
          </div>
        </div>

        <!-- 选择文件 -->
        <div class="form-group">
          <label class="form-label">课表 Excel 文件</label>
          <label class="avatar-upload-btn">
            <input type="file" accept=".xlsx,.xls" @change="onScheduleFileChange" hidden />
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <span>{{ scheduleForm.fileName || '选择 .xlsx 文件' }}</span>
          </label>
          <p class="avatar-hint">支持 .xlsx / .xls 格式，最大 2MB；列名需为 星期一~星期天</p>
        </div>

        <!-- 开学日期 -->
        <div class="form-group">
          <label class="form-label">开学日期</label>
          <input v-model="scheduleForm.startDate" type="date" class="form-input" />
          <p class="avatar-hint">学期第一天的日期，用于计算周次；可单独保存，未上传课表时也能先设置</p>
        </div>

        <div class="card-actions">
          <button class="action-btn primary" :disabled="scheduleLoading" @click="saveSchedule">
            <span v-if="scheduleLoading" class="btn-spinner"></span>
            <span v-else>{{ scheduleState.uploaded ? '更新课表' : '上传课表' }}</span>
          </button>
          <button
            class="action-btn secondary"
            :disabled="scheduleLoading"
            @click="saveStartDateOnly"
          >
            保存开学日期
          </button>
          <button
            v-if="scheduleState.uploaded"
            class="action-btn danger-soft"
            :disabled="scheduleDeleting"
            @click="removeSchedule"
          >
            <span v-if="scheduleDeleting" class="btn-spinner"></span>
            <span v-else>删除课表</span>
          </button>
        </div>
      </section>

      <!-- 模型设置 -->
      <section class="settings-card glass-strong">
        <div class="card-header">
          <h2 class="card-title">模型设置</h2>
          <p class="card-subtitle">接入你自己的 OpenAI 兼容模型（DeepSeek / 通义 / Kimi / 智谱 / Ollama 本地等），未配置时使用系统默认模型</p>
        </div>

        <div v-if="modelState.configured" class="schedule-info">
          <div class="info-row">
            <span class="info-label">当前模型：</span>
            <span>{{ modelState.model_name }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">API Key：</span>
            <span>{{ modelState.api_key || '(未设置)' }}</span>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Base URL（API 地址）</label>
          <input v-model="modelForm.baseUrl" type="text" class="form-input" placeholder="https://api.deepseek.com 或 http://127.0.0.1:11434/v1" />
        </div>
        <div class="form-group">
          <label class="form-label">API Key</label>
          <input v-model="modelForm.apiKey" type="password" class="form-input" placeholder="你的 API Key（留空则保留已保存的 Key）" autocomplete="off" />
        </div>
        <div class="form-group">
          <label class="form-label">模型名称</label>
          <input v-model="modelForm.modelName" type="text" class="form-input" placeholder="如 deepseek-chat / qwen-plus / glm-4 / gpt-4o" />
        </div>

        <div class="card-actions">
          <button class="action-btn primary" :disabled="modelLoading" @click="saveModel">
            <span v-if="modelLoading" class="btn-spinner"></span>
            <span v-else>保存模型配置</span>
          </button>
          <button
            v-if="modelState.configured"
            class="action-btn danger-soft"
            :disabled="modelLoading"
            @click="resetModel"
          >
            恢复默认模型
          </button>
        </div>
      </section>

    </main>

    <!-- 全局 Toast -->
    <Transition name="toast">
      <div v-if="toast.show" class="toast" :class="toast.type">
        <svg v-if="toast.type === 'success'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <svg v-else-if="toast.type === 'error'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="15" y1="9" x2="9" y2="15"></line>
          <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>
        <span>{{ toast.message }}</span>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import {
  getScheduleSettings, uploadSchedule, updateScheduleStartDate, deleteSchedule,
  getModelSettings, saveModelSettings, clearModelSettings
} from '@/api/auth.js'

// 课表设置
const scheduleForm = reactive({ file: null, fileName: '', startDate: '' })
const scheduleState = ref({ uploaded: false, start_date: '', uploaded_at: '', schedule_url: '' })
const scheduleLoading = ref(false)
const scheduleDeleting = ref(false)

// 模型设置
const modelForm = reactive({ baseUrl: '', apiKey: '', modelName: '' })
const modelState = ref({ configured: false, base_url: '', api_key: '', model_name: '' })
const modelLoading = ref(false)

// Toast
const toast = reactive({ show: false, type: 'success', message: '', timer: null })
function showToast(message, type = 'success') {
  if (toast.timer) clearTimeout(toast.timer)
  toast.type = type
  toast.message = message
  toast.show = true
  toast.timer = setTimeout(() => { toast.show = false }, 2600)
}

// ==================== 课表设置 ====================

async function loadScheduleSettings() {
  try {
    const data = await getScheduleSettings()
    scheduleState.value = {
      uploaded: !!data.uploaded,
      start_date: data.start_date || '',
      uploaded_at: data.uploaded_at || '',
      schedule_url: data.schedule_url || '',
    }
    if (data.start_date) scheduleForm.startDate = data.start_date
  } catch (err) {
    showToast(err.message || '获取课表设置失败', 'error')
  }
}

function onScheduleFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    showToast('文件大小不能超过 2MB', 'error')
    e.target.value = ''
    return
  }
  scheduleForm.file = file
  scheduleForm.fileName = file.name
}

async function saveSchedule() {
  if (!scheduleForm.file) {
    showToast('请先选择 Excel 文件', 'error')
    return
  }
  if (!scheduleForm.startDate) {
    showToast('请设置开学日期', 'error')
    return
  }
  try {
    scheduleLoading.value = true
    const data = await uploadSchedule(scheduleForm.file, scheduleForm.startDate)
    scheduleState.value.uploaded = true
    scheduleState.value.start_date = data.start_date
    scheduleState.value.schedule_url = data.schedule_url
    scheduleState.value.uploaded_at = new Date().toLocaleString('zh-CN')
    scheduleForm.file = null
    scheduleForm.fileName = ''
    showToast('课表已上传')
  } catch (err) {
    showToast(err.message || '上传失败', 'error')
  } finally {
    scheduleLoading.value = false
  }
}

async function saveStartDateOnly() {
  if (!scheduleForm.startDate) {
    showToast('请选择开学日期', 'error')
    return
  }
  try {
    scheduleLoading.value = true
    await updateScheduleStartDate(scheduleForm.startDate)
    scheduleState.value.start_date = scheduleForm.startDate
    showToast('开学日期已更新')
  } catch (err) {
    showToast(err.message || '更新失败', 'error')
  } finally {
    scheduleLoading.value = false
  }
}

async function removeSchedule() {
  if (!confirm('确认删除当前课表？删除后 AI 将无法查询你的课程安排。')) return
  try {
    scheduleDeleting.value = true
    await deleteSchedule()
    scheduleState.value = { uploaded: false, start_date: '', uploaded_at: '', schedule_url: '' }
    scheduleForm.startDate = ''
    scheduleForm.file = null
    scheduleForm.fileName = ''
    showToast('课表已删除')
  } catch (err) {
    showToast(err.message || '删除失败', 'error')
  } finally {
    scheduleDeleting.value = false
  }
}

// ==================== 模型设置 ====================

async function loadModelSettings() {
  try {
    const data = await getModelSettings()
    modelState.value = {
      configured: !!data.configured,
      base_url: data.base_url || '',
      api_key: data.api_key || '',
      model_name: data.model_name || '',
    }
    modelForm.baseUrl = data.base_url || ''
    modelForm.apiKey = ''
    modelForm.modelName = data.model_name || ''
  } catch (err) {
    showToast(err.message || '获取模型设置失败', 'error')
  }
}

async function saveModel() {
  const baseUrl = (modelForm.baseUrl || '').trim()
  const modelName = (modelForm.modelName || '').trim()
  if (!baseUrl) {
    showToast('请输入 Base URL', 'error')
    return
  }
  if (!/^https?:\/\//i.test(baseUrl)) {
    showToast('Base URL 必须以 http:// 或 https:// 开头', 'error')
    return
  }
  if (!modelName) {
    showToast('请输入模型名称', 'error')
    return
  }
  if (!(modelForm.apiKey || '').trim() && !modelState.value.configured) {
    showToast('请输入 API Key', 'error')
    return
  }
  try {
    modelLoading.value = true
    await saveModelSettings(baseUrl, (modelForm.apiKey || '').trim(), modelName)
    modelForm.apiKey = ''
    showToast('模型配置已保存，下次对话生效')
    await loadModelSettings()
  } catch (err) {
    showToast(err.message || '保存失败', 'error')
  } finally {
    modelLoading.value = false
  }
}

async function resetModel() {
  if (!confirm('恢复系统默认模型？你的模型配置将被清除。')) return
  try {
    modelLoading.value = true
    await clearModelSettings()
    modelState.value = { configured: false, base_url: '', api_key: '', model_name: '' }
    modelForm.baseUrl = ''
    modelForm.apiKey = ''
    modelForm.modelName = ''
    showToast('已恢复系统默认模型')
  } catch (err) {
    showToast(err.message || '操作失败', 'error')
  } finally {
    modelLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadScheduleSettings(), loadModelSettings()])
})
</script>

<style scoped>
.settings-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
}

/* —— 主体 —— */
.settings-main {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px 50px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 720px;
  width: 100%;
  margin: 0 auto;
}

.settings-card {
  padding: 26px 28px;
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: card-in 0.5s var(--ease-out-expo) both;
}

.settings-card:nth-child(2) { animation-delay: 0.05s; }
.settings-card:nth-child(3) { animation-delay: 0.1s; }
.settings-card:nth-child(4) { animation-delay: 0.15s; }
.settings-card:nth-child(5) { animation-delay: 0.2s; }

@keyframes card-in {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-light);
}

.card-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.5px;
}

.card-subtitle {
  font-size: 12.5px;
  color: var(--text-muted);
}

/* —— 上传按钮（课表选择文件复用） —— */
.avatar-upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--accent);
  color: var(--accent-contrast);
  border-radius: var(--radius-pill);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: filter var(--transition), transform var(--spring-fast);
}

.avatar-upload-btn:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
}

.avatar-hint {
  font-size: 11.5px;
  color: var(--text-muted);
}

/* —— 课表设置 —— */
.schedule-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: var(--glass-light);
  font-size: 13px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}

.info-label {
  color: var(--text-muted);
  font-weight: 500;
}

.info-link {
  color: var(--accent);
  text-decoration: none;
  transition: filter var(--transition);
}

.info-link:hover {
  filter: brightness(1.1);
  text-decoration: underline;
}

/* —— 表单 —— */
.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.3px;
}

.form-input {
  padding: 11px 15px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: inherit;
  color: var(--text);
  background: var(--panel);
  outline: none;
  transition: border-color var(--transition), box-shadow var(--transition);
}

.form-input:hover:not(:disabled) {
  border-color: rgba(var(--accent-rgb), 0.3);
}

.form-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3.5px rgba(var(--accent-rgb), 0.14);
}

.form-input::placeholder {
  color: var(--text-muted);
}

.form-input:disabled {
  background: var(--hover);
  color: var(--text-muted);
  cursor: not-allowed;
}

/* —— 卡片操作按钮 —— */
.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 22px;
  border-radius: var(--radius-pill);
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all var(--transition);
  min-height: 38px;
}

.action-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.action-btn.primary {
  background: linear-gradient(180deg, var(--accent-hover), var(--accent));
  color: var(--accent-contrast);
  box-shadow: 0 8px 22px rgba(var(--accent-rgb), 0.22);
}

.action-btn.primary:not(:disabled):hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
}

.action-btn.secondary {
  background: var(--panel);
  color: var(--text);
  border-color: var(--border);
}

.action-btn.secondary:not(:disabled):hover {
  background: var(--hover);
}

.action-btn.danger-soft {
  background: var(--danger-soft);
  color: var(--danger);
  border-color: var(--danger-border);
}

.action-btn.danger-soft:not(:disabled):hover {
  background: rgba(220, 38, 38, 0.12);
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* —— Toast —— */
.toast {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 22px;
  border-radius: var(--radius-pill);
  font-size: 13.5px;
  font-weight: 500;
  color: #fff;
  background: var(--accent);
  box-shadow: 0 12px 36px var(--shadow);
  z-index: 9999;
  backdrop-filter: blur(12px);
}

.toast.success {
  background: #161616;
}

.toast.error {
  background: var(--danger);
  box-shadow: 0 12px 36px rgba(220, 38, 38, 0.32);
}

[data-theme="dark"] .toast.success {
  background: #f2f2f2;
  color: #161616;
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.3s var(--ease-out-expo), transform 0.3s var(--ease-out-expo);
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-12px);
}

/* —— 移动端 —— */
@media (max-width: 640px) {
  .settings-main {
    padding: 18px 14px 40px;
    gap: 16px;
  }

  .settings-card {
    padding: 22px 18px;
  }

  .card-actions {
    justify-content: stretch;
  }

  .action-btn {
    flex: 1;
  }
}
</style>
