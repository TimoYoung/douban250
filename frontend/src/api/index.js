import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Request interceptor: attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: handle 401 globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────

export function login(username, password) {
  return api.post('/auth/login', { username, password })
}

export function getMe() {
  return api.get('/auth/me')
}

export function changePassword(oldPassword, newPassword) {
  return api.put('/auth/password', { old_password: oldPassword, new_password: newPassword })
}

export function updateMyDoubanSettings(data) {
  return api.put('/auth/douban-settings', data)
}

// ── Admin: User management ────────────────────────────────────────────

export function fetchUsers() {
  return api.get('/auth/users')
}

export function createUser(data) {
  return api.post('/auth/users', data)
}

export function updateUser(userId, data) {
  return api.put(`/auth/users/${userId}`, data)
}

export function deleteUser(userId) {
  return api.delete(`/auth/users/${userId}`)
}

// ── Movies ────────────────────────────────────────────────────────────

export function fetchMovies(params = {}) {
  return api.get('/movies', { params })
}

export function fetchBubbles(versionId) {
  return api.get('/movies/bubbles', { params: { version_id: versionId } })
}

export function fetchMovie(doubanId) {
  return api.get(`/movies/by-douban/${doubanId}`)
}

export function fetchMovieById(movieId) {
  return api.get(`/movies/${movieId}`)
}

export function searchMoviesGlobal(q, limit = 20) {
  return api.get('/movies/search', { params: { q, limit } })
}

export function fetchExploreFilters() {
  return api.get('/movies/explore/filters')
}

export function exploreMovies(params = {}) {
  return api.get('/movies/explore', { params })
}

// ── Versions ──────────────────────────────────────────────────────────

export function fetchVersions() {
  return api.get('/versions')
}

export function fetchCompare(versionAId, versionBId, topN = 10) {
  return api.get('/versions/compare', { params: { version_a_id: versionAId, version_b_id: versionBId, top_n: topN } })
}

export function fetchDeletePreview(id) {
  return api.get(`/versions/${id}/delete-preview`)
}

export function deleteVersion(id) {
  return api.delete(`/versions/${id}`)
}

export function updateVersion(id, data) {
  return api.patch(`/versions/${id}`, data)
}

// ── Settings (admin-only global settings) ─────────────────────────────

export function fetchSettings() {
  return api.get('/settings')
}

export function updateSettings(data) {
  return api.put('/settings', data)
}

// ── Crawl ─────────────────────────────────────────────────────────────

export function triggerCrawl() {
  return api.post('/crawl')
}

export function triggerUserScrape(full = false) {
  return api.post('/crawl/user-watched', null, { params: { full } })
}

export function fetchCrawlStatus() {
  return api.get('/crawl/status')
}

export function fetchCrawlProgress() {
  return api.get('/crawl/progress')
}

export function fetchTop250Status() {
  return api.get('/crawl/status/top250')
}

export function fetchUserWatchedStatus() {
  return api.get('/crawl/status/user-watched')
}

export function fetchCrawlLogs(limit = 20) {
  return api.get('/crawl/logs', { params: { limit } })
}

// ── User watched ──────────────────────────────────────────────────────

export function fetchWatched() {
  return api.get('/user/watched')
}

// ── Metadata backfill ─────────────────────────────────────────────────

export function triggerMetadataBackfill(mode = 'incremental') {
  return api.post('/crawl/metadata', null, { params: { mode } })
}

export function fetchMetadataProgress() {
  return api.get('/crawl/metadata/progress')
}

export function fetchMetadataStatus() {
  return api.get('/crawl/metadata/status')
}

export function fetchCookieCheck() {
  return api.get('/crawl/cookie-check')
}

// ── IMDb ──────────────────────────────────────────────────────────────

export function triggerImdbCrawl() {
  return api.post('/crawl/imdb')
}

export function fetchImdbProgress() {
  return api.get('/crawl/imdb/progress')
}

// ── Retry management ──────────────────────────────────────────────────

export function fetchRetryStatus(jobType) {
  return api.get('/crawl/retry/status', { params: { job_type: jobType } })
}

export function cancelRetry(jobType) {
  return api.post('/crawl/retry/cancel', null, { params: { job_type: jobType } })
}

export function cancelAllRetries() {
  return api.post('/crawl/retry/cancel-all')
}

// ── Pending matches ───────────────────────────────────────────────────

export function fetchPendingMatches() {
  return api.get('/pending-matches')
}

export function resolvePendingMatch(imdbId, data) {
  return api.post('/pending-matches/resolve', { imdb_id: imdbId, ...data })
}

export function fetchPendingMatchCount() {
  return api.get('/pending-matches')
}

// ── Backup & Restore ──────────────────────────────────────────────

export function fetchBackupVersions() {
  return api.get('/backup/versions')
}

export function createBackup(versionIds) {
  return api.post('/backup/create', { version_ids: versionIds })
}

export function fetchBackupProgress() {
  return api.get('/backup/progress')
}

export function fetchBackupFiles() {
  return api.get('/backup/files')
}

export function fetchBackupManifest(filename) {
  return api.get(`/backup/files/${filename}`)
}

export function restoreBackup(filename, mode = 'append') {
  return api.post('/backup/restore', { filename, mode })
}

export function deleteBackup(filename) {
  return api.delete(`/backup/files/${filename}`)
}

// ── Analytics ───────────────────────────────────────────────────────

export function fetchDashboard() {
  return api.get('/analytics/dashboard')
}

export function fetchOverlap() {
  return api.get('/analytics/cross-platform/overlap')
}

export function fetchUniqueMovies(topN = 10) {
  return api.get('/analytics/cross-platform/unique-movies', { params: { top_n: topN } })
}

export function fetchDistribution(source = 'douban', params = {}) {
  return api.get('/analytics/distribution', { params: { source, ...params } })
}

export function fetchVersionTags(source = 'douban') {
  return api.get('/analytics/version-tags', { params: { source } })
}

export function fetchRecentDebuts(topN = 3) {
  return api.get('/analytics/recent-debuts', { params: { top_n: topN } })
}

export function fetchRecentDrops(topN = 3) {
  return api.get('/analytics/recent-drops', { params: { top_n: topN } })
}

export function fetchTimelineSnapshot(tag, source = 'douban') {
  return api.get('/analytics/timeline-snapshot', { params: { tag, source } })
}

export default api
