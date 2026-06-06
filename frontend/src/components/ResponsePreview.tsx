import type { TriageResponse } from '../types/triage'
import { UrgencyBadge } from './UrgencyBadge'

interface ResponsePreviewProps {
  response: TriageResponse | null
  loading: boolean
}

function SkeletonCard({ label }: { label: string }) {
  return (
    <div className="min-h-28 rounded-lg border border-clinical-line bg-zinc-50 p-4">
      <p className="text-sm font-medium text-clinical-ink">{label}</p>
      <div className="mt-4 space-y-2" aria-hidden="true">
        <span className="block h-2 animate-pulse rounded-full bg-zinc-200 motion-safe:animate-pulse" />
        <span className="block h-2 w-2/3 animate-pulse rounded-full bg-zinc-200 motion-safe:animate-pulse" />
      </div>
    </div>
  )
}

export function ResponsePreview({ response, loading }: ResponsePreviewProps) {
  return (
    <section
      className="rounded-lg border border-clinical-line bg-white p-5 shadow-panel lg:col-span-2"
      aria-live="polite"
      aria-busy={loading || undefined}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-clinical-ink">Response Preview</h2>
          <p className="mt-1 text-sm text-zinc-600">
            Structured around the documented FastAPI response.
          </p>
        </div>
        <div className="flex flex-wrap gap-2" aria-label="Urgency tier legend">
          <UrgencyBadge urgency="Emergency" />
          <UrgencyBadge urgency="Urgent" />
          <UrgencyBadge urgency="Routine" />
          <UrgencyBadge urgency="Self-Care" />
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-4">
        {response ? (
          <>
            {/* Urgency */}
            <div className="min-h-28 rounded-lg border border-clinical-line bg-zinc-50 p-4">
              <p className="text-sm font-medium text-clinical-ink">Urgency</p>
              <div className="mt-4">
                <UrgencyBadge urgency={response.triage_result.urgency} />
              </div>
            </div>
            {/* Rationale */}
            <div className="min-h-28 rounded-lg border border-clinical-line bg-zinc-50 p-4">
              <p className="text-sm font-medium text-clinical-ink">Rationale</p>
              <p className="mt-4 text-sm text-zinc-700">{response.triage_result.rationale}</p>
            </div>
            {/* Sources */}
            <div className="min-h-28 rounded-lg border border-clinical-line bg-zinc-50 p-4">
              <p className="text-sm font-medium text-clinical-ink">Sources</p>
              <ul className="mt-4 list-disc pl-5 text-sm">
                {response.triage_result.sources.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
            {/* Disclaimer */}
            <div className="min-h-28 rounded-lg border border-clinical-line bg-zinc-50 p-4">
              <p className="text-sm font-medium text-clinical-ink">Disclaimer</p>
              <p className="mt-4 text-xs text-zinc-500">{response.triage_result.disclaimer}</p>
            </div>
          </>
        ) : (
          <>
            <SkeletonCard label="Urgency tier" />
            <SkeletonCard label="Rationale" />
            <SkeletonCard label="Sources" />
            <SkeletonCard label="Disclaimer" />
          </>
        )}
      </div>
    </section>
  )
}
