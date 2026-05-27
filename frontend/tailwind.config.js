/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f9f4',
          100: '#dcf2e4',
          500: '#2e7d55',
          600: '#256647',
          700: '#1b4f37',
          900: '#0d2b1e',
        },
      },
    },
  },
  plugins: [],
}
