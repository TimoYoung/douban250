import { defineStore } from 'pinia'
import { fetchBubbles, fetchMovie, fetchMovieById, searchMoviesGlobal } from '../api/index.js'

export const useMoviesStore = defineStore('movies', {
  state: () => ({
    bubbles: [],
    currentMovie: null,
    loading: false,
    viewMode: 'poster',
    globalResults: [],
  }),

  actions: {
    async loadBubbles(versionId = null) {
      this.loading = true
      try {
        const { data } = await fetchBubbles(versionId)
        this.bubbles = data
      } finally {
        this.loading = false
      }
    },

    async loadMovie(id) {
      this.loading = true
      try {
        const { data } = await fetchMovie(id)
        this.currentMovie = data
      } finally {
        this.loading = false
      }
    },

    async loadMovieById(id) {
      this.loading = true
      try {
        const { data } = await fetchMovieById(id)
        this.currentMovie = data
      } finally {
        this.loading = false
      }
    },

    async searchGlobal(q) {
      if (!q || !q.trim()) {
        this.globalResults = []
        return
      }
      try {
        const { data } = await searchMoviesGlobal(q)
        this.globalResults = data
      } catch {
        this.globalResults = []
      }
    },
  },
})
