import { describe, expect, it } from "vitest";
import { buildSourceLocations } from "./source-locations";
import type { SourceFile } from "@/types/api";
const source: SourceFile = {
  id: "1",
  name: "MAIN.cbl",
  kind: "program",
  content: "       COPY SHARED.\n           DISPLAY TOTAL.\n",
};
const book: SourceFile = {
  id: "2",
  name: "SHARED.cpy",
  kind: "copybook",
  content: "       01 TOTAL PIC ZZ9.\n       01 OTHER PIC 9.\n",
};
describe("review note source provenance", () => {
  it("maps expanded copybook diagnostics and subsequent program lines to original files", () => {
    const locate = buildSourceLocations(source, [source, book]);
    expect(locate("Line 1: 01 TOTAL PIC ZZ9")).toMatchObject({
      file: book,
      line: 1,
    });
    expect(locate("Line 3: DISPLAY TOTAL")).toMatchObject({
      file: source,
      line: 2,
    });
  });
  it("keeps unresolved COPY lines and rejects inconsistent diagnostics", () => {
    const locate = buildSourceLocations(source, [source]);
    expect(locate("Line 2: DISPLAY TOTAL")?.line).toBe(2);
    expect(locate("Line 3: DISPLAY TOTAL")).toBeNull();
    expect(locate("Line 2: OPEN INPUT OTHER")).toBeNull();
  });
  it("does not expand commented COPY or recursively expand copybooks", () => {
    const commented = {
      ...source,
      content: "000100*COPY SHARED.\r\n000200 DISPLAY TOTAL.\r\n",
    };
    expect(
      buildSourceLocations(commented, [book])("Line 2: DISPLAY TOTAL"),
    ).toMatchObject({ file: commented, line: 2 });
    const nested = { ...book, content: "       COPY OTHER.\n" };
    expect(
      buildSourceLocations(source, [nested])("Line 1: COPY OTHER"),
    ).toMatchObject({ file: nested, line: 1 });
  });
});
