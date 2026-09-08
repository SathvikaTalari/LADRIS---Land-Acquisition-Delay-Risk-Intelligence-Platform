/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#0f1117',
        'bg-secondary': '#161b27',
        'bg-tertiary': '#1c2233',
        'bg-elevated': '#212840',
        'bg-card': '#1a1f30',
        'accent': '#3d7ef5',
        'risk-critical': '#ef4444',
        'risk-high': '#f97316',
        'risk-medium': '#eab308',
        'risk-low': '#22c55e',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
