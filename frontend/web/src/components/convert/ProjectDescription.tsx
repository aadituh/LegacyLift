"use client";
import { useState } from "react";
import { BookOpen, X } from "lucide-react";
import { describeProject } from "@/lib/api/projects";
import type { DescribeResponse } from "@/types/api";
import { Button } from "@/components/ui/Button";
export function ProjectDescription({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<DescribeResponse | null>(null);
  async function describe() {
    setBusy(true);
    setError("");
    try {
      setResult(await describeProject(projectId));
    } catch (caught) {
      setResult(null);
      setError((caught as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="project-description">
      {open ? (
        <section
          className="project-description-panel"
          aria-label="What this project does"
        >
          <header className="project-description-heading">
            <h2>What this project does</h2>
            <Button
              variant="ghost"
              size="sm"
              aria-label="Close description"
              onClick={() => setOpen(false)}
            >
              <X size={18} aria-hidden="true" />
            </Button>
          </header>
          <div className="project-description-body">
            <p className="hint">
              A short description of each program and the files they share. Auto
              mode writes it: Groq for a smaller description, and Gemini
              (gemini-3.5-flash-lite) for a larger one. This does not change the
              conversion.
            </p>
            <Button onClick={() => void describe()} isPending={busy}>
              {busy ? "Describing…" : "Describe project"}
            </Button>
            {error && (
              <p className="notice danger" role="alert">
                {error}
              </p>
            )}
            {result && (
              <>
                <ul className="description-list">
                  {result.programs.map((program) => (
                    <li key={program.name}>
                      <strong>{program.name}</strong>
                      <span>{program.summary}</span>
                    </li>
                  ))}
                </ul>
                {result.shared_data && <p>{result.shared_data}</p>}
              </>
            )}
          </div>
        </section>
      ) : (
        <button
          type="button"
          className="project-description-toggle"
          onClick={() => setOpen(true)}
        >
          <BookOpen size={16} aria-hidden="true" />
          What this project does
        </button>
      )}
    </div>
  );
}
