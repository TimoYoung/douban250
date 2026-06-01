import { defineStore } from 'pinia'
import { fetchMovies, fetchBubbles, fetchMovie, fetchMovieById, searchMoviesGlobal } from '../api/index.js'

export const useMoviesStore = defineStore('movies', {
  state: () => ({
    movies: [],
    bubbles: [],
    currentMovie: null,
    total: 0,
    page: 1,
    pageSize: 20,
    totalPages: 0,
    loading: false,
    watchedFilter: 'all',
    search: '',
    viewMode: 'poster',
    globalResults: [],
  }),

  actions: {
    async loadMovies(versionId = null) {
      this.loading = true
      try {
        const params = {
          page: this.page,
          page_size: this.pageSize,
          watched_filter: this.watchedFilter,
        }
        if (versionId) params.version_id = versionId
        if (this.search) params.search = this.search

        const { data } = await fetchMovies(params)
        this.movies = data.items
        this.total = data.total
        this.totalPages = data.total_pages
      } finally {
        this.loading = false
      }
    },

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
