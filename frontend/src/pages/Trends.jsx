import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getTikTokTrends, scanTikTokKeyword, getAllTrends, getRefreshStatus, getKeywords } from '../api/client'
import { useState, useEffect, useRef } from 'react'
import {
  TrendingUp, TrendingDown, Minus, Zap, Clock, Search,
  RefreshCw, ArrowRight, Sparkles, ExternalLink, ChevronDown, ChevronUp
} from 'lucide-react'

const SIGNAL_COLORS = {
  'make it NOW': { bg: 'bg-red-50', text: 'text-[#D42B2B]', border: 'border-red-200' },
  'strong opportunity': { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  'worth considering': { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  'low priority': { bg: 'bg-gray-50', text: 'text-gray-500', border: 'border-gray-200' },
  'skip': { bg: 'bg-gray-50', text: 'text-gray-400', border: 'border-gray-100' },
}

function DirectionIcon({ direction, size = 14 }) {
  if (direction === 'rising') return <TrendingUp size={size} className="text-emerald-500" />
  if (direction === 'declining') return <TrendingDown size={size} className="text-red-400" />
  return <Minus size={size} className="text-gray-400" />
}

function DirectionBadge({ direction }) {
  const colors = {
    rising: 'bg-emerald-50 text-emerald-700',
    declining: 'bg-red-50 text-red-600',
    stable: 'bg-gray-100 text-gray-500',
    unknown: 'bg-gray-100 text-gray-400',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${colors[direction] || colors.unknown}`}>
      {direction || 'unknown'}
    </span>
  )
}

function MiniSparkline({ data, color = '#D42B2B', height = 28, width = 80 }) {
  if (!data || data.length === 0) return null
  const values = data.map(d => d.value)
  const max = Math.max(...values) || 1
  const min = Math.min(...values)
  const range = max - min || 1
  const points = values.map((v, i) =>
    `${(i / (values.length - 1)) * width},${height - ((v - min) / range) * (height - 4) - 2}`
  ).join(' ')
  return (
    <svg width={width} height={height} className="shrink-0">
      <polyline fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" points={points} />
    </svg>
  )
}

function OpportunityMeter({ score, max = 10 }) {
  const pct = (score / max) * 100
  let color = '#E5E7EB'
  if (score >= 7) color = '#D42B2B'
  else if (score >= 5) color = '#C9A962'
  else if (score >= 3) color = '#3B82F6'
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-[11px] font-bold" style={{ color }}>{score}/{max}</span>
    </div>
  )
}

function TikTokTrendCard({ trend }) {
  const [expanded, setExpanded] = useState(false)
  const opp = trend.opportunity_score || {}
  const pc = trend.platform_comparison || {}
  const signalStyle = SIGNAL_COLORS[opp.label] || SIGNAL_COLORS.skip

  return (
    <div className={`border rounded-xl overflow-hidden transition-all ${signalStyle.border} ${opp.score >= 5 ? 'ring-1 ring-amber-100' : ''}`}>
      <div
        className={`px-5 py-4 cursor-pointer hover:bg-gray-50/50 transition-colors ${signalStyle.bg}`}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <OpportunityMeter score={opp.score || 0} />
            <h3 className="font-semibold text-[14px] text-[#1A1A1A] truncate">{trend.keyword}</h3>
            {pc.lag_opportunity && (
              <span className="flex items-center gap-1 px-2 py-0.5 bg-[#D42B2B] text-white rounded-full text-[10px] font-bold shrink-0">
                <Zap size={10} /> LAG WINDOW
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span className={`text-[11px] font-semibold ${signalStyle.text}`}>{opp.label || 'scanning...'}</span>
            {expanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="px-5 py-4 bg-white border-t border-gray-100 space-y-4">
          {/* Platform comparison */}
          {pc.available !== false && (
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-[#FAFAFA] rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Web / TikTok</span>
                  <DirectionBadge direction={pc.web?.direction} />
                </div>
                <MiniSparkline data={pc.web?.data} color={pc.web?.direction === 'rising' ? '#10B981' : '#6B7280'} width={120} height={32} />
              </div>
              <div className="p-3 bg-[#FAFAFA] rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">YouTube</span>
                  <DirectionBadge direction={pc.youtube?.direction} />
                </div>
                <MiniSparkline data={pc.youtube?.data} color={pc.youtube?.direction === 'rising' ? '#D42B2B' : '#6B7280'} width={120} height={32} />
              </div>
            </div>
          )}

          {/* Signal explanation */}
          {pc.signal && (
            <div className="flex items-start gap-2 p-3 bg-amber-50/50 rounded-lg">
              <Sparkles size={14} className="text-[#C9A962] mt-0.5 shrink-0" />
              <p className="text-[12px] text-gray-600 leading-relaxed">{pc.signal}</p>
            </div>
          )}

          {/* Opportunity reasons */}
          {opp.reasons?.length > 0 && (
            <div className="space-y-1">
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Why this score</span>
              <ul className="space-y-0.5">
                {opp.reasons.map((r, i) => (
                  <li key={i} className="flex items-center gap-2 text-[12px] text-gray-600">
                    <span className="w-1 h-1 bg-[#C9A962] rounded-full shrink-0" />
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* TikTok suggestions */}
          {trend.suggestions?.length > 0 && (
            <div>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-2 block">
                Related TikTok Searches
              </span>
              <div className="flex flex-wrap gap-1.5">
                {(typeof trend.suggestions === 'string' ? JSON.parse(trend.suggestions) : trend.suggestions).map((s, i) => (
                  <a
                    key={i}
                    href={`https://www.tiktok.com/search?q=${encodeURIComponent(s)}`}
                    target="_blank"
                    rel="noreferrer"
                    className="px-2.5 py-1 bg-[#FAFAFA] hover:bg-gray-100 rounded-lg text-[11px] text-gray-600 hover:text-[#1A1A1A] transition-colors flex items-center gap-1"
                  >
                    {s}
                    <ExternalLink size={9} className="opacity-40" />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Hashtag views */}
          {trend.hashtag_views != null && trend.hashtag_views > 0 && (
            <div className="flex items-center gap-2 text-[12px] text-gray-500">
              <Search size={12} />
              <span>TikTok hashtag: <strong className="text-[#1A1A1A]">{formatViews(trend.hashtag_views)}</strong> views</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function formatViews(n) {
  if (!n) return '0'
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toString()
}

export default function Trends() {
  const qc = useQueryClient()
  const [scanning, setScanning] = useState(false)
  const [filter, setFilter] = useState('all') // all, opportunities, rising

  const { data: tiktokTrends = [], isLoading: loadingTT } = useQuery({
    queryKey: ['tiktok-trends'],
    queryFn: getTikTokTrends,
  })

  const { data: googleTrends = {}, isLoading: loadingGT } = useQuery({
    queryKey: ['google-trends'],
    queryFn: getAllTrends,
  })

  const [scanProgress, setScanProgress] = useState(null)
  const abortRef = useRef(false)

  async function handleScan() {
    setScanning(true)
    abortRef.current = false
    try {
      const keywords = await getKeywords()
      const activeKws = keywords.filter(k => k.active)

      for (let i = 0; i < activeKws.length; i++) {
        if (abortRef.current) break
        const kw = activeKws[i].keyword
        setScanProgress(`Scanning ${i + 1}/${activeKws.length}: ${kw}`)
        try {
          await scanTikTokKeyword(kw)
        } catch (err) {
          console.warn(`TikTok scan failed for "${kw}":`, err)
        }
      }

      setScanProgress(`Done — ${activeKws.length} keywords scanned`)
      qc.invalidateQueries({ queryKey: ['tiktok-trends'] })
      setTimeout(() => setScanProgress(null), 4000)
    } catch {
      setScanProgress(null)
    } finally {
      setScanning(false)
    }
  }

  // Sort TikTok trends by opportunity score
  const sortedTrends = [...tiktokTrends].sort((a, b) => {
    const scoreA = a.opportunity_score?.score || 0
    const scoreB = b.opportunity_score?.score || 0
    return scoreB - scoreA
  })

  const filteredTrends = sortedTrends.filter(t => {
    if (filter === 'opportunities') return (t.opportunity_score?.score || 0) >= 5
    if (filter === 'rising') return t.platform_comparison?.web?.direction === 'rising'
    return true
  })

  // Google Trends as a simple list
  const googleList = Object.entries(googleTrends)
    .map(([kw, data]) => ({ keyword: kw, ...data }))
    .sort((a, b) => {
      const order = { rising: 0, stable: 1, declining: 2, unknown: 3 }
      return (order[a.direction] ?? 3) - (order[b.direction] ?? 3)
    })

  const lagCount = sortedTrends.filter(t => t.platform_comparison?.lag_opportunity).length
  const hotCount = sortedTrends.filter(t => (t.opportunity_score?.score || 0) >= 5).length

  const isRunning = scanning || status?.running

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-end justify-between mb-8">
        <div>
          <h1 className="text-2xl font-black text-[#1A1A1A] mb-1">Trend Scanner</h1>
          <p className="text-[#6B7280] text-[13px]">
            Cross-platform trend analysis — find what's blowing up on TikTok before it hits YouTube
          </p>
        </div>
        <button
          onClick={handleScan}
          disabled={isRunning}
          className="flex items-center gap-2 px-4 py-2.5 text-[12px] font-semibold bg-[#1A1A1A] text-white rounded-xl hover:bg-black disabled:opacity-50 transition-colors"
        >
          <RefreshCw size={13} className={isRunning ? 'animate-spin' : ''} />
          {isRunning ? 'Scanning...' : 'Scan TikTok Trends'}
        </button>
      </div>

      {/* Progress bar */}
      {scanProgress && (
        <div className="mb-6 p-3 bg-[#FAFAFA] rounded-xl flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-[#C9A962] animate-pulse" />
          <span className="text-[12px] text-[#6B7280] font-medium">{scanProgress}</span>
        </div>
      )}

      {/* Stats */}
      {sortedTrends.length > 0 && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="bg-[#FAFAFA] rounded-xl p-4 text-center">
            <div className="text-2xl font-black text-[#1A1A1A]">{sortedTrends.length}</div>
            <div className="text-[11px] text-[#6B7280] font-medium">Keywords Scanned</div>
          </div>
          <div className="bg-red-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-black text-[#D42B2B]">{lagCount}</div>
            <div className="text-[11px] text-[#D42B2B] font-medium">Lag Windows</div>
          </div>
          <div className="bg-amber-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-black text-amber-700">{hotCount}</div>
            <div className="text-[11px] text-amber-700 font-medium">Hot Opportunities</div>
          </div>
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex items-center gap-1 bg-[#FAFAFA] rounded-xl p-1 mb-6 w-fit">
        {[
          { id: 'all', label: 'All Keywords' },
          { id: 'opportunities', label: 'Hot Opportunities' },
          { id: 'rising', label: 'Rising' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setFilter(tab.id)}
            className={`px-3.5 py-1.5 rounded-lg text-[12px] font-medium transition-all ${
              filter === tab.id ? 'bg-white text-[#1A1A1A] shadow-sm' : 'text-[#6B7280] hover:text-[#1A1A1A]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TikTok Trends */}
      <div className="mb-10">
        <h2 className="text-lg font-bold text-[#1A1A1A] mb-4 flex items-center gap-2">
          <span className="w-6 h-6 bg-[#1A1A1A] rounded-lg flex items-center justify-center">
            <Zap size={12} className="text-white" />
          </span>
          TikTok × YouTube Cross-Platform Trends
        </h2>

        {loadingTT ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-6 h-6 border-2 border-[#1A1A1A] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filteredTrends.length === 0 ? (
          <div className="text-center py-16 bg-[#FAFAFA] rounded-xl">
            <div className="w-16 h-16 bg-white rounded-3xl flex items-center justify-center mx-auto mb-4 shadow-sm">
              <TrendingUp size={28} className="text-gray-300" />
            </div>
            <h3 className="text-lg font-bold text-[#1A1A1A] mb-2">No trend data yet</h3>
            <p className="text-[#6B7280] text-[13px] max-w-md mx-auto mb-4">
              Click "Scan TikTok Trends" to analyze your keywords across platforms and find the TikTok→YouTube lag window.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredTrends.map(trend => (
              <TikTokTrendCard key={trend.keyword} trend={trend} />
            ))}
          </div>
        )}
      </div>

      {/* Google Trends section */}
      {googleList.length > 0 && (
        <div>
          <h2 className="text-lg font-bold text-[#1A1A1A] mb-4 flex items-center gap-2">
            <span className="w-6 h-6 bg-[#D42B2B] rounded-lg flex items-center justify-center">
              <TrendingUp size={12} className="text-white" />
            </span>
            YouTube Search Trends (Google Trends)
          </h2>
          <div className="grid grid-cols-2 gap-2">
            {googleList.map(t => (
              <div key={t.keyword} className="flex items-center justify-between p-3 bg-[#FAFAFA] rounded-xl hover:bg-gray-100/80 transition-colors">
                <div className="flex items-center gap-3 min-w-0">
                  <DirectionIcon direction={t.direction} />
                  <span className="text-[13px] font-medium text-[#1A1A1A] truncate">{t.keyword}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <MiniSparkline data={t.trend_data} color={t.direction === 'rising' ? '#10B981' : t.direction === 'declining' ? '#EF4444' : '#9CA3AF'} width={60} height={20} />
                  <DirectionBadge direction={t.direction} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strategy guide */}
      <div className="mt-10 p-5 bg-[#1A1A1A] rounded-xl text-[12px] text-gray-300 leading-relaxed">
        <strong className="text-[#C9A962] text-[13px]">How the TikTok→YouTube lag works:</strong>
        <div className="grid grid-cols-2 gap-4 mt-3">
          <ul className="space-y-1.5 list-disc list-inside">
            <li>Topics blow up on TikTok <strong className="text-white">4–8 weeks</strong> before YouTube catches up</li>
            <li><span className="text-[#D42B2B] font-bold">LAG WINDOW</span> = trending on TikTok/web but not yet on YouTube</li>
            <li>Make the YouTube version <em>before</em> it peaks there</li>
          </ul>
          <ul className="space-y-1.5 list-disc list-inside">
            <li>"Limerence," "nervous system," "soft life" all followed this pattern</li>
            <li>Higher opportunity score = more urgency to create</li>
            <li>Click any TikTok suggestion to see what's going viral right now</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
