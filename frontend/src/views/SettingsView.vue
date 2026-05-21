<template>
  <div class="sv">
    <!-- Header -->
    <div class="sv-header">
      <h1>系统设置</h1>
      <p class="sv-subtitle">配置爬取任务、同步策略和导入历史版本</p>
    </div>

    <!-- Cookie warning -->
    <div v-if="cookieWarning" class="cookie-warning">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      {{ cookieWarning }}
    </div>

    <!-- Crawl Status Cards -->
    <div class="grid-2">
      <!-- Top 250 -->
      <div class="card">
        <div class="card-pad">
          <div class="card-head">
            <div class="card-icon icon-violet">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/></svg>
            </div>
            <h3>Top 250 爬取</h3>
          </div>
          <div class="card-body">
            <p class="status-line" v-if="settingsStore.top250Status?.status === 'success'">
              最近一次：{{ formatTime(settingsStore.top250Status.finished_at) }}
            </p>
            <p class="status-line" v-else-if="settingsStore.top250Status?.status === 'running'">爬取中...</p>
            <p class="status-line status-error" v-else-if="settingsStore.top250Status?.status === 'failed'">失败：{{ settingsStore.top250Status.error_message }}</p>
            <p class="status-line status-muted" v-else>尚未执行</p>
            <div class="tag-row" v-if="settingsStore.top250Status?.status === 'success'">
              <span class="tag tag-green" v-if="settingsStore.top250Status.new_version_created">新版本</span>
              <span class="tag" v-else>未变化</span>
              <span class="tag-meta" v-if="settingsStore.top250Status.movies_found">{{ settingsStore.top250Status.movies_found }} 部</span>
            </div>
          </div>
          <button
            class="btn btn-dark w-full"
            :disabled="isCrawling"
            @click="onTriggerCrawl"
          >
            {{ isCrawling ? '爬取中...' : '立即爬取 Top 250' }}
          </button>
        </div>
      </div>

      <!-- Watched List -->
      <div class="card">
        <div class="card-pad">
          <div class="card-head">
            <div class="card-icon icon-sky">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            </div>
            <h3>看过列表同步</h3>
          </div>
          <div class="card-body">
            <p class="status-line" v-if="settingsStore.userWatchedStatus?.status === 'success'">
              最近一次：{{ formatTime(settingsStore.userWatchedStatus.finished_at) }}
            </p>
            <p class="status-line" v-else-if="settingsStore.userWatchedStatus?.status === 'running'">同步中...</p>
            <p class="status-line status-error" v-else-if="settingsStore.userWatchedStatus?.status === 'failed'">失败：{{ settingsStore.userWatchedStatus.error_message }}</p>
            <p class="status-line status-muted" v-else>尚未同步</p>
            <div class="tag-row" v-if="settingsStore.userWatchedStatus?.status === 'success'">
              <span class="tag">增量同步</span>
              <span class="tag-meta">{{ settingsStore.userWatchedStatus.movies_found }} 部</span>
            </div>
          </div>
          <div class="btn-row">
            <button
              class="btn btn-green flex-1"
              :disabled="isCrawling || !hasUserId"
              @click="onTriggerUserScrape"
            >
              增量同步
            </button>
            <button
              class="btn btn-outline flex-1"
              :disabled="isCrawling || !hasUserId"
              @click="onTriggerUserScrapeFull"
            >
              全量同步
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Crawl Progress (active) -->
    <div v-if="settingsStore.crawlProgress?.active" class="progress-card">
      <div class="progress-head">
        <svg class="pulse-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        <div>
          <p class="progress-title">{{ settingsStore.crawlProgress.message }}</p>
          <p class="progress-sub" v-if="settingsStore.crawlProgress.movies_found">
            已发现 {{ settingsStore.crawlProgress.movies_found }} 部电影
            <span v-if="settingsStore.crawlProgress.posters_total">，海报 {{ settingsStore.crawlProgress.posters_done }}/{{ settingsStore.crawlProgress.posters_total }}</span>
          </p>
        </div>
      </div>
      <template v-if="settingsStore.crawlProgress.phase === 'fetching_pages' && settingsStore.crawlProgress.page_total > 0">
        <div class="progress-label">
          <span>页面进度</span>
          <span class="progress-pct">{{ Math.round(settingsStore.crawlProgress.page_current / settingsStore.crawlProgress.page_total * 100) }}%</span>
        </div>
        <div class="progress-bar-track">
          <div class="progress-bar-fill gradient-indigo" :style="{ width: (settingsStore.crawlProgress.page_current / settingsStore.crawlProgress.page_total * 100) + '%' }"></div>
        </div>
      </template>
      <template v-if="settingsStore.crawlProgress.phase === 'downloading_posters' && settingsStore.crawlProgress.posters_total > 0">
        <div class="progress-label">
          <span>海报下载</span>
          <span class="progress-pct">{{ Math.round(settingsStore.crawlProgress.posters_done / settingsStore.crawlProgress.posters_total * 100) }}%</span>
        </div>
        <div class="progress-bar-track">
          <div class="progress-bar-fill gradient-indigo" :style="{ width: (settingsStore.crawlProgress.posters_done / settingsStore.crawlProgress.posters_total * 100) + '%' }"></div>
        </div>
      </template>
    </div>

    <!-- Task Cards -->
    <div class="grid-2">
      <!-- Metadata Backfill -->
      <div class="card">
        <div class="card-pad">
          <div class="card-head">
            <div class="card-icon icon-indigo">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
            </div>
            <h3>元数据补全</h3>
          </div>
          <div class="card-body" v-if="settingsStore.metadataProgress?.active">
            <p class="progress-msg">{{ settingsStore.metadataProgress.message }}</p>
            <div class="progress-label">
              <span>进度</span>
              <span class="progress-pct accent">{{ metaPercent }}%</span>
            </div>
            <div class="progress-bar-track">
              <div class="progress-bar-fill gradient-indigo" :style="{ width: metaPercent + '%' }"></div>
            </div>
            <div class="stat-row">
              <span class="stat-green">已更新 {{ settingsStore.metadataProgress.updated }}</span>
              <span class="stat-red">失败 {{ settingsStore.metadataProgress.failed }}</span>
            </div>
          </div>
          <div class="card-body" v-else-if="settingsStore.metadataStatus?.status === 'success'">
            <p class="status-line">最近一次：{{ formatTime(settingsStore.metadataStatus.finished_at) }}</p>
            <span class="tag">{{ settingsStore.metadataStatus.movies_found }} 部</span>
          </div>
          <div class="card-body" v-else-if="settingsStore.metadataStatus?.status === 'failed'">
            <p class="status-line status-error">失败：{{ settingsStore.metadataStatus.error_message }}</p>
          </div>
          <div class="card-body" v-else>
            <p class="status-line status-muted">尚未执行</p>
          </div>
          <button
            class="btn btn-outline w-full"
            :disabled="settingsStore.metadataProgress?.active || isCrawling"
            @click="onTriggerMeta"
          >
            {{ settingsStore.metadataProgress?.active ? '补全中...' : '立即补全元数据' }}
          </button>
        </div>
      </div>

      <!-- Doulist Import -->
      <div class="card" :class="{ 'card-active': isDoulistImporting }">
        <div class="card-pad">
          <div class="card-head">
            <div class="card-icon icon-emerald">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            </div>
            <h3>手动导入 Doulist</h3>
          </div>
          <div class="card-body">
            <div class="field-sm">
              <label>Doulist 链接</label>
              <input
                v-model="doulistUrl"
                placeholder="https://www.douban.com/doulist/918989/"
                :disabled="isDoulistImporting"
              />
            </div>
            <div class="field-sm">
              <label>版本日期</label>
              <input
                v-model="doulistTag"
                type="date"
                :disabled="isDoulistImporting"
              />
            </div>
            <div v-if="settingsStore.doulistImportProgress?.active" class="import-progress">
              <p class="progress-msg">{{ settingsStore.doulistImportProgress.message }}</p>
              <div class="progress-label">
                <span>页面进度</span>
                <span class="progress-pct accent">{{ doulistPercent }}%</span>
              </div>
              <div class="progress-bar-track">
                <div class="progress-bar-fill gradient-accent" :style="{ width: doulistPercent + '%' }"></div>
              </div>
              <div class="stat-row">
                <span>第 {{ settingsStore.doulistImportProgress.page_current }}/{{ settingsStore.doulistImportProgress.page_total }} 页</span>
                <span class="tag">{{ settingsStore.doulistImportProgress.movies_found }} 部</span>
              </div>
            </div>
            <p v-else-if="settingsStore.doulistImportProgress?.success" class="result-msg result-ok">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              {{ settingsStore.doulistImportProgress.message }}
            </p>
            <p v-else-if="settingsStore.doulistImportProgress?.error" class="result-msg result-err">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
              {{ settingsStore.doulistImportProgress.message }}
            </p>
          </div>
          <button
            class="btn btn-accent w-full"
            :disabled="isDoulistImporting || !doulistUrl || !doulistTag"
            @click="onDoulistImport"
          >
            <svg v-if="!isDoulistImporting" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            {{ isDoulistImporting ? '导入中...' : '导入' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Settings Form -->
    <form class="form-card" @submit.prevent="onSave">
      <!-- Scheduled Tasks -->
      <div class="form-section">
        <h4 class="form-section-title">定时任务</h4>
        <div class="field">
          <label>Top 250 Cron 表达式</label>
          <input v-model="settingsStore.cronExpression" placeholder="0 3 * * 0" />
          <span class="field-hint">每周日凌晨3点。格式：分 时 日 月 星期</span>
        </div>
        <div class="field">
          <label>看过列表同步 Cron</label>
          <input v-model="settingsStore.userScrapeCron" placeholder="留空则不自动同步" />
          <span class="field-hint">留空则只支持手动同步</span>
        </div>
        <div class="field">
          <label>元数据补全 Cron</label>
          <input v-model="settingsStore.metadataCron" placeholder="0 5 * * 0" />
          <span class="field-hint">每周日凌晨5点</span>
        </div>
      </div>

      <div class="form-divider"></div>

      <!-- Account -->
      <div class="form-section">
        <h4 class="form-section-title">账户与认证</h4>
        <div class="field">
          <label>豆瓣用户 ID</label>
          <input v-model="settingsStore.doubanUserId" placeholder="例如：166675383" />
          <span class="field-hint">配置后自动爬取该用户的"看过"列表并与 Top 250 对比</span>
        </div>
        <div class="field">
          <label>豆瓣 Cookie</label>
          <textarea v-model="settingsStore.doubanCookie" placeholder="粘贴从浏览器复制的 Cookie 字符串" rows="3"></textarea>
          <div class="field-actions">
            <button
              type="button"
              class="btn btn-ghost-sm"
              :disabled="!settingsStore.doubanCookie || settingsStore.checkingCookie"
              @click="onCheckCookie"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
              {{ settingsStore.checkingCookie ? '检查中...' : '检查有效性' }}
            </button>
            <span v-if="settingsStore.cookieCheck" :class="['check-result', settingsStore.cookieCheck.valid ? 'valid' : 'invalid']">
              <svg v-if="settingsStore.cookieCheck.valid" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
              {{ settingsStore.cookieCheck.valid ? 'Cookie 有效' : settingsStore.cookieCheck.message }}
            </span>
          </div>
          <span class="field-hint">登录豆瓣 → F12 开发者工具 → Network → 复制 Cookie</span>
        </div>
      </div>

      <div class="form-footer">
        <button type="submit" class="btn btn-dark btn-save" :disabled="settingsStore.saving">
          {{ settingsStore.saving ? '保存中...' : '保存设置' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useSettingsStore } from '../stores/settings.js'

const settingsStore = useSettingsStore()
let progressInterval = null

const doulistUrl = ref('')
const doulistTag = ref('')

const isCrawling = computed(() => settingsStore.crawlProgress?.active || false)
const isDoulistImporting = computed(() => settingsStore.doulistImportProgress?.active || false)
const hasUserId = computed(() => !!settingsStore.doubanUserId)

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
/* === Layout === */
.sv { width: 100%; }

.sv-header { margin-bottom: 32px; }
.sv-header h1 {
  font-size: 22px;
  font-weight: 600;
  color: #18181b;
  letter-spacing: -0.3px;
}
.sv-subtitle { margin-top: 4px; font-size: 13px; color: #a1a1aa; }

/* === Grid === */
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
@media (max-width: 640px) {
  .grid-2 { grid-template-columns: 1fr; }
  .card-pad { padding: 14px 16px; }
}

/* === Card (unified structure) === */
.card {
  background: #fff;
  border: 1px solid rgba(228, 228, 231, 0.6);
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.card:hover { border-color: rgba(212, 212, 216, 0.8); }
.card-active { border-color: rgba(99, 102, 241, 0.3); box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.05); }

.card-pad {
  display: flex;
  flex-direction: column;
  padding: 18px 20px;
  gap: 14px;
}

.card-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.card-head h3 {
  font-size: 13px;
  font-weight: 600;
  color: #18181b;
}

.card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  flex-shrink: 0;
}
.icon-violet { background: #f5f3ff; color: #8b5cf6; }
.icon-sky { background: #f0f9ff; color: #0ea5e9; }
.icon-indigo { background: #eef2ff; color: #6366f1; }
.icon-emerald { background: #ecfdf5; color: #10b981; }

.card-body {
  flex: 1;
}

/* === Status === */
.status-line { font-size: 12px; color: #71717a; margin: 0 0 8px; line-height: 1.5; }
.status-line:last-child { margin-bottom: 0; }
.status-error { color: #f43f5e; }
.status-muted { color: #d4d4d8; }

.tag-row { display: flex; align-items: center; gap: 6px; }
.tag {
  display: inline-block;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 500;
  border-radius: 4px;
  background: #f4f4f5;
  color: #71717a;
}
.tag-green { background: #ecfdf5; color: #10b981; }
.tag-meta { font-size: 11px; color: #a1a1aa; }

/* === Buttons === */
.btn-row { display: flex; gap: 8px; }

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 34px;
  padding: 0 14px;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
  flex-shrink: 0;
}
.btn:active:not(:disabled) { transform: scale(0.97); }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-dark { background: #18181b; color: #fff; }
.btn-dark:hover:not(:disabled) { background: #27272a; }

.btn-accent { background: #6366f1; color: #fff; }
.btn-accent:hover:not(:disabled) { background: #4f46e5; }

.btn-green { background: #10b981; color: #fff; }
.btn-green:hover:not(:disabled) { background: #059669; }

.btn-outline {
  background: transparent;
  color: #52525b;
  border: 1px solid #e4e4e7;
}
.btn-outline:hover:not(:disabled) { background: #fafafa; border-color: #d4d4d8; }

.btn-ghost-sm {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 10px;
  background: transparent;
  color: #6366f1;
  border: 1px solid #e4e4e7;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}
.btn-ghost-sm:hover:not(:disabled) { background: #eef2ff; border-color: #c7d2fe; }
.btn-ghost-sm:disabled { opacity: 0.4; cursor: not-allowed; }

.w-full { width: 100%; }
.flex-1 { flex: 1; }

/* === Progress (crawl) === */
.progress-card {
  background: #fff;
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 12px;
  padding: 18px 20px;
  margin-bottom: 16px;
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.05);
}

.progress-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 14px;
}

.pulse-icon { animation: pulse 2s infinite; flex-shrink: 0; margin-top: 1px; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.progress-title { font-size: 12px; color: #6366f1; font-weight: 500; margin: 0; }
.progress-sub { font-size: 11px; color: #a1a1aa; margin: 2px 0 0; }
.progress-msg { font-size: 12px; color: #6366f1; margin: 0; line-height: 1.5; }

.progress-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: #a1a1aa;
  margin-bottom: 6px;
}
.progress-pct { color: #71717a; font-weight: 500; }
.progress-pct.accent { color: #6366f1; }

.progress-bar-track {
  width: 100%;
  height: 4px;
  background: #f4f4f5;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 8px;
}
.progress-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.gradient-indigo { background: linear-gradient(90deg, #6366f1, #818cf8); }
.gradient-accent { background: linear-gradient(90deg, #6366f1, #818cf8); }

.stat-row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: #a1a1aa;
}
.stat-green { color: #10b981; font-weight: 500; }
.stat-red { color: #f43f5e; font-weight: 500; }

.import-progress { margin-top: 2px; }

/* === Result messages === */
.result-msg {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  margin: 0;
}
.result-ok { color: #10b981; }
.result-err { color: #f43f5e; }

/* === Cookie warning === */
.cookie-warning {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff1f2;
  border: 1px solid rgba(244, 63, 94, 0.2);
  color: #f43f5e;
  padding: 10px 14px;
  border-radius: 10px;
  margin-bottom: 20px;
  font-size: 12px;
  font-weight: 500;
  animation: slideDown 0.3s ease;
}

/* === Form === */
.form-card {
  background: #fff;
  border: 1px solid rgba(228, 228, 231, 0.6);
  border-radius: 12px;
  overflow: hidden;
}

.form-section { padding: 24px; }

.form-section-title {
  font-size: 11px;
  font-weight: 600;
  color: #a1a1aa;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 20px;
}

.form-divider {
  height: 1px;
  background: #f4f4f5;
  margin: 0 24px;
}

.field { margin-bottom: 20px; }
.field:last-child { margin-bottom: 0; }
.field label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #3f3f46;
}

.field input,
.field textarea {
  width: 100%;
  height: 36px;
  padding: 0 12px;
  border: 1px solid #e4e4e7;
  border-radius: 8px;
  font-size: 13px;
  font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace;
  color: #27272a;
  background: rgba(250, 250, 250, 0.5);
  transition: all 0.15s;
  box-sizing: border-box;
}

.field textarea {
  height: auto;
  padding: 10px 12px;
  resize: vertical;
  min-height: 68px;
  line-height: 1.5;
}

.field input::placeholder,
.field textarea::placeholder {
  color: #d4d4d8;
  font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
}

.field input:hover,
.field textarea:hover { border-color: #d4d4d8; }

.field input:focus,
.field textarea:focus {
  outline: none;
  background: #fff;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.field-hint {
  display: block;
  margin-top: 6px;
  font-size: 11px;
  color: #d4d4d8;
  line-height: 1.4;
}

.field-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}

.check-result {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
}
.check-result.valid { color: #10b981; }
.check-result.invalid { color: #f43f5e; }

/* === Doulist card fields === */
.field-sm { margin-bottom: 12px; }
.field-sm:last-of-type { margin-bottom: 0; }
.field-sm label {
  display: block;
  margin-bottom: 5px;
  font-size: 11px;
  font-weight: 500;
  color: #71717a;
}
.field-sm input {
  width: 100%;
  height: 32px;
  padding: 0 10px;
  border: 1px solid #e4e4e7;
  border-radius: 6px;
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace;
  color: #27272a;
  background: rgba(250, 250, 250, 0.5);
  transition: all 0.15s;
  box-sizing: border-box;
}
.field-sm input::placeholder {
  color: #d4d4d8;
  font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
}
.field-sm input:hover { border-color: #d4d4d8; }
.field-sm input:focus {
  outline: none;
  background: #fff;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

/* === Form footer === */
.form-footer {
  padding: 18px 24px;
  border-top: 1px solid #f4f4f5;
  display: flex;
  justify-content: flex-end;
}
.btn-save { padding: 0 24px; height: 36px; font-size: 13px; }

/* === Animations === */
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
