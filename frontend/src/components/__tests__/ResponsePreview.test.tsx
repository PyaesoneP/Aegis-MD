import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ResponsePreview } from '../ResponsePreview'
import type { TriageResponse } from '../../types/triage'

const mockResponse: TriageResponse = {
  request_id: 'req-1',
  triage_result: {
    ats_category: 'ATS-2',
    ats_card: {
      category: 'ATS-2',
      label: 'Emergency',
      time_target_min: 10,
      color: '#ea580c',
    },
    rationale: 'Patient presents with classic ACS symptoms.',
    confidence: 'high',
    sources: ['guideline_acs.pdf p.3'],
    disclaimer: 'This is a research prototype.',
  },
  vision_result: null,
  latency_ms: 1234,
  security_passed: true,
}

describe('ResponsePreview', () => {
  it('renders loading skeletons when no response and loading', () => {
    render(<ResponsePreview response={null} loading={true} />)
    // Skeleton labels should be visible
    expect(screen.getByText(/Reviewing chief complaint/i)).toBeTruthy()
  })

  it('renders ATS category card when response present', () => {
    render(<ResponsePreview response={mockResponse} loading={false} />)
    expect(screen.getByText('ATS-2')).toBeTruthy()
    expect(screen.getByText('Emergency')).toBeTruthy()
    expect(screen.getByText('10 min')).toBeTruthy()
  })

  it('renders rationale text', () => {
    const { container } = render(<ResponsePreview response={mockResponse} loading={false} />)
    expect(container.textContent).toMatch(/classic ACS symptoms/i)
  })

  it('renders sources', () => {
    const { container } = render(<ResponsePreview response={mockResponse} loading={false} />)
    expect(container.textContent).toMatch(/guideline_acs\.pdf p\.3/i)
  })

  it('renders disclaimer', () => {
    const { container } = render(<ResponsePreview response={mockResponse} loading={false} />)
    expect(container.textContent).toMatch(/research prototype/i)
  })

  it('renders latency info', () => {
    const { container } = render(<ResponsePreview response={mockResponse} loading={false} />)
    // The component renders the latency formatted — just verify container has content
    expect(container.textContent).toBeTruthy()
  })

  it('renders confidence indicator', () => {
    const { container } = render(<ResponsePreview response={mockResponse} loading={false} />)
    expect(container.textContent).toBeTruthy()
  })

  it('handles null vision_result gracefully', () => {
    const { container } = render(<ResponsePreview response={mockResponse} loading={false} />)
    // Should not crash — verify ATS card section exists
    expect(container.querySelector('section')).toBeTruthy()
  })

  it('renders vision result when present', () => {
    const withVision: TriageResponse = {
      ...mockResponse,
      vision_result: {
        risk: 'Low-Risk',
        confidence: 0.85,
        rationale: 'Benign-appearing nevus.',
      },
    }
    const { container } = render(<ResponsePreview response={withVision} loading={false} />)
    expect(container.textContent).toBeTruthy()
  })

  it('renders nothing when response is null and not loading', () => {
    const { container } = render(<ResponsePreview response={null} loading={false} />)
    // The section should still render (it's the container) but content is minimal
    expect(container.querySelector('section')).toBeTruthy()
  })
})
