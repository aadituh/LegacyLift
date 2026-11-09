"use client";
import { useState } from "react";
import { FileCode2, FileText, Database, Trash2, Eye } from "lucide-react";
import type { SourceFile } from "@/types/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
export function FileList({
  files,
  disabled,
  onRemove,
  onPreview,
}: {
  files: SourceFile[];
  disabled?: boolean;
  onRemove?: (id: string) => void;
  onPreview?: (file: SourceFile) => void;
}) {
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("all");
  const filtered = files.filter(
    (file) =>
      file.name.toLowerCase().includes(query.toLowerCase()) &&
      (kind === "all" || file.kind === kind),
  );
  const counts = ["program", "copybook", "data"].map(
    (kind) => files.filter((f) => f.kind === kind).length,
  );
  return (
    <div className={`file-list ${files.length > 50 ? "large-file-list" : ""}`}>
      <div className="file-list-summary">
        <strong>{files.length} files</strong>
        <span>
          {counts[0]} programs · {counts[1]} copybooks · {counts[2]} data
        </span>
      </div>
      {(files.length > 8 || query || kind !== "all") && (
        <div className="file-browser-tools">
          <label>
            <span className="sr-only">Find project files</span>
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search filenames…"
              name="file-query"
              autoComplete="off"
              spellCheck={false}
            />
          </label>
          <label>
            <span className="sr-only">File type</span>
            <select
              aria-label="File type"
              value={kind}
              onChange={(event) => setKind(event.target.value)}
            >
              <option value="all">All file types</option>
              <option value="program">Programs</option>
              <option value="copybook">Copybooks</option>
              <option value="data">Test data</option>
            </select>
          </label>
        </div>
      )}
      {!filtered.length && <p className="hint">No files match this search.</p>}
      <ul>
        {filtered.map((file) => {
          const Icon =
            file.kind === "program"
              ? FileCode2
              : file.kind === "data"
                ? Database
                : FileText;
          return (
            <li key={file.id}>
              <span className={`file-icon ${file.kind}`}>
                <Icon size={19} aria-hidden="true" />
              </span>
              <span className="file-name" title={file.name}>
                {file.name}
              </span>
              <Badge tone={file.kind === "program" ? "info" : "neutral"}>
                {file.kind}
              </Badge>
              {onPreview && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onPreview(file)}
                  aria-label={`Preview ${file.name}`}
                >
                  <Eye size={17} />
                  <span className="file-preview-label">Preview</span>
                </Button>
              )}
              {onRemove && (
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={disabled}
                  aria-label={`Remove ${file.name}`}
                  onClick={() => {
                    if (
                      window.confirm(
                        `Remove "${file.name}" from this project? Generated results will need to be refreshed.`,
                      )
                    )
                      onRemove(file.id);
                  }}
                >
                  <Trash2 size={16} aria-hidden="true" />
                </Button>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
