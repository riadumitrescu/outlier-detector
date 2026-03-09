import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getKeywords, addKeyword, removeKeyword, getAllTrends, triggerRefresh } from '../api/client'
import { useState } from 'react'
import { Plus, X, TrendingUp, TrendingDown, Minus, Tag, RefreshCw, Search } from 'lucide-react'

function TrendIndicator({ direction }) {
  if (direction === 'rising') return <span className="flex items-center gap-1 text-[11px] text-green-600 font-medium"><TrendingUp size={11} /> Rising</span>
  if (direction === 'declining') return <span className="flex items-center gap-1 text-[11px] text-[#D42B2B] font-medium"><TrendingDown size={11} /> Declining</span>
  if (direction === 'stable') return <span className="flex items-center gap-1 text-[11px] text-[#6B7280]"><Minus size={11} /> Stable</span>
  return <span className="text-[11px] text-gray-300">--</span>
}

function Sparkline({ data }) {
  if (!data || data.length < 3) return null
  const values = data.map(d => d.value)
  const max = Math.max(...values)
  const min = Math.min(...values)
  const range = max - min || 1
  const w = 70; const h = 20
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w
    const y = h - ((v - min) / range) * h
    return `${x},${y}`
  }).join(' ')
  return (
    <svg width={w} height={h} className="overflow-visible shrink-0">
      <polyline points={points} fill="none" stroke="var(--color-gold)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function Keywords() {
  const qc = useQueryClient()
  const [input, setInput] = useState('')
  const [loadingTrends, setLoadingTrends] = useState(false)
  const [trendsData, setTrendsData] = useState(null)

  const { data: keywords = [], isLoading } = useQuery({
    queryKey: ['keywords'],
    queryFn: getKeywords,
  })

  async function handleAdd(e) {
    e.preventDefault()
    const kw = input.trim().toLowerCase()
    if (!kw) return
    await addKeyword(kw)
    setInput('')
    qc.invalidateQueries({ queryKey: ['keywords'] })
  }

  async function handleRemove(kw) {
    await removeKeyword(kw)
    qc.invalidateQueries({ queryKey: ['keywords'] })
  }

  async function handleRefreshKeyword(kw) {
    await triggerRefresh(14, kw)
  }

  async function handleFetchTrends() {
    setLoadingTrends(true)
    try {
      const data = await getAllTrends()
      setTrendsData(data)
    } catch (e) { console.error('Trends error:', e) }
    finally { setLoadingTrends(false) }
  }

  const active = keywords.filter(k => k.active)
  const inactive = keywords.filter(k => !k.active)

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <div className="flex items-end justify-between mb-8">
        <div>
          <h1 className="text-2xl font-black text-[#1A1A1A] mb-1">Keyword Tracker</h1>
          <p className="text-[#6B7280] text-[13px]">{active.length} active keywords tracked</p>
        </div>
        <button
          onClick={handleFetchTrends}
          disabled={loadingTrends}
          className="flex items-center gap-2 px-3.5 py-2 text-[12px] font-semibold bg-[#1A1A1A] text-white rounded-xl hover:bg-gray-800 disabled:opacity-60 transition-colors"
        >
          <TrendingUp size={13} />
          {loadingTrends ? 'Loading...' : 'Google Trends'}
        </button>
      </div>

      {/* Add form */}
      <form onSubmit={handleAdd} className="flex gap-2 mb-6">
        <div className="flex-1 relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-300" />
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Add a keyword (e.g. morning routine, deep work)"
            className="w-full pl-9 pr-4 py-2.5 text-[13px] border border-[#F0F0F0] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#D42B2B] focus:border-transparent bg-[#FAFAFA]"
          />
        </div>
        <button type="submit" disabled={!input.trim()} className="flex items-center gap-1 px-4 py-2.5 text-[13px] font-semibold bg-[#D42B2B] text-white rounded-xl hover:bg-[#B91C1C] disabled:opacity-40 transition-colors">
          <Plus size={14} /> Add
        </button>
      </form>

      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <div className="w-6 h-6 border-2 border-[#D42B2B] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          <div className="space-y-1.5">
            {active.map(k => {
              const trend = trendsData?.[k.keyword]
              return (
                <div key={k.keyword} className="flex items-center justify-between bg-[#FAFAFA] border border-[#F0F0F0] rounded-xl px-4 py-3 group hover:border-gray-200 transition-colors">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <Tag size={12} className="text-gray-300 shrink-0" />
                    <span className="text-[13px] font-medium text-[#1A1A1A] truncate">{k.keyword}</span>
                    {trend && <TrendIndicator direction={trend.direction} />}
                  </div>
                  <div className="flex items-center gap-4">
                    {trend?.trend_data && <Sparkline data={trend.trend_data.slice(-12)} />}
                    <button
                      onClick={() => handleRefreshKeyword(k.keyword)}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-blue-50 text-gray-300 hover:text-blue-500 transition-all"
                      title="Refresh this keyword only"
                    >
                      <RefreshCw size={12} />
                    </button>
                    <button
                      onClick={() => handleRemove(k.keyword)}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-red-50 text-gray-300 hover:text-[#D42B2B] transition-all"
                      title="Remove"
                    >
                      <X size={12} />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>

          {inactive.length > 0 && (
            <div className="mt-6">
              <p className="text-[11px] text-[#6B7280] uppercase tracking-wide font-medium mb-2">Removed</p>
              <div className="flex flex-wrap gap-1.5">
                {inactive.map(k => (
                  <button
                    key={k.keyword}
                    onClick={async () => { await addKeyword(k.keyword); qc.invalidateQueries({ queryKey: ['keywords'] }) }}
                    className="text-[11px] text-gray-400 bg-gray-50 border border-[#F0F0F0] px-2.5 py-1 rounded-lg hover:text-[#1A1A1A] hover:border-gray-300 transition-colors"
                  >
                    + {k.keyword}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="mt-8 p-4 bg-[#FAFAFA] border border-[#F0F0F0] rounded-xl text-[12px] text-[#6B7280] leading-relaxed">
            <strong className="text-[#1A1A1A]">Tip:</strong> Hover a keyword and click the refresh icon to search only that keyword (saves quota).
            Google Trends data is cached for 12 hours.
          </div>
        </>
      )}
    </div>
  )
}
