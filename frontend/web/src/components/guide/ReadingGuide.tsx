"use client";
import { useId, useRef, useState } from "react";
import { BookOpen, X, ArrowRight, CheckCircle2 } from "lucide-react";
import { m, useReducedMotion } from "motion/react";
import { Button } from "@/components/ui/Button";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { CodeEditor } from "@/components/ui/CodeEditor";
import {
  cobolTerms,
  pythonTerms,
  guideCobol,
  guidePython,
} from "./guide-content";
type Topic = "start" | "cobol" | "python" | "review";
export function ReadingGuide() {
  const [open, setOpen] = useState(false);
  const [topic, setTopic] = useState<Topic>("start");
  const dialog = useRef<HTMLDialogElement>(null);
  const id = useId();
  const reduced = useReducedMotion();
  function show() {
    setOpen(true);
    dialog.current?.showModal();
  }
  return (
    <>
      <Button size="sm" onClick={show}>
        <BookOpen size={16} aria-hidden="true" />
        Reading guide
      </Button>
      <dialog
        ref={dialog}
        className="reading-guide"
        aria-labelledby={id}
        onClose={() => setOpen(false)}
      >
        {open && (
          <m.div
            initial={{ opacity: reduced ? 1 : 0, y: reduced ? 0 : 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduced ? 0 : 0.18 }}
          >
            <header className="guide-heading">
              <div>
                <span className="guide-kicker">A practical companion</span>
                <h2 id={id}>Read the code. Follow the behavior.</h2>
                <p>Start with one program and one path through its work.</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                aria-label="Close reading guide"
                onClick={() => dialog.current?.close()}
              >
                <X size={20} aria-hidden="true" />
              </Button>
            </header>
            <SegmentedControl<Topic>
              label="Reading guide topics"
              value={topic}
              onChange={setTopic}
              options={[
                { value: "start", label: "Start here" },
                { value: "cobol", label: "Read COBOL" },
                { value: "python", label: "Read Python" },
                { value: "review", label: "Compare & verify" },
              ]}
            />
            <div className="guide-content">
              {topic === "start" ? (
                <>
                  <div className="guide-steps">
                    <div>
                      <strong>1. Find the inputs</strong>
                      <p>Look for data fields, files, and shared copybooks.</p>
                    </div>
                    <ArrowRight aria-hidden="true" size={18} />
                    <div>
                      <strong>2. Follow the work</strong>
                      <p>
                        Find the entry point, branches, routines, and calls.
                      </p>
                    </div>
                    <ArrowRight aria-hidden="true" size={18} />
                    <div>
                      <strong>3. Check the outcome</strong>
                      <p>
                        Compare values, formatting, and outputs with test data.
                      </p>
                    </div>
                  </div>
                  <div className="guide-example">
                    <section>
                      <h3>COBOL source</h3>
                      <CodeEditor
                        language="cobol"
                        value={guideCobol}
                        label="Guide COBOL example"
                      />
                    </section>
                    <section>
                      <h3>A Python pattern</h3>
                      <CodeEditor
                        language="python"
                        value={guidePython}
                        label="Guide Python example"
                      />
                    </section>
                  </div>
                  <p className="hint">
                    This example explains the structure. Generated drafts may
                    use runtime helpers for numeric precision, text width, and
                    display formatting; a similar-looking translation does not
                    establish equivalence.
                  </p>
                </>
              ) : topic === "review" ? (
                <div className="guide-checklist">
                  <h3>A small, repeatable review</h3>
                  {[
                    [
                      "Trace one scenario",
                      "Use a normal case, then an edge case such as a zero balance or missing record.",
                    ],
                    [
                      "Follow dependencies",
                      "COPY supplies definitions, CALL invokes another program, and PERFORM runs a routine. A resolved reference checks a name, not its correctness.",
                    ],
                    [
                      "Review every flag",
                      "Inspect unsupported statements and TODOs in the original source. Converter line numbers can include expanded copybooks; use the original-source links.",
                    ],
                    [
                      "Compare meaningful outputs",
                      "Check signs, decimal precision, padding, records, and file behavior. A matching test covers that test case, not every possible input.",
                    ],
                    [
                      "Keep draft status honest",
                      "Not compared means execution was unavailable. Verification and AI review refer to the saved generated draft; local Python edits are included in downloads but have not been re-verified.",
                    ],
                  ].map(([title, text]) => (
                    <div key={title}>
                      <CheckCircle2 size={19} aria-hidden="true" />
                      <div>
                        <h3>{title}</h3>
                        <p>{text}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <dl className="guide-glossary">
                  {(topic === "cobol" ? cobolTerms : pythonTerms).map(
                    ([term, meaning]) => (
                      <div key={term}>
                        <dt>{term}</dt>
                        <dd>{meaning}</dd>
                      </div>
                    ),
                  )}
                </dl>
              )}
            </div>
            <footer className="guide-resources">
              <span>Continue learning</span>
              <a
                href="https://developer.ibm.com/tutorials/my-first-cobol-app/"
                target="_blank"
                rel="noreferrer"
              >
                COBOL structure (IBM){" "}
                <span className="sr-only">(opens a new tab)</span>
              </a>
              <a
                href="https://docs.python.org/3/tutorial/controlflow.html"
                target="_blank"
                rel="noreferrer"
              >
                Python functions & control flow{" "}
                <span className="sr-only">(opens a new tab)</span>
              </a>
            </footer>
          </m.div>
        )}
      </dialog>
    </>
  );
}
