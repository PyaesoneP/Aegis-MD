import { useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { PageIntro } from './components/PageIntro'
import { Shell } from './components/Shell'

export default function App() {
  const [showIntro, setShowIntro] = useState(true)

  return (
    <AnimatePresence mode="wait">
      {showIntro ? (
        <PageIntro key="intro" onComplete={() => setShowIntro(false)} />
      ) : (
        <Shell key="shell" />
      )}
    </AnimatePresence>
  )
}
