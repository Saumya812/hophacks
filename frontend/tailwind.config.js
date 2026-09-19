/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#1a2b4a',
          light: '#243860',
          dark: '#111d33',
          50: '#f2f4f7',
          100: '#e4e9ef',
          200: '#c5d0de',
          300: '#9aadc4',
          400: '#6a84a3',
          500: '#4d6786',
          600: '#3c526d',
          700: '#324359',
          800: '#1a2b4a',
          900: '#111d33',
        },
        cream: '#f8f6f1',
        accent: '#c4973a',
        danger: '#dc2626',
        success: '#16a34a',
        'text-primary': '#111827',
        'text-muted': '#6b7280',
        border: '#e5e7eb',
      },
      fontFamily: {
        display: ['"Playfair Display"', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.08)',
      },
      borderRadius: {
        xl: '12px',
      },
    },
  },
  plugins: [],
}
