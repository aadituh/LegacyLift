import { expect, it } from "vitest";
import { zipTextFiles } from "./zip";

async function unzip(blob: Blob) {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  const view = new DataView(bytes.buffer);
  const decoder = new TextDecoder();
  const files: { name: string; text: string }[] = [];
  let offset = 0;
  while (
    offset + 4 <= bytes.length &&
    view.getUint32(offset, true) === 0x04034b50
  ) {
    const size = view.getUint32(offset + 22, true);
    const nameLength = view.getUint16(offset + 26, true);
    const extraLength = view.getUint16(offset + 28, true);
    const nameStart = offset + 30;
    const dataStart = nameStart + nameLength + extraLength;
    files.push({
      name: decoder.decode(bytes.subarray(nameStart, nameStart + nameLength)),
      text: decoder.decode(bytes.subarray(dataStart, dataStart + size)),
    });
    offset = dataStart + size;
  }
  return files;
}

it("packs each text file into a zip Windows can open", async () => {
  const files = await unzip(
    zipTextFiles([
      { name: "MONTHEND.py", text: "print('balance')\n" },
      { name: "BANKMAIN.py", text: "print('statement')\n" },
    ]),
  );
  expect(files).toEqual([
    { name: "MONTHEND.py", text: "print('balance')\n" },
    { name: "BANKMAIN.py", text: "print('statement')\n" },
  ]);
});

it("renames a second file that would otherwise overwrite the first", async () => {
  const files = await unzip(
    zipTextFiles([
      { name: "MAIN.py", text: "one" },
      { name: "MAIN.py", text: "two" },
    ]),
  );
  expect(files.map((file) => file.name)).toEqual(["MAIN.py", "MAIN-2.py"]);
  expect(files.map((file) => file.text)).toEqual(["one", "two"]);
});
