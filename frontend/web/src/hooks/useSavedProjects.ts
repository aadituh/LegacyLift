"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api/projects";
import type { ProjectSummary } from "@/types/api";
import { useWorkspace } from "./useWorkspace";
export function useSavedProjects() {
  const { state, setState, activeId, lock, closeProject } = useWorkspace();
  const [projects, setProjects] = useState<ProjectSummary[]>([]),
    [isLoading, setLoading] = useState(true),
    [error, setError] = useState("");
  const router = useRouter();
  const generation = useRef(0);
  const invalidate = useCallback(() => {
    generation.current++;
  }, []);
  const refresh = useCallback(async () => {
    const version = ++generation.current;
    setLoading(true);
    setError("");
    try {
      const response = await api.listProjects();
      if (generation.current === version) setProjects(response.projects);
    } catch (e) {
      if (generation.current === version) setError((e as Error).message);
    } finally {
      if (generation.current === version) setLoading(false);
    }
  }, []);
  const fingerprint = `${state.project?.id ?? ""}:${state.project?.files.length ?? 0}`;
  useEffect(() => {
    const version = ++generation.current;
    const controller = new AbortController();
    api
      .listProjects(controller.signal)
      .then((r) => {
        if (controller.signal.aborted || generation.current !== version) return;
        setProjects(r.projects);
        setError("");
      })
      .catch((e) => {
        if (!controller.signal.aborted && generation.current === version)
          setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted && generation.current === version)
          setLoading(false);
      });
    return () => {
      invalidate();
      controller.abort();
    };
  }, [fingerprint, state.ready, invalidate]);
  async function remove(ids: string[]) {
    if (!state.ready || lock.current) return;
    lock.current = true;
    setState((s) => ({ ...s, busy: "deleting", error: "" }));
    try {
      for (const id of ids) {
        await api.deleteProject(id);
        if (activeId.current === id) {
          closeProject();
        }
      }
      setState((s) => ({
        ...s,
        status:
          ids.length > 1
            ? "Cleared saved projects."
            : "Removed the saved project.",
      }));
    } catch (e) {
      setState((s) => ({ ...s, error: (e as Error).message }));
    } finally {
      lock.current = false;
      setState((s) => ({ ...s, busy: "" }));
      await refresh();
    }
  }
  return {
    projects,
    isLoading,
    error,
    refresh,
    open: (id: string) => {
      if (state.ready && !lock.current)
        router.push(`/projects/${encodeURIComponent(id)}/convert`);
    },
    remove: (id: string) => remove([id]),
    clearAll: () => remove(projects.map((p) => p.id)),
  };
}
