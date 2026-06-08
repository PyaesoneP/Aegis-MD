import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NoiseOverlay } from '../NoiseOverlay'

describe('NoiseOverlay', () => {
  it('renders without crashing', () => {
    const { container } = render(<NoiseOverlay />)
    expect(container.firstChild).toBeTruthy()
  })

  it('renders a div with noise-overlay class', () => {
    const { container } = render(<NoiseOverlay />)
    expect(container.querySelector('.noise-overlay')).toBeTruthy()
  })
})
