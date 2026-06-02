<template>
  <div v-if="pendingCount > 0" class="pending-matches">
    <h3>待确认匹配（{{ pendingCount }} 部电影）</h3>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="matches.length === 0" class="empty">
      暂无待确认匹配
    </div>

    <div v-else class="match-list">
      <div v-for="movie in matches" :key="movie.imdb_id" class="match-card">
        <div class="match-header">
          <div class="movie-info">
            <span class="movie-title">{{ movie.imdb_title }}</span>
            <span v-if="movie.year" class="movie-year">({{ movie.year }})</span>
            <a v-if="movie.imdb_id" class="imdb-id-link" :href="'https://www.imdb.com/title/' + movie.imdb_id" target="_blank" rel="noopener">{{ movie.imdb_id }}</a>
          </div>
          <div class="version-tags">
            <span v-for="v in movie.versions" :key="v.version_id"
                  class="version-tag" :title="'排名 #' + v.rank">
              {{ v.tag }} #{{ v.rank }}
            </span>
          </div>
        </div>

        <!-- 候选列表 -->
        <div v-if="movie.candidates && movie.candidates.length > 0" class="candidates">
          <div class="candidate-label">候选：</div>
          <div v-for="(c, ci) in movie.candidates" :key="ci" class="candidate-item">
            <a
              v-if="c.douban_id"
              class="candidate-title candidate-link"
              :href="'https://movie.douban.com/subject/' + c.douban_id"
              target="_blank"
              rel="noopener"
            >{{ c.title }}</a>
            <span v-else class="candidate-title">{{ c.title }}</span>
            <span v-if="c.year" class="candidate-year">({{ c.year }})</span>
            <span v-if="c.rating" class="candidate-rating">★ {{ c.rating }}</span>
            <span v-if="c.imdb_id_from_detail" class="imdb-badge" title="详情页有 IMDb ID">IMDb</span>
            <button
              class="btn btn-sm btn-accept"
              :disabled="resolving"
              @click="accept(movie.imdb_id, c.douban_id)"
            >接受</button>
          </div>
        </div>
        <div v-else class="no-candidates">无候选结果</div>

        <!-- 操作 -->
        <div class="actions">
          <div class="manual-input">
            <input
              v-model="manualIds[movie.imdb_id]"
              type="text"
              placeholder="手动输入 douban_id"
              class="input-douban-id"
              :disabled="resolving"
              @keyup.enter="inputManual(movie.imdb_id)"
            />
            <button
              class="btn btn-sm btn-input"
              :disabled="resolving || !manualIds[movie.imdb_id]"
              @click="inputManual(movie.imdb_id)"
            >确定</button>
          </div>
          <button
            class="btn btn-sm btn-skip"
            :disabled="resolving"
            @click="skip(movie.imdb_id)"
          >跳过（仅 IMDb）</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useSettingsStore } from '../stores/settings'

const settingsStore = useSettingsStore()

const matches = ref([])
const loading = ref(false)
const resolving = ref(false)
const manualIds = ref({})

const pendingCount = ref(0)

async function loadList() {
  loading.value = true
  try {
    await settingsStore.loadPendingMatches()
    matches.value = settingsStore.pendingMatches
    pendingCount.value = settingsStore.pendingMatchCount
  } finally {
    loading.value = false
  }
}

async function loadCount() {
  await settingsStore.loadPendingMatchCount()
  pendingCount.value = settingsStore.pendingMatchCount
}

async function accept(imdbId, doubanId) {
  resolving.value = true
  try {
    await settingsStore.resolveMatch(imdbId, 'accept', doubanId)
    matches.value = settingsStore.pendingMatches
    pendingCount.value = settingsStore.pendingMatchCount
  } finally {
    resolving.value = false
  }
}

async function inputManual(imdbId) {
  const doubanId = manualIds.value[imdbId]
  if (!doubanId) return
  resolving.value = true
  try {
    await settingsStore.resolveMatch(imdbId, 'input', null, doubanId)
    matches.value = settingsStore.pendingMatches
    pendingCount.value = settingsStore.pendingMatchCount
    delete manualIds.value[imdbId]
  } finally {
    resolving.value = false
  }
}

async function skip(imdbId) {
  resolving.value = true
  try {
    await settingsStore.resolveMatch(imdbId, 'skip')
    matches.value = settingsStore.pendingMatches
    pendingCount.value = settingsStore.pendingMatchCount
  } finally {
    resolving.value = false
  }
}

// 监听外部 pendingCount 变化（来自轮询）
watch(() => settingsStore.pendingMatchCount, (newCount) => {
  pendingCount.value = newCount
  if (newCount > 0 && matches.value.length === 0) {
    loadList()
  } else if (newCount === 0) {
    matches.value = []
  }
})

onMounted(() => {
  loadCount()
  loadList()
})
</script>

<style scoped>
.pending-matches {
  background: var(--color-bg-secondary, #f8f9fa);
  border: 1px solid var(--color-border, #e0e0e0);
  border-radius: 8px;
  padding: 16px;
  margin: 12px 0;
}

h3 {
  margin: 0 0 12px 0;
  font-size: 1.05em;
  color: var(--color-text-primary, #333);
}

.loading, .empty {
  color: var(--color-text-muted, #999);
  padding: 12px 0;
  font-style: italic;
}

.match-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.match-card {
  background: var(--color-bg-primary, #fff);
  border: 1px solid var(--color-border, #e0e0e0);
  border-radius: 6px;
  padding: 12px;
}

.match-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  flex-wrap: wrap;
  gap: 6px;
}

.movie-info {
  font-weight: 600;
  font-size: 1.02em;
  color: var(--color-text-primary, #333);
}

.movie-year {
  font-weight: 400;
  color: var(--color-text-muted, #999);
  margin-left: 4px;
}

.imdb-id-link {
  font-size: 0.8em;
  color: #f5c518;
  background: #000;
  padding: 1px 6px;
  border-radius: 3px;
  text-decoration: none;
  font-weight: 600;
  margin-left: 6px;
}

.imdb-id-link:hover {
  background: #333;
}

.version-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.version-tag {
  background: var(--color-primary-soft, #e3f2fd);
  color: var(--color-primary, #1976d2);
  font-size: 0.78em;
  padding: 2px 8px;
  border-radius: 10px;
  white-space: nowrap;
}

.candidates {
  margin: 8px 0;
}

.candidate-label {
  font-size: 0.85em;
  color: var(--color-text-muted, #999);
  margin-bottom: 4px;
}

.candidate-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  background: var(--color-bg-secondary, #f5f5f5);
  border-radius: 4px;
  margin-bottom: 4px;
  font-size: 0.92em;
  flex-wrap: wrap;
}

.candidate-title {
  font-weight: 500;
}

.candidate-link {
  color: #1a73e8;
  text-decoration: none;
}

.candidate-link:hover {
  text-decoration: underline;
}

.candidate-year {
  color: var(--color-text-muted, #999);
  font-size: 0.9em;
}

.candidate-rating {
  color: #f5a623;
  font-size: 0.85em;
}

.imdb-badge {
  background: #f5c518;
  color: #000;
  font-size: 0.7em;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 600;
}

.no-candidates {
  font-size: 0.9em;
  color: var(--color-text-muted, #999);
  margin: 8px 0;
  font-style: italic;
}

.actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.manual-input {
  display: flex;
  gap: 4px;
  align-items: center;
}

.input-douban-id {
  width: 160px;
  padding: 4px 8px;
  border: 1px solid var(--color-border, #ccc);
  border-radius: 4px;
  font-size: 0.88em;
}

.btn {
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85em;
  padding: 4px 10px;
  transition: background 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  padding: 3px 8px;
  font-size: 0.82em;
}

.btn-accept {
  background: #4caf50;
  color: white;
}

.btn-accept:hover:not(:disabled) {
  background: #43a047;
}

.btn-input {
  background: #2196f3;
  color: white;
}

.btn-input:hover:not(:disabled) {
  background: #1e88e5;
}

.btn-skip {
  background: #9e9e9e;
  color: white;
  margin-left: auto;
}

.btn-skip:hover:not(:disabled) {
  background: #757575;
}
</style>
