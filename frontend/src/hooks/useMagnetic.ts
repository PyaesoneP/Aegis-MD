import { useRef } from 'react'
import { useMotionValue, useSpring } from 'framer-motion'

/**
 * Magnetic hover effect — pulls an element toward the cursor.
 * Only active on devices with fine pointer (mouse/trackpad).
 * Respects prefers-reduced-motion.
 */
export function useMagnetic() {
  const ref = useRef<HTMLButtonElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const springX = useSpring(x, { stiffness: 200, damping: 20 })
  const springY = useSpring(y, { stiffness: 200, damping: 20 })

  const reducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches

  const finePointer =
    typeof window !== 'undefined' &&
    window.matchMedia('(pointer: fine)').matches

  const enabled = !reducedMotion && finePointer

  function onMouseMove(e: React.MouseEvent) {
    if (!ref.current || !enabled) return
    const rect = ref.current.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    x.set((e.clientX - cx) * 0.35)
    y.set((e.clientY - cy) * 0.35)
  }

  function onMouseLeave() {
    x.set(0)
    y.set(0)
  }

  return { ref, x: springX, y: springY, onMouseMove, onMouseLeave }
}
