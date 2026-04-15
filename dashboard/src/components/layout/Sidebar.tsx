"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "@/app/layout";

// ---------------------------------------------------------------------------
// Navigation configuration
// ---------------------------------------------------------------------------

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  {
    label: "Dashboard",
    href: "/",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <rect x="2" y="2" width="7" height="7" rx="1.5" />
        <rect x="11" y="2" width="7" height="7" rx="1.5" />
        <rect x="2" y="11" width="7" height="7" rx="1.5" />
        <rect x="11" y="11" width="7" height="7" rx="1.5" />
      </svg>
    ),
  },
  {
    label: "Campaigns",
    href: "/campaigns",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M3 10V4a1 1 0 0 1 1-1h2l2 3h8a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-5z" />
        <path d="M8 6l4-3v14l-4-3" />
        <path d="M14 8.5c1 .5 1.5 1.5 1.5 2.5s-.5 2-1.5 2.5" />
      </svg>
    ),
  },
  {
    label: "Playbook",
    href: "/playbook",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M4 2h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4" />
        <path d="M4 2v16" />
        <path d="M4 2C4 2 6 2 6 2" />
        <line x1="8" y1="6" x2="13" y2="6" />
        <line x1="8" y1="10" x2="13" y2="10" />
        <line x1="8" y1="14" x2="11" y2="14" />
        <path d="M4 2a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2" />
      </svg>
    ),
  },
  {
    label: "Connectors",
    href: "/connectors",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="6" cy="6" r="2.5" />
        <circle cx="14" cy="14" r="2.5" />
        <path d="M8.5 6H12a2 2 0 0 1 2 2v3.5" />
        <path d="M11.5 14H8a2 2 0 0 1-2-2V8.5" />
      </svg>
    ),
  },
  {
    label: "A/B Tests",
    href: "/ab-tests",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M4 3h5v14H4zM11 3h5v14h-5z" />
        <path d="M6.5 8v4M13.5 6v8" />
      </svg>
    ),
  },
  {
    label: "Cross-Channel",
    href: "/cross-channel",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="5" cy="5" r="2" />
        <circle cx="15" cy="5" r="2" />
        <circle cx="10" cy="15" r="2" />
        <path d="M6.5 6.5L9 13M13.5 6.5L11 13" />
      </svg>
    ),
  },
  {
    label: "Reports",
    href: "/reports",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <rect x="3" y="2" width="14" height="16" rx="2" />
        <path d="M7 7h6M7 10h6M7 13h4" />
      </svg>
    ),
  },
  {
    label: "Learnings",
    href: "/learnings",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M10 2a4 4 0 0 1 4 4c0 1.5-.8 2.8-2 3.5V11a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V9.5C6.8 8.8 6 7.5 6 6a4 4 0 0 1 4-4z" />
        <line x1="8" y1="14" x2="12" y2="14" />
        <line x1="8.5" y1="16.5" x2="11.5" y2="16.5" />
        <path d="M9 12v2.5" />
        <path d="M11 12v2.5" />
      </svg>
    ),
  },
];

// ---------------------------------------------------------------------------
// Sidebar Component
// ---------------------------------------------------------------------------

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar bg-sidebar border-r border-border">
      {/* Brand / Logo */}
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-accent/10">
          <svg
            width="18"
            height="18"
            viewBox="0 0 18 18"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M9 1L2 5v8l7 4 7-4V5L9 1z"
              stroke="hsl(var(--accent))"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
            <path
              d="M9 9V17M9 9L2 5M9 9L16 5"
              stroke="hsl(var(--accent))"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <span className="sidebar-nav-label font-display text-base font-semibold text-foreground">
          Copy Agent
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-2" aria-label="Main navigation">
        <ul className="flex flex-col gap-1" role="list">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="sidebar-nav-item text-foreground-secondary"
                  data-active={isActive ? "true" : undefined}
                  aria-current={isActive ? "page" : undefined}
                >
                  <span className="sidebar-nav-icon">{item.icon}</span>
                  <span className="sidebar-nav-label">{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Bottom section — theme toggle + status */}
      <div className="px-3 py-4 border-t border-border-subtle flex flex-col gap-3">
        <ThemeToggle />
        <div className="flex items-center gap-3 px-2">
          <span className="relative flex h-2.5 w-2.5 flex-shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-success" />
          </span>
          <span className="sidebar-nav-label text-xs text-muted">
            Server connected
          </span>
        </div>
      </div>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Theme toggle
// ---------------------------------------------------------------------------

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="sidebar-nav-item text-foreground-secondary"
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      <span className="sidebar-nav-icon">
        {theme === "dark" ? (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="10" cy="10" r="4" />
            <path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.93 4.93l1.41 1.41M13.66 13.66l1.41 1.41M4.93 15.07l1.41-1.41M13.66 6.34l1.41-1.41" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M17 11.5A7.5 7.5 0 018.5 3c0-.82.13-1.61.38-2.35A8 8 0 1019.35 11.12c-.74.25-1.53.38-2.35.38z" />
          </svg>
        )}
      </span>
      <span className="sidebar-nav-label">
        {theme === "dark" ? "Light mode" : "Dark mode"}
      </span>
    </button>
  );
}
