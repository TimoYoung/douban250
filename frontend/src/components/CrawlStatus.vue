<template>
  <div class="crawl-status-section">
    <!-- Top 250 crawl status -->
    <div class="status-card">
      <h4>Top 250 爬取</h4>
      <div class="status-info" v-if="top250Status">
        <p v-if="top250Status.status === 'running'" class="running">
          爬取中...
        </p>
        <p v-else-if="top250Status.status === 'success'">
          最近一次：{{ formatTime(top250Status.finished_at) }}
          <span v-if="top250Status.new_version_created" class="tag new">新版本</span>
          <span v-else class="tag unchanged">未变化</span>
        </p>
        <p v-else-if="top250Status.status === 'failed'" class="error">
          失败：{{ top250Status.error_message }}
        </p>
        <p v-else class="never">尚未执行</p>
      </div>
      <button
        class="crawl-btn"
        :disabled="isRunning"
        @click="$emit('triggerTop250')"
      >
        {{ progress && progress.job_type === 'top250' && progress.active ? '爬取中...' : '立即爬取 Top 250' }}
      </button>
    </div>

    <!-- User watched scrape status -->
    <div class="status-card">
      <h4>看过列表同步</h4>
      <div class="status-info" v-if="userWatchedStatus">
        <p v-if="userWatchedStatus.status === 'running'" class="running">
          同步中...
        </p>
        <p v-else-if="userWatchedStatus.status === 'success'">
          最近一次：{{ formatTime(userWatchedStatus.finished_at) }}
          <span class="tag">{{ userWatchedStatus.movies_found }} 部</span>
        </p>
        <p v-else-if="userWatchedStatus.status === 'failed'" class="error">
          失败：{{ userWatchedStatus.error_message }}
        </p>
        <p v-else class="never">尚未同步</p>
      </div>
      <div class="user-btns">
        <button
          class="crawl-btn user-btn"
          :disabled="isRunning || !hasUserId"
          @click="$emit('triggerUserScrape')"
          :title="!hasUserId ? '请先配置豆瓣用户 ID' : ''"
        >
          {{ progress && progress.job_type === 'user_watched' && progress.active ? '同步中...' : '增量同步' }}
        </button>
        <button
          class="crawl-btn user-btn full-btn"
          :disabled="isRunning || !hasUserId"
          @click="$emit('triggerUserScrapeFull')"
          :title="!hasUserId ? '请先配置豆瓣用户 ID' : '全量同步会爬取所有页并清理已删除条目'"
        >
          全量同步
        </button>
      </div>
      <p v-if="!hasUserId" class="hint">请先配置豆瓣用户 ID</p>
      <p v-else class="hint">增量同步仅抓取新标记的电影，全量同步会扫描全部并清理已删除条目</p>
    </div>

    <!-- Progress display -->
    <div v-if="progress && progress.active" class="progress-panel">
      <div class="progress-message">{{ progress.message }}</div>
      <div v-if="progress.phase === 'fetching_pages' && progress.page_total > 0" class="progress-bar">
        <div class="progress-fill" :style="{ width: (progress.page_current / progress.page_total * 100) + '%' }"></div>
      </div>
      <div v-if="progress.phase === 'downloading_posters' && progress.posters_total > 0" class="progress-bar">
        <div class="progress-fill" :style="{ width: (progress.posters_done / progress.posters_total * 100) + '%' }"></div>
      </div>
      <div class="progress-detail" v-if="progress.movies_found > 0">
        已发现 {{ progress.movies_found }} 部电影
        <span v-if="progress.posters_total > 0">，海报 {{ progress.posters_done }}/{{ progress.posters_total }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  top250Status: { type: Object, default: null },
  userWatchedStatus: { type: Object, default: null },
  progress: { type: Object, default: null },
  isRunning: { type: Boolean, default: false },
  hasUserId: { type: Boolean, default: false },
})
defineEmits(['triggerTop250', 'triggerUserScrape', 'triggerUserScrapeFull'])

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}
</script>

<style scoped>
.crawl-status-section {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.status-card {
  flex: 1;
  min-width: 240px;
  background: #f6f8fa;
  border-radius: 8px;
  padding: 16px;
}

.status-card h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #333;
}

.status-info {
  margin-bottom: 12px;
}

.status-info p {
  font-size: 13px;
  color: #555;
  margin: 0;
}

.running { color: #1890ff; font-weight: 500; }
.error { color: #ff4d4f; }
.never { color: #999; }

.tag {
  display: inline-block;
  margin-left: 4px;
  padding: 0 6px;
  font-size: 11px;
  border-radius: 3px;
  background: #e8e8e8;
  color: #666;
}

.tag.new {
  background: #f6ffed;
  color: #52c41a;
}

.tag.unchanged {
  background: #fff7e6;
  color: #fa8c16;
}

.crawl-btn {
  padding: 6px 16px;
  background: #1890ff;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.crawl-btn:hover:not(:disabled) {
  background: #40a9ff;
}

.crawl-btn:disabled {
  background: #d9d9d9;
  color: #999;
  cursor: not-allowed;
}

.user-btns {
  display: flex;
  gap: 8px;
}

.user-btn {
  background: #52c41a;
}

.full-btn {
  background: #722ed1;
}

.full-btn:hover:not(:disabled) {
  background: #9254de;
}

.user-btn:hover:not(:disabled) {
  background: #73d13d;
}

.hint {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

.progress-panel {
  width: 100%;
  background: #e6f7ff;
  border: 1px solid #91d5ff;
  border-radius: 6px;
  padding: 12px 16px;
  margin-top: 8px;
}

.progress-message {
  font-size: 13px;
  color: #0050b3;
  margin-bottom: 8px;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: #d9d9d9;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}

.progress-fill {
  height: 100%;
  background: #1890ff;
  border-radius: 3px;
  transition: width 0.3s;
}

.progress-detail {
  font-size: 12px;
  color: #666;
}
</style>
