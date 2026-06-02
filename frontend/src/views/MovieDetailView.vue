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
            <div v-if="movie.rating"><strong>豆瓣评分：</strong>{{ movie.rating }}</div>
            <div v-if="movie.current_ranks && movie.current_ranks.length">
              <div v-for="cr in movie.current_ranks" :key="cr.source" class="current-rank-item">
                <strong>{{ cr.source === 'imdb' ? 'IMDb' : '豆瓣' }}排名：</strong>
                <span class="rank-value">#{{ cr.rank }}</span>
                <span class="rank-tag">({{ cr.tag }})</span>
              </div>
            </div>
            <div v-if="movie.watched" class="watched-tag">✓ 已看过</div>
            <div v-if="movie.douban_url">
              <a :href="movie.douban_url" target="_blank" rel="noopener" class="external-link douban-link">在豆瓣中打开 →</a>
            </div>
            <div v-if="movie.imdb_id">
              <a :href="`https://www.imdb.com/title/${movie.imdb_id}/`" target="_blank" rel="noopener" class="external-link imdb-link">在 IMDb 中打开 →</a>
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
  if (route.name === 'MovieDetailById') {
    store.loadMovieById(route.params.id)
  } else {
    store.loadMovie(route.params.id)
  }
})
</script>

<style scoped>
.back-link {
  display: inline-block;
  margin-bottom: 16px;
  color: #6366f1;
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
}

.detail-header {
  display: flex;
  gap: 24px;
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  border: 1px solid rgba(228, 228, 231, 0.6);
}

.detail-poster {
  flex-shrink: 0;
  width: 200px;
}

.detail-poster img {
  width: 100%;
  border-radius: 10px;
  display: block;
}

.no-poster {
  width: 200px;
  height: 300px;
  background: #f4f4f5;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a1a1aa;
  font-size: 13px;
}

.detail-info h1 {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 4px;
  color: #18181b;
  letter-spacing: -0.3px;
}

.original-title {
  color: #a1a1aa;
  margin-bottom: 16px;
  font-size: 13px;
}

.meta-grid {
  display: grid;
  gap: 6px;
  font-size: 13px;
  line-height: 1.7;
  color: #52525b;
}

.meta-grid strong {
  color: #a1a1aa;
  font-weight: 500;
}

.watched-tag {
  display: inline-block;
  padding: 2px 10px;
  background: #ecfdf5;
  color: #10b981;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.current-rank-item {
  line-height: 1.7;
}

.rank-value {
  font-weight: 600;
  color: #18181b;
}

.rank-tag {
  color: #a1a1aa;
  font-size: 12px;
  margin-left: 2px;
}

.douban-link {
  color: #6366f1;
}

.imdb-link {
  color: #e6b800;
}

.external-link {
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
}

.external-link:hover {
  text-decoration: underline;
}

.tagline {
  margin-top: 16px;
  color: #71717a;
  font-style: italic;
  font-size: 13px;
}

.detail-section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  border: 1px solid rgba(228, 228, 231, 0.6);
}

.detail-section h3 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #18181b;
}

.summary {
  font-size: 13px;
  line-height: 1.8;
  color: #52525b;
  text-indent: 2em;
  margin-bottom: 8px;
}

.single-version {
  text-align: center;
  padding: 40px;
  color: #a1a1aa;
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(228, 228, 231, 0.6);
  font-size: 13px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #a1a1aa;
  font-size: 13px;
}

@media (max-width: 640px) {
  .detail-header {
    flex-direction: column;
    align-items: center;
    padding: 20px 16px;
    gap: 16px;
  }
  .detail-poster {
    width: 160px;
  }
  .no-poster {
    width: 160px;
    height: 240px;
  }
  .detail-info {
    width: 100%;
  }
  .detail-info h1 {
    font-size: 18px;
    text-align: center;
  }
  .original-title {
    text-align: center;
  }
  .tagline {
    text-align: center;
  }
  .detail-section {
    padding: 16px;
  }
}
</style>
