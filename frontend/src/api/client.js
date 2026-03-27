import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// Keywords
export const getKeywords = () => api.get('/keywords').then(r => r.data)
export const addKeyword = (keyword) => api.post('/keywords', { keyword }).then(r => r.data)
export const removeKeyword = (keyword) => api.delete(`/keywords/${encodeURIComponent(keyword)}`).then(r => r.data)

// Dashboard
export const getDashboard = () => api.get('/dashboard').then(r => r.data)

// Refresh
export const triggerRefresh = (daysBack = 14, keywords = null) =>
  api.post('/refresh', null, { params: { days_back: daysBack, keywords } }).then(r => r.data)
export const getRefreshStatus = () => api.get('/refresh/status').then(r => r.data)
export const refreshKeyword = (keyword, daysBack = 14) =>
  api.post('/refresh-keyword', null, { params: { keyword, days_back: daysBack }, timeout: 30000 }).then(r => r.data)

// Videos (with filtering)
export const getVideos = (params = {}) =>
  api.get('/videos', {
    params: {
      breakout_only: params.breakoutOnly || false,
      keyword: params.keyword,
      channel_tier: params.channelTier,
      sort_by: params.sortBy || 'outlier_score',
      min_views: params.minViews,
      min_sub_count: params.minSubCount,
      max_sub_count: params.maxSubCount,
      limit: params.limit || 50,
    }
  }).then(r => r.data)
export const getVideo = (videoId) => api.get(`/videos/${videoId}`).then(r => r.data)
export const getTranscript = (videoId) => api.get(`/videos/${videoId}/transcript`).then(r => r.data)

// Saved
export const getSaved = () => api.get('/saved').then(r => r.data)
export const saveVideo = (videoId, notes = '') =>
  api.post(`/saved/${videoId}`, { notes }).then(r => r.data)
export const unsaveVideo = (videoId) => api.delete(`/saved/${videoId}`).then(r => r.data)
export const updateNotes = (videoId, notes) =>
  api.patch(`/saved/${videoId}/notes`, { notes }).then(r => r.data)

// Quota & Stats
export const getQuota = () => api.get('/quota').then(r => r.data)
export const getStats = () => api.get('/stats').then(r => r.data)

// Export
export const getExportUrl = (breakoutOnly = true) =>
  `/api/export/csv?breakout_only=${breakoutOnly}`

// Tracked Channels
export const getTrackedChannels = () => api.get('/channels').then(r => r.data)
export const trackChannel = (channelId, channelName = '', why = '') =>
  api.post('/channels/track', { channel_id: channelId, channel_name: channelName, why }).then(r => r.data)
export const untrackChannel = (channelId) => api.delete(`/channels/${channelId}`).then(r => r.data)
export const isChannelTracked = (channelId) => api.get(`/channels/${channelId}/is-tracked`).then(r => r.data)
export const scanChannels = () => api.post('/channels/scan').then(r => r.data)

// Trends
export const getTrend = (keyword) => api.get(`/trends/${encodeURIComponent(keyword)}`).then(r => r.data)
export const getAllTrends = () => api.get('/trends').then(r => r.data)

// TikTok Trends
export const getTikTokTrends = () => api.get('/tiktok-trends').then(r => r.data)
export const getTikTokTrend = (keyword) => api.get(`/tiktok-trends/${encodeURIComponent(keyword)}`).then(r => r.data)
export const scanTikTokTrends = () => api.post('/tiktok-trends/scan').then(r => r.data)
export const scanTikTokKeyword = (keyword) =>
  api.post('/tiktok-trends/scan-keyword', null, { params: { keyword }, timeout: 30000 }).then(r => r.data)

export default api
