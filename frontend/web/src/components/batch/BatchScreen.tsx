"use client";
import Link from "next/link";
import { ArrowRightLeft, Sparkles, Info } from "lucide-react";
import { useBatchConversion } from "@/hooks/useBatchConversion";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FileInputButton } from "@/components/ui/FileInputButton";
import { ProgressStatus } from "@/components/layout/ProgressStatus";
import { FileTabs } from "@/components/convert/FileTabs";
import { CodePanel } from "@/components/convert/CodePanel";
import { ConversionProgress } from "@/components/convert/ConversionProgress";
import { DownloadList } from "@/components/export/DownloadList";
export function BatchScreen() {
  const b = useBatchConversion(),
    current = b.batchResults[b.batchIndex];
  const busy = Boolean(b.busy);
  return (
    <>
      <PageHeader
        title="A quick lift for your code."
        description="Convert a few standalone programs. No project needed."
        eyebrow="TOOLS / BATCH CONVERSION"
        actions={
          <Link href="/upload" className="text-link">
            Working with dependencies? Use a project →
          </Link>
        }
      />
      <ProgressStatus />
      <Card
        title="Choose your COBOL files"
        eyebrow="SMALL FILES. NEW POSSIBILITIES."
      >
        <p className="muted">
          These files are converted on their own and are not added to a project.
          Batch: up to 5 UTF-8 .cbl/.cob files, 200 KB each.
        </p>
        <div className="batch-actions">
          <FileInputButton
            label="Choose COBOL files"
            accept=".cbl,.cob"
            disabled={busy}
            onFiles={b.choose}
          />
          <Button onClick={b.loadSample} disabled={busy}>
            <Sparkles size={17} aria-hidden="true" />
            Load small sample
          </Button>
          <Button
            variant="primary"
            onClick={b.convert}
            disabled={busy || !b.ready || !b.batchFiles.length}
            isPending={b.busy === "batch-converting"}
          >
            <ArrowRightLeft size={17} aria-hidden="true" />
            {b.busy === "batch-converting" ? "Converting…" : "Convert files"}
          </Button>
        </div>
        {!b.ready && (
          <p className="hint">
            Connect the API to convert. You can still choose files or load the
            sample.
          </p>
        )}
        {b.batchFiles.length > 0 && (
          <p className="hint">{b.batchFiles.map((f) => f.name).join(" · ")}</p>
        )}
      </Card>
      {b.busy === "batch-converting" && <ConversionProgress />}
      <FileTabs
        labels={b.batchFiles.map((f) => ({ name: f.name }))}
        selectedIndex={b.batchIndex}
        onSelect={b.select}
      />
      <CodePanel
        cobol={b.batchSources[b.batchIndex]}
        python={current?.python}
        pythonName={current?.python_name}
        status={current ? "Draft" : undefined}
        edited={Boolean(
          current && current.python !== b.batchOriginal[current.python_name],
        )}
        onEditPython={b.editPython}
        emptyCobolText="Choose COBOL files or load a sample."
      />
      {current?.notes.length ? (
        <Card title="Lines to review">
          <ul
            className="review-notes"
            tabIndex={0}
            aria-label="Lines to review"
          >
            {current.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </Card>
      ) : null}
      <DownloadList
        files={b.batchResults}
        selectedIndex={b.batchIndex}
        showReport={false}
        onDownloadPython={b.downloadPython}
      />
      <p className="notice">
        <Info size={18} aria-hidden="true" />
        <span>
          Verify — projects only. Batch files and local edits stay in this tab
          and are cleared on refresh.
        </span>
      </p>
    </>
  );
}
