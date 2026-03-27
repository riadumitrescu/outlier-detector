import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getTrackedChannels, trackChannel, untrackChannel, scanChannels, getRefreshStatus } from '../api/client'
import { useState } from 'react'
import { Plus, X, Radio, RefreshCw, Users, Eye, Clock, ExternalLink } from 'lucide-react'

function formatNum(n) {
  if (!n) return '0'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toString()
}

function timeAgo(dateStr) {
  if (!dateStr) return 'Never'
  const diff = (Date.now() - new Date(dateStr + 'Z').getTime()) / 1000
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
  return new Date(dateStr).toLocaleDateString()
}

export default function Channels() {
  const qc = useQueryClient()
  const [channelUrl, setChannelUrl] = useState('')
  const [adding, setAdding] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState('')

  const { data: channels = [], isLoading } = useQuery({
    queryKey: ['tracked-channels'],
    queryFn: getTrackedChannels,
  })

  // Extract channel ID from various YouTube URL formats or direct ID
  function parseChannelInput(input) {
    const trimmed = input.trim()
    // Direct channel ID (UC...)
    if (/^UC[\w-]{22}$/.test(trimmed)) return { id: trimmed }
    // youtube.com/channel/UCxxx
    const channelMatch = trimmed.match(/youtube\.com\/channel\/(UC[\w-]+)/)
    if (channelMatch) return { id: channelMatch[1] }
    // youtube.com/@handle
    const handleMatch = trimmed.match(/youtube\.com\/@([\w.-]+)/)
    if (handleMatch) return { handle: handleMatch[1] }
    // Just a handle
    if (trimmed.startsWith('@')) return { handle: trimmed.slice(1) }
    return null
  }

  async function handleAdd(e) {
    e.preventDefault()
    setError('')
    const parsed = parseChannelInput(channelUrl)
    if (!parsed) {
      setError('Enter a YouTube channel URL, @handle, or channel ID (UC...)')
      return
    }
    setAdding(true)
    try {
      // For handles, we'd need to resolve them. For now, require channel ID or URL.
      if (parsed.handle) {
        setError(`Handle "@${parsed.handle}" — for now, please use the channel URL (youtube.com/channel/UC...) or track channels from the video detail page.`)
        setAdding(false)
        return
      }
      await trackChannel(parsed.id)
      setChannelUrl('')
      qc.invalidateQueries({ queryKey: ['tracked-channels'] })
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to track channel')
    } finally {
      setAdding(false)
    }
  }

  async function handleUntrack(channelId) {
    await untrackChannel(channelId)
    qc.invalidateQueries({ queryKey: ['tracked-channels'] })
  }

  async function handleScan() {
    setScanning(true)
    try {
      await scanChannels()
      // Poll for completion
      const poll = setInterval(async () => {
        const status = await getRefreshStatus()
        if (!status.running) {
          clearInterval(poll)
          setScanning(false)
          qc.invalidateQueries({ queryKey: ['tracked-channels'] })
          qc.invalidateQueries({ queryKey: ['dashboard'] })
        }
      }, 3000)
    } catch (err) {
      setScanning(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="flex items-end justify-between mb-8">
        <div>
          <h1 className="text-2xl font-black text-[#1A1A1A] mb-1">Tracked Channels</h1>
          <p className="text-[#6B7280] text-[13px]">
            {channels.length} channel{channels.length !== 1 ? 's' : ''} monitored for breakout videos
          </p>
        </div>
        <button
          onClick={handleScan}
          disabled={scanning || channels.length === 0}
          className="flex items-center gap-2 px-4 py-2.5 text-[12px] font-semibold bg-[#D42B2B] text-white rounded-xl hover:bg-[#B91C1C] disabled:opacity-50 transition-colors"
        >
          <RefreshCw size={13} className={scanning ? 'animate-spin' : ''} />
          {scanning ? 'Scanning...' : 'Scan All Channels'}
        </button>
      </div>

      {/* Add channel */}
      <form onSubmit={handleAdd} className="flex gap-2 mb-6">
        <div className="flex-1 relative">
          <Radio size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-300" />
          <input
            value={channelUrl}
            onChange={e => { setChannelUrl(e.target.value); setError('') }}
            placeholder="Paste channel URL (youtube.com/channel/UC...) or channel ID"
            className="w-full pl-9 pr-4 py-2.5 text-[13px] border border-[#F0F0F0] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#D42B2B] focus:border-transparent bg-[#FAFAFA]"
          />
        </div>
        <button
          type="submit"
          disabled={!channelUrl.trim() || adding}
          className="flex items-center gap-1 px-4 py-2.5 text-[13px] font-semibold bg-[#D42B2B] text-white rounded-xl hover:bg-[#B91C1C] disabled:opacity-40 transition-colors"
        >
          <Plus size={14} /> Track
        </button>
      </form>

      {error && (
        <p className="text-[12px] text-[#D42B2B] mb-4 bg-red-50 rounded-xl px-4 py-2">{error}</p>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <div className="w-6 h-6 border-2 border-[#D42B2B] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : channels.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-16 h-16 bg-[#FAFAFA] rounded-3xl flex items-center justify-center mx-auto mb-4">
            <Radio size={28} className="text-[#D42B2B] opacity-30" />
          </div>
          <h2 className="text-lg font-bold text-[#1A1A1A] mb-2">No channels tracked yet</h2>
          <p className="text-[#6B7280] text-[13px] max-w-md mx-auto">
            Track channels to automatically discover their breakout videos.
            The easiest way: find a good video on the Dashboard, open it, and click <strong>"Track Channel"</strong>.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {channels.map(ch => (
            <div
              key={ch.channel_id}
              className="flex items-center justify-between bg-[#FAFAFA] border border-[#F0F0F0] rounded-xl px-5 py-4 group hover:border-gray-200 transition-colors"
            >
              <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center shrink-0">
                  <Users size={16} className="text-[#6B7280]" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <h3 className="font-semibold text-[14px] text-[#1A1A1A] truncate">{ch.channel_name || ch.channel_id}</h3>
                    <a
                      href={`https://youtube.com/channel/${ch.channel_id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-gray-300 hover:text-[#D42B2B] transition-colors"
                    >
                      <ExternalLink size={11} />
                    </a>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-[#6B7280]">
                    <span className="flex items-center gap-1">
                      <Users size={10} />
                      {formatNum(ch.current_subs || ch.subscriber_count)} subs
                    </span>
                    <span className="flex items-center gap-1">
                      <Eye size={10} />
                      {formatNum(Math.round(ch.current_avg || ch.avg_views))} avg views
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock size={10} />
                      Scanned: {timeAgo(ch.last_scanned)}
                    </span>
                  </div>
                  {ch.why_tracked && (
                    <p className="text-[11px] text-[#6B7280] mt-1 italic">"{ch.why_tracked}"</p>
                  )}
                </div>
              </div>

              <button
                onClick={() => handleUntrack(ch.channel_id)}
                className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-red-50 text-gray-300 hover:text-[#D42B2B] transition-all"
                title="Stop tracking"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="mt-8 p-4 bg-[#1A1A1A] rounded-xl text-[12px] text-gray-300 leading-relaxed">
        <strong className="text-[#C9A962]">How channel tracking works:</strong>
        <ul className="mt-2 space-y-1 list-disc list-inside">
          <li>Track channels in your niche that consistently make content you'd want to study</li>
          <li>"Scan All Channels" fetches their recent 30 videos and scores them for breakouts</li>
          <li>This is the most reliable way to find outliers — better than keyword search alone</li>
          <li>Easiest way to add: find a video on the Dashboard → open it → "Track Channel"</li>
        </ul>
      </div>
    </div>
  )
}
