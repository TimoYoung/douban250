<template>
  <div class="version-diff" v-if="diff">
    <div class="diff-header">
      <h3>{{ diff.version_a.tag }} → {{ diff.version_b.tag }}</h3>
    </div>

    <div class="diff-section" v-if="diff.added.length">
      <h4>新增电影 ({{ diff.added.length }})</h4>
      <div class="diff-movie-list">
        <div v-for="m in diff.added" :key="m.douban_id" class="diff-movie added clickable"
             @click="$router.push(`/movies/${m.douban_id}`)">
          <span class="diff-rank">#{{ m.rank }}</span>
          <span>{{ m.title }}</span>
        </div>
      </div>
    </div>

    <div class="diff-section" v-if="diff.removed.length">
      <h4>移除电影 ({{ diff.removed.length }})</h4>
      <div class="diff-movie-list">
        <div v-for="m in diff.removed" :key="m.douban_id" class="diff-movie removed clickable"
             @click="$router.push(`/movies/${m.douban_id}`)">
          <span class="diff-rank">#{{ m.rank }}</span>
          <span>{{ m.title }}</span>
        </div>
      </div>
    </div>

    <div class="diff-section" v-if="diff.rank_up.length">
      <h4>排名上升最多</h4>
      <table class="rank-table">
        <thead>
          <tr><th>电影</th><th>原排名</th><th>新排名</th><th>变化</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in diff.rank_up" :key="r.douban_id" class="clickable-row"
              @click="$router.push(`/movies/${r.douban_id}`)">
            <td>{{ r.title }}</td>
            <td>#{{ r.old_rank }}</td>
            <td>#{{ r.new_rank }}</td>
            <td class="up">+{{ r.delta }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="diff-section" v-if="diff.rank_down.length">
      <h4>排名下降最多</h4>
      <table class="rank-table">
        <thead>
          <tr><th>电影</th><th>原排名</th><th>新排名</th><th>变化</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in diff.rank_down" :key="r.douban_id" class="clickable-row"
              @click="$router.push(`/movies/${r.douban_id}`)">
            <td>{{ r.title }}</td>
            <td>#{{ r.old_rank }}</td>
            <td>#{{ r.new_rank }}</td>
            <td class="down">{{ r.delta }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
defineProps({
  diff: { type: Object, default: null },
})
</script>

<style scoped>
.version-diff {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
}

.diff-header h3 {
  margin-bottom: 16px;
  color: #333;
}

.diff-section {
  margin-bottom: 24px;
}

.diff-section h4 {
  margin-bottom: 12px;
  color: #555;
  font-size: 15px;
}

.diff-movie-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.diff-movie {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
}

.clickable {
  cursor: pointer;
  transition: opacity 0.15s;
}

.clickable:hover {
  opacity: 0.8;
}

.diff-movie.added {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
}

.diff-movie.removed {
  background: #fff2f0;
  border: 1px solid #ffccc7;
}

.diff-rank {
  font-weight: 600;
  margin-right: 4px;
}

.rank-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.rank-table th,
.rank-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
  text-align: left;
}

.rank-table th {
  background: #fafafa;
  font-weight: 500;
}

.clickable-row {
  cursor: pointer;
}

.clickable-row:hover td {
  background: #f5f8ff;
}

.up {
  color: #52c41a;
  font-weight: 600;
}

.down {
  color: #ff4d4f;
  font-weight: 600;
}
</style>
