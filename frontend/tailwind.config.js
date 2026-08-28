/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ignite: {
          50: '#fff7ed',
          100: '#ffedd5',
          500: '#f97316',
          600: '#ea580c',
          700: '#c2410c',
          900: '#7c2d12',
        },
        ink: {
          DEFAULT: '#1A2332',
          soft: '#4B5566',
        },
        muted: '#847C6E',
        surface: '#FFFFFF',
        paper: '#FAF8F4',
        line: {
          DEFAULT: '#E7E1D6',
          soft: '#F0ECE3',
        },
        flame: {
          DEFAULT: '#E8622C',
          soft: '#FDEEE6',
          line: '#F3CBB4',
          deep: '#C2410C',
        },
        good: {
          DEFAULT: '#2F7D5C',
          soft: '#E9F3EE',
          line: '#BFDBCC',
        },
        watch: {
          DEFAULT: '#AD7B1F',
          soft: '#FBF2DF',
          line: '#EBD69E',
        },
        critical: {
          DEFAULT: '#C4432B',
          soft: '#FBEAE5',
          line: '#EFC0B2',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Manrope', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(26,35,50,0.04), 0 4px 16px rgba(26,35,50,0.05)',
      },
    },
  },
  plugins: [],
}
