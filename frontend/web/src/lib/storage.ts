// Storage can be unavailable in private browsing.
export function readStored(key: string): string {
  try {
    return typeof window === "undefined"
      ? ""
      : (localStorage.getItem(key) ?? "");
  } catch {
    return "";
  }
}
export function writeStored(key: string, value: string) {
  try {
    if (value) localStorage.setItem(key, value);
    else localStorage.removeItem(key);
  } catch {
    /* Current session remains usable. */
  }
}
