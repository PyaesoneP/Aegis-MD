import React from 'react'
import '@testing-library/jest-dom'

// Make React globally available for jsdom
;(globalThis as Record<string, unknown>).React = React

// Mock window.matchMedia (not available in jsdom)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

// Mock ResizeObserver (not available in jsdom — needed by Lenis)
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
;(globalThis as Record<string, unknown>).ResizeObserver = ResizeObserverMock

// Mock Element.scrollIntoView (not available in jsdom)
Element.prototype.scrollIntoView = () => {}

// Mock window.scrollTo (not available in jsdom)
window.scrollTo = () => {}

// Mock URL.createObjectURL / revokeObjectURL (needed by TriageForm image preview)
if (!URL.createObjectURL) {
  // Vitest/jsdom may not have this — stub it
  ;(URL as unknown as Record<string, unknown>).createObjectURL = () => 'blob:mock'
  ;(URL as unknown as Record<string, unknown>).revokeObjectURL = () => {}
}
