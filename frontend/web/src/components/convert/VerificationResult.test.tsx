import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { VerifyResponse } from "@/types/api";
import { VerificationResult } from "./VerificationResult";

const projectMismatch: VerifyResponse = {
  project_id: "p1",
  run_id: "r1",
  status: "mismatch",
  passed: false,
  note: "COBOL and Python outputs differed, or a program failed to run.",
  files: [
    {
      source_name: "GOOD.cbl",
      python_name: "GOOD.py",
      equivalent: true,
      cobol_stdout: "TOTAL 5\n",
      python_stdout: "TOTAL 5\n",
      diff: "",
    },
    {
      source_name: "BAD.cbl",
      python_name: "BAD.py",
      equivalent: false,
      cobol_stdout: "TOTAL 5\n",
      python_stdout: "TOTAL 6\n",
      diff: "-TOTAL 5\n+TOTAL 6\n",
    },
  ],
};

describe("VerificationResult", () => {
  it("describes a matching program by its own result, not the project's", () => {
    render(
      <VerificationResult fileName="GOOD.cbl" verification={projectMismatch} />,
    );
    expect(screen.getByText("Verified")).toBeTruthy();
    expect(screen.getByText("COBOL and Python outputs match.")).toBeTruthy();
    expect(screen.queryByText(projectMismatch.note)).toBeNull();
  });

  it("describes a differing program as a mismatch", () => {
    render(
      <VerificationResult fileName="BAD.cbl" verification={projectMismatch} />,
    );
    expect(screen.getByText("Mismatch")).toBeTruthy();
    expect(
      screen.getByText("Outputs differed or a program failed."),
    ).toBeTruthy();
  });
});
