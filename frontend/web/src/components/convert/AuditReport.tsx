import type { DependencyLink, VerifyResponse } from "@/types/api";
import { calledProgramReports } from "@/lib/audit-report";
import { VerificationResult } from "./VerificationResult";
import { EmptyState } from "@/components/ui/EmptyState";
export function AuditReport({
  verification,
  isVerifying,
  dependencies,
}: {
  verification: VerifyResponse | null;
  isVerifying: boolean;
  dependencies: DependencyLink[];
}) {
  const called = calledProgramReports(verification, dependencies);
  return (
    <section className="stack">
      <h2>Audit report</h2>
      {isVerifying ? (
        <p role="status">Verification is running.</p>
      ) : !verification ? (
        <EmptyState>Convert this project before viewing the report.</EmptyState>
      ) : (
        <>
          {verification.files.map((file) => (
            <VerificationResult
              key={file.source_name}
              fileName={file.source_name}
              verification={verification}
              level={3}
            />
          ))}
          {!verification.files.length && (
            <p className="notice warning">
              {verification.note || "No program outputs were compared."}
            </p>
          )}
          {called.map((item) => (
            <p className="notice" key={item.program}>
              {item.program} runs inside {item.caller}.
            </p>
          ))}
        </>
      )}
    </section>
  );
}
