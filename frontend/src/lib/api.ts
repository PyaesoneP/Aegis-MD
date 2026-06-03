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

  const response = await fetch(`${API_BASE_URL}/api/v1/triage`, {
    method: 'POST',
    body: formData,
  })
  const payload: unknown = await response.json()

  if (!response.ok) {
    throw new ApiError('Triage request failed', response.status, payload)
  }

  return payload as TriageResponse
}
