import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: BASE, timeout: 15000 })

// ─── News ─────────────────────────────────────────────────────
export const getNews = (category = '', page = 1, limit = 10, topic = '') =>
  api.get('/news', { params: {
    category: category || undefined,
    page,
    limit,
    topic: topic || undefined,
  }}).then(r => r.data)

export const searchNews = (q, page = 1) =>
  api.get('/search', { params: { q, page } }).then(r => r.data)

// ─── Top 5 ────────────────────────────────────────────────────
export const getTop5 = () => api.get('/top5').then(r => r.data)

// ─── Trends ──────────────────────────────────────────────────
export const getTrends = () => api.get('/trends').then(r => r.data)
export const getTrendHistory = (days = 7) =>
  api.get('/trends/history', { params: { days } }).then(r => r.data)

// ─── Subscription ────────────────────────────────────────────
export const subscribe = (email, name = '') =>
  api.post('/subscribe', { email, name }).then(r => r.data)

export const unsubscribe = (email) =>
  api.delete('/unsubscribe', { params: { email } }).then(r => r.data)

// ─── Pipeline / Fetch News ───────────────────────────────────
export const triggerPipeline = () =>
  api.post('/fetch-news').then(r => r.data)

export const fetchLatestNews = () =>
  api.post('/fetch-news').then(r => r.data)

// ─── Meta ────────────────────────────────────────────────────
export const getMeta = () => api.get('/meta').then(r => r.data)

// ─── Bookmarks ───────────────────────────────────────────────
export const getBookmarks = () =>
  api.get('/bookmarks').then(r => r.data)

export const addBookmark = (articleId) =>
  api.post('/bookmark', { articleId }).then(r => r.data)

export const removeBookmark = (bookmarkId) =>
  api.delete(`/bookmark/${bookmarkId}`).then(r => r.data)

export const removeBookmarkByArticle = (articleId) =>
  api.delete(`/bookmark/article/${articleId}`).then(r => r.data)

export default api
