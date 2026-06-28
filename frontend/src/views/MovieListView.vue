<template>
  <div class="movie-list-view">
    <div class="toolbar">
      <VersionSelector
        :versions="versionsStore.filteredVersions"
        :modelValue="versionsStore.currentVersionId"
        :sourceFilter="versionsStore.sourceFilter"
        :sources="versionsStore.availableSources"
        @update:modelValue="onVersionChange"
        @update:sourceFilter="onSourceChange"
      />
      <div class="toolbar-right">
        <div class="search-wrapper">
          <input
            class="search-input"
            placeholder="搜索电影..."
            v-model="searchText"
            @input="onSearchInput"
            @focus="showDropdown = searchText.length > 0 && globalResults.length > 0"
            @blur="hideDropdown"
          />
          <div v-if="showDropdown && globalResults.length > 0" class="search-dropdown">
            <div class="dropdown-header">其他版本中的匹配</div>
            <div
              v-for="r in globalResults"
              :key="r.movie_id"
              class="dropdown-item"
              @mousedown.prevent="jumpToVersion(r)"
            >
              <span class="dropdown-title">{{ r.title }}</span>
              <span class="dropdown-meta">
                <span class="source-badge" :class="r.source === 'imdb' ? 'source-imdb' : 'source-douban'">{{ r.source === 'imdb' ? 'IMDb' : '豆瓣' }}</span>
                {{ r.latest_version_tag }} 排名 #{{ r.rank }}
              </span>
            </div>
          </div>
        </div>
        <select v-if="authStore.isLoggedIn" v-model="watchedFilter" @change="onFilterChange" class="filter-select">
          <option value="all">全部</option>
          <option value="watched">已看过</option>
          <option value="unwatched">未看过</option>
        </select>
        <span v-if="total > 0" class="total-count">共 {{ total }} 部电影</span>
        <div class="view-toggles">
          <button
            class="view-toggle"
            :class="{ active: viewMode === 'poster' }"
            @click="viewMode = 'poster'"
          >海报视图</button>
          <button
            class="view-toggle"
            :class="{ active: viewMode === 'list' }"
            @click="viewMode = 'list'"
          >列表视图</button>
          <button
            class="view-toggle"
            :class="{ active: viewMode === 'bubble' }"
            @click="viewMode = 'bubble'"
          >气泡视图</button>
        </div>
      </div>
    </div>

    <div v-if="isLoading && movies.length === 0" class="loading">加载中...</div>

    <template v-else>
      <div v-if="viewMode === 'poster'">
        <div class="movie-grid">
          <MovieCard v-for="movie in movies" :key="movie.id" :movie="movie" />
        </div>
      </div>

      <div v-else-if="viewMode === 'list'">
        <MovieListTable :movies="movies" />
      </div>

      <BubbleGrid v-else :movies="store.bubbles" :highlight="searchText" />

      <!-- 无限滚动 sentinel（仅 >500 条时生效，全加载模式下无感） -->
      <div ref="sentinelRef" class="load-sentinel" />
      <div v-if="isLoadingMore" class="loading-more">加载更多...</div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMoviesStore } from '../stores/movies.js'
import { useVersionsStore } from '../stores/versions.js'
import { useAuthStore } from '../stores/auth.js'
import { useMovieLoader } from '../composables/useMovieLoader.js'
import { fetchMovies } from '../api/index.js'
import VersionSelector from '../components/VersionSelector.vue'
import MovieCard from '../components/MovieCard.vue'
import MovieListTable from '../components/MovieListTable.vue'
import BubbleGrid from '../components/BubbleGrid.vue'

const store = useMoviesStore()
const versionsStore = useVersionsStore()
const authStore = useAuthStore()

// 电影列表加载（≤500 全加载，>500 无限滚动）
const {
  movies, total, isLoading, isLoadingMore,
  loadMovies, sentinelRef,
} = useMovieLoader((params) => fetchMovies(params))

const viewMode = computed({
  get: () => store.viewMode,
  set: (val) => { store.viewMode = val },
})
const watchedFilter = ref('all')
const searchText = ref('')
const showDropdown = ref(false)

const globalResults = computed(() => {
  const currentIds = new Set(movies.value.map(m => m.douban_id))
  return store.globalResults.filter(r => !currentIds.has(r.douban_id))
})

onMounted(async () => {
  await versionsStore.loadVersions()
  await Promise.all([
    loadMovies(buildParams()),
    store.loadBubbles(versionsStore.currentVersionId),
  ])
})

/** 构建列表加载参数 */
function buildParams() {
  const params = {
    version_id: versionsStore.currentVersionId,
    watched_filter: watchedFilter.value,
  }
  if (searchText.value) params.search = searchText.value
  return params
}

/** 筛选变化统一入口：重载列表 + 滚到顶部 */
function reloadList() {
  loadMovies(buildParams())
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function onVersionChange(id) {
  versionsStore.currentVersionId = id
  reloadList()
  store.loadBubbles(id)
}

function onSourceChange(source) {
  versionsStore.setSourceFilter(source)
  reloadList()
  store.loadBubbles(versionsStore.currentVersionId)
}

function onFilterChange() {
  reloadList()
}

let searchTimer = null

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    reloadList()
    store.searchGlobal(searchText.value).then(() => {
      showDropdown.value = searchText.value.length > 0 && globalResults.value.length > 0
    })
  }, 300)
}

function hideDropdown() {
  setTimeout(() => { showDropdown.value = false }, 200)
}

function jumpToVersion(result) {
  showDropdown.value = false
  if (result.source && result.source !== versionsStore.sourceFilter) {
    versionsStore.sourceFilter = result.source
  }
  versionsStore.currentVersionId = result.latest_version_id
  reloadList()
  store.loadBubbles(versionsStore.currentVersionId)
  store.searchGlobal(searchText.value)
}
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.search-input {
  padding: 6px 12px;
  border: 1px solid #e4e4e7;
  border-radius: 8px;
  font-size: 13px;
  width: 180px;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.search-input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.search-wrapper {
  position: relative;
}

.search-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  min-width: 280px;
  margin-top: 4px;
  background: #fff;
  border: 1px solid #e4e4e7;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  z-index: 100;
  max-height: 300px;
  overflow-y: auto;
}

.dropdown-header {
  padding: 8px 12px;
  font-size: 11px;
  color: #a1a1aa;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border-bottom: 1px solid #f4f4f5;
}

.dropdown-item {
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  transition: background 0.1s;
}

.dropdown-item:hover {
  background: #f5f3ff;
}

.dropdown-title {
  font-size: 13px;
  color: #18181b;
  font-weight: 500;
}

.dropdown-meta {
  font-size: 11px;
  color: #71717a;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 4px;
}

.source-badge {
  display: inline-block;
  padding: 0 5px;
  font-size: 10px;
  font-weight: 500;
  border-radius: 3px;
  line-height: 16px;
}

.source-douban {
  background: #eef2ff;
  color: #6366f1;
}

.source-imdb {
  background: #fffbeb;
  color: #d97706;
}

.filter-select {
  padding: 6px 12px;
  border: 1px solid #e4e4e7;
  border-radius: 8px;
  font-size: 13px;
  transition: border-color 0.15s;
}

.filter-select:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.view-toggles {
  display: flex;
}

.view-toggle {
  padding: 6px 12px;
  border: 1px solid #e4e4e7;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.15s;
  color: #71717a;
}

.view-toggle:first-child {
  border-radius: 8px 0 0 8px;
}

.view-toggle:nth-child(2) {
  border-left: none;
  border-right: none;
}

.view-toggle:last-child {
  border-radius: 0 8px 8px 0;
}

.view-toggle.active {
  background: #6366f1;
  color: #fff;
  border-color: #6366f1;
}

.view-toggle:hover:not(.active) {
  background: #fafafa;
  color: #3f3f46;
}

@media (max-width: 640px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .toolbar-right {
    justify-content: flex-start;
  }
  .search-input {
    width: 100%;
    flex: 1;
    min-width: 0;
  }
}

.movie-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #999;
  font-size: 16px;
}

.total-count {
  font-size: 12px;
  color: #a1a1aa;
  white-space: nowrap;
}

.load-sentinel {
  height: 1px;
}

.loading-more {
  text-align: center;
  padding: 16px;
  color: #a1a1aa;
  font-size: 13px;
}
</style>
