import { defineStore } from 'pinia'
import { login as apiLogin, getMe } from '../api/index.js'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: null,
    initialized: false,
  }),

  getters: {
    isLoggedIn: (state) => !!state.user,
    isAdmin: (state) => state.user?.role === 'admin',
  },

  actions: {
    async init() {
      const token = localStorage.getItem('auth_token')
      if (!token) {
        this.initialized = true
        return
      }
      this.token = token
      try {
        const { data } = await getMe()
        this.user = data
      } catch {
        this.token = null
        localStorage.removeItem('auth_token')
      }
      this.initialized = true
    },

    async login(username, password) {
      const { data } = await apiLogin(username, password)
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('auth_token', data.access_token)
    },

    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('auth_token')
    },
  },
})
