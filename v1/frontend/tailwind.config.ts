import type { Config } from "tailwindcss";

// Domo "두쫀쿠" Theme
// Reference: docs/01-plan/design-direction.md, docs/02-design/design.md §11
const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#1A1410",
        surface: {
          DEFAULT: "#2A2018",
          hover: "#352821",
        },
        border: "#3D2F24",
        primary: {
          DEFAULT: "#A8D76E",
          hover: "#BDE284",
          muted: "#5E7A3E",
        },
        text: {
          primary: "#F5EFE4",
          secondary: "#B5A99A",
          muted: "#7A6F60",
        },
        danger: "#E85D5D",
        warning: "#F0B14A",
        success: "#A8D76E",
      },
      fontFamily: {
        sans: [
          "Pretendard",
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "system-ui",
          "sans-serif",
        ],
      },
      borderRadius: {
        sm: "4px",
        md: "8px",
        lg: "12px",
        xl: "16px",
      },
      spacing: {
        // Default scale already covers 4/8/12/16/24/32/48/64
      },
      transitionTimingFunction: {
        out: "cubic-bezier(0.16, 1, 0.3, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
