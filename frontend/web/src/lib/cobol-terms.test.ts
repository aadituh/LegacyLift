import { expect, it } from "vitest";
import { termRanges, termsInCobol } from "./cobol-terms";

it("lists only the dictionary words that appear as whole words", () => {
  expect(
    termsInCobol(`
       WORKING-STORAGE SECTION.
       01 TOTAL PIC 9(3).
           PERFORM CLOSE-ACCOUNT
           CALL "TXNPOST"
           COPY FEERATES.
    `).map((entry) => entry.term),
  ).toEqual(["PIC", "PERFORM", "COPY", "CALL", "WORKING-STORAGE"]);
});

it("matches a word in either case and ignores it inside a longer name", () => {
  expect(
    termsInCobol("move total to balance").map((entry) => entry.term),
  ).toEqual(["MOVE"]);
  expect(
    termsInCobol("DISPLAY-LINE and END-IF").map((entry) => entry.term),
  ).toEqual([]);
  expect(termsInCobol("IF WS-TYPE = 'S'").map((entry) => entry.term)).toEqual([
    "IF",
  ]);
});

it("finds every whole-word match to highlight", () => {
  const source = "01 TOTAL PIC 9(3).\n01 NAME PIC X(10).\nDISPLAY-LINE";
  expect(termRanges(source, "PIC")).toEqual([
    { from: source.indexOf("PIC"), to: source.indexOf("PIC") + 3 },
    {
      from: source.lastIndexOf("PIC"),
      to: source.lastIndexOf("PIC") + 3,
    },
  ]);
  expect(termRanges(source, "DISPLAY")).toEqual([]);
});
