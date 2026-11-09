import { act, renderHook } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { WorkspaceProvider, useWorkspace } from "./useWorkspace";
import { useConversion } from "./useConversion";
import { useProject } from "./useProject";
import * as api from "@/lib/api/projects";
import type { ProjectResponse, Run, ConvertResponse } from "@/types/api";
vi.mock("@/lib/api/projects");
function project(id: string, name = id): ProjectResponse {
  return {
    id,
    name,
    created_at: "2026-11-08T12:00:00Z",
    files: [
      {
        id: "1",
        name: "MAIN.cbl",
        kind: "program",
        content: "       STOP RUN.",
      },
    ],
  };
}
const draft = {
  source_file_id: "1",
  source_name: "MAIN.cbl",
  python_name: "MAIN.py",
  program_name: "MAIN",
  python: "# saved",
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
  vi.resetAllMocks();
  vi.mocked(api.getProject).mockImplementation(async (id) => project(id));
  vi.mocked(api.listRuns).mockResolvedValue({ project_id: "1", runs: [] });
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
it("keeps the newest request when navigation returns to the same project", async () => {
  let resolveFirst!: (p: ProjectResponse) => void;
  vi.mocked(api.getProject).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        resolveFirst = resolve;
      }),
  );
  const { result } = renderHook(() => useWorkspace(), { wrapper });
  let old!: Promise<void>;
  act(() => {
    old = result.current.loadProject("1");
  });
  await act(() => result.current.loadProject("2"));
  await act(() => result.current.loadProject("1"));
  await act(async () => {
    resolveFirst(project("1", "Stale response"));
    await old;
  });
  expect(result.current.state.project?.name).toBe("1");
});
it("does not reopen a project after it has been closed", async () => {
  let resolve!: (p: ProjectResponse) => void;
  vi.mocked(api.getProject).mockReturnValueOnce(
    new Promise((r) => {
      resolve = r;
    }),
  );
  const { result } = renderHook(() => useWorkspace(), { wrapper });
  let old!: Promise<void>;
  act(() => {
    old = result.current.loadProject("1");
  });
  act(() => result.current.closeProject());
  await act(async () => {
    resolve(project("1"));
    await old;
  });
  expect(result.current.state.project).toBeNull();
  expect(result.current.state.loadingId).toBe("");
});
it("ignores an earlier conversion after leaving and reopening its project", async () => {
  let resolve!: (p: ConvertResponse) => void;
  vi.mocked(api.convertProject).mockReturnValueOnce(
    new Promise((r) => {
      resolve = r;
    }),
  );
  const { result } = renderHook(
    () => ({ w: useWorkspace(), c: useConversion() }),
    { wrapper },
  );
  await act(() => result.current.w.adoptProject(project("1")));
  act(() => result.current.w.setState((s) => ({ ...s, ready: true })));
  let old!: Promise<void>;
  act(() => {
    old = result.current.c.convert();
  });
  await act(() => result.current.w.adoptProject(project("2")));
  await act(() => result.current.w.adoptProject(project("1")));
  await act(async () => {
    resolve({ project_id: "1", run_id: "2", status: "draft", files: [draft] });
    await old;
  });
  expect(result.current.w.state.results).toEqual([]);
  expect(api.verifyProject).not.toHaveBeenCalled();
});
it("does not steal navigation when a background project creation finishes", async () => {
  let resolve!: (p: ProjectResponse) => void;
  vi.mocked(api.createProject).mockReturnValueOnce(
    new Promise((r) => {
      resolve = r;
    }),
  );
  const { result } = renderHook(
    () => ({ w: useWorkspace(), p: useProject() }),
    { wrapper },
  );
  act(() => result.current.w.setState((s) => ({ ...s, ready: true })));
  let create!: Promise<string | undefined>;
  act(() => {
    create = result.current.p.create("New project");
  });
  await act(() => result.current.w.adoptProject(project("2")));
  await act(async () => {
    resolve(project("3"));
    await create;
  });
  expect(result.current.w.state.project?.id).toBe("2");
});
it("does not revive saved Python after a mutation whose analysis failed", async () => {
  const analysis = run("1", "analyze"),
    converted = run("2", "convert");
  localStorage.setItem("legacylift-dirty-project:1", "2");
  vi.mocked(api.listRuns).mockResolvedValue({
    project_id: "1",
    runs: [analysis, converted],
  });
  vi.mocked(api.getRun).mockImplementation(async (_id, id) =>
    id === "1" ? analysis : converted,
  );
  const { result } = renderHook(() => useWorkspace(), { wrapper });
  await act(() => result.current.loadProject("1"));
  expect(result.current.state.results).toEqual([]);
  expect(result.current.state.verification).toBeNull();
});

it("does not show a failed background project action on a different project", async () => {
  let reject!: (reason: Error) => void;
  vi.mocked(api.createProject).mockReturnValueOnce(
    new Promise((_resolve, fail) => {
      reject = fail;
    }),
  );
  const { result } = renderHook(
    () => ({ w: useWorkspace(), p: useProject() }),
    { wrapper },
  );
  act(() => result.current.w.setState((s) => ({ ...s, ready: true })));
  let pending!: Promise<string | undefined>;
  act(() => {
    pending = result.current.p.create("Background project");
  });
  await act(() => result.current.w.adoptProject(project("2")));
  await act(async () => {
    reject(new Error("Old project failed"));
    await pending;
  });
  expect(result.current.w.state.project?.id).toBe("2");
  expect(result.current.w.state.error).toBe("");
  expect(result.current.w.state.busy).toBe("");
});
