<template>
  <div class="movie-detail-view">
    <a href="#" class="back-link" @click.prevent="$router.back()">← 返回</a>

    <div v-if="store.loading" class="loading">加载中...</div>

    <template v-if="movie">
      <div class="detail-header">
        <div class="detail-poster">
          <img v-if="movie.poster_path" :src="`/posters/${movie.poster_path}`" :alt="movie.title" />
          <div v-else class="no-poster">无海报</div>
        </div>
        <div class="detail-info">
          <h1>{{ movie.title }}</h1>
          <p v-if="movie.original_title" class="original-title">{{ movie.original_title }}</p>

          <div class="meta-grid">
            <div v-if="movie.year"><strong>年份：</strong>{{ movie.year }}</div>
            <div v-if="movie.country"><strong>地区：</strong>{{ movie.country }}</div>
            <div v-if="movie.genre"><strong>类型：</strong>{{ movie.genre }}</div>
            <div v-if="movie.director"><strong>导演：</strong>{{ movie.director }}</div>
            <div v-if="movie.cast_members && movie.cast_members.length">
              <strong>主演：</strong>{{ movie.cast_members.join(', ') }}
            </div>
            <div v-if="movie.rating"><strong>评分：</strong>{{ movie.rating }} ({{ movie.rating_count }}人评价)</div>
            <div v-if="movie.current_rank"><strong>当前排名：</strong>#{{ movie.current_rank }}</div>
            <div v-if="movie.watched" class="watched-tag">✓ 已看过</div>
            <div v-if="movie.douban_url">
              <a :href="movie.douban_url" target="_blank" rel="noopener" class="douban-link">在豆瓣中打开 →</a>
            </div>
          </div>

          <p v-if="movie.tagline" class="tagline">"{{ movie.tagline }}"</p>
        </div>
      </div>

      <div v-if="movie.summary" class="detail-section">
        <h3>剧情简介</h3>
        <p class="summary" v-for="(para, i) in summaryParagraphs" :key="i">{{ para }}</p>
      </div>

      <RankHistoryChart v-if="movie.rank_history.length > 1" :history="movie.rank_history" />
      <p v-else-if="movie.rank_history.length === 1" class="single-version">该电影目前仅在一个版本中有记录</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useMoviesStore } from '../stores/movies.js'
import RankHistoryChart from '../components/RankHistoryChart.vue'

const route = useRoute()
const store = useMoviesStore()

const movie = computed(() => store.currentMovie)

const summaryParagraphs = computed(() => {
  if (!movie.value?.summary) return []
  return movie.value.summary
    .split('\n')
    .map(s => s.replace(/^[\s　]+/, '').replace(/[\s　]+$/, '').trim())
    .filter(s => s.length > 0)
})

onMounted(() => {
  store.loadMovie(route.params.id)
})
</script>

<style scoped>
.back-link {
  display: inline-block;
  margin-bottom: 16px;
  color: #1890ff;
  text-decoration: none;
  font-size: 14px;
}

.detail-header {
  display: flex;
  gap: 24px;
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 24px;
}

.detail-poster {
  flex-shrink: 0;
  width: 200px;
}

.detail-poster img {
  width: 100%;
  border-radius: 8px;
}

.no-poster {
  width: 200px;
  height: 300px;
  background: #f0f0f0;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
}

.detail-info h1 {
  font-size: 24px;
  margin-bottom: 4px;
}

.original-title {
  color: #999;
  margin-bottom: 16px;
  font-size: 14px;
}

.meta-grid {
  display: grid;
  gap: 8px;
  font-size: 14px;
  line-height: 1.8;
}

.watched-tag {
  display: inline-block;
  padding: 2px 12px;
  background: #f6ffed;
  color: #52c41a;
  border-radius: 4px;
  font-size: 13px;
}

.douban-link {
  color: #1890ff;
  text-decoration: none;
  font-size: 13px;
}

.douban-link:hover {
  text-decoration: underline;
}

.tagline {
  margin-top: 16px;
  color: #666;
  font-style: italic;
  font-size: 14px;
}

.detail-section {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 24px;
}

.detail-section h3 {
  font-size: 16px;
  margin-bottom: 12px;
  color: #333;
}

.summary {
  font-size: 14px;
  line-height: 1.8;
  color: #555;
  text-indent: 2em;
  margin-bottom: 8px;
}

.single-version {
  text-align: center;
  padding: 40px;
  color: #999;
  background: #fff;
  border-radius: 8px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #999;
}
</style>
