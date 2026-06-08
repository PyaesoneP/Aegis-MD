import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TriageForm } from '../TriageForm'
import type { TriageFormData } from '../../types/triage'

describe('TriageForm', () => {
  let onSubmit: ReturnType<typeof vi.fn>
  let onClear: ReturnType<typeof vi.fn>

  beforeEach(() => {
    onSubmit = vi.fn()
    onClear = vi.fn()
  })

  function renderForm(loading = false, apiError: string | null = null) {
    return render(
      <TriageForm onSubmit={onSubmit} onClear={onClear} loading={loading} apiError={apiError} />,
    )
  }

  it('renders the form heading', () => {
    renderForm()
    expect(screen.getByText('ED Triage Intake')).toBeTruthy()
  })

  it('renders chief complaint textarea', () => {
    renderForm()
    expect(screen.getByRole('textbox', { name: /chief complaint/i })).toBeTruthy()
  })

  it('renders age input', () => {
    renderForm()
    expect(screen.getByPlaceholderText('e.g. 65')).toBeTruthy()
  })

  it('renders sex selection buttons', () => {
    renderForm()
    expect(screen.getByRole('button', { name: /^Male$/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /^Female$/i })).toBeTruthy()
  })

  it('renders pain score buttons 0-10', () => {
    renderForm()
    for (let i = 0; i <= 10; i++) {
      expect(screen.getByRole('button', { name: String(i) })).toBeTruthy()
    }
  })

  it('renders submit button', () => {
    renderForm()
    expect(screen.getByRole('button', { name: /submit triage/i })).toBeTruthy()
  })

  it('shows character counter for chief complaint', () => {
    renderForm()
    expect(screen.getByText('0/150')).toBeTruthy()
  })

  it('shows validation error when submitting empty form', async () => {
    renderForm()
    const submit = screen.getByRole('button', { name: /submit triage/i })
    await userEvent.click(submit)

    await waitFor(() => {
      expect(screen.getByText(/chief complaint is required/i)).toBeTruthy()
    })
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('submits when required fields are filled', async () => {
    renderForm()

    const complaint = screen.getByRole('textbox', { name: /chief complaint/i })
    await userEvent.type(complaint, 'chest pain radiating to arm')

    const ageInput = screen.getByPlaceholderText('e.g. 65') as HTMLInputElement
    await userEvent.clear(ageInput)
    await userEvent.type(ageInput, '65')

    const maleBtn = screen.getByRole('button', { name: /^Male$/i })
    await userEvent.click(maleBtn)

    const painBtn = screen.getByRole('button', { name: /^7$/ })
    await userEvent.click(painBtn)

    const submit = screen.getByRole('button', { name: /submit triage/i })
    await userEvent.click(submit)

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1)
    })

    const data: TriageFormData = onSubmit.mock.calls[0][0]
    expect(data.chief_complaint).toBe('chest pain radiating to arm')
    expect(data.age).toBe(65)
    expect(data.sex).toBe('male')
    expect(data.pain_score).toBe(7)
  })

  it('displays API error when provided', () => {
    renderForm(false, 'Server connection failed')
    expect(screen.getByText('Server connection failed')).toBeTruthy()
  })

  it('submit button shows loading state', () => {
    renderForm(true)
    const btn = screen.getByRole('button', { name: /assessing/i })
    expect(btn).toBeTruthy()
    expect(btn).toBeDisabled()
  })

  it('toggles sex selection on second click', async () => {
    renderForm()
    const maleBtn = screen.getByRole('button', { name: /^Male$/i })

    await userEvent.click(maleBtn)
    // After clicking male, the button should have the active class
    // Then click again to deselect
    await userEvent.click(maleBtn)

    // Submit should fail because sex is now empty
    const complaint = screen.getByRole('textbox', { name: /chief complaint/i })
    await userEvent.type(complaint, 'test')

    const ageInput = screen.getByPlaceholderText('e.g. 65') as HTMLInputElement
    await userEvent.clear(ageInput)
    await userEvent.type(ageInput, '30')

    const painBtn = screen.getByRole('button', { name: /^5$/ })
    await userEvent.click(painBtn)

    const submit = screen.getByRole('button', { name: /submit triage/i })
    await userEvent.click(submit)

    await waitFor(() => {
      expect(screen.getByText(/sex is required/i)).toBeTruthy()
    })
  })

  it('calls onClear when clear button is clicked', async () => {
    renderForm()
    const complaint = screen.getByRole('textbox', { name: /chief complaint/i })
    await userEvent.type(complaint, 'test')

    const clearBtn = screen.getByRole('button', { name: /clear/i })
    await userEvent.click(clearBtn)

    expect(onClear).toHaveBeenCalled()
    // Textarea should be cleared
    expect(complaint).toHaveValue('')
  })

  it('shows pregnancy field when female is selected', async () => {
    renderForm()
    // Pregnancy field not visible initially (sex is empty)
    expect(screen.queryByText('Pregnancy')).toBeFalsy()

    const femaleBtn = screen.getByRole('button', { name: /^Female$/i })
    await userEvent.click(femaleBtn)

    await waitFor(() => {
      expect(screen.getByText('Pregnancy')).toBeTruthy()
    })
  })

  it('renders comorbidity checkboxes', () => {
    renderForm()
    expect(screen.getByText('Cardiac disease')).toBeTruthy()
    expect(screen.getByText('Diabetes mellitus')).toBeTruthy()
    expect(screen.getByText('Anticoagulants')).toBeTruthy()
  })
})
