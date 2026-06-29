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
            <template v-if="movie.rank != null">
              #{{ movie.rank }}
              <span v-if="movie.rank_change === null" class="rank-badge new">新</span>
              <span v-else-if="movie.rank_change > 0" class="rank-badge up">▲{{ movie.rank_change }}</span>
              <span v-else-if="movie.rank_change < 0" class="rank-badge down">▼{{ Math.abs(movie.rank_change) }}</span>
            </template>
            <span v-else>-</span>
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
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(228, 228, 231, 0.6);
}

.movie-list-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.movie-list-table th {
  background: #fafafa;
  padding: 10px 16px;
  text-align: left;
  font-weight: 500;
  color: #a1a1aa;
  border-bottom: 1px solid #f4f4f5;
  white-space: nowrap;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.movie-list-table td {
  padding: 8px 16px;
  border-bottom: 1px solid #f4f4f5;
  cursor: pointer;
}

.movie-list-table tr:last-child td {
  border-bottom: none;
}

.movie-list-table tr:hover td {
  background: #f5f3ff;
}

.movie-list-table tr.watched td {
  background: #ecfdf5;
}

.col-rank {
  width: 100px;
  text-align: left;
  font-weight: 600;
  color: #a1a1aa;
  white-space: nowrap;
}

.col-title {
  font-weight: 500;
  color: #18181b;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-year { width: 70px; color: #a1a1aa; }
.col-rating { width: 70px; color: #f59e0b; font-weight: 600; }
.col-director { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #71717a; }
.col-genre { max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #71717a; }

.rank-badge {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  font-weight: 600;
  margin-left: 4px;
}

.rank-badge.new { background: #6366f1; color: #fff; }
.rank-badge.up { background: #10b981; color: #fff; }
.rank-badge.down { background: #f43f5e; color: #fff; }

.watched-badge {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 5px;
  background: #10b981;
  color: #fff;
  font-size: 10px;
  border-radius: 4px;
  vertical-align: middle;
  font-weight: 500;
}
</style>
