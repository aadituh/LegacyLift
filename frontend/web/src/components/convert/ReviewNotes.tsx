"use client";
import { useMemo, useRef, useState } from "react";
import { AlertTriangle } from "lucide-react";
import type { SourceFile } from "@/types/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { TextPreview } from "@/components/ui/TextPreview";
import { groupReviewNotes } from "@/lib/review-notes";
import {
  buildSourceLocations,
  type SourceLocation,
} from "@/lib/source-locations";
export function ReviewNotes({
  notes,
  source,
  files,
  onJumpLine,
}: {
  notes: string[];
  source?: SourceFile;
  files: SourceFile[];
  onJumpLine: (line: number) => void;
}) {
  const locate = useMemo(
    () => (source ? buildSourceLocations(source, files) : () => null),
    [source, files],
  );
  const [preview, setPreview] = useState<SourceLocation | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  return (
    <>
      <Card
        title="Lines to review"
        actions={
          <span className="badge badge-warning">{notes.length} flagged</span>
        }
      >
        {!notes.length ? (
          <p className="resolved-note">
            No unsupported lines were flagged. Review the generated code before
            use.
          </p>
        ) : (
          <>
            <p className="hint">
              These statements need human review. Converter line numbers include
              expanded copybooks; source links take you to the original file.
            </p>
            <div className="review-groups">
              {groupReviewNotes(notes).map((group) => (
                <details key={group.title} className="review-group">
                  <summary>
                    <AlertTriangle size={17} aria-hidden="true" /> {group.title}{" "}
                    <span className="count-pill">{group.notes.length}</span>
                  </summary>
                  <p className="hint">{group.guide}</p>
                  <ul>
                    {group.notes.map((note, i) => {
                      const location = locate(note.text);
                      return (
                        <li key={i}>
                          <code>
                            {note.text.replace(/^Line\s+\d+\s*:\s*/i, "")}
                          </code>
                          <span className="hint">
                            {note.line
                              ? `Converter line ${note.line}`
                              : "Converter diagnostic"}
                          </span>
                          {location ? (
                            <Button
                              size="sm"
                              onClick={() => {
                                if (location.file.id === source?.id)
                                  onJumpLine(location.line);
                                else {
                                  setPreview(location);
                                  dialog.current?.showModal();
                                }
                              }}
                            >
                              {location.file.id === source?.id
                                ? `View source line ${location.line}`
                                : `View ${location.file.name}, line ${location.line}`}
                            </Button>
                          ) : (
                            <span className="hint">
                              Locate this statement in the source; an exact
                              original location is unavailable.
                            </span>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </details>
              ))}
            </div>
          </>
        )}
      </Card>
      <dialog
        ref={dialog}
        className="file-dialog"
        aria-label="Review source preview"
      >
        <div className="dialog-heading">
          <h2>Original source location</h2>
          <Button onClick={() => dialog.current?.close()}>Close preview</Button>
        </div>
        {preview && (
          <TextPreview
            key={preview.file.id + ":" + preview.line}
            name={preview.file.name}
            text={preview.file.content}
            focusLine={preview.line}
          />
        )}
      </dialog>
    </>
  );
}
