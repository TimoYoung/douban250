import { defineStore } from 'pinia'
import { fetchVersions, fetchVersionDiff } from '../api/index.js'

export const useVersionsStore = defineStore('versions', {
  state: () => ({
    versions: [],
    currentVersionId: null,
    sourceFilter: 'douban',
    diff: null,
    diffError: null,
    loading: false,
  }),

  getters: {
    filteredVersions(state) {
      return state.versions.filter(v => v.source === state.sourceFilter)
    },
    availableSources(state) {
      const sources = new Set(state.versions.map(v => v.source))
      return [...sources]
    },
  },

  actions: {
    async loadVersions() {
      this.loading = true
      try {
        const { data } = await fetchVersions()
        this.versions = data
        // Auto-select first version of current source filter
        const matching = data.filter(v => v.source === this.sourceFilter)
        if (matching.length > 0 && !this.currentVersionId) {
          this.currentVersionId = matching[0].id
        } else if (matching.length > 0) {
          // Verify current selection is still valid for this source
          const current = data.find(v => v.id === this.currentVersionId)
          if (!current || current.source !== this.sourceFilter) {
            this.currentVersionId = matching[0].id
          }
        }
      } finally {
        this.loading = false
      }
    },

    setSourceFilter(source) {
      this.sourceFilter = source
      // Switch to first version of new source
      const matching = this.versions.filter(v => v.source === source)
      if (matching.length > 0) {
        this.currentVersionId = matching[0].id
      }
    },

    async loadDiff(versionId, compareId = null, topN = 10) {
      this.loading = true
      this.diff = null
      this.diffError = null
      try {
        const { data } = await fetchVersionDiff(versionId, compareId, topN)
        this.diff = data
      } catch (e) {
        if (e.response?.status === 404) {
          this.diffError = e.response.data?.detail || '无对比数据'
        } else {
          this.diffError = '加载失败'
        }
      } finally {
        this.loading = false
      }
    },
  },
})
