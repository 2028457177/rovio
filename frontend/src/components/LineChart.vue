<template>
  <div class="line-chart">
    <div v-if="!series || !series.length || !labels.length" class="chart-empty">
      <span class="empty-icon">chart</span>
      <span>暂无数据</span>
    </div>
    <svg v-else :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="xMidYMid meet" class="chart-svg">
      <!-- 网格线 -->
      <g class="grid">
        <line v-for="i in 5" :key="`h-${i}`"
          :x1="padding.left" :x2="width - padding.right"
          :y1="chartTop + (chartHeight / 4) * (i - 1)"
          :y2="chartTop + (chartHeight / 4) * (i - 1)"
          stroke="var(--border-light)" stroke-width="1" stroke-dasharray="3 4" opacity="0.6" />
      </g>

      <!-- Y 轴刻度 -->
      <g class="y-axis">
        <text v-for="(val, i) in yTicks" :key="`yt-${i}`"
          :x="padding.left - 8" :y="chartTop + (chartHeight / 4) * i + 4"
          text-anchor="end" font-size="11" fill="var(--text-muted)">
          {{ formatTick(val) }}
        </text>
      </g>

      <!-- X 轴标签 -->
      <g class="x-axis">
        <text v-for="(label, i) in xLabels" :key="`xt-${i}`"
          :x="getX(i)" :y="height - padding.bottom + 18"
          text-anchor="middle" font-size="11" fill="var(--text-muted)"
          :transform="labelRotate ? `rotate(-45, ${getX(i)}, ${height - padding.bottom + 18})` : ''">
          {{ label }}
        </text>
      </g>

      <!-- 折线 -->
      <g v-for="(s, si) in series" :key="`s-${si}`" class="series">
        <polyline
          :points="points(si)"
          fill="none"
          :stroke="s.color || colors[si % colors.length]"
          stroke-width="2.2"
          stroke-linejoin="round"
          stroke-linecap="round"
        />
        <!-- 数据点 -->
        <circle v-for="(v, i) in s.data" :key="`p-${si}-${i}`"
          :cx="getX(i)" :cy="getY(v)"
          r="3"
          :fill="s.color || colors[si % colors.length]"
        />
      </g>
    </svg>

    <!-- 图例 -->
    <div v-if="series.length > 1" class="chart-legend">
      <div v-for="(s, i) in series" :key="`lg-${i}`" class="legend-item">
        <span class="legend-dot" :style="{ background: s.color || colors[i % colors.length] }"></span>
        <span class="legend-label">{{ s.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  labels: { type: Array, default: () => [] },        // x 轴标签
  series: { type: Array, default: () => [] },         // [{ name, data: [], color }]
  yMax: { type: Number, default: null },              // 自定义 y 轴最大值
  height: { type: Number, default: 280 },
})

const width = 720
const padding = { top: 20, right: 24, bottom: 50, left: 56 }
const colors = ['#6366f1', '#22c55e', '#f59e0b', '#ec4899']

const chartTop = padding.top
const chartHeight = computed(() => props.height - padding.top - padding.bottom - 20)

const allData = computed(() => {
  const all = []
  props.series.forEach(s => (s.data || []).forEach(v => all.push(Number(v) || 0)))
  return all
})

const maxY = computed(() => {
  if (props.yMax) return props.yMax
  const max = Math.max(...(allData.value.length ? allData.value : [1]), 1)
  // 向上取整到合理刻度
  const mag = Math.pow(10, Math.floor(Math.log10(max)))
  const norm = max / mag
  let nice = 1
  if (norm > 5) nice = 10
  else if (norm > 2) nice = 5
  else if (norm > 1) nice = 2
  return nice * mag
})

const yTicks = computed(() => {
  const m = maxY.value
  return [m, m * 0.75, m * 0.5, m * 0.25, 0]
})

const xLabels = computed(() => {
  if (props.labels.length <= 8) return props.labels
  // 太密则抽样显示
  const step = Math.ceil(props.labels.length / 8)
  return props.labels.map((l, i) => (i % step === 0 ? l : ''))
})

const labelRotate = computed(() => props.labels.length > 10)

function getX(i) {
  if (props.labels.length === 1) return padding.left + (width - padding.left - padding.right) / 2
  const inner = width - padding.left - padding.right
  return padding.left + (inner / (props.labels.length - 1)) * i
}

function getY(v) {
  const val = Number(v) || 0
  return chartTop + chartHeight.value * (1 - val / (maxY.value || 1))
}

function points(si) {
  const s = props.series[si]
  if (!s || !s.data) return ''
  return s.data.map((v, i) => `${getX(i)},${getY(v)}`).join(' ')
}

function formatTick(v) {
  if (v >= 1000) return (v / 1000).toFixed(v >= 10000 ? 0 : 1) + 'k'
  return Math.round(v)
}
</script>

<style scoped>
.line-chart {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chart-svg {
  width: 100%;
  height: auto;
  display: block;
}

.chart-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: 13px;
  padding: 32px 0;
}

.empty-icon {
  font-size: 24px;
  opacity: 0.4;
}

.chart-legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  padding: 4px 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
</style>
