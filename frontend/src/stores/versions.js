import { defineStore } from 'pinia'
import { fetchVersions, fetchVersionDiff } from '../api/index.js'

export const useVersionsStore = defineStore('versions', {
  state: () => ({
    versions: [],
    currentVersionId: null,
    diff: null,
    diffError: null,
    loading: false,
  }),

  actions: {
    async loadVersions() {
      this.loading = true
      try {
        const { data } = await fetchVersions()
        this.versions = data
        if (data.length > 0 && !this.currentVersionId) {
          this.currentVersionId = data[0].id
        }
      } finally {
        this.loading = false
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
