<template>
  <div class="movie-list-view">
    <div class="toolbar">
      <VersionSelector
        :versions="versionsStore.versions"
        :modelValue="versionsStore.currentVersionId"
        @update:modelValue="onVersionChange"
      />
      <div class="toolbar-right">
        <input
          class="search-input"
          placeholder="搜索电影..."
          v-model="searchText"
          @keyup.enter="onSearch"
        />
        <select v-model="watchedFilter" @change="onFilterChange" class="filter-select">
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

      <BubbleGrid v-else :movies="store.bubbles" />
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMoviesStore } from '../stores/movies.js'
import { useVersionsStore } from '../stores/versions.js'
import VersionSelector from '../components/VersionSelector.vue'
import MovieCard from '../components/MovieCard.vue'
import MovieListTable from '../components/MovieListTable.vue'
import BubbleGrid from '../components/BubbleGrid.vue'
import PaginationBar from '../components/PaginationBar.vue'

const store = useMoviesStore()
const versionsStore = useVersionsStore()

const viewMode = ref('poster')
const watchedFilter = ref('all')
const searchText = ref('')

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

function onFilterChange() {
  store.watchedFilter = watchedFilter.value
  store.page = 1
  loadData()
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
