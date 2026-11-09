import { FileCode2, Download, FileSpreadsheet } from "lucide-react";
import type { ConvertedFile, VerifyResponse } from "@/types/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
export function DownloadList({
  files,
  selectedIndex = 0,
  verification,
  showReport = true,
  onDownloadPython,
  onDownloadReport,
  onPreview,
}: {
  files: ConvertedFile[];
  selectedIndex?: number;
  verification?: VerifyResponse | null;
  showReport?: boolean;
  onDownloadPython: (index: number) => void;
  onDownloadReport?: () => void;
  onPreview?: (index: number) => void;
}) {
  return (
    <Card title="Downloads" actions={<Download size={21} aria-hidden="true" />}>
      {!files.length ? (
        <EmptyState>
          Convert a program first. The Python files will show up here.
        </EmptyState>
      ) : (
        <ul className="download-list">
          {files.map((file, i) => (
            <li
              className={selectedIndex === i ? "selected" : ""}
              key={file.python_name}
            >
              <span className="file-icon program">
                <FileCode2 size={22} aria-hidden="true" />
              </span>
              <div>
                <h3>{file.python_name}</h3>
                <p className="hint">Python draft · from {file.source_name}</p>
              </div>
              {onPreview && (
                <Button size="sm" onClick={() => onPreview(i)}>
                  Preview<span className="sr-only"> {file.python_name}</span>
                </Button>
              )}
              <Button size="sm" onClick={() => onDownloadPython(i)}>
                <Download size={16} aria-hidden="true" />
                Download .py<span className="sr-only"> {file.python_name}</span>
              </Button>
            </li>
          ))}
        </ul>
      )}
      {showReport && (
        <div className="report-download">
          <span className="file-icon data">
            <FileSpreadsheet size={22} aria-hidden="true" />
          </span>
          <div>
            <h3>audit-report.csv</h3>
            <p className="hint">
              {verification
                ? "Saved draft verification · output comparison"
                : "Verify the project first to create the report."}
            </p>
          </div>
          <Button size="sm" onClick={onDownloadReport} disabled={!verification}>
            <Download size={16} aria-hidden="true" />
            Download .csv
          </Button>
        </div>
      )}
    </Card>
  );
}
