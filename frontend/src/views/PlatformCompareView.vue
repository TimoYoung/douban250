<template>
  <div class="compare-view">
    <h2>平台对比</h2>

    <div class="compare-controls">
      <div class="control-group">
        <label>版本 A：</label>
        <select v-model="versionA" @change="loadCompare">
          <option v-for="v in versionsStore.versions" :key="v.id" :value="v.id">
            {{ sourceLabels[v.source] || v.source }} · {{ v.tag }}
          </option>
        </select>
      </div>
      <div class="control-group">
        <label>版本 B：</label>
        <select v-model="versionB" @change="loadCompare">
          <option v-for="v in versionsStore.versions" :key="v.id" :value="v.id">
            {{ sourceLabels[v.source] || v.source }} · {{ v.tag }}
          </option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <template v-else-if="data">
      <div class="summary-bar">
        <span class="summary-item">
          <span class="dot dot-green"></span>
          共同上榜 <strong>{{ data.common.length }}</strong> 部
        </span>
        <span class="summary-item">
          <span class="dot dot-blue"></span>
          仅 {{ sourceLabels[data.version_a?.source] || 'A' }} <strong>{{ data.only_a.length }}</strong> 部
        </span>
        <span class="summary-item">
          <span class="dot dot-amber"></span>
          仅 {{ sourceLabels[data.version_b?.source] || 'B' }} <strong>{{ data.only_b.length }}</strong> 部
        </span>
      </div>

      <!-- 共同上榜 -->
      <div class="section" v-if="data.common.length">
        <h3>共同上榜（排名差异最大 Top 20）</h3>
        <table class="compare-table">
          <thead>
            <tr>
              <th>电影</th>
              <th>{{ sourceLabels[data.version_a?.source] || 'A' }} 排名</th>
              <th>{{ sourceLabels[data.version_b?.source] || 'B' }} 排名</th>
              <th>差异</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in data.common.slice(0, 20)" :key="m.movie_id" @click="goDetail(m)">
              <td class="col-title">{{ m.title }}</td>
              <td class="col-rank">#{{ m.rank_a }}</td>
              <td class="col-rank">#{{ m.rank_b }}</td>
              <td class="col-delta" :class="deltaClass(m.delta)">
                {{ m.delta > 0 ? `▲${m.delta}` : m.delta < 0 ? `▼${Math.abs(m.delta)}` : '=' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 仅 A -->
      <div class="section" v-if="data.only_a.length">
        <h3>仅 {{ sourceLabels[data.version_a?.source] || 'A' }} 上榜（{{ data.only_a.length }} 部）</h3>
        <div class="movie-chips">
          <span v-for="m in data.only_a" :key="m.movie_id" class="chip" @click="goDetail(m)">
            #{{ m.rank }} {{ m.title }}
          </span>
        </div>
      </div>

      <!-- 仅 B -->
      <div class="section" v-if="data.only_b.length">
        <h3>仅 {{ sourceLabels[data.version_b?.source] || 'B' }} 上榜（{{ data.only_b.length }} 部）</h3>
        <div class="movie-chips">
          <span v-for="m in data.only_b" :key="m.movie_id" class="chip" @click="goDetail(m)">
            #{{ m.rank }} {{ m.title }}
          </span>
        </div>
      </div>
    </template>

    <p v-else class="empty">请选择两个版本进行对比</p>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useVersionsStore } from '../stores/versions.js'
import { fetchCompare } from '../api/index.js'

const router = useRouter()
const versionsStore = useVersionsStore()

const sourceLabels = { douban: '豆瓣', imdb: 'IMDb' }
const versionA = ref(null)
const versionB = ref(null)
const data = ref(null)
const loading = ref(false)

onMounted(async () => {
  await versionsStore.loadVersions()
  // Default: pick one douban and one imdb version
  const doubanVersions = versionsStore.versions.filter(v => v.source === 'douban')
  const imdbVersions = versionsStore.versions.filter(v => v.source === 'imdb')
  if (doubanVersions.length > 0) versionA.value = doubanVersions[0].id
  if (imdbVersions.length > 0) versionB.value = imdbVersions[0].id
  if (versionA.value && versionB.value) loadCompare()
})

async function loadCompare() {
  if (!versionA.value || !versionB.value) return
  loading.value = true
  try {
    const { data: result } = await fetchCompare(versionA.value, versionB.value)
    data.value = result
  } finally {
    loading.value = false
  }
}

function deltaClass(delta) {
  if (delta > 0) return 'delta-up'
  if (delta < 0) return 'delta-down'
  return ''
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
}

.compare-controls {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  background: #fff;
  padding: 16px 20px;
  border-radius: 12px;
  border: 1px solid rgba(228, 228, 231, 0.6);
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-group label {
  font-size: 13px;
  color: #71717a;
  white-space: nowrap;
  font-weight: 500;
}

.control-group select {
  padding: 6px 12px;
  border: 1px solid #e4e4e7;
  border-radius: 8px;
  font-size: 13px;
  min-width: 200px;
}

.summary-bar {
  display: flex;
  gap: 24px;
  margin-bottom: 20px;
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

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-green { background: #10b981; }
.dot-blue { background: #1890ff; }
.dot-amber { background: #f5c518; }

.section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
  border: 1px solid rgba(228, 228, 231, 0.6);
}

.section h3 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #18181b;
}

.compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
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

.compare-table tr:hover td {
  background: #f5f3ff;
}

.col-title {
  font-weight: 500;
  color: #18181b;
}

.col-rank {
  color: #71717a;
  width: 100px;
}

.col-delta {
  width: 80px;
  font-weight: 600;
}

.delta-up { color: #10b981; }
.delta-down { color: #f43f5e; }

.movie-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
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

.chip:hover {
  background: #e4e4e7;
}

.loading, .empty {
  text-align: center;
  padding: 40px;
  color: #a1a1aa;
  font-size: 13px;
}
</style>
