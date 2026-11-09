"use client";
import { useCallback, useEffect, useMemo, useRef } from "react";
import CodeMirror, { type ReactCodeMirrorRef } from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { cobol } from "@codemirror/legacy-modes/mode/cobol";
import { StreamLanguage, syntaxHighlighting } from "@codemirror/language";
import { classHighlighter } from "@lezer/highlight";
import { StateEffect, StateField } from "@codemirror/state";
import { Decoration, EditorView, type DecorationSet } from "@codemirror/view";
import { openSearchPanel } from "@codemirror/search";
const highlightLine = StateEffect.define<number | null>();
const sourceHighlight = StateField.define<DecorationSet>({
  create: () => Decoration.none,
  update(value, transaction) {
    value = value.map(transaction.changes);
    for (const effect of transaction.effects)
      if (effect.is(highlightLine)) {
        value =
          effect.value && effect.value <= transaction.state.doc.lines
            ? Decoration.set([
                Decoration.line({ class: "focused-line" }).range(
                  transaction.state.doc.line(effect.value).from,
                ),
              ])
            : Decoration.none;
      }
    return value;
  },
  provide: (field) => EditorView.decorations.from(field),
});
const cobolLanguage = StreamLanguage.define(cobol);
export function CodeEditor({
  value,
  language,
  label,
  editable = false,
  onChange,
  wrap = false,
  focusLine,
  findRequest = 0,
  scrollToFocus = false,
}: {
  value: string;
  language: "cobol" | "python";
  label: string;
  editable?: boolean;
  onChange?: (text: string) => void;
  wrap?: boolean;
  focusLine?: { line: number; tick?: number } | null;
  findRequest?: number;
  scrollToFocus?: boolean;
}) {
  const editor = useRef<ReactCodeMirrorRef>(null);
  const extensions = useMemo(
    () => [
      language === "python" ? python() : cobolLanguage,
      syntaxHighlighting(classHighlighter),
      sourceHighlight,
      EditorView.contentAttributes.of({
        "aria-label": label,
        "aria-readonly": String(!editable),
        tabindex: "0",
        "data-language": language,
      }),
      ...(wrap ? [EditorView.lineWrapping] : []),
    ],
    [language, label, editable, wrap],
  );
  const reveal = useCallback(
    (view: EditorView) => {
      if (
        !focusLine ||
        focusLine.line < 1 ||
        focusLine.line > view.state.doc.lines
      )
        return;
      const line = view.state.doc.line(focusLine.line);
      view.dispatch({
        selection: { anchor: line.from },
        effects: [
          highlightLine.of(focusLine.line),
          EditorView.scrollIntoView(line.from, { y: "center" }),
        ],
      });
      if (scrollToFocus) {
        view.dom.scrollIntoView({ block: "center", behavior: "instant" });
        view.focus();
      }
    },
    [focusLine, scrollToFocus],
  );
  useEffect(() => {
    const view = editor.current?.view;
    if (!view) return;
    if (focusLine) reveal(view);
    else view.dispatch({ effects: highlightLine.of(null) });
  }, [focusLine, value, reveal]);
  useEffect(() => {
    if (findRequest && editor.current?.view)
      openSearchPanel(editor.current.view);
  }, [findRequest]);
  return (
    <CodeMirror
      ref={editor}
      className="syntax-editor"
      translate="no"
      value={value}
      extensions={extensions}
      theme="none"
      editable={editable}
      readOnly={!editable}
      indentWithTab={false}
      onChange={onChange}
      onCreateEditor={reveal}
      basicSetup={{
        foldGutter: false,
        highlightActiveLine: editable,
        highlightActiveLineGutter: editable,
        autocompletion: editable,
        closeBrackets: editable,
        bracketMatching: true,
        searchKeymap: true,
        tabSize: 4,
      }}
    />
  );
}
