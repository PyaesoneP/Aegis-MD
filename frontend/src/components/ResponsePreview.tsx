import { motion, AnimatePresence } from 'framer-motion'
import type { TriageResponse } from '../types/triage'
import { UrgencyBadge } from './UrgencyBadge'

interface ResponsePreviewProps {
  response: TriageResponse | null
  loading: boolean
}

const cardVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.06, duration: 0.25, ease: 'easeOut' as const },
  }),
}

function SkeletonCard({ label }: { label: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">{label}</p>
      <div className="mt-3 space-y-2" aria-hidden="true">
        <span className="block h-2 animate-pulse rounded-full bg-border motion-safe:animate-pulse" />
        <span className="block h-2 w-2/3 animate-pulse rounded-full bg-border motion-safe:animate-pulse" />
      </div>
    </div>
  )
}

export function ResponsePreview({ response, loading }: ResponsePreviewProps) {
  const showSkeletons = !response

  return (
    <section
      className="rounded-2xl border border-border bg-gradient-to-b from-surface to-canvas p-6 shadow-card"
      aria-live="polite"
      aria-busy={loading || undefined}
    >
      <div className="mb-6">
        <h2 className="text-lg font-semibold tracking-tight text-ink">Response</h2>
        <p className="mt-1 text-sm text-muted">AI-generated triage assessment.</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <AnimatePresence mode="wait">
          {showSkeletons ? (
            <motion.div
              key="skeletons"
              className="contents"
              exit={{ opacity: 0, transition: { duration: 0.12 } }}
            >
              <SkeletonCard label="Urgency" />
              <SkeletonCard label="Rationale" />
              <SkeletonCard label="Sources" />
              <SkeletonCard label="Disclaimer" />
            </motion.div>
          ) : (
            <motion.div key="content" className="contents">
              <motion.div
                className="rounded-xl border border-border bg-gradient-to-b from-surface to-canvas p-4 shadow-sm"
                custom={0}
                variants={cardVariants}
                initial="hidden"
                animate="visible"
              >
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">Urgency</p>
                <div className="mt-3">
                  <UrgencyBadge urgency={response!.triage_result.urgency} />
                </div>
              </motion.div>
              <motion.div
                className="rounded-xl border border-border bg-gradient-to-b from-surface to-canvas p-4 shadow-sm"
                custom={1}
                variants={cardVariants}
                initial="hidden"
                animate="visible"
              >
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">Rationale</p>
                <p className="mt-3 text-sm leading-relaxed text-ink">{response!.triage_result.rationale}</p>
              </motion.div>
              <motion.div
                className="rounded-xl border border-border bg-gradient-to-b from-surface to-canvas p-4 shadow-sm"
                custom={2}
                variants={cardVariants}
                initial="hidden"
                animate="visible"
              >
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">Sources</p>
                <ul className="mt-3 list-disc pl-4 text-sm text-ink space-y-1 break-words">
                  {response!.triage_result.sources.map((s, i) => (
                    <li key={i} className="break-all">{s}</li>
                  ))}
                </ul>
              </motion.div>
              <motion.div
                className="rounded-xl border border-border bg-gradient-to-b from-surface to-canvas p-4 shadow-sm"
                custom={3}
                variants={cardVariants}
                initial="hidden"
                animate="visible"
              >
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">Disclaimer</p>
                <p className="mt-3 text-xs leading-relaxed text-muted">{response!.triage_result.disclaimer}</p>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  )
}
