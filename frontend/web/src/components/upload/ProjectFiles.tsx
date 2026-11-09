"use client";
import { useRef, useState } from "react";
import type { SourceFile } from "@/types/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FileInputButton } from "@/components/ui/FileInputButton";
import { TextPreview } from "@/components/ui/TextPreview";
import { FileList } from "./FileList";
export function ProjectFiles({
  files,
  disabled,
  uploading,
  onUpload,
  onRemove,
  compact = false,
}: {
  files: SourceFile[];
  disabled: boolean;
  uploading: boolean;
  onUpload: (files: File[]) => void;
  onRemove: (id: string) => void;
  compact?: boolean;
}) {
  const [preview, setPreview] = useState<SourceFile | null>(null);
  const [dragging, setDragging] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const drop = (
    <div
      className={`project-drop ${dragging ? "dragging" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (!disabled) onUpload(Array.from(e.dataTransfer.files));
      }}
    >
      <strong>
        {files.length
          ? "Drop more files here, or choose Add files."
          : "Add COBOL files to begin"}
      </strong>
      <p className="hint">
        Programs (.cbl, .cob) are converted. Copybooks (.cpy) supply shared
        definitions. Data (.dat) supplies test inputs.
      </p>
      <span className="hint">
        UTF-8 text · up to 100 files · 200 KB per file
      </span>
    </div>
  );
  return (
    <section
      id="project-files"
      className={`project-files ${compact ? "compact" : ""}`}
    >
      <Card
        title="Project files"
        eyebrow={compact ? undefined : "01 / START WITH YOUR SOURCE"}
        actions={
          <>
            {compact && (
              <span className="project-file-counts">
                {files.filter((f) => f.kind === "program").length} programs ·{" "}
                {files.filter((f) => f.kind === "copybook").length} copybooks ·{" "}
                {files.filter((f) => f.kind === "data").length} data files
              </span>
            )}
            <FileInputButton
              label="Add files"
              accept=".cbl,.cob,.cpy,.dat"
              disabled={disabled}
              isPending={uploading}
              onFiles={onUpload}
            />
          </>
        }
      >
        {!compact && drop}
        {!!files.length && (
          <details
            className="project-file-details"
            open={!compact && files.length <= 3}
          >
            <summary>Browse, preview & manage {files.length} files</summary>
            {compact && drop}
            <FileList
              files={files}
              disabled={disabled}
              onRemove={onRemove}
              onPreview={(file) => {
                setPreview(file);
                dialog.current?.showModal();
              }}
            />
          </details>
        )}
      </Card>
      <dialog
        ref={dialog}
        className="file-dialog"
        aria-label="Source file preview"
      >
        <div className="dialog-heading">
          <h2>Source file preview</h2>
          <Button onClick={() => dialog.current?.close()}>Close preview</Button>
        </div>
        {preview && (
          <TextPreview
            key={preview.id}
            name={preview.name}
            text={preview.content}
          />
        )}
      </dialog>
    </section>
  );
}
