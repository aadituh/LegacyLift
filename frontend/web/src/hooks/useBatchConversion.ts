"use client";
import { checkBatchFiles, readUtf8, SAMPLE_COBOL } from "@/lib/files";
import { convertFiles } from "@/lib/api/convert";
import { saveText } from "@/lib/download";
import { useWorkspace } from "./useWorkspace";
export function useBatchConversion() {
  const { state, setState, lock } = useWorkspace();
  async function choose(files: File[]) {
    if (lock.current || !files.length) return;
    lock.current = true;
    setState((s) => ({
      ...s,
      busy: "reading",
      error: "",
      batchResults: [],
      batchFiles: [],
      batchSources: [],
      downloadId: "",
    }));
    try {
      const problem = await checkBatchFiles(files);
      if (problem) throw new Error(problem);
      const sources = await Promise.all(files.map(readUtf8));
      setState((s) => ({
        ...s,
        batchFiles: files,
        batchSources: sources,
        batchIndex: 0,
        status: `${files.length} file(s) ready for batch conversion.`,
      }));
    } catch (e) {
      setState((s) => ({ ...s, error: (e as Error).message }));
    } finally {
      lock.current = false;
      setState((s) => ({ ...s, busy: "" }));
    }
  }
  async function convert() {
    if (lock.current) return;
    if (!state.ready || !state.batchFiles.length) {
      setState((s) => ({
        ...s,
        error: !state.ready
          ? "Backend is offline. Check the API connection, then try again."
          : "Choose COBOL files or load a sample before converting.",
      }));
      return;
    }
    lock.current = true;
    setState((s) => ({
      ...s,
      busy: "batch-converting",
      error: "",
      batchResults: [],
      downloadId: "",
    }));
    try {
      const result = await convertFiles(state.batchFiles);
      setState((s) => ({
        ...s,
        batchResults: result.files,
        batchOriginal: Object.fromEntries(
          result.files.map((f) => [f.python_name, f.python]),
        ),
        downloadId: result.download_id,
        batchIndex: 0,
        status: `Converted ${result.files.length} file(s). Download your Python drafts below.`,
      }));
    } catch (e) {
      setState((s) => ({ ...s, error: (e as Error).message }));
    } finally {
      lock.current = false;
      setState((s) => ({ ...s, busy: "" }));
    }
  }
  return {
    ...state,
    choose,
    loadSample: () =>
      choose([
        new File([SAMPLE_COBOL], "hello_team.cbl", { type: "text/plain" }),
      ]),
    convert,
    select: (batchIndex: number) => setState((s) => ({ ...s, batchIndex })),
    editPython: (python: string) =>
      setState((s) => ({
        ...s,
        batchResults: s.batchResults.map((f, i) =>
          i === s.batchIndex ? { ...f, python } : f,
        ),
      })),
    downloadPython: (index: number) => {
      const f = state.batchResults[index];
      if (f) saveText(f.python, f.python_name, "text/x-python;charset=utf-8");
    },
  };
}
