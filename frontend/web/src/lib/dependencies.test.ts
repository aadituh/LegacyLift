import { describe, expect, it } from "vitest";
import { groupConnections } from "./dependencies";
describe("dependency grouping", () => {
  it("keeps every original source location when references share a target", () => {
    const items = groupConnections(
      [
        { source: "MAIN.cbl", target: "POST", kind: "perform", line: 22 },
        { source: "MAIN.cbl", target: "POST", kind: "perform", line: 9 },
        { source: "MAIN.cbl", target: "POST", kind: "perform", line: 22 },
      ],
      [],
    );
    expect(items).toHaveLength(1);
    expect(items[0]).toMatchObject({
      kind: "perform",
      target: "POST",
      lines: [9, 22],
      missing: false,
    });
  });
  it("does not hide a missing reference behind a resolved item or another relationship type", () => {
    const items = groupConnections(
      [
        { source: "MAIN.cbl", target: "SHARED", kind: "COPY", line: 3 },
        { source: "MAIN.cbl", target: "SHARED", kind: "call", line: 7 },
      ],
      [{ source: "MAIN.cbl", name: "SHARED", kind: "copy", line: 8 }],
    );
    expect(items).toHaveLength(3);
    expect(new Set(items.map((item) => item.id)).size).toBe(3);
    expect(items.find((item) => item.missing)?.lines).toEqual([8]);
  });
  it("handles empty analysis and names containing separators without identity collisions", () => {
    expect(groupConnections([], [])).toEqual([]);
    const items = groupConnections(
      [
        { source: "MAIN.cbl", target: "B:C", kind: "a", line: 1 },
        { source: "MAIN.cbl", target: "C", kind: "a:b", line: 2 },
      ],
      [],
    );
    expect(new Set(items.map((item) => item.id)).size).toBe(2);
  });
});
