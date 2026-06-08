// ── ATS Triage Categories (Australasian Triage Scale) ─────────────────
export type ATSCategory = 'ATS-1' | 'ATS-2' | 'ATS-3' | 'ATS-4' | 'ATS-5'

export interface ATSCard {
  category: ATSCategory
  label: string
  time_target_min: number
  color: string
}

export type Confidence = 'low' | 'medium' | 'high'

export type VisionRisk = 'High-Risk' | 'Low-Risk' | 'insufficient confidence'

// ── ED Triage Enums ───────────────────────────────────────────────────
export type Onset = '<1 hour' | '1-6 hours' | '6-24 hours' | '>24 hours'
export type ArrivalMode = 'Ambulatory' | 'Wheelchair' | 'Stretcher' | 'Ambulance'
export type AVPU = 'Alert' | 'Verbal' | 'Pain' | 'Unresponsive'
export type Mechanism = 'Fall' | 'MVA' | 'Assault' | 'Penetrating' | 'Other'
export type PregnancyStatus = 'Yes' | 'No' | 'Unknown'

// ── Data Models ────────────────────────────────────────────────────────

export interface Vitals {
  hr?: number
  rr?: number
  spo2?: number
  temp?: number
  bp_systolic?: number
  bp_diastolic?: number
}

export interface ComorbidityFlags {
  cardiac_disease?: boolean
  diabetes_mellitus?: boolean
  respiratory_disease?: boolean
  immunocompromised?: boolean
  anticoagulants?: boolean
  renal_disease?: boolean
}

/** The form data collected by the ED triage form. */
export interface TriageFormData {
  chief_complaint: string
  vitals: Vitals
  age: number
  sex: 'male' | 'female'
  pain_score: number
  onset?: Onset
  arrival_mode?: ArrivalMode
  consciousness?: AVPU
  mechanism?: Mechanism
  comorbidities: ComorbidityFlags
  pregnancy?: PregnancyStatus
  allergies?: string
  image?: File
}

// ── Response Models ────────────────────────────────────────────────────

export interface TriageResult {
  ats_category: ATSCategory
  ats_card: ATSCard
  rationale: string
  confidence: Confidence
  sources: string[]
  disclaimer: string
}

export interface VisionResult {
  risk: VisionRisk
  confidence?: number
  rationale?: string
}

export interface TriageResponse {
  request_id: string
  triage_result: TriageResult
  vision_result: VisionResult | null
  latency_ms: number
  security_passed: true
}

export interface BlockedResponse {
  error: string
  request_id: string
  security_passed: false
}

// ── Legacy (kept for existing component compatibility during transition) ─
export type Urgency = 'Emergency' | 'Urgent' | 'Routine' | 'Self-Care'

export interface PatientContext {
  age?: number
  sex?: 'male' | 'female'
}
