/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        'cyber-green': '#00ff88',
        'cyber-cyan': '#00ccff',
        'risk-red': '#ff4444',
        'risk-orange': '#ff8800',
        'bg-dark': '#0a0a0f',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'monospace'],
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        shake: {
          '0%,100%': { transform: 'translateX(0)' },
          '15%,45%,75%': { transform: 'translateX(-7px)' },
          '30%,60%,90%': { transform: 'translateX(7px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-600px 0' },
          '100%': { backgroundPosition: '600px 0' },
        },
        popIn: {
          '0%': { opacity: '0', transform: 'scale(0.8)' },
          '65%': { transform: 'scale(1.05)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        spin: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-8px)', maxHeight: '0' },
          '100%': { opacity: '1', transform: 'translateY(0)', maxHeight: '80px' },
        },
      },
      animation: {
        'fade-up': 'fadeUp 0.6s ease-out forwards',
        'fade-in': 'fadeIn 0.5s ease-out forwards',
        shake: 'shake 0.4s ease-in-out',
        shimmer: 'shimmer 1.5s linear infinite',
        'pop-in': 'popIn 0.4s ease-out forwards',
        spin: 'spin 1s linear infinite',
        'slide-down': 'slideDown 0.3s ease-out forwards',
      },
    },
  },
  plugins: [],
}
