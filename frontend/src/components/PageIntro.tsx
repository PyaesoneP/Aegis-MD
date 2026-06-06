import { useEffect, useRef } from 'react'
import SplitType from 'split-type'
import { motion } from 'framer-motion'

interface PageIntroProps {
  onComplete: () => void
}

export function PageIntro({ onComplete }: PageIntroProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  const hasReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches

  useEffect(() => {
    if (hasReducedMotion) {
      const t = setTimeout(onComplete, 200)
      return () => clearTimeout(t)
    }

    if (!headingRef.current) return

    // Split heading text into characters
    const split = new SplitType(headingRef.current, { types: 'chars' })
    const chars = split.chars ?? []

    // Set initial state on all chars
    chars.forEach((char) => {
      char.style.opacity = '0'
      char.style.transform = 'translateY(16px)'
    })

    // Stagger reveal each character
    chars.forEach((char, i) => {
      setTimeout(() => {
        char.style.transition = 'opacity 0.3s ease-out, transform 0.4s ease-out'
        char.style.opacity = '1'
        char.style.transform = 'translateY(0)'
      }, i * 25)
    })

    // Complete after all chars revealed + hold
    const totalDelay = chars.length * 25 + 1200
    const t = setTimeout(onComplete, totalDelay)
    return () => clearTimeout(t)
  }, [hasReducedMotion, onComplete])

  return (
    <motion.div
      className="fixed inset-0 z-100 flex items-center justify-center bg-canvas"
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5, ease: 'easeInOut' }}
    >
      <div className="text-center px-6">
        <p
          className="text-xs font-semibold uppercase tracking-[0.2em] text-muted font-display animate-fade-in"
          style={{ animationDelay: '0.6s', animationFillMode: 'both' }}
        >
          Aegis-MD
        </p>
        <h1
          ref={headingRef}
          className="mt-4 text-3xl font-bold tracking-tight text-ink font-display sm:text-4xl lg:text-5xl text-balance"
        >
          Multimodal Triage Console
        </h1>
      </div>
    </motion.div>
  )
}
