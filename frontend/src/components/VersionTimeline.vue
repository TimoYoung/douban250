<template>
  <div
    class="version-timeline"
    :style="{ '--bar-color': barColor }"
    tabindex="0"
    ref="timelineRef"
    @keydown="onKeydown"
  >
    <!-- Stepper row -->
    <div class="tl-stepper">
      <button
        class="tl-step-btn"
        :disabled="currentIndex <= 0"
        @click="step(-1)"
        title="上一版本 (←)"
      >◄</button>

      <div class="tl-current">
        <span class="tl-tag">{{ currentVersion?.tag || '-' }}</span>
        <span class="tl-count">({{ currentVersion?.movie_count || 0 }} 部)</span>
        <span class="tl-index" v-if="sortedVersions.length">{{ currentIndex + 1 }}/{{ sortedVersions.length }}</span>
      </div>

      <button
        class="tl-step-btn"
        :disabled="currentIndex >= sortedVersions.length - 1"
        @click="step(1)"
        title="下一版本 (→)"
      >►</button>
    </div>

    <!-- Minimap bar -->
    <div class="tl-minimap-wrap"
      @mousemove="onMinimapMove"
      @mouseleave="onMinimapLeave"
      @click="onMinimapClick"
    >
      <canvas ref="canvasRef" class="tl-minimap"></canvas>
      <!-- Position indicator -->
      <div
        class="tl-indicator"
        :style="{ left: indicatorLeft + 'px' }"
        v-if="sortedVersions.length"
      ></div>
      <!-- Hover tooltip -->
      <div
        v-if="hoverVersion"
        class="tl-tooltip"
        :style="{ left: hoverX + 'px' }"
      >{{ hoverVersion.tag }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'

const props = defineProps({
  versions: { type: Array, default: () => [] },
  modelValue: { type: Number, default: null },
  barColor: { type: String, default: '#6366f1' },
})
const emit = defineEmits(['update:modelValue'])

const timelineRef = ref(null)
const canvasRef = ref(null)
const hoverVersion = ref(null)
const hoverX = ref(0)

let resizeObserver = null

onMounted(() => {
  drawMinimap()
  resizeObserver = new ResizeObserver(() => {
    drawMinimap()
  })
  if (timelineRef.value) resizeObserver.observe(timelineRef.value)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})

// Sort versions by tag (ascending)
const sortedVersions = computed(() =>
  [...props.versions].sort((a, b) => a.tag.localeCompare(b.tag))
)

const currentIndex = computed(() =>
  sortedVersions.value.findIndex(v => v.id === props.modelValue)
)

const currentVersion = computed(() =>
  sortedVersions.value[currentIndex.value] || null
)

// 从 tag 提取日期时间戳（tag 格式: "2025-07-10" 或 "2025-07-10-2"）
// 不使用 crawled_at：抓取时间和版本时间不是正相关关系，会导致指示线跳跃
function tagToTs(tag) {
  return new Date(tag.substring(0, 10)).getTime()
}

// Time range (shared between indicator, heatmap, click-to-jump)
const timeRange = computed(() => {
  const versions = sortedVersions.value
  if (!versions.length) return { min: 0, max: 0, span: 1 }
  const timestamps = versions.map(v => tagToTs(v.tag))
  const min = Math.min(...timestamps)
  const max = Math.max(...timestamps)
  return { min, max, span: max - min || 1 }
})

// Convert timestamp → x pixel (linear time, same as heatmap bins)
function tsToX(ts, width) {
  const { min, span } = timeRange.value
  return ((ts - min) / span) * (width - 4) + 2
}

// Convert x pixel → nearest version index
function xToIndex(x, width) {
  const versions = sortedVersions.value
  if (!versions.length) return -1
  if (versions.length === 1) return 0

  const { min, span } = timeRange.value
  const targetTs = (x - 2) / (width - 4) * span + min

  // 线性扫描找时间戳最近的版本
  let best = 0
  let bestDist = Infinity
  for (let i = 0; i < versions.length; i++) {
    const ts = tagToTs(versions[i].tag)
    const dist = Math.abs(ts - targetTs)
    if (dist < bestDist) {
      bestDist = dist
      best = i
    }
  }
  return best
}

// Indicator position (time-based, consistent with heatmap)
const indicatorLeft = computed(() => {
  if (!canvasRef.value || !currentVersion.value) return 0
  const width = canvasRef.value.offsetWidth
  const ts = tagToTs(currentVersion.value.tag)
  return tsToX(ts, width)
})

// Draw minimap density heatmap
function drawMinimap() {
  const canvas = canvasRef.value
  if (!canvas) return

  const versions = sortedVersions.value
  if (!versions.length) return

  const dpr = window.devicePixelRatio || 1
  const rect = canvas.getBoundingClientRect()
  const width = rect.width
  const height = rect.height

  canvas.width = width * dpr
  canvas.height = height * dpr
  const ctx = canvas.getContext('2d')
  ctx.scale(dpr, dpr)
  ctx.clearRect(0, 0, width, height)

  // Background
  ctx.fillStyle = '#f0f0f2'
  ctx.beginPath()
  ctx.roundRect(0, 0, width, height, 3)
  ctx.fill()

  if (versions.length < 2) return

  // Bin versions into pixel columns (using shared tsToX mapping)
  const bins = new Array(Math.ceil(width)).fill(0)
  for (const v of versions) {
    const ts = tagToTs(v.tag)
    const x = Math.round(tsToX(ts, width))
    bins[x] = (bins[x] || 0) + 1
  }

  const maxBin = Math.max(...bins, 1)

  // Draw density bars
  for (let x = 0; x < width; x++) {
    if (bins[x] === 0) continue
    const intensity = bins[x] / maxBin
    // Color: light purple → dark purple based on density
    const alpha = 0.15 + intensity * 0.6
    ctx.fillStyle = `rgba(99, 102, 241, ${alpha})`
    ctx.fillRect(x, 0, 1, height)
  }
}

// Redraw when versions change
watch(() => props.versions, () => {
  nextTick(() => drawMinimap())
})

// Minimap hover — find nearest version (time-based)
function onMinimapMove(e) {
  const canvas = canvasRef.value
  if (!canvas || !sortedVersions.value.length) return

  const rect = canvas.getBoundingClientRect()
  const x = e.clientX - rect.left
  const idx = xToIndex(x, rect.width)
  if (idx >= 0) {
    hoverVersion.value = sortedVersions.value[idx]
    hoverX.value = x
  }
}

function onMinimapLeave() {
  hoverVersion.value = null
}

// Minimap click — jump to nearest version (time-based)
function onMinimapClick(e) {
  const canvas = canvasRef.value
  if (!canvas || !sortedVersions.value.length) return

  const rect = canvas.getBoundingClientRect()
  const x = e.clientX - rect.left
  const idx = xToIndex(x, rect.width)
  if (idx >= 0) {
    selectVersion(sortedVersions.value[idx].id)
  }
}

function selectVersion(id) {
  emit('update:modelValue', id)
}

function step(delta) {
  const idx = currentIndex.value
  const newIdx = idx + delta
  if (newIdx >= 0 && newIdx < sortedVersions.value.length) {
    selectVersion(sortedVersions.value[newIdx].id)
  }
}

function onKeydown(e) {
  if (e.key === 'ArrowLeft') {
    e.preventDefault()
    step(-1)
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    step(1)
  } else if (e.key === 'Home') {
    e.preventDefault()
    if (sortedVersions.value.length) selectVersion(sortedVersions.value[0].id)
  } else if (e.key === 'End') {
    e.preventDefault()
    if (sortedVersions.value.length) selectVersion(sortedVersions.value[sortedVersions.value.length - 1].id)
  }
}
</script>

<style scoped>
.version-timeline {
  outline: none;
  padding: 4px 0;
  border-radius: 8px;
  transition: box-shadow 0.15s;
}

.version-timeline:focus-visible {
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

/* Stepper */
.tl-stepper {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.tl-step-btn {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border: 1px solid #e4e4e7;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 11px;
  color: #71717a;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  padding: 0;
}

.tl-step-btn:hover:not(:disabled) {
  background: #f4f4f5;
  border-color: #a1a1aa;
  color: #3f3f46;
}

.tl-step-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.tl-current {
  flex: 1;
  text-align: center;
  cursor: default;
  min-width: 0;
}

.tl-tag {
  font-size: 14px;
  font-weight: 600;
  color: #27272a;
  font-family: 'SF Mono', monospace;
}

.tl-count {
  color: #a1a1aa;
  font-size: 11px;
  margin-left: 4px;
}

.tl-index {
  color: #d4d4d8;
  font-size: 10px;
  margin-left: 6px;
  font-family: 'SF Mono', monospace;
}

/* Minimap */
.tl-minimap-wrap {
  position: relative;
  height: 10px;
  cursor: pointer;
}

.tl-minimap {
  width: 100%;
  height: 100%;
  display: block;
  border-radius: 3px;
}

.tl-indicator {
  position: absolute;
  top: -1px;
  width: 3px;
  height: 12px;
  background: var(--bar-color, #6366f1);
  border-radius: 2px;
  transform: translateX(-50%);
  pointer-events: none;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.8);
  transition: left 0.15s ease;
}

.tl-tooltip {
  position: absolute;
  bottom: calc(100% + 6px);
  transform: translateX(-50%);
  background: #27272a;
  color: #fff;
  font-size: 10px;
  font-family: 'SF Mono', monospace;
  padding: 3px 6px;
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;
  z-index: 10;
}

.tl-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-top-color: #27272a;
}
</style>
