import type { Urgency } from '../types/triage'

const urgencyStyles: Record<Urgency, string> = {
  Emergency: 'bg-rose-50 text-clinical-rose ring-rose-200',
  Urgent: 'bg-amber-50 text-clinical-amber ring-amber-200',
  Routine: 'bg-emerald-50 text-clinical-teal ring-emerald-200',
  'Self-Care': 'bg-zinc-100 text-zinc-700 ring-zinc-300',
}

interface UrgencyBadgeProps {
  urgency: Urgency
}

export function UrgencyBadge({ urgency }: UrgencyBadgeProps) {
  return (
    <span
      className={`rounded-md px-3 py-1 text-xs font-semibold ring-1 ring-inset ${urgencyStyles[urgency]}`}
    >
      {urgency}
    </span>
  )
}
