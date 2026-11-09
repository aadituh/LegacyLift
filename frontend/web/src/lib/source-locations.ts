import type { SourceFile } from "@/types/api";
export type SourceLocation = { file: SourceFile; line: number; code: string };
function lines(text: string) {
  // Match Python splitlines for ordinary COBOL text, including final-newline handling.
  const result = text.split(/\r\n|[\n\r\v\f\u0085\u2028\u2029]/);
  if (result.at(-1) === "") result.pop();
  return result;
}
function clean(raw: string) {
  if (raw.length > 6 && /^[\d ]*$/.test(raw.slice(0, 6))) {
    if ("*/".includes(raw[6])) return "";
    if (" -".includes(raw[6])) raw = raw.slice(7);
  }
  const code = raw.trim();
  return code.startsWith("*>") ? "" : code.replace(/\.$/, "").trim();
}
export function buildSourceLocations(source: SourceFile, files: SourceFile[]) {
  const books = new Map(
    files
      .filter((f) => f.kind === "copybook")
      .map((f) => [f.name.replace(/\.[^.]+$/, "").toUpperCase(), f]),
  );
  const original = (file: SourceFile) =>
    lines(file.content).map((raw, i) => ({
      file,
      line: i + 1,
      code: clean(raw),
    }));
  const expanded = original(source).flatMap((location) => {
    const name = location.code.match(/^COPY\s+([A-Z][A-Z0-9-]*)\s*$/i)?.[1];
    const book = name ? books.get(name.toUpperCase()) : null;
    // The converter expands one level; nested COPY statements remain in the copybook.
    return book ? original(book) : [location];
  });
  return (note: string): SourceLocation | null => {
    const match = note.match(/^Line\s+(\d+)\s*:\s*(.+)$/i);
    if (!match) return null;
    const location = expanded[Number(match[1]) - 1];
    if (!location?.code) return null;
    const statement = match[2].replace(/\.$/, "").trim();
    // Validate the statement too. If the converter changes its numbering, never guess.
    return statement === location.code ||
      statement.startsWith(location.code + " ")
      ? location
      : null;
  };
}
