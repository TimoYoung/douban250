<template>
  <div class="settings-view">
    <h2>系统设置</h2>

    <!-- Cookie warning -->
    <div v-if="cookieWarning" class="cookie-warning">
      {{ cookieWarning }}
    </div>

    <!-- Crawl status -->
    <CrawlStatus
      :top250Status="settingsStore.top250Status"
      :userWatchedStatus="settingsStore.userWatchedStatus"
      :progress="settingsStore.crawlProgress"
      :isRunning="settingsStore.crawlProgress?.active || false"
      :hasUserId="!!settingsStore.doubanUserId"
      @triggerTop250="onTriggerCrawl"
      @triggerUserScrape="onTriggerUserScrape"
      @triggerUserScrapeFull="onTriggerUserScrapeFull"
    />

    <!-- Metadata backfill status -->
    <div class="meta-backfill-card">
      <h4>元数据补全</h4>
      <div v-if="settingsStore.metadataProgress?.active" class="meta-progress">
        <div class="progress-message">{{ settingsStore.metadataProgress.message }}</div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: metaPercent + '%' }"></div>
        </div>
        <div class="progress-detail">
          {{ settingsStore.metadataProgress.done }}/{{ settingsStore.metadataProgress.total }}
          (已更新 {{ settingsStore.metadataProgress.updated }}，失败 {{ settingsStore.metadataProgress.failed }})
        </div>
      </div>
      <div v-else-if="settingsStore.metadataStatus?.status === 'success'" class="meta-status">
        最近一次：{{ formatTime(settingsStore.metadataStatus.finished_at) }}，
        更新 {{ settingsStore.metadataStatus.movies_found }} 部
      </div>
      <div v-else-if="settingsStore.metadataStatus?.status === 'failed'" class="meta-status error">
        失败：{{ settingsStore.metadataStatus.error_message }}
      </div>
      <div v-else class="meta-status">尚未执行</div>
      <button
        class="meta-btn"
        :disabled="settingsStore.metadataProgress?.active || settingsStore.crawlProgress?.active"
        @click="onTriggerMeta"
      >
        {{ settingsStore.metadataProgress?.active ? '补全中...' : '立即补全元数据' }}
      </button>
    </div>

    <!-- Doulist import -->
    <div class="meta-backfill-card">
      <h4>手动导入 Doulist</h4>
      <div class="form-group" style="margin-bottom: 12px;">
        <label style="font-size: 13px;">Doulist 链接</label>
        <input
          v-model="doulistUrl"
          placeholder="https://www.douban.com/doulist/918989/"
          :disabled="isDoulistImporting"
        />
      </div>
      <div class="form-group" style="margin-bottom: 12px;">
        <label style="font-size: 13px;">版本日期</label>
        <input
          v-model="doulistTag"
          type="date"
          :disabled="isDoulistImporting"
        />
      </div>
      <div v-if="settingsStore.doulistImportProgress?.active" class="meta-progress">
        <div class="progress-message">{{ settingsStore.doulistImportProgress.message }}</div>
        <div v-if="settingsStore.doulistImportProgress.page_total" class="progress-bar">
          <div class="progress-fill" :style="{ width: doulistPercent + '%' }"></div>
        </div>
        <div class="progress-detail">
          第 {{ settingsStore.doulistImportProgress.page_current }}/{{ settingsStore.doulistImportProgress.page_total }} 页，
          已爬取 {{ settingsStore.doulistImportProgress.movies_found }} 部电影
        </div>
      </div>
      <div v-else-if="settingsStore.doulistImportProgress?.success" class="meta-status" style="color: #52c41a;">
        {{ settingsStore.doulistImportProgress.message }}
      </div>
      <div v-else-if="settingsStore.doulistImportProgress?.error" class="meta-status error">
        {{ settingsStore.doulistImportProgress.message }}
      </div>
      <button
        class="meta-btn"
        :disabled="isDoulistImporting || !doulistUrl || !doulistTag"
        @click="onDoulistImport"
      >
        {{ isDoulistImporting ? '导入中...' : '导入' }}
      </button>
    </div>

    <div class="settings-form">
      <div class="form-group">
        <label>Top 250 Cron 表达式</label>
        <input v-model="settingsStore.cronExpression" placeholder="0 3 * * 0" />
        <p class="hint">默认每周日凌晨3点执行。格式：分 时 日 月 星期</p>
      </div>

      <div class="form-group">
        <label>豆瓣用户 ID</label>
        <input v-model="settingsStore.doubanUserId" placeholder="例如：166675383" />
        <p class="hint">填入豆瓣用户 ID 后，系统会爬取该用户的"看过"列表并与 Top 250 对比</p>
      </div>

      <div class="form-group">
        <label>豆瓣 Cookie</label>
        <textarea v-model="settingsStore.doubanCookie" placeholder="粘贴从浏览器复制的 Cookie 字符串" rows="3"></textarea>
        <div class="cookie-actions">
          <button
            class="cookie-check-btn"
            :disabled="!settingsStore.doubanCookie || settingsStore.checkingCookie"
            @click="onCheckCookie"
          >
            {{ settingsStore.checkingCookie ? '检查中...' : '检查 Cookie 有效性' }}
          </button>
          <span v-if="settingsStore.cookieCheck" :class="['cookie-result', settingsStore.cookieCheck.valid ? 'valid' : 'invalid']">
            {{ settingsStore.cookieCheck.valid ? '有效' : settingsStore.cookieCheck.message }}
          </span>
        </div>
        <p class="hint">登录豆瓣后从浏览器开发者工具复制 Cookie。提供 Cookie 后可抓取完整的看过列表</p>
      </div>

      <div class="form-group">
        <label>看过列表同步 Cron 表达式（可选）</label>
        <input v-model="settingsStore.userScrapeCron" placeholder="留空则不自动同步" />
        <p class="hint">设置自动同步"看过"列表的周期。留空则只支持手动同步</p>
      </div>

      <div class="form-group">
        <label>元数据补全 Cron 表达式</label>
        <input v-model="settingsStore.metadataCron" placeholder="0 5 * * 0" />
        <p class="hint">定期补全缺失的电影元数据（简介、导演等）。默认每周日凌晨5点</p>
      </div>

      <button class="save-btn" :disabled="settingsStore.saving" @click="onSave">
        {{ settingsStore.saving ? '保存中...' : '保存设置' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useSettingsStore } from '../stores/settings.js'
import CrawlStatus from '../components/CrawlStatus.vue'

const settingsStore = useSettingsStore()
let progressInterval = null

const doulistUrl = ref('')
const doulistTag = ref('')

const isDoulistImporting = computed(() => settingsStore.doulistImportProgress?.active || false)

const cookieWarning = computed(() => {
  if (settingsStore.doubanCookie && settingsStore.cookieCheck && !settingsStore.cookieCheck.valid) {
    return settingsStore.cookieCheck.message
  }
  return null
})

const metaPercent = computed(() => {
  const p = settingsStore.metadataProgress
  if (!p || p.total === 0) return 0
  return Math.round(p.done / p.total * 100)
})

const doulistPercent = computed(() => {
  const p = settingsStore.doulistImportProgress
  if (!p || !p.page_total) return 0
  return Math.round(p.page_current / p.page_total * 100)
})

onMounted(async () => {
  await Promise.all([
    settingsStore.loadSettings(),
    settingsStore.loadTop250Status(),
    settingsStore.loadUserWatchedStatus(),
    settingsStore.loadCrawlProgress(),
    settingsStore.loadMetadataProgress(),
    settingsStore.loadMetadataStatus(),
    settingsStore.loadCookieCheck(),
    settingsStore.loadDoulistImportProgress(),
  ])
  progressInterval = setInterval(async () => {
    await settingsStore.loadCrawlProgress()
    await settingsStore.loadMetadataProgress()
    await settingsStore.loadDoulistImportProgress()
    if (!settingsStore.crawlProgress?.active && !settingsStore.metadataProgress?.active) {
      await Promise.all([
        settingsStore.loadTop250Status(),
        settingsStore.loadUserWatchedStatus(),
        settingsStore.loadMetadataStatus(),
      ])
    }
  }, 2000)
})

onUnmounted(() => {
  if (progressInterval) clearInterval(progressInterval)
})

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

async function onSave() {
  await settingsStore.saveSettings()
  await settingsStore.loadCookieCheck()
}

async function onCheckCookie() {
  await settingsStore.checkCookie()
}

async function onTriggerCrawl() {
  await settingsStore.triggerCrawl()
}

async function onTriggerUserScrape() {
  await settingsStore.triggerUserScrape()
}

async function onTriggerUserScrapeFull() {
  await settingsStore.triggerUserScrape(true)
}

async function onTriggerMeta() {
  await settingsStore.triggerMetadataBackfill()
}

async function onDoulistImport() {
  if (!doulistUrl.value || !doulistTag.value) return
  await settingsStore.triggerDoulistImport(doulistUrl.value, doulistTag.value)
}
</script>

<style scoped>
.settings-view h2 {
  margin-bottom: 16px;
}

.cookie-warning {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: #ff4d4f;
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 14px;
}

.cookie-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.cookie-check-btn {
  padding: 4px 12px;
  background: #fff;
  color: #1890ff;
  border: 1px solid #1890ff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.cookie-check-btn:hover:not(:disabled) {
  background: #e6f7ff;
}

.cookie-check-btn:disabled {
  color: #d9d9d9;
  border-color: #d9d9d9;
  cursor: not-allowed;
}

.cookie-result {
  font-size: 13px;
}

.cookie-result.valid {
  color: #52c41a;
}

.cookie-result.invalid {
  color: #ff4d4f;
}

.meta-backfill-card {
  background: #f6f8fa;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.meta-backfill-card h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #333;
}

.meta-status {
  font-size: 13px;
  color: #555;
  margin-bottom: 12px;
}

.meta-status.error {
  color: #ff4d4f;
}

.meta-progress {
  margin-bottom: 12px;
}

.progress-message {
  font-size: 13px;
  color: #0050b3;
  margin-bottom: 6px;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: #d9d9d9;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 4px;
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

.meta-btn {
  padding: 6px 16px;
  background: #1890ff;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.meta-btn:hover:not(:disabled) {
  background: #40a9ff;
}

.meta-btn:disabled {
  background: #d9d9d9;
  color: #999;
  cursor: not-allowed;
}

.settings-form {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.form-group input,
.form-group textarea {
  width: 100%;
  max-width: 600px;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  font-family: monospace;
}

.form-group textarea {
  resize: vertical;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24,144,255,0.2);
}

.hint {
  margin-top: 4px;
  font-size: 12px;
  color: #999;
}

.save-btn {
  padding: 8px 24px;
  background: #1890ff;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.save-btn:hover:not(:disabled) {
  background: #40a9ff;
}

.save-btn:disabled {
  background: #d9d9d9;
  color: #999;
  cursor: not-allowed;
}
</style>
