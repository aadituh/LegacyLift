"use client";
import { useState, useRef, useEffect } from "react";
import { Copy, Check } from "lucide-react";
import { Button } from "./Button";
import { CodeEditor } from "./CodeEditor";
export function TextPreview({
  text,
  name,
  focusLine,
}: {
  text: string;
  name: string;
  focusLine?: number;
}) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const pre = useRef<HTMLPreElement>(null);
  const sourceLines = text.split("\n");
  useEffect(() => {
    if (focusLine && pre.current)
      pre.current.scrollTop = Math.max(0, (focusLine - 1) * 26.6 - 80);
  }, [focusLine]);
  return (
    <div className="text-preview">
      <div className="preview-toolbar">
        <strong>{name}</strong>
        <Button
          size="sm"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(text);
              setCopied(true);
              setError("");
            } catch {
              setError("Select the text below to copy it.");
            }
          }}
        >
          {copied ? <Check size={16} /> : <Copy size={16} />}{" "}
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      {error && (
        <p role="status" className="hint">
          {error}
        </p>
      )}
      {/\.(py|cbl|cob|cpy)$/i.test(name) ? (
        <CodeEditor
          language={/\.py$/i.test(name) ? "python" : "cobol"}
          value={text}
          label={`Preview of ${name}`}
          focusLine={focusLine ? { line: focusLine } : null}
        />
      ) : (
        <pre ref={pre} tabIndex={0} aria-label={`Preview of ${name}`}>
          {focusLine
            ? sourceLines.map((line, i) => (
                <span
                  key={i}
                  className={focusLine === i + 1 ? "focused-line" : undefined}
                >
                  {line}
                  {i < sourceLines.length - 1 ? "\n" : ""}
                </span>
              ))
            : text || "(Empty file)"}
        </pre>
      )}
    </div>
  );
}
