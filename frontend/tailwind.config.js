/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        poker: {
          bg:       "#0F1923",
          surface:  "#162030",
          table:    "#1B5E20",
          felt:     "#2E7D32",
          border:   "#1A3A4A",
          gold:     "#FFD700",
          goldDim:  "#B8860B",
          red:      "#E53935",
          chip:     "#1565C0",
          text:     "#E8EAF0",
          muted:    "#6B7A90",
          glow:     "#00E5FF",
        }
      },
      fontFamily: {
        mono:  ["'JetBrains Mono'", "monospace"],
        poker: ["'Oswald'", "sans-serif"],
      },
      boxShadow: {
        "glow-gold": "0 0 20px rgba(255,215,0,0.4)",
        "glow-cyan": "0 0 20px rgba(0,229,255,0.4)",
        "glow-red":  "0 0 20px rgba(229,57,53,0.5)",
        "table":     "inset 0 0 80px rgba(0,0,0,0.6)",
      },
      animation: {
        "pulse-glow": "pulseGlow 1.5s ease-in-out infinite",
        "thinking":   "thinking 1.2s steps(3) infinite",
        "slide-up":   "slideUp 0.3s ease-out",
        "flip":       "flip 0.5s ease-in-out",
      },
      keyframes: {
        pulseGlow: {
          "0%,100%": { boxShadow: "0 0 8px rgba(0,229,255,0.3)" },
          "50%":     { boxShadow: "0 0 24px rgba(0,229,255,0.8)" },
        },
        thinking: {
          "0%":   { content: "''" },
          "33%":  { content: "'.'" },
          "66%":  { content: "'..'" },
          "100%": { content: "'...'" },
        },
        slideUp: {
          from: { transform: "translateY(20px)", opacity: "0" },
          to:   { transform: "translateY(0)",    opacity: "1" },
        },
        flip: {
          "0%":   { transform: "rotateY(0deg)" },
          "50%":  { transform: "rotateY(90deg)" },
          "100%": { transform: "rotateY(0deg)" },
        },
      },
    },
  },
  plugins: [],
};
