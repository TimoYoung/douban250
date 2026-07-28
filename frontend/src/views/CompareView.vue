<template>
  <div class="compare-view">
    <h2>版本对比</h2>

    <div class="compare-controls">
      <div class="selectors">
        <!-- Version A -->
        <div class="selector-group">
          <div class="selector-header">
            <span class="selector-label">版本A</span>
            <div class="source-toggle">
              <button :class="{ active: sourceA === 'douban' }" @click="setSourceA('douban')">豆瓣</button>
              <button :class="{ active: sourceA === 'imdb' }" @click="setSourceA('imdb')">IMDb</button>
            </div>
          </div>
          <VersionDropdown
            :versions="versionsAList"
            v-model="versionAId"
          />
        </div>

        <span class="vs-badge">VS</span>

        <!-- Version B -->
        <div class="selector-group">
          <div class="selector-header">
            <span class="selector-label">版本B</span>
            <div class="source-toggle">
              <button :class="{ active: usePrev }" @click="setPrev">上一版本</button>
              <button :class="{ active: !usePrev && sourceB === 'douban' }" @click="setSourceB('douban')">豆瓣</button>
              <button :class="{ active: !usePrev && sourceB === 'imdb' }" @click="setSourceB('imdb')">IMDb</button>
            </div>
          </div>
          <VersionDropdown
            :versions="usePrev ? versionsAList : versionsBList"
            v-model="effectiveBId"
            :disabled="usePrev"
          />
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中…</div>

    <template v-else-if="displayData">
      <!-- Comparison header -->
      <div class="compare-header" :class="displayData.same_source ? 'same-source' : 'cross-source'">
        <span class="ch-label">{{ sourceLabels[displayData.display_a.source] }}</span>
        <span class="ch-tag">{{ displayData.display_a.tag }}</span>
        <span class="ch-arrow">→</span>
        <span class="ch-label">{{ sourceLabels[displayData.display_b.source] }}</span>
        <span class="ch-tag">{{ displayData.display_b.tag }}</span>
        <span class="ch-hint">{{ displayData.same_source ? '同源时间对比' : '跨平台对比' }}</span>
      </div>

      <!-- Summary -->
      <div class="summary-bar">
        <span class="summary-item">
          <span class="dot dot-gray"></span>
          {{ displayData.same_source ? '未变' : '共同' }} <strong>{{ displayData.summary.common_count }}</strong> 部
        </span>
        <span class="summary-item">
          <span class="dot" :class="displayData.same_source ? 'dot-red' : 'dot-green'"></span>
          {{ displayData.labelOnlyA }} <strong>{{ displayData.summary.only_a_count }}</strong> 部
        </span>
        <span class="summary-item">
          <span class="dot" :class="displayData.same_source ? 'dot-green' : 'dot-amber'"></span>
          {{ displayData.labelOnlyB }} <strong>{{ displayData.summary.only_b_count }}</strong> 部
        </span>
      </div>

      <!-- Venn diagram (cross-platform only) -->
      <div class="section" v-if="rawData && isCrossPlatform">
        <div class="venn-bar">
          <VennDiagram
            :only-a="displayData.summary.only_a_count"
            :both="displayData.summary.common_count"
            :only-b="displayData.summary.only_b_count"
            :label-a="displayData.labelOnlyA"
            label-center="共同"
            :label-b="displayData.labelOnlyB"
          />
        </div>
      </div>

      <!-- Distribution stats (cross-platform only, moved right after Venn) -->
      <div class="section" v-if="isCrossPlatform && compareDistData">
        <div class="section-inner" style="padding: 16px 20px;">
          <div class="dist-header">
            <span class="section-title">📊 分布统计（两榜对比）</span>
            <div class="dist-tabs">
              <button :class="{ active: distTab === 'genres' }" @click="distTab = 'genres'">类型</button>
              <button :class="{ active: distTab === 'countries' }" @click="distTab = 'countries'">国家</button>
              <button :class="{ active: distTab === 'years' }" @click="distTab = 'years'">年代</button>
            </div>
          </div>
          <DistributionChart
            :labels="distChartLabels"
            :douban-values="distDoubanValues"
            :imdb-values="distImdbValues"
            :is-compare="true"
          />
        </div>
      </div>

      <!-- Only in display A -->
      <div class="section" v-if="displayData.display_only_a.length">
        <details open>
          <summary class="section-title">{{ displayData.labelOnlyA }}（{{ displayData.display_only_a.length }} 部）</summary>
          <div class="movie-chips">
            <span v-for="m in displayData.display_only_a" :key="m.movie_id"
              class="chip" :class="displayData.same_source ? 'chip-red' : 'chip-green'"
              @click="goDetail(m)">
              #{{ m.rank }} {{ m.title }}
            </span>
          </div>
        </details>
      </div>

      <!-- Only in display B -->
      <div class="section" v-if="displayData.display_only_b.length">
        <details open>
          <summary class="section-title">{{ displayData.labelOnlyB }}（{{ displayData.display_only_b.length }} 部）</summary>
          <div class="movie-chips">
            <span v-for="m in displayData.display_only_b" :key="m.movie_id"
              class="chip" :class="displayData.same_source ? 'chip-green' : 'chip-amber'"
              @click="goDetail(m)">
              #{{ m.rank }} {{ m.title }}
            </span>
          </div>
        </details>
      </div>

      <!-- Same-source: rank up top 10 -->
      <div class="section" v-if="displayData.same_source && displayData.rank_up.length">
        <details open>
          <summary class="section-title">排名上升 Top {{ Math.min(displayData.rank_up.length, 10) }}</summary>
          <table class="compare-table">
            <thead>
              <tr><th>电影</th><th>旧排名</th><th>新排名</th><th>变化</th></tr>
            </thead>
            <tbody>
              <tr v-for="m in displayData.rank_up" :key="m.movie_id" @click="goDetail(m)">
                <td class="col-title">{{ m.title }}</td>
                <td class="col-rank">#{{ m.display_rank_a }}</td>
                <td class="col-rank">#{{ m.display_rank_b }}</td>
                <td class="col-delta delta-up">▲{{ m.display_delta }}</td>
              </tr>
            </tbody>
          </table>
        </details>
      </div>

      <!-- Same-source: rank down top 10 -->
      <div class="section" v-if="displayData.same_source && displayData.rank_down.length">
        <details open>
          <summary class="section-title">排名下降 Top {{ Math.min(displayData.rank_down.length, 10) }}</summary>
          <table class="compare-table">
            <thead>
              <tr><th>电影</th><th>旧排名</th><th>新排名</th><th>变化</th></tr>
            </thead>
            <tbody>
              <tr v-for="m in displayData.rank_down" :key="m.movie_id" @click="goDetail(m)">
                <td class="col-title">{{ m.title }}</td>
                <td class="col-rank">#{{ m.display_rank_a }}</td>
                <td class="col-rank">#{{ m.display_rank_b }}</td>
                <td class="col-delta delta-down">▼{{ Math.abs(m.display_delta) }}</td>
              </tr>
            </tbody>
          </table>
        </details>
      </div>
    </template>

    <p v-else class="empty">请选择版本进行对比</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useVersionsStore } from '../stores/versions.js'
import { fetchCompare, fetchDistribution } from '../api/index.js'
import VersionDropdown from '../components/VersionDropdown.vue'
import DistributionChart from '../components/DistributionChart.vue'
import VennDiagram from '../components/VennDiagram.vue'
import { useDistributionChartData } from '../composables/useDistributionChartData.js'

const router = useRouter()
const route = useRoute()
const versionsStore = useVersionsStore()

const sourceLabels = { douban: '豆瓣', imdb: 'IMDb' }

const sourceA = ref(route.query.sourceA || 'douban')
const sourceB = ref(route.query.sourceB || 'douban')
const usePrev = ref(route.query.usePrev !== 'false')
const versionAId = ref(parseId(route.query.versionA))
const versionBId = ref(parseId(route.query.versionB))
const rawData = ref(null)
const loading = ref(false)

function parseId(val) {
  const n = Number(val)
  return Number.isFinite(n) && n > 0 ? n : null
}

// 同步状态到URL
function syncToUrl() {
  const query = {}
  if (sourceA.value !== 'douban') query.sourceA = sourceA.value
  if (!usePrev.value) {
    query.usePrev = 'false'
    if (sourceB.value !== 'douban') query.sourceB = sourceB.value
  }
  if (versionAId.value != null) query.versionA = versionAId.value
  if (versionBId.value != null && !usePrev.value) query.versionB = versionBId.value
  router.replace({ query })
}

// Flat version list filtered by source (tag descending)
const versionsAList = computed(() =>
  versionsStore.versions
    .filter(v => (v.source || 'douban') === sourceA.value)
    .sort((a, b) => b.tag.localeCompare(a.tag))
)
const versionsBList = computed(() =>
  versionsStore.versions
    .filter(v => (v.source || 'douban') === sourceB.value)
    .sort((a, b) => b.tag.localeCompare(a.tag))
)

// "上一版本" computed
const computedPrevId = computed(() => {
  if (versionAId.value == null) return null
  const sorted = versionsAList.value
  const idx = sorted.findIndex(v => v.id === versionAId.value)
  if (idx >= 0 && idx < sorted.length - 1) return sorted[idx + 1].id
  return null
})

// 版本B的有效ID：当usePrev为true时使用computedPrevId，否则使用versionBId
// 这是一个派生状态，避免了手动同步的复杂性
const effectiveBId = computed({
  get: () => usePrev.value ? computedPrevId.value : versionBId.value,
  // 只在非prev模式下允许写入，防止在prev模式下对effectiveBId的写入被静默忽略
  set: (val) => { if (!usePrev.value) versionBId.value = val }
})

// 状态变化时自动同步URL并加载对比数据
// usePrev 不需要显式监听，因为 effectiveBId 已依赖它，usePrev 变化时 effectiveBId 也会变化
watch([sourceA, sourceB, versionAId, effectiveBId], () => {
  syncToUrl()
  loadCompare()
})

function setSourceA(src) {
  sourceA.value = src
  versionAId.value = versionsAList.value.length ? versionsAList.value[0].id : null
}

function setSourceB(src) {
  usePrev.value = false
  sourceB.value = src
  versionBId.value = versionsBList.value.length ? versionsBList.value[0].id : null
}

function setPrev() {
  usePrev.value = true
}

onMounted(async () => {
  await versionsStore.loadVersions()

  if (versionAId.value == null) {
    versionAId.value = versionsAList.value.length ? versionsAList.value[0].id : null
  }

  if (!usePrev.value && versionBId.value == null) {
    versionBId.value = versionsBList.value.length ? versionsBList.value[0].id : null
  }

  loadCompare()
})

// Build display data with ordering logic
const displayData = computed(() => {
  if (!rawData.value) return null
  const d = rawData.value

  const va = d.version_a
  const vb = d.version_b
  const sameSource = d.same_source

  // Display ordering:
  // - Same source: earlier tag (date) first, later second
  // - Cross source: douban first, imdb second
  let displayA, displayB, swapped
  if (sameSource) {
    if (va.tag <= vb.tag) {
      displayA = va; displayB = vb; swapped = false
    } else {
      displayA = vb; displayB = va; swapped = true
    }
  } else {
    if ((va.source || 'douban') === 'douban') {
      displayA = va; displayB = vb; swapped = false
    } else {
      displayA = vb; displayB = va; swapped = true
    }
  }

  // Apply swap to lists
  const onlyA = swapped ? d.only_b : d.only_a
  const onlyB = swapped ? d.only_a : d.only_b
  const common = d.common.map(m => ({
    ...m,
    display_rank_a: swapped ? m.rank_b : m.rank_a,
    display_rank_b: swapped ? m.rank_a : m.rank_b,
    display_delta: swapped ? -m.delta : m.delta,
  }))

  const labelOnlyA = sameSource ? '移出' : `仅${sourceLabels[displayA.source]}`
  const labelOnlyB = sameSource ? '新增' : `仅${sourceLabels[displayB.source]}`

  // Rank up/down: for same source, use display ordering (earlier→later = positive delta = up)
  const rankUp = sameSource
    ? common.filter(m => m.display_delta > 0).sort((a, b) => b.display_delta - a.display_delta).slice(0, 10)
    : d.rank_up?.map(m => ({
        ...m,
        display_rank_a: swapped ? m.rank_b : m.rank_a,
        display_rank_b: swapped ? m.rank_a : m.rank_b,
        display_delta: swapped ? -m.delta : m.delta,
      })) || []
  const rankDown = sameSource
    ? common.filter(m => m.display_delta < 0).sort((a, b) => a.display_delta - b.display_delta).slice(0, 10)
    : d.rank_down?.map(m => ({
        ...m,
        display_rank_a: swapped ? m.rank_b : m.rank_a,
        display_rank_b: swapped ? m.rank_a : m.rank_b,
        display_delta: swapped ? -m.delta : m.delta,
      })) || []

  return {
    same_source: sameSource,
    display_a: displayA,
    display_b: displayB,
    display_only_a: onlyA,
    display_only_b: onlyB,
    rank_up: rankUp,
    rank_down: rankDown,
    labelOnlyA,
    labelOnlyB,
    summary: d.summary,
  }
})

async function loadCompare() {
  if (!versionAId.value || !effectiveBId.value) {
    rawData.value = null
    return
  }

  loading.value = true
  // Fix #2: 在新请求开始时立即清除旧的分布数据，防止过期数据在窗口期内显示
  compareDistData.value = null
  try {
    const { data: result } = await fetchCompare(versionAId.value, effectiveBId.value)
    rawData.value = result

    // Load distribution data when in cross-platform mode
    if (isCrossPlatform.value) {
      loadDistData()
    }
  } finally {
    loading.value = false
  }
}

// Cross-platform mode detection
const isCrossPlatform = computed(() => {
  if (!rawData.value) return false
  return !rawData.value.same_source
})

// 切换模式时清除旧的分布数据
watch(isCrossPlatform, (cross) => {
  if (!cross) compareDistData.value = null
})

// Distribution chart state
const distTab = ref('genres')
const compareDistData = ref(null)

// 分布图 chart computed（共享 composable，始终 compare 模式）
const {
  labels: distChartLabels,
  doubanValues: distDoubanValues,
  imdbValues: distImdbValues,
} = useDistributionChartData(
  compareDistData,
  distTab,
  true,
  '#1890ff'
)

// Fix #2: 分布请求计数器，防止过期响应覆盖新数据
let distRequestId = 0

async function loadDistData() {
  if (!rawData.value) return
  const myRequestId = ++distRequestId
  const va = rawData.value.version_a
  const vb = rawData.value.version_b
  try {
    // 从当前对比的版本中提取 tag，用于获取正确的分布数据
    const params = { limit: 0 }
    if (va?.source === 'douban') params.douban_tag = va.tag
    else if (vb?.source === 'douban') params.douban_tag = vb.tag
    if (va?.source === 'imdb') params.imdb_tag = va.tag
    else if (vb?.source === 'imdb') params.imdb_tag = vb.tag

    const { data } = await fetchDistribution('compare', params)
    // 丢弃过期请求的结果
    if (myRequestId !== distRequestId) return
    compareDistData.value = data
  } catch (e) {
    // 分布图加载失败时保持 compareDistData = null（section 隐藏），输出日志供排查
    console.warn('[CompareView] loadDistData failed:', e.message || e)
  }
}

function goDetail(movie) {
  if (movie.douban_id) {
    router.push(`/movies/${movie.douban_id}`)
  } else {
    router.push(`/movies/id/${movie.movie_id}`)
  }
}
</script>

<style scoped>
.compare-view h2 {
  margin-bottom: 16px;
  font-size: 22px;
  font-weight: 600;
  color: #18181b;
  letter-spacing: -0.3px;
}

.compare-controls {
  background: #fff;
  padding: 16px 20px;
  border-radius: 12px;
  border: 1px solid rgba(228, 228, 231, 0.6);
  margin-bottom: 20px;
}

.selectors {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}

.selector-group {
  flex: 1;
  min-width: 260px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.selector-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.selector-label {
  font-size: 12px;
  font-weight: 600;
  color: #71717a;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.source-toggle {
  display: flex;
  gap: 0;
}

.source-toggle button {
  padding: 3px 10px;
  border: 1px solid #e4e4e7;
  background: #fff;
  cursor: pointer;
  font-size: 11px;
  font-weight: 500;
  color: #71717a;
  transition: all 0.15s;
  font-family: inherit;
}

.source-toggle button:first-child { border-radius: 5px 0 0 5px; }
.source-toggle button:last-child { border-radius: 0 5px 5px 0; border-left: none; }
.source-toggle button.active { background: #6366f1; color: #fff; border-color: #6366f1; }
.source-toggle button:hover:not(.active) { background: #fafafa; color: #3f3f46; }

.selector-group select:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15);
}

.vs-badge {
  font-size: 13px;
  font-weight: 700;
  color: #a1a1aa;
  background: #f4f4f5;
  padding: 2px 8px;
  border-radius: 4px;
  flex-shrink: 0;
  align-self: center;
  margin-bottom: 8px;
}

/* Comparison header */
.compare-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  border-radius: 12px;
  margin-bottom: 16px;
  font-size: 14px;
  flex-wrap: wrap;
}

.compare-header.same-source {
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  border: 1px solid #bfdbfe;
}

.compare-header.cross-source {
  background: linear-gradient(135deg, #f5f3ff, #ede9fe);
  border: 1px solid #c4b5fd;
}

.ch-label {
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.same-source .ch-label { background: #3b82f6; color: #fff; }
.cross-source .ch-label { background: #8b5cf6; color: #fff; }

.ch-tag {
  font-weight: 600;
  color: #1e293b;
  font-size: 15px;
}

.ch-arrow {
  color: #94a3b8;
  font-size: 16px;
  margin: 0 2px;
}

.ch-hint {
  margin-left: auto;
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

/* Summary bar */
.summary-bar {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  background: #fff;
  padding: 12px 20px;
  border-radius: 12px;
  border: 1px solid rgba(228, 228, 231, 0.6);
  flex-wrap: wrap;
}

.summary-item {
  font-size: 13px;
  color: #52525b;
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot-green { background: #10b981; }
.dot-blue { background: #1890ff; }
.dot-amber { background: #f5c518; }
.dot-red { background: #ef4444; }
.dot-gray { background: #a1a1aa; }

/* Sections */
.section {
  background: #fff;
  border-radius: 12px;
  margin-bottom: 16px;
  border: 1px solid rgba(228, 228, 231, 0.6);
  overflow: hidden;
}

.section details {
  padding: 16px 20px;
}

.section summary {
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  color: #18181b;
  list-style: none;
  display: flex;
  align-items: center;
  gap: 6px;
}

.section summary::before {
  content: '▶';
  font-size: 10px;
  color: #a1a1aa;
  transition: transform 0.15s;
}

.section details[open] summary::before {
  transform: rotate(90deg);
}

.section summary::-webkit-details-marker { display: none; }

.movie-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.chip {
  padding: 4px 10px;
  background: #f4f4f5;
  border-radius: 6px;
  font-size: 12px;
  color: #52525b;
  cursor: pointer;
  transition: background 0.15s;
}

.chip:hover { background: #e4e4e7; }

.chip-green { background: #dcfce7; color: #166534; }
.chip-green:hover { background: #bbf7d0; }
.chip-red { background: #fee2e2; color: #991b1b; }
.chip-red:hover { background: #fecaca; }
.chip-amber { background: #fef3c7; color: #92400e; }
.chip-amber:hover { background: #fde68a; }

.compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-top: 12px;
}

.compare-table th {
  text-align: left;
  padding: 8px 12px;
  color: #a1a1aa;
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  border-bottom: 1px solid #f4f4f5;
}

.compare-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #f4f4f5;
  cursor: pointer;
}

.compare-table tr:hover td { background: #f5f3ff; }
.col-title { font-weight: 500; color: #18181b; }
.col-rank { color: #71717a; width: 100px; }
.col-delta { width: 80px; font-weight: 600; }
.delta-up { color: #10b981; }
.delta-down { color: #f43f5e; }

.loading, .empty {
  text-align: center;
  padding: 40px;
  color: #a1a1aa;
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(228, 228, 231, 0.6);
  font-size: 13px;
}

/* Venn diagram */
.venn-bar {
  padding: 12px 20px;
  text-align: center;
}

/* Distribution */
.dist-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.dist-tabs {
  display: flex;
  gap: 0;
}

.dist-tabs button {
  padding: 4px 12px;
  border: 1px solid #e4e4e7;
  background: #fff;
  cursor: pointer;
  font-size: 11px;
  font-weight: 500;
  color: #71717a;
  transition: all 0.15s;
  font-family: inherit;
}

.dist-tabs button:first-child { border-radius: 5px 0 0 5px; }
.dist-tabs button:last-child { border-radius: 0 5px 5px 0; border-left: none; }
.dist-tabs button:not(:first-child):not(:last-child) { border-left: none; }
.dist-tabs button.active { background: #6366f1; color: #fff; border-color: #6366f1; }
.dist-tabs button:hover:not(.active) { background: #fafafa; color: #3f3f46; }

@media (max-width: 640px) {
  .selectors { flex-direction: column; gap: 12px; }
  .vs-badge { display: none; }
  .selector-group { min-width: 100%; }
  .ch-hint { margin-left: 0; width: 100%; }
}
</style>
