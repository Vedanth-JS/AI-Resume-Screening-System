/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#EEF1F7',
          100: '#D4DBEB',
          200: '#A9B7D7',
          300: '#7E93C3',
          400: '#536FAF',
          500: '#2B4FA0',
          600: '#1A3580',
          700: '#0F1E3C',
          800: '#0A1528',
          900: '#060D18',
        },
        cream: '#F8F6F1',
        accent: '#C9A84C',
      },
      fontFamily: {
        serif: ['"Playfair Display"', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'card': '0 2px 16px 0 rgba(15,30,60,0.08)',
        'card-hover': '0 8px 32px 0 rgba(15,30,60,0.16)',
        'modal': '0 24px 64px 0 rgba(15,30,60,0.24)',
      },
    },
  },
  plugins: [],
}
