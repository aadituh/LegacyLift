"use client";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  Check,
  Upload,
  ArrowRightLeft,
  ShieldCheck,
  ChevronRight,
} from "lucide-react";
import { useWorkspace } from "@/hooks/useWorkspace";
import { getProgress } from "@/lib/progress";
import { projectUrl } from "@/lib/routes";
export function ProgressStatus() {
  const { state } = useWorkspace();
  const batch = usePathname() === "/batch";
  const { step, states, note } = getProgress({
    files: batch ? state.batchFiles.length : (state.project?.files.length ?? 0),
    programs: batch
      ? state.batchFiles.length
      : (state.project?.files.filter((f) => f.kind === "program").length ?? 0),
    results: batch ? state.batchResults.length : state.results.length,
    verification: batch ? null : state.verification,
    verifying: state.busy === "verifying",
    batch,
  });
  const icons = [Upload, ArrowRightLeft, ShieldCheck];
  return (
    <section
      className="progress-card"
      aria-label={`Progress ${step} of 3. ${note}`}
    >
      <div className="progress-heading">
        <span className="eyebrow">THE PATH FORWARD</span>
        <span className="hint">{step} of 3 complete</span>
      </div>
      <ol className="progress-steps">
        {["Upload source", "Convert to Python", "Verify output"].map(
          (label, i) => {
            const Icon = icons[i];
            return (
              <li
                key={label}
                aria-current={
                  states[i] === "Current" || states[i] === "Running"
                    ? "step"
                    : undefined
                }
                className={
                  states[i] === "Complete" || states[i] === "Verified"
                    ? "step-done"
                    : states[i] === "Current" || states[i] === "Running"
                      ? "step-current"
                      : states[i] === "Not compared"
                        ? "step-warning"
                        : states[i] === "Mismatch"
                          ? "step-danger"
                          : ""
                }
              >
                <span className="step-icon">
                  {states[i] === "Complete" || states[i] === "Verified" ? (
                    <Check size={19} aria-hidden="true" />
                  ) : (
                    <Icon size={19} aria-hidden="true" />
                  )}
                </span>
                <span>
                  {batch ||
                  !state.project ||
                  (i === 2 && !state.results.length) ? (
                    <strong>{label}</strong>
                  ) : (
                    <Link
                      className="progress-link"
                      href={
                        i === 0
                          ? `/upload?project=${state.project.id}`
                          : projectUrl(
                              "convert",
                              state.project.id,
                              i === 2 ? "verification" : undefined,
                            )
                      }
                    >
                      <strong>{label}</strong>
                    </Link>
                  )}
                  <small>{states[i]}</small>
                </span>
                {i < 2 && (
                  <ChevronRight
                    className="step-chevron"
                    size={18}
                    aria-hidden="true"
                  />
                )}
              </li>
            );
          },
        )}
      </ol>
      <p className="progress-note">{note}</p>
    </section>
  );
}
