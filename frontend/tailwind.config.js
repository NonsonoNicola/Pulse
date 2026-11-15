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
        crew: {
          elena: '#5eead4',
          maya: '#a78bfa',
          luca: '#fbbf24',
          aiko: '#f472b6',
        },
        status: {
          green: '#22c55e',
          yellow: '#eab308',
          orange: '#f97316',
          red: '#ef4444',
          gray: '#9ca3af',
        },
      },
    },
  },
  plugins: [],
}