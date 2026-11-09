"use client";
import { useState } from "react";
import type {
  ConvertedFile,
  SourceFile,
  AnalyzeResponse,
  VerifyResponse,
} from "@/types/api";
import { Card } from "@/components/ui/Card";
import { TextPreview } from "@/components/ui/TextPreview";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { AuditReport } from "@/components/convert/AuditReport";
import { buildAuditReportCsv, calledProgramReports } from "@/lib/audit-report";
type View = "python" | "source" | "report";
export function ExportPreview({
  file,
  source,
  verification,
  analysis,
}: {
  file: ConvertedFile;
  source?: SourceFile;
  verification: VerifyResponse | null;
  analysis: AnalyzeResponse | null;
}) {
  const [view, setView] = useState<View>("python");
  return (
    <section id="export-preview" className="export-preview">
      <Card
        title="Preview before downloading"
        actions={
          <SegmentedControl<View>
            label="Export preview"
            value={view}
            onChange={setView}
            options={[
              { value: "python", label: "Python" },
              { value: "source", label: "Original COBOL" },
              { value: "report", label: "Audit report" },
            ]}
          />
        }
      >
        <p className="hint preview-hint">
          {view === "python"
            ? "This is the exact Python text included in the download. Local edits are included."
            : view === "source"
              ? "The original source is kept unchanged for reference."
              : "The report describes the saved generated draft. Local Python edits have not been verified."}
        </p>
        {view === "report" ? (
          <>
            <AuditReport
              verification={verification}
              isVerifying={false}
              dependencies={analysis?.dependencies ?? []}
            />
            {verification && (
              <details>
                <summary>Preview audit-report.csv</summary>
                <TextPreview
                  name="audit-report.csv"
                  text={buildAuditReportCsv(
                    verification,
                    calledProgramReports(verification, analysis?.dependencies),
                  )}
                />
              </details>
            )}
          </>
        ) : (
          <TextPreview
            key={file.python_name + view}
            name={
              view === "python"
                ? file.python_name
                : (source?.name ?? file.source_name)
            }
            text={
              view === "python"
                ? file.python
                : (source?.content ?? "Source file is unavailable.")
            }
          />
        )}
      </Card>
    </section>
  );
}
