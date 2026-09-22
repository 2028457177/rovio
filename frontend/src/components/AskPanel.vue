<template>
  <div class="ask-panel" :class="{ answered: question.answered }">
    <!-- 标题条 -->
    <div class="ask-header">
      <span class="ask-icon">?</span>
      <span class="ask-title">{{ question.header || '补充信息' }}</span>
      <span v-if="!question.answered" class="ask-hint">选择后我会继续</span>
      <span v-else class="ask-done">已回答</span>
    </div>

    <!-- 问题 -->
    <div class="ask-question">{{ question.question }}</div>

    <!-- 已回答态：只显示选择结果 -->
    <template v-if="question.answered">
      <div class="ask-selected">你的选择：{{ question.selected }}</div>
    </template>

    <!-- 待回答态 -->
    <template v-else>
      <!-- 选项列表 -->
      <div v-if="options.length" class="ask-options">
        <button
          v-for="opt in options"
          :key="opt.label"
          type="button"
          class="ask-option"
          :class="{ checked: multiMode && checkedSet.has(opt.label) }"
          @click="onPick(opt)"
        >
          <span v-if="multiMode" class="ask-check" :class="{ on: checkedSet.has(opt.label) }"></span>
          <span class="ask-option-body">
            <span class="ask-option-label">{{ opt.label }}</span>
            <span v-if="opt.description" class="ask-option-desc">{{ opt.description }}</span>
          </span>
        </button>
        <button
          v-if="multiMode"
          type="button"
          class="ask-confirm"
          :disabled="!checkedSet.size"
          @click="onConfirmMulti"
        >确认选择（{{ checkedSet.size }}）</button>
      </div>

      <!-- 自由输入 -->
      <div v-else class="ask-free">
        <input
          v-model="freeText"
          class="ask-input"
          placeholder="输入你的回答…"
          maxlength="200"
          @keydown.enter="onFreeSubmit"
        />
        <button type="button" class="ask-confirm" :disabled="!freeText.trim()" @click="onFreeSubmit">发送</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  question: { type: Object, required: true } // {question_id, question, options, header, multi_select, answered, selected}
})

const emit = defineEmits(['answer'])

const options = computed(() => {
  const raw = Array.isArray(props.question.options) ? props.question.options : []
  return raw.filter(o => o && o.label).slice(0, 4)
})

const multiMode = computed(() => !!props.question.multi_select && options.value.length > 1)
const checkedSet = ref(new Set())
const freeText = ref('')

function toggleCheck(label) {
  const next = new Set(checkedSet.value)
  if (next.has(label)) next.delete(label)
  else next.add(label)
  checkedSet.value = next
}

function onPick(opt) {
  if (multiMode.value) {
    toggleCheck(opt.label)
    return
  }
  emit('answer', opt.label)
}

function onConfirmMulti() {
  if (!checkedSet.value.size) return
  emit('answer', Array.from(checkedSet.value).join('、'))
}

function onFreeSubmit() {
  const text = freeText.value.trim()
  if (!text) return
  emit('answer', text)
}
</script>

<style scoped>
.ask-panel {
  margin: 10px 0 4px;
  max-width: 480px;
  border: 1px solid rgba(var(--accent-rgb), 0.35);
  border-radius: 14px;
  background: rgba(var(--accent-rgb), 0.045);
  overflow: hidden;
  animation: ask-in 0.35s var(--ease-out-expo) both;
}

@keyframes ask-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.ask-panel.answered {
  border-color: var(--border-light);
  background: var(--panel);
  opacity: 0.85;
}

.ask-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px 0;
}

.ask-icon {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--accent);
  color: var(--accent-contrast);
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ask-title {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--accent);
  text-transform: uppercase;
}

.ask-hint {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
}

.ask-done {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.ask-done::before {
  content: '✓';
  color: var(--accent);
  font-weight: 800;
}

.ask-question {
  padding: 8px 14px 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.6;
}

.ask-options {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 0 12px 12px;
}

.ask-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  text-align: left;
  padding: 9px 12px;
  border: 1px solid var(--border-light);
  border-radius: 10px;
  background: var(--panel);
  cursor: pointer;
  font-family: inherit;
  transition: border-color var(--transition), background var(--transition), transform var(--spring-fast);
}

.ask-option:hover:not(:disabled) {
  border-color: rgba(var(--accent-rgb), 0.55);
  background: var(--accent-light, rgba(var(--accent-rgb), 0.07));
  transform: translateY(-1px);
}

.ask-option.checked {
  border-color: var(--accent);
  background: rgba(var(--accent-rgb), 0.09);
}

.ask-check {
  width: 16px;
  height: 16px;
  border-radius: 5px;
  border: 1.5px solid var(--border);
  flex-shrink: 0;
  margin-top: 2px;
  position: relative;
  transition: all var(--transition);
}

.ask-check.on {
  background: var(--accent);
  border-color: var(--accent);
}

.ask-check.on::after {
  content: '';
  position: absolute;
  left: 4.5px;
  top: 1.5px;
  width: 4px;
  height: 8px;
  border: solid var(--accent-contrast);
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.ask-option-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.ask-option-label {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text);
}

.ask-option-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.ask-confirm {
  align-self: flex-end;
  padding: 6px 16px;
  border-radius: var(--radius-pill, 999px);
  border: none;
  background: linear-gradient(180deg, var(--accent-hover), var(--accent));
  color: var(--accent-contrast);
  font-size: 12.5px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: filter var(--transition);
}

.ask-confirm:hover:not(:disabled) { filter: brightness(1.08); }

.ask-confirm:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ask-free {
  display: flex;
  gap: 8px;
  padding: 0 12px 12px;
}

.ask-input {
  flex: 1;
  min-width: 0;
  padding: 8px 12px;
  border: 1px solid var(--border-light);
  border-radius: 10px;
  background: var(--panel);
  color: var(--text);
  font-size: 13.5px;
  font-family: inherit;
  outline: none;
  transition: border-color var(--transition);
}

.ask-input:focus {
  border-color: rgba(var(--accent-rgb), 0.55);
}

.ask-selected {
  padding: 0 14px 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.ask-selected::before {
  content: '› ';
  color: var(--accent);
  font-weight: 700;
}

@media (max-width: 767px) {
  .ask-panel { max-width: 100%; }
}
</style>
