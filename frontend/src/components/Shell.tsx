import { API_BASE_URL } from '../lib/api'

const intakeFields = ['Symptoms', 'Patient context', 'Optional image']
const responseFields = ['Urgency tier', 'Rationale', 'Sources', 'Disclaimer']
const gatewayStages = ['React UI', 'FastAPI Gateway', 'Security Filter', 'Router']

export function Shell() {
  return (
    <main className="min-h-screen bg-clinical-paper">
      <header className="border-b border-clinical-line bg-white">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-5 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-clinical-teal">
              Aegis-MD
            </p>
            <h1 className="mt-1 text-2xl font-semibold text-clinical-ink sm:text-3xl">
              Multimodal Triage Console
            </h1>
          </div>
          <div className="rounded-lg border border-clinical-line bg-clinical-mint px-4 py-3 text-sm text-clinical-ink">
            <span className="font-semibold">API</span>
            <span className="ml-2 break-all">{API_BASE_URL}</span>
          </div>
        </div>
      </header>

      <div className="mx-auto grid w-full max-w-6xl gap-5 px-5 py-6 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-lg border border-clinical-line bg-white p-5 shadow-panel">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-clinical-ink">
                Triage Intake
              </h2>
              <p className="mt-1 text-sm text-zinc-600">
                Static scaffold for the future multipart request flow.
              </p>
            </div>
            <span className="rounded-md bg-clinical-mint px-3 py-1 text-xs font-semibold text-clinical-teal">
              Ready
            </span>
          </div>

          <div className="mt-5 grid gap-3">
            {intakeFields.map((field) => (
              <div
                key={field}
                className="flex min-h-14 items-center justify-between rounded-lg border border-clinical-line bg-zinc-50 px-4"
              >
                <span className="text-sm font-medium text-clinical-ink">
                  {field}
                </span>
                <span className="h-2 w-24 rounded-full bg-zinc-200" />
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-clinical-line bg-white p-5 shadow-panel">
          <h2 className="text-lg font-semibold text-clinical-ink">
            Gateway Path
          </h2>
          <div className="mt-5 grid gap-3">
            {gatewayStages.map((stage, index) => (
              <div key={stage} className="flex items-center gap-3">
                <span className="grid size-8 shrink-0 place-items-center rounded-md bg-clinical-teal text-sm font-semibold text-white">
                  {index + 1}
                </span>
                <span className="text-sm font-medium text-clinical-ink">
                  {stage}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-clinical-line bg-white p-5 shadow-panel lg:col-span-2">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-clinical-ink">
                Response Preview
              </h2>
              <p className="mt-1 text-sm text-zinc-600">
                Structured around the documented FastAPI response.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className="rounded-md bg-rose-50 px-3 py-1 text-xs font-semibold text-clinical-rose">
                Emergency
              </span>
              <span className="rounded-md bg-amber-50 px-3 py-1 text-xs font-semibold text-clinical-amber">
                Urgent
              </span>
              <span className="rounded-md bg-emerald-50 px-3 py-1 text-xs font-semibold text-clinical-teal">
                Routine
              </span>
              <span className="rounded-md bg-zinc-100 px-3 py-1 text-xs font-semibold text-zinc-700">
                Self-Care
              </span>
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-4">
            {responseFields.map((field) => (
              <div
                key={field}
                className="min-h-28 rounded-lg border border-clinical-line bg-zinc-50 p-4"
              >
                <p className="text-sm font-medium text-clinical-ink">
                  {field}
                </p>
                <div className="mt-4 space-y-2">
                  <span className="block h-2 rounded-full bg-zinc-200" />
                  <span className="block h-2 w-2/3 rounded-full bg-zinc-200" />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  )
}
