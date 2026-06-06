import { useState, useRef, useEffect, type ChangeEvent } from 'react'
import type { PatientContext, TriageRequest } from '../types/triage'

const MAX_SYMPTOMS = 2000
const MAX_FILE_SIZE = 5 * 1024 * 1024
const ALLOWED_TYPES = ['image/jpeg', 'image/png']

interface TriageFormProps {
  onSubmit: (req: TriageRequest) => void
  onClear?: () => void
  loading: boolean
  apiError: string | null
}

export function TriageForm({ onSubmit, onClear, loading, apiError }: TriageFormProps) {
  const [symptoms, setSymptoms] = useState('')
  const [age, setAge] = useState<number | ''>('')
  const [sex, setSex] = useState<'male' | 'female' | ''>('')
  const [image, setImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    return () => {
      if (imagePreview) URL.revokeObjectURL(imagePreview)
    }
  }, [imagePreview])

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    setValidationError(null)
    const f = e.target.files?.[0] ?? null

    if (imagePreview) {
      URL.revokeObjectURL(imagePreview)
      setImagePreview(null)
    }

    if (!f) {
      setImage(null)
      return
    }

    if (!ALLOWED_TYPES.includes(f.type)) {
      setValidationError('Image must be JPEG or PNG')
      if (fileRef.current) fileRef.current.value = ''
      return
    }
    if (f.size > MAX_FILE_SIZE) {
      setValidationError('Image must be 5 MB or smaller')
      if (fileRef.current) fileRef.current.value = ''
      return
    }

    setImage(f)
    setImagePreview(URL.createObjectURL(f))
  }

  function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault()
    setValidationError(null)

    if (!symptoms.trim()) {
      setValidationError('Symptoms are required')
      return
    }
    if (symptoms.length > MAX_SYMPTOMS) {
      setValidationError(`Symptoms must be ${MAX_SYMPTOMS} characters or fewer`)
      return
    }

    const patientContext: PatientContext | undefined =
      age || sex
        ? { age: typeof age === 'number' ? age : undefined, sex: sex || undefined }
        : undefined

    onSubmit({
      symptoms: symptoms.trim(),
      patientContext,
      image: image ?? undefined,
    })
  }

  function handleClear() {
    if (imagePreview) {
      URL.revokeObjectURL(imagePreview)
    }
    setSymptoms('')
    setAge('')
    setSex('')
    setImage(null)
    setImagePreview(null)
    setValidationError(null)
    if (fileRef.current) fileRef.current.value = ''
    onClear?.()
  }

  function handleSexChange(e: ChangeEvent<HTMLSelectElement>) {
    const value = e.target.value
    setSex(value === 'male' || value === 'female' ? value : '')
  }

  const displayError = validationError ?? apiError
  const charRatio = symptoms.length / MAX_SYMPTOMS
  const counterColor =
    charRatio > 0.9 ? 'text-critical' : charRatio > 0.75 ? 'text-warning' : 'text-muted'

  return (
    <section className="rounded-2xl border border-border bg-gradient-to-b from-surface to-canvas p-6 shadow-card">
      <div className="mb-7">
        <h2 className="text-lg font-semibold tracking-tight text-ink">Triage Intake</h2>
        <p className="mt-1 text-sm text-muted">
          Enter patient symptoms and optional context for AI-assisted triage.
        </p>
      </div>

      <form className="grid gap-6" onSubmit={handleSubmit} noValidate>
        {/* Symptoms */}
        <div className="flex flex-col gap-2">
          <label htmlFor="triage-symptoms" className="text-sm font-medium text-ink">
            Symptoms
          </label>
          <textarea
            id="triage-symptoms"
            aria-label="symptoms"
            aria-describedby="symptoms-counter symptoms-error"
            aria-invalid={validationError?.startsWith('Symptoms') || undefined}
            value={symptoms}
            onChange={(e) => setSymptoms(e.target.value)}
            className="min-h-[140px] rounded-xl border border-border bg-surface px-4 py-3 text-sm text-ink placeholder:text-muted transition-shadow focus:border-accent/40 focus:outline-none focus:shadow-input"
            maxLength={MAX_SYMPTOMS}
            placeholder="Describe symptoms, e.g. chest pain, shortness of breath..."
          />
          <div id="symptoms-counter" className={`text-xs tabular-nums ${counterColor}`}>
            {symptoms.length}/{MAX_SYMPTOMS}
          </div>
        </div>

        {/* Age + Sex */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="triage-age" className="text-sm font-medium text-ink">
              Age <span className="font-normal text-muted">· optional</span>
            </label>
            <input
              id="triage-age"
              type="number"
              min={0}
              max={130}
              value={age}
              onChange={(e) => setAge(e.target.value === '' ? '' : Number(e.target.value))}
              className="mt-1.5 w-full rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-ink placeholder:text-muted transition-shadow focus:border-accent/40 focus:outline-none focus:shadow-input"
              placeholder="e.g. 45"
            />
          </div>
          <div>
            <label htmlFor="triage-sex" className="text-sm font-medium text-ink">
              Sex <span className="font-normal text-muted">· optional</span>
            </label>
            <select
              id="triage-sex"
              value={sex}
              onChange={handleSexChange}
              className="mt-1.5 w-full rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-ink transition-shadow focus:border-accent/40 focus:outline-none focus:shadow-input"
            >
              <option value="">Not provided</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select>
          </div>
        </div>

        {/* Image upload */}
        <div>
          <label htmlFor="triage-image" className="text-sm font-medium text-ink">
            Image <span className="font-normal text-muted">· optional, JPEG/PNG, max 5 MB</span>
          </label>
          <input
            ref={fileRef}
            id="triage-image"
            type="file"
            accept="image/png,image/jpeg"
            onChange={handleFileChange}
            aria-label="Upload image (JPEG or PNG, max 5 MB)"
            className="mt-2 text-sm text-muted file:mr-3 file:cursor-pointer file:rounded-lg file:border file:border-border file:bg-surface file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-ink file:shadow-sm file:transition-colors hover:file:bg-canvas"
          />
          {imagePreview && (
            <div className="relative mt-3 inline-block">
              <img
                src={imagePreview}
                alt="Uploaded image preview"
                className="max-h-40 rounded-xl"
              />
              <button
                type="button"
                onClick={() => {
                  if (imagePreview) URL.revokeObjectURL(imagePreview)
                  setImage(null)
                  setImagePreview(null)
                  if (fileRef.current) fileRef.current.value = ''
                }}
                className="absolute -right-1.5 -top-1.5 grid size-5 place-items-center rounded-full bg-ink text-[10px] text-white shadow-sm transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1"
                aria-label="Remove image"
              >
                ✕
              </button>
            </div>
          )}
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-3 pt-1">
          <button
            type="button"
            onClick={handleClear}
            className="min-h-[44px] rounded-xl border border-border px-5 py-2.5 text-sm font-medium text-ink transition-all hover:bg-canvas hover:shadow-sm focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1 disabled:opacity-30"
            disabled={loading}
          >
            Clear
          </button>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-accent px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-accent-hover hover:shadow-md focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1 disabled:opacity-40"
          >
            {loading && (
              <svg
                className="size-4 animate-spin motion-safe:animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            )}
            {loading ? 'Submitting...' : 'Submit Triage'}
          </button>
        </div>

        {/* Error display */}
        {displayError && (
          <div
            id="symptoms-error"
            role="alert"
            aria-live="assertive"
            className="rounded-xl border border-critical/20 bg-critical-subtle px-4 py-3 text-sm font-medium text-critical"
          >
            {displayError}
          </div>
        )}
      </form>
    </section>
  )
}
