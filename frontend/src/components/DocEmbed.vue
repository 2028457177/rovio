<template>
  <div class="doc-embed" :class="{ open }">
    <!-- 卡片头：图标 + 标题 + 操作 -->
    <div class="de-head" @click="toggle">
      <span class="de-icon" :class="embed.kind">{{ icon }}</span>
      <div class="de-title-wrap">
        <span class="de-title">{{ embed.title }}</span>
        <span class="de-kind">{{ kindLabel }}</span>
      </div>
      <button class="de-btn" type="button" @click.stop="toggle">{{ open ? '收起' : '预览' }}</button>
      <a class="de-btn dl" :href="embed.download_url" :download="embed.title" @click.stop>下载</a>
    </div>

    <!-- 预览体 -->
    <div v-if="open" class="de-body">
      <div v-if="loading" class="de-loading"><span class="de-spinner"></span>正在转换预览…</div>
      <div v-else-if="error" class="de-error">
        {{ error }}
        <a class="de-btn dl" :href="embed.download_url" :download="embed.title">下载文件</a>
      </div>

      <!-- docx：转换出的 HTML -->
      <template v-else-if="data && data.kind === 'docx'">
        <div class="de-doc" v-html="data.html"></div>
      </template>

      <!-- xlsx：sheet 页签 + 表格 -->
      <template v-else-if="data && data.kind === 'xlsx'">
        <div class="de-tabs">
          <button
            v-for="(s, i) in data.sheets" :key="s.name"
            type="button" class="de-tab" :class="{ active: sheetIdx === i }"
            @click="sheetIdx = i"
          >{{ s.name }}</button>
        </div>
        <div v-if="activeSheet" class="de-table-wrap">
          <table class="de-table">
            <tbody>
              <tr v-for="(row, ri) in activeSheet.rows" :key="ri" :class="{ head: ri === 0 }">
                <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="activeSheet.truncated" class="de-note">行数较多，仅显示前 {{ activeSheet.rows.length }} 行</div>
        </div>
      </template>

      <!-- pptx：翻页 -->
      <template v-else-if="data && data.kind === 'pptx'">
        <div class="de-slide-nav">
          <button class="de-btn" type="button" :disabled="slideIdx <= 0" @click="slideIdx--">‹</button>
          <span class="de-slide-pos">{{ slideIdx + 1 }} / {{ data.slides.length }}</span>
          <button class="de-btn" type="button" :disabled="slideIdx >= data.slides.length - 1" @click="slideIdx++">›</button>
          <span v-if="activeSlide && activeSlide.title" class="de-slide-title">{{ activeSlide.title }}</span>
        </div>
        <div v-if="activeSlide" class="de-slide">
          <template v-for="(b, bi) in activeSlide.blocks" :key="bi">
            <p v-if="b.type === 'text'" class="de-slide-text">{{ b.text }}</p>
            <table v-else-if="b.type === 'table'" class="de-table slide-table">
              <tbody><tr v-for="(row, ri) in b.rows" :key="ri"><td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td></tr></tbody>
            </table>
            <img v-else-if="b.type === 'image'" :src="b.src" class="de-slide-img" alt="幻灯片插图" />
          </template>
          <p v-if="!activeSlide.blocks.length" class="de-slide-empty">（本页无文本内容）</p>
        </div>
      </template>

      <!-- pdf：浏览器原生 iframe -->
      <template v-else-if="embed.kind === 'pdf'">
        <iframe class="de-pdf" :src="embed.preview_url" title="PDF 预览"></iframe>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  embed: { type: Object, required: true } // {kind, title, preview_url, download_url}
})

const open = ref(false)
const loading = ref(false)
const error = ref('')
const data = ref(null)
const sheetIdx = ref(0)
const slideIdx = ref(0)

const ICONS = { docx: 'W', xlsx: 'X', pptx: 'P', pdf: 'F' }
const LABELS = { docx: 'Word 文档', xlsx: 'Excel 表格', pptx: 'PPT 幻灯片', pdf: 'PDF 文档' }
const icon = computed(() => ICONS[props.embed.kind] || '?')
const kindLabel = computed(() => LABELS[props.embed.kind] || props.embed.kind)

const activeSheet = computed(() => {
  const sheets = data.value?.sheets || []
  return sheets[sheetIdx.value] || null
})
const activeSlide = computed(() => {
  const slides = data.value?.slides || []
  return slides[slideIdx.value] || null
})

async function toggle() {
  open.value = !open.value
  if (open.value && !data.value && !loading.value && props.embed.kind !== 'pdf') {
    loading.value = true
    error.value = ''
    try {
      const res = await fetch(props.embed.preview_url)
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
}
</script>

<style scoped>
.doc-embed {
  margin: 8px 0 4px;
  max-width: 560px;
  border: 1px solid var(--border-light);
  border-radius: 14px;
  background: var(--panel);
  overflow: hidden;
  animation: de-in 0.3s var(--ease-out-expo) both;
  box-shadow: 0 3px 14px var(--shadow-sm);
}

@keyframes de-in {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.doc-embed.open { max-width: min(720px, 100%); }

.de-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition: background var(--transition);
}

.de-head:hover { background: var(--hover, rgba(var(--accent-rgb), 0.04)); }

.de-icon {
  width: 34px; height: 34px;
  border-radius: 9px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 800; color: #fff;
  flex-shrink: 0;
}
.de-icon.docx { background: #2b579a; }
.de-icon.xlsx { background: #217346; }
.de-icon.pptx { background: #c43e1c; }
.de-icon.pdf { background: #b30b00; }

.de-title-wrap { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }

.de-title {
  font-size: 13.5px; font-weight: 600; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.de-kind { font-size: 11px; color: var(--text-muted); }

.de-btn {
  padding: 5px 13px;
  border-radius: var(--radius-pill, 999px);
  border: 1px solid var(--border);
  background: var(--panel);
  color: var(--text-secondary);
  font-size: 12px; font-weight: 600; font-family: inherit;
  cursor: pointer; text-decoration: none;
  transition: all var(--transition);
  flex-shrink: 0;
}

.de-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.de-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.de-btn.dl { color: var(--accent); border-color: rgba(var(--accent-rgb), 0.4); }

.de-body { border-top: 1px solid var(--border-light); }

.de-loading, .de-error {
  display: flex; align-items: center; justify-content: center; gap: 9px;
  padding: 26px 14px; font-size: 13px; color: var(--text-secondary);
  flex-wrap: wrap;
}

.de-spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(var(--accent-rgb), 0.25);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: de-spin 0.8s linear infinite;
}
@keyframes de-spin { to { transform: rotate(360deg); } }

/* docx 正文 */
.de-doc {
  max-height: 480px; overflow-y: auto;
  padding: 18px 22px;
  font-size: 13.5px; line-height: 1.75; color: var(--text);
}
.de-doc :deep(h1) { font-size: 19px; font-weight: 800; margin: 16px 0 8px; }
.de-doc :deep(h2) { font-size: 16px; font-weight: 700; margin: 14px 0 6px; }
.de-doc :deep(h3) { font-size: 14.5px; font-weight: 700; margin: 12px 0 5px; }
.de-doc :deep(p) { margin: 6px 0; }
.de-doc :deep(img) { max-width: 100%; border-radius: 8px; margin: 8px 0; }
.de-doc :deep(table) { border-collapse: collapse; margin: 10px 0; width: 100%; font-size: 12.5px; }
.de-doc :deep(td), .de-doc :deep(th) { border: 1px solid var(--border-light); padding: 6px 10px; }
.de-doc :deep(ul), .de-doc :deep(ol) { padding-left: 22px; margin: 6px 0; }

/* xlsx */
.de-tabs {
  display: flex; gap: 4px; overflow-x: auto;
  padding: 8px 10px 0;
  border-bottom: 1px solid var(--border-light);
}
.de-tab {
  padding: 6px 14px; border: none; border-bottom: 2px solid transparent;
  background: none; color: var(--text-secondary);
  font-size: 12.5px; font-weight: 600; font-family: inherit;
  cursor: pointer; white-space: nowrap;
  transition: color var(--transition), border-color var(--transition);
}
.de-tab.active { color: var(--accent); border-bottom-color: var(--accent); }

.de-table-wrap { max-height: 440px; overflow: auto; }
.de-table { border-collapse: collapse; min-width: 100%; font-size: 12.5px; }
.de-table td {
  border: 1px solid var(--border-light);
  padding: 6px 12px; color: var(--text);
  white-space: nowrap; max-width: 320px; overflow: hidden; text-overflow: ellipsis;
}
.de-table tr.head td { background: rgba(var(--accent-rgb), 0.06); font-weight: 700; }
.de-note { padding: 8px 14px; font-size: 11.5px; color: var(--text-muted); }

/* pptx */
.de-slide-nav {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; border-bottom: 1px solid var(--border-light);
}
.de-slide-pos { font-size: 12px; color: var(--text-secondary); font-variant-numeric: tabular-nums; }
.de-slide-title { font-size: 12.5px; font-weight: 700; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.de-slide {
  min-height: 220px; max-height: 460px; overflow-y: auto;
  padding: 20px 24px;
  background: #fff;
}
[data-theme="dark"] .de-slide { background: #fafafa; }
.de-slide-text { font-size: 13.5px; color: #222; line-height: 1.7; margin: 6px 0; white-space: pre-wrap; }
.de-slide-img { max-width: 100%; border-radius: 6px; margin: 8px 0; }
.de-slide-empty { color: #999; font-size: 12.5px; text-align: center; padding: 30px 0; }
.slide-table { margin: 8px 0; }
.slide-table td { border: 1px solid #ddd; padding: 5px 10px; color: #222; }

/* pdf */
.de-pdf { width: 100%; height: 480px; border: none; }

@media (max-width: 767px) {
  .doc-embed, .doc-embed.open { max-width: 100%; }
  .de-pdf { height: 380px; }
  .de-kind { display: none; }
}
</style>
