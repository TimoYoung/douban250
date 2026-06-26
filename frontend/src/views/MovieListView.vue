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

    <div v-if="store.loading" class="loading">加载中...</div>

    <template v-else>
      <div v-if="viewMode === 'poster'">
        <div class="movie-grid">
          <MovieCard v-for="movie in store.movies" :key="movie.id" :movie="movie" />
        </div>
        <PaginationBar
          :page="store.page"
          :pageSize="store.pageSize"
          :totalPages="store.totalPages"
          :total="store.total"
          @update:page="onPageChange"
          @update:pageSize="onPageSizeChange"
        />
      </div>

      <div v-else-if="viewMode === 'list'">
        <MovieListTable :movies="store.movies" />
        <PaginationBar
          :page="store.page"
          :pageSize="store.pageSize"
          :totalPages="store.totalPages"
          :total="store.total"
          @update:page="onPageChange"
          @update:pageSize="onPageSizeChange"
        />
      </div>

      <BubbleGrid v-else :movies="store.bubbles" :highlight="searchText" />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMoviesStore } from '../stores/movies.js'
import { useVersionsStore } from '../stores/versions.js'
import { useAuthStore } from '../stores/auth.js'
import VersionSelector from '../components/VersionSelector.vue'
import MovieCard from '../components/MovieCard.vue'
import MovieListTable from '../components/MovieListTable.vue'
import BubbleGrid from '../components/BubbleGrid.vue'
import PaginationBar from '../components/PaginationBar.vue'

const store = useMoviesStore()
const versionsStore = useVersionsStore()
const authStore = useAuthStore()

const viewMode = computed({
  get: () => store.viewMode,
  set: (val) => { store.viewMode = val },
})
const watchedFilter = ref(store.watchedFilter || 'all')
const searchText = ref(store.search || '')
const showDropdown = ref(false)

const globalResults = computed(() => {
  // Filter out movies that are already in the current version's movie list
  const currentIds = new Set(store.movies.map(m => m.douban_id))
  return store.globalResults.filter(r => !currentIds.has(r.douban_id))
})

onMounted(async () => {
  await versionsStore.loadVersions()
  store.watchedFilter = watchedFilter.value
  await Promise.all([
    store.loadMovies(versionsStore.currentVersionId),
    store.loadBubbles(versionsStore.currentVersionId),
  ])
})

function onVersionChange(id) {
  versionsStore.currentVersionId = id
  store.page = 1
  loadData()
}

function onSourceChange(source) {
  versionsStore.setSourceFilter(source)
  store.page = 1
  loadData()
}

function onFilterChange() {
  store.watchedFilter = watchedFilter.value
  store.page = 1
  loadData()
}

let searchTimer = null

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    store.search = searchText.value
    store.page = 1
    loadData()
    // Global search for cross-version results
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
  // Sync source filter so VersionSelector's filtered list includes the target version
  if (result.source && result.source !== versionsStore.sourceFilter) {
    versionsStore.sourceFilter = result.source
  }
  versionsStore.currentVersionId = result.latest_version_id
  store.page = 1
  loadData()
  // Trigger global search again for the new version context
  store.searchGlobal(searchText.value)
}

function onSearch() {
  store.search = searchText.value
  store.page = 1
  loadData()
}

function onPageChange(p) {
  store.page = p
  store.loadMovies(versionsStore.currentVersionId)
}

function onPageSizeChange(size) {
  store.pageSize = size
  store.page = 1
  store.loadMovies(versionsStore.currentVersionId)
}

function loadData() {
  store.loadMovies(versionsStore.currentVersionId)
  store.loadBubbles(versionsStore.currentVersionId)
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
</style>
