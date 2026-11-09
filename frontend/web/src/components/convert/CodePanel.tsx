"use client";
import { useEffect, useRef, useState } from "react";
import {
  Copy,
  Check,
  Code2,
  FileCode2,
  Search,
  Maximize2,
  Minimize2,
  WrapText,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { CodeEditor } from "@/components/ui/CodeEditor";
export function CodePanel({
  cobol,
  sourceName,
  python,
  pythonName,
  status,
  edited,
  onEditPython,
  emptyCobolText = "Upload programs to a project.",
  view = "both",
  focusLine,
}: {
  cobol?: string;
  sourceName?: string;
  python?: string;
  pythonName?: string;
  status?: string;
  edited?: boolean;
  onEditPython: (text: string) => void;
  emptyCobolText?: string;
  view?: "both" | "cobol" | "python";
  focusLine?: { line: number; tick: number } | null;
}) {
  const [copied, setCopied] = useState("");
  const [message, setMessage] = useState("");
  const [wrap, setWrap] = useState(false);
  const [focused, setFocused] = useState(false);
  const [findSource, setFindSource] = useState(0);
  const [findPython, setFindPython] = useState(0);
  const workbench = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const update = () =>
      setFocused(document.fullscreenElement === workbench.current);
    document.addEventListener("fullscreenchange", update);
    return () => document.removeEventListener("fullscreenchange", update);
  }, []);
  async function copy(text: string, type: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(type);
      setMessage(`${type} copied.`);
    } catch {
      setMessage("Select the code and copy it with your keyboard.");
    }
  }
  async function focus() {
    try {
      if (document.fullscreenElement === workbench.current)
        await document.exitFullscreen();
      else await workbench.current?.requestFullscreen();
    } catch {
      setMessage(
        "Focus mode is unavailable in this browser. Use the single-language view for more space.",
      );
    }
  }
  return (
    <div ref={workbench} className="code-workbench">
      <div className="editor-tools">
        <span className="hint">
          Syntax highlighted · source stays unchanged
        </span>
        <div className="actions">
          <Button
            size="sm"
            variant="ghost"
            aria-pressed={wrap}
            onClick={() => setWrap(!wrap)}
          >
            <WrapText size={16} aria-hidden="true" />
            Wrap lines
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={focus}
            aria-label={focused ? "Exit focus mode" : "Focus code"}
          >
            {focused ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            {focused ? "Exit focus" : "Focus code"}
          </Button>
        </div>
      </div>
      <div className={`code-grid ${view !== "both" ? "single" : ""}`}>
        {view !== "python" && (
          <section className="code-panel">
            <header>
              <div>
                <span className="code-symbol cobol-symbol">
                  <FileCode2 size={19} aria-hidden="true" />
                </span>
                <div>
                  <p className="eyebrow">COBOL / READ ONLY</p>
                  <h2>{sourceName || "COBOL"}</h2>
                </div>
              </div>
              <div className="actions">
                <Badge>Original</Badge>
                {cobol !== undefined && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setFindSource((n) => n + 1)}
                      aria-label="Find in COBOL"
                    >
                      <Search size={16} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => void copy(cobol, "COBOL")}
                      aria-label="Copy COBOL"
                    >
                      {copied === "COBOL" ? (
                        <Check size={16} />
                      ) : (
                        <Copy size={16} />
                      )}
                    </Button>
                  </>
                )}
              </div>
            </header>
            {cobol !== undefined ? (
              <div
                className="source-code-region"
                role="region"
                aria-label="COBOL source code"
              >
                <CodeEditor
                  key={sourceName}
                  label="Read original COBOL"
                  language="cobol"
                  value={cobol}
                  wrap={wrap}
                  focusLine={focusLine}
                  findRequest={findSource}
                  scrollToFocus
                />
              </div>
            ) : (
              <div className="code-empty">
                <FileCode2 size={27} aria-hidden="true" />
                <p>{emptyCobolText}</p>
              </div>
            )}
            <footer>
              <span>
                {cobol !== undefined
                  ? `${cobol.split("\n").length} lines · fixed-format COBOL`
                  : "Fixed-format COBOL"}
              </span>
              <span>UTF-8</span>
            </footer>
          </section>
        )}
        {view !== "cobol" && (
          <section className="code-panel python-panel">
            <header>
              <div>
                <span className="code-symbol">
                  <Code2 size={19} aria-hidden="true" />
                </span>
                <div>
                  <p className="eyebrow">PYTHON / EDITABLE DRAFT</p>
                  <h2>{pythonName || "Python"}</h2>
                </div>
              </div>
              <div className="actions">
                {edited ? (
                  <Badge tone="warning">Edited</Badge>
                ) : status ? (
                  <Badge>{status}</Badge>
                ) : null}
                {python !== undefined && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setFindPython((n) => n + 1)}
                      aria-label="Find in Python"
                    >
                      <Search size={16} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => void copy(python, "Python")}
                      aria-label="Copy Python"
                    >
                      {copied === "Python" ? (
                        <Check size={17} />
                      ) : (
                        <Copy size={17} />
                      )}
                    </Button>
                  </>
                )}
              </div>
            </header>
            {python !== undefined ? (
              <CodeEditor
                key={pythonName}
                value={python}
                label={`Edit ${pythonName ?? "Python"}`}
                language="python"
                editable
                wrap={wrap}
                findRequest={findPython}
                onChange={(text) => {
                  setCopied("");
                  onEditPython(text);
                }}
              />
            ) : (
              <div className="code-empty">
                <Code2 size={27} aria-hidden="true" />
                <p>Convert this project to see the Python draft.</p>
                <span>
                  You can inspect the original source and its connections now.
                </span>
              </div>
            )}
            <footer>
              <span>
                {edited
                  ? "Local edits · download to keep changes"
                  : "Edit directly · verification describes the saved draft"}
              </span>
              <span>Python 3</span>
            </footer>
          </section>
        )}
      </div>
      {message && (
        <p className="hint editor-message" role="status">
          {message}
        </p>
      )}
    </div>
  );
}
