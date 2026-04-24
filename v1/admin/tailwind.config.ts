import type { Config } from "tailwindcss";

// Domo Admin Theme — Distinct from frontend "두쫀쿠" warm-dark theme.
// Admin uses a cool slate base with indigo accent for a professional,
// data-dense console look.
const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Legacy tokens (kept for backwards compatibility while we migrate)
        background: "#0F172A",
        surface: {
          DEFAULT: "#1E293B",
          hover: "#293548",
        },
        border: "#334155",
        primary: {
          DEFAULT: "#6366F1",
          hover: "#818CF8",
          muted: "#4338CA",
        },
        text: {
          primary: "#F1F5F9",
          secondary: "#CBD5E1",
          muted: "#94A3B8",
        },
        danger: "#EF4444",
        warning: "#F59E0B",
        success: "#10B981",

        // New admin-namespaced tokens — preferred for new admin UI work
        admin: {
          bg: "#0B1220",          // page background
          surface: "#111A2E",     // cards / sidebar
          "surface-2": "#1A2540", // hover / nested surfaces
          border: "#243049",      // hairline borders
          fg: "#E5EDF7",          // primary text
          "fg-soft": "#A9B6CC",   // secondary text
          muted: "#6B7A95",       // tertiary / hints / labels
          accent: "#6366F1",      // indigo-500 — primary action
          "accent-hover": "#818CF8",
          danger: "#F87171",
          warning: "#FBBF24",
          success: "#34D399",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "Pretendard",
          "-apple-system",
          "BlinkMacSystemFont",
          "system-ui",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
      borderRadius: {
        sm: "4px",
        md: "6px",
        lg: "8px",
        xl: "10px",
      },
      transitionTimingFunction: {
        out: "cubic-bezier(0.16, 1, 0.3, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
