export type Urgency = 'Emergency' | 'Urgent' | 'Routine' | 'Self-Care'

export type Confidence = 'low' | 'medium' | 'high'

export type VisionRisk = 'High-Risk' | 'Low-Risk' | 'insufficient confidence'

export interface PatientContext {
  age?: number
  sex?: 'male' | 'female'
}

export interface TriageRequest {
  symptoms: string
  patientContext?: PatientContext
  image?: File
}

export interface TriageResult {
  urgency: Urgency
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
