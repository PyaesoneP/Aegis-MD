interface SkeletonCardProps {
  label: string
  lines?: number
  className?: string
}

export function SkeletonCard({ label, lines = 2, className = '' }: SkeletonCardProps) {
  return (
    <div className={`glass rounded-2xl p-5 ${className}`}>
      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted font-display">
        {label}
      </p>
      <div className="mt-3 space-y-2" aria-hidden="true">
        {Array.from({ length: lines }).map((_, i) => (
          <span
            key={i}
            className="block h-2 rounded-full bg-gradient-to-r from-border/50 via-surface to-border/50 bg-[length:200%_100%] animate-shimmer"
            style={{ width: i === lines - 1 ? '60%' : '100%' }}
          />
        ))}
      </div>
    </div>
  )
}
