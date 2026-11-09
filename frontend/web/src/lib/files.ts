export const MAX_BATCH_FILES = 5;
export const MAX_PROJECT_FILES = 100;
export const MAX_FILE_BYTES = 200_000;
export const SAMPLE_COBOL = `       IDENTIFICATION DIVISION.
       PROGRAM-ID. HELLO-TEAM.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 TEAM-NAME PIC X(20) VALUE "LegacyLift".
       PROCEDURE DIVISION.
           DISPLAY "Hello, " TEAM-NAME
           STOP RUN.
`;
export async function readUtf8(file: File): Promise<string> {
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(
      await file.arrayBuffer(),
    );
  } catch {
    throw new Error(`${file.name} must be UTF-8 text.`);
  }
}
async function check(
  files: File[],
  existing: number,
  batch: boolean,
): Promise<string | null> {
  if (batch && files.length > MAX_BATCH_FILES) return "Choose up to 5 files.";
  if (!batch && files.length + existing > MAX_PROJECT_FILES)
    return `A project can take up to 100 files. This project already has ${existing}${existing < 100 ? `, so ${100 - existing} more can be added.` : "."}`;
  const large = files.filter((f) => f.size > MAX_FILE_BYTES);
  if (large.length)
    return `${large.map((f) => f.name).join(", ")} must be 200 KB or less.`;
  const invalid = files.filter(
    (f) => !(batch ? /\.(cbl|cob)$/i : /\.(cbl|cob|cpy|dat)$/i).test(f.name),
  );
  if (invalid.length)
    return `${invalid.map((f) => f.name).join(", ")} must be a ${batch ? ".cbl or .cob" : ".cbl, .cob, .cpy, or .dat"} file.`;
  if (new Set(files.map((f) => f.name.toLowerCase())).size !== files.length)
    return "Each file must have a unique name.";
  try {
    await Promise.all(files.map(readUtf8));
  } catch (error) {
    return (error as Error).message;
  }
  return null;
}
export const checkBatchFiles = (files: File[]) => check(files, 0, true);
export const checkProjectFiles = (files: File[], existing = 0) =>
  check(files, existing, false);
