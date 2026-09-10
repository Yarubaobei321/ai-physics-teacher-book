/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        yucai: {
          50: '#eef7ff',
          100: '#d8ecff',
          200: '#b7dcff',
          300: '#85c6ff',
          400: '#4ba6ff',
          500: '#177de8',
          600: '#0b63c7',
          700: '#074f9f',
          800: '#0a437f',
          900: '#0d3969'
        },
        ink: '#102033',
        lab: '#f5f8fb',
        signal: '#f4a51c'
      },
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'PingFang SC',
          'Microsoft YaHei',
          'Segoe UI',
          'sans-serif'
        ]
      },
      boxShadow: {
        soft: '0 18px 60px rgba(16, 32, 51, 0.12)'
      }
    }
  },
  plugins: []
};
