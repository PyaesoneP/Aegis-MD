import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../lib/api'

type HealthStatus = 'ok' | 'error' | 'checking'

const dotColors: Record<HealthStatus, string> = {
  ok: 'bg-emerald-500',
  error: 'bg-rose-500',
  checking: 'bg-zinc-400 animate-pulse',
}

const dotLabels: Record<HealthStatus, string> = {
  ok: 'API reachable',
  error: 'API unreachable',
  checking: 'Checking API status',
}

export function TriageHeader() {
  const [health, setHealth] = useState<HealthStatus>('checking')

  useEffect(() => {
    let cancelled = false
    async function check() {
      try {
        const res = await fetch(`${API_BASE_URL}/health`, { signal: AbortSignal.timeout(5000) })
        if (!cancelled) setHealth(res.ok ? 'ok' : 'error')
      } catch {
        if (!cancelled) setHealth('error')
      }
    }
    check()
    return () => { cancelled = true }
  }, [])

  return (
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
        <div className="flex items-center gap-3 rounded-lg border border-clinical-line bg-clinical-mint px-4 py-3 text-sm text-clinical-ink">
          <span
            className={`inline-block size-2.5 shrink-0 rounded-full ${dotColors[health]}`}
            aria-label={dotLabels[health]}
            title={dotLabels[health]}
          />
          <span className="font-semibold">API</span>
          <span className="break-all">{API_BASE_URL}</span>
        </div>
      </div>
    </header>
  )
}
