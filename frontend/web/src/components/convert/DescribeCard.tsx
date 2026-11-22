"use client";
import { useState } from "react";
import { BookOpen } from "lucide-react";
import { describeProject } from "@/lib/api/projects";
import type { DescribeResponse } from "@/types/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
export function DescribeCard({ projectId }: { projectId: string }) {
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
    <Card
      title="What this project does"
      actions={<BookOpen size={21} aria-hidden="true" />}
    >
      <p className="hint">
        A short description of each program and the files they share. This does
        not change the conversion.
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
    </Card>
  );
}
