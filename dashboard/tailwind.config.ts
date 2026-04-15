import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",

  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background) / <alpha-value>)",
        surface: "hsl(var(--surface) / <alpha-value>)",
        elevated: "hsl(var(--elevated) / <alpha-value>)",
        sidebar: "hsl(var(--sidebar) / <alpha-value>)",

        foreground: "hsl(var(--foreground) / <alpha-value>)",
        "foreground-secondary": "hsl(var(--foreground-secondary) / <alpha-value>)",
        muted: "hsl(var(--muted) / <alpha-value>)",

        border: "hsl(var(--border) / <alpha-value>)",
        "border-subtle": "hsl(var(--border-subtle) / <alpha-value>)",

        accent: {
          DEFAULT: "hsl(var(--accent) / <alpha-value>)",
          foreground: "hsl(var(--accent-foreground) / <alpha-value>)",
        },

        success: {
          DEFAULT: "hsl(var(--success) / <alpha-value>)",
          muted: "hsl(var(--success) / 0.1)",
        },
        warning: {
          DEFAULT: "hsl(var(--warning) / <alpha-value>)",
          muted: "hsl(var(--warning) / 0.1)",
        },
        error: {
          DEFAULT: "hsl(var(--error) / <alpha-value>)",
          muted: "hsl(var(--error) / 0.1)",
        },
        info: {
          DEFAULT: "hsl(var(--info) / <alpha-value>)",
          muted: "hsl(var(--info) / 0.1)",
        },

        channel: {
          email: "hsl(var(--channel-email) / <alpha-value>)",
          sms: "hsl(var(--channel-sms) / <alpha-value>)",
          seo: "hsl(var(--channel-seo) / <alpha-value>)",
          ad: "hsl(var(--channel-ad) / <alpha-value>)",
        },

        confidence: {
          low: "hsl(var(--confidence-low) / <alpha-value>)",
          medium: "hsl(var(--confidence-medium) / <alpha-value>)",
          high: "hsl(var(--confidence-high) / <alpha-value>)",
        },

        agent: {
          idle: "hsl(var(--agent-idle) / <alpha-value>)",
          thinking: "hsl(var(--agent-thinking) / <alpha-value>)",
          error: "hsl(var(--agent-error) / <alpha-value>)",
        },
      },

      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
          "Apple Color Emoji",
          "Segoe UI Emoji",
        ],
        display: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "Liberation Mono",
          "Courier New",
          "monospace",
        ],
      },

      fontSize: {
        kpi: ["2.5rem", { lineHeight: "1", fontWeight: "600", letterSpacing: "-0.025em" }],
        "kpi-sm": ["1.75rem", { lineHeight: "1", fontWeight: "600", letterSpacing: "-0.02em" }],
        "chart-label": ["0.6875rem", { lineHeight: "1", fontWeight: "500" }],
        "chart-value": ["0.75rem", { lineHeight: "1.2", fontWeight: "600" }],
        badge: ["0.6875rem", { lineHeight: "1.25", fontWeight: "500" }],
      },

      spacing: {
        sidebar: "240px",
        "sidebar-collapsed": "64px",
        "chat-panel": "380px",
      },

      borderRadius: {
        card: "0.75rem",
        badge: "0.375rem",
      },

      boxShadow: {
        card: "0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)",
        "card-hover": "0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04)",
        panel: "0 8px 24px rgba(0, 0, 0, 0.1)",
      },

      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "thinking-dot": {
          "0%, 80%, 100%": { opacity: "0.3", transform: "scale(0.8)" },
          "40%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "agent-pulse": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
      },

      animation: {
        "fade-in": "fade-in 200ms ease-out",
        "thinking-dot": "thinking-dot 1.4s ease-in-out infinite",
        shimmer: "shimmer 1.5s ease-in-out infinite",
        "agent-pulse": "agent-pulse 2s ease-in-out infinite",
      },

      transitionDuration: {
        fast: "150ms",
        normal: "200ms",
        slow: "300ms",
      },

      zIndex: {
        sidebar: "30",
        topbar: "40",
        "chat-panel": "50",
        overlay: "60",
        toast: "80",
      },
    },
  },

  plugins: [],
};

export default config;
