"use client";
import Link from "next/link";
import { ArrowLeft, Info, CheckCircle2 } from "lucide-react";
import { useProject } from "@/hooks/useProject";
import { useConversion } from "@/hooks/useConversion";
import { useRuns } from "@/hooks/useRuns";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Spinner";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ProjectNotFound } from "@/components/layout/ProjectNotFound";
import { ProgressStatus } from "@/components/layout/ProgressStatus";
import { RunHistory } from "./RunHistory";
import { DownloadList } from "./DownloadList";
import { ExportPreview } from "./ExportPreview";
import { ReadingGuide } from "@/components/guide/ReadingGuide";
export function ExportScreen({ projectId }: { projectId: string }) {
  const p = useProject(projectId),
    c = useConversion(),
    history = useRuns(projectId);
  if (p.notFound) return <ProjectNotFound />;
  if (!p.project || p.project.id !== projectId)
    return p.error && !p.loadingId ? (
      <Card title="Couldn’t open this project">
        <p>{p.error}</p>
        <Button onClick={p.retry}>Try again</Button>
      </Card>
    ) : (
      <Skeleton label="Loading your project…" />
    );
  return (
    <>
      <PageHeader
        title="Take the next chapter with you."
        description={`${p.project.name} · Download your Python drafts and the evidence behind them.`}
        eyebrow="03 / EXPORT"
        actions={
          <>
            <ReadingGuide />
            <Link
              className="button button-secondary"
              href={`/projects/${projectId}/convert`}
            >
              <ArrowLeft size={16} aria-hidden="true" />
              Back to Convert
            </Link>
          </>
        }
      />
      <ProgressStatus />
      {c.edited && (
        <div className="notice warning">
          <Info size={18} aria-hidden="true" />
          <span>
            Downloads include your local Python edits. The audit report
            describes the saved generated draft, before those edits.
          </span>
        </div>
      )}
      <div className={c.results.length ? "export-layout" : undefined}>
        <DownloadList
          onPreview={(index) => {
            c.select(index);
            document
              .getElementById("export-preview")
              ?.scrollIntoView({ block: "start", behavior: "instant" });
          }}
          files={c.results}
          selectedIndex={c.selectedIndex}
          verification={c.verification}
          onDownloadPython={c.downloadPython}
          onDownloadReport={c.downloadReport}
        />
        {c.results[c.selectedIndex] && (
          <ExportPreview
            key={c.results[c.selectedIndex].python_name}
            file={c.results[c.selectedIndex]}
            source={p.project.files.find(
              (f) => f.name === c.results[c.selectedIndex].source_name,
            )}
            verification={c.verification}
            analysis={c.analysis}
          />
        )}
      </div>
      <div className="notice">
        <CheckCircle2 size={18} aria-hidden="true" />
        <span>
          Your project and generated runs are saved. Local edits remain in this
          tab until downloaded.
        </span>
      </div>
      {history.error && (
        <p role="alert" className="notice danger">
          {history.error}
        </p>
      )}
      <RunHistory runs={history.runs} />
      <p className="supported-note">
        Generated Python is a draft. Review business logic, unsupported lines,
        and verification results before use.
      </p>
    </>
  );
}
