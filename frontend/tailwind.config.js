/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        claude: {
          bg: "#181716",
          surface: "#232220",
          surfaceSubtle: "#1C1B19",
          surfaceHover: "#2C2B27",
          border: "#363430",
          borderSubtle: "#2E2C29",
          text: "#EDE9E3",
          textMuted: "#9C968F",
          textLight: "#6E6A64",
          accent: "#D97757",
          accentHover: "#C2683D",
          accentSoft: "#33251F",
          accentBorder: "#52352B",
        },
        tiktok: {
          red: "#D97757",
          redHover: "#C2683D",
          cyan: "#4E9F76",
          cyanHover: "#3D825F",
          dark: "#181716",
          surface: "#232220",
          card: "#232220",
          cardHover: "#2C2B27",
          border: "#363430",
          borderHover: "#D97757",
        }
      },
      fontFamily: {
        heading: ['Prompt', 'Inter', 'sans-serif'],
        serif: ['Prompt', 'Inter', 'sans-serif'],
        sans: ['Inter', 'Prompt', 'system-ui', 'sans-serif'],
        prompt: ['Prompt', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'subtle': '0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.2)',
        'card': '0 2px 8px -2px rgba(0, 0, 0, 0.4), 0 1px 4px -1px rgba(0, 0, 0, 0.3)',
        'elevated': '0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.4)',
        'terracotta': '0 4px 14px 0 rgba(217, 119, 87, 0.3)',
      }
    },
  },
  plugins: [],
}
