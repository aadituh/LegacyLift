import { describe, expect, it } from "vitest";
import {
  buildAuditReportCsv,
  calledProgramReports,
  csvCell,
} from "./audit-report";
import type { VerifyResponse } from "@/types/api";
const verification: VerifyResponse = {
  project_id: "1",
  run_id: "3",
  passed: true,
  status: "verified",
  note: "",
  files: [
    {
      source_name: "MAIN.cbl",
      python_name: "MAIN.py",
      equivalent: true,
      cobol_stdout: "hello\r\nworld\r\n",
      python_stdout: "hello\nworld\n",
      error: null,
      diff: "",
    },
  ],
};
describe("audit report", () => {
  it("quotes commas and quotes, and neutralizes spreadsheet formulas", () => {
    expect(csvCell('one,"two"')).toBe('"one,""two"""');
    expect(csvCell("=2+2")).toBe('"\'=2+2"');
    expect(csvCell(" @SUM(A1)")).toBe('"\' @SUM(A1)"');
  });
  it("includes a BOM, CRLF rows, program status and output lines", () => {
    const csv = buildAuditReportCsv(verification);
    expect(csv).toContain("\uFEFFprogram,status,error,line,cobol,python\r\n");
    expect(csv).toContain("MAIN.cbl,verified,,2,world,world");
  });
  it("records programs with no output and error", () => {
    const csv = buildAuditReportCsv({
      ...verification,
      status: "not_verified",
      files: [
        {
          ...verification.files[0],
          cobol_stdout: "",
          python_stdout: "",
          error: "Runner off",
        },
      ],
    });
    expect(csv).toContain("MAIN.cbl,not_verified,Runner off,,,");
  });
  it("deduplicates called programs and omits them when not compared", () => {
    const links = [
      { source: "MAIN.cbl:START", target: "SUB.cbl", kind: "call", line: 3 },
    ];
    expect(calledProgramReports(verification, [...links, ...links])).toEqual([
      { program: "SUB.cbl", caller: "MAIN" },
    ]);
    expect(
      calledProgramReports({ ...verification, status: "not_verified" }, links),
    ).toEqual([]);
  });
});
