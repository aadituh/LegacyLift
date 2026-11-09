import type { ReactNode } from "react";
export type Tone = "neutral" | "success" | "warning" | "danger" | "info";
export function statusTone(status: string): Tone {
  return ["verified", "clear"].includes(status)
    ? "success"
    : status === "mismatch"
      ? "danger"
      : ["review_required", "concerns", "not_verified"].includes(status)
        ? "warning"
        : status === "analyzed"
          ? "info"
          : "neutral";
}
export function Badge({
  tone = "neutral",
  children,
}: {
  tone?: Tone;
  children: ReactNode;
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
