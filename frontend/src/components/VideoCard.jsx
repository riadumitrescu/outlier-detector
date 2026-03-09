import { Link } from 'react-router-dom'
import { BookmarkPlus, BookmarkCheck, TrendingUp, Users } from 'lucide-react'
import { saveVideo, unsaveVideo } from '../api/client'
import { useState } from 'react'

function formatNum(n) {
  if (!n) return '0'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toString()
}

function formatDuration(secs) {
  if (!secs) return ''
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = (Date.now() - new Date(dateStr).getTime()) / 1000
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
  return new Date(dateStr).toLocaleDateString()
}

function ScoreBadge({ score }) {
  if (!score || score <= 0) return null
  let bg, text
  if (score >= 10) { bg = '#D42B2B'; text = 'white' }
  else if (score >= 5) { bg = '#D42B2B'; text = 'white' }
  else if (score >= 3) { bg = '#C9A962'; text = 'white' }
  else { bg = '#e5e7eb'; text = '#374151' }
  return (
    <span className="font-bold px-2 py-0.5 rounded-md text-[11px] leading-none" style={{ backgroundColor: bg, color: text }}>
      {score.toFixed(1)}
    </span>
  )
}

function ChannelTierDot({ count }) {
  if (!count) return null
  let color = '#d1d5db'
  if (count >= 1000000) color = '#D42B2B'
  else if (count >= 100000) color = '#C9A962'
  else if (count >= 10000) color = '#22c55e'
  else if (count >= 1000) color = '#3b82f6'
  return <span className="w-1.5 h-1.5 rounded-full inline-block shrink-0" style={{ backgroundColor: color }} title={`${formatNum(count)} subscribers`} />
}

export default function VideoCard({ video, onSaveToggle }) {
  const [saved, setSaved] = useState(!!video.is_saved)
  const [saving, setSaving] = useState(false)

  const score = video.outlier_score || 0
  const avgMult = video.view_to_average_ratio || 0

  async function handleSaveToggle(e) {
    e.preventDefault()
    e.stopPropagation()
    setSaving(true)
    try {
      if (saved) { await unsaveVideo(video.video_id); setSaved(false) }
      else { await saveVideo(video.video_id, ''); setSaved(true) }
      onSaveToggle?.()
    } catch (err) { console.error('Save error:', err) }
    finally { setSaving(false) }
  }

  return (
    <Link
      to={`/video/${video.video_id}`}
      className="block bg-white rounded-2xl border border-[#F0F0F0] overflow-hidden hover:border-gray-200 hover:shadow-lg transition-all duration-200 group"
    >
      <div className="relative">
        {video.thumbnail_url ? (
          <img src={video.thumbnail_url} alt="" className="w-full aspect-video object-cover" loading="lazy" />
        ) : (
          <div className="w-full aspect-video bg-gray-50" />
        )}

        {video.duration_seconds > 0 && (
          <span className="absolute bottom-2 right-2 bg-black/80 text-white text-[10px] px-1.5 py-0.5 rounded font-mono">
            {formatDuration(video.duration_seconds)}
          </span>
        )}

        {video.is_breakout ? (
          <span className="absolute top-2 left-2 flex items-center gap-1 bg-[#D42B2B] text-white text-[10px] font-bold px-2 py-0.5 rounded-lg shadow-sm">
            <TrendingUp size={9} /> BREAKOUT
          </span>
        ) : null}

        <button
          onClick={handleSaveToggle}
          disabled={saving}
          className="absolute top-2 right-2 p-1.5 rounded-lg bg-white/90 hover:bg-white shadow-sm transition-colors opacity-0 group-hover:opacity-100"
          title={saved ? 'Unsave' : 'Save'}
        >
          {saved
            ? <BookmarkCheck size={14} className="text-[#C9A962]" />
            : <BookmarkPlus size={14} className="text-gray-400" />
          }
        </button>
      </div>

      <div className="p-3.5">
        <h3 className="font-semibold text-[13px] leading-snug line-clamp-2 text-[#1A1A1A] group-hover:text-[#D42B2B] transition-colors mb-1.5">
          {video.title}
        </h3>

        <div className="flex items-center gap-1.5 text-[11px] text-[#6B7280] mb-3">
          <ChannelTierDot count={video.subscriber_count} />
          <span className="truncate">{video.channel_name}</span>
          <span>·</span>
          <span className="shrink-0">{timeAgo(video.published_at)}</span>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 text-[11px] text-[#6B7280]">
            <span>{formatNum(video.view_count)} views</span>
            {video.subscriber_count > 0 && (
              <span className="flex items-center gap-0.5">
                <Users size={10} />
                {formatNum(video.subscriber_count)}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            {avgMult >= 2 && (
              <span className="text-[10px] text-[#6B7280] font-medium">{avgMult.toFixed(1)}x avg</span>
            )}
            <ScoreBadge score={score} />
          </div>
        </div>
      </div>
    </Link>
  )
}
