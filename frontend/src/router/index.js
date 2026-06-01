import { createRouter, createWebHistory } from 'vue-router'

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
    name: 'PlatformCompare',
    component: () => import('../views/PlatformCompareView.vue'),
  },
  {
    path: '/versions',
    name: 'VersionDiff',
    component: () => import('../views/VersionDiffView.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
