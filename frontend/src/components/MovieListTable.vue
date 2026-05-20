<template>
  <div class="movie-list-table">
    <table>
      <thead>
        <tr>
          <th class="col-rank">排名</th>
          <th class="col-title">电影</th>
          <th class="col-year">年份</th>
          <th class="col-rating">评分</th>
          <th class="col-director">导演</th>
          <th class="col-genre">类型</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="movie in movies"
          :key="movie.douban_id"
          :class="{ watched: movie.watched }"
          @click="$router.push(`/movies/${movie.douban_id}`)"
        >
          <td class="col-rank">
            #{{ movie.rank }}
            <span v-if="movie.rank_change === null" class="rank-badge new">新</span>
            <span v-else-if="movie.rank_change > 0" class="rank-badge up">▲{{ movie.rank_change }}</span>
            <span v-else-if="movie.rank_change < 0" class="rank-badge down">▼{{ Math.abs(movie.rank_change) }}</span>
          </td>
          <td class="col-title">
            {{ movie.title }}
            <span v-if="movie.watched" class="watched-badge">看过</span>
          </td>
          <td class="col-year">{{ movie.year || '-' }}</td>
          <td class="col-rating">{{ movie.rating || '-' }}</td>
          <td class="col-director">{{ movie.director || '-' }}</td>
          <td class="col-genre">{{ movie.genre || '-' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({
  movies: { type: Array, required: true },
})
</script>

<style scoped>
.movie-list-table {
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

.movie-list-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.movie-list-table th {
  background: #fafafa;
  padding: 8px 12px;
  text-align: left;
  font-weight: 500;
  color: #666;
  border-bottom: 1px solid #f0f0f0;
  white-space: nowrap;
}

.movie-list-table td {
  padding: 6px 12px;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
}

.movie-list-table tr:hover td {
  background: #f5f8ff;
}

.movie-list-table tr.watched td {
  background: #f6ffed;
}

.col-rank {
  width: 90px;
  text-align: left;
  font-weight: 600;
  color: #999;
  white-space: nowrap;
}

.col-title {
  font-weight: 500;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-year { width: 60px; color: #999; }
.col-rating { width: 60px; color: #faad14; font-weight: 600; }
.col-director { max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #666; }
.col-genre { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #666; }

.rank-badge {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 2px;
  font-weight: 700;
  margin-left: 4px;
}

.rank-badge.new { background: #1890ff; color: #fff; }
.rank-badge.up { background: #52c41a; color: #fff; }
.rank-badge.down { background: #ff4d4f; color: #fff; }

.watched-badge {
  display: inline-block;
  margin-left: 6px;
  padding: 0 4px;
  background: #52c41a;
  color: #fff;
  font-size: 10px;
  border-radius: 2px;
  vertical-align: middle;
}
</style>
