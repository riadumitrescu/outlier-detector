import { useQuery } from '@tanstack/react-query'
import { getQuota } from '../api/client'

export default function QuotaBar() {
  const { data } = useQuery({
    queryKey: ['quota'],
    queryFn: getQuota,
    refetchInterval: 30000,
  })

  if (!data) return null

  const pct = Math.round((data.units_used / data.limit) * 100)
  const remaining = data.limit - data.units_used
  const color = pct > 80 ? 'var(--color-red)' : pct > 50 ? 'var(--color-gold)' : '#22c55e'

  return (
    <div className="hidden lg:flex items-center gap-2.5 text-xs text-[#6B7280]" title={`${remaining.toLocaleString()} units remaining (~${Math.floor(remaining / 100)} searches)`}>
      <span className="font-mono text-[11px]">{data.units_used.toLocaleString()}/{(data.limit / 1000).toFixed(0)}K</span>
      <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(pct, 100)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}
