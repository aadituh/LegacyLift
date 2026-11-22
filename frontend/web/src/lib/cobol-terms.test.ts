import { expect, it } from "vitest";
import { cobolTerms } from "@/components/guide/guide-content";
import {
  cobolDictionary,
  matchingTerms,
  termRanges,
  termsInCobol,
} from "./cobol-terms";

const divisionSentence = (label: string) =>
  cobolTerms.find(([term]) => term === label)?.[1];

it("gives every compiler word a real sentence", () => {
  expect(
    cobolDictionary.some((entry) => /reserved word/i.test(entry.sentence)),
  ).toBe(false);
  expect(cobolDictionary.find((entry) => entry.term === "MOVE")?.sentence).toBe(
    "Copies a value into one or more fields.",
  );
  expect(cobolDictionary.find((entry) => entry.term === "ADD")?.sentence).toBe(
    "Adds one or more values into a field.",
  );
});

it("includes every GnuCOBOL reserved word and the reading-guide phrases", () => {
  const names = cobolDictionary.map((entry) => entry.term);
  expect(names.length).toBeGreaterThan(900);
  expect(names).toEqual([...new Set(names)].sort((a, b) => a.localeCompare(b)));
  expect(names).toContain("MOVE");
  expect(names).toContain("IF");
  expect(names).toContain("READ");
  expect(names).toContain("DATA DIVISION");
  expect(names).toContain("PROCEDURE DIVISION");
  expect(names).toContain("STOP RUN");
});

it("lists the dictionary terms that appear in the file", () => {
  const found = termsInCobol(`
       IDENTIFICATION DIVISION.
       PROGRAM-ID. BANKMAIN.
       ENVIRONMENT DIVISION.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       PROCEDURE DIVISION.
           PERFORM CLOSE-ACCOUNT
           CALL "TXNPOST"
           COPY FEERATES.
    `).map((entry) => entry.term);
  expect(found).toContain("IDENTIFICATION DIVISION");
  expect(found).toContain("DATA DIVISION");
  expect(found).toContain("PROCEDURE DIVISION");
  expect(found).toContain("COPY");
  expect(found).toContain("CALL");
  expect(found).toContain("PERFORM");
  expect(found).not.toContain("MOVE");
  expect(termsInCobol("01 TOTAL PIC 9(3).").map((entry) => entry.term)).toEqual(
    ["PIC"],
  );
});

it("uses the reading guide's sentences", () => {
  const found = termsInCobol("DATA DIVISION.\nPROCEDURE DIVISION.");
  expect(found.find((entry) => entry.term === "DATA DIVISION")?.sentence).toBe(
    divisionSentence("DATA DIVISION"),
  );
  expect(
    found.find((entry) => entry.term === "PROCEDURE DIVISION")?.sentence,
  ).toBe(divisionSentence("PROCEDURE DIVISION"));
  expect(cobolDictionary.find((entry) => entry.term === "COPY")?.sentence).toBe(
    "Include shared definitions.",
  );
  expect(cobolDictionary.find((entry) => entry.term === "CALL")?.sentence).toBe(
    "Invoke another program.",
  );
  expect(
    cobolDictionary.find((entry) => entry.term === "PERFORM")?.sentence,
  ).toBe("Run a local routine or loop.");
  expect(cobolDictionary.find((entry) => entry.term === "PIC")?.sentence).toBe(
    "Describes how a field is stored, such as the number of digits.",
  );
});

it("matches a phrase in either case and ignores it inside a longer name", () => {
  expect(
    termsInCobol("procedure division.").map((entry) => entry.term),
  ).toEqual(["DIVISION", "PROCEDURE", "PROCEDURE DIVISION"]);
  const insideNames = termsInCobol(
    "DATA DIVISION-LINE and END-IF and COPYBOOK",
  ).map((entry) => entry.term);
  expect(insideNames).not.toContain("DIVISION");
  expect(insideNames).not.toContain("IF");
  expect(insideNames).not.toContain("COPY");
  expect(insideNames).toContain("AND");
  expect(insideNames).toContain("DATA");
  expect(
    termsInCobol("PERFORM CLOSE-ACCOUNT").map((entry) => entry.term),
  ).toEqual(["PERFORM"]);
  expect(termsInCobol("DISPLAY-LINE").map((entry) => entry.term)).toEqual([]);
  expect(termRanges("STOP.", "STOP RUN")).toEqual([]);
});

it("ignores words inside comments and quoted text", () => {
  const source = `
      * month-end close for the accounting team.
           DISPLAY "MONTH-END CLOSE - OCTOBER"
           PERFORM CLOSE-ACCOUNT
           CLOSE ACCOUNT-FILE.
  `;
  const names = termsInCobol(source).map((entry) => entry.term);
  expect(names).toContain("CLOSE");
  expect(names).toContain("DISPLAY");
  expect(names).toContain("PERFORM");
  const ranges = termRanges(source, "CLOSE");
  expect(ranges).toHaveLength(1);
  expect(source.slice(ranges[0].from, ranges[0].to + 13)).toBe(
    "CLOSE ACCOUNT-FILE",
  );
});

it("finds every whole phrase to highlight", () => {
  const source = "DATA DIVISION.\nPROCEDURE DIVISION.\nDATA DIVISION-LINE";
  const first = source.indexOf("DATA DIVISION");
  expect(termRanges(source, "DATA DIVISION")).toEqual([
    { from: first, to: first + "DATA DIVISION".length },
  ]);
  expect(termRanges(source, "PERFORM")).toEqual([]);
});

it("filters the dictionary by the typed term", () => {
  expect(matchingTerms("pic").map((entry) => entry.term)).toContain("PIC");
  expect(matchingTerms("division").map((entry) => entry.term)).toEqual(
    expect.arrayContaining([
      "DIVISION",
      "IDENTIFICATION DIVISION",
      "ENVIRONMENT DIVISION",
      "DATA DIVISION",
      "PROCEDURE DIVISION",
    ]),
  );
  expect(matchingTerms("zzzz")).toEqual([]);
});
