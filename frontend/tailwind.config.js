/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        zuke: {
          navy: '#1b2a4a',
          'navy-dark': '#121c32',
          'navy-light': '#2e426c',
          orange: '#e97132',
          'orange-hover': '#d65e20',
          teal: '#2b8a7c',
          'teal-light': '#e8f5f3',
          dark: '#222222',
          gray: '#6b6b6b',
          'gray-light': '#f3f4f6',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
