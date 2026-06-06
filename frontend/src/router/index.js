import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const routes = [
  {
    path: '/',
    redirect: '/movies',
  },
  {
    path: '/movies',
    name: 'MovieList',
    component: () => import('../views/MovieListView.vue'),
  },
  {
    path: '/movies/id/:id',
    name: 'MovieDetailById',
    component: () => import('../views/MovieDetailView.vue'),
  },
  {
    path: '/movies/:id',
    name: 'MovieDetail',
    component: () => import('../views/MovieDetailView.vue'),
  },
  {
    path: '/compare',
    name: 'Compare',
    component: () => import('../views/CompareView.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Wait for initial auth check on first navigation
  if (!authStore.initialized) {
    await authStore.init()
  }

  // Settings page requires login
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  next()
})

export default router
