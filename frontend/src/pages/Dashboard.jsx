import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getDashboard, getVideos } from '../api/client'
import VideoCard from '../components/VideoCard'
import { TrendingUp, Clock, BarChart2, ChevronRight, Filter, Flame, Zap, Eye, Bookmark } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

const CHANNEL_TIERS = [
  { value: '', label: 'All sizes' },
  { value: 'nano', label: '< 1K subs' },
  { value: 'micro', label: '1K–10K' },
  { value: 'small', label: '10K–100K' },
  { value: 'medium', label: '100K–1M' },
  { value: 'large', label: '1M+' },
]

const SORT_OPTIONS = [
  { value: 'outlier_score', label: 'Outlier Score' },
  { value: 'views', label: 'Most Views' },
  { value: 'recent', label: 'Most Recent' },
  { value: 'view_to_sub', label: 'Views/Subs Ratio' },
  { value: 'view_to_avg', label: 'Views vs Avg' },
  { value: 'comments', label: 'Most Comments' },
]

export default function Dashboard() {
  const qc = useQueryClient()
  const [activeTab, setActiveTab] = useState('breakout')
  const [channelTier, setChannelTier] = useState('')
  const [sortBy, setSortBy] = useState('outlier_score')
  const [showFilters, setShowFilters] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
    refetchInterval: 60000,
  })

  // Filtered query for when filters are active
  const filtersActive = channelTier || sortBy !== 'outlier_score'
  const { data: filteredVideos } = useQuery({
    queryKey: ['videos-filtered', activeTab, channelTier, sortBy],
    queryFn: () => getVideos({
      breakoutOnly: activeTab === 'breakout',
      channelTier: channelTier || undefined,
      sortBy,
      limit: 50,
    }),
    enabled: filtersActive,
  })

  function handleSaveToggle() {
    qc.invalidateQueries({ queryKey: ['dashboard'] })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-[#D42B2B] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-[#6B7280] text-sm">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center max-w-sm">
          <div className="w-12 h-12 bg-red-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Zap size={20} className="text-[#D42B2B]" />
          </div>
          <p className="text-[#1A1A1A] font-semibold mb-1">Couldn't load dashboard</p>
          <p className="text-[#6B7280] text-sm mb-4">Make sure the backend is running on port 8000.</p>
          <code className="text-xs text-[#6B7280] bg-[#FAFAFA] px-3 py-2 rounded-lg block">
            cd backend && uvicorn main:app --reload --port 8000
          </code>
        </div>
      </div>
    )
  }

  const breakouts = data?.breakout_videos || []
  const recent = data?.recent_videos || []
  const kwSummary = data?.keyword_summary || []
  const quota = data?.quota
  const stats = data?.stats || {}
  const refreshStatus = data?.refresh_status

  const videos = filtersActive
    ? (filteredVideos || [])
    : (activeTab === 'breakout' ? breakouts : recent)

  const lastRefresh = refreshStatus?.last_done
    ? new Date(refreshStatus.last_done + 'Z').toLocaleString()
    : null

  const isEmpty = breakouts.length === 0 && recent.length === 0

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-8">

      {/* Stats row */}
      {!isEmpty && (
        <div className="grid grid-cols-5 gap-3 mb-8">
          {[
            { icon: Eye, label: 'Videos Tracked', value: stats.total_videos || 0, color: 'text-[#1A1A1A]' },
            { icon: Flame, label: 'Breakouts', value: stats.breakout_count || 0, color: 'text-[#D42B2B]' },
            { icon: TrendingUp, label: 'Top Score', value: stats.top_score || '—', color: 'text-[#C9A962]' },
            { icon: BarChart2, label: 'Avg Score', value: stats.avg_breakout_score || '—', color: 'text-[#6B7280]' },
            { icon: Bookmark, label: 'Saved', value: stats.saved_count || 0, color: 'text-[#C9A962]' },
          ].map(({ icon: Icon, label, value, color }) => (
            <div key={label} className="bg-[#FAFAFA] rounded-xl border border-[#F0F0F0] px-4 py-3.5 flex items-center gap-3">
              <Icon size={18} className={color} />
              <div>
                <p className="text-lg font-bold text-[#1A1A1A] leading-none">{typeof value === 'number' ? value.toLocaleString() : value}</p>
                <p className="text-[11px] text-[#6B7280] mt-0.5">{label}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {isEmpty && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-16 h-16 bg-[#FAFAFA] rounded-3xl flex items-center justify-center mb-6">
            <TrendingUp size={28} className="text-[#D42B2B] opacity-40" />
          </div>
          <h2 className="text-xl font-bold text-[#1A1A1A] mb-2">Ready to find breakout videos</h2>
          <p className="text-[#6B7280] text-sm mb-6 max-w-md text-center">
            Click the <strong>Refresh</strong> button in the top-right to search YouTube for your tracked keywords and discover outlier videos.
          </p>
          {lastRefresh && (
            <p className="text-xs text-[#6B7280]">Last refresh: {lastRefresh}</p>
          )}
        </div>
      )}

      {!isEmpty && (
        <div className="grid grid-cols-12 gap-6">
          {/* Main content */}
          <div className="col-span-9">
            {/* Tabs + Filters */}
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-1 bg-[#FAFAFA] rounded-xl p-1">
                <button
                  onClick={() => setActiveTab('breakout')}
                  className={`flex items-center gap-1.5 px-4 py-2 text-[13px] font-semibold rounded-lg transition-all ${
                    activeTab === 'breakout' ? 'bg-white text-[#1A1A1A] shadow-sm' : 'text-[#6B7280] hover:text-[#1A1A1A]'
                  }`}
                >
                  <Flame size={13} />
                  Breakout
                  {breakouts.length > 0 && (
                    <span className="bg-[#D42B2B] text-white text-[10px] rounded-full px-1.5 py-0.5 leading-none font-bold">
                      {breakouts.length}
                    </span>
                  )}
                </button>
                <button
                  onClick={() => setActiveTab('recent')}
                  className={`flex items-center gap-1.5 px-4 py-2 text-[13px] font-semibold rounded-lg transition-all ${
                    activeTab === 'recent' ? 'bg-white text-[#1A1A1A] shadow-sm' : 'text-[#6B7280] hover:text-[#1A1A1A]'
                  }`}
                >
                  <Clock size={13} />
                  New This Week
                </button>
              </div>

              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors ${
                  showFilters || filtersActive
                    ? 'bg-[#1A1A1A] text-white'
                    : 'text-[#6B7280] hover:bg-[#FAFAFA]'
                }`}
              >
                <Filter size={12} />
                Filters{filtersActive ? ' (active)' : ''}
              </button>
            </div>

            {/* Filter bar */}
            {showFilters && (
              <div className="flex items-center gap-3 mb-5 bg-[#FAFAFA] rounded-xl p-3 border border-[#F0F0F0]">
                <div className="flex items-center gap-2">
                  <label className="text-[11px] text-[#6B7280] font-medium uppercase tracking-wide">Channel Size</label>
                  <select
                    value={channelTier}
                    onChange={e => setChannelTier(e.target.value)}
                    className="text-[12px] text-[#1A1A1A] bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-[#D42B2B]"
                  >
                    {CHANNEL_TIERS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div className="w-px h-5 bg-gray-200" />
                <div className="flex items-center gap-2">
                  <label className="text-[11px] text-[#6B7280] font-medium uppercase tracking-wide">Sort by</label>
                  <select
                    value={sortBy}
                    onChange={e => setSortBy(e.target.value)}
                    className="text-[12px] text-[#1A1A1A] bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-[#D42B2B]"
                  >
                    {SORT_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </div>
                {filtersActive && (
                  <>
                    <div className="w-px h-5 bg-gray-200" />
                    <button
                      onClick={() => { setChannelTier(''); setSortBy('outlier_score') }}
                      className="text-[11px] text-[#D42B2B] font-medium hover:underline"
                    >
                      Clear filters
                    </button>
                  </>
                )}
              </div>
            )}

            {/* Video grid */}
            {videos.length === 0 ? (
              <div className="text-center py-16 text-[#6B7280]">
                <TrendingUp size={32} className="mx-auto mb-3 opacity-15" />
                <p className="text-sm">No {activeTab === 'breakout' ? 'breakout' : 'recent'} videos found{filtersActive ? ' with these filters' : ''}.</p>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-4">
                {videos.map(v => (
                  <VideoCard key={v.video_id} video={v} onSaveToggle={handleSaveToggle} />
                ))}
              </div>
            )}

            {lastRefresh && (
              <p className="text-center text-[11px] text-[#6B7280] mt-6">
                Last refreshed {lastRefresh}
              </p>
            )}
          </div>

          {/* Sidebar */}
          <div className="col-span-3 space-y-5">
            {/* Keyword performance */}
            <div className="bg-[#FAFAFA] rounded-2xl border border-[#F0F0F0] p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold text-[13px] text-[#1A1A1A] flex items-center gap-1.5">
                  <BarChart2 size={13} className="text-[#C9A962]" />
                  Top Keywords
                </h2>
                <Link to="/keywords" className="text-[11px] text-[#D42B2B] hover:underline flex items-center gap-0.5 font-medium">
                  All <ChevronRight size={10} />
                </Link>
              </div>
              {kwSummary.length === 0 ? (
                <p className="text-xs text-[#6B7280]">Refresh to see which keywords produce breakouts.</p>
              ) : (
                <div className="space-y-2">
                  {kwSummary.map(({ keyword, count }, i) => (
                    <div key={keyword} className="flex items-center gap-2">
                      <span className="text-[10px] text-[#6B7280] w-4 text-right shrink-0 font-mono">{i + 1}</span>
                      <span className="text-[12px] text-[#1A1A1A] truncate flex-1">{keyword}</span>
                      <div className="flex items-center gap-1">
                        <div className="w-8 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${Math.min((count / (kwSummary[0]?.count || 1)) * 100, 100)}%`,
                              backgroundColor: 'var(--color-gold)',
                            }}
                          />
                        </div>
                        <span className="text-[10px] font-bold text-[#C9A962] w-5 text-right">{count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Quota */}
            {quota && (
              <div className="bg-[#FAFAFA] rounded-2xl border border-[#F0F0F0] p-5">
                <h2 className="font-bold text-[13px] text-[#1A1A1A] mb-3">API Quota Today</h2>
                <div className="mb-2.5">
                  <div className="flex justify-between text-[11px] mb-1.5">
                    <span className="text-[#6B7280]">{quota.units_used.toLocaleString()} used</span>
                    <span className="text-[#6B7280]">{quota.limit.toLocaleString()}</span>
                  </div>
                  <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min((quota.units_used / quota.limit) * 100, 100)}%`,
                        backgroundColor: quota.units_used > 8000 ? 'var(--color-red)' : quota.units_used > 5000 ? 'var(--color-gold)' : '#22c55e',
                      }}
                    />
                  </div>
                </div>
                <p className="text-[11px] text-[#6B7280]">
                  ~{Math.floor((quota.limit - quota.units_used) / 200)} keyword searches left today
                </p>
              </div>
            )}

            {/* Guide */}
            <div className="bg-[#1A1A1A] rounded-2xl p-5 text-white">
              <h2 className="font-bold text-[13px] mb-3 text-[#C9A962]">Score Guide</h2>
              <div className="space-y-2.5 text-[12px] text-gray-300">
                <div className="flex items-center justify-between">
                  <span>Score 10+</span>
                  <span className="bg-[#D42B2B] text-white text-[10px] font-bold px-2 py-0.5 rounded">Viral</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Score 5–9</span>
                  <span className="bg-[#D42B2B] text-white text-[10px] font-bold px-2 py-0.5 rounded">Strong</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Score 3–5</span>
                  <span className="bg-[#C9A962] text-white text-[10px] font-bold px-2 py-0.5 rounded">Breakout</span>
                </div>
                <div className="border-t border-gray-700 pt-2.5 mt-3 text-[11px] text-gray-400 leading-relaxed">
                  A higher score means the video is performing far above what's normal for that channel.
                  Focus on breakout videos from small channels — that's where the replicable patterns are.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
