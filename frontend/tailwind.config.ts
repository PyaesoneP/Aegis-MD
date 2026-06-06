import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#ffffff',
        canvas: '#f7f7f8',
        border: '#e8eaed',
        ink: '#131316',
        muted: '#6b7280',
        accent: '#635bff',
        'accent-hover': '#4f46e5',
        'accent-subtle': '#f0efff',
        critical: '#df1b41',
        'critical-subtle': '#fef0f3',
        warning: '#c27200',
        'warning-subtle': '#fef9ee',
        safe: '#007a5e',
        'safe-subtle': '#eef9f5',
        neutral: '#6b7280',
        'neutral-subtle': '#f3f4f6',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(19,19,22,0.04), 0 4px 16px rgba(19,19,22,0.04)',
        'card-hover': '0 1px 2px rgba(19,19,22,0.06), 0 8px 24px rgba(19,19,22,0.06)',
        input: '0 0 0 1px rgba(99,91,255,0.2), 0 0 0 3px rgba(99,91,255,0.1)',
      },
      borderRadius: {
        xl: '0.875rem',
        '2xl': '1rem',
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
      },
      animation: {
        'fade-up': 'fade-up 0.3s ease-out both',
        'fade-in': 'fade-in 0.2s ease-out both',
      },
    },
  },
  plugins: [],
} satisfies Config
