---
name: premium-frontend-ui
user-invocable: true
applyTo:
  - frontend/src/components/**
  - frontend/src/**/*.tsx
  - frontend/src/**/*.ts
triggers:
  - craft premium UI
  - build immersive component
  - create award-level design
  - design high-fidelity interface
  - premium polish
description: '**WORKSPACE-SCOPED** — Implementation checklist for crafting immersive, high-performance web experiences with advanced motion, typography, and architectural craftsmanship in Aegis-MD. Use when building premium UI components that demand aesthetic quality, deep interactivity, and flawless performance.'
metadata:
  author: 'Utkarsh Patrikar'
  author_url: 'https://github.com/utkarsh232005'
---

# Premium Frontend UI Craftsmanship

Implementation checklist for building award-level web experiences in Aegis-MD. Apply these standards to every component, page, and interaction that requires premium visual polish, intentional motion, and flawless performance.

## Quick Start: Before You Build

When you receive a request to build premium UI, **do not start coding immediately**. Instead, follow this pre-flight checklist:

1. **[ ] Identify Visual Identity** (Context-Dependent)
   - [ ] Editorial Brutalism (high-contrast, oversized type, sharp edges)
   - [ ] Organic Fluidity (soft gradients, rounded corners, glassmorphism)
   - [ ] Cyber/Technical (dark mode, neon accents, monospace, staggered reveals)
   - [ ] Cinematic Pacing (full-viewport imagery, cross-fades, negative space)
   - *Choose based on component context, not a global standard*

2. **[ ] Confirm Scope**
   - [ ] Single component or full page?
   - [ ] Existing design system to extend or new identity?
   - [ ] Performance constraints (animations, transitions)?
   - [ ] Accessibility requirements (motion preferences, keyboard nav)?

3. **[ ] Plan Motion Architecture**
   - [ ] Entry sequence needed? (preloader, intro animation)
   - [ ] Scroll-driven interactions?
   - [ ] Micro-interactions (hover, cursor tracking, magnetic buttons)?
   - [ ] Performance implications?

---

## Layer 1: The Entry Sequence (Preloading & Initialization)

A blank screen is unacceptable. The user's first interaction must set expectations.

### Implementation Checklist

- **[ ] Preloader Component**
  - [ ] Lightweight asset resolution (fonts, critical images)
  - [ ] Smooth transition away from preloader
  - [ ] Respects `prefers-reduced-motion` setting
  - [ ] Minimal blocking (async/defer critical assets)

- **[ ] Animation Options (choose one)**
  - [ ] Split-door reveal (viewport slides from edges)
  - [ ] Scale-up zoom (preloader scales to reveal page)
  - [ ] Staggered text sweep (animated words reveal content)
  - [ ] Fade transition (simple but effective for accessibility)

### Code Structure (React Example)

```tsx
// Use Framer Motion for React
// - Wrap preloader in AnimatePresence
// - Use transition: { duration: 0.6 } for smooth exit
// - Apply motion.div with initial/animate/exit props
```

---

## Layer 2: Hero Architecture

The top fold must command attention immediately and create visual hierarchy.

### Implementation Checklist

- **[ ] Full-Bleed Container**
  - [ ] Use `100vh` or `100dvh` (dynamic viewport height for mobile)
  - [ ] Ensure overflow is hidden or handled
  - [ ] Test on mobile devices (notches, safe areas)

- **[ ] Typography Engine**
  - [ ] Headline broken into spans (word/character wrapping)
  - [ ] Cascading entrance animations for text chunks
  - [ ] `clamp()` function for fluid scaling (`font-size: clamp(24px, 8vw, 120px)`)
  - [ ] Minimum readable size: body text ≥ 16px

- **[ ] Depth & Layering**
  - [ ] Floating elements with subtle parallax
  - [ ] Background clipping paths for visual interest
  - [ ] Z-index stack clearly documented
  - [ ] Transparency used intentionally (not to hide content)

### Performance Considerations

- **[ ] Only animate `transform` and `opacity`**
- **[ ] Apply `will-change: transform` sparingly**
- **[ ] Remove `will-change` after animation completes**
- **[ ] Test on mid-range devices (Lighthouse score ≥ 85)**

---

## Layer 3: Fluid & Contextual Navigation

Navigation should react to scroll and user context, not sit statically.

### Implementation Checklist

- **[ ] Scroll-Aware Header**
  - [ ] Hide on scroll down, reveal on scroll up
  - [ ] Smooth transitions (not jarring)
  - [ ] Background transitions (transparent → opaque as user scrolls)
  - [ ] Accessible focus management

- **[ ] Rich Hover Interactions**
  - [ ] Mega-menu on hover (display image previews)
  - [ ] Dimensional feedback (scale, rotate, shadow changes)
  - [ ] Only applies on devices with hover capability (`@media (hover: hover)`)
  - [ ] Keyboard navigation fully supported

### Touch/Mobile Considerations

- **[ ] Mobile Menu**
  - [ ] Accessible hamburger button (ARIA labels)
  - [ ] Smooth drawer animation
  - [ ] Close button clearly visible
  - [ ] Body scroll locked while menu open

---

## Layer 4: Motion Design System

Animation is the connective tissue of premium sites. Not an afterthought.

### 4.1 Scroll-Driven Narratives

Use modern scroll libraries to tie animations to user progress:

- **[ ] Pinned Containers**
  - [ ] Section locks into viewport
  - [ ] Secondary content flows past or reveals
  - [ ] Smooth scroll progression
  - [ ] Accessible alternative for reduced-motion

- **[ ] Horizontal Journeys**
  - [ ] Translate vertical scroll into horizontal movement
  - [ ] Gallery/showcase components
  - [ ] Snapping behavior for touch devices

- **[ ] Parallax Mapping**
  - [ ] Varying scroll speeds for background/midground/foreground
  - [ ] Subtle effect (don't overdo—creates nausea on some devices)
  - [ ] Disabled on mobile or reduced-motion setting

**Recommended Libraries:**
- **Primary**: `Framer Motion` (spring physics, gesture handling, most use cases)
- **Secondary**: `@gsap/react` + `gsap/ScrollTrigger` (complex scroll narratives when Framer Motion insufficient)
- **Utility**: `@studio-freight/lenis` (smooth scrolling), `split-type` (text animation)

### 4.2 High-Fidelity Micro-Interactions

The cursor is the user's avatar. Build interactions around it.

- **[ ] Magnetic Components**
  - [ ] Calculate distance: mouse position → button center
  - [ ] Pull button towards cursor dynamically
  - [ ] Smooth interpolation (lerp) for fluid movement
  - [ ] Reset on click or mouse leave

- **[ ] Custom Tracking Cursor**
  - [ ] Follow mouse with calculated lag/easing
  - [ ] Only on devices with precise pointer (`@media (pointer: fine)`)
  - [ ] Fallback to default cursor on touch
  - [ ] Minimal JavaScript (performance critical)

- **[ ] Dimensional Hover States**
  - [ ] Use `transform: scale()`, `rotateX()`, `translate3d()`
  - [ ] Add shadow/glow for depth
  - [ ] Transitions smooth (200-300ms duration)
  - [ ] Accessible keyboard alternative (`:focus-visible`)

**Performance Rule:** Never animate layout-affecting properties (`width`, `height`, `margin`, `top`). Only animate `transform` and `opacity`.

---

## Layer 5: Typography & Visual Texture

Premium UI reflects meticulous typographic craftsmanship.

### Implementation Checklist

- **[ ] Type Hierarchy**
  - [ ] Extreme scale contrast (headlines 8vw-12vw, body 16px-18px)
  - [ ] Font weight variation (bold headlines, regular body, light captions)
  - [ ] Consistent line-height ratios (1.2 headlines, 1.6 body)
  - [ ] Letter-spacing appropriate for size (tighter for small, looser for large)

- **[ ] Font Selection**
  - [ ] Specify variable fonts or premium typefaces
  - [ ] Avoid system defaults for headlines
  - [ ] Load fonts optimally (WOFF2, font-display: swap)
  - [ ] Test on various OS (font rendering varies)

- **[ ] Atmospheric Texture**
  - [ ] Subtle noise overlay (`mix-blend-mode: overlay`, opacity 0.02-0.05)
  - [ ] Removes digital sterility
  - [ ] Adds photographic quality
  - [ ] Performance impact minimal (single layer)

- **[ ] Glassmorphism & Depth**
  - [ ] `backdrop-filter: blur(x)` for frosted-glass effect
  - [ ] Ultra-thin, semi-transparent borders
  - [ ] Consistent opacity strategy (0.7-0.95 range)
  - [ ] Fallback for browsers without backdrop-filter support

### Accessibility Considerations

- **[ ] Color Contrast**
  - [ ] WCAG AA minimum: 4.5:1 for body text
  - [ ] WCAG AA minimum: 3:1 for large text
  - [ ] Test with accessibility tools (axe, WAVE)
  - [ ] Avoid color-only information (use icons + text)

---

## Layer 6: Performance Imperative

A beautiful site that stutters is a failure. Enforce strict guardrails.

### 6.1 Hardware Acceleration Checklist

- **[ ] Layout-Safe Animations**
  - [ ] Animate only `transform` and `opacity`
  - [ ] Avoid animating: `width`, `height`, `top`, `left`, `margin`, `padding`
  - [ ] Use `transform: translate()` instead of `left`/`top`
  - [ ] Use `transform: scale()` instead of `width`/`height`

- **[ ] GPU Compositing**
  - [ ] Apply `will-change: transform` to animated elements
  - [ ] Remove `will-change` after animation finishes
  - [ ] Monitor memory usage on lower-end devices
  - [ ] Limit simultaneous animations (browser CPU/GPU limits)

- **[ ] Render Optimization**
  - [ ] Use `contain` CSS property where applicable
  - [ ] Lazy-load images below the fold
  - [ ] Debounce scroll handlers (throttle to 60fps max)
  - [ ] Profile with DevTools (Performance tab, Lighthouse)

### 6.2 Responsive Degradation

- **[ ] Device Capability Detection**
  ```css
  /* Only apply complex animations on capable devices */
  @media (hover: hover) and (pointer: fine) {
    /* Magnetic buttons, cursor tracking */
  }
  
  @media (prefers-reduced-motion: no-preference) {
    /* Scroll animations, entrance effects */
  }
  
  @media (prefers-color-scheme: dark) {
    /* Dark mode optimizations */
  }
  ```

- **[ ] Testing Checklist**
  - [ ] Desktop performance: Lighthouse ≥ 85
  - [ ] Mobile performance: Lighthouse ≥ 80
  - [ ] Tablet responsiveness at 768px, 1024px breakpoints
  - [ ] Reduced motion: All animations disabled or alternatives provided
  - [ ] Touch devices: No hover-dependent interactions

### 6.3 Accessibility Standards

- **[ ] Motion Preferences**
  - [ ] Respect `prefers-reduced-motion: reduce`
  - [ ] Provide static alternatives for scroll-driven animations
  - [ ] Disable parallax on reduced-motion devices

- **[ ] Keyboard Navigation**
  - [ ] All interactive elements keyboard-accessible
  - [ ] Tab order logical and visible
  - [ ] Focus indicators clear (`:focus-visible`)

- **[ ] ARIA & Semantics**
  - [ ] Proper heading hierarchy (h1, h2, h3...)
  - [ ] Form labels associated with inputs
  - [ ] Image alt text meaningful
  - [ ] Interactive regions have `role`, `aria-label` as needed

---

## Layer 7: Tech Stack & Implementation Ecosystem

Choose tools aligned with Aegis-MD's architecture and audience.

### For React/Vite (Aegis-MD Primary Stack)

**Recommended Packages:**

| Package | Purpose | When to Use |
|---------|---------|------------|
| `framer-motion` | Layout transitions, spring physics, gestures | All animated components | ⭐ Primary |
| `@gsap/react` + `gsap/ScrollTrigger` | Complex scroll narratives | Hero sections, scroll-pinning | Secondary |
| `@studio-freight/lenis` | Smooth scrolling | Full-page scroll experience | Optional |
| `split-type` | Typography chunking | Staggered text animations | Optional |

**Installation:**
```bash
npm install framer-motion gsap @gsap/react @studio-freight/lenis split-type
```

### For Vanilla/Astro (If Needed)

| Package | Purpose |
|---------|---------|
| `gsap` | Timeline sequencing, animations |
| `lenis` (vanilla) | Scroll smoothing |
| `SplitType` (vanilla) | Typography animation |

---

## Quick Implementation Workflow

When building a premium component, follow this order:

1. **Establish Identity** → Choose visual language (Brutalism, Fluidity, Cyber, Cinematic)
2. **Structure HTML** → Semantic, accessible markup with wrapping spans for text animation
3. **Base Styles** → Typography, layout, spacing using Tailwind + custom CSS
4. **Interactions** → Hover states, focus visible, responsive adjustments
5. **Scroll Animations** → ScrollTrigger/Framer Motion for entrance, parallax, pinning
6. **Polish** → Micro-interactions, cursor effects, noise overlays
7. **Test** → Lighthouse, reduced-motion, touch devices, keyboard nav

---

## Example Prompts to Trigger This Skill

```
"Craft a premium hero section for the Aegis-MD dashboard"
"Build an immersive component with scroll-driven animations"
"Design a high-fidelity triage form with polished interactions"
"Create an award-level landing page for the application"
"Add premium motion design to the Shell component"
```

---

## Sequential Workflow: Build → Review → Iterate

This skill is **Step 1** of a multi-step process:

1. **Build Premium UI** (this skill) → Implement component with checklists
2. **Review Design** (web-design-reviewer skill) → Visual inspection for issues
3. **Fix Issues** → Apply corrections based on review findings
4. **Verify** → Re-screenshot to confirm fixes

**After completing this workflow, consider:**

- **accessibility-audit** — Deep WCAG compliance checks with automated tools
- **performance-optimization** — Lighthouse score improvement, bundle analysis
- **frontend-testing** — E2E tests for interactive components

---

## Key Principles (Reminder)

- ✅ **Every interaction intentional** — No accidental, purposeless animation
- ✅ **Performance first** — Beautiful sites that stutter are failures
- ✅ **Accessibility built-in** — Not retrofitted, not an afterthought
- ✅ **Responsive by default** — Mobile-first, then enhance for larger screens
- ✅ **Motion respects preferences** — `prefers-reduced-motion` always honored

---

## Troubleshooting

### Animations Jank/Stutter

- [ ] Check DevTools Performance tab for layout recalculation
- [ ] Ensure only `transform` and `opacity` are animated
- [ ] Verify `will-change` is applied appropriately
- [ ] Test on actual mobile device (simulator can be misleading)

### Styles Not Applying

- [ ] Check CSS specificity (Tailwind classes may conflict)
- [ ] Verify CSS-in-JS override priorities
- [ ] Inspect element in DevTools
- [ ] Clear cache and rebuild

### Performance Score Low

- [ ] Reduce simultaneous animations
- [ ] Lazy-load images
- [ ] Split code by route
- [ ] Profile with Lighthouse in DevTools

### Accessibility Warnings

- [ ] Test with screen reader (NVDA, JAWS, VoiceOver)
- [ ] Use axe DevTools extension
- [ ] Verify keyboard navigation
- [ ] Check color contrast ratios
