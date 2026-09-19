/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#1a2b4a',
          50: '#f2f4f7',
          100: '#e4e9ef',
          200: '#c5d0de',
          300: '#9aadc4',
          400: '#6a84a3',
          500: '#4d6786',
          600: '#3c526d',
          700: '#324359',
          800: '#1a2b4a',
          900: '#121e33',
        },
      },
      fontFamily: {
        display: ['"Fraunces"', 'Georgia', 'serif'],
        sans: ['"Source Sans 3"', 'Segoe UI', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
