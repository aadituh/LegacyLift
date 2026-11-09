export const reviewCategories = {
  numbers: {
    title: "Numbers & display formatting",
    guide: "Check decimal precision, signs, and how amounts appear in reports.",
  },
  files: {
    title: "File input & output",
    guide:
      "Connect file paths and record handling, then test with representative data.",
  },
  flow: {
    title: "Program flow & integration",
    guide: "Check branching, routine calls, and how execution starts or ends.",
  },
  other: {
    title: "Other source statements",
    guide:
      "Inspect these statements and confirm their behavior in the Python draft.",
  },
};
export function groupReviewNotes(notes: string[]) {
  return Object.entries(reviewCategories)
    .map(([key, category]) => ({
      ...category,
      notes: notes
        .filter((note) => {
          const type = /\bPIC(?:TURE)?\b|\bDECIMAL\b|\bROUNDED\b/i.test(note)
            ? "numbers"
            : /\b(?:OPEN|READ|WRITE|CLOSE|REWRITE|DELETE|FILE|SELECT|AT END)\b/i.test(
                  note,
                )
              ? "files"
              : /\b(?:CALL|PERFORM|GO TO|GOTO|STOP|GOBACK|EXIT|ENTRY|ALTER|EVALUATE)\b/i.test(
                    note,
                  )
                ? "flow"
                : "other";
          return type === key;
        })
        .map((text) => ({
          text,
          line: Number(text.match(/^Line\s+(\d+)\s*:/i)?.[1]) || null,
        })),
    }))
    .filter((group) => group.notes.length);
}
