import { motion, AnimatePresence } from 'framer-motion'
import type { TriageResponse } from '../types/triage'
import { UrgencyBadge } from './UrgencyBadge'
import { SkeletonCard } from './SkeletonCard'

interface ResponsePreviewProps {
  response: TriageResponse | null
  loading: boolean
}

const cardVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.3, ease: 'easeOut' as const },
  }),
}

const loadingStages = [
  { label: 'Reviewing chief complaint…', colSpan: '' as string },
  { label: 'Assessing vitals…', colSpan: 'lg:col-span-2' as string },
  { label: 'Cross-referencing guidelines…', colSpan: '' as string },
  { label: 'Generating triage card…', colSpan: 'lg:col-span-2' as string },
]

const loadingCardVariants = {
  hidden: { opacity: 0, y: 6 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.35, duration: 0.35, ease: 'easeOut' as const },
  }),
}

function LoadingSequence() {
  return (
    <AnimatePresence>
      <motion.div key="loading-sequence" className="contents">
        {loadingStages.map((stage, i) => (
          <motion.div
            key={stage.label}
            custom={i}
            variants={loadingCardVariants}
            initial="hidden"
            animate="visible"
            className={stage.colSpan || undefined}
          >
            <SkeletonCard label={stage.label} />
          </motion.div>
        ))}
      </motion.div>
    </AnimatePresence>
  )
}

export function ResponsePreview({ response, loading }: ResponsePreviewProps) {
  const showSkeletons = !response

  return (
    <section
      className="glass relative overflow-hidden rounded-3xl p-8 shadow-card border-t-2 border-t-accent"
      aria-live="polite"
      aria-busy={loading || undefined}
    >
      {/* Progress bar — only visible during loading */}
      {loading && (
        <div className="absolute inset-x-0 top-0 h-0.5 bg-accent/15" aria-hidden="true">
          <motion.div
            className="h-full bg-gradient-to-r from-accent to-accent-hover"
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 5, ease: 'easeOut' }}
            style={{ transformOrigin: 'left' }}
          />
        </div>
      )}

      {/* Breathing pulse dot next to heading during loading */}
      <div className="mb-10">
        <h2 className="text-3xl font-bold tracking-tight text-ink font-display flex items-center gap-3">
          {loading ? 'Processing Triage' : 'Triage Assessment'}
          {loading && (
            <span className="relative flex size-2.5" aria-label="Processing">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-accent/40" />
              <span className="relative inline-flex size-2.5 rounded-full bg-accent" />
            </span>
          )}
        </h2>
        <p className="mt-2 text-sm text-muted font-sans">
          {loading
            ? 'AI is analyzing your submission. This may take a few seconds.'
            : 'AI-generated analysis based on submitted symptoms and context.'}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <AnimatePresence mode="wait">
          {showSkeletons ? (
            loading ? (
              <LoadingSequence key="loading-sequence" />
            ) : (
              <motion.div
                key="skeletons"
                className="contents"
                exit={{ opacity: 0, transition: { duration: 0.12 } }}
              >
                <SkeletonCard label="Urgency" />
                <SkeletonCard label="Rationale" className="lg:col-span-2" />
                <SkeletonCard label="Sources" />
                <SkeletonCard label="Disclaimer" className="lg:col-span-2" />
              </motion.div>
            )
          ) : (
            <motion.div key="content" className="contents">
              {/* Urgency */}
              <motion.div
                className="glass rounded-2xl p-5 shadow-sm border-l-[3px] border-l-critical"
                custom={0}
                variants={cardVariants}
                initial="hidden"
                animate="visible"
              >
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted font-display">
                  ATS Category
                </p>
                <div className="mt-3">
                  <UrgencyBadge
                    category={response!.triage_result.ats_category}
                    card={response!.triage_result.ats_card}
                  />
                </div>
              </motion.div>

              {/* Rationale */}
              <motion.div
                className="glass rounded-2xl p-5 shadow-sm lg:col-span-2"
                custom={1}
                variants={cardVariants}
                initial="hidden"
                animate="visible"
              >
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted font-display">
                  Rationale
                </p>
                <p className="mt-3 text-base leading-relaxed text-ink font-sans">
                  {response!.triage_result.rationale}
                </p>
              </motion.div>

              {/* Sources */}
              <motion.div
                className="glass rounded-2xl p-5 shadow-sm"
                custom={2}
                variants={cardVariants}
                initial="hidden"
                animate="visible"
              >
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted font-display">
                  Sources
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {response!.triage_result.sources.map((s, i) => (
                    <span
                      key={i}
                      className="inline-block rounded-full bg-accent-subtle px-2.5 py-0.5 text-xs font-medium text-accent font-mono break-all"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </motion.div>

              {/* Disclaimer */}
              <motion.div
                className="glass rounded-2xl p-5 shadow-sm lg:col-span-2"
                custom={3}
                variants={cardVariants}
                initial="hidden"
                animate="visible"
              >
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted font-display">
                  Disclaimer
                </p>
                <p className="mt-3 text-xs leading-relaxed text-muted/80 italic font-sans">
                  {response!.triage_result.disclaimer}
                </p>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  )
}
