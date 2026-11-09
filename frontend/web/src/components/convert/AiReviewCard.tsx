import type { AIReviewResponse } from "@/types/api";
import { Sparkles } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Spinner";
import { formatLineList } from "@/lib/format";
export function AiReviewCard({
  review,
  isReviewing,
  fileName,
}: {
  review: AIReviewResponse | null;
  isReviewing: boolean;
  fileName?: string;
}) {
  if (!review && !isReviewing) return null;
  const concerns =
    review?.files.reduce((n, f) => n + (f.concerns ?? []).length, 0) ?? 0;
  return (
    <Card title="AI review" actions={<Sparkles size={21} aria-hidden="true" />}>
      <div aria-busy={isReviewing}>
        {isReviewing ? (
          <Skeleton label="AI review is running." />
        ) : (
          <>
            <div className="verification-summary">
              <Badge tone={concerns ? "warning" : "success"}>
                {concerns ? `${concerns} concerns` : "Clear"}
              </Badge>
              {review?.model && <span className="muted">{review.model}</span>}
            </div>
            <p className="hint">
              AI findings support human review. They do not prove equivalence.
            </p>
            {review?.files.map((file) => (
              <details
                className="review-file ai-file-group"
                key={file.source_name}
                open={!fileName || fileName === file.source_name}
              >
                <summary>
                  {file.source_name}
                  <span className="count-pill">
                    {(file.concerns ?? []).length} concerns
                  </span>
                </summary>
                {!(file.concerns ?? []).length ? (
                  <p className="resolved-note">No concerns.</p>
                ) : (
                  <ul>
                    {(file.concerns ?? []).map((f, i) => (
                      <li key={i}>
                        <p>{f.detail}</p>
                        <p className="hint">
                          COBOL lines {formatLineList(f.cobol_lines)} · Python
                          lines {formatLineList(f.python_lines)}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
                {Boolean((file.matches ?? []).length) && (
                  <details>
                    <summary>
                      Supported behaviors ({(file.matches ?? []).length})
                    </summary>
                    <ul>
                      {(file.matches ?? []).map((f, i) => (
                        <li key={i}>
                          {f.detail}
                          <p className="hint">
                            COBOL lines {formatLineList(f.cobol_lines)} · Python
                            lines {formatLineList(f.python_lines)}
                          </p>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </details>
            ))}
          </>
        )}
      </div>
    </Card>
  );
}
