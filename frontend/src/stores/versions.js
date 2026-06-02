import { defineStore } from 'pinia'
import { fetchVersions } from '../api/index.js'

export const useVersionsStore = defineStore('versions', {
  state: () => ({
    versions: [],
    currentVersionId: null,
    sourceFilter: 'douban',
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
        const matching = data.filter(v => v.source === this.sourceFilter)
        if (matching.length > 0 && !this.currentVersionId) {
          this.currentVersionId = matching[0].id
        } else if (matching.length > 0) {
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
      const matching = this.versions.filter(v => v.source === source)
      if (matching.length > 0) {
        this.currentVersionId = matching[0].id
      }
    },
  },
})
