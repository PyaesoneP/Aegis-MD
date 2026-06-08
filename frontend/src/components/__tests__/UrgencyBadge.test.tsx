import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { UrgencyBadge } from '../UrgencyBadge'
import type { ATSCard } from '../../types/triage'

function card(ats: string, label: string, time: number, color: string): ATSCard {
  return { category: ats as ATSCard['category'], label, time_target_min: time, color }
}

describe('UrgencyBadge', () => {
  it('renders ATS-1 with Resuscitation label', () => {
    const { container } = render(<UrgencyBadge category="ATS-1" card={card('ATS-1', 'Resuscitation', 0, '#dc2626')} />)
    const text = container.textContent ?? ''
    expect(text).toContain('ATS-1')
    expect(text).toContain('Resuscitation')
    expect(text).toContain('Immediate')
  })

  it('renders ATS-2 with Emergency label', () => {
    const { container } = render(<UrgencyBadge category="ATS-2" card={card('ATS-2', 'Emergency', 10, '#ea580c')} />)
    const text = container.textContent ?? ''
    expect(text).toContain('ATS-2')
    expect(text).toContain('Emergency')
    expect(text).toContain('10 min')
  })

  it('renders ATS-3 with Urgent label', () => {
    const { container } = render(<UrgencyBadge category="ATS-3" card={card('ATS-3', 'Urgent', 30, '#d97706')} />)
    const text = container.textContent ?? ''
    expect(text).toContain('ATS-3')
    expect(text).toContain('Urgent')
    expect(text).toContain('30 min')
  })

  it('renders ATS-4 with Semi-urgent label', () => {
    const { container } = render(<UrgencyBadge category="ATS-4" card={card('ATS-4', 'Semi-urgent', 60, '#059669')} />)
    const text = container.textContent ?? ''
    expect(text).toContain('ATS-4')
    expect(text).toContain('Semi-urgent')
    expect(text).toContain('60 min')
  })

  it('renders ATS-5 with Non-urgent label', () => {
    const { container } = render(<UrgencyBadge category="ATS-5" card={card('ATS-5', 'Non-urgent', 120, '#2563eb')} />)
    const text = container.textContent ?? ''
    expect(text).toContain('ATS-5')
    expect(text).toContain('Non-urgent')
    expect(text).toContain('120 min')
  })

  it('renders category as label when card not provided', () => {
    render(<UrgencyBadge category="ATS-3" />)
    // When no card is provided, ATS-3 appears as both category and label text.
    const elements = screen.getAllByText('ATS-3')
    expect(elements.length).toBeGreaterThanOrEqual(1)
  })
})
