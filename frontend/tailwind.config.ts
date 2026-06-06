import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#ffffff',
        canvas: '#fafaf9',
        border: '#e8e5e2',
        ink: '#0c0a09',
        muted: '#78716c',
        accent: '#635bff',
        'accent-hover': '#4f46e5',
        'accent-subtle': '#f0efff',
        critical: '#e11d48',
        'critical-subtle': '#fef1f4',
        warning: '#d97706',
        'warning-subtle': '#fef9ee',
        safe: '#059669',
        'safe-subtle': '#eef9f5',
        neutral: '#78716c',
        'neutral-subtle': '#f5f4f4',
      },
      fontFamily: {
        display: ['Satoshi', 'sans-serif'],
        sans: ['Inter Variable', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono Variable', 'JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        card: '0 0 0 1px rgba(12,10,9,0.04), 0 1px 2px rgba(12,10,9,0.04), 0 4px 16px rgba(12,10,9,0.04)',
        'card-hover':
          '0 0 0 1px rgba(12,10,9,0.06), 0 1px 2px rgba(12,10,9,0.06), 0 8px 32px rgba(12,10,9,0.08)',
        glass: '0 0 0 1px rgba(255,255,255,0.1) inset, 0 1px 2px rgba(12,10,9,0.06)',
        glow: '0 0 0 1px rgba(99,91,255,0.2), 0 0 0 4px rgba(99,91,255,0.08)',
        input: '0 0 0 1px rgba(99,91,255,0.2), 0 0 0 3px rgba(99,91,255,0.1)',
      },
      borderRadius: {
        xl: '0.75rem',
        '2xl': '1rem',
        '3xl': '1.25rem',
      },
      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        shimmer: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
        breath: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.005)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-4px)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.4s ease-out both',
        'fade-in': 'fade-in 0.3s ease-out both',
        'shimmer': 'shimmer 2.5s ease-in-out infinite',
        'breath': 'breath 4s ease-in-out infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      backgroundImage: {
        noise: "url('/noise.svg')",
      },
    },
  },
  plugins: [],
} satisfies Config
