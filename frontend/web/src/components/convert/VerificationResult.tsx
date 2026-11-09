"use client";
import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import type { VerifyResponse } from "@/types/api";
import { Card } from "@/components/ui/Card";
import { Badge, statusTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Spinner";
import { formatRunStatus, outputLines, verificationStatus } from "@/lib/format";
export function VerificationResult({
  fileName,
  verification,
  isVerifying = false,
  calledBy,
  level = 2,
}: {
  fileName: string;
  verification: VerifyResponse | null;
  isVerifying?: boolean;
  calledBy?: string;
  level?: 2 | 3;
}) {
  const [showAll, setShowAll] = useState(false);
  if (!verification && !isVerifying) return null;
  const file = verification?.files.find((f) => f.source_name === fileName);
  const cobol = outputLines(file?.cobol_stdout ?? ""),
    python = outputLines(file?.python_stdout ?? "");
  const count = Math.max(cobol.length, python.length),
    differing = Array.from(
      { length: count },
      (_, i) => cobol[i] !== python[i],
    ).filter(Boolean).length;
  const status = verification
    ? verificationStatus(file, verification)
    : "not_verified";
  return (
    <Card
      title={`Verification for ${fileName}`}
      level={level}
      actions={<ShieldCheck size={21} aria-hidden="true" />}
    >
      {isVerifying ? (
        <Skeleton label="Verification is running." />
      ) : calledBy && !file ? (
        <p className="notice">
          {fileName} runs inside {calledBy}. Its output is checked with the
          caller.
        </p>
      ) : (
        <>
          <div className="verification-summary">
            <Badge tone={statusTone(status)}>{formatRunStatus(status)}</Badge>
            <span className="muted">
              {status === "not_verified"
                ? "Verification is unavailable. No outputs were compared."
                : verification?.note ||
                  (status === "verified"
                    ? "COBOL and Python outputs match."
                    : "Outputs differed or a program failed.")}
            </span>
          </div>
          {file?.error &&
            (status === "not_verified" ? (
              <details>
                <summary>Verification details</summary>
                <p className="hint">{file.error}</p>
              </details>
            ) : (
              <p className="notice danger">{file.error}</p>
            ))}
          {count > 0 && (
            <>
              <p className="hint">
                {differing} of {count} output lines differ
              </p>
              <div
                className="output-table-wrap"
                tabIndex={0}
                role="region"
                aria-label={`COBOL and Python output lines for ${fileName}`}
              >
                <table className="output-table">
                  <thead>
                    <tr>
                      <th scope="col">Line</th>
                      <th scope="col">COBOL output</th>
                      <th scope="col">Python output</th>
                      <th scope="col">Comparison</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Array.from(
                      { length: showAll ? count : Math.min(count, 200) },
                      (_, i) => (
                        <tr
                          key={i}
                          className={cobol[i] !== python[i] ? "diff-row" : ""}
                        >
                          <th scope="row">{i + 1}</th>
                          <td>
                            <pre>{cobol[i] ?? ""}</pre>
                          </td>
                          <td>
                            <pre>{python[i] ?? ""}</pre>
                          </td>
                          <td>
                            {cobol[i] !== python[i] ? "Differs" : "Match"}
                          </td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>
              {count > 200 && (
                <Button size="sm" onClick={() => setShowAll(!showAll)}>
                  {showAll ? "Show first 200 rows" : `Show all ${count} rows`}
                </Button>
              )}
            </>
          )}
        </>
      )}
    </Card>
  );
}
