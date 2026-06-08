import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PageIntro } from '../PageIntro'

describe('PageIntro', () => {
  it('renders the Aegis-MD heading', () => {
    const onComplete = vi.fn()
    render(<PageIntro onComplete={onComplete} />)
    expect(screen.getByText('Aegis-MD')).toBeTruthy()
  })

  it('renders a h1 element', () => {
    const onComplete = vi.fn()
    const { container } = render(<PageIntro onComplete={onComplete} />)
    expect(container.querySelector('h1')).toBeTruthy()
  })

  it('calls onComplete in reduced motion path', async () => {
    vi.useFakeTimers()
    const onComplete = vi.fn()
    render(<PageIntro onComplete={onComplete} />)
    vi.advanceTimersByTime(2000)
    expect(onComplete).toHaveBeenCalled()
    vi.useRealTimers()
  })
})
