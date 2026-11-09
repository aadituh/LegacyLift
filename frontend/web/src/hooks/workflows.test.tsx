import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WorkspaceProvider, useWorkspace } from "./useWorkspace";
import { useProject } from "./useProject";
import { useConversion } from "./useConversion";
import { useSavedProjects } from "./useSavedProjects";
import { useRuns } from "./useRuns";
import { useBatchConversion } from "./useBatchConversion";
import { useBackendStatus } from "./useBackendStatus";
import * as api from "@/lib/api/projects";
import { convertFiles } from "@/lib/api/convert";
import { checkBackend } from "@/lib/api/client";
import type { ProjectResponse, Run } from "@/types/api";
const navigation = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => navigation }));
vi.mock("@/lib/api/projects");
vi.mock("@/lib/api/convert");
vi.mock("@/lib/api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/api/client")>();
  return { ...original, checkBackend: vi.fn() };
});
const project: ProjectResponse = {
  id: "1",
  name: "Bank",
  created_at: "2026-11-08T12:00:00Z",
  files: [
    { id: "1", name: "BANK.cbl", kind: "program", content: "       STOP RUN." },
  ],
};
const draft = {
  source_file_id: "1",
  source_name: "BANK.cbl",
  python_name: "BANK.py",
  program_name: "BANK",
  python: "print('bank')",
  notes: [],
  status: "draft" as const,
};
function run(id: string, kind: Run["kind"]): Run {
  return {
    id,
    kind,
    status: kind === "convert" ? "draft" : "analyzed",
    created_at: `2026-11-08T12:0${id}:00Z`,
    files: kind === "convert" ? [draft] : [],
    checks: [],
    reviews: [],
    dependencies: [],
    unresolved: [],
    programs: [],
  };
}
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <WorkspaceProvider>{children}</WorkspaceProvider>
);
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listRuns).mockResolvedValue({ project_id: "1", runs: [] });
  vi.mocked(api.listProjects).mockResolvedValue({ projects: [] });
  vi.mocked(api.getProject).mockResolvedValue(project);
  vi.mocked(api.analyzeProject).mockResolvedValue({
    project_id: "1",
    run_id: "1",
    status: "analyzed",
    program_count: 1,
    copybook_count: 0,
    data_file_count: 0,
    dependencies: [],
    unresolved: [],
    programs: [],
  });
});
describe("workspace workflows", () => {
  it("creates and analyzes once, then preserves edits across consumers", async () => {
    vi.mocked(api.createProject).mockResolvedValue(project);
    const { result } = renderHook(
      () => ({ p: useProject(), c: useConversion(), w: useWorkspace() }),
      { wrapper },
    );
    act(() => result.current.w.setState((s) => ({ ...s, ready: true })));
    await act(() => result.current.p.create(" Bank "));
    expect(api.createProject).toHaveBeenCalledWith("Bank");
    expect(api.analyzeProject).toHaveBeenCalledTimes(1);
    act(() =>
      result.current.w.setState((s) => ({
        ...s,
        results: [draft],
        originalPython: { "BANK.py": draft.python },
      })),
    );
    act(() => result.current.c.editPython("# revised"));
    expect(result.current.w.state.results[0].python).toBe("# revised");
    expect(result.current.c.edited).toBe(true);
  });
  it("rejects empty names and offline mutations", async () => {
    const { result } = renderHook(() => useProject(), { wrapper });
    await act(() => result.current.create(" "));
    expect(result.current.error).toBe("Enter a project name.");
    await act(() => result.current.create("Bank"));
    expect(result.current.error).toContain("offline");
    expect(api.createProject).not.toHaveBeenCalled();
  });
  it("restores saved drafts, verification and AI review using stored field names", async () => {
    const convert = run("2", "convert"),
      analyze = run("1", "analyze");
    const verify = {
      ...run("3", "verify"),
      status: "verified" as const,
      checks: [
        {
          source_name: "BANK.cbl",
          python_name: "BANK.py",
          equivalent: true,
          cobol_stdout: "bank",
          python_stdout: "bank",
          error: null,
          diff: "",
        },
      ],
    };
    const review = {
      ...run("4", "ai_review"),
      status: "clear" as const,
      reviews: [],
    };
    vi.mocked(api.listRuns).mockResolvedValue({
      project_id: "1",
      runs: [analyze, convert, verify, review],
    });
    vi.mocked(api.getRun).mockImplementation(async (_id, id) =>
      [analyze, convert, verify, review].find((r) => r.id === id)!,
    );
    const { result } = renderHook(() => useWorkspace(), { wrapper });
    await act(() => result.current.loadProject("1"));
    expect(result.current.state.results).toEqual([draft]);
    expect(result.current.state.verification?.files).toEqual(verify.checks);
    expect(result.current.state.review?.status).toBe("clear");
    expect(api.analyzeProject).not.toHaveBeenCalled();
  });
  it("does not resurrect drafts after an upload inventory change", async () => {
    const analysis = run("1", "analyze"),
      convert = run("2", "convert");
    vi.mocked(api.getProject).mockResolvedValue({
      ...project,
      files: [{ ...project.files[0], id: "2" }],
    });
    vi.mocked(api.listRuns).mockResolvedValue({
      project_id: "1",
      runs: [analysis, convert],
    });
    vi.mocked(api.getRun).mockImplementation(async (_id, id) =>
      id === "1" ? analysis : convert,
    );
    const { result } = renderHook(() => useWorkspace(), { wrapper });
    await act(() => result.current.loadProject("1"));
    expect(result.current.state.results).toEqual([]);
    expect(result.current.state.runId).toBe("");
  });
  it("ignores late responses from a previously opened project", async () => {
    let resolveFirst!: (p: ProjectResponse) => void;
    vi.mocked(api.getProject).mockImplementation((id) =>
      id === "1"
        ? new Promise((resolve) => {
            resolveFirst = resolve;
          })
        : Promise.resolve({ ...project, id }),
    );
    const { result } = renderHook(() => useWorkspace(), { wrapper });
    let first!: Promise<void>;
    act(() => {
      first = result.current.loadProject("1");
    });
    await act(() => result.current.loadProject("2"));
    await act(async () => {
      resolveFirst(project);
      await first;
    });
    expect(result.current.state.project?.id).toBe("2");
  });
  it("converts then verifies, and clears the old AI result", async () => {
    vi.mocked(api.convertProject).mockResolvedValue({
      project_id: "1",
      run_id: "2",
      status: "draft",
      files: [draft],
    });
    vi.mocked(api.verifyProject).mockResolvedValue({
      project_id: "1",
      run_id: "3",
      status: "not_verified",
      passed: null,
      note: "Runner is off.",
      files: [],
    });
    const { result } = renderHook(
      () => ({ c: useConversion(), w: useWorkspace() }),
      { wrapper },
    );
    await act(() => result.current.w.adoptProject(project));
    act(() => result.current.w.setState((s) => ({ ...s, ready: true })));
    await act(() => result.current.c.convert());
    expect(api.convertProject).toHaveBeenCalledWith("1");
    expect(api.verifyProject).toHaveBeenCalledWith("1");
    expect(result.current.c.verification?.status).toBe("not_verified");
    expect(result.current.c.review).toBeNull();
  });
  it("refreshes saved projects and closes an active project on deletion", async () => {
    const { result } = renderHook(
      () => ({ saved: useSavedProjects(), w: useWorkspace() }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.saved.isLoading).toBe(false));
    await act(() => result.current.w.adoptProject(project));
    act(() => result.current.w.setState((s) => ({ ...s, ready: true })));
    await act(() => result.current.saved.remove("1"));
    expect(api.deleteProject).toHaveBeenCalledWith("1");
    expect(result.current.w.state.project).toBeNull();
  });
  it("lists runs newest first", async () => {
    vi.mocked(api.listRuns).mockResolvedValue({
      project_id: "1",
      runs: [run("1", "analyze"), run("2", "convert")],
    });
    const { result } = renderHook(
      () => ({ history: useRuns("1"), w: useWorkspace() }),
      { wrapper },
    );
    await act(() => result.current.w.adoptProject(project));
    await waitFor(() => expect(result.current.history.runs[0]?.id).toBe("2"));
  });
  it("tracks the real backend health result", async () => {
    vi.mocked(checkBackend).mockResolvedValue(true);
    const { result } = renderHook(() => useBackendStatus(), { wrapper });
    await waitFor(() => expect(result.current.checked).toBe(true));
    expect(result.current.ready).toBe(true);
    vi.mocked(checkBackend).mockResolvedValue(false);
    await act(() => result.current.retry());
    expect(result.current.ready).toBe(false);
  });
  it("validates and converts standalone batch files", async () => {
    const { result } = renderHook(
      () => ({ b: useBatchConversion(), w: useWorkspace() }),
      { wrapper },
    );
    const bytes = new TextEncoder().encode("       STOP RUN.");
    const file = {
      name: "BANK.cbl",
      size: bytes.length,
      arrayBuffer: async () => bytes.buffer,
    } as File;
    await act(() => result.current.b.choose([file]));
    vi.mocked(convertFiles).mockResolvedValue({
      download_id: "batch-1",
      files: [draft],
    });
    act(() => result.current.w.setState((s) => ({ ...s, ready: true })));
    await act(() => result.current.b.convert());
    expect(convertFiles).toHaveBeenCalledWith([file]);
    expect(result.current.b.batchResults[0].python_name).toBe("BANK.py");
  });
});
