const stages = ['React UI', 'FastAPI Gateway', 'Security Filter', 'Router']

interface GatewayPathProps {
  activeStage?: number
}

export function GatewayPath({ activeStage }: GatewayPathProps) {
  return (
    <section
      className="rounded-lg border border-clinical-line bg-white p-5 shadow-panel"
      aria-label="Request gateway path"
    >
      <h2 className="text-lg font-semibold text-clinical-ink">Gateway Path</h2>
      <div className="mt-5 grid gap-3" aria-hidden="true">
        {stages.map((stage, index) => {
          const isActive = activeStage !== undefined && index < activeStage
          const isCurrent = activeStage !== undefined && index === activeStage
          return (
            <div key={stage} className="flex items-center gap-3">
              <span
                className={`grid size-8 shrink-0 place-items-center rounded-md text-sm font-semibold text-white ${
                  isCurrent
                    ? 'bg-clinical-teal ring-2 ring-clinical-teal ring-offset-1'
                    : isActive
                      ? 'bg-clinical-teal'
                      : 'bg-zinc-400'
                }`}
              >
                {index + 1}
              </span>
              <span className="text-sm font-medium text-clinical-ink">{stage}</span>
            </div>
          )
        })}
      </div>
      {/* Screen-reader accessible description */}
      <p className="sr-only">
        Requests flow through {stages.length} stages:{' '}
        {stages.join(', then ')}.
      </p>
    </section>
  )
}
