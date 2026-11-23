import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ProjectDescription } from "./ProjectDescription";

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
  const view = render(<ProjectDescription projectId="1" />);
  fireEvent.click(
    screen.getByRole("button", { name: "What this project does" }),
  );
  expect(screen.getByText(/gemini-3.5-flash-lite/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Describe project" }));
  expect(
    await screen.findByText("Closes October and prints the ledger totals."),
  ).toBeTruthy();
  expect(
    screen.getByText("MONTHEND copies the fee sheet FEERATES."),
  ).toBeTruthy();
  vi.mocked(describeProject).mockRejectedValueOnce(
    new Error("Set LEGACYLIFT_GEMINI_API_KEY before describing a project."),
  );
  view.rerender(<ProjectDescription projectId="1" />);
  fireEvent.click(screen.getByRole("button", { name: "Describe project" }));
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Set LEGACYLIFT_GEMINI_API_KEY before describing a project.",
  );
});
