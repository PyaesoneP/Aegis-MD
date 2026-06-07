import { useState, useRef, useEffect } from 'react'
import Lenis from 'lenis'
import { submitTriage, ApiError } from '../lib/api'
import type { TriageRequest, TriageResponse } from '../types/triage'
import { TriageHeader } from './TriageHeader'
import { TriageForm } from './TriageForm'
import { ResponsePreview } from './ResponsePreview'
import { NoiseOverlay } from './NoiseOverlay'
import { CursorGlow } from './CursorGlow'

export function Shell() {
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const [response, setResponse] = useState<TriageResponse | null>(null)
  const responseRef = useRef<HTMLDivElement | null>(null)

  // Lenis smooth scrolling
  useEffect(() => {
    const reducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (reducedMotion) return

    const lenis = new Lenis({ lerp: 0.08, duration: 1.2, smoothWheel: true })

    function raf(time: number) {
      lenis.raf(time)
      requestAnimationFrame(raf)
    }
    requestAnimationFrame(raf)

    return () => lenis.destroy()
  }, [])

  async function handleSubmit(req: TriageRequest) {
    setApiError(null)
    setResponse(null)
    setLoading(true)

    // Scroll to the loading sequence so user sees the engaging animation
    responseRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })

    try {
      const res = await submitTriage(req)
      setResponse(res)
      setTimeout(() => {
        responseRef.current?.querySelector('h2')?.focus()
      }, 0)
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        // Use the descriptive message (includes URL, status, and hint for fallback URLs).
        setApiError(err.message)
      } else if (err instanceof Error) {
        setApiError(err.message)
      } else {
        setApiError('An unexpected error occurred')
      }
    } finally {
      setLoading(false)
    }
  }

  function handleClear() {
    setApiError(null)
    setResponse(null)
  }

  return (
    <main className="min-h-screen bg-canvas">
      <NoiseOverlay />
      <CursorGlow />
      <TriageHeader />

      {/* Response — hero section when present */}
      {response && (
        <div className="bg-gradient-to-b from-surface via-surface/50 to-canvas border-b border-border/40">
          <div className="mx-auto max-w-6xl px-6 py-12">
            <ResponsePreview response={response} loading={false} />
          </div>
        </div>
      )}

      {/* Form — primary when no response yet, secondary after submission */}
      <div className="mx-auto max-w-5xl space-y-8 px-6 py-8">
        {response ? (
          <details className="group">
            <summary className="flex cursor-pointer items-center gap-3 text-sm text-muted hover:text-ink transition-colors marker:content-none">
              <span className="inline-flex size-1.5 rounded-full bg-accent" />
              <span className="truncate font-medium font-sans">
                Query submitted — tap to edit
              </span>
              <svg
                className="size-3 shrink-0 transition-transform group-open:rotate-180"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </summary>
            <div className="mt-4">
              <TriageForm
                onSubmit={handleSubmit}
                onClear={handleClear}
                loading={loading}
                apiError={apiError}
              />
            </div>
          </details>
        ) : (
          <>
            <TriageForm
              onSubmit={handleSubmit}
              onClear={handleClear}
              loading={loading}
              apiError={apiError}
            />

            <div ref={responseRef}>
              <ResponsePreview response={response} loading={loading} />
            </div>
          </>
        )}
      </div>
    </main>
  )
}
