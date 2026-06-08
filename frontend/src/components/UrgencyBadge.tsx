import { motion } from 'framer-motion'
import type { ATSCategory, ATSCard } from '../types/triage'

const atsStyles: Record<ATSCategory, { bg: string; text: string; ring: string; border: string; dot: string }> = {
  'ATS-1': {
    bg: 'bg-red-50',
    text: 'text-red-700',
    ring: 'ring-red-200',
    border: 'border-l-red-600',
    dot: 'bg-red-600',
  },
  'ATS-2': {
    bg: 'bg-orange-50',
    text: 'text-orange-700',
    ring: 'ring-orange-200',
    border: 'border-l-orange-500',
    dot: 'bg-orange-500',
  },
  'ATS-3': {
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    ring: 'ring-amber-200',
    border: 'border-l-amber-500',
    dot: 'bg-amber-500',
  },
  'ATS-4': {
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    ring: 'ring-emerald-200',
    border: 'border-l-emerald-500',
    dot: 'bg-emerald-500',
  },
  'ATS-5': {
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    ring: 'ring-blue-200',
    border: 'border-l-blue-500',
    dot: 'bg-blue-500',
  },
}

interface ATSBadgeProps {
  category: ATSCategory
  card?: ATSCard
}

export function UrgencyBadge({ category, card }: ATSBadgeProps) {
  const s = atsStyles[category]
  const label = card?.label ?? category
  const time = card?.time_target_min
  const timeText = time !== undefined
    ? time === 0 ? 'Immediate' : `${time} min`
    : undefined

  return (
    <motion.span
      layout
      className={`inline-flex items-center gap-2 rounded-xl border-l-[3px] px-3 py-1.5 text-xs font-semibold ring-1 ring-inset font-sans ${s.bg} ${s.text} ${s.ring} ${s.border}`}
      whileHover={{ scale: 1.04 }}
    >
      <span className={`size-1.5 rounded-full ${s.dot} ${category === 'ATS-1' ? 'animate-ping' : ''}`} />
      <span>{category}</span>
      <span className="text-muted/60">·</span>
      <span>{label}</span>
      {timeText && (
        <>
          <span className="text-muted/60">·</span>
          <span className={category === 'ATS-1' ? 'font-bold' : ''}>{timeText}</span>
        </>
      )}
    </motion.span>
  )
}
