import { motion } from 'framer-motion'
import type { Urgency } from '../types/triage'

const urgencyStyles: Record<Urgency, { bg: string; text: string; ring: string }> = {
  Emergency: {
    bg: 'bg-critical-subtle',
    text: 'text-critical',
    ring: 'ring-critical/25',
  },
  Urgent: {
    bg: 'bg-warning-subtle',
    text: 'text-warning',
    ring: 'ring-warning/25',
  },
  Routine: {
    bg: 'bg-safe-subtle',
    text: 'text-safe',
    ring: 'ring-safe/25',
  },
  'Self-Care': {
    bg: 'bg-neutral-subtle',
    text: 'text-neutral',
    ring: 'ring-neutral/25',
  },
}

interface UrgencyBadgeProps {
  urgency: Urgency
}

export function UrgencyBadge({ urgency }: UrgencyBadgeProps) {
  const s = urgencyStyles[urgency]
  return (
    <motion.span
      layout
      className={`inline-block rounded-lg px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${s.bg} ${s.text} ${s.ring}`}
      whileHover={{ scale: 1.04 }}
    >
      {urgency}
    </motion.span>
  )
}
