import React from 'react'
import { describe, beforeEach, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock the API client
vi.mock('../../lib/api', () => ({
  API_BASE_URL: 'http://test-api.local',
  submitTriage: vi.fn(),
  ApiError: class ApiError extends Error {},
}))

import { submitTriage } from '../../lib/api'
import { Shell } from '../Shell'

const mockResponse = {
  request_id: 'req-1',
  triage_result: {
    ats_category: 'ATS-2',
    ats_card: { category: 'ATS-2', label: 'Emergency', time_target_min: 10, color: '#ea580c' },
    rationale: 'Test rationale',
    confidence: 'high',
    sources: ['source1'],
    disclaimer: 'Test disclaimer',
  },
  vision_result: null,
  latency_ms: 123,
  security_passed: true,
}

describe('Shell component', () => {
  beforeEach(() => {
    ;(submitTriage as unknown as vi.Mock).mockReset()
  })

  it('submits form and displays response', async () => {
    ;(submitTriage as unknown as vi.Mock).mockResolvedValue(mockResponse)

    render(<Shell />)

    const textarea = screen.getByRole('textbox', { name: /chief complaint/i })
    await userEvent.type(textarea, 'I have chest pain')

    const ageInput = screen.getByPlaceholderText('e.g. 65') as HTMLInputElement
    await userEvent.clear(ageInput)
    await userEvent.type(ageInput, '65')

    // Select sex (male button)
    const maleBtn = screen.getByRole('button', { name: /^Male$/i })
    await userEvent.click(maleBtn)

    // Select pain score
    const painBtn = screen.getByRole('button', { name: /^7$/ })
    await userEvent.click(painBtn)

    const submit = screen.getByRole('button', { name: /submit triage/i })
    await userEvent.click(submit)

    // wait for response to be rendered
    await waitFor(() => {
      expect(screen.getByText(/ATS Category/i)).toBeTruthy()
      expect(screen.getByText(/Test rationale/)).toBeTruthy()
    })

    expect(submitTriage).toHaveBeenCalled()
  })
})
