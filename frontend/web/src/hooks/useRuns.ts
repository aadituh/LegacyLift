"use client";
import { useEffect, useState } from "react";
import { listRuns } from "@/lib/api/projects";
import { useWorkspace } from "./useWorkspace";
export function useRuns(id: string) {
  const { state, setState } = useWorkspace();
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    listRuns(id, controller.signal)
      .then((r) => {
        if (controller.signal.aborted) return;
        setError("");
        setState((s) => (s.project?.id === id ? { ...s, runs: r.runs } : s));
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [id, setState, state.busy, state.project?.id]);
  return { runs: [...state.runs].reverse(), error };
}
