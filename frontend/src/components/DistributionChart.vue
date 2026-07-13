<template>
  <div ref="wrapperRef" class="distribution-chart-wrapper" :style="{ height: chartHeight + 'px' }">
    <div ref="chartRef" class="distribution-chart"></div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  // 标签列表 (y 轴)
  labels: { type: Array, default: () => [] },
  // 对比模式数据
  doubanValues: { type: Array, default: () => [] },
  imdbValues: { type: Array, default: () => [] },
  isCompare: { type: Boolean, default: false },
  // 单模式数据
  singleValues: { type: Array, default: () => [] },
  barColor: { type: String, default: '#1890ff' },
})

// ── 标准化配置 ──
const GRID_LEFT = 120
const GRID_RIGHT = 50
const BAR_WIDTH = 14
const BAR_GAP = '0'          // 双条形图同标签下两 bar 间距为 0
const BAR_CATEGORY_GAP = '40%'  // 不同标签之间的间距（单/双模式一致）
const LABEL_FONT_SIZE = 11
const AXIS_FONT_SIZE = 11
const LEGEND_FONT_SIZE = 11
const VALUE_LABEL_FONT_SIZE = 10

const chartHeight = computed(() => {
  return Math.max(280, props.labels.length * 32 + 60)
})

const wrapperRef = ref(null)
const chartRef = ref(null)
let chart = null
let ro = null

function renderChart() {
  if (!chartRef.value || !chart) return

  const labels = [...props.labels].reverse()
  const isCompare = props.isCompare

  if (isCompare) {
    const doubanValues = [...props.doubanValues].reverse()
    const imdbValues = [...props.imdbValues].reverse()
    chart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: {
        data: ['豆瓣', 'IMDb'],
        bottom: 0,
        textStyle: { fontSize: LEGEND_FONT_SIZE, color: '#71717a' },
      },
      grid: { left: GRID_LEFT, right: GRID_RIGHT, top: 10, bottom: 36 },
      xAxis: {
        type: 'value',
        axisLabel: { fontSize: AXIS_FONT_SIZE, color: '#71717a' },
        splitLine: { lineStyle: { color: '#f4f4f5' } },
      },
      yAxis: {
        type: 'category',
        data: labels,
        axisLabel: { fontSize: LABEL_FONT_SIZE, color: '#3f3f46', width: GRID_LEFT - 20, overflow: 'none' },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [
        {
          name: '豆瓣',
          type: 'bar',
          data: doubanValues,
          barWidth: BAR_WIDTH,
          barGap: BAR_GAP,
          barCategoryGap: BAR_CATEGORY_GAP,
          itemStyle: { color: '#1890ff', borderRadius: [0, 3, 3, 0] },
          label: { show: true, position: 'right', fontSize: VALUE_LABEL_FONT_SIZE, color: '#71717a' },
        },
        {
          name: 'IMDb',
          type: 'bar',
          data: imdbValues,
          barWidth: BAR_WIDTH,
          barCategoryGap: BAR_CATEGORY_GAP,
          itemStyle: { color: '#f5c518', borderRadius: [0, 3, 3, 0] },
          label: { show: true, position: 'right', fontSize: VALUE_LABEL_FONT_SIZE, color: '#71717a' },
        },
      ],
    }, true)
  } else {
    const values = [...props.singleValues].reverse()
    chart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: GRID_LEFT, right: GRID_RIGHT, top: 10, bottom: 10 },
      xAxis: {
        type: 'value',
        axisLabel: { fontSize: AXIS_FONT_SIZE, color: '#71717a' },
        splitLine: { lineStyle: { color: '#f4f4f5' } },
      },
      yAxis: {
        type: 'category',
        data: labels,
        axisLabel: { fontSize: LABEL_FONT_SIZE, color: '#3f3f46', width: GRID_LEFT - 20, overflow: 'none' },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [{
        type: 'bar',
        data: values,
        barWidth: BAR_WIDTH,
        barCategoryGap: BAR_CATEGORY_GAP,
        itemStyle: { color: props.barColor, borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', fontSize: VALUE_LABEL_FONT_SIZE, color: '#71717a' },
      }],
    }, true)
  }

  // 同步 resize 到当前容器尺寸
  chart.resize()
}

function initChart() {
  if (!chartRef.value) return
  if (chart) {
    chart.dispose()
  }
  chart = echarts.init(chartRef.value)
  renderChart()
}

// 当数据变化时重新渲染
watch(
  () => [props.labels, props.doubanValues, props.imdbValues, props.singleValues, props.isCompare, props.barColor],
  () => nextTick(() => renderChart()),
  { deep: true }
)

// 监听容器高度变化 → resize
onMounted(() => {
  nextTick(() => {
    initChart()
    if (wrapperRef.value) {
      ro = new ResizeObserver(() => {
        chart?.resize()
      })
      ro.observe(wrapperRef.value)
    }
  })
})

onBeforeUnmount(() => {
  ro?.disconnect()
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.distribution-chart-wrapper {
  width: 100%;
  transition: height 0.2s;
}
.distribution-chart {
  width: 100%;
  height: 100%;
}
</style>
