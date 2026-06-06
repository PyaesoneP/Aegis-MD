import type { TriageRequest, TriageResponse } from '../types/triage'

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? 'http://localhost:8000'

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly payload: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

const TRIAGE_TIMEOUT_MS = 30_000

export async function submitTriage(
  request: TriageRequest,
): Promise<TriageResponse> {
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
    response = await fetch(`${API_BASE_URL}/api/v1/triage`, {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(TRIAGE_TIMEOUT_MS),
    })
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'TimeoutError') {
      throw new ApiError(
        'Request timed out. The server may be unavailable. Please try again.',
        0,
        null,
      )
    }
    throw new ApiError(
      'Cannot reach server. Check your connection and try again.',
      0,
      null,
    )
  }

  const payload: unknown = await response.json()

  if (!response.ok) {
    throw new ApiError('Triage request failed', response.status, payload)
  }

  return payload as TriageResponse
}
