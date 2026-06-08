import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CursorGlow } from '../CursorGlow'

describe('CursorGlow', () => {
  it('renders without crashing (may render null in jsdom without fine pointer)', () => {
    const { container } = render(<CursorGlow />)
    // In jsdom, matchMedia('pointer: fine') is false, so the component
    // renders nothing. This is expected behavior — just verify no crash.
    expect(container).toBeTruthy()
  })
})
