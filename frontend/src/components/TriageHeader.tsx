import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../lib/api'

type HealthStatus = 'ok' | 'error' | 'checking'

const dotColors: Record<HealthStatus, string> = {
  ok: 'bg-safe',
  error: 'bg-critical',
  checking: 'bg-muted animate-breath',
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
        const res = await fetch(`${API_BASE_URL}/health`, {
          signal: AbortSignal.timeout(5000),
        })
        if (!cancelled) setHealth(res.ok ? 'ok' : 'error')
      } catch {
        if (!cancelled) setHealth('error')
      }
    }
    check()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <header className="glass sticky top-0 z-40 border-b border-white/20 transition-shadow">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted font-display">
            Aegis-MD
          </p>
          <h1 className="mt-1 text-xl font-bold tracking-tight text-ink font-sans">
            Multimodal Triage Console
          </h1>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-border/60 bg-surface px-3 py-1.5 text-xs shadow-sm">
          <span
            className={`inline-block size-2 shrink-0 rounded-full ${dotColors[health]}`}
            aria-label={dotLabels[health]}
            title={dotLabels[health]}
          />
          <span className="font-medium text-ink tabular-nums font-mono">
            {API_BASE_URL}
          </span>
        </div>
      </div>
    </header>
  )
}
