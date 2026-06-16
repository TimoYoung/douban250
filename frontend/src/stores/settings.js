import { defineStore } from 'pinia'
import {
  fetchSettings, updateSettings,
  triggerCrawl, triggerUserScrape, triggerMetadataBackfill,
  fetchCrawlStatus, fetchCrawlProgress,
  fetchTop250Status, fetchUserWatchedStatus,
  fetchMetadataProgress, fetchMetadataStatus, fetchCookieCheck,
  triggerImdbCrawl, fetchImdbProgress,
  fetchRetryStatus, cancelRetry, cancelAllRetries,
  fetchVersions, deleteVersion, updateVersion,
  fetchPendingMatches, resolvePendingMatch,
  fetchPendingMatchCount,
  updateMyDoubanSettings,
  fetchUsers, createUser, updateUser, deleteUser,
  changePassword,
} from '../api/index.js'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    // Global settings (admin)
    cronExpression: '0 9 * * 1',
    userScrapeCron: '',
    metadataCron: '0 5 * * 0',
    imdbCron: '0 4 * * *',
    // Status
    crawlStatus: null,
    top250Status: null,
    userWatchedStatus: null,
    crawlProgress: null,
    metadataProgress: null,
    metadataStatus: null,
    cookieCheck: null,
    checkingCookie: false,
    imdbProgress: null,
    // Retry state
    top250Retry: null,
    imdbRetry: null,
    retryInterval: 3600,
    maxRetries: 3,
    versions: [],
    loading: false,
    saving: false,
    // Pending matches
    pendingMatches: [],
    pendingMatchCount: 0,
    pendingMatchesLoading: false,
    // User management (admin)
    users: [],
    usersLoading: false,
  }),

  actions: {
    // ── Global settings (admin) ────────────────────────────────────────
    async loadSettings() {
      this.loading = true
      try {
        const { data } = await fetchSettings()
        this.cronExpression = data.cron_expression
        this.userScrapeCron = data.user_scrape_cron || ''
        this.metadataCron = data.metadata_cron || '0 5 * * 0'
        this.imdbCron = data.imdb_cron || '0 4 * * *'
        this.retryInterval = data.retry_interval || 3600
        this.maxRetries = data.max_retries || 3
      } finally {
        this.loading = false
      }
    },

    async saveSettings() {
      this.saving = true
      try {
        const { data } = await updateSettings({
          cron_expression: this.cronExpression,
          user_scrape_cron: this.userScrapeCron,
          metadata_cron: this.metadataCron,
          imdb_cron: this.imdbCron,
          retry_interval: this.retryInterval,
          max_retries: this.maxRetries,
        })
        this.cronExpression = data.cron_expression
        this.userScrapeCron = data.user_scrape_cron || ''
        this.metadataCron = data.metadata_cron || '0 5 * * 0'
        this.imdbCron = data.imdb_cron || '0 4 * * *'
        this.retryInterval = data.retry_interval || 3600
        this.maxRetries = data.max_retries || 3
      } finally {
        this.saving = false
      }
    },

    // ── Per-user douban settings ───────────────────────────────────────
    async saveMyDoubanSettings(doubanUserId, doubanCookie) {
      const { data } = await updateMyDoubanSettings({
        douban_user_id: doubanUserId,
        douban_cookie: doubanCookie,
      })
      return data
    },

    // ── Password ──────────────────────────────────────────────────────
    async changeMyPassword(oldPassword, newPassword) {
      await changePassword(oldPassword, newPassword)
    },

    // ── User management (admin) ───────────────────────────────────────
    async loadUsers() {
      this.usersLoading = true
      try {
        const { data } = await fetchUsers()
        this.users = data
      } finally {
        this.usersLoading = false
      }
    },

    async addUser(userData) {
      const { data } = await createUser(userData)
      this.users.push(data)
      return data
    },

    async updateUser(userId, userData) {
      const { data } = await updateUser(userId, userData)
      const idx = this.users.findIndex(u => u.id === userId)
      if (idx !== -1) this.users[idx] = data
      return data
    },

    async removeUser(userId) {
      await deleteUser(userId)
      this.users = this.users.filter(u => u.id !== userId)
    },

    // ── Crawl ─────────────────────────────────────────────────────────
    async triggerCrawl() {
      await triggerCrawl()
      await this.loadCrawlStatus()
    },

    async triggerUserScrape(full = false) {
      await triggerUserScrape(full)
      await this.loadUserWatchedStatus()
    },

    async triggerMetadataBackfill(mode = 'incremental') {
      await triggerMetadataBackfill(mode)
      await this.loadMetadataProgress()
    },

    async loadCrawlStatus() {
      const { data } = await fetchCrawlStatus()
      this.crawlStatus = data
    },

    async loadTop250Status() {
      const { data } = await fetchTop250Status()
      this.top250Status = data
    },

    async loadUserWatchedStatus() {
      const { data } = await fetchUserWatchedStatus()
      this.userWatchedStatus = data
    },

    async loadCrawlProgress() {
      const { data } = await fetchCrawlProgress()
      this.crawlProgress = data
      // 提取重试状态
      if (data.retry) {
        this.top250Retry = data.retry
      }
    },

    async loadMetadataProgress() {
      const { data } = await fetchMetadataProgress()
      this.metadataProgress = data
    },

    async loadMetadataStatus() {
      const { data } = await fetchMetadataStatus()
      this.metadataStatus = data
    },

    async loadCookieCheck() {
      const { data } = await fetchCookieCheck()
      this.cookieCheck = data
    },

    async checkCookie() {
      this.checkingCookie = true
      try {
        const { data } = await fetchCookieCheck()
        this.cookieCheck = data
      } finally {
        this.checkingCookie = false
      }
    },

    // ── IMDb ──────────────────────────────────────────────────────────
    async triggerImdbCrawl() {
      await triggerImdbCrawl()
      await this.loadImdbProgress()
    },

    async loadImdbProgress() {
      const { data } = await fetchImdbProgress()
      this.imdbProgress = data
      // 提取重试状态
      if (data.retry) {
        this.imdbRetry = data.retry
      }
    },

    // ── Retry management ──────────────────────────────────────────────
    async cancelRetry(jobType) {
      await cancelRetry(jobType)
      // 重新加载对应的重试状态
      if (jobType === 'top250') {
        await this.loadCrawlProgress()
      } else if (jobType === 'imdb') {
        await this.loadImdbProgress()
      }
    },

    async cancelAllRetries() {
      await cancelAllRetries()
      // 重新加载所有重试状态
      await this.loadCrawlProgress()
      await this.loadImdbProgress()
    },

    async saveRetrySettings() {
      this.saving = true
      try {
        const { data } = await updateSettings({
          retry_interval: this.retryInterval,
          max_retries: this.maxRetries,
        })
        this.retryInterval = data.retry_interval || 3600
        this.maxRetries = data.max_retries || 3
      } finally {
        this.saving = false
      }
    },

    // ── Pending matches ───────────────────────────────────────────────
    async loadPendingMatches() {
      this.pendingMatchesLoading = true
      try {
        const { data } = await fetchPendingMatches()
        this.pendingMatches = data.movies
        this.pendingMatchCount = data.total
      } finally {
        this.pendingMatchesLoading = false
      }
    },

    async loadPendingMatchCount() {
      const { data } = await fetchPendingMatchCount()
      this.pendingMatchCount = data.total
    },

    async resolveMatch(imdbId, action, candidateDoubanId, manualDoubanId) {
      const body = { action }
      if (candidateDoubanId) body.candidate_douban_id = candidateDoubanId
      if (manualDoubanId) body.manual_douban_id = manualDoubanId
      const { data } = await resolvePendingMatch(imdbId, body)
      this.pendingMatches = this.pendingMatches.filter(m => m.imdb_id !== imdbId)
      this.pendingMatchCount = this.pendingMatches.length
      await this.loadVersions()
      return data
    },

    async finalizeVersion() {
      this.pendingMatches = []
      this.pendingMatchCount = 0
      await this.loadVersions()
    },

    // ── Versions ──────────────────────────────────────────────────────
    async loadVersions() {
      const { data } = await fetchVersions()
      this.versions = data
    },

    async removeVersion(id) {
      const { data } = await deleteVersion(id)
      this.versions = this.versions.filter(v => v.id !== id)
      return data
    },

    async editVersionTag(id, tag) {
      const { data } = await updateVersion(id, { tag })
      const idx = this.versions.findIndex(v => v.id === id)
      if (idx !== -1) {
        this.versions[idx] = data
      }
    },
  },
})
