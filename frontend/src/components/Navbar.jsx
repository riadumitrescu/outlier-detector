import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Bookmark, Tag, RefreshCw, Download } from 'lucide-react'
import { triggerRefresh, getRefreshStatus, getExportUrl } from '../api/client'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import QuotaBar from './QuotaBar'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/saved', label: 'Saved', icon: Bookmark },
  { to: '/keywords', label: 'Keywords', icon: Tag },
]

export default function Navbar() {
  const loc = useLocation()
  const qc = useQueryClient()
  const [refreshing, setRefreshing] = useState(false)

  const { data: status } = useQuery({
    queryKey: ['refresh-status'],
    queryFn: getRefreshStatus,
    refetchInterval: refreshing ? 1500 : 10000,
  })

  useEffect(() => {
    if (refreshing && status && !status.running) {
      setRefreshing(false)
      qc.invalidateQueries()
    }
  }, [status, refreshing, qc])

  async function handleRefresh() {
    setRefreshing(true)
    try {
      await triggerRefresh(14)
    } catch {
      setRefreshing(false)
    }
  }

  const isRunning = status?.running || refreshing
  const progressText = isRunning && status?.progress
    ? status.progress.length > 50 ? status.progress.slice(0, 50) + '...' : status.progress
    : null

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-[#F0F0F0]">
      <div className="max-w-[1400px] mx-auto px-6 flex items-center justify-between h-14">
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <div className="w-7 h-7 bg-[#D42B2B] rounded-lg flex items-center justify-center">
            <span className="text-white font-black text-xs">OD</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-[#1A1A1A] font-extrabold text-base tracking-tight">OUTLIER</span>
            <span className="text-[#6B7280] font-light text-sm">DETECTOR</span>
          </div>
        </Link>

        <nav className="flex items-center gap-0.5 bg-[#FAFAFA] rounded-xl p-1">
          {NAV.map(({ to, label, icon: Icon }) => {
            const active = to === '/' ? loc.pathname === '/' : loc.pathname.startsWith(to)
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[13px] font-medium transition-all ${
                  active ? 'bg-white text-[#1A1A1A] shadow-sm' : 'text-[#6B7280] hover:text-[#1A1A1A]'
                }`}
              >
                <Icon size={14} />
                {label}
              </Link>
            )
          })}
        </nav>

        <div className="flex items-center gap-3 shrink-0">
          <QuotaBar />
          <a
            href={getExportUrl(true)}
            className="hidden md:flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[12px] text-[#6B7280] hover:text-[#1A1A1A] hover:bg-[#FAFAFA] transition-colors"
            title="Export CSV"
          >
            <Download size={13} />
          </a>
          <button
            onClick={handleRefresh}
            disabled={isRunning}
            className="flex items-center gap-1.5 pl-3.5 pr-4 py-1.5 rounded-xl text-[13px] font-semibold bg-[#D42B2B] text-white hover:bg-[#B91C1C] disabled:opacity-60 disabled:cursor-not-allowed transition-all shadow-sm"
          >
            <RefreshCw size={13} className={isRunning ? 'animate-spin' : ''} />
            {isRunning ? 'Refreshing' : 'Refresh'}
          </button>
        </div>
      </div>
      {isRunning && progressText && (
        <div className="bg-[#FAFAFA] border-t border-[#F0F0F0] px-6 py-1.5">
          <div className="max-w-[1400px] mx-auto flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-[#C9A962] animate-pulse" />
            <span className="text-xs text-[#6B7280] font-medium">{progressText}</span>
          </div>
        </div>
      )}
    </header>
  )
}
