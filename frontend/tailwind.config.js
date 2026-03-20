/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: '#0f1117',
          card: '#1a1d27',
          raised: '#232733',
          hover: '#2a2e3b',
          border: '#2e3345',
        },
        ember: {
          DEFAULT: '#e8590c',
          light: '#ff6b1a',
          dim: '#c44b0a',
          glow: 'rgba(232, 89, 12, 0.15)',
        },
        frost: {
          DEFAULT: '#94a3b8',
          light: '#cbd5e1',
          dim: '#7b93ab',
        },
        gain: '#22c55e',
        loss: '#ef4444',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Cinzel', 'Georgia', 'serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
