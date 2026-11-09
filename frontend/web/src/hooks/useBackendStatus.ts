"use client";
import { useCallback, useEffect, useRef } from "react";
import { checkBackend } from "@/lib/api/client";
import { useWorkspace } from "./useWorkspace";
export function useBackendStatus() {
  const { state, setState } = useWorkspace();
  const generation = useRef(0);
  const invalidate = useCallback(() => {
    generation.current++;
  }, []);
  const retry = useCallback(async () => {
    const version = ++generation.current;
    const ready = await checkBackend();
    if (generation.current === version)
      setState((s) => ({ ...s, checked: true, ready }));
  }, [setState]);
  useEffect(() => {
    void retry();
    const timer = setInterval(retry, 30000);
    return () => {
      invalidate();
      clearInterval(timer);
    };
  }, [retry, invalidate]);
  return { checked: state.checked, ready: state.ready, retry };
}
