"use client";

import "./globals.css";
import { useState, useEffect, useCallback, createContext, useContext } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { ChatPanel } from "@/components/layout/ChatPanel";

// ---------------------------------------------------------------------------
// Theme context
// ---------------------------------------------------------------------------

type Theme = "light" | "dark";

const ThemeContext = createContext<{
  theme: Theme;
  toggleTheme: () => void;
}>({ theme: "dark", toggleTheme: () => {} });

export function useTheme() {
  return useContext(ThemeContext);
}

// ---------------------------------------------------------------------------
// Root layout
// ---------------------------------------------------------------------------

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [chatOpen, setChatOpen] = useState(false);
  const toggleChat = () => setChatOpen((prev) => !prev);

  const [theme, setTheme] = useState<Theme>("dark");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("theme") as Theme | null;
    if (stored === "light" || stored === "dark") {
      setTheme(stored);
    }
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme, mounted]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  return (
    <html lang="en" className={mounted ? theme : "dark"}>
      <head>
        <title>Copy Agent Dashboard</title>
        <meta
          name="description"
          content="Self-optimizing marketing copy agent dashboard"
        />
      </head>
      <body className="font-sans">
        <ThemeContext.Provider value={{ theme, toggleTheme }}>
          <div className="dashboard-layout" data-chat-open={chatOpen}>
            <Sidebar />
            <main className="main-content">{children}</main>
            <ChatPanel isOpen={chatOpen} onToggle={toggleChat} />
          </div>
        </ThemeContext.Provider>
      </body>
    </html>
  );
}
