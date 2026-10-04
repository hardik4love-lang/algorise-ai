/**
 * Tailwind config for the Algorise web app.
 *
 * The pages previously loaded the Tailwind Play CDN, which ships ~407 KB of
 * compiler and generates the stylesheet IN THE BROWSER. On a slow connection
 * that means the page renders unstyled for seconds, which reads as a broken
 * page. Worse, cdn.tailwindcss.com is deprecated.
 *
 * Styles are now compiled here, at build time, into one small static file.
 * No runtime compiler, no CDN dependency.
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
      },
      colors: {
        brand: {
          50: "#ecfdf5",
          100: "#d1fae5",
          500: "#10b981",
          600: "#059669",
          700: "#047857",
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
