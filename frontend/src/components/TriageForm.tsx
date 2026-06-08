import { useState, useRef, useEffect, type ChangeEvent } from 'react'
import { motion } from 'framer-motion'
import type { TriageFormData, Vitals, ComorbidityFlags, Onset, ArrivalMode, AVPU, Mechanism, PregnancyStatus } from '../types/triage'
import { useMagnetic } from '../hooks/useMagnetic'

const MAX_COMPLAINT = 150
const MAX_ALLERGIES = 200
const MAX_FILE_SIZE = 5 * 1024 * 1024
const ALLOWED_TYPES = ['image/jpeg', 'image/png']

interface TriageFormProps {
  onSubmit: (data: TriageFormData) => void
  onClear?: () => void
  loading: boolean
  apiError: string | null
}

const emptyVitals: Vitals = {
  hr: undefined, rr: undefined, spo2: undefined,
  temp: undefined, bp_systolic: undefined, bp_diastolic: undefined,
}

const emptyComorbidities: ComorbidityFlags = {
  cardiac_disease: false, diabetes_mellitus: false,
  respiratory_disease: false, immunocompromised: false,
  anticoagulants: false, renal_disease: false,
}

export function TriageForm({ onSubmit, onClear, loading, apiError }: TriageFormProps) {
  const [complaint, setComplaint] = useState('')
  const [vitals, setVitals] = useState<Vitals>({ ...emptyVitals })
  const [age, setAge] = useState<number | ''>('')
  const [sex, setSex] = useState<'male' | 'female' | ''>('')
  const [painScore, setPainScore] = useState<number | null>(null)
  const [onset, setOnset] = useState<Onset | ''>('')
  const [arrivalMode, setArrivalMode] = useState<ArrivalMode | ''>('')
  const [consciousness, setConsciousness] = useState<AVPU | ''>('')
  const [mechanism, setMechanism] = useState<Mechanism | ''>('')
  const [comorbidities, setComorbidities] = useState<ComorbidityFlags>({ ...emptyComorbidities })
  const [pregnancy, setPregnancy] = useState<PregnancyStatus | ''>('')
  const [allergies, setAllergies] = useState('')
  const [image, setImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)

  const fileRef = useRef<HTMLInputElement | null>(null)
  const magnetic = useMagnetic()

  useEffect(() => {
    return () => { if (imagePreview) URL.revokeObjectURL(imagePreview) }
  }, [imagePreview])

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    setValidationError(null)
    const f = e.target.files?.[0] ?? null
    if (imagePreview) { URL.revokeObjectURL(imagePreview); setImagePreview(null) }
    if (!f) { setImage(null); return }
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

  function setVital(key: keyof Vitals, value: string) {
    if (value === '') {
      setVitals(prev => ({ ...prev, [key]: undefined }))
      return
    }
    const num = key === 'temp' ? parseFloat(value) : parseInt(value, 10)
    if (!isNaN(num)) setVitals(prev => ({ ...prev, [key]: num }))
  }

  function toggleComorbidity(key: keyof ComorbidityFlags) {
    setComorbidities(prev => ({ ...prev, [key]: !prev[key] }))
  }

  function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault()
    setValidationError(null)

    if (!complaint.trim()) { setValidationError('Chief complaint is required'); return }
    if (complaint.length > MAX_COMPLAINT) { setValidationError('Chief complaint must be ' + MAX_COMPLAINT + ' characters or fewer'); return }
    if (!sex) { setValidationError('Sex is required'); return }
    if (age === '' || (age as number) < 0 || (age as number) > 130) { setValidationError('Valid age (0-130) is required'); return }
    if (painScore === null) { setValidationError('Pain score is required'); return }

    const data: TriageFormData = {
      chief_complaint: complaint.trim(),
      vitals,
      age: age as number,
      sex: sex as 'male' | 'female',
      pain_score: painScore,
      onset: onset || undefined,
      arrival_mode: arrivalMode || undefined,
      consciousness: consciousness || undefined,
      mechanism: mechanism || undefined,
      comorbidities,
      pregnancy: pregnancy || undefined,
      allergies: allergies.trim() || undefined,
      image: image ?? undefined,
    }
    onSubmit(data)
  }

  function handleClear() {
    if (imagePreview) URL.revokeObjectURL(imagePreview)
    setComplaint(''); setVitals({ ...emptyVitals }); setAge(''); setSex('')
    setPainScore(null); setOnset(''); setArrivalMode(''); setConsciousness('')
    setMechanism(''); setComorbidities({ ...emptyComorbidities }); setPregnancy('')
    setAllergies(''); setImage(null); setImagePreview(null); setValidationError(null)
    if (fileRef.current) fileRef.current.value = ''
    onClear?.()
  }

  const displayError = validationError ?? apiError
  const charRatio = complaint.length / MAX_COMPLAINT
  const counterColor = charRatio > 0.9 ? 'text-critical' : charRatio > 0.75 ? 'text-warning' : 'text-muted'

  const showPregnancy = sex === 'female'
  const showMechanism = true

  return (
    <section className="glass rounded-3xl p-6 shadow-card border-t-2 border-t-accent">
      <div className="mb-8">
        <h2 className="text-2xl font-bold tracking-tight text-ink font-display">
          ED Triage Intake
        </h2>
        <p className="mt-1.5 text-sm text-muted font-sans">
          Designed for 2-5 minute triage assessment. Complete all required fields.
        </p>
      </div>

      <form className="grid gap-7" onSubmit={handleSubmit} noValidate>

        <div className="flex flex-col gap-2">
          <label htmlFor="chief-complaint" className="text-sm font-semibold text-ink font-sans">
            Chief Complaint <span className="text-critical">*</span>
          </label>
          <textarea
            id="chief-complaint"
            aria-label="Chief complaint"
            aria-describedby="complaint-counter complaint-error"
            aria-invalid={!!validationError?.startsWith('Chief complaint') || undefined}
            value={complaint}
            onChange={e => setComplaint(e.target.value)}
            className="min-h-[80px] rounded-2xl border border-border bg-surface px-4 py-3 text-sm text-ink placeholder:text-muted transition-all duration-200 focus:border-accent/40 focus:outline-none focus:shadow-glow"
            maxLength={MAX_COMPLAINT}
            placeholder="e.g. 65M, central chest pain radiating to jaw, onset 40 min ago, diaphoretic"
          />
          <div id="complaint-counter" className={'text-xs tabular-nums ' + counterColor}>
            {complaint.length}/{MAX_COMPLAINT}
          </div>
        </div>

        <fieldset className="border-0 p-0">
          <legend className="text-sm font-semibold text-ink font-sans mb-3">Vitals</legend>
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-3">
            <VitalInput label="HR" unit="bpm" value={vitals.hr} onChange={v => setVital('hr', v)} hint="60-100" />
            <VitalInput label="RR" unit="/min" value={vitals.rr} onChange={v => setVital('rr', v)} hint="12-20" />
            <VitalInput label="SpO2" unit="%" value={vitals.spo2} onChange={v => setVital('spo2', v)} hint=">=95" />
            <VitalInput label="Temp" unit="C" value={vitals.temp} onChange={v => setVital('temp', v)} hint="36.1-37.2" />
            <VitalInput label="BP Sys" unit="mmHg" value={vitals.bp_systolic} onChange={v => setVital('bp_systolic', v)} hint="100-140" />
            <VitalInput label="BP Dia" unit="mmHg" value={vitals.bp_diastolic} onChange={v => setVital('bp_diastolic', v)} hint="60-90" />
          </div>
        </fieldset>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="triage-age" className="text-sm font-semibold text-ink font-sans">
              Age <span className="text-critical">*</span>
            </label>
            <input
              id="triage-age"
              type="number"
              min={0} max={130}
              value={age}
              onChange={e => setAge(e.target.value === '' ? '' : Number(e.target.value))}
              className="mt-1.5 w-full rounded-2xl border border-border bg-surface px-4 py-2.5 text-sm text-ink placeholder:text-muted transition-all duration-200 focus:border-accent/40 focus:outline-none focus:shadow-glow"
              placeholder="e.g. 65"
            />
          </div>
          <div>
            <label className="text-sm font-semibold text-ink font-sans block mb-1.5">
              Sex <span className="text-critical">*</span>
            </label>
            <div className="flex gap-1.5">
              {(['male', 'female'] as const).map(opt => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => setSex(sex === opt ? '' : opt)}
                  className={'flex-1 rounded-xl border px-3 py-2 text-xs font-medium transition-all duration-150 ' +
                    (sex === opt ? 'bg-accent text-white border-accent shadow-sm' : 'bg-surface text-ink border-border hover:bg-canvas hover:border-accent/30')}
                >
                  {opt.charAt(0).toUpperCase() + opt.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div>
          <label className="text-sm font-semibold text-ink font-sans block mb-1.5">
            Pain Score (0-10) <span className="text-critical">*</span>
          </label>
          <div className="flex gap-0.5 flex-wrap">
            {Array.from({ length: 11 }, (_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setPainScore(i)}
                className={'min-w-[2.5rem] rounded-lg border px-2 py-1.5 text-xs font-semibold transition-all duration-150 ' +
                  (painScore === i
                    ? 'bg-accent text-white border-accent shadow-sm scale-105'
                    : 'bg-surface text-ink border-border hover:bg-canvas hover:border-accent/30')}
              >
                {i}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <ButtonGroup
            label="Onset"
            options={['<1 hour', '1-6 hours', '6-24 hours', '>24 hours']}
            value={onset}
            onChange={v => setOnset(v as Onset | '')}
          />
          <ButtonGroup
            label="Arrival Mode"
            options={['Ambulatory', 'Wheelchair', 'Stretcher', 'Ambulance']}
            value={arrivalMode}
            onChange={v => setArrivalMode(v as ArrivalMode | '')}
          />
        </div>

        <ButtonGroup
          label="Consciousness (AVPU)"
          options={['Alert', 'Verbal', 'Pain', 'Unresponsive']}
          value={consciousness}
          onChange={v => setConsciousness(v as AVPU | '')}
        />

        {showMechanism && (
          <ButtonGroup
            label="Mechanism (if trauma)"
            options={['Fall', 'MVA', 'Assault', 'Penetrating', 'Other']}
            value={mechanism}
            onChange={v => setMechanism(v as Mechanism | '')}
          />
        )}

        <fieldset className="border-0 p-0">
          <legend className="text-sm font-semibold text-ink font-sans mb-2">
            Risk Modifiers
          </legend>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {([
              ['cardiac_disease', 'Cardiac disease'],
              ['diabetes_mellitus', 'Diabetes mellitus'],
              ['respiratory_disease', 'Respiratory disease'],
              ['immunocompromised', 'Immunocompromised'],
              ['anticoagulants', 'Anticoagulants'],
              ['renal_disease', 'Renal disease'],
            ] as [keyof ComorbidityFlags, string][]).map(([key, label]) => (
              <label
                key={key}
                className={'flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-medium transition-all duration-150 cursor-pointer select-none ' +
                  (comorbidities[key]
                    ? 'bg-accent-subtle border-accent/40 text-ink'
                    : 'bg-surface border-border text-muted hover:border-accent/20 hover:text-ink')}
              >
                <input
                  type="checkbox"
                  checked={!!comorbidities[key]}
                  onChange={() => toggleComorbidity(key)}
                  className="sr-only"
                />
                <span className={'size-3.5 rounded border-2 flex items-center justify-center transition-all ' +
                  (comorbidities[key] ? 'bg-accent border-accent' : 'border-muted/40')}>
                  {comorbidities[key] && (
                    <svg className="size-2 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={4}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </span>
                {label}
              </label>
            ))}
          </div>
        </fieldset>

        {showPregnancy && (
          <ButtonGroup
            label="Pregnancy"
            options={['Yes', 'No', 'Unknown']}
            value={pregnancy}
            onChange={v => setPregnancy(v as PregnancyStatus | '')}
          />
        )}

        <div>
          <label htmlFor="triage-image" className="text-sm font-medium text-ink font-sans">
            Image <span className="font-normal text-muted"> - optional, JPEG/PNG, max 5 MB</span>
          </label>
          <input
            ref={fileRef}
            id="triage-image"
            type="file"
            accept="image/png,image/jpeg"
            onChange={handleFileChange}
            className="mt-2 text-sm text-muted file:mr-3 file:cursor-pointer file:rounded-xl file:border file:border-border file:bg-surface file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-ink file:shadow-sm file:transition-all hover:file:bg-canvas hover:file:shadow-md"
          />
          {imagePreview && (
            <motion.div
              className="relative mt-3 inline-block"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.2 }}
            >
              <img src={imagePreview} alt="Preview" className="max-h-32 rounded-xl border border-border object-cover" />
              <button
                type="button"
                onClick={() => { setImage(null); setImagePreview(null); if (fileRef.current) fileRef.current.value = '' }}
                className="absolute -top-2 -right-2 flex size-5 items-center justify-center rounded-full bg-critical text-white text-xs shadow-sm"
              >
                X
              </button>
            </motion.div>
          )}
        </div>

        <div>
          <label htmlFor="triage-allergies" className="text-sm font-medium text-ink font-sans">
            Known Allergies <span className="font-normal text-muted"> - optional</span>
          </label>
          <input
            id="triage-allergies"
            type="text"
            value={allergies}
            onChange={e => setAllergies(e.target.value)}
            maxLength={MAX_ALLERGIES}
            className="mt-1.5 w-full rounded-2xl border border-border bg-surface px-4 py-2.5 text-sm text-ink placeholder:text-muted transition-all duration-200 focus:border-accent/40 focus:outline-none focus:shadow-glow"
            placeholder="e.g. penicillin, latex"
          />
        </div>

        {displayError && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl bg-critical-subtle border border-critical/20 px-4 py-2.5 text-sm text-critical font-medium"
            role="alert"
          >
            {displayError}
          </motion.div>
        )}

        <div className="flex items-center gap-3 pt-1">
          <motion.button
            ref={magnetic.ref}
            type="submit"
            disabled={loading}
            whileHover={{ scale: loading ? 1 : 1.02 }}
            whileTap={{ scale: loading ? 1 : 0.98 }}
            style={{ x: magnetic.x, y: magnetic.y }}
            onMouseMove={magnetic.onMouseMove}
            onMouseLeave={magnetic.onMouseLeave}
            className="flex-1 rounded-2xl bg-accent px-6 py-3 text-sm font-semibold text-white shadow-sm transition-all duration-200 hover:bg-accent-hover hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Assessing...' : 'Submit Triage'}
          </motion.button>
          <button
            type="button"
            onClick={handleClear}
            className="rounded-2xl border border-border bg-surface px-5 py-3 text-sm font-medium text-muted transition-all duration-200 hover:text-ink hover:border-ink/20"
          >
            Clear
          </button>
        </div>

      </form>
    </section>
  )
}

function VitalInput({
  label, unit, value, onChange, hint,
}: {
  label: string
  unit: string
  value: number | undefined
  onChange: (v: string) => void
  hint: string
}) {
  const displayValue = value !== undefined ? String(value) : ''
  return (
    <div className="flex flex-col">
      <label className="text-xs font-medium text-muted font-sans mb-1 flex items-baseline gap-1">
        {label}
        <span className="text-[10px] text-muted/60">{unit}</span>
      </label>
      <input
        type="number"
        value={displayValue}
        onChange={e => onChange(e.target.value)}
        className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-ink placeholder:text-muted/40 transition-all duration-200 focus:border-accent/40 focus:outline-none focus:shadow-glow"
        placeholder={hint}
      />
      <span className="text-[10px] text-muted/50 mt-0.5">Norm: {hint}</span>
    </div>
  )
}

function ButtonGroup({
  label, options, value, onChange,
}: {
  label: string
  options: string[]
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div>
      <label className="text-sm font-semibold text-ink font-sans block mb-1.5">{label}</label>
      <div className="flex flex-wrap gap-1.5">
        {options.map(opt => (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(value === opt ? '' : opt)}
            className={'rounded-xl border px-3 py-2 text-xs font-medium transition-all duration-150 ' +
              (value === opt
                ? 'bg-accent text-white border-accent shadow-sm'
                : 'bg-surface text-ink border-border hover:bg-canvas hover:border-accent/30')}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  )
}
