<template>
  <div class="dashboard-view">
    <div v-if="loading" class="loading">加载中…</div>

    <template v-else-if="analytics.dashboard">
      <!-- KPI Cards -->
      <div class="kpi-row">
        <div class="kpi-card kpi-douban">
          <div class="kpi-source-label">🟦 豆瓣</div>
          <div class="kpi-row-inner">
            <div class="kpi-field">
              <span class="kpi-field-label">最新</span>
              <span class="kpi-field-value">{{ analytics.dashboard.douban.latest_tag || '-' }}</span>
              <span class="kpi-sub-text" v-if="analytics.dashboard.douban.latest_crawled_at">{{ formatCrawlTime(analytics.dashboard.douban.latest_crawled_at) }}</span>
            </div>
            <div class="kpi-field" v-if="authStore.isAdmin && analytics.dashboard.douban.next_fire_time">
              <span class="kpi-field-label">下次</span>
              <span class="kpi-field-value next-fire">{{ formatNextFire(analytics.dashboard.douban.next_fire_time) }}</span>
            </div>
          </div>
          <div class="kpi-changes">
            <span class="delta-up" v-if="analytics.dashboard.douban.kpi_changes.added">+{{ analytics.dashboard.douban.kpi_changes.added }} 新进</span>
            <span class="delta-down" v-if="analytics.dashboard.douban.kpi_changes.removed">-{{ analytics.dashboard.douban.kpi_changes.removed }} 跌出</span>
            <span v-if="!analytics.dashboard.douban.kpi_changes.added && !analytics.dashboard.douban.kpi_changes.removed" class="no-change">暂无变动</span>
          </div>
          <div class="kpi-version-count">{{ analytics.dashboard.douban.version_count }} 个版本</div>
        </div>

        <div class="kpi-card kpi-imdb">
          <div class="kpi-source-label">🟨 IMDb</div>
          <div class="kpi-row-inner">
            <div class="kpi-field">
              <span class="kpi-field-label">最新</span>
              <span class="kpi-field-value">{{ analytics.dashboard.imdb.latest_tag || '-' }}</span>
              <span class="kpi-sub-text" v-if="analytics.dashboard.imdb.latest_crawled_at">{{ formatCrawlTime(analytics.dashboard.imdb.latest_crawled_at) }}</span>
            </div>
            <div class="kpi-field" v-if="authStore.isAdmin && analytics.dashboard.imdb.next_fire_time">
              <span class="kpi-field-label">下次</span>
              <span class="kpi-field-value next-fire">{{ formatNextFire(analytics.dashboard.imdb.next_fire_time) }}</span>
            </div>
          </div>
          <div class="kpi-changes">
            <span class="delta-up" v-if="analytics.dashboard.imdb.kpi_changes.added">+{{ analytics.dashboard.imdb.kpi_changes.added }} 新进</span>
            <span class="delta-down" v-if="analytics.dashboard.imdb.kpi_changes.removed">-{{ analytics.dashboard.imdb.kpi_changes.removed }} 跌出</span>
            <span v-if="!analytics.dashboard.imdb.kpi_changes.added && !analytics.dashboard.imdb.kpi_changes.removed" class="no-change">暂无变动</span>
          </div>
          <div class="kpi-version-count">{{ analytics.dashboard.imdb.version_count }} 个版本</div>
        </div>

        <div class="kpi-card kpi-total">
          <div class="kpi-source-label">📚 收录</div>
          <div class="kpi-big-number">{{ analytics.dashboard.total_movies }}</div>
          <div class="kpi-sub-text">部电影 (去重)</div>
        </div>
      </div>

      <!-- Source stories -->
      <div v-for="src in ['douban', 'imdb']" :key="src" class="source-story" :class="src">
        <div class="source-story-header">
          <span class="source-story-icon">{{ src === 'douban' ? '🟦' : '🟨' }}</span>
          <span class="source-story-title">{{ src === 'douban' ? '豆瓣' : 'IMDb' }}</span>
        </div>

        <!-- 排名变化 -->
        <div class="source-card">
          <div class="sc-header">
            <div class="sc-header-text">
              <span class="sc-title">排名变化</span>
              <span class="sc-subtitle" v-if="analytics.dashboard[src].prev_tag">
                {{ analytics.dashboard[src].prev_tag }} → {{ analytics.dashboard[src].latest_tag }}
              </span>
              <span class="sc-subtitle" v-else>首个版本，暂无对比</span>
            </div>
            <router-link
              v-if="analytics.dashboard[src].latest_version_id && analytics.dashboard[src].prev_version_id"
              :to="compareUrl(src, analytics.dashboard[src].latest_version_id, analytics.dashboard[src].prev_version_id)"
              class="view-all">查看全部 →</router-link>
          </div>
          <div class="sc-body" v-if="analytics.dashboard[src].rank_changes.risers_top5?.length || analytics.dashboard[src].rank_changes.fallers_top5?.length">
            <div class="rank-list-row">
              <div class="rank-list" v-if="analytics.dashboard[src].rank_changes.risers_top5?.length">
                <div class="sc-label">🔺 上升 Top 5</div>
                <div v-for="m in analytics.dashboard[src].rank_changes.risers_top5" :key="m.movie_id" class="rank-item" @click="goMovieDetail(m)">
                  <span class="rank-title">{{ m.title }}</span>
                  <span class="rank-delta delta-up">▲{{ m.rank_change }}</span>
                  <span class="rank-target">#{{ m.current_rank }}</span>
                </div>
              </div>
              <div class="rank-list" v-if="analytics.dashboard[src].rank_changes.fallers_top5?.length">
                <div class="sc-label">🔻 下降 Top 5</div>
                <div v-for="m in analytics.dashboard[src].rank_changes.fallers_top5" :key="m.movie_id" class="rank-item" @click="goMovieDetail(m)">
                  <span class="rank-title">{{ m.title }}</span>
                  <span class="rank-delta delta-down">▼{{ Math.abs(m.rank_change) }}</span>
                  <span class="rank-target">#{{ m.current_rank }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="sc-body sc-empty" v-else>暂无排名变动</div>
        </div>

        <!-- 进出 -->
        <div class="source-card">
          <div class="sc-header">
            <div class="sc-header-text">
              <span class="sc-title">进出</span>
              <span class="sc-subtitle" v-if="analytics.dashboard[src].prev_changed_tag">
                上次有电影进出 · {{ analytics.dashboard[src].prev_changed_tag }} → {{ analytics.dashboard[src].latest_tag }}
              </span>
              <span class="sc-subtitle" v-else>首个版本，暂无对比基准</span>
            </div>
            <router-link
              v-if="analytics.dashboard[src].latest_version_id && analytics.dashboard[src].prev_changed_version_id"
              :to="compareUrl(src, analytics.dashboard[src].latest_version_id, analytics.dashboard[src].prev_changed_version_id)"
              class="view-all">查看全部 →</router-link>
          </div>
          <div class="sc-body" v-if="analytics.dashboard[src].changes.added || analytics.dashboard[src].changes.removed">
            <div class="sc-section" v-if="analytics.dashboard[src].changes.added_movies?.length">
              <div class="sc-label">🆕 新上榜 ({{ analytics.dashboard[src].changes.added }})</div>
              <div class="movie-chips">
                <span v-for="m in analytics.dashboard[src].changes.added_movies" :key="m.movie_id" class="chip chip-green" @click="goMovieDetail(m)">
                  #{{ m.rank }} {{ m.title }}
                </span>
              </div>
            </div>
            <div class="sc-section" v-if="analytics.dashboard[src].changes.removed_movies?.length">
              <div class="sc-label">💀 跌出榜 ({{ analytics.dashboard[src].changes.removed }})</div>
              <div class="movie-chips">
                <span v-for="m in analytics.dashboard[src].changes.removed_movies" :key="m.movie_id" class="chip chip-red" @click="goMovieDetail(m)">
                  #{{ m.rank }} {{ m.title }}
                </span>
              </div>
            </div>
          </div>
          <div class="sc-body sc-empty" v-else>暂无进出变动</div>
        </div>

        <!-- 入榜与跌出 (历史纵深) -->
        <div class="source-card">
          <div class="sc-header">
            <span class="sc-title">入榜与跌出</span>
          </div>
          <div class="history-row">
            <!-- 首次入榜 -->
            <div class="history-col">
              <div class="history-col-title">🌟 首次入榜</div>
              <template v-if="analytics.recentDebuts[src]?.length">
                <div class="debut-group" v-for="group in analytics.recentDebuts[src]" :key="group.debut_version_id">
                  <div class="debut-group-header">
                    {{ group.debut_tag }}
                    <span class="debut-group-count">({{ group.movies.length }} 部)</span>
                  </div>
                  <div class="debut-movies">
                    <router-link
                      v-for="m in group.movies"
                      :key="m.movie_id"
                      :to="m.douban_id ? `/movies/${m.douban_id}` : `/movies/id/${m.movie_id}`"
                      class="debut-movie-item">
                      <span class="debut-rank">#{{ m.debut_rank }}</span>
                      <span class="debut-title">{{ m.title }}</span>
                    </router-link>
                  </div>
                </div>
              </template>
              <div v-else class="history-empty">暂无数据</div>
            </div>
            <!-- 最近跌出 -->
            <div class="history-col">
              <div class="history-col-title">📉 最近跌出</div>
              <template v-if="analytics.recentDrops[src]?.length">
                <div class="drop-group" v-for="group in analytics.recentDrops[src]" :key="group.drop_version_id">
                  <div class="drop-group-header">
                    {{ group.drop_tag }}
                    <span class="drop-group-count">({{ group.movies.length }} 部)</span>
                  </div>
                  <div class="drop-movies">
                    <router-link
                      v-for="m in group.movies"
                      :key="m.movie_id"
                      :to="m.douban_id ? `/movies/${m.douban_id}` : `/movies/id/${m.movie_id}`"
                      class="drop-movie-item">
                      <span class="drop-rank">#{{ m.drop_rank }}</span>
                      <span class="drop-title">{{ m.title }}</span>
                    </router-link>
                  </div>
                </div>
              </template>
              <div v-else class="history-empty">暂无数据</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Cross-platform section (standalone row) -->
      <div class="section-card">
        <div class="section-header">
          <div class="section-header-text">
            <span class="section-title">⚔️ 豆瓣 vs IMDb</span>
            <div class="section-subtitle" v-if="analytics.dashboard.douban.latest_tag && analytics.dashboard.imdb.latest_tag">
              两榜最新版本对比 · 豆瓣 {{ analytics.dashboard.douban.latest_tag }} vs IMDb {{ analytics.dashboard.imdb.latest_tag }}
            </div>
          </div>
          <router-link
            v-if="analytics.dashboard.douban.latest_version_id && analytics.dashboard.imdb.latest_version_id"
            :to="{ path: '/compare', query: { sourceA: 'douban', sourceB: 'imdb', usePrev: 'false', versionA: analytics.dashboard.douban.latest_version_id, versionB: analytics.dashboard.imdb.latest_version_id } }"
            class="view-all">查看全部 →</router-link>
        </div>
        <div class="cross-platform-body">
          <!-- Venn diagram -->
          <div class="venn-section" v-if="analytics.overlap">
            <VennDiagram
              :only-a="analytics.overlap.only_douban"
              :both="analytics.overlap.both"
              :only-b="analytics.overlap.only_imdb"
            />
            <div class="overlap-rate">重叠率 {{ overlapPercent }}%</div>
          </div>
          <!-- Unique movies lists -->
          <div class="unique-lists" v-if="analytics.uniqueMovies">
            <div class="unique-col">
              <div class="unique-col-header douban-text">仅豆瓣 Top {{ analytics.uniqueMovies.only_douban?.length || 0 }}</div>
              <div v-for="m in analytics.uniqueMovies.only_douban" :key="m.movie_id" class="unique-item" @click="goMovieDetail(m)">
                <span class="unique-rank">#{{ m.rank }}</span>
                <span class="unique-title">{{ m.title }}</span>
              </div>
              <div v-if="!analytics.uniqueMovies.only_douban?.length" class="unique-empty">无</div>
            </div>
            <div class="unique-col">
              <div class="unique-col-header imdb-text">仅 IMDb Top {{ analytics.uniqueMovies.only_imdb?.length || 0 }}</div>
              <div v-for="m in analytics.uniqueMovies.only_imdb" :key="m.movie_id" class="unique-item" @click="goMovieDetail(m)">
                <span class="unique-rank">#{{ m.rank }}</span>
                <span class="unique-title">{{ m.title }}</span>
              </div>
              <div v-if="!analytics.uniqueMovies.only_imdb?.length" class="unique-empty">无</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Distribution + Version pickers -->
      <div class="section-card">
        <div class="section-header">
          <span class="section-title">📊 分布统计</span>
          <div class="section-controls">
            <div class="source-toggle">
              <button :class="{ active: distSource === 'douban' }" @click="switchDistSource('douban')">豆瓣</button>
              <button :class="{ active: distSource === 'imdb' }" @click="switchDistSource('imdb')">IMDb</button>
              <button :class="{ active: distSource === 'compare' }" @click="switchDistSource('compare')">两榜对比</button>
            </div>
            <a :href="distDetailUrl" class="view-all">查看详情 →</a>
          </div>
        </div>

        <!-- Tabs: 类型 | 国家 | 年代 -->
        <div class="dist-tabs">
          <button :class="{ active: distTab === 'genres' }" @click="distTab = 'genres'">类型</button>
          <button :class="{ active: distTab === 'countries' }" @click="distTab = 'countries'">国家</button>
          <button :class="{ active: distTab === 'years' }" @click="distTab = 'years'">年代</button>
        </div>

        <!-- Version timelines -->
        <div class="version-timeline-wrapper" v-if="distSource !== 'compare'">
          <VersionTimeline
            :versions="currentVersionTagsAsVersions"
            :modelValue="selectedVersionId"
            :barColor="distSource === 'douban' ? '#1890ff' : '#f5c518'"
            @update:modelValue="onSingleVersionChange"
          />
        </div>
        <div class="version-timeline-row" v-else>
          <div class="version-timeline-col">
            <label class="tl-source-label douban-text">🟦 豆瓣版本</label>
            <VersionTimeline
              :versions="doubanTagsAsVersions"
              :modelValue="selectedDoubanVerId"
              barColor="#1890ff"
              @update:modelValue="onDoubanVerChange"
            />
          </div>
          <div class="version-timeline-col">
            <label class="tl-source-label imdb-text">🟨 IMDb版本</label>
            <VersionTimeline
              :versions="imdbTagsAsVersions"
              :modelValue="selectedImdbVerId"
              barColor="#f5c518"
              @update:modelValue="onImdbVerChange"
            />
          </div>
        </div>

        <!-- Chart -->
        <div class="dist-chart-wrapper">
          <DistributionChart
            :labels="chartLabels"
            :douban-values="chartDoubanValues"
            :imdb-values="chartImdbValues"
            :is-compare="distSource === 'compare'"
            :single-values="chartSingleValues"
            :bar-color="chartBarColor"
          />
          <div v-if="distLoading" class="dist-loading">加载中…</div>
        </div>
      </div>
    </template>

    <div v-if="error" class="error-msg">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAnalyticsStore } from '../stores/analytics.js'
import { useAuthStore } from '../stores/auth.js'
import VersionTimeline from '../components/VersionTimeline.vue'
import DistributionChart from '../components/DistributionChart.vue'
import VennDiagram from '../components/VennDiagram.vue'
import { useDistributionChartData } from '../composables/useDistributionChartData.js'

const router = useRouter()
const analytics = useAnalyticsStore()
const authStore = useAuthStore()

const loading = ref(true)
const error = ref('')

// Distribution
const distSource = ref('compare')
const distTab = ref('genres')
const distLoading = ref(false)

// 分布图数据源：compare 模式用 compareDistribution，单源模式用 distribution
const activeDistribution = computed(() =>
  distSource.value === 'compare' ? analytics.compareDistribution : analytics.distribution
)

const {
  labels: chartLabels,
  doubanValues: chartDoubanValues,
  imdbValues: chartImdbValues,
  singleValues: chartSingleValues,
  barColor: chartBarColor,
} = useDistributionChartData(
  activeDistribution,
  distTab,
  computed(() => distSource.value === 'compare'),
  computed(() => distSource.value === 'douban' ? '#1890ff' : '#f5c518')
)

// Version selection
const selectedVersionId = ref(null)      // single source mode
const selectedDoubanVerId = ref(null)    // compare mode
const selectedImdbVerId = ref(null)      // compare mode

// Version tags — 直接响应式引用 store 数据（避免一次性拷贝断裂响应式链路）
const doubanTags = computed(() => analytics.versionTags.douban)
const imdbTags = computed(() => analytics.versionTags.imdb)

// Convert to VersionTimeline format [{id, tag, movie_count}]
const doubanTagsAsVersions = computed(() =>
  doubanTags.value.map(t => ({ id: t.id, tag: t.tag, movie_count: t.movie_count }))
)
const imdbTagsAsVersions = computed(() =>
  imdbTags.value.map(t => ({ id: t.id, tag: t.tag, movie_count: t.movie_count }))
)
const currentVersionTagsAsVersions = computed(() =>
  distSource.value === 'imdb' ? imdbTagsAsVersions.value : doubanTagsAsVersions.value
)

// Current selected version objects (for "查看详情" URL)
const currentSelectedVer = computed(() => {
  if (distSource.value === 'compare') return null
  const tags = distSource.value === 'imdb' ? imdbTags.value : doubanTags.value
  const id = selectedVersionId.value
  return tags.find(t => t.id === id) || null
})
const currentDoubanVer = computed(() =>
  doubanTags.value.find(t => t.id === selectedDoubanVerId.value) || null
)
const currentImdbVer = computed(() =>
  imdbTags.value.find(t => t.id === selectedImdbVerId.value) || null
)

const overlapPercent = computed(() => {
  if (!analytics.overlap) return 0
  const total = analytics.overlap.only_douban + analytics.overlap.only_imdb + analytics.overlap.both
  return total > 0 ? Math.round(analytics.overlap.both / total * 100) : 0
})

// "查看详情" URL
const distDetailUrl = computed(() => {
  if (distSource.value === 'compare') {
    const dId = currentDoubanVer.value?.id
    const iId = currentImdbVer.value?.id
    if (dId && iId) {
      return `/compare?sourceA=douban&sourceB=imdb&usePrev=false&versionA=${dId}&versionB=${iId}`
    }
    return '/compare?sourceA=douban&sourceB=imdb'
  }
  const ver = currentSelectedVer.value
  if (ver) return `/movies?source=${distSource.value}&version_id=${ver.id}`
  return '/movies'
})

function compareUrl(source, latestId, prevId) {
  return {
    path: '/compare',
    query: { sourceA: source, usePrev: 'false', sourceB: source, versionA: latestId, versionB: prevId },
  }
}

function formatCrawlTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${d.getMonth() + 1}月${d.getDate()}日 ${hh}:${mm}`
}

function formatNextFire(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  const now = new Date()
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  const dayName = days[d.getDay()]
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const target = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const diffDays = Math.round((target - today) / 86400000)
  if (diffDays === 0) return `今天 ${hh}:${mm}`
  if (diffDays === 1) return `明天 ${hh}:${mm}`
  if (diffDays < 7) return `${dayName} ${hh}:${mm}`
  return `${d.getMonth() + 1}/${d.getDate()} ${hh}:${mm}`
}

onMounted(async () => {
  try {
    await analytics.loadDashboard()
    await Promise.all([
      analytics.loadOverlapAndUnique(),
      analytics.loadRecentDebuts(3),
      analytics.loadRecentDrops(3),
    ])

    await Promise.all([
      analytics.loadVersionTags('douban'),
      analytics.loadVersionTags('imdb'),
    ])

    // Init version selections to latest
    if (doubanTags.value.length) {
      const latestD = doubanTags.value[doubanTags.value.length - 1]
      selectedVersionId.value = latestD.id
      selectedDoubanVerId.value = latestD.id
    }
    if (imdbTags.value.length) {
      const latestI = imdbTags.value[imdbTags.value.length - 1]
      selectedImdbVerId.value = latestI.id
    }

    await loadDistributionData()
  } catch (e) {
    error.value = e.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
})

async function loadDistributionData() {
  error.value = ''
  distLoading.value = true
  try {
    if (distSource.value === 'compare') {
      const dTag = currentDoubanVer.value?.tag
      const iTag = currentImdbVer.value?.tag
      await analytics.loadDistribution('compare', {
        limit: 0,
        ...(dTag ? { douban_tag: dTag } : {}),
        ...(iTag ? { imdb_tag: iTag } : {}),
      })
    } else {
      const ver = currentSelectedVer.value
      const tag = ver?.tag
      await analytics.loadDistribution(distSource.value, { limit: 0, ...(tag ? { tag } : {}) })
    }
  } catch (e) {
    error.value = '分布数据加载失败'
    console.error('loadDistributionData failed:', e)
  } finally {
    distLoading.value = false
  }
}

function switchDistSource(source) {
  // 先清空旧数据（computed 依赖 distSource，必须在切换前清除，避免一帧内引用旧来源数据）
  analytics.distribution = null
  analytics.compareDistribution = null
  distSource.value = source
  // Reset selection to latest
  if (source === 'douban' && doubanTags.value.length) {
    selectedVersionId.value = doubanTags.value[doubanTags.value.length - 1].id
  } else if (source === 'imdb' && imdbTags.value.length) {
    selectedVersionId.value = imdbTags.value[imdbTags.value.length - 1].id
  }
  loadDistributionData()
}

function onSingleVersionChange(newId) {
  selectedVersionId.value = newId
  loadDistributionData()
}

function onDoubanVerChange(newId) {
  selectedDoubanVerId.value = newId
  loadDistributionData()
}

function onImdbVerChange(newId) {
  selectedImdbVerId.value = newId
  loadDistributionData()
}

function goMovieDetail(movie) {
  if (movie.douban_id) {
    router.push(`/movies/${movie.douban_id}`)
  } else {
    router.push(`/movies/id/${movie.movie_id}`)
  }
}
</script>

<style scoped>
/* KPI Cards */
.kpi-row {
  display: grid;
  grid-template-columns: 1fr 1fr 0.6fr;
  gap: 12px;
  margin-bottom: 20px;
}

.kpi-card {
  background: #fff;
  border: 1px solid rgba(228, 228, 231, 0.6);
  border-radius: 12px;
  padding: 16px 20px;
}

.kpi-source-label {
  font-size: 13px;
  font-weight: 600;
  color: #18181b;
  margin-bottom: 10px;
}

.kpi-row-inner {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
}

.kpi-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kpi-field-label {
  font-size: 10px;
  color: #a1a1aa;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.kpi-field-value {
  font-size: 15px;
  font-weight: 600;
  color: #27272a;
  font-family: 'SF Mono', monospace;
}

.kpi-field-value.next-fire {
  color: #6366f1;
  font-size: 13px;
}

.kpi-changes {
  font-size: 12px;
  display: flex;
  gap: 10px;
  margin-bottom: 6px;
}

.kpi-version-count {
  font-size: 11px;
  color: #a1a1aa;
}

.kpi-big-number {
  font-size: 32px;
  font-weight: 700;
  color: #18181b;
  font-family: 'SF Mono', monospace;
  letter-spacing: -1px;
}

.kpi-sub-text {
  font-size: 11px;
  color: #a1a1aa;
}

.delta-up { color: #10b981; font-weight: 600; }
.delta-down { color: #f43f5e; font-weight: 600; }
.no-change { color: #a1a1aa; }

/* Source story blocks */
.source-story {
  margin-bottom: 20px;
  border: 1px solid rgba(228, 228, 231, 0.6);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}

.source-story.douban { border-left: 3px solid #1890ff; }
.source-story.imdb { border-left: 3px solid #f5c518; }

.source-story-header {
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.source-story.douban .source-story-header {
  background: rgba(24, 144, 255, 0.04);
  color: #1890ff;
}

.source-story.imdb .source-story-header {
  background: rgba(245, 197, 24, 0.04);
  color: #d97706;
}

.source-story-icon {
  font-size: 14px;
}

.source-story-title {
  font-size: 14px;
  font-weight: 600;
}

/* Cards within source story */
.source-card {
  border-top: 1px solid rgba(228, 228, 231, 0.4);
  padding: 12px 16px;
}

.sc-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
  gap: 8px;
}

.sc-header-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sc-title {
  font-size: 12px;
  font-weight: 600;
  color: #3f3f46;
}

.sc-subtitle {
  font-size: 11px;
  font-weight: 400;
  color: #a1a1aa;
  font-family: 'SF Mono', monospace;
}

.sc-body { padding: 0; }

.sc-body.sc-empty {
  text-align: center;
  color: #a1a1aa;
  font-size: 12px;
  padding: 16px 0;
}

.sc-section {
  margin-bottom: 10px;
}

.sc-label {
  font-size: 11px;
  font-weight: 600;
  color: #71717a;
  margin-bottom: 5px;
}

.movie-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.chip {
  padding: 3px 8px;
  background: #f4f4f5;
  border-radius: 5px;
  font-size: 11px;
  color: #52525b;
  cursor: pointer;
  transition: background 0.15s;
}

.chip:hover { background: #e4e4e7; }
.chip-green { background: #dcfce7; color: #166534; }
.chip-green:hover { background: #bbf7d0; }
.chip-red { background: #fee2e2; color: #991b1b; }
.chip-red:hover { background: #fecaca; }

.rank-list-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 6px;
}

.rank-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 4px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 11px;
  transition: background 0.1s;
}

.rank-item:hover { background: #f5f3ff; }

.rank-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #27272a;
}

.rank-delta {
  font-size: 10px;
  font-weight: 600;
  min-width: 28px;
  text-align: right;
}

.rank-target {
  font-size: 10px;
  color: #a1a1aa;
  font-family: 'SF Mono', monospace;
}

.view-all {
  font-size: 12px;
  color: #6366f1;
  text-decoration: none;
  font-weight: 500;
}

.view-all:hover { text-decoration: underline; }

/* Section cards */
.section-card {
  background: #fff;
  border: 1px solid rgba(228, 228, 231, 0.6);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-header-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.section-subtitle {
  font-size: 11px;
  color: #a1a1aa;
  font-weight: 400;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #18181b;
}

.section-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.source-toggle {
  display: flex;
  gap: 0;
}

.source-toggle button {
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

.source-toggle button:first-child { border-radius: 5px 0 0 5px; }
.source-toggle button:last-child { border-radius: 0 5px 5px 0; border-left: none; }
.source-toggle button:not(:first-child):not(:last-child) { border-left: none; }
.source-toggle button.active { background: #6366f1; color: #fff; border-color: #6366f1; }
.source-toggle button:hover:not(.active) { background: #fafafa; color: #3f3f46; }

/* Cross-platform */
.cross-platform-body {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.venn-section {
  flex-shrink: 0;
  text-align: center;
}

.overlap-rate {
  font-size: 12px;
  color: #6366f1;
  font-weight: 600;
  margin-top: 4px;
}

.unique-lists {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.unique-col-header {
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 6px;
}

.douban-text { color: #1890ff; }
.imdb-text { color: #d97706; }

.unique-item {
  display: flex;
  gap: 6px;
  padding: 3px 4px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.1s;
}

.unique-item:hover { background: #f5f3ff; }

.unique-rank {
  color: #a1a1aa;
  font-family: 'SF Mono', monospace;
  font-size: 10px;
  min-width: 24px;
}

.unique-title {
  color: #27272a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.unique-empty {
  font-size: 11px;
  color: #a1a1aa;
  padding: 8px 0;
}

/* Distribution tabs */
.dist-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 12px;
}

.dist-tabs button {
  padding: 5px 14px;
  border: 1px solid #e4e4e7;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  color: #71717a;
  transition: all 0.15s;
  font-family: inherit;
}

.dist-tabs button:first-child { border-radius: 6px 0 0 6px; }
.dist-tabs button:last-child { border-radius: 0 6px 6px 0; border-left: none; }
.dist-tabs button:not(:first-child):not(:last-child) { border-left: none; }
.dist-tabs button.active { background: #6366f1; color: #fff; border-color: #6366f1; }
.dist-tabs button:hover:not(.active) { background: #fafafa; color: #3f3f46; }

/* Version timelines */
.version-timeline-wrapper {
  margin-bottom: 12px;
}

.version-timeline-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.version-timeline-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tl-source-label {
  font-size: 11px;
  font-weight: 600;
}

.loading, .error-msg {
  text-align: center;
  padding: 30px;
  color: #a1a1aa;
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(228, 228, 231, 0.6);
  font-size: 13px;
}

.error-msg { color: #f43f5e; border-color: rgba(244, 63, 94, 0.2); }

/* Distribution chart loading overlay */
.dist-chart-wrapper {
  position: relative;
}

.dist-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  color: #a1a1aa;
  border-radius: 8px;
  z-index: 1;
}

/* History row (debuts | drops inside source card) */
.history-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.history-col {
  min-width: 0;
}

.history-col-title {
  font-size: 11px;
  font-weight: 600;
  color: #71717a;
  margin-bottom: 6px;
}

.history-empty {
  font-size: 11px;
  color: #a1a1aa;
  padding: 8px 0;
}

.debut-group {
  margin-bottom: 8px;
}

.debut-group-header {
  font-size: 11px;
  font-weight: 500;
  color: #71717a;
  margin-bottom: 4px;
  font-family: 'SF Mono', monospace;
}

.debut-group-count {
  color: #a1a1aa;
  font-weight: 400;
}

.debut-movies {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.debut-movie-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 6px;
  border-radius: 4px;
  font-size: 12px;
  text-decoration: none;
  transition: background 0.1s;
}

.debut-movie-item:hover { background: #f5f3ff; }

.debut-rank {
  color: #a1a1aa;
  font-family: 'SF Mono', monospace;
  font-size: 10px;
  min-width: 28px;
}

.debut-title {
  color: #27272a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drop-group {
  margin-bottom: 8px;
}

.drop-group-header {
  font-size: 11px;
  font-weight: 500;
  color: #71717a;
  margin-bottom: 4px;
  font-family: 'SF Mono', monospace;
}

.drop-group-count {
  color: #a1a1aa;
  font-weight: 400;
}

.drop-movies {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.drop-movie-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 6px;
  border-radius: 4px;
  font-size: 12px;
  text-decoration: none;
  transition: background 0.1s;
}

.drop-movie-item:hover { background: #f5f3ff; }

.drop-rank {
  color: #a1a1aa;
  font-family: 'SF Mono', monospace;
  font-size: 10px;
  min-width: 28px;
}

.drop-title {
  color: #27272a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .kpi-row { grid-template-columns: 1fr; }
  .history-row { grid-template-columns: 1fr; }
  .cross-platform-body { flex-direction: column; }
  .unique-lists { grid-template-columns: 1fr; }
  .rank-list-row { grid-template-columns: 1fr; }
}

@media (max-width: 640px) {
  .section-controls { flex-direction: column; align-items: flex-end; gap: 6px; }
}
</style>
