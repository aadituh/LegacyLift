import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import type { VerifyResponse } from "@/types/api";
import { VerificationResult } from "./VerificationResult";

const verification: VerifyResponse = {
  project_id: "1",
  run_id: "3",
  passed: false,
  status: "mismatch",
  note: "",
  files: [
    {
      source_name: "BANKMAIN.cbl",
      python_name: "BANKMAIN.py",
      equivalent: false,
      cobol_stdout: "Alice 100\nElena 50\nTotal 150\n",
      python_stdout: "Alice 100\nElena 55\nTotal 150\n",
      error: null,
      diff: "",
    },
  ],
};

it("hides matching output lines until all lines are shown again", () => {
  render(
    <VerificationResult fileName="BANKMAIN.cbl" verification={verification} />,
  );
  expect(screen.getAllByText("Alice 100")).toHaveLength(2);
  expect(screen.getByText("Elena 50")).toBeTruthy();
  expect(screen.getAllByText("Match")).toHaveLength(2);
  fireEvent.click(screen.getByRole("button", { name: "Differences only" }));
  expect(screen.queryByText("Alice 100")).toBeNull();
  expect(screen.getByText("Elena 50")).toBeTruthy();
  expect(screen.getByText("Elena 55")).toBeTruthy();
  expect(screen.queryByText("Match")).toBeNull();
  expect(screen.getByRole("rowheader", { name: "2" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Show all lines" }));
  expect(screen.getAllByText("Alice 100")).toHaveLength(2);
  expect(screen.getAllByText("Match")).toHaveLength(2);
});
