import { ShieldCheck } from "lucide-react";
import type { SourceFile } from "@/types/api";
import type { useConversion } from "@/hooks/useConversion";
import { Button } from "@/components/ui/Button";
import { DependencyCard } from "./DependencyCard";
import { VerificationResult } from "./VerificationResult";
import { AiReviewCard } from "./AiReviewCard";
import { ReviewNotes } from "./ReviewNotes";
import { calledProgramReports } from "@/lib/audit-report";
export function ProjectReview({
  conversion: c,
  source,
  files,
  onJumpLine,
}: {
  conversion: ReturnType<typeof useConversion>;
  source?: SourceFile;
  files: SourceFile[];
  onJumpLine: (line: number) => void;
}) {
  const current = c.results[c.selectedIndex];
  const called = calledProgramReports(
    c.verification,
    c.analysis?.dependencies,
  ).find((file) => file.program === source?.name);
  return (
    <div className="project-review-flow">
      <DependencyCard
        fileName={source?.name ?? ""}
        analysis={c.analysis}
        onJumpLine={onJumpLine}
      />
      {current && (
        <div className="review-decision-row">
          <section id="review-findings" className="review-findings">
            <ReviewNotes
              notes={current.notes}
              source={source}
              files={files}
              onJumpLine={onJumpLine}
            />
          </section>
          <div className="review-checks">
            <div id="verification">
              <VerificationResult
                fileName={source?.name ?? ""}
                verification={c.verification}
                isVerifying={c.busy === "verifying"}
                calledBy={called?.caller}
              />
            </div>
            <div className="reverify">
              <p className="hint">
                Verification compares the saved generated draft using your
                project’s test data.
              </p>
              <Button
                size="sm"
                disabled={!c.ready || Boolean(c.busy)}
                onClick={c.verify}
              >
                <ShieldCheck size={16} aria-hidden="true" />
                Run verification again
              </Button>
            </div>
          </div>
        </div>
      )}
      <AiReviewCard
        review={c.review}
        isReviewing={c.busy === "reviewing"}
        fileName={source?.name}
      />
    </div>
  );
}
