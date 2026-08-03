<template>
  <div class="agent-caps">
    <!-- 头部操作栏 -->
    <div class="ac-toolbar">
      <span class="ac-count" v-if="agents.length">共 {{ agents.length }} 个专业智能体</span>
      <button class="ac-refresh" :disabled="loading" @click="load">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" :class="{ spinning: loading }">
          <polyline points="23 4 23 10 17 10"></polyline>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
        </svg>
        <span>{{ loading ? '刷新中…' : '刷新' }}</span>
      </button>
    </div>

    <!-- 加载态 -->
    <div v-if="loading && !agents.length" class="ac-state">
      <span class="ac-spinner"></span>
      <p class="ac-state-text">正在加载 Agent 清单…</p>
    </div>

    <!-- 错误态 -->
    <div v-else-if="error" class="ac-state">
      <p class="ac-state-text error">{{ error }}</p>
      <button class="ac-retry" @click="load">重试</button>
    </div>

    <!-- 空态 -->
    <div v-else-if="!agents.length" class="ac-state">
      <span class="ac-state-icon">🤖</span>
      <p class="ac-state-text">暂无可用的专业智能体</p>
    </div>

    <!-- 卡片列表 -->
    <div v-else class="ac-grid">
      <div v-for="agent in agents" :key="agent.name" class="ac-card">
        <div class="ac-card-head">
          <span class="ac-avatar" :class="`cat-${agent.category || 'generic'}`">
            {{ (agent.name || '?').charAt(0).toUpperCase() }}
          </span>
          <div class="ac-title-box">
            <h3 class="ac-name">{{ agent.name }}</h3>
            <span v-if="agent.category" class="ac-category">{{ agent.category }}</span>
          </div>
        </div>

        <p class="ac-desc">{{ agent.description }}</p>

        <div v-if="agent.workflow_hint" class="ac-block">
          <div class="ac-label">工作流提示</div>
          <p class="ac-hint">{{ agent.workflow_hint }}</p>
        </div>

        <div v-if="agent.tools && agent.tools.length" class="ac-block">
          <div class="ac-label">可用工具</div>
          <div class="ac-tools">
            <span v-for="t in agent.tools" :key="t" class="ac-tool">{{ t }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchSubagentsApi } from '@/api/chat.js'

const agents = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    agents.value = await fetchSubagentsApi()
  } catch (e) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.agent-caps {
  padding: 20px 24px 28px;
  color: rgba(20, 20, 25, 0.95);
  flex: 1;
}

.ac-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.ac-count {
  font-size: 12.5px;
  color: rgba(20, 20, 25, 0.6);
}

.ac-refresh {
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
.ac-refresh:hover {
  border-color: rgba(var(--accent-rgb), 0.5);
  color: var(--accent);
}
.ac-refresh:disabled { opacity: 0.6; cursor: not-allowed; }
.ac-refresh svg.spinning { animation: ac-spin 0.8s linear infinite; }
@keyframes ac-spin { to { transform: rotate(360deg); } }

.ac-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 70px 20px;
  text-align: center;
}
.ac-state-icon { font-size: 34px; }
.ac-state-text {
  font-size: 13.5px;
  color: rgba(20, 20, 25, 0.55);
  line-height: 1.8;
}
.ac-state-text.error { color: var(--danger); }
.ac-spinner {
  width: 26px; height: 26px;
  border: 3px solid rgba(var(--accent-rgb), 0.2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: ac-spin 0.7s linear infinite;
}
.ac-retry {
  padding: 7px 22px;
  border: none;
  border-radius: var(--radius-pill);
  background: var(--accent);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.ac-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 14px;
}

.ac-card {
  border: 1px solid rgba(20, 20, 25, 0.1);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.75);
  padding: 16px 18px;
  transition: border-color 0.2s ease, transform 0.2s ease;
}
.ac-card:hover {
  border-color: rgba(var(--accent-rgb), 0.35);
  transform: translateY(-2px);
}

.ac-card-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.ac-avatar {
  width: 38px; height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  font-weight: 800;
  color: #fff;
  flex-shrink: 0;
}
.cat-generic { background: linear-gradient(135deg, #6366f1, #8b5cf6); }
.cat-search, .cat-browser, .cat-web { background: linear-gradient(135deg, #0ea5e9, #06b6d4); }
.cat-codexec, .cat-code, .cat-artifact, .cat-file { background: linear-gradient(135deg, #f59e0b, #f97316); }
.cat-memory, .cat-document, .cat-report, .cat-knowledge { background: linear-gradient(135deg, #10b981, #14b8a6); }

.ac-title-box {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.ac-name {
  margin: 0;
  font-size: 14.5px;
  font-weight: 700;
  color: rgba(20, 20, 25, 0.95);
  letter-spacing: 0.3px;
}

.ac-category {
  font-size: 10.5px;
  font-weight: 600;
  color: rgba(20, 20, 25, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.6px;
}

.ac-desc {
  margin: 0 0 12px;
  font-size: 12.5px;
  line-height: 1.7;
  color: rgba(20, 20, 25, 0.72);
}

.ac-block { margin-bottom: 10px; }

.ac-label {
  font-size: 10.5px;
  font-weight: 700;
  color: rgba(20, 20, 25, 0.45);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 5px;
}

.ac-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.65;
  color: rgba(20, 20, 25, 0.65);
  background: rgba(var(--accent-rgb), 0.05);
  border: 1px solid rgba(var(--accent-rgb), 0.12);
  border-radius: 8px;
  padding: 8px 11px;
}

.ac-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ac-tool {
  font-size: 11px;
  font-weight: 600;
  color: rgba(20, 20, 25, 0.7);
  background: rgba(20, 20, 25, 0.06);
  padding: 2.5px 10px;
  border-radius: var(--radius-pill);
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
}

@media (max-width: 767px) {
  .agent-caps { padding: 16px 14px 24px; }
  .ac-grid { grid-template-columns: 1fr; }
}
</style>
