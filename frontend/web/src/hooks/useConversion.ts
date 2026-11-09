"use client";
import * as api from "@/lib/api/projects";
import { downloadFile } from "@/lib/api/client";
import { saveText } from "@/lib/download";
import { buildAuditReportCsv, calledProgramReports } from "@/lib/audit-report";
import { useWorkspace } from "./useWorkspace";
import { writeStored } from "@/lib/storage";
export function useConversion() {
  const { state, setState, activeId, lock, revision } = useWorkspace();
  async function execute(
    kind: string,
    work: (id: string, version: number) => Promise<void>,
  ) {
    if (lock.current) return;
    if (!state.ready || !state.project) {
      setState((s) => ({
        ...s,
        error: !state.ready
          ? "Backend is offline. Check the API connection, then try again."
          : "Create a project first.",
      }));
      return;
    }
    const id = state.project.id;
    const version = revision.current;
    lock.current = true;
    setState((s) => ({ ...s, busy: kind, error: "" }));
    try {
      await work(id, version);
    } catch (e) {
      if (activeId.current === id && revision.current === version)
        setState((s) => ({ ...s, error: (e as Error).message }));
    } finally {
      lock.current = false;
      setState((s) => ({ ...s, busy: "" }));
    }
  }
  const convert = () =>
    execute("converting", async (id, version) => {
      if (!state.project?.files.some((f) => f.kind === "program"))
        throw new Error(
          "Upload a COBOL program before converting this project.",
        );
      setState((s) => ({
        ...s,
        results: [],
        originalPython: {},
        runId: "",
        verification: null,
        review: null,
      }));
      const result = await api.convertProject(id);
      writeStored(`legacylift-dirty-project:${id}`, "");
      if (activeId.current !== id || revision.current !== version) return;
      setState((s) => ({
        ...s,
        results: result.files,
        originalPython: Object.fromEntries(
          result.files.map((f) => [f.python_name, f.python]),
        ),
        runId: result.run_id,
        selectedIndex: 0,
        busy: "verifying",
        status: `Converted ${result.files.length} program(s). Comparing COBOL and Python outputs.`,
      }));
      const verification = await api.verifyProject(id);
      if (activeId.current === id && revision.current === version)
        setState((s) => ({
          ...s,
          verification,
          status:
            verification.status === "not_verified"
              ? "Conversion saved. Verification is unavailable; you can review and download your Python draft."
              : verification.note || "Verification complete.",
        }));
    });
  const verify = () =>
    execute("verifying", async (id, version) => {
      const verification = await api.verifyProject(id);
      if (activeId.current === id && revision.current === version)
        setState((s) => ({
          ...s,
          verification,
          status:
            verification.status === "not_verified"
              ? "Verification is unavailable. Your saved Python draft is ready for review."
              : verification.note,
        }));
    });
  const review = () =>
    execute("reviewing", async (id, version) => {
      const review = await api.reviewProject(id);
      if (activeId.current === id && revision.current === version)
        setState((s) => ({
          ...s,
          review,
          status: `AI review ${review.status === "clear" ? "found no concerns" : `found ${review.files.reduce((n, f) => n + (f.concerns ?? []).length, 0)} concern(s)`}.`,
        }));
    });
  const editPython = (text: string) =>
    setState((s) => ({
      ...s,
      results: s.results.map((f, i) =>
        i === s.selectedIndex ? { ...f, python: text } : f,
      ),
    }));
  const select = (selectedIndex: number) =>
    setState((s) => ({ ...s, selectedIndex }));
  async function downloadPython(index: number) {
    try {
      const file = state.results[index];
      if (!file) throw new Error("Convert the files again before downloading.");
      if (typeof file.python === "string")
        saveText(file.python, file.python_name, "text/x-python;charset=utf-8");
      else if (state.project && state.runId)
        await downloadFile(
          api.runFilePath(state.project.id, state.runId, file.python_name),
          file.python_name,
        );
      else
        throw new Error(
          "Convert the files again before downloading. This copy is not on the API.",
        );
    } catch (e) {
      setState((s) => ({ ...s, error: (e as Error).message }));
    }
  }
  function downloadReport() {
    if (state.verification)
      saveText(
        buildAuditReportCsv(
          state.verification,
          calledProgramReports(
            state.verification,
            state.analysis?.dependencies,
          ),
        ),
        "audit-report.csv",
        "text/csv;charset=utf-8",
      );
  }
  return {
    ...state,
    convert,
    verify,
    reviewProject: review,
    editPython,
    select,
    downloadPython,
    downloadReport,
    edited: state.results.some(
      (f) => f.python !== state.originalPython[f.python_name],
    ),
    selectedEdited: Boolean(
      state.results[state.selectedIndex] &&
      state.results[state.selectedIndex].python !==
        state.originalPython[state.results[state.selectedIndex].python_name],
    ),
  };
}
