"use client";
import { useEffect } from "react";
import * as api from "@/lib/api/projects";
import { checkProjectFiles } from "@/lib/files";
import { emptyProject, useWorkspace } from "./useWorkspace";
import { readStored, writeStored } from "@/lib/storage";
export function useProject(projectId?: string) {
  const {
    state,
    setState,
    loadProject,
    adoptProject,
    analyze,
    activeId,
    lock,
    revision,
  } = useWorkspace();
  useEffect(() => {
    if (projectId) void loadProject(projectId);
  }, [projectId, loadProject]);
  async function action<T>(
    kind: string,
    work: () => Promise<T>,
  ): Promise<T | undefined> {
    if (lock.current) return;
    if (!state.ready) {
      setState((s) => ({
        ...s,
        error: "Backend is offline. Check the API connection, then try again.",
      }));
      return;
    }
    const version = revision.current;
    lock.current = true;
    setState((s) => ({ ...s, busy: kind, error: "" }));
    try {
      return await work();
    } catch (e) {
      if (revision.current === version)
        setState((s) => ({ ...s, error: (e as Error).message }));
    } finally {
      lock.current = false;
      setState((s) => ({ ...s, busy: "" }));
    }
  }
  async function create(name: string) {
    if (!name.trim()) {
      setState((s) => ({ ...s, error: "Enter a project name." }));
      return;
    }
    return action("creating", async () => {
      const version = revision.current;
      const project = await api.createProject(name.trim());
      if (revision.current !== version) return;
      await adoptProject(project);
      setState((s) => ({
        ...s,
        status: `Project "${project.name}" created. Upload your COBOL files to continue.`,
      }));
      return project.id;
    });
  }
  const loadDemo = () =>
    action("demo", async () => {
      const version = revision.current;
      const project = await api.createDemoProject();
      if (revision.current !== version) return;
      await adoptProject(project);
      setState((s) => ({
        ...s,
        status: `Loaded "${project.name}" with ${project.files.length} sample files. Ready to convert.`,
      }));
      return project.id;
    });
  const upload = (files: File[]) =>
    action("uploading", async () => {
      if (!state.project) throw new Error("Create a project first.");
      if (!files.length) return;
      const id = state.project.id;
      const version = revision.current;
      const problem = await checkProjectFiles(
        files,
        state.project.files.length,
      );
      if (activeId.current !== id || revision.current !== version) return;
      if (problem) throw new Error(problem);
      const result = await api.uploadProjectFiles(id, files);
      writeStored(
        `legacylift-dirty-project:${id}`,
        state.runId || readStored(`legacylift-dirty-project:${id}`) || "*",
      );
      if (activeId.current !== id || revision.current !== version) return;
      const project = {
        ...state.project,
        files: [...state.project.files, ...result.files],
      };
      setState((s) => ({
        ...s,
        ...emptyProject,
        project,
        status: `Uploaded ${files.length} file(s). Ready for conversion.`,
      }));
      await analyze(project);
    });
  const removeFile = (fileId: string) =>
    action("removing-file", async () => {
      if (!state.project) return;
      const id = state.project.id;
      const version = revision.current;
      await api.deleteProjectFile(id, fileId);
      writeStored(
        `legacylift-dirty-project:${id}`,
        state.runId || readStored(`legacylift-dirty-project:${id}`) || "*",
      );
      if (activeId.current !== id || revision.current !== version) return;
      const project = {
        ...state.project,
        files: state.project.files.filter((f) => f.id !== fileId),
      };
      setState((s) => ({
        ...s,
        ...emptyProject,
        project,
        status: "File removed. Convert again to update the Python.",
      }));
      await analyze(project);
    });
  return {
    ...state,
    programs: state.project?.files.filter((f) => f.kind === "program") ?? [],
    create,
    loadDemo,
    upload,
    removeFile,
    retry: () => projectId && loadProject(projectId),
  };
}
