/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#3d4a5c',
          light: '#5a6878',
          dark: '#2c3542',
          50: '#eef1f4',
          100: '#e4e8ec',
        },
        misty: '#e8ece8',
        mist: '#e8ece8',
        cream: '#f7f4ef',
        stone: '#ebe6de',
        sage: '#8a9a8b',
        ink: '#3a3835',
        gold: '#a8906e',
        accent: '#a8906e',
        danger: '#dc2626',
        success: '#5f8f6b',
        'text-primary': '#3a3835',
        'text-muted': '#8a857c',
        border: '#e2ddd4',
      },
      fontFamily: {
        display: ['"Playfair Display"', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 3px rgba(58, 56, 53, 0.06)',
        nav: '0 1px 0 rgba(58, 56, 53, 0.06)',
        gallery: '0 8px 24px rgba(58, 56, 53, 0.1)',
        modal: '0 24px 64px rgba(0,0,0,0.2)',
        frame: '0 2px 8px rgba(0,0,0,0.12)',
      },
      borderRadius: {
        xl: '12px',
      },
    },
  },
  plugins: [],
}
