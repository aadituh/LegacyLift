import { describe, it, expect } from "vitest";
import {
  MAX_FILE_BYTES,
  SAMPLE_COBOL,
  checkBatchFiles,
  checkProjectFiles,
  readUtf8,
} from "./files";
function file(
  name: string,
  content: string | Uint8Array = SAMPLE_COBOL,
  size?: number,
) {
  const bytes =
    typeof content === "string" ? new TextEncoder().encode(content) : content;
  return {
    name,
    size: size ?? bytes.byteLength,
    arrayBuffer: async () => bytes.buffer,
  } as File;
}
describe("upload validation", () => {
  it("checks count before size and type", async () => {
    expect(
      await checkBatchFiles(
        Array.from({ length: 6 }, () =>
          file("bad.exe", "", MAX_FILE_BYTES + 1),
        ),
      ),
    ).toBe("Choose up to 5 files.");
  });
  it("checks size before extension", async () => {
    expect(
      await checkBatchFiles([file("large.exe", "", MAX_FILE_BYTES + 1)]),
    ).toContain("200 KB");
  });
  it("allows project dependencies but rejects them for batch", async () => {
    expect(
      await checkProjectFiles([file("records.cpy"), file("records.dat")]),
    ).toBeNull();
    expect(await checkBatchFiles([file("records.cpy")])).toContain(
      ".cbl or .cob",
    );
  });
  it("respects existing project capacity", async () => {
    expect(
      await checkProjectFiles([file("a.cbl"), file("b.cbl")], 99),
    ).toContain("1 more");
  });
  it("rejects invalid UTF-8 and duplicate names", async () => {
    await expect(
      readUtf8(file("bad.cbl", new Uint8Array([255, 254]))),
    ).rejects.toThrow("UTF-8");
    expect(await checkBatchFiles([file("A.cbl"), file("a.cbl")])).toContain(
      "unique",
    );
  });
  it("reads source without changing fixed-format indentation", async () => {
    expect(await readUtf8(file("hello.cbl"))).toBe(SAMPLE_COBOL);
  });
});
