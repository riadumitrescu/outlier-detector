import { useParams, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getVideo, getTranscript, saveVideo, unsaveVideo, updateNotes } from '../api/client'
import { useState, useEffect } from 'react'
import {
  ArrowLeft, BookmarkPlus, BookmarkCheck, ExternalLink,
  Eye, ThumbsUp, MessageSquare, Users, TrendingUp, Clock,
  ChevronDown, ChevronUp, Zap, FileText, Hash, Lightbulb,
  Target, BarChart2, Sparkles, Copy, Check
} from 'lucide-react'

function fmtNum(n) {
  if (!n) return '0'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n?.toLocaleString?.() || '0'
}

function fmtDuration(secs) {
  if (!secs) return '--'
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}h ${m}m`
  return `${m}m ${s}s`
}

function Section({ icon: Icon, title, children, defaultOpen = true, accent }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="bg-[#FAFAFA] rounded-2xl border border-[#F0F0F0] overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between p-5 hover:bg-gray-50/50 transition-colors">
        <h2 className="font-bold text-[14px] text-[#1A1A1A] flex items-center gap-2">
          <Icon size={15} className={accent || 'text-[#6B7280]'} /> {title}
        </h2>
        {open ? <ChevronUp size={14} className="text-[#6B7280]" /> : <ChevronDown size={14} className="text-[#6B7280]" />}
      </button>
      {open && <div className="px-5 pb-5 -mt-1">{children}</div>}
    </div>
  )
}

function MetricRow({ label, value, highlight, sub }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-[#F0F0F0] last:border-0">
      <span className="text-[12px] text-[#6B7280]">{label}</span>
      <div className="text-right">
        <span className={`text-[13px] font-bold ${highlight ? 'text-[#D42B2B]' : 'text-[#1A1A1A]'}`}>{value}</span>
        {sub && <span className="text-[10px] text-[#6B7280] ml-1.5">{sub}</span>}
      </div>
    </div>
  )
}

function StrengthMeter({ score, max, label }) {
  const pct = (score / max) * 100
  let color = '#d1d5db'
  if (label === 'very strong') color = '#22c55e'
  else if (label === 'strong') color = '#C9A962'
  else if (label === 'moderate') color = '#f59e0b'
  else color = '#ef4444'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-[11px] font-semibold uppercase tracking-wide shrink-0" style={{ color }}>{label}</span>
    </div>
  )
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  function copy() {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={copy} className="p-1 rounded hover:bg-gray-100 text-[#6B7280] transition-colors" title="Copy">
      {copied ? <Check size={12} className="text-green-600" /> : <Copy size={12} />}
    </button>
  )
}

export default function VideoDetail() {
  const { videoId } = useParams()
  const qc = useQueryClient()
  const [showFullDesc, setShowFullDesc] = useState(false)
  const [showFullTranscript, setShowFullTranscript] = useState(false)
  const [notes, setNotes] = useState('')
  const [notesSaved, setNotesSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(null)

  const { data: video, isLoading, error } = useQuery({
    queryKey: ['video', videoId],
    queryFn: () => getVideo(videoId),
  })

  useEffect(() => {
    if (video?.notes) setNotes(video.notes)
  }, [video])

  const { data: transcript, isLoading: transcriptLoading } = useQuery({
    queryKey: ['transcript', videoId],
    queryFn: () => getTranscript(videoId),
  })

  const isSaved = saved !== null ? saved : video?.is_saved

  async function handleSaveToggle() {
    setSaving(true)
    try {
      if (isSaved) { await unsaveVideo(videoId); setSaved(false) }
      else { await saveVideo(videoId, notes); setSaved(true) }
      qc.invalidateQueries({ queryKey: ['saved'] })
    } finally { setSaving(false) }
  }

  async function handleSaveNotes() {
    await updateNotes(videoId, notes)
    setNotesSaved(true)
    setTimeout(() => setNotesSaved(false), 2000)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="w-10 h-10 border-2 border-[#D42B2B] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error || !video) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-10 text-center">
        <p className="text-[#D42B2B] font-semibold mb-2">Video not found</p>
        <Link to="/" className="text-sm text-[#6B7280] hover:text-[#1A1A1A]">Back to Dashboard</Link>
      </div>
    )
  }

  const ta = video.title_analysis || {}
  const da = video.description_analysis || {}
  const metrics = video.metrics || {}
  const score = video.outlier_score || 0
  const description = video.description || ''

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-6">
      <Link to="/" className="inline-flex items-center gap-1.5 text-[12px] text-[#6B7280] hover:text-[#1A1A1A] mb-5 transition-colors font-medium">
        <ArrowLeft size={13} /> Dashboard
      </Link>

      <div className="grid grid-cols-12 gap-6">
        {/* Main — 8 cols */}
        <div className="col-span-8 space-y-5">

          {/* Hero */}
          <div className="bg-[#FAFAFA] rounded-2xl border border-[#F0F0F0] overflow-hidden">
            {video.thumbnail_url && (
              <div className="relative">
                <img src={video.thumbnail_url} alt="" className="w-full" />
                {video.is_breakout && (
                  <div className="absolute top-3 left-3 flex items-center gap-1 bg-[#D42B2B] text-white text-[12px] font-bold px-3 py-1 rounded-xl shadow-md">
                    <TrendingUp size={12} /> BREAKOUT
                  </div>
                )}
                <a
                  href={`https://www.youtube.com/watch?v=${video.video_id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="absolute bottom-3 right-3 flex items-center gap-1.5 bg-black/80 text-white text-xs font-medium px-3 py-1.5 rounded-xl hover:bg-black transition-colors"
                >
                  Watch on YouTube <ExternalLink size={11} />
                </a>
              </div>
            )}
            <div className="p-5">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h1 className="text-lg font-black text-[#1A1A1A] leading-tight">{video.title}</h1>
                    <CopyButton text={video.title} />
                  </div>
                  <div className="flex items-center gap-3 text-[12px] text-[#6B7280]">
                    <span className="font-semibold text-[#1A1A1A]">{video.channel_name}</span>
                    <span>·</span>
                    <span>{fmtNum(video.subscriber_count)} subs</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 font-medium">{video.channel_tier_label}</span>
                    <span>·</span>
                    <span>{new Date(video.published_at).toLocaleDateString()}</span>
                    <span>·</span>
                    <span>{fmtDuration(video.duration_seconds)}</span>
                  </div>
                </div>
                <button
                  onClick={handleSaveToggle}
                  disabled={saving}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-[13px] font-semibold transition-all shrink-0 ${
                    isSaved
                      ? 'bg-[#C9A962] text-white hover:bg-[#D4BA7A]'
                      : 'bg-[#FAFAFA] border border-[#F0F0F0] text-[#1A1A1A] hover:bg-gray-100'
                  }`}
                >
                  {isSaved ? <BookmarkCheck size={14} /> : <BookmarkPlus size={14} />}
                  {isSaved ? 'Saved' : 'Save'}
                </button>
              </div>
            </div>
          </div>

          {/* Title Analysis */}
          <Section icon={Zap} title="Title Analysis" accent="text-[#C9A962]">
            <div className="mb-4">
              <StrengthMeter score={ta.strength?.score || 0} max={ta.strength?.max || 8} label={ta.strength?.label || 'unknown'} />
            </div>

            <div className="grid grid-cols-3 gap-3 mb-4">
              {[
                { label: 'Characters', value: ta.char_count, note: ta.char_count > 70 ? 'May truncate' : ta.char_count < 40 ? 'Short' : 'Good' },
                { label: 'Words', value: ta.word_count },
                { label: 'Format', value: ta.format === 'question' ? 'Question' : 'Statement' },
              ].map(({ label, value, note }) => (
                <div key={label} className="bg-white rounded-xl p-3 border border-[#F0F0F0]">
                  <p className="text-[10px] text-[#6B7280] uppercase tracking-wide mb-0.5">{label}</p>
                  <p className="text-[14px] font-bold text-[#1A1A1A]">{value}</p>
                  {note && <p className="text-[10px] text-[#6B7280]">{note}</p>}
                </div>
              ))}
            </div>

            {ta.strength?.notes?.length > 0 && (
              <div className="bg-white rounded-xl p-3 border border-[#F0F0F0] mb-3">
                <p className="text-[10px] text-[#6B7280] uppercase tracking-wide mb-1.5">Title Strengths</p>
                <div className="flex flex-wrap gap-1.5">
                  {ta.strength.notes.map((note, i) => (
                    <span key={i} className="text-[11px] bg-green-50 text-green-700 px-2 py-0.5 rounded-lg">{note}</span>
                  ))}
                </div>
              </div>
            )}

            {ta.detected_patterns?.length > 0 && (
              <div className="mb-3">
                <p className="text-[10px] text-[#6B7280] uppercase tracking-wide mb-1.5">Detected Formula</p>
                <div className="flex gap-1.5">
                  {ta.detected_patterns.map(p => (
                    <span key={p.id} className="text-[11px] bg-blue-50 text-blue-700 px-2.5 py-1 rounded-lg font-medium">{p.label}</span>
                  ))}
                </div>
              </div>
            )}

            <div className="flex flex-wrap gap-4">
              {ta.power_words?.length > 0 && (
                <div>
                  <p className="text-[10px] text-[#6B7280] uppercase tracking-wide mb-1">Power Words</p>
                  <div className="flex flex-wrap gap-1">
                    {ta.power_words.map(w => (
                      <span key={w} className="text-[11px] bg-red-50 text-[#D42B2B] font-semibold px-2 py-0.5 rounded-lg">{w}</span>
                    ))}
                  </div>
                </div>
              )}
              {ta.emotional_triggers?.length > 0 && (
                <div>
                  <p className="text-[10px] text-[#6B7280] uppercase tracking-wide mb-1">Emotional Triggers</p>
                  <div className="flex flex-wrap gap-1">
                    {ta.emotional_triggers.map(w => (
                      <span key={w} className="text-[11px] bg-amber-50 text-amber-700 font-semibold px-2 py-0.5 rounded-lg">{w}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="grid grid-cols-4 gap-2 mt-3 text-[11px]">
              {[
                ['Number', ta.has_number ? `Yes (${ta.numbers?.join(', ')})` : 'No'],
                ['Structure', ta.structure],
                ['Parenthetical', ta.has_parenthetical ? 'Yes' : 'No'],
                ['Starts w/ #', ta.starts_with_number ? 'Yes' : 'No'],
              ].map(([l, v]) => (
                <div key={l} className="text-center bg-white rounded-lg p-2 border border-[#F0F0F0]">
                  <p className="text-[#6B7280] text-[9px] uppercase">{l}</p>
                  <p className="text-[#1A1A1A] font-medium">{v}</p>
                </div>
              ))}
            </div>
          </Section>

          {/* Description */}
          <Section icon={FileText} title="Description" accent="text-blue-500">
            {description ? (
              <>
                <div className="flex gap-2 mb-3 flex-wrap">
                  {da.has_timestamps && <span className="text-[10px] bg-blue-50 text-blue-600 px-2 py-0.5 rounded-lg font-medium">Has timestamps ({da.timestamp_count})</span>}
                  {da.has_links && <span className="text-[10px] bg-purple-50 text-purple-600 px-2 py-0.5 rounded-lg font-medium">{da.link_count} links</span>}
                  {da.has_cta && <span className="text-[10px] bg-green-50 text-green-600 px-2 py-0.5 rounded-lg font-medium">Has CTAs</span>}
                  <span className="text-[10px] bg-gray-50 text-[#6B7280] px-2 py-0.5 rounded-lg">{da.word_count} words / {da.line_count} lines</span>
                </div>
                {da.first_line && (
                  <div className="bg-white border border-[#F0F0F0] rounded-xl p-3 mb-3">
                    <p className="text-[10px] text-[#6B7280] uppercase tracking-wide mb-1">First Line (the hook)</p>
                    <p className="text-[13px] text-[#1A1A1A] font-medium">{da.first_line}</p>
                  </div>
                )}
                <p className="text-[12px] text-[#1A1A1A] whitespace-pre-wrap leading-relaxed">
                  {showFullDesc ? description : description.slice(0, 500)}
                  {!showFullDesc && description.length > 500 && '...'}
                </p>
                {description.length > 500 && (
                  <button onClick={() => setShowFullDesc(!showFullDesc)} className="mt-2 flex items-center gap-1 text-[11px] text-[#D42B2B] font-medium hover:underline">
                    {showFullDesc ? <><ChevronUp size={11} /> Less</> : <><ChevronDown size={11} /> Full description</>}
                  </button>
                )}
              </>
            ) : <p className="text-[12px] text-[#6B7280]">No description.</p>}
          </Section>

          {/* Tags */}
          {video.tags?.length > 0 && (
            <Section icon={Hash} title={`Tags (${video.tags.length})`} accent="text-purple-500" defaultOpen={false}>
              <div className="flex flex-wrap gap-1.5">
                {video.tags.map(tag => (
                  <span key={tag} className="text-[11px] bg-white border border-[#F0F0F0] text-[#6B7280] px-2 py-0.5 rounded-lg">{tag}</span>
                ))}
              </div>
            </Section>
          )}

          {/* Transcript */}
          <Section icon={Sparkles} title="Transcript" accent="text-[#D42B2B]">
            {transcriptLoading ? (
              <div className="flex items-center gap-2 text-[12px] text-[#6B7280]">
                <div className="w-4 h-4 border-2 border-[#D42B2B] border-t-transparent rounded-full animate-spin" />
                Fetching transcript...
              </div>
            ) : transcript?.available ? (
              <>
                {/* Hook */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-[#D42B2B]">Hook (first 60s)</p>
                    <span className="text-[10px] text-[#6B7280]">{transcript.word_count?.toLocaleString()} words total · ~{transcript.estimated_read_time_min}min read</span>
                  </div>
                  <div className="bg-red-50/50 border border-red-100 rounded-xl p-4">
                    <p className="text-[13px] text-[#1A1A1A] leading-relaxed italic">"{transcript.hook_text}"</p>
                  </div>
                </div>

                {/* Opening (30s) */}
                {transcript.opening_text && transcript.opening_text !== transcript.hook_text && (
                  <div className="mb-4">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-orange-600 mb-1.5">Critical Opening (first 30s)</p>
                    <p className="text-[12px] text-[#1A1A1A] bg-orange-50/50 border border-orange-100 rounded-xl p-3 italic leading-relaxed">
                      "{transcript.opening_text}"
                    </p>
                  </div>
                )}

                {/* Retention markers */}
                {transcript.retention_markers?.length > 0 && (
                  <div className="mb-4">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-[#C9A962] mb-1.5">Retention Hooks ({transcript.retention_markers.length})</p>
                    <div className="space-y-1">
                      {transcript.retention_markers.slice(0, 10).map((m, i) => (
                        <div key={i} className="flex items-center gap-2 text-[11px]">
                          <span className="text-[#C9A962] font-mono shrink-0 w-10">{m.timestamp}</span>
                          <span className="text-[#6B7280] bg-amber-50 px-1.5 py-0.5 rounded text-[10px] shrink-0">{m.phrase}</span>
                          <span className="text-[#1A1A1A] truncate">{m.text}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Topic words */}
                {transcript.topic_words?.length > 0 && (
                  <div className="mb-4">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-[#6B7280] mb-1.5">Key Topics</p>
                    <div className="flex flex-wrap gap-1">
                      {transcript.topic_words.slice(0, 15).map(({ word, count }) => (
                        <span key={word} className="text-[10px] bg-white border border-[#F0F0F0] text-[#1A1A1A] px-2 py-0.5 rounded-lg">
                          {word} <span className="text-[#6B7280]">({count})</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Full transcript toggle */}
                <button onClick={() => setShowFullTranscript(!showFullTranscript)} className="flex items-center gap-1 text-[11px] text-[#D42B2B] font-medium hover:underline">
                  {showFullTranscript ? <><ChevronUp size={11} /> Hide</> : <><ChevronDown size={11} /> Full transcript</>}
                </button>
                {showFullTranscript && (
                  <div className="mt-3 max-h-96 overflow-y-auto text-[12px] text-[#1A1A1A] leading-relaxed whitespace-pre-wrap bg-white border border-[#F0F0F0] rounded-xl p-4">
                    {transcript.full_text}
                  </div>
                )}
              </>
            ) : (
              <p className="text-[12px] text-[#6B7280]">{transcript?.error || 'Transcript not available.'}</p>
            )}
          </Section>

          {/* Notes */}
          <Section icon={Lightbulb} title="Your Notes" accent="text-[#C9A962]">
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="What can you learn from this video? Hook structure, title formula, content angle, CTA placement..."
              className="w-full h-28 text-[13px] text-[#1A1A1A] placeholder-gray-300 border border-[#F0F0F0] rounded-xl p-3 resize-none focus:outline-none focus:ring-2 focus:ring-[#D42B2B] focus:border-transparent bg-white"
            />
            <div className="flex items-center justify-between mt-2">
              <span className="text-[11px] text-green-600 h-4">{notesSaved ? 'Saved!' : ''}</span>
              <button onClick={handleSaveNotes} className="text-[11px] font-semibold bg-[#1A1A1A] text-white px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors">
                Save Notes
              </button>
            </div>
          </Section>
        </div>

        {/* Sidebar — 4 cols */}
        <div className="col-span-4 space-y-5">

          {/* Outlier Score */}
          <div className="rounded-2xl border-2 p-6 text-center" style={{ borderColor: score >= 5 ? 'var(--color-red)' : score >= 3 ? 'var(--color-gold)' : '#e5e7eb' }}>
            <p className="text-[10px] text-[#6B7280] uppercase tracking-widest mb-2">Outlier Score</p>
            <p className="text-5xl font-black leading-none" style={{ color: score >= 5 ? 'var(--color-red)' : score >= 3 ? 'var(--color-gold)' : 'var(--color-ink)' }}>
              {score.toFixed(1)}
            </p>
            {video.is_breakout && <p className="text-[11px] font-bold text-[#D42B2B] mt-2">BREAKOUT VIDEO</p>}
          </div>

          {/* Stats cards */}
          <div className="grid grid-cols-2 gap-3">
            {[
              { icon: Eye, label: 'Views', value: fmtNum(video.view_count) },
              { icon: ThumbsUp, label: 'Likes', value: fmtNum(video.like_count) },
              { icon: MessageSquare, label: 'Comments', value: fmtNum(video.comment_count) },
              { icon: Users, label: 'Subs', value: fmtNum(video.subscriber_count) },
            ].map(({ icon: Icon, label, value }) => (
              <div key={label} className="bg-[#FAFAFA] rounded-xl border border-[#F0F0F0] p-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <Icon size={12} className="text-[#6B7280]" />
                  <span className="text-[10px] text-[#6B7280] uppercase tracking-wide">{label}</span>
                </div>
                <p className="font-bold text-xl text-[#1A1A1A]">{value}</p>
              </div>
            ))}
          </div>

          {/* Performance Ratios */}
          <div className="bg-[#FAFAFA] rounded-2xl border border-[#F0F0F0] p-5">
            <h3 className="font-bold text-[13px] text-[#1A1A1A] mb-3 flex items-center gap-1.5">
              <BarChart2 size={13} className="text-[#C9A962]" /> Ratios
            </h3>
            <MetricRow label="Engagement rate" value={`${metrics.engagement_rate}%`} />
            <MetricRow label="Like rate" value={`${metrics.like_to_view_pct}%`} />
            <MetricRow label="Comment rate" value={`${metrics.comment_to_view_pct}%`} />
            <MetricRow
              label="Views vs channel avg"
              value={`${metrics.vs_channel_avg_multiplier}x`}
              highlight={metrics.vs_channel_avg_multiplier >= 3}
            />
            <MetricRow
              label="Views / subs"
              value={`${metrics.view_to_sub_ratio}x`}
              highlight={metrics.view_to_sub_ratio >= 3}
            />
            <MetricRow label="Views per day" value={fmtNum(metrics.views_per_day)} />
            <MetricRow label="Days since upload" value={`${metrics.days_since_upload}d`} />
          </div>

          {/* Channel context */}
          {video.last_video_titles?.length > 0 && (
            <div className="bg-[#FAFAFA] rounded-2xl border border-[#F0F0F0] p-5">
              <h3 className="font-bold text-[13px] text-[#1A1A1A] mb-1 flex items-center gap-1.5">
                <Target size={13} className="text-[#6B7280]" /> Channel Context
              </h3>
              <p className="text-[11px] text-[#6B7280] mb-3">Recent videos by {video.channel_name}</p>

              <div className="space-y-2">
                {video.last_video_titles.map((v, i) => {
                  const isOutlier = video.avg_views && v.view_count > video.avg_views * 2
                  return (
                    <div key={i} className="flex items-start justify-between gap-2">
                      <p className={`text-[11px] leading-snug flex-1 line-clamp-2 ${isOutlier ? 'text-[#1A1A1A] font-medium' : 'text-[#6B7280]'}`}>{v.title}</p>
                      <span className={`text-[10px] shrink-0 font-mono ${isOutlier ? 'text-[#D42B2B] font-bold' : 'text-[#6B7280]'}`}>{fmtNum(v.view_count)}</span>
                    </div>
                  )
                })}
              </div>

              {video.avg_views > 0 && (
                <div className="mt-3 pt-3 border-t border-[#F0F0F0] flex justify-between text-[11px]">
                  <span className="text-[#6B7280]">Channel avg</span>
                  <span className="font-bold text-[#1A1A1A]">{fmtNum(Math.round(video.avg_views))} views</span>
                </div>
              )}
            </div>
          )}

          {/* Keywords matched */}
          {video.keywords_matched?.length > 0 && (
            <div className="bg-[#FAFAFA] rounded-2xl border border-[#F0F0F0] p-5">
              <h3 className="font-bold text-[13px] text-[#1A1A1A] mb-3">Matched Keywords</h3>
              <div className="flex flex-wrap gap-1.5">
                {video.keywords_matched.map(kw => (
                  <span key={kw} className="text-[11px] bg-white border border-[#F0F0F0] text-[#1A1A1A] px-2 py-0.5 rounded-lg">{kw}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
