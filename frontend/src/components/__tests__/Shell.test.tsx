import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

// Mock the API client
vi.mock('../../lib/api', () => ({
  submitTriage: vi.fn(),
}))

import { submitTriage } from '../../lib/api'
import { Shell } from '../Shell'

const mockResponse = {
  request_id: 'req-1',
  triage_result: {
    urgency: 'Urgent',
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

    const textarea = screen.getByRole('textbox', { name: /symptoms/i })
    await userEvent.type(textarea, 'I have chest pain')

    const ageInput = screen.getByPlaceholderText('e.g. 45') as HTMLInputElement
    await userEvent.clear(ageInput)
    await userEvent.type(ageInput, '45')

    const submit = screen.getByRole('button', { name: /submit triage/i })
    userEvent.click(submit)

    // loading state
    expect(submit).toHaveTextContent(/submitting/i)

    // wait for response to be rendered
    await waitFor(() => {
      expect(screen.getByText(/Urgency/i)).toBeInTheDocument()
      expect(screen.getByText(/Test rationale/)).toBeInTheDocument()
    })

    expect(submitTriage).toHaveBeenCalled()
  })
})
