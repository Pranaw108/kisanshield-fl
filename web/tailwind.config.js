/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        // KisanShield-FL palette — deep green + warm paper, not SVS's blue brand:
        // this is an agri-tech product with its own identity.
        paper: { DEFAULT: "#f6f4ee", dark: "#12160f" },
        card: { DEFAULT: "#ffffff", dark: "#1b2118" },
        ink: { DEFAULT: "#1c2318", soft: "#4b5443", dark: "#edf1e8", darksoft: "#b7c0ad" },
        muted: { DEFAULT: "#7a8171", dark: "#8b9480" },
        line: { DEFAULT: "#e1ddd0", dark: "#2c3327" },
        brand: { DEFAULT: "#1f5d3f", dark: "#5fb98a", ink: "#ffffff", darkink: "#0c1a11" },
        amber: { DEFAULT: "#a3651c", soft: "#fbeedd", dark: "#e0a862", darksoft: "#2c2416" },
        danger: { DEFAULT: "#9b3b3b", soft: "#fbe9e7", dark: "#e2938c", darksoft: "#2c1c1a" },
      },
      fontFamily: {
        display: ["Georgia", "Times New Roman", "ui-serif", "serif"],
        body: ["system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      borderRadius: { xl2: "16px" },
    },
  },
  plugins: [],
};
