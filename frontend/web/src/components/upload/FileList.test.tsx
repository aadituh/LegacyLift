import { render, fireEvent, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import type { SourceFile } from "@/types/api";
import { FileList } from "./FileList";
it("keeps active file filters available after deleting below the search threshold", () => {
  const files: SourceFile[] = Array.from({ length: 9 }, (_, index) => ({
    id: String(index),
    name: `FILE${index}.${index > 6 ? "cpy" : "cbl"}`,
    kind: index > 6 ? "copybook" : "program",
    content: "",
  }));
  const view = render(<FileList files={files} />);
  fireEvent.change(screen.getByLabelText("File type"), {
    target: { value: "copybook" },
  });
  expect(view.container.querySelectorAll(".file-list li")).toHaveLength(2);
  view.rerender(<FileList files={files.slice(0, 8)} />);
  expect(screen.queryByLabelText("File type")).not.toBeNull();
  expect(view.container.querySelectorAll(".file-list li")).toHaveLength(1);
  fireEvent.change(screen.getByLabelText("File type"), {
    target: { value: "all" },
  });
  expect(view.container.querySelectorAll(".file-list li")).toHaveLength(8);
});
