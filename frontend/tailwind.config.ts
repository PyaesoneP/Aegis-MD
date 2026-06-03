import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        clinical: {
          ink: '#17201f',
          paper: '#f7faf9',
          line: '#dbe7e2',
          teal: '#0f766e',
          mint: '#d9f5ed',
          amber: '#b7791f',
          rose: '#be123c',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        panel: '0 10px 30px rgba(23, 32, 31, 0.08)',
      },
    },
  },
  plugins: [],
} satisfies Config
