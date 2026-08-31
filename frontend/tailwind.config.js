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
        tiktok: {
          red: "#FE2C55",
          redHover: "#E02449",
          cyan: "#25F4EE",
          cyanHover: "#1FE0DA",
          dark: "#0B0E14",
          surface: "#121622",
          card: "#161B26",
          cardHover: "#1F2636",
          border: "rgba(255, 255, 255, 0.08)",
          borderHover: "rgba(254, 44, 85, 0.3)",
        }
      },
      fontFamily: {
        kanit: ['Kanit', 'sans-serif'],
        prompt: ['Prompt', 'sans-serif'],
        inter: ['Inter', 'sans-serif'],
      },
      boxShadow: {
        'neon-red': '0 0 20px rgba(254, 44, 85, 0.45)',
        'neon-cyan': '0 0 20px rgba(37, 244, 238, 0.45)',
        'card-glow': '0 10px 30px rgba(0, 0, 0, 0.45)',
      }
    },
  },
  plugins: [],
}
