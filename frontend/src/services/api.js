import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: BASE, timeout: 15000 })

// Intercept requests to add token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Intercept 401 responses — clear auth state on token expiry
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // Dispatch custom event so App can react
      window.dispatchEvent(new Event('auth-expired'))
    }
    return Promise.reject(err)
  }
)

// ─── Auth ─────────────────────────────────────────────────────
export const login = (email, password) =>
  api.post('/auth/login', { email, password }).then(r => r.data)

export const signup = (email, password, name) =>
  api.post('/auth/signup', { email, password, name }).then(r => r.data)

// ─── News ─────────────────────────────────────────────────────
export const getNews = (category = '', page = 1, limit = 10, topic = '', filters = {}, language = 'en') =>
  api.get('/news', { params: {
    category: category || undefined,
    page,
    limit,
    topic: topic || undefined,
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
    source: filters.source || undefined,
    language,
  }}).then(r => r.data)

export const searchNews = (q, page = 1) =>
  api.get('/search', { params: { q, page } }).then(r => r.data)

export const getNewsSources = () =>
  api.get('/news/sources').then(r => r.data)

export const getCategoryCounts = (params = {}) =>
  api.get('/news/categories/counts', { params }).then(r => r.data)

// ─── Top 10 ───────────────────────────────────────────────────
export const getTop10 = (language = 'en') => api.get('/top10', { params: { language } }).then(r => r.data)

// ─── Trends ──────────────────────────────────────────────────
export const getTrends = (language = 'en') => api.get('/trends', { params: { language } }).then(r => r.data)
export const getTrendHistory = (days = 7, language = 'en') =>
  api.get('/trends/history', { params: { days, language } }).then(r => r.data)

// ─── Subscription (legacy) ──────────────────────────────────
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

// ─── Bookmarks (auth-required) ───────────────────────────────
export const getBookmarks = () =>
  api.get('/bookmarks').then(r => r.data)

export const addBookmark = (articleId) =>
  api.post('/bookmark', { articleId }).then(r => r.data)

export const removeBookmark = (bookmarkId) =>
  api.delete(`/bookmark/${bookmarkId}`).then(r => r.data)

export const removeBookmarkByArticle = (articleId) =>
  api.delete(`/bookmark/article/${articleId}`).then(r => r.data)

// ─── Personalization (auth-required) ─────────────────────────
export const getMyPreferences = () =>
  api.get('/me/preferences').then(r => r.data)

export const updateMyPreferences = (prefs) =>
  api.put('/me/preferences', prefs).then(r => r.data)

export const getMyFeed = (params = {}) =>
  api.get('/me/feed', { params }).then(r => r.data)

export const postMySubscribe = () =>
  api.post('/me/subscribe').then(r => r.data)

export const postMyUnsubscribe = () =>
  api.post('/me/unsubscribe').then(r => r.data)

export default api
