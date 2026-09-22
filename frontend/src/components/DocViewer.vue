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

            <!-- 内容区：大尺寸阅读视图（渲染逻辑见 DocPreviewContent） -->
            <div class="dv-body">
              <DocPreviewContent v-if="modelValue" :doc="doc" />
            </div>
          </aside>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import DocPreviewContent from './DocPreviewContent.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  doc: { type: Object, required: true } // {kind, title, preview_url, download_url}
})
const emit = defineEmits(['update:modelValue'])

const ICONS = { docx: 'W', xlsx: 'X', pptx: 'P', pdf: 'F' }
const LABELS = { docx: 'Word 文档', xlsx: 'Excel 表格', pptx: 'PPT 幻灯片', pdf: 'PDF 文档' }
const icon = computed(() => ICONS[props.doc.kind] || '?')
const kindLabel = computed(() => LABELS[props.doc.kind] || props.doc.kind)

function close() {
  emit('update:modelValue', false)
}

function onKeydown(e) {
  if (e.key === 'Escape' && props.modelValue) close()
}

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

/* 动画 */
.dv-fade-enter-active, .dv-fade-leave-active { transition: opacity 0.3s ease; }
.dv-fade-enter-from, .dv-fade-leave-to { opacity: 0; }
.dv-slide-enter-active, .dv-slide-leave-active { transition: transform 0.38s var(--ease-out-expo, cubic-bezier(0.16, 1, 0.3, 1)); }
.dv-slide-enter-from, .dv-slide-leave-to { transform: translateX(-100%); }

@media (max-width: 767px) {
  .dv-panel { width: 100vw; max-width: 100vw; }
  .dv-kind { display: none; }
}
</style>
