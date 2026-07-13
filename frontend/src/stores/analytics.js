import { defineStore } from 'pinia'
import {
  fetchDashboard,
  fetchOverlap,
  fetchUniqueMovies,
  fetchDistribution,
  fetchVersionTags,
} from '../api/index.js'

// 模块级请求计数器，非响应式（无需触发 Vue 依赖通知）
let distRequestId = 0

export const useAnalyticsStore = defineStore('analytics', {
  state: () => ({
    // Dashboard V2
    dashboard: null,
    dashboardLoading: false,

    // Cross-platform overlap + unique movies
    overlap: null,
    uniqueMovies: null,

    // Distribution (single source)
    distribution: null,

    // Distribution (compare mode)
    compareDistribution: null,

    // Version tags for timeline
    versionTags: { douban: [], imdb: [] },
  }),

  actions: {
    async loadDashboard() {
      this.dashboardLoading = true
      try {
        const { data } = await fetchDashboard()
        this.dashboard = data
      } finally {
        this.dashboardLoading = false
      }
    },

    async loadOverlapAndUnique() {
      const [overlapRes, uniqueRes] = await Promise.all([
        fetchOverlap(),
        fetchUniqueMovies(),
      ])
      this.overlap = overlapRes.data
      this.uniqueMovies = uniqueRes.data
    },

    async loadDistribution(source = 'douban', params = {}) {
      // 数据所有者负责生命周期：入口即清空旧数据，调用方无需手动清空
      if (source === 'compare') {
        this.compareDistribution = null
      } else {
        this.distribution = null
      }
      const myRequestId = ++distRequestId
      try {
        const { data } = await fetchDistribution(source, params)
        // 仅当请求仍为最新时才写入 store，丢弃过期请求的结果
        if (myRequestId !== distRequestId) return
        if (source === 'compare') {
          this.compareDistribution = data
        } else {
          this.distribution = data
        }
      } catch (e) {
        // 请求失败时保持 null，由调用方处理错误反馈
        if (myRequestId !== distRequestId) return
        if (source === 'compare') {
          this.compareDistribution = null
        } else {
          this.distribution = null
        }
        throw e
      }
    },

    async loadVersionTags(source = 'douban') {
      const { data } = await fetchVersionTags(source)
      this.versionTags[source] = data
    },
  },
})
