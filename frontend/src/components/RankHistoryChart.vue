<template>
  <div class="rank-charts">
    <div v-for="s in sources" :key="s" class="rank-chart-wrapper">
      <div class="rank-chart" :ref="el => chartRefs[s] = el"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  history: { type: Array, default: () => [] },
})

const SOURCE_COLORS = {
  douban: '#1890ff',
  imdb: '#f5c518',
}
const SOURCE_LABELS = {
  douban: '豆瓣',
  imdb: 'IMDb',
}

const chartRefs = ref({})
const charts = {}

const sources = computed(() => {
  return [...new Set(props.history.map(h => h.source || 'douban'))]
})

function formatDate(ts) {
  const d = new Date(ts)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function initCharts() {
  if (!props.history.length) return

  for (const source of sources.value) {
    const el = chartRefs.value[source]
    if (!el) continue

    if (charts[source]) charts[source].dispose()
    const chart = echarts.init(el)
    charts[source] = chart

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
    const isDense = items.length > 15
    const veryDense = items.length > 30

    const series = [{
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
        show: !isDense,
        position: 'top',
        formatter: (p) => p.value?.[1] != null ? `#${p.value[1]}` : '',
        fontSize: 11,
        color: '#333',
      },
    }]

    if (droppedData.length > 0) {
      series.push({
        name: `${label} 脱榜`,
        type: 'scatter',
        data: droppedData,
        symbol: 'diamond',
        symbolSize: veryDense ? 6 : isDense ? 8 : 12,
        itemStyle: { color: '#ff4d4f' },
        label: {
          show: !isDense,
          position: 'top',
          formatter: '未上榜',
          fontSize: 11,
          color: '#ff4d4f',
          fontWeight: 'bold',
        },
      })
    }

    chart.setOption({
      title: { text: `${label}排名历史`, left: 'center' },
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          if (!params.length) return ''
          const p = params.find(p => p.value != null && p.value[1] != null) || params[0]
          if (!p) return ''
          const date = formatDate(p.value[0])
          if (p.value[1] === 251) return `${date}<br/>未上榜`
          return `${date}<br/>排名: #${p.value[1]}`
        },
      },
      dataZoom: [
        {
          type: 'slider',
          start: 0,
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
          start: 0,
          end: 100,
          zoomOnMouseWheel: false,
          pinchZoom: false,
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
      grid: { left: 60, right: 30, bottom: isDense ? 80 : 60, top: 50 },
    })
  }
}

function handleResize() {
  for (const key in charts) {
    charts[key]?.resize()
  }
}

onMounted(() => {
  initCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  for (const key in charts) {
    charts[key]?.dispose()
  }
})

watch(() => props.history, initCharts, { deep: true })
</script>

<style scoped>
.rank-charts {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rank-chart-wrapper {
  background: #fff;
  border: 1px solid rgba(228, 228, 231, 0.6);
  border-radius: 12px;
  overflow: hidden;
}

.rank-chart {
  width: 100%;
  height: 360px;
}
</style>
