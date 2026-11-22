"use client";
import { useState } from "react";
import { termsInCobol } from "@/lib/cobol-terms";
import { Button } from "@/components/ui/Button";
export function CobolTerms({
  source,
  onSelect,
}: {
  source: string;
  onSelect?: (term: string | null) => void;
}) {
  const found = termsInCobol(source);
  const [open, setOpen] = useState<string | null>(null);
  const selected = found.find((entry) => entry.term === open);
  function choose(term: string) {
    const next = open === term ? null : term;
    setOpen(next);
    onSelect?.(next);
  }
  if (!found.length) return null;
  return (
    <div className="cobol-terms">
      <p className="hint">Words in this file</p>
      <div className="cobol-terms-list" role="group" aria-label="COBOL terms">
        {found.map((entry) => (
          <Button
            key={entry.term}
            size="sm"
            variant="ghost"
            aria-pressed={open === entry.term}
            onClick={() => choose(entry.term)}
          >
            {entry.term}
          </Button>
        ))}
      </div>
      {selected && <p>{selected.sentence}</p>}
    </div>
  );
}
