import { motion } from 'framer-motion'
import type { Urgency } from '../types/triage'

const urgencyStyles: Record<Urgency, { bg: string; text: string; ring: string; border: string }> = {
  Emergency: {
    bg: 'bg-critical-subtle',
    text: 'text-critical',
    ring: 'ring-critical/25',
    border: 'border-l-critical',
  },
  Urgent: {
    bg: 'bg-warning-subtle',
    text: 'text-warning',
    ring: 'ring-warning/25',
    border: 'border-l-warning',
  },
  Routine: {
    bg: 'bg-safe-subtle',
    text: 'text-safe',
    ring: 'ring-safe/25',
    border: 'border-l-safe',
  },
  'Self-Care': {
    bg: 'bg-neutral-subtle',
    text: 'text-neutral',
    ring: 'ring-neutral/25',
    border: 'border-l-neutral',
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
      className={`inline-block rounded-xl border-l-[3px] px-3 py-1.5 text-xs font-semibold ring-1 ring-inset font-sans ${s.bg} ${s.text} ${s.ring} ${s.border}`}
      whileHover={{ scale: 1.04 }}
    >
      {urgency}
    </motion.span>
  )
}
