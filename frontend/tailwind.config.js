/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Restrained 3-color palette: deep navy brand, warm amber accent.
        brand: {
          DEFAULT: "#1e293b", // slate-800
          dark: "#0f172a",    // slate-900
        },
        accent: {
          DEFAULT: "#f59e0b", // amber-500
          dark: "#d97706",
        },
      },
      minHeight: {
        touch: "44px", // WCAG / mobile minimum touch target
      },
    },
  },
  plugins: [],
};
