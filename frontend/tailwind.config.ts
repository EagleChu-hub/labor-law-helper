import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "var(--canvas)",
        card: "var(--card)",
        line: "var(--line)",
        ink: "var(--ink)",
        muted: "var(--muted)",
        navy: {
          DEFAULT: "var(--navy)",
          50: "var(--navy-50)",
          100: "var(--navy-100)",
          600: "var(--navy-600)",
          700: "var(--navy)",
          800: "var(--navy-800)",
          900: "var(--navy-900)",
        },
        gold: {
          DEFAULT: "var(--gold)",
          deep: "var(--gold-deep)",
          soft: "var(--gold-soft)",
          border: "var(--gold-border)",
        },
        danger: {
          DEFAULT: "var(--red)",
          deep: "var(--red-deep)",
          soft: "var(--red-soft)",
          border: "var(--red-border)",
        },
        warn: {
          DEFAULT: "var(--amber)",
          soft: "var(--amber-soft)",
          border: "var(--amber-border)",
        },
        ok: {
          DEFAULT: "var(--green)",
          soft: "var(--green-soft)",
          border: "var(--green-border)",
        },
      },
      fontFamily: {
        sans: ["var(--font-noto)", "sans-serif"],
        sora: ["var(--font-sora)", "sans-serif"],
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
export default config;
