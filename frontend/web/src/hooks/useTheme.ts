"use client";
import { useSyncExternalStore } from "react";
import { readStored, writeStored } from "@/lib/storage";
export type Theme = "light" | "dark" | "system";
const key = "legacylift-theme";
function snapshot(): Theme {
  const stored = readStored(key);
  return stored === "light" || stored === "dark" ? stored : "system";
}
function apply() {
  const theme = snapshot();
  document.documentElement.dataset.theme =
    theme === "system"
      ? window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
      : theme;
}
function subscribe(callback: () => void) {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const update = () => {
    apply();
    callback();
  };
  window.addEventListener("storage", update);
  window.addEventListener("legacylift-theme", update);
  media.addEventListener("change", update);
  apply();
  return () => {
    window.removeEventListener("storage", update);
    window.removeEventListener("legacylift-theme", update);
    media.removeEventListener("change", update);
  };
}
export function useTheme() {
  const theme = useSyncExternalStore(
    subscribe,
    snapshot,
    () => "system" as Theme,
  );
  return {
    theme,
    setTheme: (value: Theme) => {
      writeStored(key, value);
      document.documentElement.dataset.theme =
        value === "system"
          ? window.matchMedia("(prefers-color-scheme: dark)").matches
            ? "dark"
            : "light"
          : value;
      window.dispatchEvent(new Event("legacylift-theme"));
    },
  };
}
