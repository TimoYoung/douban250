<template>
  <div class="movie-card" @click="$router.push(`/movies/${movie.douban_id}`)">
    <div class="card-rank" v-if="movie.rank != null">
      #{{ movie.rank }}
      <span v-if="movie.rank_change === null" class="rank-badge new">新</span>
      <span v-else-if="movie.rank_change > 0" class="rank-badge up">▲{{ movie.rank_change }}</span>
      <span v-else-if="movie.rank_change < 0" class="rank-badge down">▼{{ Math.abs(movie.rank_change) }}</span>
    </div>
    <div class="card-poster">
      <img v-if="movie.poster_path" :src="`/posters/${movie.poster_path}`" :alt="movie.title" loading="lazy" />
      <div v-else class="no-poster">无海报</div>
    </div>
    <div class="card-info">
      <h3 class="card-title">{{ movie.title }}</h3>
      <div class="card-meta">
        <span v-if="movie.year">{{ movie.year }}</span>
        <span v-if="movie.rating" class="card-rating">{{ movie.rating }}</span>
      </div>
      <span v-if="movie.watched" class="watched-badge">看过</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  movie: { type: Object, required: true },
})
</script>

<style scoped>
.movie-card {
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  position: relative;
}

.movie-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.card-rank {
  position: absolute;
  top: 8px;
  left: 8px;
  background: rgba(0,0,0,0.7);
  color: #fff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 4px;
}

.rank-badge {
  font-size: 10px;
  padding: 0 3px;
  border-radius: 2px;
  font-weight: 700;
}

.rank-badge.new {
  background: #1890ff;
  color: #fff;
}

.rank-badge.up {
  background: #52c41a;
  color: #fff;
}

.rank-badge.down {
  background: #ff4d4f;
  color: #fff;
}

.card-poster {
  width: 100%;
  aspect-ratio: 2/3;
  overflow: hidden;
  background: #f0f0f0;
}

.card-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-poster {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 14px;
}

.card-info {
  padding: 12px;
}

.card-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #999;
}

.card-rating {
  color: #faad14;
  font-weight: 600;
}

.watched-badge {
  display: inline-block;
  margin-top: 4px;
  padding: 1px 6px;
  background: #52c41a;
  color: #fff;
  font-size: 11px;
  border-radius: 3px;
}
</style>
