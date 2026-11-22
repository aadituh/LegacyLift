import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { CobolTerms } from "./CobolTerms";

const source = `
       DATA DIVISION.
           PERFORM CLOSE-ACCOUNT
           PERFORM NEXT-ACCOUNT
`;

it("says how many times the chosen term appears", () => {
  render(<CobolTerms source={source} />);
  expect(screen.queryByRole("combobox", { name: "Choose a term" })).toBeNull();
  expect(screen.queryByText("Terms in this file")).toBeNull();
  const box = screen.getByRole("combobox", { name: "COBOL dictionary" });
  fireEvent.change(box, { target: { value: "DATA DIVISION" } });
  expect(
    screen.getByText(
      "Defines records, fields, and working storage. PIC describes a field's representation.",
    ),
  ).toBeTruthy();
  expect(screen.getByText("1").closest("mark")).toBeTruthy();
  expect(screen.getByText(/Found/).textContent).toBe(
    "Found 1 time in this file.",
  );
  fireEvent.change(box, { target: { value: "PERFORM" } });
  expect(screen.getByText("2").closest("mark")).toBeTruthy();
  expect(screen.getByText(/Found/).textContent).toBe(
    "Found 2 times in this file.",
  );
  fireEvent.change(box, { target: { value: "DISPLAY" } });
  expect(screen.getByText("Prints a line.")).toBeTruthy();
  expect(screen.getByText("This term is not in this file.")).toBeTruthy();
});

it("lists only the terms in the open file and still defines the others", () => {
  render(<CobolTerms source={source} />);
  fireEvent.click(
    screen.getByRole("button", { name: "Show terms in this file" }),
  );
  expect(screen.getByRole("option", { name: "DATA DIVISION" })).toBeTruthy();
  expect(screen.getByRole("option", { name: "PERFORM" })).toBeTruthy();
  expect(screen.queryByRole("option", { name: "MOVE" })).toBeNull();
  fireEvent.click(screen.getByRole("option", { name: "PERFORM" }));
  expect(screen.getByText(/Found/).textContent).toBe(
    "Found 2 times in this file.",
  );
  fireEvent.change(screen.getByRole("combobox", { name: "COBOL dictionary" }), {
    target: { value: "MOVE" },
  });
  expect(
    screen.getByText("Copies a value into one or more fields."),
  ).toBeTruthy();
  expect(screen.getByText("This term is not in this file.")).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "Show terms in this file" }),
  );
  expect(screen.getByRole("option", { name: "DATA DIVISION" })).toBeTruthy();
  fireEvent.click(screen.getByRole("option", { name: "DATA DIVISION" }));
  expect(
    screen.getByText(
      "Defines records, fields, and working storage. PIC describes a field's representation.",
    ),
  ).toBeTruthy();
});

it("closes the menu when the click is outside the box", () => {
  render(
    <div>
      <CobolTerms source={source} />
      <button type="button">Away</button>
    </div>,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Show terms in this file" }),
  );
  expect(screen.getByRole("option", { name: "PERFORM" })).toBeTruthy();
  fireEvent.pointerDown(screen.getByRole("button", { name: "Away" }));
  expect(screen.queryByRole("option", { name: "PERFORM" })).toBeNull();
  fireEvent.click(
    screen.getByRole("button", { name: "Show terms in this file" }),
  );
  fireEvent.pointerDown(screen.getByText("COBOL dictionary"));
  expect(screen.queryByRole("option", { name: "PERFORM" })).toBeNull();
});

it("says when a typed word is not a COBOL term", () => {
  render(<CobolTerms source={source} />);
  fireEvent.change(screen.getByRole("combobox", { name: "COBOL dictionary" }), {
    target: { value: "zzzz" },
  });
  expect(
    screen.getByText("This dictionary does not have that term."),
  ).toBeTruthy();
});
