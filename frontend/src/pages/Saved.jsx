import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getSaved, unsaveVideo, updateNotes, getExportUrl } from '../api/client'
import { Link } from 'react-router-dom'
import { Bookmark, Trash2, ExternalLink, Edit2, Check, Download, TrendingUp, Copy } from 'lucide-react'
import { useState } from 'react'

function fmtNum(n) {
  if (!n) return '0'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n?.toString() || '0'
}

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = (Date.now() - new Date(dateStr).getTime()) / 1000
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
  return new Date(dateStr).toLocaleDateString()
}

function ScoreBadge({ score }) {
  if (!score || score <= 0) return null
  const bg = score >= 5 ? 'var(--color-red)' : 'var(--color-gold)'
  return <span className="text-[10px] font-bold px-2 py-0.5 rounded-md text-white" style={{ backgroundColor: bg }}>{score.toFixed(1)}</span>
}

function SavedRow({ item, onRemove }) {
  const [editing, setEditing] = useState(false)
  const [notes, setNotes] = useState(item.notes || '')
  const [justSaved, setJustSaved] = useState(false)

  async function handleSave() {
    await updateNotes(item.video_id, notes)
    setJustSaved(true)
    setEditing(false)
    setTimeout(() => setJustSaved(false), 2000)
  }

  return (
    <div className="bg-white border border-[#F0F0F0] rounded-2xl overflow-hidden hover:border-gray-200 hover:shadow-sm transition-all group">
      <div className="flex gap-4 p-4">
        <Link to={`/video/${item.video_id}`} className="shrink-0">
          {item.thumbnail_url ? (
            <img src={item.thumbnail_url} alt="" className="w-44 aspect-video object-cover rounded-xl" />
          ) : (
            <div className="w-44 aspect-video bg-gray-50 rounded-xl flex items-center justify-center">
              <Bookmark size={18} className="text-gray-300" />
            </div>
          )}
        </Link>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3 mb-1.5">
            <Link to={`/video/${item.video_id}`}>
              <h3 className="font-semibold text-[13px] text-[#1A1A1A] leading-snug hover:text-[#D42B2B] transition-colors line-clamp-2">
                {item.title || item.video_id}
              </h3>
            </Link>
            <div className="flex items-center gap-1.5 shrink-0">
              <ScoreBadge score={item.outlier_score} />
              <a href={`https://www.youtube.com/watch?v=${item.video_id}`} target="_blank" rel="noreferrer" className="p-1 rounded-md hover:bg-gray-100 text-[#6B7280] transition-colors">
                <ExternalLink size={12} />
              </a>
              <button onClick={() => onRemove(item.video_id)} className="p-1 rounded-md hover:bg-red-50 text-gray-300 hover:text-[#D42B2B] transition-colors opacity-0 group-hover:opacity-100" title="Remove">
                <Trash2 size={12} />
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2 text-[11px] text-[#6B7280] mb-2">
            <span className="font-medium text-[#1A1A1A]">{item.channel_name}</span>
            <span>·</span>
            <span>{fmtNum(item.view_count)} views</span>
            {item.subscriber_count > 0 && <><span>·</span><span>{fmtNum(item.subscriber_count)} subs</span></>}
            <span>·</span>
            <span>Saved {timeAgo(item.saved_at)}</span>
          </div>

          {editing ? (
            <div>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                className="w-full text-[12px] border border-[#F0F0F0] rounded-xl p-2.5 resize-none h-16 focus:outline-none focus:ring-2 focus:ring-[#D42B2B] bg-[#FAFAFA]"
                placeholder="Hook structure, title formula, content angle..."
                autoFocus
              />
              <div className="flex items-center gap-2 mt-1.5">
                <button onClick={handleSave} className="flex items-center gap-1 text-[11px] bg-[#1A1A1A] text-white px-2.5 py-1 rounded-lg hover:bg-gray-800 transition-colors">
                  <Check size={10} /> Save
                </button>
                <button onClick={() => setEditing(false)} className="text-[11px] text-[#6B7280] hover:text-[#1A1A1A]">Cancel</button>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-2">
              {notes ? (
                <p className="text-[11px] text-[#6B7280] italic flex-1 line-clamp-2">"{notes}"</p>
              ) : (
                <p className="text-[11px] text-gray-300 italic flex-1">No notes</p>
              )}
              <button onClick={() => setEditing(true)} className="shrink-0 p-1 rounded hover:bg-gray-100 text-gray-300 hover:text-[#6B7280] transition-colors">
                <Edit2 size={10} />
              </button>
            </div>
          )}
          {justSaved && <p className="text-[10px] text-green-600 mt-1">Notes saved!</p>}
        </div>
      </div>
    </div>
  )
}

export default function Saved() {
  const qc = useQueryClient()
  const { data: saved = [], isLoading } = useQuery({ queryKey: ['saved'], queryFn: getSaved })

  async function handleRemove(videoId) {
    await unsaveVideo(videoId)
    qc.invalidateQueries({ queryKey: ['saved'] })
  }

  function handleCopyAll() {
    const text = saved.map(s => `${s.title}\nhttps://youtube.com/watch?v=${s.video_id}\n${s.notes ? `Notes: ${s.notes}` : ''}`).join('\n\n---\n\n')
    navigator.clipboard.writeText(text)
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="flex items-end justify-between mb-8">
        <div>
          <h1 className="text-2xl font-black text-[#1A1A1A] mb-1">Saved Videos</h1>
          <p className="text-[#6B7280] text-[13px]">{saved.length} video{saved.length !== 1 ? 's' : ''} in your collection</p>
        </div>
        {saved.length > 0 && (
          <div className="flex items-center gap-2">
            <button onClick={handleCopyAll} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[12px] font-medium text-[#6B7280] hover:bg-[#FAFAFA] transition-colors" title="Copy all to clipboard">
              <Copy size={12} /> Copy All
            </button>
            <a href={getExportUrl(false)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[12px] font-medium bg-[#1A1A1A] text-white hover:bg-gray-800 transition-colors">
              <Download size={12} /> Export CSV
            </a>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <div className="w-6 h-6 border-2 border-[#D42B2B] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : saved.length === 0 ? (
        <div className="text-center py-20 text-[#6B7280]">
          <div className="w-14 h-14 bg-[#FAFAFA] rounded-3xl flex items-center justify-center mx-auto mb-5">
            <Bookmark size={24} className="text-gray-300" />
          </div>
          <p className="text-[13px] font-medium text-[#1A1A1A] mb-1">No saved videos yet</p>
          <p className="text-[12px] mb-5">Click the bookmark icon on any video to start building your collection.</p>
          <Link to="/" className="inline-flex items-center gap-1.5 text-[13px] text-[#D42B2B] font-semibold hover:underline">
            <TrendingUp size={13} /> Browse Dashboard
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {saved.map(item => (
            <SavedRow key={item.video_id} item={item} onRemove={handleRemove} />
          ))}
        </div>
      )}
    </div>
  )
}
