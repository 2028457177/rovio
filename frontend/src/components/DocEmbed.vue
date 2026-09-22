<template>
  <div class="doc-embed" @click="emit('open', embed)">
    <span class="de-icon" :class="embed.kind">{{ icon }}</span>
    <div class="de-title-wrap">
      <span class="de-title">{{ embed.title }}</span>
      <span class="de-kind">{{ kindLabel }}</span>
    </div>
    <span class="de-open">查看
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="9 18 15 12 9 6"></polyline>
      </svg>
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  embed: { type: Object, required: true } // {kind, title, preview_url, download_url}
})
const emit = defineEmits(['open'])

const ICONS = { docx: 'W', xlsx: 'X', pptx: 'P', pdf: 'F' }
const LABELS = { docx: 'Word', xlsx: 'Excel', pptx: 'PPT', pdf: 'PDF' }
const icon = computed(() => ICONS[props.embed.kind] || '?')
const kindLabel = computed(() => LABELS[props.embed.kind] || props.embed.kind)
</script>

<style scoped>
.doc-embed {
  display: flex;
  align-items: center;
  gap: 11px;
  margin: 8px 0 4px;
  max-width: 440px;
  padding: 10px 14px;
  border: 1px solid var(--border-light);
  border-radius: 12px;
  background: var(--panel);
  cursor: pointer;
  transition: border-color var(--transition), background var(--transition), transform var(--spring-fast), box-shadow var(--transition);
  animation: de-in 0.3s var(--ease-out-expo) both;
}

.doc-embed:hover {
  border-color: rgba(var(--accent-rgb), 0.5);
  background: var(--accent-light, rgba(var(--accent-rgb), 0.06));
  transform: translateY(-1px);
  box-shadow: 0 5px 18px var(--shadow-sm);
}

@keyframes de-in {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
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

.de-open {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12.5px; font-weight: 600; color: var(--accent);
  flex-shrink: 0;
}

@media (max-width: 767px) {
  .doc-embed { max-width: 100%; }
  .de-kind { display: none; }
}
</style>
