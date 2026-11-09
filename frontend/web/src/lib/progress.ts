import type { VerifyResponse } from "@/types/api";
export function getProgress({
  files,
  programs,
  results,
  verification,
  verifying,
  batch = false,
}: {
  files: number;
  programs: number;
  results: number;
  verification: VerifyResponse | null;
  verifying: boolean;
  batch?: boolean;
}) {
  const step =
    verification && verification.status !== "not_verified"
      ? 3
      : results
        ? 2
        : programs
          ? 1
          : 0;
  const states = [
    files ? "Complete" : "Current",
    results ? "Complete" : programs ? "Current" : "Waiting",
    batch
      ? "Projects only"
      : verifying
        ? "Running"
        : verification
          ? verification.status === "not_verified"
            ? "Not compared"
            : verification.status === "verified"
              ? "Verified"
              : "Mismatch"
          : results
            ? "Ready"
            : "Waiting",
  ];
  const note = verifying
    ? "Verification is running."
    : verification
      ? verification.status === "not_verified"
        ? "Verification is unavailable. Your Python draft is ready for review and download."
        : verification.note ||
          `Verification ${verification.status.replaceAll("_", " ")}.`
      : !programs
        ? files
          ? "Upload a COBOL program before converting."
          : "Add your source files to get started."
        : !results
          ? "Your files are ready for conversion."
          : batch
            ? "Batch drafts are ready. Verification is available in projects."
            : "Review your Python and compare the program outputs.";
  return { step, states, note };
}
