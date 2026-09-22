<template>
  <div class="dpc-root" :class="{ compact }">
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
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'

const props = defineProps({
  doc: { type: Object, required: true }, // {kind, title, preview_url, download_url}
  compact: { type: Boolean, default: false } // 消息内联模式：限高 + 紧凑排版
})

const loading = ref(false)
const error = ref('')
const data = ref(null)
const sheetIdx = ref(0)
const slideIdx = ref(0)

const activeSheet = computed(() => (data.value?.sheets || [])[sheetIdx.value] || null)
const activeSlide = computed(() => (data.value?.slides || [])[slideIdx.value] || null)

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

onMounted(load)
watch(() => props.doc, load)
</script>

<style scoped>
.dpc-root { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.dpc-root.compact { max-height: 480px; overflow: hidden; border-top: 1px solid var(--border-light); }

.dv-state { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 40px 20px; font-size: 14px; color: var(--text-secondary); flex-wrap: wrap; }
.dv-state.error { color: var(--danger); flex-direction: column; gap: 14px; }

.dv-spinner {
  width: 16px; height: 16px; border: 2px solid rgba(var(--accent-rgb), 0.25);
  border-top-color: var(--accent); border-radius: 50%; animation: dv-spin 0.8s linear infinite;
}
@keyframes dv-spin { to { transform: rotate(360deg); } }

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

/* docx 阅读视图 */
.dv-doc {
  padding: 36px 48px 60px; max-width: 860px; width: 100%;
  font-size: 15px; line-height: 1.85; color: var(--text);
  overflow-y: auto;
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
.dpc-root.compact .dv-pdf { min-height: 420px; }

/* compact：消息内联模式，缩小留白 */
.dpc-root.compact .dv-doc { padding: 16px 20px 24px; font-size: 13.5px; line-height: 1.75; }
.dpc-root.compact .dv-doc :deep(h1) { font-size: 19px; }
.dpc-root.compact .dv-doc :deep(h2) { font-size: 16px; }
.dpc-root.compact .dv-doc :deep(h3) { font-size: 14.5px; }
.dpc-root.compact .dv-slide { padding: 16px 20px; min-height: 200px; }
.dpc-root.compact .dv-state { padding: 28px 16px; }

@media (max-width: 767px) {
  .dv-doc { padding: 24px 20px 48px; }
  .dv-slide { padding: 20px 22px; }
  .dpc-root.compact { max-height: 380px; }
}
</style>
