<template>
  <div class="doc-embed">
    <div class="de-header">
      <span class="de-icon" :class="embed.kind">{{ icon }}</span>
      <div class="de-title-wrap">
        <span class="de-title">{{ embed.title }}</span>
        <span class="de-kind">{{ kindLabel }}</span>
      </div>
      <div class="de-actions">
        <button class="de-btn" type="button" @click="expanded = !expanded">
          {{ expanded ? '收起' : '展开' }}
        </button>
        <button class="de-btn" type="button" @click="emit('open', embed)" title="在大面板中查看">放大</button>
        <a class="de-btn" :href="embed.download_url" :download="embed.title" title="下载文件">下载</a>
      </div>
    </div>
    <div v-if="expanded" class="de-body">
      <DocPreviewContent :doc="embed" compact />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import DocPreviewContent from './DocPreviewContent.vue'

const props = defineProps({
  embed: { type: Object, required: true } // {kind, title, preview_url, download_url}
})
const emit = defineEmits(['open'])

const expanded = ref(false)

const ICONS = { docx: 'W', xlsx: 'X', pptx: 'P', pdf: 'F' }
const LABELS = { docx: 'Word', xlsx: 'Excel', pptx: 'PPT', pdf: 'PDF' }
const icon = computed(() => ICONS[props.embed.kind] || '?')
const kindLabel = computed(() => LABELS[props.embed.kind] || props.embed.kind)
</script>

<style scoped>
.doc-embed {
  margin: 8px 0 4px;
  max-width: 720px;
  border: 1px solid var(--border-light);
  border-radius: 12px;
  background: var(--panel);
  overflow: hidden;
  animation: de-in 0.3s var(--ease-out-expo) both;
}

@keyframes de-in {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.de-header {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 10px 14px;
}

.de-icon {
  width: 36px; height: 36px; border-radius: 9px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 800; color: #fff; flex-shrink: 0;
}
.de-icon.docx { background: #2b579a; }
.de-icon.xlsx { background: #217346; }
.de-icon.pptx { background: #c43e1c; }
.de-icon.pdf { background: #b30b00; }

.de-title-wrap { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.de-title { font-size: 13.5px; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.de-kind { font-size: 11px; color: var(--text-muted); }

.de-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.de-btn {
  padding: 4px 10px; border-radius: var(--radius-pill, 999px);
  border: 1px solid var(--border); background: transparent;
  color: var(--text-secondary); font-size: 12px; font-weight: 600;
  font-family: inherit; cursor: pointer; text-decoration: none;
  transition: all var(--transition);
}
.de-btn:hover { border-color: var(--accent); color: var(--accent); }

.de-body { background: var(--bg, transparent); }

@media (max-width: 767px) {
  .doc-embed { max-width: 100%; }
  .de-kind { display: none; }
  .de-btn { padding: 4px 8px; }
}
</style>
