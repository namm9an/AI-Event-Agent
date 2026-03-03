import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b1220",
        slate: "#111d34",
        cyan: "#19d3ff",
        mint: "#53f6c4",
        sand: "#f3eadc",
        ember: "#ff8c5a"
      }
    }
  },
  plugins: []
};

export default config;
