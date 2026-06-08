import { describe, it, expect, vi, beforeEach } from 'vitest'
import { submitTriage, ApiError, API_BASE_URL, diagnose } from '../api'
import type { TriageFormData } from '../../types/triage'

const validFormData: TriageFormData = {
  chief_complaint: 'chest pain radiating to left arm',
  vitals: { hr: 110, rr: 22, spo2: 94 },
  age: 65,
  sex: 'male',
  pain_score: 8,
  comorbidities: { cardiac_disease: true },
}

describe('ApiError', () => {
  it('has correct name and properties', () => {
    const err = new ApiError('Not Found', 404, { detail: 'missing' })
    expect(err.name).toBe('ApiError')
    expect(err.message).toBe('Not Found')
    expect(err.status).toBe(404)
    expect(err.payload).toEqual({ detail: 'missing' })
  })

  it('stores optional url', () => {
    const err = new ApiError('Error', 500, null, 'http://example.com/api')
    expect(err.url).toBe('http://example.com/api')
  })
})

describe('API_BASE_URL', () => {
  it('is a string', () => {
    expect(typeof API_BASE_URL).toBe('string')
  })

  it('defaults to localhost:8000', () => {
    expect(API_BASE_URL).toBe('http://localhost:8000')
  })
})

describe('submitTriage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('sends POST with multipart form data', async () => {
    const mockResponse = {
      request_id: 'req-1',
      triage_result: {
        ats_category: 'ATS-2',
        ats_card: { category: 'ATS-2', label: 'Emergency', time_target_min: 10, color: '#ea580c' },
        rationale: 'Test',
        confidence: 'high',
        sources: [],
        disclaimer: 'Disclaimer',
      },
      vision_result: null,
      latency_ms: 100,
      security_passed: true,
    }

    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    const result = await submitTriage(validFormData)

    expect(result).toEqual(mockResponse)
    expect(fetch).toHaveBeenCalledTimes(1)
    const [url, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(url).toContain('/api/v1/triage')
    expect(init.method).toBe('POST')
    expect(init.body).toBeInstanceOf(FormData)
  })

  it('throws ApiError on non-ok response', async () => {
    const errorPayload = { error: 'Bad request' }
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: () => Promise.resolve(errorPayload),
    })

    let caught: ApiError | null = null
    try {
      await submitTriage(validFormData)
    } catch (err) {
      caught = err as ApiError
    }
    expect(caught).toBeInstanceOf(ApiError)
    expect(caught!.status).toBe(400)
  })

  it('throws ApiError on network failure', async () => {
    globalThis.fetch = vi.fn().mockRejectedValueOnce(new TypeError('Failed to fetch'))

    await expect(submitTriage(validFormData)).rejects.toThrow(ApiError)
  })
})

describe('diagnose', () => {
  it('returns a diagnostic string with API_BASE_URL', async () => {
    globalThis.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        headers: new Map([['content-type', 'application/json']]) as unknown as Headers,
        json: () => Promise.resolve({ status: 'ok' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 204,
        headers: new Map([['access-control-allow-origin', '*']]) as unknown as Headers,
      })

    const result = await diagnose()
    expect(result).toContain('http://localhost:8000')
    expect(result).toContain('Health GET')
    expect(result).toContain('CORS preflight')
  })
})
