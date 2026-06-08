<template>
  <div class="explore-view">
    <!-- 筛选面板 -->
    <aside class="filter-panel" :class="{ open: filterPanelOpen }">
      <div class="filter-header">
        <h2>筛选</h2>
        <button class="filter-close" @click="filterPanelOpen = false">✕</button>
      </div>

      <!-- 评分范围 -->
      <div class="filter-section">
        <h3>豆瓣评分</h3>
        <div class="range-inputs">
          <input
            type="number"
            class="range-input"
            :min="filterMeta.rating_min"
            :max="filterMeta.rating_max"
            step="0.1"
            v-model.number="ratingRange[0]"
            @blur="onRangeInputBlur('rating', 0)"
            @keydown.enter="$event.target.blur()"
          />
          <span class="range-sep">—</span>
          <input
            type="number"
            class="range-input"
            :min="filterMeta.rating_min"
            :max="filterMeta.rating_max"
            step="0.1"
            v-model.number="ratingRange[1]"
            @blur="onRangeInputBlur('rating', 1)"
            @keydown.enter="$event.target.blur()"
          />
        </div>
        <div class="dual-slider">
          <input
            type="range"
            :min="filterMeta.rating_min"
            :max="filterMeta.rating_max"
            step="0.1"
            v-model.number="ratingRange[0]"
            @change="clampRange('rating')"
          />
          <input
            type="range"
            :min="filterMeta.rating_min"
            :max="filterMeta.rating_max"
            step="0.1"
            v-model.number="ratingRange[1]"
            @change="clampRange('rating')"
          />
        </div>
      </div>

      <!-- 类型 -->
      <div class="filter-section">
        <h3>类型</h3>
        <div class="genre-chips">
          <button
            v-for="g in filterMeta.genres"
            :key="g"
            class="genre-chip"
            :class="{ active: selectedGenres.includes(g) }"
            @click="toggleGenre(g)"
          >
            {{ g }}
          </button>
        </div>
      </div>

      <!-- 地区 -->
      <div class="filter-section">
        <h3>地区</h3>
        <div class="genre-chips">
          <button
            v-for="c in filterMeta.countries"
            :key="c"
            class="genre-chip"
            :class="{ active: selectedCountries.includes(c) }"
            @click="toggleCountry(c)"
          >
            {{ c }}
          </button>
        </div>
      </div>

      <!-- 年份范围 -->
      <div class="filter-section">
        <h3>年份</h3>
        <div class="range-inputs">
          <input
            type="number"
            class="range-input"
            :min="filterMeta.year_min"
            :max="filterMeta.year_max"
            step="1"
            v-model.number="yearRange[0]"
            @blur="onRangeInputBlur('year', 0)"
            @keydown.enter="$event.target.blur()"
          />
          <span class="range-sep">—</span>
          <input
            type="number"
            class="range-input"
            :min="filterMeta.year_min"
            :max="filterMeta.year_max"
            step="1"
            v-model.number="yearRange[1]"
            @blur="onRangeInputBlur('year', 1)"
            @keydown.enter="$event.target.blur()"
          />
        </div>
        <div class="dual-slider">
          <input
            type="range"
            :min="filterMeta.year_min"
            :max="filterMeta.year_max"
            step="1"
            v-model.number="yearRange[0]"
            @change="clampRange('year')"
          />
          <input
            type="range"
            :min="filterMeta.year_min"
            :max="filterMeta.year_max"
            step="1"
            v-model.number="yearRange[1]"
            @change="clampRange('year')"
          />
        </div>
        <div class="year-presets">
          <button
            v-for="p in yearPresets"
            :key="p.label"
            class="preset-btn"
            :class="{ active: yearRange[0] === p.from && yearRange[1] === p.to }"
            @click="yearRange = [p.from, p.to]"
          >
            {{ p.label }}
          </button>
        </div>
      </div>

      <!-- 时长范围 -->
      <div class="filter-section">
        <h3>时长（分钟）</h3>
        <div class="range-inputs">
          <input
            type="number"
            class="range-input"
            :min="filterMeta.duration_min"
            :max="filterMeta.duration_max"
            step="1"
            v-model.number="durationRange[0]"
            @blur="onRangeInputBlur('duration', 0)"
            @keydown.enter="$event.target.blur()"
          />
          <span class="range-sep">—</span>
          <input
            type="number"
            class="range-input"
            :min="filterMeta.duration_min"
            :max="filterMeta.duration_max"
            step="1"
            v-model.number="durationRange[1]"
            @blur="onRangeInputBlur('duration', 1)"
            @keydown.enter="$event.target.blur()"
          />
        </div>
        <div class="dual-slider">
          <input
            type="range"
            :min="filterMeta.duration_min"
            :max="filterMeta.duration_max"
            step="1"
            v-model.number="durationRange[0]"
            @change="clampRange('duration')"
          />
          <input
            type="range"
            :min="filterMeta.duration_min"
            :max="filterMeta.duration_max"
            step="1"
            v-model.number="durationRange[1]"
            @change="clampRange('duration')"
          />
        </div>
      </div>

      <!-- 看过状态 -->
      <div class="filter-section" v-if="authStore.isLoggedIn">
        <h3>看过状态</h3>
        <div class="watched-toggle">
          <button
            v-for="opt in watchedOptions"
            :key="opt.value"
            class="watched-btn"
            :class="{ active: watchedFilter === opt.value }"
            @click="watchedFilter = opt.value"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>

      <!-- 排序 -->
      <div class="filter-section">
        <h3>排序</h3>
        <div class="sort-controls">
          <select v-model="sortBy" class="sort-select">
            <option value="rating">评分</option>
            <option value="year">年份</option>
            <option value="title">片名</option>
            <option value="duration">时长</option>
          </select>
          <button
            class="sort-order-btn"
            @click="sortOrder = sortOrder === 'desc' ? 'asc' : 'desc'"
            :title="sortOrder === 'desc' ? '降序' : '升序'"
          >
            {{ sortOrder === 'desc' ? '↓' : '↑' }}
          </button>
        </div>
      </div>

      <!-- 重置 -->
      <div class="filter-actions">
        <button class="reset-btn" @click="resetFilters">重置筛选</button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="explore-content">
      <!-- 移动端筛选按钮 + 结果统计 + 视图切换 -->
      <div class="content-header">
        <button class="mobile-filter-btn" @click="filterPanelOpen = true">
          <span>⚙</span> 筛选
          <span v-if="activeFilterCount > 0" class="filter-badge">{{ activeFilterCount }}</span>
        </button>
        <div class="result-info">
          <span v-if="!loading">共 <strong>{{ total }}</strong> 部电影</span>
          <span v-else class="loading-text">加载中...</span>
        </div>
        <div class="view-toggle">
          <button
            class="view-btn"
            :class="{ active: viewMode === 'grid' }"
            @click="viewMode = 'grid'"
            title="海报视图"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <rect x="1" y="1" width="6" height="6" rx="1"/>
              <rect x="9" y="1" width="6" height="6" rx="1"/>
              <rect x="1" y="9" width="6" height="6" rx="1"/>
              <rect x="9" y="9" width="6" height="6" rx="1"/>
            </svg>
          </button>
          <button
            class="view-btn"
            :class="{ active: viewMode === 'list' }"
            @click="viewMode = 'list'"
            title="列表视图"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <rect x="1" y="2" width="14" height="2" rx="1"/>
              <rect x="1" y="7" width="14" height="2" rx="1"/>
              <rect x="1" y="12" width="14" height="2" rx="1"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- 海报视图 -->
      <div class="movie-grid" v-if="viewMode === 'grid' && movies.length > 0">
        <MovieCard v-for="movie in movies" :key="movie.id" :movie="movie" />
      </div>

      <!-- 列表视图 -->
      <div class="movie-list" v-else-if="viewMode === 'list' && movies.length > 0">
        <div class="list-header">
          <span class="list-col col-poster"></span>
          <span class="list-col col-title">片名</span>
          <span class="list-col col-year">年份</span>
          <span class="list-col col-duration">时长</span>
          <span class="list-col col-rating">评分</span>
          <span class="list-col col-director">导演</span>
          <span class="list-col col-genre">类型</span>
        </div>
        <div
          v-for="movie in movies"
          :key="movie.id"
          class="list-row"
          @click="$router.push(`/movies/${movie.douban_id}`)"
        >
          <span class="list-col col-poster">
            <img v-if="movie.poster_path" :src="`/posters/${movie.poster_path}`" :alt="movie.title" />
            <div v-else class="list-no-poster">无</div>
          </span>
          <span class="list-col col-title">
            <span class="list-title-text">{{ movie.title }}</span>
            <span v-if="movie.watched" class="list-watched">看过</span>
          </span>
          <span class="list-col col-year">{{ movie.year || '-' }}</span>
          <span class="list-col col-duration">{{ movie.duration ? movie.duration + '分' : '-' }}</span>
          <span class="list-col col-rating">
            <span v-if="movie.rating" class="list-rating">{{ movie.rating }}</span>
            <span v-else>-</span>
          </span>
          <span class="list-col col-director">{{ movie.director || '-' }}</span>
          <span class="list-col col-genre">{{ movie.genre || '-' }}</span>
        </div>
      </div>

      <div v-else-if="!loading" class="empty-state">
        <div class="empty-icon">🎬</div>
        <p>没有找到符合条件的电影</p>
        <button class="reset-btn" @click="resetFilters">重置筛选</button>
      </div>

      <!-- 分页 -->
      <div class="pagination-wrapper" v-if="totalPages > 1">
        <PaginationBar
          :page="page"
          :pageSize="pageSize"
          :totalPages="totalPages"
          :total="total"
          @update:page="page = $event"
          @update:pageSize="onPageSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { fetchExploreFilters, exploreMovies } from '../api/index.js'
import MovieCard from '../components/MovieCard.vue'
import PaginationBar from '../components/PaginationBar.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// ── 筛选元数据 ──
const filterMeta = ref({
  genres: [],
  countries: [],
  year_min: 1900,
  year_max: 2026,
  rating_min: 0,
  rating_max: 10,
  duration_min: 0,
  duration_max: 300,
})

// ── 筛选状态 ──
const ratingRange = ref([0, 10])
const selectedGenres = ref([])
const selectedCountries = ref([])
const yearRange = ref([1900, 2026])
const durationRange = ref([0, 300])
const watchedFilter = ref('all')
const sortBy = ref('rating')
const sortOrder = ref('desc')
const page = ref(1)
const pageSize = ref(20)
const filterPanelOpen = ref(false)
const viewMode = ref('grid')  // 'grid' or 'list'

// ── 结果数据 ──
const movies = ref([])
const total = ref(0)
const totalPages = ref(0)
const loading = ref(false)

// ── 选项 ──
const watchedOptions = [
  { value: 'all', label: '全部' },
  { value: 'watched', label: '已看过' },
  { value: 'unwatched', label: '未看过' },
]

const yearPresets = computed(() => {
  const max = filterMeta.value.year_max
  return [
    { label: '2020s', from: 2020, to: max },
    { label: '2010s', from: 2010, to: 2019 },
    { label: '2000s', from: 2000, to: 2009 },
    { label: '90s', from: 1990, to: 1999 },
    { label: '经典', from: filterMeta.value.year_min, to: 1989 },
  ]
})

// ── 计算属性 ──
const activeFilterCount = computed(() => {
  let count = 0
  if (ratingRange.value[0] > filterMeta.value.rating_min || ratingRange.value[1] < filterMeta.value.rating_max) count++
  if (selectedGenres.value.length > 0) count++
  if (selectedCountries.value.length > 0) count++
  if (yearRange.value[0] > filterMeta.value.year_min || yearRange.value[1] < filterMeta.value.year_max) count++
  if (durationRange.value[0] > filterMeta.value.duration_min || durationRange.value[1] < filterMeta.value.duration_max) count++
  if (watchedFilter.value !== 'all') count++
  return count
})

// ── 方法 ──
function toggleGenre(genre) {
  const idx = selectedGenres.value.indexOf(genre)
  if (idx >= 0) {
    selectedGenres.value.splice(idx, 1)
  } else {
    selectedGenres.value.push(genre)
  }
}

function toggleCountry(country) {
  const idx = selectedCountries.value.indexOf(country)
  if (idx >= 0) {
    selectedCountries.value.splice(idx, 1)
  } else {
    selectedCountries.value.push(country)
  }
}

function clampRange(type) {
  if (type === 'rating') {
    if (ratingRange.value[0] > ratingRange.value[1]) {
      ratingRange.value = [ratingRange.value[1], ratingRange.value[0]]
    }
  } else if (type === 'year') {
    if (yearRange.value[0] > yearRange.value[1]) {
      yearRange.value = [yearRange.value[1], yearRange.value[0]]
    }
  } else if (type === 'duration') {
    if (durationRange.value[0] > durationRange.value[1]) {
      durationRange.value = [durationRange.value[1], durationRange.value[0]]
    }
  }
}

function onRangeInputBlur(type, index) {
  const meta = filterMeta.value
  if (type === 'rating') {
    const min = meta.rating_min
    const max = meta.rating_max
    let val = ratingRange.value[index]
    if (isNaN(val) || val < min) val = min
    if (val > max) val = max
    ratingRange.value[index] = Math.round(val * 10) / 10
    clampRange('rating')
  } else if (type === 'year') {
    const min = meta.year_min
    const max = meta.year_max
    let val = yearRange.value[index]
    if (isNaN(val) || val < min) val = min
    if (val > max) val = max
    yearRange.value[index] = Math.round(val)
    clampRange('year')
  } else if (type === 'duration') {
    const min = meta.duration_min
    const max = meta.duration_max
    let val = durationRange.value[index]
    if (isNaN(val) || val < min) val = min
    if (val > max) val = max
    durationRange.value[index] = Math.round(val)
    clampRange('duration')
  }
}

function resetFilters() {
  ratingRange.value = [filterMeta.value.rating_min, filterMeta.value.rating_max]
  selectedGenres.value = []
  selectedCountries.value = []
  yearRange.value = [filterMeta.value.year_min, filterMeta.value.year_max]
  durationRange.value = [filterMeta.value.duration_min, filterMeta.value.duration_max]
  watchedFilter.value = 'all'
  sortBy.value = 'rating'
  sortOrder.value = 'desc'
  page.value = 1
  pageSize.value = 20
}

function onPageSizeChange(newSize) {
  pageSize.value = newSize
  page.value = 1  // 切换每页条数时重置到第一页
  syncToQuery()
  loadMovies()
}

// 从 URL 恢复筛选状态
function restoreFromQuery() {
  const q = route.query
  if (q.rating_min) ratingRange.value[0] = parseFloat(q.rating_min)
  if (q.rating_max) ratingRange.value[1] = parseFloat(q.rating_max)
  if (q.genres) selectedGenres.value = q.genres.split(',')
  if (q.countries) selectedCountries.value = q.countries.split(',')
  if (q.year_min) yearRange.value[0] = parseInt(q.year_min)
  if (q.year_max) yearRange.value[1] = parseInt(q.year_max)
  if (q.duration_min) durationRange.value[0] = parseInt(q.duration_min)
  if (q.duration_max) durationRange.value[1] = parseInt(q.duration_max)
  if (q.watched) watchedFilter.value = q.watched
  if (q.sort_by) sortBy.value = q.sort_by
  if (q.sort_order) sortOrder.value = q.sort_order
  if (q.page) page.value = parseInt(q.page)
  if (q.page_size) pageSize.value = parseInt(q.page_size)
}

// 同步筛选状态到 URL
function syncToQuery() {
  const q = {}
  const meta = filterMeta.value
  if (ratingRange.value[0] > meta.rating_min) q.rating_min = ratingRange.value[0].toFixed(1)
  if (ratingRange.value[1] < meta.rating_max) q.rating_max = ratingRange.value[1].toFixed(1)
  if (selectedGenres.value.length > 0) q.genres = selectedGenres.value.join(',')
  if (selectedCountries.value.length > 0) q.countries = selectedCountries.value.join(',')
  if (yearRange.value[0] > meta.year_min) q.year_min = yearRange.value[0]
  if (yearRange.value[1] < meta.year_max) q.year_max = yearRange.value[1]
  if (durationRange.value[0] > meta.duration_min) q.duration_min = durationRange.value[0]
  if (durationRange.value[1] < meta.duration_max) q.duration_max = durationRange.value[1]
  if (watchedFilter.value !== 'all') q.watched = watchedFilter.value
  if (sortBy.value !== 'rating') q.sort_by = sortBy.value
  if (sortOrder.value !== 'desc') q.sort_order = sortOrder.value
  if (page.value > 1) q.page = page.value
  if (pageSize.value !== 20) q.page_size = pageSize.value
  router.replace({ query: q })
}

async function loadFilters() {
  try {
    const { data } = await fetchExploreFilters()
    filterMeta.value = data
    // 用元数据初始化范围（如果 URL 没有覆盖的话）
    if (!route.query.rating_min && !route.query.rating_max) {
      ratingRange.value = [data.rating_min, data.rating_max]
    }
    if (!route.query.year_min && !route.query.year_max) {
      yearRange.value = [data.year_min, data.year_max]
    }
    if (!route.query.duration_min && !route.query.duration_max) {
      durationRange.value = [data.duration_min, data.duration_max]
    }
  } catch (e) {
    console.error('Failed to load explore filters:', e)
  }
}

async function loadMovies() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
      watched_filter: watchedFilter.value,
    }
    const meta = filterMeta.value
    if (ratingRange.value[0] > meta.rating_min) params.rating_min = ratingRange.value[0].toFixed(1)
    if (ratingRange.value[1] < meta.rating_max) params.rating_max = ratingRange.value[1].toFixed(1)
    if (selectedGenres.value.length > 0) params.genres = selectedGenres.value.join(',')
    if (selectedCountries.value.length > 0) params.countries = selectedCountries.value.join(',')
    if (yearRange.value[0] > meta.year_min) params.year_min = yearRange.value[0]
    if (yearRange.value[1] < meta.year_max) params.year_max = yearRange.value[1]
    if (durationRange.value[0] > meta.duration_min) params.duration_min = durationRange.value[0]
    if (durationRange.value[1] < meta.duration_max) params.duration_max = durationRange.value[1]

    const { data } = await exploreMovies(params)
    movies.value = data.items
    total.value = data.total
    totalPages.value = data.total_pages
  } catch (e) {
    console.error('Failed to load explore movies:', e)
  } finally {
    loading.value = false
  }
}

// ── 监听筛选变化（防抖） ──
let debounceTimer = null
function debouncedLoad() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    syncToQuery()
    loadMovies()
  }, 300)
}

watch([ratingRange, selectedGenres, selectedCountries, yearRange, durationRange, watchedFilter, sortBy, sortOrder], debouncedLoad, { deep: true })
watch(page, () => {
  syncToQuery()
  loadMovies()
  // 滚动到顶部
  window.scrollTo({ top: 0, behavior: 'smooth' })
})

// ── 初始化 ──
onMounted(async () => {
  await loadFilters()
  restoreFromQuery()
  loadMovies()
})
</script>

<style scoped>
.explore-view {
  display: flex;
  gap: 24px;
  min-height: calc(100vh - 120px);
}

/* ── 筛选面板 ── */
.filter-panel {
  width: 260px;
  flex-shrink: 0;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border, rgba(228, 228, 231, 0.6));
  border-radius: 10px;
  padding: 20px;
  position: sticky;
  top: 72px;
  max-height: calc(100vh - 96px);
  overflow-y: auto;
  scrollbar-width: thin;
}

.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.filter-header h2 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text, #27272a);
}

.filter-close {
  display: none;
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #71717a;
  padding: 4px;
}

.filter-section {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border, rgba(228, 228, 231, 0.6));
}

.filter-section:last-of-type {
  border-bottom: none;
}

.filter-section h3 {
  font-size: 12px;
  font-weight: 600;
  color: #71717a;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}

/* ── 范围输入 ── */
.range-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.range-input {
  flex: 1;
  min-width: 0;
  text-align: center;
  font-size: 13px;
  font-weight: 600;
  color: var(--text, #27272a);
  border: 1px solid #e4e4e7;
  border-radius: 6px;
  padding: 4px 6px;
  background: #fff;
  outline: none;
  transition: border-color 0.15s;
  -moz-appearance: textfield;
}

.range-input::-webkit-outer-spin-button,
.range-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.range-input:focus {
  border-color: var(--accent, #6366f1);
}

.range-sep {
  color: #d4d4d8;
  flex-shrink: 0;
}

.dual-slider {
  position: relative;
  height: 20px;
}

.dual-slider input[type="range"] {
  position: absolute;
  width: 100%;
  height: 4px;
  top: 8px;
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
  pointer-events: none;
}

.dual-slider input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--accent, #6366f1);
  cursor: pointer;
  pointer-events: auto;
  border: 2px solid #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.dual-slider input[type="range"]::-webkit-slider-runnable-track {
  height: 4px;
  background: #e4e4e7;
  border-radius: 2px;
}

/* ── 类型标签 ── */
.genre-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.genre-chip {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid #e4e4e7;
  border-radius: 14px;
  background: transparent;
  color: #52525b;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.genre-chip:hover {
  border-color: var(--accent, #6366f1);
  color: var(--accent, #6366f1);
}

.genre-chip.active {
  background: var(--accent, #6366f1);
  border-color: var(--accent, #6366f1);
  color: #fff;
}

/* ── 年份预设 ── */
.year-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

.preset-btn {
  padding: 3px 8px;
  font-size: 11px;
  border: 1px solid #e4e4e7;
  border-radius: 4px;
  background: transparent;
  color: #71717a;
  cursor: pointer;
  transition: all 0.15s;
}

.preset-btn:hover {
  border-color: var(--accent, #6366f1);
  color: var(--accent, #6366f1);
}

.preset-btn.active {
  background: #eef2ff;
  border-color: var(--accent, #6366f1);
  color: var(--accent, #6366f1);
}

/* ── 看过状态 ── */
.watched-toggle {
  display: flex;
  gap: 4px;
}

.watched-btn {
  flex: 1;
  padding: 6px 0;
  font-size: 12px;
  border: 1px solid #e4e4e7;
  border-radius: 6px;
  background: transparent;
  color: #71717a;
  cursor: pointer;
  transition: all 0.15s;
}

.watched-btn:hover {
  border-color: var(--accent, #6366f1);
}

.watched-btn.active {
  background: var(--accent, #6366f1);
  border-color: var(--accent, #6366f1);
  color: #fff;
}

/* ── 排序 ── */
.sort-controls {
  display: flex;
  gap: 6px;
}

.sort-select {
  flex: 1;
  padding: 6px 10px;
  font-size: 13px;
  border: 1px solid #e4e4e7;
  border-radius: 6px;
  background: #fff;
  color: var(--text, #27272a);
  cursor: pointer;
  outline: none;
}

.sort-select:focus {
  border-color: var(--accent, #6366f1);
}

.sort-order-btn {
  width: 36px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  border: 1px solid #e4e4e7;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  transition: all 0.15s;
  color: var(--text, #27272a);
}

.sort-order-btn:hover {
  border-color: var(--accent, #6366f1);
  color: var(--accent, #6366f1);
}

/* ── 重置按钮 ── */
.filter-actions {
  margin-top: 8px;
}

.reset-btn {
  width: 100%;
  padding: 8px 0;
  font-size: 13px;
  border: 1px solid #e4e4e7;
  border-radius: 6px;
  background: transparent;
  color: #71717a;
  cursor: pointer;
  transition: all 0.15s;
}

.reset-btn:hover {
  background: #f4f4f5;
  color: #3f3f46;
}

/* ── 主内容区 ── */
.explore-content {
  flex: 1;
  min-width: 0;
}

.content-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.mobile-filter-btn {
  display: none;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 13px;
  border: 1px solid #e4e4e7;
  border-radius: 6px;
  background: var(--card-bg, #fff);
  cursor: pointer;
  color: var(--text, #27272a);
  position: relative;
}

.filter-badge {
  background: var(--accent, #6366f1);
  color: #fff;
  font-size: 10px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.result-info {
  font-size: 13px;
  color: #71717a;
}

.result-info strong {
  color: var(--text, #27272a);
}

.loading-text {
  color: #a1a1aa;
}

/* ── 视图切换 ── */
.view-toggle {
  display: flex;
  gap: 2px;
  margin-left: auto;
  background: #f4f4f5;
  border-radius: 6px;
  padding: 2px;
}

.view-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 28px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #71717a;
  cursor: pointer;
  transition: all 0.15s;
}

.view-btn:hover {
  color: #3f3f46;
}

.view-btn.active {
  background: #fff;
  color: var(--accent, #6366f1);
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

/* ── 电影网格 ── */
.movie-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

/* ── 电影列表 ── */
.movie-list {
  background: #fff;
  border-radius: 10px;
  border: 1px solid rgba(228, 228, 231, 0.6);
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  background: #fafafa;
  border-bottom: 1px solid #e4e4e7;
  font-size: 12px;
  font-weight: 600;
  color: #71717a;
}

.list-row {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid #f4f4f5;
  cursor: pointer;
  transition: background 0.15s;
}

.list-row:last-child {
  border-bottom: none;
}

.list-row:hover {
  background: #fafafa;
}

.list-col {
  font-size: 13px;
  color: #52525b;
}

.col-poster {
  width: 40px;
  flex-shrink: 0;
  margin-right: 12px;
}

.col-poster img {
  width: 40px;
  height: 56px;
  object-fit: cover;
  border-radius: 4px;
}

.list-no-poster {
  width: 40px;
  height: 56px;
  background: #f4f4f5;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: #a1a1aa;
}

.col-title {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.list-title-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
  color: #18181b;
}

.list-watched {
  flex-shrink: 0;
  padding: 1px 6px;
  background: #ecfdf5;
  color: #10b981;
  font-size: 11px;
  border-radius: 3px;
}

.col-year {
  width: 50px;
  text-align: center;
  flex-shrink: 0;
}

.col-duration {
  width: 60px;
  text-align: center;
  flex-shrink: 0;
}

.col-rating {
  width: 50px;
  text-align: center;
  flex-shrink: 0;
}

.list-rating {
  color: #faad14;
  font-weight: 600;
}

.col-director {
  width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 0;
}

.col-genre {
  width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 0;
  font-size: 12px;
  color: #71717a;
}

/* ── 空状态 ── */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #a1a1aa;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-state p {
  font-size: 14px;
  margin-bottom: 16px;
}

.empty-state .reset-btn {
  width: auto;
  display: inline-block;
  padding: 8px 24px;
}

/* ── 分页 ── */
.pagination-wrapper {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .explore-view {
    flex-direction: column;
  }

  .filter-panel {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100vh;
    max-height: 100vh;
    border-radius: 0;
    z-index: 200;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
  }

  .filter-panel.open {
    transform: translateX(0);
  }

  .filter-close {
    display: block;
  }

  .mobile-filter-btn {
    display: inline-flex;
  }

  .movie-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px;
  }

  .col-director,
  .col-genre {
    display: none;
  }
}
</style>
