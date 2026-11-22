const terms = [
  {
    term: "PIC",
    sentence: "Describes how a field is stored, such as the number of digits.",
  },
  {
    term: "PERFORM",
    sentence: "Runs a paragraph, or repeats it.",
  },
  {
    term: "COPY",
    sentence: "Pulls in a shared definition from another file.",
  },
  {
    term: "CALL",
    sentence: "Runs another program.",
  },
  {
    term: "WORKING-STORAGE",
    sentence: "Holds fields the program uses while it runs.",
  },
  {
    term: "DISPLAY",
    sentence: "Prints a line.",
  },
  {
    term: "MOVE",
    sentence: "Copies a value into a field.",
  },
  {
    term: "IF",
    sentence: "Runs the next steps only when a condition is true.",
  },
] as const;

export type CobolTerm = (typeof terms)[number];

function termExpression(term: string, flags: string) {
  return new RegExp(`(?<![A-Z0-9-])${term}(?![A-Z0-9-])`, flags);
}

export function termsInCobol(source: string): CobolTerm[] {
  return terms.filter((entry) => termExpression(entry.term, "i").test(source));
}

export function termRanges(source: string, term: string) {
  return [...source.matchAll(termExpression(term, "gi"))].flatMap((match) =>
    match.index === undefined
      ? []
      : [{ from: match.index, to: match.index + match[0].length }],
  );
}
