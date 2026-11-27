/**
 * Tailwind config for the Algorise web app.
 */
module.exports = {
  content: [
    "./*.html",
    "./algorise-accounting/**/*.html",
    "./algorise-accounting/**/*.js",
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
        guardDark: "#070a13",
        guardNavy: "#0c1322",
        guardSurface: "#131e34",
        guardCard: "#131e34",
        guardCyan: "#06b6d4",
        guardEmerald: "#10b981",
        guardRose: "#f43f5e",
        guardAmber: "#f59e0b",
        guardPurple: "#a855f7",
      },
    },
  },
  plugins: [],
};
