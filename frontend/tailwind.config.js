/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Corporate palette: deep navy brand, refined gold accent, cool ink
        // for body text/borders — restrained, no more than 3 hues.
        brand: {
          light: "#1e2a44",
          DEFAULT: "#111a30", // near-black navy
          dark: "#0a1122",
        },
        accent: {
          light: "#d4b571",
          DEFAULT: "#b8933f", // muted gold, not garish amber
          dark: "#8f6f2a",
        },
        ink: {
          50: "#f7f8fa",
          100: "#eceef2",
          200: "#d7dbe3",
          300: "#b3bac8",
          400: "#8892a6",
          500: "#647087",
          600: "#4a5468",
          700: "#374056",
          800: "#242c3f",
          900: "#151b2b",
        },
      },
      fontFamily: {
        display: ['"Source Serif 4"', "Georgia", "serif"],
        sans: ['"Inter"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
      minHeight: {
        touch: "44px", // WCAG / mobile minimum touch target
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(17 26 48 / 0.04), 0 1px 3px 0 rgb(17 26 48 / 0.06)",
      },
    },
  },
  plugins: [],
};
