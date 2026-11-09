"use client";
import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from "react";
import type {
  AIReviewResponse,
  AnalyzeResponse,
  ConvertedFile,
  ProjectResponse,
  RunSummary,
  VerifyResponse,
} from "@/types/api";
import * as api from "@/lib/api/projects";
import { ApiError } from "@/lib/api/client";
import { readStored } from "@/lib/storage";
export interface WorkspaceState {
  project: ProjectResponse | null;
  analysis: AnalyzeResponse | null;
  results: ConvertedFile[];
  originalPython: Record<string, string>;
  runId: string;
  verification: VerifyResponse | null;
  review: AIReviewResponse | null;
  selectedIndex: number;
  runs: RunSummary[];
  batchFiles: File[];
  batchSources: string[];
  batchResults: ConvertedFile[];
  batchOriginal: Record<string, string>;
  batchIndex: number;
  downloadId: string;
  status: string;
  error: string;
  busy: string;
  checked: boolean;
  ready: boolean;
  notFound: boolean;
  loadingId: string;
}
export const emptyProject = {
  project: null,
  analysis: null,
  results: [],
  originalPython: {},
  runId: "",
  verification: null,
  review: null,
  selectedIndex: 0,
  runs: [],
  notFound: false,
};
const initial: WorkspaceState = {
  ...emptyProject,
  batchFiles: [],
  batchSources: [],
  batchResults: [],
  batchOriginal: {},
  batchIndex: 0,
  downloadId: "",
  status: "",
  error: "",
  busy: "",
  checked: false,
  ready: false,
  loadingId: "",
};
interface WorkspaceValue {
  state: WorkspaceState;
  setState: React.Dispatch<React.SetStateAction<WorkspaceState>>;
  activeId: React.RefObject<string>;
  lock: React.RefObject<boolean>;
  revision: React.RefObject<number>;
  closeProject: () => void;
  loadProject: (id: string) => Promise<void>;
  adoptProject: (project: ProjectResponse) => Promise<void>;
  analyze: (project: ProjectResponse) => Promise<void>;
}
const Context = createContext<WorkspaceValue | null>(null);
export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<WorkspaceState>(initial);
  const activeId = useRef("");
  const revision = useRef(0);
  const lock = useRef(false);
  const analyze = useCallback(async (project: ProjectResponse) => {
    if (!project.files.length) return;
    const version = revision.current;
    try {
      const analysis = await api.analyzeProject(project.id);
      if (activeId.current === project.id && revision.current === version)
        setState((s) => ({ ...s, analysis }));
    } catch (e) {
      if (activeId.current === project.id && revision.current === version)
        setState((s) => ({
          ...s,
          analysis: null,
          error: (e as Error).message,
        }));
    }
  }, []);
  const adoptProject = useCallback(
    async (project: ProjectResponse) => {
      revision.current++;
      activeId.current = project.id;
      setState((s) => ({
        ...s,
        ...emptyProject,
        project,
        loadingId: "",
        error: "",
      }));
      await analyze(project);
    },
    [analyze],
  );
  const closeProject = useCallback(() => {
    revision.current++;
    activeId.current = "";
    setState((s) => ({ ...s, ...emptyProject, loadingId: "" }));
  }, []);
  const loadProject = useCallback(
    async (id: string) => {
      if (activeId.current === id) return;
      const version = ++revision.current;
      activeId.current = id;
      setState((s) => ({ ...s, ...emptyProject, loadingId: id, error: "" }));
      try {
        const [project, history] = await Promise.all([
          api.getProject(id),
          api.listRuns(id),
        ]);
        if (activeId.current !== id || revision.current !== version) return;
        const latest = (kind: string) =>
          [...history.runs].reverse().find((r) => r.kind === kind);
        const convert = latest("convert"),
          analysis = latest("analyze");
        const position = convert
          ? history.runs.findIndex((r) => r.id === convert.id)
          : Infinity;
        const newer = (kind: string) =>
          history.runs
            .slice(position + 1)
            .reverse()
            .find((r) => r.kind === kind);
        const verify = newer("verify"),
          review = newer("ai_review");
        const [c, a, v, r] = await Promise.all([
          convert ? api.getRun(id, convert.id) : null,
          analysis ? api.getRun(id, analysis.id) : null,
          verify ? api.getRun(id, verify.id) : null,
          review ? api.getRun(id, review.id) : null,
        ]);
        if (activeId.current !== id || revision.current !== version) return;
        // Uploads/deletions do not create a run. Reject old drafts when the source inventory changed.
        const programs = project.files.filter((f) => f.kind === "program");
        const dirtyRun = readStored(`legacylift-dirty-project:${id}`);
        const stale = Boolean(
          c &&
          (dirtyRun === "*" ||
            dirtyRun === c.id ||
            programs.length !== (c.files ?? []).length ||
            (c.files ?? []).some(
              (f) => !programs.some((p) => p.id === f.source_file_id),
            ) ||
            (a && new Date(a.created_at ?? "") > new Date(c.created_at ?? ""))),
        );
        const files = stale ? [] : (c?.files ?? []);
        setState((s) => ({
          ...s,
          project,
          runs: history.runs,
          results: files,
          originalPython: Object.fromEntries(
            files.map((f) => [f.python_name, f.python]),
          ),
          runId: stale ? "" : (c?.id ?? ""),
          analysis: a
            ? {
                project_id: id,
                run_id: a.id,
                status: a.status,
                program_count: programs.length,
                copybook_count: project.files.filter(
                  (f) => f.kind === "copybook",
                ).length,
                data_file_count: project.files.filter((f) => f.kind === "data")
                  .length,
                dependencies: a.dependencies,
                unresolved: a.unresolved,
                programs: a.programs,
              }
            : null,
          verification:
            !stale && v
              ? {
                  project_id: id,
                  run_id: v.id,
                  status: v.status,
                  passed:
                    v.status === "not_verified"
                      ? null
                      : v.status === "verified",
                  note: "",
                  files: v.checks,
                }
              : null,
          review:
            !stale && r
              ? {
                  project_id: id,
                  run_id: r.id,
                  status: r.status,
                  model: "",
                  files: r.reviews,
                }
              : null,
          status: `Opened "${project.name}"${files.length ? " with the saved Python." : ". Convert it to see the Python."}`,
        }));
        if (!a && project.files.length) await analyze(project);
      } catch (e) {
        if (activeId.current === id && revision.current === version) {
          activeId.current = "";
          setState((s) => ({
            ...s,
            notFound: e instanceof ApiError && e.status === 404,
            error: (e as Error).message,
          }));
        }
      } finally {
        if (revision.current === version)
          setState((s) => (s.loadingId === id ? { ...s, loadingId: "" } : s));
      }
    },
    [analyze],
  );
  return (
    <Context.Provider
      value={{
        state,
        setState,
        activeId,
        lock,
        revision,
        closeProject,
        loadProject,
        adoptProject,
        analyze,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useWorkspace() {
  const value = useContext(Context);
  if (!value) throw new Error("useWorkspace needs WorkspaceProvider");
  return value;
}
