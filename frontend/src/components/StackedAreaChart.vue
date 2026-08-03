<template>
  <div class="stacked-area">
    <div v-if="!series || !series.length || !labels.length" class="chart-empty">
      <span class="empty-icon">area</span>
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

      <!-- 堆叠面积层 -->
      <g v-for="(layer, idx) in layers" :key="`layer-${idx}`" class="area-layer">
        <polygon
          :points="areaPoints(idx)"
          :fill="layer.color"
          fill-opacity="0.55"
          stroke="none"
        />
        <polyline
          :points="linePoints(idx)"
          fill="none"
          :stroke="layer.color"
          stroke-width="1.8"
          stroke-linejoin="round"
        />
      </g>
    </svg>

    <!-- 图例 -->
    <div class="chart-legend">
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
  labels: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },  // [{ name, data: [], color }] 从下往上堆叠
  height: { type: Number, default: 280 },
})

const width = 720
const padding = { top: 20, right: 24, bottom: 50, left: 56 }
const colors = ['#6366f1', '#22c55e', '#f59e0b', '#ec4899']

const chartTop = padding.top
const chartHeight = computed(() => props.height - padding.top - padding.bottom - 20)

// 每个数据点的堆叠总值
const stackedTotals = computed(() => {
  const n = props.labels.length
  const totals = new Array(n).fill(0)
  props.series.forEach(s => {
    (s.data || []).forEach((v, i) => {
      if (i < n) totals[i] += Number(v) || 0
    })
  })
  return totals
})

const maxY = computed(() => {
  const max = Math.max(...(stackedTotals.value.length ? stackedTotals.value : [1]), 1)
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
  const step = Math.ceil(props.labels.length / 8)
  return props.labels.map((l, i) => (i % step === 0 ? l : ''))
})

const labelRotate = computed(() => props.labels.length > 10)

// 计算每一层的累计值（从下往上堆叠：第一层是 series[0]，第二层是 series[0]+series[1]...）
const layers = computed(() => {
  const n = props.labels.length
  const cumulative = new Array(n).fill(0)
  return props.series.map((s, idx) => {
    const data = []
    for (let i = 0; i < n; i++) {
      cumulative[i] += Number((s.data || [])[i]) || 0
      data.push(cumulative[i])
    }
    return {
      name: s.name,
      data,
      color: s.color || colors[idx % colors.length],
      isBottom: idx === 0,
    }
  })
})

function getX(i) {
  if (props.labels.length === 1) return padding.left + (width - padding.left - padding.right) / 2
  const inner = width - padding.left - padding.right
  return padding.left + (inner / (props.labels.length - 1)) * i
}

function getY(v) {
  const val = Number(v) || 0
  return chartTop + chartHeight.value * (1 - val / (maxY.value || 1))
}

// 每层的上边界折线
function linePoints(idx) {
  const layer = layers.value[idx]
  if (!layer) return ''
  return layer.data.map((v, i) => `${getX(i)},${getY(v)}`).join(' ')
}

// 闭合多边形：上边界 + 下边界（前一层的上边界或底部）
function areaPoints(idx) {
  const layer = layers.value[idx]
  if (!layer) return ''
  const top = layer.data.map((v, i) => `${getX(i)},${getY(v)}`)
  // 下边界：前一层的上边界（如果存在），否则是 x 轴底部
  const bottom = []
  if (idx > 0) {
    const prev = layers.value[idx - 1]
    for (let i = prev.data.length - 1; i >= 0; i--) {
      bottom.push(`${getX(i)},${getY(prev.data[i])}`)
    }
  } else {
    // 底层：下边界是 x 轴
    for (let i = props.labels.length - 1; i >= 0; i--) {
      bottom.push(`${getX(i)},${chartTop + chartHeight.value}`)
    }
  }
  return [...top, ...bottom].join(' ')
}

function formatTick(v) {
  if (v >= 1000) return (v / 1000).toFixed(v >= 10000 ? 0 : 1) + 'k'
  return Math.round(v)
}
</script>

<style scoped>
.stacked-area {
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
