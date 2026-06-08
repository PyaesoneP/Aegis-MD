import type { TriageFormData, TriageResponse } from '../types/triage'

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? 'http://localhost:8000'

/** True when the built-in fallback URL is in use — means no VITE_API_BASE_URL was set. */
export const isUsingFallbackUrl = API_BASE_URL === 'http://localhost:8000'

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly payload: unknown,
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
  formData: TriageFormData,
): Promise<TriageResponse> {
  const url = triageUrl()
  const fd = new FormData()

  // Required fields
  fd.append('chief_complaint', formData.chief_complaint)
  fd.append('age', String(formData.age))
  fd.append('sex', formData.sex)
  fd.append('pain_score', String(formData.pain_score))

  // Vitals as JSON
  fd.append('vitals', JSON.stringify(formData.vitals))

  // Contextual fields (only send if provided)
  if (formData.onset) fd.append('onset', formData.onset)
  if (formData.arrival_mode) fd.append('arrival_mode', formData.arrival_mode)
  if (formData.consciousness) fd.append('consciousness', formData.consciousness)
  if (formData.mechanism) fd.append('mechanism', formData.mechanism)

  // Comorbidities as JSON
  fd.append('comorbidities', JSON.stringify(formData.comorbidities))

  // Pregnancy
  if (formData.pregnancy) fd.append('pregnancy', formData.pregnancy)

  // Allergies
  if (formData.allergies) fd.append('allergies', formData.allergies)

  // Image
  if (formData.image) fd.append('image', formData.image)

  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      body: fd,
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
    throw new ApiError(
      `Network error connecting to ${url}: ${err instanceof Error ? err.message : String(err)}`,
      0,
      null,
      url,
    )
  }

  const body = await response.json()

  if (!response.ok) {
    throw new ApiError(
      body?.error ?? `Request failed with status ${response.status}`,
      response.status,
      body,
      url,
    )
  }

  return body as TriageResponse
}
