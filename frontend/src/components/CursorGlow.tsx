import { useEffect, useRef } from 'react'

/**
 * Ambient cursor glow — a large radial gradient that follows the cursor.
 * Only renders on devices with a fine pointer (mouse/trackpad).
 * Respects prefers-reduced-motion.
 */
export function CursorGlow() {
  const glowRef = useRef<HTMLDivElement>(null)
  const rafRef = useRef<number>(0)
  const target = useRef({ x: -500, y: -500 })
  const current = useRef({ x: -500, y: -500 })

  const enabled =
    typeof window !== 'undefined' &&
    window.matchMedia('(pointer: fine)').matches &&
    !window.matchMedia('(prefers-reduced-motion: reduce)').matches

  useEffect(() => {
    if (!enabled || !glowRef.current) return

    const el = glowRef.current

    function onMove(e: MouseEvent) {
      target.current.x = e.clientX
      target.current.y = e.clientY
    }

    function animate() {
      // Lerp toward target for smooth trailing
      current.current.x += (target.current.x - current.current.x) * 0.06
      current.current.y += (target.current.y - current.current.y) * 0.06
      el.style.transform = `translate(${current.current.x - 200}px, ${current.current.y - 200}px)`
      rafRef.current = requestAnimationFrame(animate)
    }

    window.addEventListener('mousemove', onMove, { passive: true })
    rafRef.current = requestAnimationFrame(animate)

    return () => {
      window.removeEventListener('mousemove', onMove)
      cancelAnimationFrame(rafRef.current)
    }
  }, [enabled])

  if (!enabled) return null

  return (
    <div
      ref={glowRef}
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-40"
      style={{
        width: 400,
        height: 400,
        borderRadius: '50%',
        background:
          'radial-gradient(circle, rgba(99,91,255,0.05) 0%, transparent 70%)',
        willChange: 'transform',
      }}
    />
  )
}
