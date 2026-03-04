import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#000000",
        primary: "#19d3ff",
        accent: "#53f6c4",
        sand: "#f2f7ff",
        ember: "#ff7d93",
        // keep old names for dashboard compatibility
        cyan: "#19d3ff",
        mint: "#53f6c4",
        slate: "#111d34",
      },
      fontFamily: {
        display: ["var(--font-display)", "Space Grotesk", "sans-serif"],
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
