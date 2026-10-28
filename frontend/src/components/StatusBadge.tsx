import type { RunStatusValue } from '../api/client'

const COLORS: Record<RunStatusValue, string> = {
  pending: '#8a8f98',
  running: '#2563eb',
  done: '#16a34a',
  failed: '#dc2626',
  cancelled: '#d97706',
}

export default function StatusBadge({ status }: { status: RunStatusValue | string }) {
  const color = COLORS[status as RunStatusValue] ?? '#8a8f98'
  return (
    <span
      className="status-badge"
      style={{ backgroundColor: `${color}1a`, color, border: `1px solid ${color}55` }}
    >
      {status}
    </span>
  )
}
