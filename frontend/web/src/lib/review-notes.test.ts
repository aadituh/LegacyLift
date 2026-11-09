import { describe, expect, it } from "vitest";
import { groupReviewNotes } from "./review-notes";
describe("source review guidance", () => {
  it("groups formatting and file handling without dropping unknown statements", () => {
    const notes = [
      "Line 73: 05 TOTAL PIC Z,ZZ9.99",
      "Line 102: OPEN INPUT ACCOUNT-FILE",
      "Line 105: AT END",
      "Line 12: GO TO EXIT-PROGRAM",
      "An unfamiliar diagnostic",
    ];
    const groups = groupReviewNotes(notes);
    expect(groups.map((g) => [g.title, g.notes.length])).toEqual([
      ["Numbers & display formatting", 1],
      ["File input & output", 2],
      ["Program flow & integration", 1],
      ["Other source statements", 1],
    ]);
    expect(
      groups
        .flatMap((g) => g.notes)
        .map((n) => n.text)
        .sort(),
    ).toEqual([...notes].sort());
    expect(groups[0].notes[0].line).toBe(73);
    expect(groups[3].notes[0].line).toBeNull();
  });
  it("does not infer a source location from numbers inside a diagnostic", () => {
    expect(
      groupReviewNotes(["Unexpected value 123"])[0].notes[0].line,
    ).toBeNull();
    expect(groupReviewNotes([])).toEqual([]);
  });
});
