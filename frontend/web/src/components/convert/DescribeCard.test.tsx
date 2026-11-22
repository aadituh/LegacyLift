import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { DescribeCard } from "./DescribeCard";

vi.mock("@/lib/api/projects", () => ({
  describeProject: vi.fn(),
}));

import { describeProject } from "@/lib/api/projects";

beforeEach(() => {
  vi.mocked(describeProject).mockReset();
});

it("shows each program summary and the missing-key error", async () => {
  vi.mocked(describeProject).mockResolvedValueOnce({
    project_id: "1",
    programs: [
      {
        name: "MONTHEND",
        summary: "Closes October and prints the ledger totals.",
      },
    ],
    shared_data: "MONTHEND copies the fee sheet FEERATES.",
  });
  const view = render(<DescribeCard projectId="1" />);
  fireEvent.click(screen.getByRole("button", { name: "Describe project" }));
  expect(
    await screen.findByText("Closes October and prints the ledger totals."),
  ).toBeTruthy();
  expect(screen.getByText("MONTHEND copies the fee sheet FEERATES.")).toBeTruthy();
  vi.mocked(describeProject).mockRejectedValueOnce(
    new Error("Set LEGACYLIFT_GEMINI_API_KEY before describing a project."),
  );
  view.rerender(<DescribeCard projectId="1" />);
  fireEvent.click(screen.getByRole("button", { name: "Describe project" }));
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Set LEGACYLIFT_GEMINI_API_KEY before describing a project.",
  );
});
