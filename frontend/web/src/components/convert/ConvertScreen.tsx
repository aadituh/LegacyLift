"use client";
import { useState } from "react";
import { ProjectFiles } from "@/components/upload/ProjectFiles";
import { ProjectReview } from "./ProjectReview";
import Link from "next/link";
import {
  ArrowRight,
  ArrowRightLeft,
  Sparkles,
  RefreshCw,
  Info,
} from "lucide-react";
import { useProject } from "@/hooks/useProject";
import { useConversion } from "@/hooks/useConversion";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { Skeleton } from "@/components/ui/Spinner";
import { ProgressStatus } from "@/components/layout/ProgressStatus";
import { ProjectNotFound } from "@/components/layout/ProjectNotFound";
import { FileTabs } from "./FileTabs";
import { CodePanel } from "./CodePanel";
import { ConversionProgress } from "./ConversionProgress";
import { AuditReport } from "./AuditReport";
import { formatRunStatus } from "@/lib/format";
import { ReadingGuide } from "@/components/guide/ReadingGuide";
type View = "both" | "cobol" | "python" | "report";
export function ConvertScreen({ projectId }: { projectId: string }) {
  const p = useProject(projectId),
    c = useConversion();
  const [view, setView] = useState<View>("both");
  const [focusLine, setFocusLine] = useState<{
    line: number;
    tick: number;
    sourceKey: string;
  } | null>(null);
  function jumpLine(line: number) {
    setView("both");
    setFocusLine((previous) => ({
      line,
      tick: (previous?.tick ?? 0) + 1,
      sourceKey: `${projectId}:${source?.name}`,
    }));
  }
  if (p.notFound) return <ProjectNotFound />;
  if (!p.project || p.project.id !== projectId)
    return p.error && !p.loadingId ? (
      <Card title="Couldn’t open this project">
        <p>{p.error}</p>
        <Button onClick={p.retry}>
          <RefreshCw size={16} />
          Try again
        </Button>
      </Card>
    ) : (
      <Skeleton label="Loading project and saved results…" />
    );
  const current = c.results[c.selectedIndex],
    source = current
      ? p.programs.find((f) => f.name === current.source_name)
      : p.programs[c.selectedIndex];
  const disabled = !c.ready || Boolean(c.busy),
    converting = c.busy === "converting";
  return (
    <div className="convert-workspace">
      <PageHeader
        title="From legacy to possibility."
        description={`${p.project.name} · Review your source, understand the links, and shape what comes next.`}
        eyebrow="02 / CONVERT & REVIEW"
        actions={
          <>
            <ReadingGuide />
            {c.results.length > 0 && (
              <Link
                className="button button-secondary"
                href={`/projects/${projectId}/export`}
              >
                Go to Export <ArrowRight size={17} aria-hidden="true" />
              </Link>
            )}
          </>
        }
      />
      <ProgressStatus />
      <ProjectFiles
        key={p.project.id}
        compact={p.programs.length > 0}
        files={p.project.files}
        disabled={!c.ready || Boolean(c.busy)}
        uploading={c.busy === "uploading"}
        onUpload={(files) => {
          if (
            !c.edited ||
            window.confirm(
              "Adding files will reset generated results and local Python edits. Download your edits first. Continue?",
            )
          )
            void p.upload(files);
        }}
        onRemove={(id) => {
          if (
            !c.edited ||
            window.confirm(
              "Removing this file will discard local Python edits. Continue?",
            )
          )
            void p.removeFile(id);
        }}
      />
      {p.programs.length > 0 && (
        <>
          <div className="conversion-toolbar">
            <SegmentedControl<View>
              label="Code view"
              value={view}
              onChange={setView}
              options={[
                { value: "both", label: "Side by side" },
                { value: "cobol", label: "COBOL" },
                { value: "python", label: "Python" },
                { value: "report", label: "Audit report" },
              ]}
            />
            <div className="actions">
              <Button
                onClick={c.reviewProject}
                disabled={disabled || !c.results.length}
                isPending={c.busy === "reviewing"}
              >
                <Sparkles size={17} aria-hidden="true" />
                {c.busy === "reviewing" ? "Reviewing…" : "Review with AI"}
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  if (
                    !c.edited ||
                    window.confirm(
                      "Converting again replaces local Python edits. Download them first. Continue?",
                    )
                  )
                    void c.convert();
                }}
                disabled={disabled || !p.programs.length}
                isPending={converting}
              >
                <ArrowRightLeft size={17} aria-hidden="true" />
                {converting ? "Converting…" : "Convert project"}
              </Button>
            </div>
          </div>
          {(!c.ready || !p.programs.length || !c.results.length) && (
            <p className="toolbar-hint">
              {!c.ready
                ? "Connect the API to convert or review."
                : !p.programs.length
                  ? "Upload a .cbl or .cob program to enable conversion."
                  : "Convert your project to enable AI review."}
            </p>
          )}
          {converting && <ConversionProgress />}
          {c.edited && (
            <div className="notice warning">
              <Info size={18} aria-hidden="true" />
              <span>
                You have local Python edits. Verification and AI review describe
                the saved generated draft. Download your edits before refreshing
                or converting again.
              </span>
            </div>
          )}
          {view === "report" ? (
            <AuditReport
              verification={c.verification}
              isVerifying={c.busy === "verifying"}
              dependencies={c.analysis?.dependencies ?? []}
            />
          ) : (
            <>
              <FileTabs
                labels={
                  c.results.length
                    ? c.results.map((f) => ({ name: f.source_name }))
                    : p.programs.map((f) => ({ name: f.name }))
                }
                selectedIndex={c.selectedIndex}
                onSelect={c.select}
              />
              <CodePanel
                sourceName={source?.name}
                focusLine={
                  focusLine?.sourceKey === `${projectId}:${source?.name}`
                    ? focusLine
                    : null
                }
                cobol={source?.content}
                python={current?.python}
                pythonName={current?.python_name}
                status={
                  current
                    ? formatRunStatus(
                        current.notes.length ? "review_required" : "draft",
                      )
                    : undefined
                }
                edited={c.selectedEdited}
                onEditPython={c.editPython}
                view={view}
              />
              <div className="file-review-summary">
                <span>
                  {source?.name}{" "}
                  {current
                    ? `· ${current.notes.length} statements flagged for review`
                    : "· original source"}
                </span>
                {current && (
                  <a href="#review-findings">
                    Review this file <ArrowRight size={14} aria-hidden="true" />
                  </a>
                )}
              </div>
              <ProjectReview
                conversion={c}
                source={source}
                files={p.project.files}
                onJumpLine={jumpLine}
              />
            </>
          )}
        </>
      )}
      <p className="supported-note">
        Supports fields, groups, OCCURS, IF / EVALUATE, PERFORM, CALL, and COPY.
        Unsupported statements stay visible as review notes.
      </p>
    </div>
  );
}
