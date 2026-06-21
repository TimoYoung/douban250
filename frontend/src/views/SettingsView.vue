<template>
  <div class="sv">
    <!-- Header -->
    <div class="sv-header">
      <h1>控制台</h1>
      <p class="sv-subtitle">管理版本、爬取任务和系统配置</p>
    </div>

    <!-- Cookie warning -->
    <div v-if="cookieWarning" class="cookie-warning">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      {{ cookieWarning }}
    </div>

    <!-- Section: 版本管理 (admin only) -->
    <div class="section" v-if="isAdmin">
      <h4 class="section-title">版本管理</h4>

      <!-- Create Version: two side-by-side cards -->
      <div class="grid-2">
        <!-- 抓取豆瓣 Top 250 -->
        <div class="card card-stretch" :class="{ 'card-active': isCrawling }">
          <div class="card-pad">
            <div class="card-head">
              <div class="card-icon icon-violet">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></svg>
              </div>
              <div>
                <h3>抓取豆瓣 Top 250</h3>
                <p class="card-subtitle">从豆瓣抓取最新的 Top 250 排行榜数据</p>
              </div>
            </div>
            <div class="card-body">
              <p class="status-line" v-if="settingsStore.top250Status?.status === 'success'">
                最近一次：{{ formatTime(settingsStore.top250Status.finished_at) }}
              </p>
              <p class="status-line" v-else-if="settingsStore.top250Status?.status === 'running'">爬取中...</p>
              <p class="status-line status-error" v-else-if="settingsStore.top250Status?.status === 'failed'">失败：{{ settingsStore.top250Status.error_message }}，系统将自动重试</p>
              <p class="status-line status-muted" v-else>尚未执行</p>
              <div class="tag-row" v-if="settingsStore.top250Status?.status === 'success'">
                <span class="tag tag-green" v-if="settingsStore.top250Status.new_version_created">新版本</span>
                <span class="tag" v-else>未变化</span>
                <span class="tag-meta" v-if="settingsStore.top250Status.movies_found">{{ settingsStore.top250Status.movies_found }} 部</span>
              </div>
              <!-- Crawl Progress -->
              <div v-if="settingsStore.crawlProgress?.active" class="crawl-progress">
                <p class="progress-msg">{{ settingsStore.crawlProgress.message }}</p>
                <div v-if="settingsStore.crawlProgress.phase === 'fetching_pages' && settingsStore.crawlProgress.page_total > 0" class="progress-label">
                  <span>页面进度</span>
                  <span class="progress-pct accent">{{ Math.round(settingsStore.crawlProgress.page_current / settingsStore.crawlProgress.page_total * 100) }}%</span>
                </div>
                <div v-if="settingsStore.crawlProgress.phase === 'fetching_pages' && settingsStore.crawlProgress.page_total > 0" class="progress-bar-track">
                  <div class="progress-bar-fill gradient-indigo" :style="{ width: (settingsStore.crawlProgress.page_current / settingsStore.crawlProgress.page_total * 100) + '%' }"></div>
                </div>
                <div v-if="settingsStore.crawlProgress.phase === 'downloading_posters' && settingsStore.crawlProgress.posters_total > 0" class="progress-label">
                  <span>海报下载</span>
                  <span class="progress-pct accent">{{ Math.round(settingsStore.crawlProgress.posters_done / settingsStore.crawlProgress.posters_total * 100) }}%</span>
                </div>
                <div v-if="settingsStore.crawlProgress.phase === 'downloading_posters' && settingsStore.crawlProgress.posters_total > 0" class="progress-bar-track">
                  <div class="progress-bar-fill gradient-indigo" :style="{ width: (settingsStore.crawlProgress.posters_done / settingsStore.crawlProgress.posters_total * 100) + '%' }"></div>
                </div>
                <p class="progress-sub" v-if="settingsStore.crawlProgress.movies_found">
                  已发现 {{ settingsStore.crawlProgress.movies_found }} 部电影
                  <span v-if="settingsStore.crawlProgress.posters_total">，海报 {{ settingsStore.crawlProgress.posters_done }}/{{ settingsStore.crawlProgress.posters_total }}</span>
                </p>
              </div>
              <div class="cron-inline">
                <label>Cron</label>
                <input v-model="settingsStore.cronExpression" placeholder="0 9 * * 1" class="cron-input" />
                <button v-if="settingsStore.cronExpression !== savedCron" class="cron-save" @click="onSaveCron('cron')">保存</button>
                <span v-else class="cron-hint">默认 0 9 * * 1（每周一上午9点）</span>
              </div>
              <div v-if="cronNextRun('cron')" class="cron-next">
                下次运行: {{ cronNextRun('cron') }}
              </div>
              <!-- Auto Execution Status -->
              <div v-if="settingsStore.top250Retry && settingsStore.top250Retry.status !== 'exhausted'" class="retry-status">
                <div class="retry-header">
                  <span class="retry-label">自动执行状态</span>
                  <span class="retry-tag" :class="'retry-' + settingsStore.top250Retry.status">
                    {{ retryStatusText(settingsStore.top250Retry.status) }}
                  </span>
                </div>
                <div v-if="settingsStore.top250Retry.status === 'pending'" class="retry-info">
                  <span class="retry-count">第 {{ settingsStore.top250Retry.retry_count }}/{{ settingsStore.top250Retry.max_retries }} 次重试</span>
                  <span class="retry-time">下次自动执行: {{ formatRetryTime(settingsStore.top250Retry.next_retry) }}</span>
                </div>
                <div v-if="settingsStore.top250Retry.last_error" class="retry-error" :title="settingsStore.top250Retry.last_error">
                  {{ truncateError(settingsStore.top250Retry.last_error) }}
                </div>
                <button v-if="settingsStore.top250Retry.status === 'pending'" class="btn btn-outline btn-sm" @click="onCancelRetry('top250')">
                  取消自动重试
                </button>
              </div>
            </div>
            <button class="btn btn-dark w-full" :disabled="isCrawling" @click="onTriggerCrawl">
              {{ isCrawling ? '抓取中...' : '立即抓取' }}
            </button>
          </div>
        </div>

        <!-- 抓取 IMDb Top 250 -->
        <div class="card card-stretch" :class="{ 'card-active': isImdbCrawling }">
          <div class="card-pad">
            <div class="card-head">
              <div class="card-icon icon-amber">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></svg>
              </div>
              <div>
                <h3>抓取 IMDb Top 250</h3>
                <p class="card-subtitle">从 IMDb 抓取 Top 250 排行榜并与豆瓣电影关联</p>
              </div>
            </div>
            <div class="card-body">
              <p class="status-line" v-if="settingsStore.imdbProgress?.status === 'done'">
                {{ imdbDoneMessage }}
              </p>
              <div v-if="settingsStore.imdbProgress?.status === 'done'" class="tag-row">
                <span class="tag tag-green" v-if="settingsStore.imdbProgress.new_version">新版本</span>
                <span class="tag" v-else-if="settingsStore.imdbProgress.new_version === false">未变化</span>
                <span v-if="settingsStore.imdbProgress.matched" class="tag-meta">{{ settingsStore.imdbProgress.matched }} 部</span>
                <span class="tag tag-amber" v-if="settingsStore.pendingMatchCount > 0">{{ settingsStore.pendingMatchCount }} 部待确认</span>
              </div>
              <p class="status-line status-error" v-else-if="settingsStore.imdbProgress?.status === 'error'">
                失败：{{ settingsStore.imdbProgress.message }}，系统将自动重试
              </p>
              <p class="status-line status-muted" v-else-if="!settingsStore.imdbProgress || settingsStore.imdbProgress.status === 'idle'">尚未执行</p>
              <!-- IMDb Crawl Progress -->
              <div v-if="settingsStore.imdbProgress?.status === 'running'" class="crawl-progress">
                <p class="progress-msg">{{ settingsStore.imdbProgress.message || '爬取中...' }}</p>
                <div v-if="settingsStore.imdbProgress.total > 0" class="progress-label">
                  <span>{{ settingsStore.imdbProgress.phase === 'matching' ? '匹配进度' : '进度' }}</span>
                  <span class="progress-pct accent">{{ Math.round(settingsStore.imdbProgress.current / settingsStore.imdbProgress.total * 100) }}%</span>
                </div>
                <div v-if="settingsStore.imdbProgress.total > 0" class="progress-bar-track">
                  <div class="progress-bar-fill gradient-amber" :style="{ width: (settingsStore.imdbProgress.current / settingsStore.imdbProgress.total * 100) + '%' }"></div>
                </div>
                <p class="progress-sub">
                  <span v-if="settingsStore.imdbProgress.current">{{ settingsStore.imdbProgress.current }}/{{ settingsStore.imdbProgress.total }}</span>
                  <span v-if="settingsStore.imdbProgress.matched"> · 匹配 {{ settingsStore.imdbProgress.matched }}（新建 {{ settingsStore.imdbProgress.created || 0 }}）</span>
                  <span v-if="settingsStore.imdbProgress.pending"> · 待确认 {{ settingsStore.imdbProgress.pending }}</span>
                </p>
              </div>
              <div class="cron-inline">
                <label>Cron</label>
                <input v-model="settingsStore.imdbCron" placeholder="0 4 * * *" class="cron-input" />
                <button v-if="settingsStore.imdbCron !== savedImdbCron" class="cron-save" @click="onSaveCron('imdb')">保存</button>
                <span v-else class="cron-hint">默认 0 4 * * *（每天凌晨4点）</span>
              </div>
              <div v-if="cronNextRun('imdb')" class="cron-next">
                下次运行: {{ cronNextRun('imdb') }}
              </div>
              <!-- Auto Execution Status -->
              <div v-if="settingsStore.imdbRetry && settingsStore.imdbRetry.status !== 'exhausted'" class="retry-status">
                <div class="retry-header">
                  <span class="retry-label">自动执行状态</span>
                  <span class="retry-tag" :class="'retry-' + settingsStore.imdbRetry.status">
                    {{ retryStatusText(settingsStore.imdbRetry.status) }}
                  </span>
                </div>
                <div v-if="settingsStore.imdbRetry.status === 'pending'" class="retry-info">
                  <span class="retry-count">第 {{ settingsStore.imdbRetry.retry_count }}/{{ settingsStore.imdbRetry.max_retries }} 次重试</span>
                  <span class="retry-time">下次自动执行: {{ formatRetryTime(settingsStore.imdbRetry.next_retry) }}</span>
                </div>
                <div v-if="settingsStore.imdbRetry.last_error" class="retry-error" :title="settingsStore.imdbRetry.last_error">
                  {{ truncateError(settingsStore.imdbRetry.last_error) }}
                </div>
                <button v-if="settingsStore.imdbRetry.status === 'pending'" class="btn btn-outline btn-sm" @click="onCancelRetry('imdb')">
                  取消自动重试
                </button>
              </div>
            </div>
            <button class="btn btn-dark w-full" :disabled="isImdbCrawling" @click="onTriggerImdbCrawl">
              {{ isImdbCrawling ? '抓取中...' : '立即抓取' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Retry Settings -->
      <div class="card">
        <div class="card-pad">
          <div class="card-head">
            <div class="card-icon icon-indigo">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
            </div>
            <div>
              <h3>自动执行配置</h3>
              <p class="card-subtitle">配置爬虫失败后的自动重试策略</p>
            </div>
          </div>
          <div class="card-body">
            <div class="retry-settings-row">
              <div class="retry-setting">
                <label>自动重试间隔（秒）</label>
                <input v-model.number="settingsStore.retryInterval" type="number" min="60" max="86400" class="retry-input" />
                <span class="retry-hint">默认 3600（1小时）</span>
              </div>
              <div class="retry-setting">
                <label>最大自动重试次数</label>
                <input v-model.number="settingsStore.maxRetries" type="number" min="1" max="10" class="retry-input" />
                <span class="retry-hint">默认 3 次</span>
              </div>
            </div>
          </div>
          <button class="btn btn-outline w-full" :disabled="settingsStore.saving" @click="onSaveRetrySettings">
            {{ settingsStore.saving ? '保存中...' : '保存自动执行配置' }}
          </button>
        </div>
      </div>

      <!-- Pending Matches -->
      <PendingMatches />

      <!-- Version List -->
      <div class="card">
        <div class="card-pad">
          <div class="card-head">
            <div class="card-icon icon-emerald">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
            </div>
            <h3>版本列表</h3>
            <div class="source-tabs">
              <button
                v-for="s in sourceOptions"
                :key="s.value"
                class="source-tab"
                :class="{ active: versionSourceFilter === s.value }"
                @click="versionSourceFilter = s.value; versionPage = 1"
              >{{ s.label }}<span v-if="s.count != null" class="tab-count">{{ s.count }}</span></button>
            </div>
          </div>
          <div v-if="isAdmin && selectedVersionIds.length > 0" class="backup-toolbar">
            <span class="backup-count">已选 {{ selectedVersionIds.length }} 个版本</span>
            <button class="btn-link" @click="selectAllVersions">全选</button>
            <span class="sep">|</span>
            <button class="btn-link" @click="invertSelection">反选</button>
            <button class="btn btn-dark btn-sm" @click="onCreateBackup" :disabled="backupProgress.active">
              创建备份
            </button>
          </div>
          <div class="version-table-wrap">
            <table class="version-table">
              <thead>
                <tr>
                  <th v-if="isAdmin" class="th-checkbox">
                    <input type="checkbox" :checked="isAllPageSelected" @change="togglePageSelection" />
                  </th>
                  <th class="th-sortable" @click="toggleSort('tag')">
                    版本日期
                    <span class="sort-icon" v-if="sortField === 'tag'">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
                    <span class="sort-icon sort-idle" v-else>↕</span>
                  </th>
                  <th>来源</th>
                  <th>电影数量</th>
                  <th class="th-sortable" @click="toggleSort('crawled_at')">
                    抓取时间
                    <span class="sort-icon" v-if="sortField === 'crawled_at'">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
                    <span class="sort-icon sort-idle" v-else>↕</span>
                  </th>
                  <th class="th-actions">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="v in pagedVersions" :key="v.id">
                  <td v-if="isAdmin">
                    <input type="checkbox" :value="v.id" v-model="selectedVersionIds" />
                  </td>
                  <td>
                    <template v-if="editingId === v.id">
                      <input v-model="editTag" type="date" class="edit-input" @keyup.enter="onSaveEdit(v.id)" @keyup.escape="cancelEdit" />
                    </template>
                    <template v-else>
                      <span class="version-tag">{{ v.tag }}</span>
                      <span v-if="v.status === 'pending_confirmation'" class="version-pending-badge">待确认</span>
                    </template>
                  </td>
                  <td>
                    <span class="source-badge" :class="v.source === 'imdb' ? 'source-imdb' : 'source-douban'">
                      {{ v.source === 'imdb' ? 'IMDb' : '豆瓣' }}
                    </span>
                  </td>
                  <td>{{ v.movie_count }} 部</td>
                  <td class="td-time">{{ formatTime(v.crawled_at) }}</td>
                  <td class="td-actions">
                    <template v-if="editingId === v.id">
                      <button class="action-btn action-save" @click="onSaveEdit(v.id)" title="保存">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                      </button>
                      <button class="action-btn" @click="cancelEdit" title="取消">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                      </button>
                    </template>
                    <template v-else>
                      <button class="action-btn" @click="startEdit(v)" title="修改日期">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                      </button>
                      <button class="action-btn action-delete" @click="onDelete(v)" title="删除">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                      </button>
                    </template>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <PaginationBar
            :page="versionPage"
            :pageSize="versionPageSize"
            :totalPages="versionTotalPages"
            :total="sortedVersions.length"
            @update:page="versionPage = $event"
            @update:pageSize="onVersionPageSizeChange"
          />

          <!-- 备份进度 -->
          <div v-if="isAdmin && backupProgress.active && backupProgress.type === 'backup'" class="backup-progress">
            <div class="progress-header">
              <span class="progress-title">正在备份...</span>
              <span class="progress-percent">{{ backupProgress.percent }}%</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: backupProgress.percent + '%' }"></div>
            </div>
            <div class="progress-detail">
              <span>{{ backupProgress.detail || backupProgress.message }}</span>
              <span class="progress-time">已耗时 {{ formatTime(backupProgress.elapsed_seconds) }}</span>
            </div>
          </div>

          <!-- 备份完成 -->
          <div v-else-if="isAdmin && backupResult && backupResult.success" class="backup-result">
            <div class="result-icon">✅</div>
            <div class="result-info">
              <p class="result-title">备份成功！</p>
              <p>文件：{{ backupResult.filename }}</p>
              <p>大小：{{ formatSize(backupResult.file_size) }}</p>
              <p>内容：{{ backupResult.version_count }} 个版本、{{ backupResult.movie_count }} 部电影、{{ backupResult.poster_count }} 张海报</p>
              <p>耗时：{{ backupResult.elapsed_seconds }} 秒</p>
            </div>
            <button class="btn btn-outline" @click="backupResult = null">关闭</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Section: 数据维护 -->
    <div class="section">
      <h4 class="section-title">数据维护</h4>
      <div class="grid-2">
        <!-- Metadata Backfill (admin only) -->
        <div class="card" v-if="isAdmin">
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
            <div class="cron-inline">
              <label>Cron</label>
              <input v-model="settingsStore.metadataCron" placeholder="0 5 * * 0" class="cron-input" />
              <button v-if="settingsStore.metadataCron !== savedMetaCron" class="cron-save" @click="onSaveCron('meta')">保存</button>
              <span v-else class="cron-hint">默认 0 5 * * 0（每周日凌晨5点）</span>
            </div>
            <div class="btn-row">
              <button class="btn btn-dark flex-1" :disabled="settingsStore.metadataProgress?.active || isCrawling" @click="onTriggerMeta('incremental')">
                {{ settingsStore.metadataProgress?.active ? '补全中...' : '增量补全' }}
              </button>
              <button class="btn btn-outline flex-1" :disabled="settingsStore.metadataProgress?.active || isCrawling" @click="onTriggerMeta('full')">
                全量覆盖
              </button>
            </div>
          </div>
        </div>

        <!-- Watched Sync -->
        <div class="card">
          <div class="card-pad">
            <div class="card-head">
              <div class="card-icon icon-sky">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              </div>
              <h3>看过列表同步</h3>
            </div>
            <div class="card-body">
              <!-- Sync progress -->
              <div v-if="settingsStore.crawlProgress?.active && settingsStore.crawlProgress?.job_type === 'user_watched'" class="crawl-progress">
                <p class="progress-msg">{{ settingsStore.crawlProgress.message }}</p>
                <div v-if="settingsStore.crawlProgress.page_total > 0" class="progress-label">
                  <span>页面进度</span>
                  <span class="progress-pct accent">{{ Math.round(settingsStore.crawlProgress.page_current / settingsStore.crawlProgress.page_total * 100) }}%</span>
                </div>
                <div v-if="settingsStore.crawlProgress.page_total > 0" class="progress-bar-track">
                  <div class="progress-bar-fill gradient-indigo" :style="{ width: (settingsStore.crawlProgress.page_current / settingsStore.crawlProgress.page_total * 100) + '%' }"></div>
                </div>
                <p class="progress-sub" v-if="settingsStore.crawlProgress.movies_found">
                  已发现 {{ settingsStore.crawlProgress.movies_found }} 部电影
                </p>
              </div>
              <!-- Status (when not actively syncing) -->
              <template v-else>
                <p class="status-line" v-if="settingsStore.userWatchedStatus?.status === 'success'">
                  最近一次：{{ formatTime(settingsStore.userWatchedStatus.finished_at) }}
                </p>
                <p class="status-line status-error" v-else-if="settingsStore.userWatchedStatus?.status === 'failed'">失败：{{ settingsStore.userWatchedStatus.error_message }}</p>
                <p class="status-line status-muted" v-else>尚未同步</p>
                <div class="tag-row" v-if="settingsStore.userWatchedStatus?.status === 'success'">
                  <span class="tag">增量同步</span>
                  <span class="tag-meta">{{ settingsStore.userWatchedStatus.movies_found }} 部</span>
                </div>
              </template>
              <div class="cron-inline">
                <label>Cron</label>
                <input v-model="settingsStore.userScrapeCron" placeholder="留空则不自动同步" class="cron-input" />
                <button v-if="settingsStore.userScrapeCron !== savedUserCron" class="cron-save" @click="onSaveCron('user')">保存</button>
                <span v-else class="cron-hint">默认留空（仅手动触发）</span>
              </div>
            </div>
            <div class="btn-row">
              <button class="btn btn-dark flex-1" :disabled="isCrawling || !hasUserId" @click="onTriggerUserScrape">
                {{ isUserSyncing ? '同步中...' : '增量同步' }}
              </button>
              <button class="btn btn-outline flex-1" :disabled="isCrawling || !hasUserId" @click="onTriggerUserScrapeFull">
                {{ isUserSyncing ? '同步中...' : '全量同步' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Section: 账户 -->
    <div class="section">
      <h4 class="section-title">账户</h4>
      <div class="grid-2">
        <!-- Douban Settings -->
        <div class="card">
          <div class="card-pad">
            <div class="card-head">
              <div class="card-icon icon-sky">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              </div>
              <h3>豆瓣配置</h3>
            </div>
            <div class="card-body">
              <!-- Hidden inputs to absorb Chrome autofill -->
              <div style="position:absolute;opacity:0;height:0;overflow:hidden;">
                <input type="text" autocomplete="username" />
                <input type="password" autocomplete="new-password" />
              </div>
              <div class="field">
                <label>豆瓣用户 ID</label>
                <input v-model="myDoubanUserId" placeholder="例如：166675383" autocomplete="off" />
                <span class="field-hint">配置后可同步您的"看过"列表</span>
              </div>
              <div class="field">
                <label>豆瓣 Cookie</label>
                <textarea v-model="myDoubanCookie" placeholder="粘贴从浏览器复制的 Cookie 字符串" rows="3" autocomplete="off"></textarea>
                <div class="field-actions">
                  <button type="button" class="btn btn-ghost-sm" :disabled="!myDoubanCookie" @click="onCheckMyCookie">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                    检查有效性
                  </button>
                  <span v-if="settingsStore.cookieCheck" :class="['check-result', settingsStore.cookieCheck.valid ? 'valid' : 'invalid']">
                    <svg v-if="settingsStore.cookieCheck.valid" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                    {{ settingsStore.cookieCheck.valid ? 'Cookie 有效' : settingsStore.cookieCheck.message }}
                  </span>
                </div>
                <span class="field-hint">登录豆瓣 → F12 → Network → 复制 Cookie</span>
              </div>
            </div>
            <button type="button" class="btn btn-dark w-full" @click="onSaveMyDouban" :disabled="accountSaving">
              {{ accountSaving ? '保存中...' : accountSaved ? '已保存 ✓' : '保存豆瓣配置' }}
            </button>
          </div>
        </div>

        <!-- Password Change -->
        <div class="card">
          <div class="card-pad">
            <div class="card-head">
              <div class="card-icon icon-amber">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              </div>
              <h3>修改密码</h3>
            </div>
            <div class="card-body">
              <div class="field">
                <label>原密码</label>
                <input v-model="oldPassword" type="password" placeholder="请输入原密码" />
              </div>
              <div class="field">
                <label>新密码</label>
                <input v-model="newPassword" type="password" placeholder="请输入新密码" />
              </div>
              <div class="field">
                <label>确认新密码</label>
                <input v-model="confirmPassword" type="password" placeholder="再次输入新密码" />
              </div>
              <p v-if="passwordMsg" class="status-line" style="color: #16a34a;">{{ passwordMsg }}</p>
              <p v-if="passwordError" class="status-line status-error">{{ passwordError }}</p>
            </div>
            <button type="button" class="btn btn-dark w-full" @click="onChangePassword" :disabled="passwordSaving">
              {{ passwordSaving ? '修改中...' : '修改密码' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Section: 用户管理 (admin only) -->
    <div class="section" v-if="isAdmin">
      <h4 class="section-title">用户管理</h4>
      <div class="card">
        <div class="card-pad">
          <div class="card-head">
            <div class="card-icon icon-violet">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            </div>
            <h3>用户列表</h3>
            <button class="btn btn-dark" style="margin-left:auto;padding:4px 12px;font-size:12px;" @click="showAddUser = !showAddUser">
              {{ showAddUser ? '取消' : '+ 新增用户' }}
            </button>
          </div>

          <!-- Add user form -->
          <div v-if="showAddUser" class="add-user-form">
            <div class="field-row">
              <div class="field">
                <label>用户名</label>
                <input v-model="newUser.username" placeholder="用户名" />
              </div>
              <div class="field">
                <label>密码</label>
                <input v-model="newUser.password" type="password" placeholder="密码" />
              </div>
              <div class="field">
                <label>角色</label>
                <select v-model="newUser.role">
                  <option value="user">普通用户</option>
                  <option value="admin">管理员</option>
                </select>
              </div>
            </div>
            <div class="field-row">
              <div class="field flex-2">
                <label>豆瓣用户 ID</label>
                <input v-model="newUser.douban_user_id" placeholder="可选" autocomplete="off" />
              </div>
              <div class="field flex-3">
                <label>豆瓣 Cookie</label>
                <input v-model="newUser.douban_cookie" placeholder="可选" />
              </div>
            </div>
            <button class="btn btn-dark" @click="onAddUser">创建用户</button>
          </div>

          <!-- Users table -->
          <div class="version-table-wrap" v-if="settingsStore.users.length > 0">
            <table class="version-table">
              <thead>
                <tr>
                  <th>用户名</th>
                  <th>角色</th>
                  <th>豆瓣 ID</th>
                  <th>状态</th>
                  <th>创建时间</th>
                  <th class="th-actions">操作</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="u in settingsStore.users" :key="u.id">
                  <!-- Display row -->
                  <tr>
                    <td>{{ u.username }}</td>
                    <td>
                      <span class="source-badge" :class="u.role === 'admin' ? 'source-imdb' : 'source-douban'">
                        {{ u.role === 'admin' ? '管理员' : '用户' }}
                      </span>
                    </td>
                    <td>{{ u.douban_user_id || '-' }}</td>
                    <td>
                      <span :class="u.is_active ? 'tag tag-green' : 'tag'">{{ u.is_active ? '启用' : '禁用' }}</span>
                    </td>
                    <td class="td-time">{{ u.created_at ? new Date(u.created_at).toLocaleDateString('zh-CN') : '-' }}</td>
                    <td class="td-actions">
                      <button class="action-btn" @click="startEditUser(u)" title="编辑">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                      </button>
                      <button
                        v-if="canDeleteUser(u)"
                        class="action-btn action-delete"
                        @click="onDeleteUser(u)"
                        title="删除"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                      </button>
                    </td>
                  </tr>
                  <!-- Edit row (inline) -->
                  <tr v-if="editingUser === u.id" class="edit-row">
                    <td colspan="6">
                      <div class="edit-form">
                        <div class="edit-fields">
                          <div class="edit-field">
                            <label>角色</label>
                            <select v-model="editUserForm.role" :disabled="editingUser === authStore.user?.id">
                              <option value="user" :disabled="editingUser === authStore.user?.id">普通用户</option>
                              <option value="admin">管理员</option>
                            </select>
                            <span v-if="editingUser === authStore.user?.id" class="field-hint" style="margin:0;font-size:10px;">不能修改自己的角色</span>
                          </div>
                          <div class="edit-field">
                            <label>状态</label>
                            <select v-model="editUserForm.is_active" :disabled="editingUser === authStore.user?.id">
                              <option :value="true">启用</option>
                              <option :value="false" :disabled="editingUser === authStore.user?.id">禁用</option>
                            </select>
                            <span v-if="editingUser === authStore.user?.id" class="field-hint" style="margin:0;font-size:10px;">不能禁用自己</span>
                          </div>
                          <div class="edit-field">
                            <label>豆瓣用户 ID</label>
                            <input v-model="editUserForm.douban_user_id" placeholder="留空不修改" autocomplete="off" />
                          </div>
                          <div class="edit-field">
                            <label>新密码</label>
                            <input v-model="editUserForm.password" type="password" placeholder="留空不修改" />
                          </div>
                        </div>
                        <div class="edit-actions">
                          <button class="btn btn-dark" style="height:28px;padding:0 12px;font-size:12px;" @click="onSaveUser(u.id)">保存</button>
                          <button class="btn btn-outline" style="height:28px;padding:0 12px;font-size:12px;" @click="cancelEditUser">取消</button>
                        </div>
                      </div>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
          <p v-else class="status-line status-muted">暂无用户数据</p>
        </div>
      </div>
    </div>

    <!-- Section: 恢复备份 (admin only) -->
    <div class="section" v-if="isAdmin">
      <h4 class="section-title">恢复备份</h4>

      <!-- 恢复卡片 -->
      <div class="card">
        <div class="card-pad">
          <div class="card-head">
            <div class="card-icon icon-amber">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
            </div>
            <h3>恢复备份</h3>
          </div>

          <!-- 恢复进度 -->
          <div v-if="backupProgress.active && backupProgress.type === 'restore'" class="backup-progress">
            <div class="progress-header">
              <span class="progress-title">正在恢复...</span>
              <span class="progress-percent">{{ backupProgress.percent }}%</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: backupProgress.percent + '%' }"></div>
            </div>
            <div class="progress-detail">
              <span>{{ backupProgress.detail || backupProgress.message }}</span>
              <span class="progress-time">已耗时 {{ formatTime(backupProgress.elapsed_seconds) }}</span>
            </div>
          </div>

          <!-- 恢复完成 -->
          <div v-else-if="restoreResult && restoreResult.success" class="backup-result">
            <div class="result-icon">✅</div>
            <div class="result-info">
              <p class="result-title">恢复成功！</p>
              <p>模式：{{ restoreResult.mode === 'append' ? '追加' : '覆盖' }}</p>
              <p>电影：导入 {{ restoreResult.movies_imported }} 部，跳过 {{ restoreResult.movies_skipped }} 部</p>
              <p>版本：导入 {{ restoreResult.versions_imported }} 个，跳过 {{ restoreResult.versions_skipped }} 个</p>
              <p>海报：导入 {{ restoreResult.posters_imported }} 张，跳过 {{ restoreResult.posters_skipped }} 张</p>
              <p>耗时：{{ restoreResult.elapsed_seconds }} 秒</p>
            </div>
            <button class="btn btn-outline" @click="restoreResult = null">关闭</button>
          </div>

          <!-- 备份文件列表 -->
          <div v-else class="restore-form">
            <div v-if="backupFiles.length === 0" class="empty-backup">
              暂无备份文件
            </div>

            <div v-else class="backup-file-list">
              <label
                v-for="f in backupFiles"
                :key="f.filename"
                class="backup-file-item"
                :class="{ selected: selectedBackupFile === f.filename, corrupted: f.corrupted }"
              >
                <input
                  type="radio"
                  :value="f.filename"
                  v-model="selectedBackupFile"
                  :disabled="f.corrupted"
                />
                <div class="file-info">
                  <div class="file-name">{{ f.filename }}</div>
                  <div class="file-meta">
                    <span>{{ formatSize(f.size) }}</span>
                    <span>{{ f.versions.length }} 个版本</span>
                    <span>{{ f.movie_count }} 部电影</span>
                  </div>
                  <div class="file-versions" v-if="f.versions.length > 0">
                    <span
                      v-for="v in f.versions"
                      :key="v.tag + v.source"
                      class="source-badge"
                      :class="v.source === 'imdb' ? 'source-imdb' : 'source-douban'"
                    >
                      {{ v.source === 'imdb' ? 'IMDb' : '豆瓣' }} {{ v.tag }}
                    </span>
                  </div>
                  <div v-if="f.corrupted" class="file-corrupted">⚠️ 备份文件已损坏</div>
                </div>
                <button
                  class="action-btn action-delete"
                  @click.stop="onDeleteBackup(f.filename)"
                  title="删除"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </label>
            </div>

            <div v-if="selectedBackupFile" class="restore-options">
              <div class="restore-mode-header">恢复模式：</div>
              <label class="restore-mode-option">
                <input type="radio" value="append" v-model="restoreMode" />
                <div>
                  <div class="mode-label">追加模式</div>
                  <div class="mode-desc">保留现有版本，添加备份中的新版本</div>
                </div>
              </label>
              <label class="restore-mode-option">
                <input type="radio" value="overwrite" v-model="restoreMode" />
                <div>
                  <div class="mode-label">覆盖模式</div>
                  <div class="mode-desc">删除现有版本，用备份数据替换</div>
                </div>
              </label>
              <div v-if="restoreMode === 'overwrite'" class="restore-warning">
                ⚠️ 覆盖模式将删除所有现有版本数据，此操作不可撤销
              </div>
            </div>

            <button
              class="btn btn-dark w-full"
              @click="onRestoreBackup"
              :disabled="!selectedBackupFile || backupProgress.active"
            >
              开始恢复
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete version confirmation modal -->
    <ConfirmModal
      :visible="deleteModal.visible"
      title="删除版本"
      confirmText="确认删除"
      :confirmLoading="deleteModal.loading"
      @cancel="deleteModal.visible = false"
      @confirm="onDeleteConfirm"
    >
      <p v-if="deleteModal.version">
        确定删除版本
        <strong>{{ deleteModal.version.tag }}</strong>
        （{{ deleteModal.version.source === 'imdb' ? 'IMDb' : '豆瓣' }}）吗？
      </p>
      <p>
        该版本包含 <strong>{{ deleteModal.movieCount }}</strong> 部电影，
        其中 <strong>{{ deleteModal.orphanCount }}</strong> 部在删除后将无任何版本关联，将被一并清理。
      </p>
      <p v-if="deleteModal.pendingCount > 0" style="color: #b45309;">
        ⚠ 该版本还有 <strong>{{ deleteModal.pendingCount }}</strong> 条待确认匹配，将一并删除。
      </p>
      <p style="color: #a1a1aa; font-size: 12px; margin-top: 8px;">此操作不可恢复。</p>
    </ConfirmModal>

    <!-- Delete user confirmation modal -->
    <ConfirmModal
      :visible="deleteUserModal.visible"
      title="删除用户"
      confirmText="确认删除"
      :confirmLoading="deleteUserModal.loading"
      @cancel="deleteUserModal.visible = false"
      @confirm="onDeleteUserConfirm"
    >
      <p v-if="deleteUserModal.user">
        确定删除用户 <strong>{{ deleteUserModal.user.username }}</strong> 吗？
      </p>
      <p style="color: #a1a1aa; font-size: 12px; margin-top: 8px;">此操作不可恢复。该用户的看过列表数据将保留。</p>
    </ConfirmModal>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useSettingsStore } from '../stores/settings.js'
import { useAuthStore } from '../stores/auth.js'
import {
  fetchDeletePreview, fetchCookieCheck,
  createBackup, fetchBackupProgress,
  fetchBackupFiles, restoreBackup, deleteBackup as apiDeleteBackup,
} from '../api/index.js'
import PaginationBar from '../components/PaginationBar.vue'
import PendingMatches from '../components/PendingMatches.vue'
import ConfirmModal from '../components/ConfirmModal.vue'
import { CronExpressionParser } from 'cron-parser'

const settingsStore = useSettingsStore()
const authStore = useAuthStore()
const isAdmin = computed(() => authStore.isAdmin)
let progressInterval = null
let backupProgressInterval = null

// Cron saved snapshots (for dirty detection)
const savedCron = ref('')
const savedMetaCron = ref('')
const savedUserCron = ref('')
const savedImdbCron = ref('')

// Version list
const editingId = ref(null)
const editTag = ref('')
const sortField = ref('tag')
const sortDir = ref('desc')
const versionPage = ref(1)
const versionPageSize = ref(10)
const versionSourceFilter = ref('all')

// Delete confirmation modal
const deleteModal = ref({ visible: false, version: null, loading: false, movieCount: 0, orphanCount: 0, pendingCount: 0 })

const sourceOptions = computed(() => {
  const all = settingsStore.versions
  const doubanCount = all.filter(v => (v.source || 'douban') !== 'imdb').length
  const imdbCount = all.filter(v => v.source === 'imdb').length
  return [
    { value: 'all', label: '全部', count: all.length },
    { value: 'douban', label: '豆瓣', count: doubanCount },
    { value: 'imdb', label: 'IMDb', count: imdbCount },
  ]
})

const isCrawling = computed(() => settingsStore.crawlProgress?.active || false)
const isUserSyncing = computed(() => settingsStore.crawlProgress?.active && settingsStore.crawlProgress?.job_type === 'user_watched')
const isImdbCrawling = computed(() => settingsStore.imdbProgress?.status === 'running' || false)
const hasUserId = computed(() => !!authStore.user?.douban_user_id)

// Account settings (per-user)
const myDoubanUserId = ref('')
const myDoubanCookie = ref('')
const accountSaving = ref(false)
const accountSaved = ref(false)

// Password change
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordSaving = ref(false)
const passwordMsg = ref('')
const passwordError = ref('')

// User management (admin)
const showAddUser = ref(false)
const newUser = ref({ username: '', password: '', role: 'user', douban_user_id: '', douban_cookie: '' })
const editingUser = ref(null)
const editUserForm = ref({ role: '', is_active: true, password: '', douban_user_id: '' })
const deleteUserModal = ref({ visible: false, user: null, loading: false })

// Backup & Restore
const selectedVersionIds = ref([])
const backupProgress = ref({ active: false, type: '', percent: 0, detail: '', message: '', elapsed_seconds: 0 })
const backupResult = ref(null)
const backupFiles = ref([])
const selectedBackupFile = ref('')
const restoreMode = ref('append')
const restoreResult = ref(null)

const imdbDoneMessage = computed(() => {
  const msg = settingsStore.imdbProgress?.message || ''
  if (settingsStore.pendingMatchCount > 0) return msg
  // 移除 "，X 部电影待确认。请前往控制台处理待确认匹配。"
  let cleaned = msg.replace(/，\d+ 部电影待确认。请前往控制台处理待确认匹配。$/, '')
  // 用版本列表中的实际数量替换静态数量
  const imdbVersion = settingsStore.versions.find(v => v.source === 'imdb')
  if (imdbVersion) {
    cleaned = cleaned.replace(/（\d+ 部）/, `（${imdbVersion.movie_count} 部）`)
  }
  return cleaned
})

const cookieWarning = computed(() => {
  // Cookie warning is now per-user, shown in account section
  return null
})

const metaPercent = computed(() => {
  const p = settingsStore.metadataProgress
  if (!p || p.total === 0) return 0
  return Math.round(p.done / p.total * 100)
})

const sortedVersions = computed(() => {
  let list = [...settingsStore.versions]
  if (versionSourceFilter.value !== 'all') {
    if (versionSourceFilter.value === 'imdb') {
      list = list.filter(v => v.source === 'imdb')
    } else {
      list = list.filter(v => (v.source || 'douban') !== 'imdb')
    }
  }
  const field = sortField.value
  const dir = sortDir.value === 'asc' ? 1 : -1
  list.sort((a, b) => {
    const va = a[field] || ''
    const vb = b[field] || ''
    if (va < vb) return -1 * dir
    if (va > vb) return 1 * dir
    return 0
  })
  return list
})

const versionTotalPages = computed(() => Math.max(1, Math.ceil(sortedVersions.value.length / versionPageSize.value)))

const pagedVersions = computed(() => {
  const start = (versionPage.value - 1) * versionPageSize.value
  return sortedVersions.value.slice(start, start + versionPageSize.value)
})

function toggleSort(field) {
  if (sortField.value === field) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortDir.value = 'desc'
  }
  versionPage.value = 1
}

function onVersionPageSizeChange(size) {
  versionPageSize.value = size
  versionPage.value = 1
}

function snapshotCrons() {
  savedCron.value = settingsStore.cronExpression
  savedMetaCron.value = settingsStore.metadataCron
  savedUserCron.value = settingsStore.userScrapeCron
  savedImdbCron.value = settingsStore.imdbCron
}

onMounted(async () => {
  // Clear stale cookie check result from previous user session
  settingsStore.cookieCheck = null

  // Load user's own douban settings from auth store
  if (authStore.user) {
    myDoubanUserId.value = authStore.user.douban_user_id || ''
    myDoubanCookie.value = authStore.user.douban_cookie || ''
  }

  // Load all data once
  const promises = [
    settingsStore.loadVersions(),
    settingsStore.loadUserWatchedStatus(),
    settingsStore.loadCrawlProgress(),
    settingsStore.loadImdbProgress(),
  ]

  if (isAdmin.value) {
    promises.push(
      settingsStore.loadSettings(),
      settingsStore.loadTop250Status(),
      settingsStore.loadMetadataProgress(),
      settingsStore.loadMetadataStatus(),
      settingsStore.loadCookieCheck(),
      settingsStore.loadPendingMatchCount(),
      settingsStore.loadUsers(),
      loadBackupData(),
    )
  }

  await Promise.all(promises)
  snapshotCrons()

  // If a job was already running when page loaded, start polling
  if (hasActiveJob()) startPolling()
})

onUnmounted(() => {
  stopPolling()
  stopBackupPolling()
})

function hasActiveJob() {
  return settingsStore.crawlProgress?.active
    || settingsStore.metadataProgress?.active
    || settingsStore.imdbProgress?.status === 'running'
}

function startPolling() {
  if (progressInterval) return
  progressInterval = setInterval(async () => {
    // Load progress for active jobs
    await settingsStore.loadCrawlProgress()
    if (isAdmin.value) await settingsStore.loadMetadataProgress()
    await settingsStore.loadImdbProgress()

    // If no jobs are active, stop polling and refresh status once
    if (!hasActiveJob()) {
      stopPolling()
      await refreshStatus()
    }
  }, 2000)
}

function stopPolling() {
  if (progressInterval) {
    clearInterval(progressInterval)
    progressInterval = null
  }
}

async function refreshStatus() {
  const promises = [
    settingsStore.loadVersions(),
    settingsStore.loadUserWatchedStatus(),
  ]
  if (isAdmin.value) {
    promises.push(
      settingsStore.loadTop250Status(),
      settingsStore.loadMetadataStatus(),
      settingsStore.loadPendingMatchCount(),
    )
  }
  await Promise.all(promises)
}

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

function retryStatusText(status) {
  const map = {
    pending: '等待重试',
    running: '重试中',
    cancelled: '已取消',
    exhausted: '已耗尽',
    failed: '失败',
  }
  return map[status] || status
}

function formatRetryTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

function truncateError(msg) {
  if (!msg) return ''
  return msg.length > 50 ? msg.slice(0, 50) + '...' : msg
}

function cronNextRun(type) {
  try {
    const expr = type === 'cron' ? settingsStore.cronExpression : settingsStore.imdbCron
    if (!expr || !expr.trim()) return ''
    const interval = CronExpressionParser.parse(expr)
    const next = interval.next().toDate()
    return next.toLocaleString('zh-CN')
  } catch {
    return ''
  }
}

async function onCancelRetry(jobType) {
  try {
    await settingsStore.cancelRetry(jobType)
  } catch (e) {
    alert(e.response?.data?.detail || '取消重试失败')
  }
}

async function onSaveRetrySettings() {
  try {
    await settingsStore.saveRetrySettings()
    alert('自动执行配置已保存')
  } catch (e) {
    alert(e.response?.data?.detail || '保存失败')
  }
}

async function onSave() {
  if (!isAdmin.value) return
  await settingsStore.saveSettings()
  snapshotCrons()
  await settingsStore.loadCookieCheck()
}

async function onSaveMyDouban() {
  accountSaving.value = true
  accountSaved.value = false
  try {
    const updated = await settingsStore.saveMyDoubanSettings(myDoubanUserId.value, myDoubanCookie.value)
    authStore.user.douban_user_id = updated.douban_user_id
    accountSaved.value = true
    setTimeout(() => { accountSaved.value = false }, 2000)
  } catch (e) {
    alert(e.response?.data?.detail || '保存失败')
  } finally {
    accountSaving.value = false
  }
}

async function onChangePassword() {
  passwordMsg.value = ''
  passwordError.value = ''
  if (!oldPassword.value || !newPassword.value) {
    passwordError.value = '请填写原密码和新密码'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = '两次输入的新密码不一致'
    return
  }
  if (newPassword.value.length < 4) {
    passwordError.value = '新密码至少 4 个字符'
    return
  }
  passwordSaving.value = true
  try {
    await settingsStore.changeMyPassword(oldPassword.value, newPassword.value)
    passwordMsg.value = '密码修改成功'
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch (e) {
    passwordError.value = e.response?.data?.detail || '修改失败'
  } finally {
    passwordSaving.value = false
  }
}

async function onCheckMyCookie() {
  try {
    const { data } = await fetchCookieCheck()
    settingsStore.cookieCheck = data
  } catch (e) {
    settingsStore.cookieCheck = { valid: false, message: '检查失败' }
  }
}

// User management (admin)
async function onAddUser() {
  if (!newUser.value.username || !newUser.value.password) {
    alert('请填写用户名和密码')
    return
  }
  try {
    await settingsStore.addUser(newUser.value)
    showAddUser.value = false
    newUser.value = { username: '', password: '', role: 'user', douban_user_id: '', douban_cookie: '' }
  } catch (e) {
    alert(e.response?.data?.detail || '创建失败')
  }
}

// Role hierarchy: admin > user
const ROLE_LEVEL = { admin: 2, user: 1 }

function canDeleteUser(u) {
  if (u.id === authStore.user?.id) return false  // 不能删自己
  const myLevel = ROLE_LEVEL[authStore.user?.role] || 0
  const targetLevel = ROLE_LEVEL[u.role] || 0
  return myLevel >= targetLevel  // 可以删除同级或更低级的用户
}

function onDeleteUser(user) {
  deleteUserModal.value = { visible: true, user, loading: false }
}

async function onDeleteUserConfirm() {
  const user = deleteUserModal.value.user
  if (!user) return
  deleteUserModal.value.loading = true
  try {
    await settingsStore.removeUser(user.id)
    deleteUserModal.value.visible = false
  } catch (e) {
    alert(e.response?.data?.detail || '删除失败')
  } finally {
    deleteUserModal.value.loading = false
  }
}

function startEditUser(u) {
  editingUser.value = u.id
  editUserForm.value = {
    role: u.role,
    is_active: u.is_active,
    password: '',
    douban_user_id: u.douban_user_id || '',
  }
}

function cancelEditUser() {
  editingUser.value = null
}

async function onSaveUser(userId) {
  const payload = {}
  if (editUserForm.value.role) payload.role = editUserForm.value.role
  payload.is_active = editUserForm.value.is_active
  if (editUserForm.value.password) payload.password = editUserForm.value.password
  if (editUserForm.value.douban_user_id !== undefined) payload.douban_user_id = editUserForm.value.douban_user_id
  try {
    await settingsStore.updateUser(userId, payload)
    editingUser.value = null
  } catch (e) {
    alert(e.response?.data?.detail || '修改失败')
  }
}

// Backup & Restore functions
async function loadBackupData() {
  try {
    const filesRes = await fetchBackupFiles()
    backupFiles.value = filesRes.data.files
  } catch (e) {
    console.error('Failed to load backup data:', e)
  }
}

function selectAllVersions() {
  const filteredIds = sortedVersions.value.map(v => v.id)
  const otherSelected = selectedVersionIds.value.filter(id => !filteredIds.includes(id))
  selectedVersionIds.value = [...otherSelected, ...filteredIds]
}

function invertSelection() {
  const filteredIds = new Set(sortedVersions.value.map(v => v.id))
  const otherSelected = selectedVersionIds.value.filter(id => !filteredIds.has(id))
  const invertedFiltered = sortedVersions.value
    .filter(v => !selectedVersionIds.value.includes(v.id))
    .map(v => v.id)
  selectedVersionIds.value = [...otherSelected, ...invertedFiltered]
}

const isAllPageSelected = computed(() => {
  if (pagedVersions.value.length === 0) return false
  return pagedVersions.value.every(v => selectedVersionIds.value.includes(v.id))
})

function togglePageSelection() {
  const pageIds = pagedVersions.value.map(v => v.id)
  if (isAllPageSelected.value) {
    selectedVersionIds.value = selectedVersionIds.value.filter(id => !pageIds.includes(id))
  } else {
    const otherSelected = selectedVersionIds.value.filter(id => !pageIds.includes(id))
    selectedVersionIds.value = [...otherSelected, ...pageIds]
  }
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(1)} ${units[i]}`
}

function formatElapsed(seconds) {
  if (!seconds) return '0 秒'
  if (seconds < 60) return `${seconds} 秒`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins} 分 ${secs} 秒`
}

function startBackupPolling() {
  if (backupProgressInterval) return
  backupProgressInterval = setInterval(async () => {
    try {
      const { data } = await fetchBackupProgress()
      backupProgress.value = data

      if (!data.active) {
        stopBackupPolling()
        if (data.result) {
          if (data.type === 'backup') {
            backupResult.value = data.result
          } else {
            restoreResult.value = data.result
          }
          // Reload backup files list
          const filesRes = await fetchBackupFiles()
          backupFiles.value = filesRes.data.files
        }
      }
    } catch (e) {
      console.error('Failed to poll backup progress:', e)
    }
  }, 500)
}

function stopBackupPolling() {
  if (backupProgressInterval) {
    clearInterval(backupProgressInterval)
    backupProgressInterval = null
  }
}

async function onCreateBackup() {
  if (selectedVersionIds.value.length === 0) return

  backupResult.value = null
  try {
    await createBackup(selectedVersionIds.value)
    startBackupPolling()
  } catch (e) {
    alert(e.response?.data?.detail || '备份失败')
  }
}

async function onRestoreBackup() {
  if (!selectedBackupFile.value) return

  if (restoreMode.value === 'overwrite') {
    if (!confirm('覆盖模式将删除所有现有版本数据，此操作不可撤销。确定继续吗？')) {
      return
    }
  }

  restoreResult.value = null
  try {
    await restoreBackup(selectedBackupFile.value, restoreMode.value)
    startBackupPolling()
  } catch (e) {
    alert(e.response?.data?.detail || '恢复失败')
  }
}

async function onDeleteBackup(filename) {
  if (!confirm(`确定删除备份文件 ${filename} 吗？`)) return

  try {
    await apiDeleteBackup(filename)
    backupFiles.value = backupFiles.value.filter(f => f.filename !== filename)
    if (selectedBackupFile.value === filename) {
      selectedBackupFile.value = ''
    }
  } catch (e) {
    alert(e.response?.data?.detail || '删除失败')
  }
}

async function onSaveCron(which) {
  await settingsStore.saveSettings()
  snapshotCrons()
}

async function onCheckCookie() { await settingsStore.checkCookie() }
async function onTriggerCrawl() { await settingsStore.triggerCrawl(); startPolling() }
async function onTriggerUserScrape() { await settingsStore.triggerUserScrape(); startPolling() }
async function onTriggerUserScrapeFull() { await settingsStore.triggerUserScrape(true); startPolling() }
async function onTriggerMeta(mode = 'incremental') { await settingsStore.triggerMetadataBackfill(mode); startPolling() }
async function onTriggerImdbCrawl() { await settingsStore.triggerImdbCrawl(); startPolling() }

function startEdit(v) { editingId.value = v.id; editTag.value = v.tag }
function cancelEdit() { editingId.value = null; editTag.value = '' }

async function onSaveEdit(id) {
  if (!editTag.value) return
  try {
    await settingsStore.editVersionTag(id, editTag.value)
    editingId.value = null
    editTag.value = ''
  } catch (e) {
    alert(e.response?.data?.detail || '修改失败')
  }
}

async function onDelete(v) {
  try {
    const { data } = await fetchDeletePreview(v.id)
    deleteModal.value = {
      visible: true,
      version: v,
      loading: false,
      movieCount: data.movie_count,
      orphanCount: data.orphan_movie_count,
      pendingCount: data.pending_match_count,
    }
  } catch (e) {
    alert(e.response?.data?.detail || '获取删除信息失败')
  }
}

async function onDeleteConfirm() {
  const v = deleteModal.value.version
  if (!v) return
  deleteModal.value.loading = true
  try {
    const data = await settingsStore.removeVersion(v.id)
    deleteModal.value.visible = false
    const msg = []
    if (data.orphan_movies_deleted > 0) msg.push(`清理了 ${data.orphan_movies_deleted} 部孤立电影`)
    if (data.posters_deleted > 0) msg.push(`删除了 ${data.posters_deleted} 张海报`)
    if (data.pending_matches_deleted > 0) msg.push(`删除了 ${data.pending_matches_deleted} 条待确认匹配`)
    if (msg.length) alert(`版本已删除。\n${msg.join('；')}。`)
  } catch (e) {
    alert(e.response?.data?.detail || '删除失败')
  } finally {
    deleteModal.value.loading = false
  }
}
</script>

<style scoped>
/* === Layout === */
.sv { width: 100%; }
.sv-header { margin-bottom: 32px; }
.sv-header h1 { font-size: 22px; font-weight: 600; color: #18181b; letter-spacing: -0.3px; }
.sv-subtitle { margin-top: 4px; font-size: 13px; color: #a1a1aa; }

/* === Section === */
.section { margin-bottom: 28px; }
.section-title { font-size: 11px; font-weight: 600; color: #a1a1aa; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 12px; }

/* === Grid === */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 640px) { .grid-2 { grid-template-columns: 1fr; } }

/* === Card === */
.card { background: #fff; border: 1px solid rgba(228, 228, 231, 0.6); border-radius: 12px; overflow: hidden; margin-bottom: 12px; transition: border-color 0.2s, box-shadow 0.2s; }
.card:last-child { margin-bottom: 0; }
.card:hover { border-color: rgba(212, 212, 216, 0.8); }
.card-active { border-color: rgba(99, 102, 241, 0.3); box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.05); }
.card-stretch { display: flex; flex-direction: column; }
.card-stretch .card-pad { flex: 1; }
.card-stretch .btn { margin-top: auto; }
.card-pad { display: flex; flex-direction: column; padding: 18px 20px; gap: 14px; }
.card-head { display: flex; align-items: flex-start; gap: 10px; flex-wrap: wrap; }
.card-head h3 { font-size: 13px; font-weight: 600; color: #18181b; }

/* === Source tabs (in card-head) === */
.source-tabs { display: flex; gap: 4px; margin-left: auto; }
.source-tab {
  display: inline-flex; align-items: center; gap: 4px;
  height: 26px; padding: 0 10px;
  border: 1px solid #e4e4e7; border-radius: 6px;
  background: #fff; color: #71717a;
  font-size: 11px; font-weight: 500; font-family: inherit;
  cursor: pointer; transition: all 0.15s;
}
.source-tab:hover { border-color: #d4d4d8; color: #3f3f46; }
.source-tab.active { background: #18181b; border-color: #18181b; color: #fff; }
.tab-count { font-size: 10px; opacity: 0.6; }
.source-tab.active .tab-count { opacity: 0.8; }
.card-subtitle { font-size: 11px; color: #a1a1aa; margin-top: 2px; line-height: 1.4; }
.card-icon { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 8px; flex-shrink: 0; }
.icon-violet { background: #f5f3ff; color: #8b5cf6; }
.icon-sky { background: #f0f9ff; color: #0ea5e9; }
.icon-indigo { background: #eef2ff; color: #6366f1; }
.icon-amber { background: #fffbeb; color: #d97706; }
.icon-emerald { background: #ecfdf5; color: #10b981; }
.card-body { flex: 1; }

.field-sm-date { width: 180px; }
@media (max-width: 640px) { .field-sm-date { width: 100%; } }
.field-sm label { display: block; margin-bottom: 5px; font-size: 11px; font-weight: 500; color: #71717a; }
.field-sm input { width: 100%; height: 32px; padding: 0 10px; border: 1px solid #e4e4e7; border-radius: 6px; font-size: 12px; font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace; color: #27272a; background: rgba(250, 250, 250, 0.5); transition: all 0.15s; box-sizing: border-box; }
.field-sm input::placeholder { color: #d4d4d8; font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif; }
.field-sm input:hover { border-color: #d4d4d8; }
.field-sm input:focus { outline: none; background: #fff; border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1); }

/* === Status === */
.status-line { font-size: 12px; color: #71717a; margin: 0 0 8px; line-height: 1.5; }
.status-line:last-child { margin-bottom: 0; }
.status-error { color: #f43f5e; }
.status-muted { color: #d4d4d8; }
.tag-row { display: flex; align-items: center; gap: 6px; }
.tag { display: inline-block; padding: 1px 6px; font-size: 10px; font-weight: 500; border-radius: 4px; background: #f4f4f5; color: #71717a; }
.tag-green { background: #ecfdf5; color: #10b981; }
.tag-amber { background: #fffbeb; color: #d97706; }
.tag-meta { font-size: 11px; color: #a1a1aa; }

/* === Cron === */
.cron-inline { display: flex; align-items: center; gap: 8px; padding-top: 8px; border-top: 1px solid #f4f4f5; }
.cron-inline label { font-size: 11px; font-weight: 500; color: #a1a1aa; white-space: nowrap; }
.cron-input { width: 130px; height: 28px; padding: 0 8px; border: 1px solid #e4e4e7; border-radius: 6px; font-size: 12px; font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace; color: #27272a; background: rgba(250, 250, 250, 0.5); transition: all 0.15s; }
.cron-input:hover { border-color: #d4d4d8; }
.cron-input:focus { outline: none; background: #fff; border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1); }
.cron-hint { font-size: 11px; color: #d4d4d8; }
.cron-save {
  height: 24px; padding: 0 10px;
  border: 1px solid #6366f1; border-radius: 5px;
  background: #eef2ff; color: #6366f1;
  font-size: 11px; font-weight: 500;
  cursor: pointer; transition: all 0.15s;
  font-family: inherit;
}
.cron-save:hover { background: #6366f1; color: #fff; }
.cron-next {
  font-size: 11px;
  color: #a1a1aa;
  padding-left: 8px;
}

/* === Retry Settings === */
.retry-settings-row {
  display: flex;
  gap: 16px;
}
.retry-setting {
  flex: 1;
}
.retry-setting label {
  display: block;
  font-size: 11px;
  font-weight: 500;
  color: #71717a;
  margin-bottom: 6px;
}
.retry-input {
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
.retry-input:hover {
  border-color: #d4d4d8;
}
.retry-input:focus {
  outline: none;
  background: #fff;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}
.retry-hint {
  display: block;
  font-size: 10px;
  color: #d4d4d8;
  margin-top: 4px;
}
@media (max-width: 640px) {
  .retry-settings-row {
    flex-direction: column;
  }
}

/* === Progress === */
.crawl-progress { margin-top: 4px; }
.import-progress { margin-top: 2px; }
.progress-msg { font-size: 12px; color: #6366f1; margin: 0; line-height: 1.5; }
.progress-sub { font-size: 11px; color: #a1a1aa; margin: 4px 0 0; }
.progress-label { display: flex; align-items: center; justify-content: space-between; font-size: 11px; color: #a1a1aa; margin-bottom: 6px; margin-top: 8px; }
.progress-pct { color: #71717a; font-weight: 500; }
.progress-pct.accent { color: #6366f1; }
.progress-bar-track { width: 100%; height: 4px; background: #f4f4f5; border-radius: 2px; overflow: hidden; margin-bottom: 8px; }
.progress-bar-fill { height: 100%; border-radius: 2px; background: linear-gradient(90deg, #6366f1, #818cf8); transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1); }
.gradient-indigo { background: linear-gradient(90deg, #6366f1, #818cf8); }
.gradient-amber { background: linear-gradient(90deg, #f59e0b, #fbbf24); }

/* === Retry Status === */
.retry-status {
  margin-top: 8px;
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #f4f4f5;
}
.retry-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.retry-label {
  font-size: 11px;
  font-weight: 600;
  color: #71717a;
}
.retry-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 500;
  border-radius: 4px;
}
.retry-pending {
  background: #fffbeb;
  color: #d97706;
}
.retry-running {
  background: #eef2ff;
  color: #6366f1;
}
.retry-cancelled {
  background: #f4f4f5;
  color: #71717a;
}
.retry-exhausted {
  background: #fef2f2;
  color: #ef4444;
}
.retry-failed {
  background: #fef2f2;
  color: #ef4444;
}
.retry-info {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: #71717a;
  margin-bottom: 6px;
}
.retry-count {
  font-weight: 500;
}
.retry-time {
  color: #a1a1aa;
}
.retry-error {
  font-size: 11px;
  color: #ef4444;
  margin-bottom: 8px;
  cursor: help;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.btn-sm {
  height: 28px;
  padding: 0 10px;
  font-size: 11px;
}
.backup-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  margin-bottom: 8px;
  background: #f9fafb;
  border-radius: 6px;
  font-size: 13px;
}
.backup-count {
  color: #6366f1;
  font-weight: 600;
  margin-right: 4px;
}
.th-checkbox {
  width: 36px;
  text-align: center !important;
}
.th-checkbox input[type="checkbox"],
.version-table td:first-child input[type="checkbox"] {
  width: 15px;
  height: 15px;
  accent-color: #6366f1;
  cursor: pointer;
}

.stat-row { display: flex; align-items: center; gap: 12px; font-size: 11px; color: #a1a1aa; }
.stat-green { color: #10b981; font-weight: 500; }
.stat-red { color: #f43f5e; font-weight: 500; }

/* === Result === */
.result-msg { display: flex; align-items: center; gap: 6px; font-size: 12px; margin: 0; }
.result-ok { color: #10b981; }
.result-err { color: #f43f5e; }

/* === Version table === */
.version-table-wrap { overflow-x: auto; }
.version-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.version-table th { text-align: left; padding: 8px 12px; font-size: 11px; font-weight: 600; color: #a1a1aa; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #f4f4f5; vertical-align: middle; }
.version-table td { padding: 8px 12px; border-bottom: 1px solid #f4f4f5; color: #3f3f46; vertical-align: middle; }
.version-table tr:last-child td { border-bottom: none; }
.version-table tr:hover td { background: #fafafa; }
.version-tag { font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace; font-weight: 500; color: #18181b; }
.version-pending-badge {
  display: inline-block; margin-left: 6px; padding: 1px 6px;
  font-size: 10px; font-weight: 500; border-radius: 4px;
  background: #fffbeb; color: #d97706;
}
.source-badge { display: inline-block; padding: 1px 6px; font-size: 10px; font-weight: 500; border-radius: 4px; }
.source-douban { background: #eef2ff; color: #6366f1; }
.source-imdb { background: #fffbeb; color: #d97706; }
.td-time { font-size: 12px; color: #71717a; white-space: nowrap; }
.th-sortable { cursor: pointer; user-select: none; }
.th-sortable:hover { color: #52525b; }
.sort-icon { font-size: 11px; margin-left: 2px; }
.sort-idle { color: #d4d4d8; }
.th-actions { text-align: right; vertical-align: middle; }
.td-actions { text-align: right; white-space: nowrap; vertical-align: middle; line-height: 1; }
.edit-input { height: 28px; padding: 0 8px; border: 1px solid #6366f1; border-radius: 6px; font-size: 12px; font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1); vertical-align: middle; }
.action-btn { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border: none; border-radius: 6px; background: transparent; color: #a1a1aa; cursor: pointer; transition: all 0.15s; vertical-align: middle; }
.action-btn:hover { background: #f4f4f5; color: #52525b; }
.action-save:hover { background: #eef2ff; color: #6366f1; }
.action-delete:hover { background: #fff1f2; color: #f43f5e; }

/* === Buttons === */
.btn-row { display: flex; gap: 8px; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; height: 34px; padding: 0 14px; border: none; border-radius: 8px; font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.15s; font-family: inherit; flex-shrink: 0; }
.btn:active:not(:disabled) { transform: scale(0.97); }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-dark { background: #18181b; color: #fff; }
.btn-dark:hover:not(:disabled) { background: #27272a; }
.btn-outline { background: transparent; color: #52525b; border: 1px solid #e4e4e7; }
.btn-outline:hover:not(:disabled) { background: #fafafa; border-color: #d4d4d8; }
.btn-ghost-sm { display: inline-flex; align-items: center; gap: 5px; height: 28px; padding: 0 10px; background: transparent; color: #6366f1; border: 1px solid #e4e4e7; border-radius: 6px; font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.15s; font-family: inherit; }
.btn-ghost-sm:hover:not(:disabled) { background: #eef2ff; border-color: #c7d2fe; }
.btn-ghost-sm:disabled { opacity: 0.4; cursor: not-allowed; }
.w-full { width: 100%; }
.flex-1 { flex: 1; }

/* === Cookie warning === */
.cookie-warning { display: flex; align-items: center; gap: 8px; background: #fff1f2; border: 1px solid rgba(244, 63, 94, 0.2); color: #f43f5e; padding: 10px 14px; border-radius: 10px; margin-bottom: 20px; font-size: 12px; font-weight: 500; }

/* === Form fields === */
.field { margin-bottom: 16px; }
.field:last-of-type { margin-bottom: 12px; }
.field label { display: block; margin-bottom: 6px; font-size: 13px; font-weight: 500; color: #3f3f46; }
.field input, .field textarea { width: 100%; height: 36px; padding: 0 12px; border: 1px solid #e4e4e7; border-radius: 8px; font-size: 13px; font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace; color: #27272a; background: rgba(250, 250, 250, 0.5); transition: all 0.15s; box-sizing: border-box; }
.field textarea { height: auto; padding: 10px 12px; resize: vertical; min-height: 68px; line-height: 1.5; }
.field input::placeholder, .field textarea::placeholder { color: #d4d4d8; font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif; }
.field input:hover, .field textarea:hover { border-color: #d4d4d8; }
.field input:focus, .field textarea:focus { outline: none; background: #fff; border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1); }
.field-hint { display: block; margin-top: 6px; font-size: 11px; color: #d4d4d8; line-height: 1.4; }
.field-actions { display: flex; align-items: center; gap: 10px; margin-top: 10px; }
.check-result { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 500; }
.check-result.valid { color: #10b981; }
.check-result.invalid { color: #f43f5e; }

/* === User management === */
.add-user-form { padding: 14px 0; border-top: 1px solid #f4f4f5; margin-top: 10px; }
.field-row { display: flex; gap: 12px; margin-bottom: 12px; }
.field-row .field { flex: 1; margin-bottom: 0; }
.field-row .flex-2 { flex: 2; }
.field-row .flex-3 { flex: 3; }
.field select { width: 100%; height: 36px; padding: 0 12px; border: 1px solid #e4e4e7; border-radius: 8px; font-size: 13px; font-family: inherit; color: #27272a; background: rgba(250, 250, 250, 0.5); transition: all 0.15s; box-sizing: border-box; }
.field select:focus { outline: none; background: #fff; border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1); }

/* Inline edit form */
.edit-row td { padding: 0 !important; background: #fafafa; border-bottom: 1px solid #e4e4e7; }
.edit-form { padding: 14px 20px; display: flex; align-items: flex-end; gap: 16px; }
.edit-fields { display: flex; gap: 12px; flex: 1; flex-wrap: wrap; }
.edit-field { display: flex; flex-direction: column; gap: 4px; min-width: 120px; }
.edit-field label { font-size: 11px; font-weight: 500; color: #71717a; }
.edit-field input, .edit-field select { height: 28px; padding: 0 8px; border: 1px solid #e4e4e7; border-radius: 6px; font-size: 12px; font-family: inherit; color: #27272a; background: #fff; }
.edit-field input:focus, .edit-field select:focus { outline: none; border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.1); }
.edit-actions { display: flex; gap: 6px; flex-shrink: 0; }

@media (max-width: 640px) {
  .card-pad { padding: 14px 16px; }
  .field-row { flex-direction: column; gap: 0; }
  .field-row .field { flex: unset; margin-bottom: 12px; }
}

/* === Backup & Restore === */
.btn-link {
  background: none;
  border: none;
  color: #6366f1;
  cursor: pointer;
  font-size: 12px;
  padding: 0;
}

.btn-link:hover {
  text-decoration: underline;
}

.sep {
  color: #e4e4e7;
}

.backup-progress {
  padding: 16px 0;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.progress-title {
  font-size: 13px;
  font-weight: 500;
  color: #27272a;
}

.progress-percent {
  font-size: 13px;
  font-weight: 600;
  color: #6366f1;
}

.progress-bar {
  height: 8px;
  background: #f4f4f5;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #818cf8);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-detail {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #71717a;
  margin-top: 8px;
}

.progress-time {
  color: #a1a1aa;
}

.backup-result {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
}

.result-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.result-info {
  flex: 1;
}

.result-title {
  font-size: 14px;
  font-weight: 600;
  color: #166534;
  margin-bottom: 8px;
}

.result-info p {
  font-size: 12px;
  color: #52525b;
  margin-bottom: 4px;
}

.empty-backup {
  text-align: center;
  padding: 24px;
  color: #a1a1aa;
  font-size: 13px;
}

.backup-file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.backup-file-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border: 1px solid #e4e4e7;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}

.backup-file-item:hover {
  border-color: #d4d4d8;
  background: #fafafa;
}

.backup-file-item.selected {
  border-color: #6366f1;
  background: #eef2ff;
}

.backup-file-item.corrupted {
  opacity: 0.6;
  cursor: not-allowed;
}

.backup-file-item input[type="radio"] {
  margin-top: 2px;
  accent-color: #6366f1;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 13px;
  font-weight: 500;
  color: #27272a;
  margin-bottom: 4px;
}

.file-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #71717a;
  margin-bottom: 6px;
}

.file-versions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.file-corrupted {
  font-size: 12px;
  color: #f43f5e;
  margin-top: 4px;
}

.restore-options {
  padding: 12px 0;
  border-top: 1px solid #f4f4f5;
}

.restore-mode-header {
  font-size: 13px;
  font-weight: 500;
  color: #3f3f46;
  margin-bottom: 10px;
}

.restore-mode-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #e4e4e7;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 8px;
  transition: all 0.15s;
}

.restore-mode-option:hover {
  border-color: #d4d4d8;
  background: #fafafa;
}

.restore-mode-option input[type="radio"] {
  margin-top: 2px;
  accent-color: #6366f1;
}

.mode-label {
  font-size: 13px;
  font-weight: 500;
  color: #27272a;
  margin-bottom: 2px;
}

.mode-desc {
  font-size: 12px;
  color: #71717a;
}

.restore-warning {
  padding: 10px 12px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 6px;
  font-size: 12px;
  color: #9a3412;
  margin-top: 8px;
}
</style>
