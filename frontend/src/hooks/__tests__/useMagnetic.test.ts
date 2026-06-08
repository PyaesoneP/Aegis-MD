import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useMagnetic } from '../useMagnetic'

describe('useMagnetic', () => {
  it('returns expected shape', () => {
    const { result } = renderHook(() => useMagnetic())

    expect(result.current).toHaveProperty('ref')
    expect(result.current).toHaveProperty('x')
    expect(result.current).toHaveProperty('y')
    expect(result.current).toHaveProperty('onMouseMove')
    expect(result.current).toHaveProperty('onMouseLeave')
    expect(typeof result.current.onMouseMove).toBe('function')
    expect(typeof result.current.onMouseLeave).toBe('function')
  })

  it('x and y are motion values that can be read', () => {
    const { result } = renderHook(() => useMagnetic())

    // MotionValues have a .get() method
    expect(typeof result.current.x.get).toBe('function')
    expect(typeof result.current.y.get).toBe('function')
  })

  it('onMouseLeave does not throw', () => {
    const { result } = renderHook(() => useMagnetic())

    act(() => {
      result.current.onMouseLeave()
    })
    // Should not throw
    expect(true).toBe(true)
  })
})
