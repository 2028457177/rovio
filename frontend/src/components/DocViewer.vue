<template>
  <Teleport to="body">
    <Transition name="dv-fade">
      <div v-if="modelValue" class="dv-overlay" @click.self="close">
        <Transition name="dv-slide" appear>
          <aside v-if="modelValue" class="dv-panel glass-strong" role="dialog" aria-modal="true" :aria-label="doc.title">
            <!-- 头部：类型图标 + 文件名 + 下载 + 关闭 -->
            <header class="dv-header">
              <div class="dv-header-left">
                <span class="dv-icon" :class="doc.kind">{{ icon }}</span>
                <div class="dv-title-wrap">
                  <h2 class="dv-title">{{ doc.title }}</h2>
                  <span class="dv-kind">{{ kindLabel }}</span>
                </div>
              </div>
              <div class="dv-actions">
                <a class="dv-btn dl" :href="doc.download_url" :download="doc.title" title="下载">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                  </svg>
                  下载
                </a>
                <button class="dv-close" @click="close" title="关闭" aria-label="关闭">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </div>
            </header>

            <!-- 内容区：大尺寸阅读视图 -->
            <div class="dv-body">
              <div v-if="loading" class="dv-state"><span class="dv-spinner"></span>正在加载预览…</div>
              <div v-else-if="error" class="dv-state error">
                {{ error }}
                <a class="dv-btn dl" :href="doc.download_url" :download="doc.title">下载文件</a>
              </div>

              <!-- docx：排版 HTML 阅读视图 -->
              <template v-else-if="data && data.kind === 'docx'">
                <article class="dv-doc" v-html="data.html"></article>
              </template>

              <!-- xlsx：sheet 页签 + 表格 -->
              <template v-else-if="data && data.kind === 'xlsx'">
                <div class="dv-tabs">
                  <button v-for="(s, i) in data.sheets" :key="s.name" type="button" class="dv-tab"
                    :class="{ active: sheetIdx === i }" @click="sheetIdx = i">{{ s.name }}</button>
                </div>
                <div v-if="activeSheet" class="dv-table-wrap">
                  <table class="dv-table">
                    <tbody>
                      <tr v-for="(row, ri) in activeSheet.rows" :key="ri" :class="{ head: ri === 0 }">
                        <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
                      </tr>
                    </tbody>
                  </table>
                  <div v-if="activeSheet.truncated" class="dv-note">行数较多，仅显示前 {{ activeSheet.rows.length }} 行</div>
                </div>
              </template>

              <!-- pptx：逐页翻看 -->
              <template v-else-if="data && data.kind === 'pptx'">
                <div class="dv-slide-nav">
                  <button class="dv-btn" type="button" :disabled="slideIdx <= 0" @click="slideIdx--">‹ 上一页</button>
                  <span class="dv-slide-pos">{{ slideIdx + 1 }} / {{ data.slides.length }}</span>
                  <button class="dv-btn" type="button" :disabled="slideIdx >= data.slides.length - 1" @click="slideIdx++">下一页 ›</button>
                  <span v-if="activeSlide && activeSlide.title" class="dv-slide-title">{{ activeSlide.title }}</span>
                </div>
                <div v-if="activeSlide" class="dv-slide">
                  <template v-for="(b, bi) in activeSlide.blocks" :key="bi">
                    <p v-if="b.type === 'text'" class="dv-slide-text">{{ b.text }}</p>
                    <table v-else-if="b.type === 'table'" class="dv-table slide-table">
                      <tbody><tr v-for="(row, ri) in b.rows" :key="ri"><td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td></tr></tbody>
                    </table>
                    <img v-else-if="b.type === 'image'" :src="b.src" class="dv-slide-img" alt="幻灯片插图" />
                  </template>
                  <p v-if="!activeSlide.blocks.length" class="dv-slide-empty">（本页无文本内容）</p>
                </div>
              </template>

              <!-- pdf：浏览器原生 -->
              <template v-else-if="doc.kind === 'pdf'">
                <iframe class="dv-pdf" :src="doc.preview_url" title="PDF 预览"></iframe>
              </template>
            </div>
          </aside>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  doc: { type: Object, required: true } // {kind, title, preview_url, download_url}
})
const emit = defineEmits(['update:modelValue'])

const ICONS = { docx: 'W', xlsx: 'X', pptx: 'P', pdf: 'F' }
const LABELS = { docx: 'Word 文档', xlsx: 'Excel 表格', pptx: 'PPT 幻灯片', pdf: 'PDF 文档' }
const icon = computed(() => ICONS[props.doc.kind] || '?')
const kindLabel = computed(() => LABELS[props.doc.kind] || props.doc.kind)

const loading = ref(false)
const error = ref('')
const data = ref(null)
const sheetIdx = ref(0)
const slideIdx = ref(0)

const activeSheet = computed(() => (data.value?.sheets || [])[sheetIdx.value] || null)
const activeSlide = computed(() => (data.value?.slides || [])[slideIdx.value] || null)

function close() {
  emit('update:modelValue', false)
}

function onKeydown(e) {
  if (e.key === 'Escape' && props.modelValue) close()
}

async function load() {
  if (!props.doc || !props.doc.preview_url) return
  sheetIdx.value = 0
  slideIdx.value = 0
  if (props.doc.kind === 'pdf') return // pdf 走 iframe，无需拉 JSON
  data.value = null
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(props.doc.preview_url)
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || `加载失败 (${res.status})`)
    }
    data.value = await res.json()
  } catch (e) {
    error.value = e.message || '预览加载失败'
  } finally {
    loading.value = false
  }
}

// 打开时加载
watch(() => props.modelValue, (open) => {
  if (open) load()
})
watch(() => props.doc, () => {
  if (props.modelValue) load()
})

if (typeof document !== 'undefined') {
  document.addEventListener('keydown', onKeydown)
}
</script>

<style scoped>
.dv-overlay {
  position: fixed;
  inset: 0;
  z-index: 9200;
  background: rgba(0, 0, 0, 0.42);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  display: flex;
  justify-content: flex-start;
}

.dv-panel {
  width: min(72vw, 1040px);
  max-width: 94vw;
  height: 100vh;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  box-shadow: 16px 0 48px rgba(0, 0, 0, 0.18);
  background: var(--glass-strong);
}

/* 头部 */
.dv-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.dv-header-left { display: flex; align-items: center; gap: 12px; min-width: 0; }

.dv-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 17px; font-weight: 800; color: #fff; flex-shrink: 0;
}
.dv-icon.docx { background: #2b579a; }
.dv-icon.xlsx { background: #217346; }
.dv-icon.pptx { background: #c43e1c; }
.dv-icon.pdf { background: #b30b00; }

.dv-title-wrap { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.dv-title { font-size: 17px; font-weight: 700; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dv-kind { font-size: 12px; color: var(--text-muted); }

.dv-actions { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

.dv-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 15px; border-radius: var(--radius-pill, 999px);
  border: 1px solid var(--border); background: var(--panel);
  color: var(--text-secondary); font-size: 12.5px; font-weight: 600;
  font-family: inherit; cursor: pointer; text-decoration: none;
  transition: all var(--transition);
}
.dv-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.dv-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.dv-btn.dl { color: var(--accent); border-color: rgba(var(--accent-rgb), 0.4); }

.dv-close {
  display: flex; align-items: center; justify-content: center;
  width: 38px; height: 38px; border-radius: 50%;
  border: 1px solid var(--border); background: var(--panel);
  color: var(--text-secondary); cursor: pointer; transition: all var(--transition);
}
.dv-close:hover { background: var(--danger-soft); color: var(--danger); border-color: var(--danger-border); transform: rotate(90deg); }

/* 内容区 */
.dv-body { flex: 1; overflow: auto; display: flex; flex-direction: column; }

.dv-state { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 60px 20px; font-size: 14px; color: var(--text-secondary); flex-wrap: wrap; }
.dv-state.error { color: var(--danger); flex-direction: column; gap: 14px; }

.dv-spinner {
  width: 16px; height: 16px; border: 2px solid rgba(var(--accent-rgb), 0.25);
  border-top-color: var(--accent); border-radius: 50%; animation: dv-spin 0.8s linear infinite;
}
@keyframes dv-spin { to { transform: rotate(360deg); } }

/* docx 阅读视图 */
.dv-doc {
  padding: 36px 48px 60px; max-width: 860px; width: 100%;
  font-size: 15px; line-height: 1.85; color: var(--text);
}
.dv-doc :deep(h1) { font-size: 24px; font-weight: 800; margin: 22px 0 10px; }
.dv-doc :deep(h2) { font-size: 19px; font-weight: 700; margin: 18px 0 8px; }
.dv-doc :deep(h3) { font-size: 16px; font-weight: 700; margin: 14px 0 6px; }
.dv-doc :deep(p) { margin: 8px 0; }
.dv-doc :deep(img) { max-width: 100%; border-radius: 8px; margin: 10px 0; }
.dv-doc :deep(table) { border-collapse: collapse; margin: 12px 0; width: 100%; font-size: 13.5px; }
.dv-doc :deep(td), .dv-doc :deep(th) { border: 1px solid var(--border-light); padding: 8px 12px; }
.dv-doc :deep(ul), .dv-doc :deep(ol) { padding-left: 24px; margin: 8px 0; }

/* xlsx */
.dv-tabs { display: flex; gap: 4px; overflow-x: auto; padding: 10px 16px 0; border-bottom: 1px solid var(--border-light); flex-shrink: 0; }
.dv-tab {
  padding: 7px 16px; border: none; border-bottom: 2px solid transparent;
  background: none; color: var(--text-secondary); font-size: 13px; font-weight: 600;
  font-family: inherit; cursor: pointer; white-space: nowrap;
  transition: color var(--transition), border-color var(--transition);
}
.dv-tab.active { color: var(--accent); border-bottom-color: var(--accent); }

.dv-table-wrap { flex: 1; overflow: auto; }
.dv-table { border-collapse: collapse; min-width: 100%; font-size: 13.5px; }
.dv-table td { border: 1px solid var(--border-light); padding: 8px 16px; color: var(--text); white-space: nowrap; max-width: 420px; overflow: hidden; text-overflow: ellipsis; }
.dv-table tr.head td { background: rgba(var(--accent-rgb), 0.06); font-weight: 700; position: sticky; top: 0; }
.dv-note { padding: 10px 18px; font-size: 12px; color: var(--text-muted); }

/* pptx */
.dv-slide-nav { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-bottom: 1px solid var(--border-light); flex-shrink: 0; }
.dv-slide-pos { font-size: 13px; color: var(--text-secondary); font-variant-numeric: tabular-nums; }
.dv-slide-title { font-size: 13px; font-weight: 700; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }

.dv-slide {
  flex: 1; overflow-y: auto; padding: 32px 44px; background: #fff; min-height: 300px;
}
[data-theme="dark"] .dv-slide { background: #fafafa; }
.dv-slide-text { font-size: 14.5px; color: #222; line-height: 1.75; margin: 8px 0; white-space: pre-wrap; }
.dv-slide-img { max-width: 100%; border-radius: 6px; margin: 10px 0; }
.dv-slide-empty { color: #999; font-size: 13px; text-align: center; padding: 40px 0; }
.slide-table { margin: 10px 0; }
.slide-table td { border: 1px solid #ddd; padding: 6px 12px; color: #222; }

/* pdf */
.dv-pdf { width: 100%; flex: 1; min-height: 0; border: none; }

/* 动画 */
.dv-fade-enter-active, .dv-fade-leave-active { transition: opacity 0.3s ease; }
.dv-fade-enter-from, .dv-fade-leave-to { opacity: 0; }
.dv-slide-enter-active, .dv-slide-leave-active { transition: transform 0.38s var(--ease-out-expo, cubic-bezier(0.16, 1, 0.3, 1)); }
.dv-slide-enter-from, .dv-slide-leave-to { transform: translateX(-100%); }

@media (max-width: 767px) {
  .dv-panel { width: 100vw; max-width: 100vw; }
  .dv-doc { padding: 24px 20px 48px; }
  .dv-slide { padding: 20px 22px; }
  .dv-kind { display: none; }
}
</style>
