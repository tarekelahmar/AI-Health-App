/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',
          600: '#0d9488',
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
        },
        health: {
          good: '#10b981',
          caution: '#f59e0b',
          alert: '#ef4444',
          info: '#06b6d4',
          neutral: '#6b7280',
        },
        verdict: {
          helpful: '#10b981',
          not_helpful: '#6b7280',
          unclear: '#f59e0b',
          insufficient: '#9ca3af',
        },
        risk: {
          low: '#10b981',
          moderate: '#f59e0b',
          elevated: '#f97316',
          high: '#ef4444',
        },
        domain: {
          sleep: '#6366f1',
          stress: '#8b5cf6',
          energy: '#f59e0b',
          cardiometabolic: '#ef4444',
          gastrointestinal: '#22c55e',
          inflammation: '#f97316',
          hormonal: '#ec4899',
          cognitive: '#3b82f6',
          musculoskeletal: '#14b8a6',
          nutrition: '#84cc16',
        },
      },
    },
  },
  plugins: [],
}
