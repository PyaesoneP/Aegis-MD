import React, { useState, useRef } from 'react'
import { API_BASE_URL, submitTriage, ApiError } from '../lib/api'
import type { PatientContext, TriageRequest, TriageResponse } from '../types/triage'

const responseFields = ['Urgency tier', 'Rationale', 'Sources', 'Disclaimer']
const gatewayStages = ['React UI', 'FastAPI Gateway', 'Security Filter', 'Router']

export function Shell() {
  const [symptoms, setSymptoms] = useState('')
  const [age, setAge] = useState<number | ''>('')
  const [sex, setSex] = useState<'male' | 'female' | ''>('')
  const [image, setImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [response, setResponse] = useState<TriageResponse | null>(null)
  const fileRef = useRef<HTMLInputElement | null>(null)

  const maxSymptoms = 2000

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setError(null)
    const f = e.target.files?.[0] ?? null
    if (!f) {
      setImage(null)
      setImagePreview(null)
      return
    }

    if (!['image/jpeg', 'image/png'].includes(f.type)) {
      setError('Image must be JPEG or PNG')
      fileRef.current && (fileRef.current.value = '')
      return
    }
    if (f.size > 5 * 1024 * 1024) {
      setError('Image must be 5 MB or smaller')
      fileRef.current && (fileRef.current.value = '')
      return
    }

    setImage(f)
    setImagePreview(URL.createObjectURL(f))
  }

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault()
    setError(null)
    setResponse(null)

    if (!symptoms.trim()) {
      setError('Symptoms are required')
      return
    }
    if (symptoms.length > maxSymptoms) {
      setError(`Symptoms must be ${maxSymptoms} characters or fewer`)
      return
    }

    const patientContext: PatientContext | undefined =
      age || sex
        ? { age: typeof age === 'number' ? age : undefined, sex: sex || undefined }
        : undefined

    const req: TriageRequest = {
      symptoms,
      patientContext,
      image: image ?? undefined,
    }

    setLoading(true)
    try {
      const res = await submitTriage(req)
      setResponse(res)
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(
          typeof err.payload === 'string' ? err.payload : 'Triage request failed',
        )
      } else {
        setError(String(err?.message ?? 'Unknown error'))
      }
    } finally {
      setLoading(false)
    }
  }

  function clearForm() {
    setSymptoms('')
    setAge('')
    setSex('')
    setImage(null)
    setImagePreview(null)
    setError(null)
    setResponse(null)
    if (fileRef.current) fileRef.current.value = ''
  }

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

          <form className="mt-5 grid gap-3" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-clinical-ink">Symptoms</label>
              <textarea
                aria-label="symptoms"
                value={symptoms}
                onChange={(e) => setSymptoms(e.target.value)}
                className="min-h-[120px] rounded-md border border-clinical-line p-3"
                maxLength={maxSymptoms}
                placeholder="Describe symptoms, e.g. chest pain, shortness of breath..."
              />
              <div className="text-xs text-zinc-500">{symptoms.length}/{maxSymptoms}</div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium text-clinical-ink">Age (optional)</label>
                <input
                  type="number"
                  min={0}
                  max={130}
                  value={age}
                  onChange={(e) => setAge(e.target.value === '' ? '' : Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-clinical-line p-2"
                  placeholder="e.g. 45"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-clinical-ink">Sex (optional)</label>
                <select
                  value={sex}
                  onChange={(e) => setSex(e.target.value as any)}
                  className="mt-1 w-full rounded-md border border-clinical-line p-2"
                >
                  <option value="">Not provided</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-clinical-ink">Optional image</label>
              <input
                ref={fileRef}
                type="file"
                accept="image/png,image/jpeg"
                onChange={handleFileChange}
                className="mt-2"
              />
              {imagePreview && (
                <img src={imagePreview} alt="preview" className="mt-2 max-h-40 rounded-md" />
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={clearForm}
                className="rounded-md border border-clinical-line px-3 py-2 text-sm"
                disabled={loading}
              >
                Clear
              </button>
              <button
                type="submit"
                disabled={loading}
                className="rounded-md bg-clinical-teal px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                {loading ? 'Submitting...' : 'Submit Triage'}
              </button>
            </div>

            {error && <div className="text-sm text-rose-600">{error}</div>}
          </form>
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
              {response ? (
                <>
                  <div className="min-h-28 rounded-lg border border-clinical-line bg-zinc-50 p-4">
                    <p className="text-sm font-medium text-clinical-ink">Urgency</p>
                    <div className="mt-4 text-xl font-semibold">{response.triage_result.urgency}</div>
                  </div>
                  <div className="min-h-28 rounded-lg border border-clinical-line bg-zinc-50 p-4">
                    <p className="text-sm font-medium text-clinical-ink">Rationale</p>
                    <div className="mt-4 text-sm text-zinc-700">{response.triage_result.rationale}</div>
                  </div>
                  <div className="min-h-28 rounded-lg border border-clinical-line bg-zinc-50 p-4">
                    <p className="text-sm font-medium text-clinical-ink">Sources</p>
                    <ul className="mt-4 list-disc pl-5 text-sm">
                      {response.triage_result.sources.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="min-h-28 rounded-lg border border-clinical-line bg-zinc-50 p-4">
                    <p className="text-sm font-medium text-clinical-ink">Disclaimer</p>
                    <div className="mt-4 text-xs text-zinc-500">{response.triage_result.disclaimer}</div>
                  </div>
                </>
              ) : (
                responseFields.map((field) => (
                  <div
                    key={field}
                    className="min-h-28 rounded-lg border border-clinical-line bg-zinc-50 p-4"
                  >
                    <p className="text-sm font-medium text-clinical-ink">{field}</p>
                    <div className="mt-4 space-y-2">
                      <span className="block h-2 rounded-full bg-zinc-200" />
                      <span className="block h-2 w-2/3 rounded-full bg-zinc-200" />
                    </div>
                  </div>
                ))
              )}
          </div>
        </section>
      </div>
    </main>
  )
}
