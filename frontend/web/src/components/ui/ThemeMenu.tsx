"use client";
import { Moon, Sun, Monitor } from "lucide-react";
import { useTheme, type Theme } from "@/hooks/useTheme";
export function ThemeMenu() {
  const { theme, setTheme } = useTheme();
  const Icon = theme === "dark" ? Moon : theme === "light" ? Sun : Monitor;
  return (
    <details className="theme-menu">
      <summary aria-label="Color theme" title="Color theme">
        <Icon size={18} />
      </summary>
      <div
        className="theme-options"
        role="group"
        aria-label="Color theme options"
      >
        {(["light", "dark", "system"] as Theme[]).map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={theme === value}
            onClick={(e) => {
              setTheme(value);
              const menu = e.currentTarget.closest("details");
              menu?.removeAttribute("open");
              menu?.querySelector("summary")?.focus();
            }}
          >
            {value === "system"
              ? "Use system"
              : value === "dark"
                ? "Dark mode"
                : "Light mode"}
          </button>
        ))}
      </div>
    </details>
  );
}
