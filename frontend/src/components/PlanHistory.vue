<template>
  <div class="plan-history">
    <!-- 头部操作栏 -->
    <div class="ph-toolbar">
      <span class="ph-count" v-if="plans.length">共 {{ plans.length }} 条执行记录</span>
      <button class="ph-refresh" :disabled="loading" @click="load">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" :class="{ spinning: loading }">
          <polyline points="23 4 23 10 17 10"></polyline>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
        </svg>
        <span>{{ loading ? '刷新中…' : '刷新' }}</span>
      </button>
    </div>

    <!-- 加载态 -->
    <div v-if="loading && !plans.length" class="ph-state">
      <span class="ph-spinner"></span>
      <p class="ph-state-text">正在加载计划历史…</p>
    </div>

    <!-- 错误态 -->
    <div v-else-if="error" class="ph-state">
      <p class="ph-state-text error">{{ error }}</p>
      <button class="ph-retry" @click="load">重试</button>
    </div>

    <!-- 空态 -->
    <div v-else-if="!plans.length" class="ph-state">
      <span class="ph-state-icon">🗂️</span>
      <p class="ph-state-text">还没有执行过长任务<br />给 AI 一个复杂需求，它会拆解成计划分步完成</p>
    </div>

    <!-- 列表 -->
    <div v-else class="ph-list">
      <div
        v-for="plan in plans"
        :key="plan.id"
        class="ph-item"
      >
        <div class="ph-item-head" @click="toggle(plan.id)">
          <span class="ph-status" :class="plan.status">{{ statusLabel(plan.status) }}</span>
          <span class="ph-goal" :title="plan.goal">{{ plan.goal }}</span>
          <span class="ph-meta">
            <span class="ph-time">{{ fmtTime(plan.created_at) }}</span>
            <span v-if="details[plan.id] && details[plan.id].steps" class="ph-steps-count">{{ details[plan.id].steps.length }} 步</span>
          </span>
          <span class="ph-arrow" :class="{ open: opened[plan.id] }">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </span>
        </div>

        <!-- 步骤明细（展开时按需加载详情） -->
        <div v-if="opened[plan.id]" class="ph-steps">
          <div v-if="detailLoading[plan.id]" class="ph-step-loading">
            <span class="ph-mini-spin"></span> 正在加载步骤明细…
          </div>
          <div v-else-if="detailError[plan.id]" class="ph-step-loading error">
            加载失败：{{ detailError[plan.id] }}
          </div>
          <template v-else-if="details[plan.id]">
            <div
              v-for="step in details[plan.id].steps || []"
              :key="step.step_idx"
              class="ph-step"
            >
              <div class="ph-step-head" @click="toggleStep(plan.id, step.step_idx)">
                <span class="ph-step-status">
                  <span v-if="step.status === 'completed'" class="ph-step-check">✓</span>
                  <span v-else-if="step.status === 'failed' || step.status === 'blocked'" class="ph-step-cross">✗</span>
                  <span v-else-if="step.status === 'running'" class="ph-mini-spin"></span>
                  <span v-else class="ph-step-dot">○</span>
                </span>
                <span v-if="step.subagent" class="ph-agent">{{ step.subagent }}</span>
                <span class="ph-step-desc">{{ step.description }}</span>
                <span v-if="step.result || step.error_msg" class="ph-step-arrow" :class="{ open: stepOpened[`${plan.id}-${step.step_idx}`] }">▾</span>
              </div>
              <div v-if="stepOpened[`${plan.id}-${step.step_idx}`]" class="ph-step-detail">
                <div v-if="step.error_msg" class="ph-step-error">错误：{{ step.error_msg }}</div>
                <div v-if="step.result" class="ph-step-result">
                  <div class="ph-label">步骤结果</div>
                  <pre class="ph-pre">{{ step.result }}</pre>
                </div>
              </div>
            </div>
            <div v-if="details[plan.id].final_answer" class="ph-final">
              <div class="ph-label">最终回答</div>
              <p class="ph-final-text">{{ details[plan.id].final_answer }}</p>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { fetchPlansApi, fetchPlanDetailApi } from '@/api/chat.js'

const plans = ref([])
const loading = ref(false)
const error = ref('')
const opened = reactive({})
const stepOpened = reactive({})
const details = reactive({})
const detailLoading = reactive({})
const detailError = reactive({})

const STATUS_TEXT = {
  pending: '待执行',
  executing: '执行中',
  completed: '已完成',
  failed: '失败',
  blocked: '阻塞'
}

function statusLabel(s) {
  return STATUS_TEXT[s] || s
}

function fmtTime(v) {
  if (!v) return ''
  // 后端列表接口已格式化 "YYYY-MM-DD HH:MM:SS"
  if (typeof v === 'string') return v
  const d = new Date(v * 1000)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function loadDetail(id) {
  detailLoading[id] = true
  detailError[id] = ''
  try {
    const detail = await fetchPlanDetailApi(id)
    if (detail) details[id] = detail
  } catch (e) {
    detailError[id] = e.message || '加载失败'
  } finally {
    detailLoading[id] = false
  }
}

async function toggle(id) {
  opened[id] = !opened[id]
  if (opened[id] && !details[id]) {
    loadDetail(id)
  }
}

function toggleStep(planId, idx) {
  const key = `${planId}-${idx}`
  stepOpened[key] = !stepOpened[key]
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    plans.value = await fetchPlansApi()
  } catch (e) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.plan-history {
  padding: 20px 24px 28px;
  color: rgba(20, 20, 25, 0.95);
  flex: 1;
}

.ph-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.ph-count {
  font-size: 12.5px;
  color: rgba(20, 20, 25, 0.6);
}

.ph-refresh {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid rgba(20, 20, 25, 0.14);
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.7);
  color: rgba(20, 20, 25, 0.85);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}
.ph-refresh:hover {
  border-color: rgba(var(--accent-rgb), 0.5);
  color: var(--accent);
}
.ph-refresh:disabled { opacity: 0.6; cursor: not-allowed; }
.ph-refresh svg.spinning { animation: ph-spin 0.8s linear infinite; }
@keyframes ph-spin { to { transform: rotate(360deg); } }

.ph-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 70px 20px;
  text-align: center;
}
.ph-state-icon { font-size: 34px; }
.ph-state-text {
  font-size: 13.5px;
  color: rgba(20, 20, 25, 0.55);
  line-height: 1.8;
}
.ph-state-text.error { color: var(--danger); }
.ph-spinner {
  width: 26px; height: 26px;
  border: 3px solid rgba(var(--accent-rgb), 0.2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: ph-spin 0.7s linear infinite;
}
.ph-retry {
  padding: 7px 22px;
  border: none;
  border-radius: var(--radius-pill);
  background: var(--accent);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.ph-list { display: flex; flex-direction: column; gap: 10px; }

.ph-item {
  border: 1px solid rgba(20, 20, 25, 0.1);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.75);
  overflow: hidden;
  transition: border-color 0.2s ease;
}
.ph-item:hover { border-color: rgba(var(--accent-rgb), 0.35); }

.ph-item-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
}

.ph-status {
  font-size: 11px;
  font-weight: 700;
  padding: 2.5px 10px;
  border-radius: var(--radius-pill);
  flex-shrink: 0;
}
.ph-status.pending { background: rgba(148, 163, 184, 0.2); color: #64748b; }
.ph-status.executing { background: rgba(var(--accent-rgb), 0.15); color: var(--accent); }
.ph-status.completed { background: rgba(34, 197, 94, 0.15); color: #16a34a; }
.ph-status.failed { background: rgba(239, 68, 68, 0.15); color: #dc2626; }
.ph-status.blocked { background: rgba(245, 158, 11, 0.15); color: #d97706; }

.ph-goal {
  flex: 1;
  min-width: 0;
  font-size: 13.5px;
  font-weight: 600;
  color: rgba(20, 20, 25, 0.92);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ph-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.ph-time { font-size: 11.5px; color: rgba(20, 20, 25, 0.5); }
.ph-steps-count {
  font-size: 11px;
  color: rgba(20, 20, 25, 0.55);
  background: rgba(20, 20, 25, 0.06);
  padding: 2px 8px;
  border-radius: var(--radius-pill);
}

.ph-arrow { color: rgba(20, 20, 25, 0.4); transition: transform 0.25s ease; flex-shrink: 0; }
.ph-arrow.open { transform: rotate(180deg); }

.ph-steps { padding: 0 16px 12px; border-top: 1px dashed rgba(20, 20, 25, 0.1); }

.ph-step-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 6px;
  font-size: 12.5px;
  color: rgba(20, 20, 25, 0.55);
}
.ph-step-loading.error { color: var(--danger); }

.ph-step { transition: background 0.15s ease; border-radius: 8px; }
.ph-step:hover { background: rgba(var(--accent-rgb), 0.04); }

.ph-step-head {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 6px;
  cursor: pointer;
  user-select: none;
}

.ph-step-status {
  width: 16px; height: 16px;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px;
  flex-shrink: 0;
}
.ph-step-check { color: #16a34a; font-weight: 700; }
.ph-step-cross { color: #dc2626; font-weight: 700; }
.ph-step-dot { color: rgba(20, 20, 25, 0.35); }
.ph-mini-spin {
  width: 11px; height: 11px;
  border: 2px solid rgba(var(--accent-rgb), 0.25);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: ph-spin 0.8s linear infinite;
}

.ph-agent {
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 8px;
  border-radius: var(--radius-pill);
  background: rgba(var(--accent-rgb), 0.12);
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  flex-shrink: 0;
}

.ph-step-desc {
  flex: 1;
  min-width: 0;
  font-size: 12.5px;
  color: rgba(20, 20, 25, 0.78);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ph-step-arrow { font-size: 10px; color: rgba(20, 20, 25, 0.4); transition: transform 0.25s ease; flex-shrink: 0; }
.ph-step-arrow.open { transform: rotate(180deg); }

.ph-step-detail { padding: 0 6px 10px 31px; }

.ph-step-error {
  font-size: 12px;
  color: #dc2626;
  background: rgba(239, 68, 68, 0.08);
  padding: 6px 10px;
  border-radius: 6px;
  margin-bottom: 8px;
}

.ph-label {
  font-size: 10.5px;
  font-weight: 700;
  color: rgba(20, 20, 25, 0.45);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 5px;
}

.ph-pre {
  margin: 0 0 10px;
  padding: 9px 12px;
  background: rgba(20, 20, 25, 0.04);
  border: 1px solid rgba(20, 20, 25, 0.08);
  border-radius: 8px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 11.5px;
  color: rgba(20, 20, 25, 0.75);
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 220px;
  overflow-y: auto;
}

.ph-final {
  margin-top: 6px;
  padding: 10px 12px;
  background: rgba(34, 197, 94, 0.05);
  border: 1px solid rgba(34, 197, 94, 0.18);
  border-radius: 8px;
}
.ph-final-text {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.7;
  color: rgba(20, 20, 25, 0.85);
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 767px) {
  .plan-history { padding: 16px 14px 24px; }
  .ph-meta { display: none; }
}
</style>
