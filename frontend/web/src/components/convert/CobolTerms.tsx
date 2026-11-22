"use client";
import { useEffect, useId, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import {
  cobolDictionary,
  matchingTerms,
  termRanges,
  termsInCobol,
} from "@/lib/cobol-terms";

export function CobolTerms({
  source,
  onSelect,
}: {
  source: string;
  onSelect?: (term: string | null) => void;
}) {
  const listId = useId();
  const field = useRef<HTMLSpanElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const dismissedAt = useRef(0);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [browsing, setBrowsing] = useState(false);
  const inFile = termsInCobol(source);
  const needle = query.trim().toLowerCase();
  const menuTerms =
    browsing || !needle
      ? inFile
      : inFile.filter((entry) => entry.term.toLowerCase().includes(needle));
  const found = matchingTerms(query);
  const selected = cobolDictionary.find((entry) => entry.term === open);
  const count = selected ? termRanges(source, selected.term).length : 0;
  function choose(term: string | null) {
    setOpen(term);
    onSelect?.(term);
  }
  function lookUp(value: string) {
    setBrowsing(false);
    setQuery(value);
    const exact = cobolDictionary.find(
      (entry) => entry.term.toLowerCase() === value.trim().toLowerCase(),
    );
    choose(exact ? exact.term : null);
    setMenuOpen(
      inFile.some((entry) =>
        entry.term.toLowerCase().includes(value.trim().toLowerCase()),
      ),
    );
  }
  function showFileTerms() {
    if (menuOpen && browsing) {
      setMenuOpen(false);
      return;
    }
    setBrowsing(true);
    setMenuOpen(true);
  }
  function pick(term: string) {
    setQuery(term);
    choose(term);
    setMenuOpen(false);
  }
  useEffect(() => {
    function insideMenu(target: EventTarget | null) {
      return (
        target instanceof Node &&
        (!!field.current?.contains(target) || !!menu.current?.contains(target))
      );
    }
    function close(event: PointerEvent) {
      if (insideMenu(event.target)) {
        dismissedAt.current = 0;
        return;
      }
      dismissedAt.current = performance.now();
      setMenuOpen(false);
    }
    document.addEventListener("pointerdown", close, true);
    return () => document.removeEventListener("pointerdown", close, true);
  }, []);
  return (
    <div className="cobol-terms">
      <div
        className="cobol-dictionary"
        onBlur={(event) => {
          const next = event.relatedTarget;
          if (next instanceof Node && event.currentTarget.contains(next))
            return;
          setMenuOpen(false);
        }}
      >
        <span className="hint">COBOL dictionary</span>
        <span className="cobol-dictionary-field" ref={field}>
          <input
            role="combobox"
            aria-label="COBOL dictionary"
            aria-expanded={menuOpen}
            aria-controls={listId}
            value={query}
            placeholder="Type or choose a term"
            autoComplete="off"
            onChange={(event) => lookUp(event.target.value)}
            onFocus={() => {
              if (performance.now() - dismissedAt.current < 300) return;
              setMenuOpen(menuTerms.length > 0);
            }}
            onKeyDown={(event) => {
              if (event.key === "Escape") setMenuOpen(false);
            }}
          />
          <button
            type="button"
            aria-label="Show terms in this file"
            aria-expanded={menuOpen}
            onClick={showFileTerms}
          >
            <ChevronDown size={18} aria-hidden="true" />
          </button>
        </span>
        {menuOpen && menuTerms.length > 0 && (
          <div
            className="cobol-dictionary-menu"
            id={listId}
            role="listbox"
            ref={menu}
          >
            {menuTerms.map((entry) => (
              <button
                key={entry.term}
                type="button"
                role="option"
                aria-selected={open === entry.term}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => pick(entry.term)}
              >
                {entry.term}
              </button>
            ))}
          </div>
        )}
      </div>
      {query.trim() && !found.length && (
        <p>This dictionary does not have that term.</p>
      )}
      {selected && (
        <>
          <p>{selected.sentence}</p>
          {count === 0 ? (
            <p>This term is not in this file.</p>
          ) : (
            <p className="cobol-term-count">
              Found <mark>{count}</mark> {count === 1 ? "time" : "times"} in
              this file.
            </p>
          )}
        </>
      )}
    </div>
  );
}
