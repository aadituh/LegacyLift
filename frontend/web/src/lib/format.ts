import type { FileEquivalenceResponse, VerifyResponse } from "@/types/api";
export function formatRunLabel(kind: string) {
  return (
    (
      {
        convert: "Convert",
        analyze: "Analyze",
        verify: "Verify",
        ai_review: "AI review",
      } as Record<string, string>
    )[kind] ?? kind
  );
}
export function formatRunStatus(status: string) {
  return (
    (
      {
        draft: "Draft",
        review_required: "Review required",
        inventory_only: "File count only",
        not_verified: "Not compared",
        analyzed: "Analyzed",
        verified: "Verified",
        mismatch: "Mismatch",
        clear: "Clear",
        concerns: "Concerns",
      } as Record<string, string>
    )[status] ?? status
  );
}
export function formatRunTime(iso: string = "") {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
}
export const formatLineList = (lines: number[] = []) =>
  lines.length ? lines.join(", ") : "none";
export function outputLines(text: string) {
  if (!text) return [];
  const normalized = text.replace(/\r\n/g, "\n").replace(/\n$/, "");
  return normalized ? normalized.split("\n") : [];
}
export function verificationStatus(
  file: FileEquivalenceResponse | undefined,
  verification: VerifyResponse,
) {
  return verification.status === "not_verified"
    ? "not_verified"
    : file?.equivalent
      ? "verified"
      : "mismatch";
}
