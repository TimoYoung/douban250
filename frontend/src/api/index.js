import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Movies
export function fetchMovies(params = {}) {
  return api.get('/movies', { params })
}

export function fetchBubbles(versionId) {
  return api.get('/movies/bubbles', { params: { version_id: versionId } })
}

export function fetchMovie(doubanId) {
  return api.get(`/movies/by-douban/${doubanId}`)
}

// Versions
export function fetchVersions() {
  return api.get('/versions')
}

export function fetchVersionDiff(versionId, compareId, topN = 10) {
  return api.get(`/versions/${versionId}/diff`, {
    params: { compare_id: compareId, top_n: topN },
  })
}

// Settings
export function fetchSettings() {
  return api.get('/settings')
}

export function updateSettings(data) {
  return api.put('/settings', data)
}

// Crawl
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

// User watched
export function fetchWatched() {
  return api.get('/user/watched')
}

// Metadata backfill
export function triggerMetadataBackfill() {
  return api.post('/crawl/metadata')
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

export default api
