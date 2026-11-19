import { readStored, writeStored } from "@/lib/storage";

export type ModelMode = "auto" | "gemini" | "groq" | "openrouter";

export type ModelSelection = {
  mode: ModelMode;
  groqModel: string;
  openrouterModel: string;
};

const KEY = "legacylift-translation-model";

export const DEFAULT_SELECTION: ModelSelection = {
  mode: "auto",
  groqModel: "",
  openrouterModel: "",
};

const MODES = new Set<ModelMode>(["auto", "gemini", "groq", "openrouter"]);
const listeners = new Set<() => void>();
let snapshot = DEFAULT_SELECTION;
let loaded = false;

function parse(raw: string): ModelSelection {
  if (!raw) return DEFAULT_SELECTION;
  try {
    const parsed = JSON.parse(raw) as Partial<ModelSelection>;
    if (!parsed.mode || !MODES.has(parsed.mode)) return DEFAULT_SELECTION;
    return {
      mode: parsed.mode,
      groqModel: typeof parsed.groqModel === "string" ? parsed.groqModel : "",
      openrouterModel:
        typeof parsed.openrouterModel === "string"
          ? parsed.openrouterModel
          : "",
    };
  } catch {
    return DEFAULT_SELECTION;
  }
}

export function readModelSelection(): ModelSelection {
  if (typeof window === "undefined") return DEFAULT_SELECTION;
  if (!loaded) {
    snapshot = parse(readStored(KEY));
    loaded = true;
  }
  return snapshot;
}

export function writeModelSelection(selection: ModelSelection) {
  snapshot = selection;
  loaded = true;
  writeStored(KEY, JSON.stringify(selection));
  listeners.forEach((listener) => listener());
}

export function subscribeModelSelection(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
