/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    extend: {
      colors: {
        linen: {
          50: "#FDFDFB",
          100: "#FAFAF7",
          200: "#F5F5F0",
          300: "#EDEDE6",
          400: "#E3E3DA",
          500: "#D6D6CC",
        },
        earth: {
          50: "#F5F0EB",
          100: "#EDE5DC",
          200: "#DDD1C3",
          300: "#C4A882",
          400: "#A8917A",
          500: "#8B7A68",
          600: "#7A7267",
          700: "#5C4B3F",
          800: "#4A3D33",
          900: "#3A3632",
        },
        moss: {
          50: "#F2F5F0",
          100: "#E4EBE0",
          200: "#C8D6C1",
          300: "#A7B99D",
          400: "#8B9A7F",
          500: "#6E7D63",
          600: "#576450",
          700: "#3F4A39",
        },
        mist: {
          50: "#F0F4F7",
          100: "#E0E9EF",
          200: "#C1D3DF",
          300: "#A0B4C2",
          400: "#8299AA",
          500: "#657F92",
          600: "#4D6575",
        },
        clay: {
          50: "#F7F1EA",
          100: "#EFE3D5",
          200: "#DFC7AB",
          300: "#C4A882",
          400: "#A98D68",
          500: "#8E7452",
        },
        charcoal: "#3A3632",
        stone: { DEFAULT: "#A8A8A8", light: "#C5C5C0", dark: "#7A7A76" },
        "rose-earth": "#B89B8F",
      },
      fontFamily: {
        serif: ['"Crimson Text"', '"Noto Serif JP"', "Georgia", "serif"],
        body: ['"Crimson Text"', "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        jp: ['"Noto Serif JP"', "serif"],
      },
      borderRadius: {
        wabi: "0.375rem 0.5rem 0.325rem 0.45rem",
        "wabi-lg": "0.5rem 0.75rem 0.45rem 0.625rem",
        "wabi-xl": "0.75rem 1rem 0.625rem 0.875rem",
      },
      boxShadow: {
        wabi: "0 2px 8px rgba(92, 75, 63, 0.06), 0 1px 3px rgba(92, 75, 63, 0.04)",
        "wabi-hover": "0 4px 16px rgba(92, 75, 63, 0.08), 0 2px 6px rgba(92, 75, 63, 0.05)",
        "wabi-lg": "0 8px 24px rgba(92, 75, 63, 0.08), 0 4px 12px rgba(92, 75, 63, 0.04)",
        "wabi-inner": "inset 0 1px 3px rgba(92, 75, 63, 0.06)",
        ink: "0 1px 2px rgba(58, 54, 50, 0.06)",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        mistReveal: {
          "0%": { opacity: "0", filter: "blur(8px)" },
          "100%": { opacity: "1", filter: "blur(0)" },
        },
        inkFill: {
          "0%": { width: "0%" },
          "100%": { width: "var(--fill-width, 100%)" },
        },
        breathe: {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        "fade-up": "fadeUp 0.6s ease-out forwards",
        "fade-in": "fadeIn 0.5s ease-out forwards",
        "mist-reveal": "mistReveal 0.8s ease-out forwards",
        "ink-fill": "inkFill 1s ease-out forwards",
        breathe: "breathe 3s ease-in-out infinite",
      },
      spacing: {
        18: "4.5rem",
        22: "5.5rem",
        88: "22rem",
        128: "32rem",
      },
      maxWidth: {
        prose: "65ch",
      },
      transitionTimingFunction: {
        wabi: "cubic-bezier(0.25, 0.1, 0.25, 1)",
      },
    },
  },
  plugins: [],
};
