import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { CobolTerms } from "./CobolTerms";

const source = `
       01 TOTAL PIC 9(3).
           PERFORM CLOSE-ACCOUNT
`;

it("shows a sentence for a word in the file and hides it again", () => {
  render(<CobolTerms source={source} />);
  expect(screen.queryByRole("button", { name: "CALL" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "PIC" }));
  expect(
    screen.getByText(
      "Describes how a field is stored, such as the number of digits.",
    ),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "PIC" }));
  expect(
    screen.queryByText(
      "Describes how a field is stored, such as the number of digits.",
    ),
  ).toBeNull();
});
