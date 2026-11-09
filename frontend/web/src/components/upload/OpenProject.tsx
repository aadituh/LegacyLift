"use client";
import { useRef, useState } from "react";
import Link from "next/link";
import { Upload, ArrowRight } from "lucide-react";
import type { ProjectResponse } from "@/types/api";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { FileInputButton } from "@/components/ui/FileInputButton";
import { TextPreview } from "@/components/ui/TextPreview";
import { Button } from "@/components/ui/Button";
import { FileList } from "./FileList";
export function OpenProject({
  project,
  disabled,
  uploading,
  onUpload,
  onRemove,
}: {
  project: ProjectResponse;
  disabled: boolean;
  uploading: boolean;
  onUpload: (files: File[]) => void;
  onRemove: (id: string) => void;
}) {
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState<
    ProjectResponse["files"][number] | null
  >(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const programs = project.files.filter(
    (file) => file.kind === "program",
  ).length;
  return (
    <>
      <Card
        title={project.name}
        eyebrow="Open project"
        className="open-project-card"
        actions={<Badge tone="info">{project.files.length} files</Badge>}
      >
        <div
          className={`dropzone compact-dropzone ${dragging ? "dragging" : ""}`}
          onDragOver={(event) => {
            event.preventDefault();
            if (!disabled) setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            if (!disabled) onUpload(Array.from(event.dataTransfer.files));
          }}
        >
          <Upload size={22} aria-hidden="true" />
          <div>
            <h3>
              {project.files.length
                ? "Add to your source"
                : "Add your source files"}
            </h3>
            <p>
              Drop .cbl, .cob, .cpy or .dat files here. Up to 100 files, 200 KB
              each.
            </p>
          </div>
          <FileInputButton
            label="Browse files"
            accept=".cbl,.cob,.cpy,.dat"
            disabled={disabled}
            isPending={uploading}
            onFiles={onUpload}
          />
        </div>
        {!!project.files.length && (
          <FileList
            files={project.files}
            disabled={disabled}
            onRemove={onRemove}
            onPreview={(file) => {
              setPreview(file);
              dialog.current?.showModal();
            }}
          />
        )}
        <div className="card-bottom">
          <p className="hint">
            {programs
              ? `${programs} programs ready for the next step.`
              : "Add a .cbl or .cob program to continue."}
          </p>
          {programs > 0 && (
            <Link
              className="button button-primary"
              href={`/projects/${project.id}/convert`}
            >
              Continue to Convert
              <ArrowRight size={17} aria-hidden="true" />
            </Link>
          )}
        </div>
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
    </>
  );
}
