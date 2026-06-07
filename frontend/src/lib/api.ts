import type { TriageRequest, TriageResponse } from '../types/triage'

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? 'http://localhost:8000'

/** True when the built-in fallback URL is in use — means no VITE_API_BASE_URL was set. */
export const isUsingFallbackUrl = API_BASE_URL === 'http://localhost:8000'

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly payload: unknown,
    /** The full URL that was called (for debugging). */
    public readonly url?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

const TRIAGE_TIMEOUT_MS = 600_000 // 10 minutes — Cloud Run LLM inference is slow on L4 GPU

function triageUrl(): string {
  return `${API_BASE_URL}/api/v1/triage`
}

/**
 * Build a human-readable diagnostic summary for debugging connectivity issues.
 * Call this from the browser console: `await diagnose()`
 */
export async function diagnose(): Promise<string> {
  const lines: string[] = [
    `API_BASE_URL = ${API_BASE_URL}`,
    `Fallback?     = ${isUsingFallbackUrl}`,
    `Triage URL    = ${triageUrl()}`,
    ``,
  ]

  // 1. Health check
  try {
    const res = await fetch(`${API_BASE_URL}/health`, {
      signal: AbortSignal.timeout(5_000),
    })
    lines.push(`Health GET  → ${res.status} ${res.statusText}`)
    const ct = res.headers.get('content-type') ?? ''
    lines.push(`  Content-Type: ${ct}`)
    if (ct.includes('json')) {
      const body = await res.json()
      lines.push(`  Body: ${JSON.stringify(body).slice(0, 200)}`)
    }
  } catch (err) {
    lines.push(`Health GET  → FAILED: ${err instanceof Error ? err.message : String(err)}`)
  }

  // 2. CORS preflight
  try {
    const res = await fetch(triageUrl(), {
      method: 'OPTIONS',
      signal: AbortSignal.timeout(5_000),
    })
    lines.push(`CORS preflight → ${res.status}`)
    lines.push(`  Allow-Origin: ${res.headers.get('access-control-allow-origin') ?? 'MISSING'}`)
  } catch (err) {
    lines.push(`CORS preflight → FAILED: ${err instanceof Error ? err.message : String(err)}`)
  }

  return lines.join('\n')
}

export async function submitTriage(
  request: TriageRequest,
): Promise<TriageResponse> {
  const url = triageUrl()
  const formData = new FormData()
  formData.append('symptoms', request.symptoms)

  if (request.patientContext) {
    formData.append('patient_context', JSON.stringify(request.patientContext))
  }

  if (request.image) {
    formData.append('image', request.image)
  }

  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(TRIAGE_TIMEOUT_MS),
    })
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'TimeoutError') {
      throw new ApiError(
        `Request to ${url} timed out after ${TRIAGE_TIMEOUT_MS / 1000}s. ` +
          'The backend may be cold-starting or overloaded. Try again in a few seconds.',
        0,
        null,
        url,
      )
    }
    // Network errors include CORS blocks, DNS failures, connection refused.
    const hint = isUsingFallbackUrl
      ? ' The app is using the fallback URL (localhost). Set VITE_API_BASE_URL for production.'
      : ''
    throw new ApiError(
      `Cannot reach ${url}. Check your connection and try again.${hint}`,
      0,
      null,
      url,
    )
  }

  // Handle non-JSON responses gracefully.
  let payload: unknown
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('json')) {
    payload = await response.json()
  } else {
    const text = await response.text().catch(() => '')
    payload = text.slice(0, 500)
  }

  if (!response.ok) {
    const detail =
      typeof payload === 'object' && payload !== null && 'detail' in payload
        ? String((payload as Record<string, unknown>).detail)
        : ''
    throw new ApiError(
      `Triage request failed (${response.status}): ${detail || 'Unknown error'}`,
      response.status,
      payload,
      url,
    )
  }

  return payload as TriageResponse
}
