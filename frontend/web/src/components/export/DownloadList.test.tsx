import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import type { ConvertedFile } from "@/types/api";
import { DownloadList } from "./DownloadList";

const saveBlob = vi.fn();
vi.mock("@/lib/download", () => ({
  saveBlob: (...args: unknown[]) => saveBlob(...args),
}));

function draft(name: string, python: string): ConvertedFile {
  return {
    program_name: name,
    python,
    notes: [],
    source_name: `${name}.cbl`,
    python_name: `${name}.py`,
  };
}

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

beforeEach(() => {
  saveBlob.mockReset();
});

it("packs every Python draft into one zip", async () => {
  render(
    <DownloadList
      showReport={false}
      files={[
        draft("MONTHEND", "print('balance')\n"),
        draft("BANKMAIN", "print('statement')\n"),
      ]}
      onDownloadPython={() => undefined}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: /Download \.zip/ }));
  const [blob, name] = saveBlob.mock.calls[0] as [Blob, string];
  expect(name).toBe("python-drafts.zip");
  expect(await unzip(blob)).toEqual([
    { name: "MONTHEND.py", text: "print('balance')\n" },
    { name: "BANKMAIN.py", text: "print('statement')\n" },
  ]);
});

it("leaves a single Python file on its own download button", () => {
  render(
    <DownloadList
      showReport={false}
      files={[draft("MONTHEND", "print('balance')\n")]}
      onDownloadPython={() => undefined}
    />,
  );
  expect(screen.queryByRole("button", { name: /Download \.zip/ })).toBeNull();
});
