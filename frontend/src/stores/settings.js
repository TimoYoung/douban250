import { defineStore } from 'pinia'
import {
  fetchSettings, updateSettings,
  triggerCrawl, triggerUserScrape, triggerMetadataBackfill,
  fetchCrawlStatus, fetchCrawlProgress,
  fetchTop250Status, fetchUserWatchedStatus,
  fetchMetadataProgress, fetchMetadataStatus, fetchCookieCheck,
  triggerDoulistImport, fetchDoulistImportProgress,
  triggerImdbCrawl, fetchImdbProgress,
  fetchVersions, deleteVersion, updateVersion,
} from '../api/index.js'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    cronExpression: '0 3 * * 0',
    doubanUserId: '',
    doubanCookie: '',
    userScrapeCron: '',
    metadataCron: '0 5 * * 0',
    imdbCron: '',
    crawlStatus: null,
    top250Status: null,
    userWatchedStatus: null,
    crawlProgress: null,
    metadataProgress: null,
    metadataStatus: null,
    cookieCheck: null,
    checkingCookie: false,
    doulistImportProgress: null,
    imdbProgress: null,
    versions: [],
    loading: false,
    saving: false,
  }),

  actions: {
    // Settings
    async loadSettings() {
      this.loading = true
      try {
        const { data } = await fetchSettings()
        this.cronExpression = data.cron_expression
        this.doubanUserId = data.douban_user_id
        this.doubanCookie = data.douban_cookie || ''
        this.userScrapeCron = data.user_scrape_cron || ''
        this.metadataCron = data.metadata_cron || '0 5 * * 0'
      } finally {
        this.loading = false
      }
    },

    async saveSettings() {
      this.saving = true
      try {
        const { data } = await updateSettings({
          cron_expression: this.cronExpression,
          douban_user_id: this.doubanUserId,
          douban_cookie: this.doubanCookie,
          user_scrape_cron: this.userScrapeCron,
          metadata_cron: this.metadataCron,
          imdb_cron: this.imdbCron,
        })
        this.cronExpression = data.cron_expression
        this.doubanUserId = data.douban_user_id
        this.doubanCookie = data.douban_cookie || ''
        this.userScrapeCron = data.user_scrape_cron || ''
        this.metadataCron = data.metadata_cron || '0 5 * * 0'
        this.imdbCron = data.imdb_cron || ''
      } finally {
        this.saving = false
      }
    },

    // Crawl
    async triggerCrawl() {
      await triggerCrawl()
      await this.loadCrawlStatus()
    },

    async triggerUserScrape(full = false) {
      await triggerUserScrape(full)
      await this.loadUserWatchedStatus()
    },

    async triggerMetadataBackfill() {
      await triggerMetadataBackfill()
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

    // Doulist Import
    async triggerDoulistImportAction(url, tag) {
      await triggerDoulistImport(url, tag)
      await this.loadDoulistImportProgress()
    },

    async loadDoulistImportProgress() {
      const { data } = await fetchDoulistImportProgress()
      this.doulistImportProgress = data
    },

    // IMDb
    async triggerImdbCrawl() {
      await triggerImdbCrawl()
      await this.loadImdbProgress()
    },

    async loadImdbProgress() {
      const { data } = await fetchImdbProgress()
      this.imdbProgress = data
    },

    // Versions
    async loadVersions() {
      const { data } = await fetchVersions()
      this.versions = data
    },

    async removeVersion(id) {
      await deleteVersion(id)
      this.versions = this.versions.filter(v => v.id !== id)
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
