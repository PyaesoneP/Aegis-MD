import { useState, useRef } from 'react'
import { submitTriage, ApiError } from '../lib/api'
import type { TriageRequest, TriageResponse } from '../types/triage'
import { TriageHeader } from './TriageHeader'
import { TriageForm } from './TriageForm'
import { GatewayPath } from './GatewayPath'
import { ResponsePreview } from './ResponsePreview'

export function Shell() {
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const [response, setResponse] = useState<TriageResponse | null>(null)
  const responseRef = useRef<HTMLDivElement | null>(null)

  async function handleSubmit(req: TriageRequest) {
    setApiError(null)
    setResponse(null)
    setLoading(true)

    try {
      const res = await submitTriage(req)
      setResponse(res)
      // Move focus to the response section after a tick so the DOM has updated
      setTimeout(() => {
        responseRef.current?.querySelector('h2')?.focus()
      }, 0)
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setApiError(
          typeof err.payload === 'string' ? err.payload : 'Triage request failed',
        )
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
    <main className="min-h-screen bg-clinical-paper">
      <TriageHeader />

      <div className="mx-auto grid w-full max-w-6xl gap-5 px-5 py-6 lg:grid-cols-[1.15fr_0.85fr]">
        <TriageForm
          onSubmit={handleSubmit}
          onClear={handleClear}
          loading={loading}
          apiError={apiError}
        />

        <GatewayPath />

        <div ref={responseRef}>
          <ResponsePreview response={response} loading={loading} />
        </div>
      </div>
    </main>
  )
}
