<template>
  <div class="plan-panel">
    <div class="plan-header">
      <span class="plan-icon">🎯</span>
      <span class="plan-goal">{{ plan.goal || '执行计划' }}</span>
      <span v-if="streaming" class="plan-status running">执行中</span>
      <span v-else-if="plan.status === 'completed'" class="plan-status done">已完成</span>
      <span v-else-if="plan.status === 'failed'" class="plan-status failed">失败</span>
    </div>

    <div class="plan-steps">
      <div
        v-for="step in stepsList"
        :key="step.step_idx"
        class="plan-step"
        :class="step.status"
      >
        <div class="step-header" @click="toggleStep(step.step_idx)">
          <span class="step-status-icon">
            <span v-if="step.status === 'running'" class="step-spinner"></span>
            <span v-else-if="step.status === 'done'" class="step-check">✓</span>
            <span v-else-if="step.status === 'failed'" class="step-cross">✗</span>
            <span v-else class="step-pending-dot">○</span>
          </span>
          <span v-if="step.subagent" class="step-agent-tag">{{ step.subagent }}</span>
          <span class="step-desc">{{ step.description }}</span>
          <span
            v-if="step.thinking || step.output || step.error"
            class="step-expand"
            :class="{ open: opened[step.step_idx] }"
          >▾</span>
        </div>

        <div v-if="opened[step.step_idx]" class="step-detail">
          <div v-if="step.error" class="step-error">错误：{{ step.error }}</div>
          <div v-if="step.thinking" class="step-thinking">
            <div class="detail-label">思考</div>
            <pre class="detail-content">{{ step.thinking }}</pre>
          </div>
          <div v-if="step.output" class="step-output">
            <div class="detail-label">输出</div>
            <pre class="detail-content">{{ step.output }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed } from 'vue'

const props = defineProps({
  plan: { type: Object, required: true },
  steps: { type: Object, default: () => ({}) },
  streaming: { type: Boolean, default: false }
})

const opened = reactive({})

function toggleStep(idx) {
  opened[idx] = !opened[idx]
}

// 合并 plan.steps（静态结构）和 steps（实时状态更新）
const stepsList = computed(() => {
  const planSteps = props.plan.steps || []
  return planSteps.map(s => {
    const live = props.steps[s.step_idx] || {}
    return {
      step_idx: s.step_idx,
      description: s.description,
      subagent: s.subagent || live.subagent || '',
      status: live.status || s.status || 'pending',
      thinking: live.thinking || '',
      output: live.output || '',
      error: live.error || ''
    }
  })
})
</script>

<style scoped>
.plan-panel {
  margin-bottom: 8px;
  border: 1px solid var(--border-light);
  border-radius: 12px;
  overflow: hidden;
  background: rgba(var(--accent-rgb), 0.03);
}

.plan-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  background: rgba(var(--accent-rgb), 0.06);
  border-bottom: 1px solid var(--border-light);
}

.plan-icon { font-size: 14px; flex-shrink: 0; }

.plan-goal {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plan-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  font-weight: 600;
  flex-shrink: 0;
}
.plan-status.running {
  background: rgba(var(--accent-rgb), 0.15);
  color: var(--accent);
}
.plan-status.done {
  background: rgba(34, 197, 94, 0.15);
  color: #16a34a;
}
.plan-status.failed {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
}

.plan-steps { padding: 4px 0; }

.plan-step {
  padding: 0 14px;
  transition: background var(--transition);
}
.plan-step:hover { background: rgba(var(--accent-rgb), 0.04); }
.plan-step.running { background: rgba(var(--accent-rgb), 0.05); }

.step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 0;
  cursor: pointer;
  user-select: none;
}

.step-status-icon {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 13px;
}

.step-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--accent-soft);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: step-spin 0.8s linear infinite;
}
@keyframes step-spin { to { transform: rotate(360deg); } }

.step-check { color: #16a34a; font-weight: 700; }
.step-cross { color: var(--danger); font-weight: 700; }
.step-pending-dot { color: var(--text-muted); }

.step-agent-tag {
  font-size: 10.5px;
  font-weight: 600;
  padding: 1px 7px;
  border-radius: var(--radius-pill);
  background: rgba(var(--accent-rgb), 0.12);
  color: var(--accent);
  flex-shrink: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.step-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-expand {
  font-size: 10px;
  color: var(--text-muted);
  transition: transform var(--transition);
  flex-shrink: 0;
}
.step-expand.open { transform: rotate(180deg); }

.step-detail {
  padding: 0 0 10px 26px;
  animation: detail-in 0.2s ease;
}
@keyframes detail-in {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.step-error {
  font-size: 12px;
  color: var(--danger);
  background: rgba(239, 68, 68, 0.08);
  padding: 6px 10px;
  border-radius: 6px;
  margin-bottom: 6px;
}

.detail-label {
  font-size: 10.5px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 3px;
}

.detail-content {
  margin: 0 0 8px;
  padding: 7px 10px;
  background: var(--panel);
  border: 1px solid var(--border-light);
  border-radius: 6px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 11.5px;
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}

@media (max-width: 767px) {
  .plan-goal { font-size: 12.5px; }
  .step-desc { font-size: 12px; }
  .plan-step { padding: 0 10px; }
  .step-detail { padding-left: 22px; }
}
</style>
