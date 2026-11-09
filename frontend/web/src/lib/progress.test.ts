import { it, expect } from "vitest";
import { getProgress } from "./progress";
import { outputLines, formatRunTime, formatRunStatus } from "./format";
const base = {
  files: 0,
  programs: 0,
  results: 0,
  verification: null,
  verifying: false,
};
it("progress reflects uploads, conversion, running verification, and batch restrictions", () => {
  expect(getProgress(base).step).toBe(0);
  expect(getProgress({ ...base, files: 1 }).note).toContain("COBOL");
  expect(getProgress({ ...base, files: 1, programs: 1 }).step).toBe(1);
  expect(getProgress({ ...base, results: 1 }).step).toBe(2);
  expect(getProgress({ ...base, verifying: true }).states[2]).toBe("Running");
  expect(getProgress({ ...base, batch: true }).states[2]).toBe("Projects only");
});
it("normalizes output lines without discarding significant whitespace", () => {
  expect(outputLines(" A\r\nB \r\n")).toEqual([" A", "B "]);
  expect(outputLines("")).toEqual([]);
  expect(outputLines("\n")).toEqual([]);
  expect(formatRunTime("invalid")).toBe("");
  expect(formatRunStatus("not_verified")).toBe("Not compared");
});
it("never presents an unavailable runner as verified", () => {
  const verification = {
    project_id: "1",
    run_id: "3",
    status: "not_verified" as const,
    passed: null,
    note: "Runner off",
    files: [],
  };
  const progress = getProgress({
    ...base,
    programs: 1,
    files: 1,
    results: 1,
    verification,
  });
  expect(progress.step).toBe(2);
  expect(progress.states[2]).toBe("Not compared");
  expect(progress.note).toContain("unavailable");
  expect(
    getProgress({
      ...base,
      verification: { ...verification, status: "mismatch", passed: false },
    }).states[2],
  ).toBe("Mismatch");
});
