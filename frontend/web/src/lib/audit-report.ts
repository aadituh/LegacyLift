import type { DependencyLink, VerifyResponse } from "@/types/api";
import { outputLines, verificationStatus } from "./format";
export type CalledProgram = { program: string; caller: string };
export function calledProgramReports(
  verification: VerifyResponse | null,
  dependencies: DependencyLink[] = [],
): CalledProgram[] {
  if (!verification || verification.status === "not_verified") return [];
  const seen = new Set(verification.files.map((f) => f.source_name));
  return dependencies.flatMap((link) => {
    if (link.kind !== "call" || seen.has(link.target)) return [];
    seen.add(link.target);
    return [
      {
        program: link.target,
        caller: link.source.split(":")[0].replace(/\.(cbl|cob)$/i, ""),
      },
    ];
  });
}
export function csvCell(value: unknown) {
  const text = value == null ? "" : String(value);
  // Quoting alone does not stop Excel evaluating formula-like text.
  const safe = /^\s*[=+\-@]/.test(text) ? `'${text}` : text;
  return /[",\r\n]/.test(safe) || safe !== text
    ? `"${safe.replaceAll('"', '""')}"`
    : safe;
}
export function buildAuditReportCsv(
  verification: VerifyResponse,
  calledPrograms: CalledProgram[] = [],
) {
  const rows: unknown[][] = [
    ["program", "status", "error", "line", "cobol", "python"],
  ];
  for (const item of calledPrograms)
    rows.push([item.program, `runs inside ${item.caller}`, "", "", "", ""]);
  for (const file of verification.files) {
    const cobol = outputLines(file.cobol_stdout ?? ""),
      python = outputLines(file.python_stdout ?? "");
    const count = Math.max(cobol.length, python.length);
    for (let i = 0; i < Math.max(1, count); i++)
      rows.push([
        file.source_name,
        verificationStatus(file, verification),
        i ? "" : (file.error ?? ""),
        count ? i + 1 : "",
        cobol[i] ?? "",
        python[i] ?? "",
      ]);
  }
  return (
    "\uFEFF" +
    rows.map((row) => row.map(csvCell).join(",")).join("\r\n") +
    "\r\n"
  );
}
