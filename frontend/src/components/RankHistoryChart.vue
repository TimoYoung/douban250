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

const SOURCE_COLORS = {
  douban: '#1890ff',
  imdb: '#f5c518',
}
const SOURCE_LABELS = {
  douban: '豆瓣',
  imdb: 'IMDb',
}

function formatDate(ts) {
  const d = new Date(ts)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function initChart() {
  if (!chartRef.value || !props.history.length) return

  if (chart) chart.dispose()
  chart = echarts.init(chartRef.value)

  const sources = [...new Set(props.history.map(h => h.source || 'douban'))]
  const isDense = props.history.length > 15
  const veryDense = props.history.length > 30

  const series = []

  for (const source of sources) {
    const items = props.history.filter(h => (h.source || 'douban') === source)
    const rankData = []
    const droppedData = []

    for (const h of items) {
      const ts = new Date(h.tag).getTime()
      if (h.dropped) {
        rankData.push([ts, null])
        droppedData.push([ts, 251])
      } else {
        rankData.push([ts, h.rank])
      }
    }

    const color = SOURCE_COLORS[source] || '#999'
    const label = SOURCE_LABELS[source] || source

    series.push({
      name: label,
      type: 'line',
      data: rankData,
      connectNulls: false,
      smooth: true,
      symbol: 'circle',
      symbolSize: veryDense ? 3 : isDense ? 4 : 8,
      lineStyle: { width: 2, color },
      itemStyle: { color },
      label: {
        show: !isDense && sources.length === 1,
        position: 'top',
        formatter: (p) => p.value?.[1] != null ? `#${p.value[1]}` : '',
        fontSize: 11,
        color: '#333',
      },
    })

    if (droppedData.length > 0) {
      series.push({
        name: `${label} 脱榜`,
        type: 'scatter',
        data: droppedData,
        symbol: 'diamond',
        symbolSize: veryDense ? 6 : isDense ? 8 : 12,
        itemStyle: { color: '#ff4d4f' },
        label: {
          show: !isDense && sources.length === 1,
          position: 'top',
          formatter: '未上榜',
          fontSize: 11,
          color: '#ff4d4f',
          fontWeight: 'bold',
        },
      })
    }
  }

  const startPercent = isDense ? Math.max(0, (1 - 12 / props.history.length) * 100) : 0

  chart.setOption({
    title: { text: '排名历史', left: 'center' },
    legend: {
      show: sources.length > 1,
      top: 30,
      data: sources.map(s => SOURCE_LABELS[s] || s),
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        if (!params.length) return ''
        const p = params.find(p => p.value != null && p.value[1] != null) || params[0]
        if (!p) return ''
        const date = formatDate(p.value[0])
        const seriesName = p.seriesName || ''
        if (p.value[1] === 251) {
          return `${date} (${seriesName})<br/>未上榜`
        }
        return `${date} (${seriesName})<br/>排名: #${p.value[1]}`
      },
    },
    dataZoom: [
      {
        type: 'slider',
        start: startPercent,
        end: 100,
        bottom: 10,
        height: 20,
        borderColor: '#e4e4e7',
        fillerColor: 'rgba(99,102,241,0.08)',
        handleStyle: { color: '#6366f1' },
        show: isDense,
      },
      {
        type: 'inside',
        start: startPercent,
        end: 100,
        minSpan: Math.max(10, Math.min(50, (12 / props.history.length) * 100)),
        maxSpan: 100,
        zoomOnMouseWheel: false,
      },
    ],
    xAxis: {
      type: 'time',
      axisLabel: {
        rotate: 30,
        formatter: (value) => formatDate(value),
      },
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
    series,
    grid: { left: 60, right: 30, bottom: isDense ? 80 : 60, top: sources.length > 1 ? 60 : 50 },
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
