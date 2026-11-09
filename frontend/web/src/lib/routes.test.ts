import { describe, expect, it } from "vitest";
import { projectUrl } from "./routes";

describe("projectUrl", () => {
  it("puts the project id in the query string", () => {
    expect(projectUrl("convert", "12")).toBe("/convert?project=12");
    expect(projectUrl("export", "12")).toBe("/export?project=12");
  });

  it("encodes the id and keeps a hash", () => {
    expect(projectUrl("convert", "a b", "verification")).toBe(
      "/convert?project=a%20b#verification",
    );
  });
});
