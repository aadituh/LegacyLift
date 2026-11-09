"use client";
import { useEffect } from "react";
import { useWorkspace } from "@/hooks/useWorkspace";
export function DraftExitGuard() {
  const { state } = useWorkspace();
  const edited =
    state.results.some(
      (file) => file.python !== state.originalPython[file.python_name],
    ) ||
    state.batchResults.some(
      (file) => file.python !== state.batchOriginal[file.python_name],
    );
  useEffect(() => {
    if (!edited) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [edited]);
  return null;
}
