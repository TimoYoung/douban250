<template>
  <div class="rank-chart" ref="chartRef"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  history: { type: Array, default: () => [] },
})

const chartRef = ref(null)
let chart = null

function initChart() {
  if (!chartRef.value || !props.history.length) return

  if (chart) chart.dispose()
  chart = echarts.init(chartRef.value)

  const tags = props.history.map(h => h.tag)

  // For display: use rank value, or null for dropped versions
  const ranks = props.history.map(h => h.dropped ? null : h.rank)

  // For dropped markers: use 251 (below chart) to show a marker
  const droppedData = props.history.map(h => h.dropped ? 251 : null)

  chart.setOption({
    title: { text: '排名历史', left: 'center' },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const tag = params[0].name
        const item = props.history.find(h => h.tag === tag)
        if (item?.dropped) {
          return `${tag}<br/>未上榜`
        }
        const rank = params[0]?.value ?? params[1]?.value
        return `${tag}<br/>排名: #${rank}`
      },
    },
    xAxis: {
      type: 'category',
      data: tags,
      axisLabel: { rotate: 30 },
    },
    yAxis: {
      type: 'value',
      inverse: true,
      min: 1,
      max: 260,
      name: '排名',
      axisLabel: {
        formatter: (v) => v <= 250 ? `#${v}` : '',
      },
    },
    series: [
      // Main rank line
      {
        name: '排名',
        type: 'line',
        data: ranks,
        connectNulls: false,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { width: 2, color: '#1890ff' },
        itemStyle: { color: '#1890ff' },
        label: {
          show: true,
          position: 'top',
          formatter: (p) => p.value != null ? `#${p.value}` : '',
          fontSize: 11,
          color: '#333',
        },
      },
      // Dropped marker
      {
        name: '掉出榜单',
        type: 'scatter',
        data: droppedData,
        symbol: 'diamond',
        symbolSize: 12,
        itemStyle: { color: '#ff4d4f' },
        label: {
          show: true,
          position: 'top',
          formatter: '未上榜',
          fontSize: 11,
          color: '#ff4d4f',
          fontWeight: 'bold',
        },
      },
    ],
    grid: { left: 60, right: 30, bottom: 60, top: 50 },
  })
}

function handleResize() {
  chart?.resize()
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})

watch(() => props.history, initChart, { deep: true })
</script>

<style scoped>
.rank-chart {
  width: 100%;
  height: 400px;
}
</style>
