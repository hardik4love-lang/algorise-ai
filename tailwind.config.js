/**
 * Tailwind config for the Algorise web app.
 */
module.exports = {
  content: [
    "./*.html",
    "./compare/*.html",
    "./industry/*.html",
    "./assets/**/*.js",
  ],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      colors: {
        brand: {
          50: "#ecfdf5",
          100: "#d1fae5",
          500: "#10b981",
          600: "#059669",
          700: "#047857",
          cyan: "#00F2FE",
          violet: "#9B5CFF",
          void: "#03050C",
        },
        dark: {
          900: "#0b0f19",
          800: "#111827",
          700: "#1f2937",
          600: "#374151",
        },
      },
    },
  },
  plugins: [],
};
