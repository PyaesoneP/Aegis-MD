import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SkeletonCard } from '../SkeletonCard'

describe('SkeletonCard', () => {
  it('renders the label text', () => {
    render(<SkeletonCard label="Loading data…" />)
    expect(screen.getByText('Loading data…')).toBeTruthy()
  })

  it('renders default 2 shimmer lines', () => {
    const { container } = render(<SkeletonCard label="Test" />)
    const lines = container.querySelectorAll('[aria-hidden="true"] span')
    expect(lines).toHaveLength(2)
  })

  it('renders custom number of lines', () => {
    const { container } = render(<SkeletonCard label="Test" lines={4} />)
    const lines = container.querySelectorAll('[aria-hidden="true"] span')
    expect(lines).toHaveLength(4)
  })

  it('accepts custom className', () => {
    const { container } = render(<SkeletonCard label="Test" className="custom-cls" />)
    expect(container.firstChild).toHaveClass('custom-cls')
  })
})
