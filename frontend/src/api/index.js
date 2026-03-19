import axios from 'axios'

const api = axios.create({
    baseURL: '/api',
    headers: { 'Content-Type': 'application/json' },
})

// ─── News ─────────────────────────────────────────────────────────────────────
export const fetchFeed = (params = {}) =>
    api.get('/news/feed', { params }).then(r => r.data)

export const fetchNewsItem = (id) =>
    api.get(`/news/${id}`).then(r => r.data)

export const refreshFeed = () =>
    api.post('/news/refresh').then(r => r.data)

export const fetchStats = () =>
    api.get('/news/stats/summary').then(r => r.data)

// ─── Favorites ────────────────────────────────────────────────────────────────
export const fetchFavorites = () =>
    api.get('/favorites/').then(r => r.data)

export const addFavorite = (newsItemId) =>
    api.post(`/favorites/${newsItemId}`).then(r => r.data)

export const removeFavorite = (newsItemId) =>
    api.delete(`/favorites/${newsItemId}`).then(r => r.data)

// ─── Broadcast ───────────────────────────────────────────────────────────────
export const broadcast = (payload) =>
    api.post('/broadcast/', payload).then(r => r.data)

export const fetchBroadcastLogs = () =>
    api.get('/broadcast/logs').then(r => r.data)

// ─── Sources ──────────────────────────────────────────────────────────────────
export const fetchSources = () =>
    api.get('/sources/').then(r => r.data)

export const toggleSource = (id) =>
    api.patch(`/sources/${id}/toggle`).then(r => r.data)

export const createSource = (payload) =>
    api.post('/sources/', payload).then(r => r.data)

export const deleteSource = (id) =>
    api.delete(`/sources/${id}`).then(r => r.data)

export default api