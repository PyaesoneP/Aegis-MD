import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TriageHeader } from '../TriageHeader'

// Mock the API_BASE_URL import
vi.mock('../../lib/api', () => ({
  API_BASE_URL: 'http://test-api.local',
}))

describe('TriageHeader', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the title', () => {
    render(<TriageHeader />)
    expect(screen.getByText('Aegis-MD')).toBeTruthy()
  })

  it('renders a link to the API', () => {
    const { container } = render(<TriageHeader />)
    // The header shows the API_BASE_URL somewhere
    expect(container.textContent).toContain('http://test-api.local')
  })

  it('renders without crashing', () => {
    const { container } = render(<TriageHeader />)
    expect(container).toBeTruthy()
  })
})
