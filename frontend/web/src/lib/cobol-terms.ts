import { cobolTerms as guideTerms } from "@/components/guide/guide-content";
import { reservedTerms } from "./cobol-reserved";

export type CobolTerm = {
  term: string;
  sentence: string;
};

const explainedTerms: CobolTerm[] = [
  { term: "PROGRAM-ID", sentence: "The program's name." },
  {
    term: "WORKING-STORAGE SECTION",
    sentence: "Where the program keeps fields while it runs.",
  },
  {
    term: "PIC",
    sentence: "Describes how a field is stored, such as the number of digits.",
  },
  { term: "VALUE", sentence: "The starting value stored in a field." },
  { term: "DISPLAY", sentence: "Prints a line." },
  { term: "STOP RUN", sentence: "Ends the program." },
];

function finishSentence(piece: string) {
  const trimmed = piece.trim();
  const capitalized = trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
  return /[.!?]$/.test(capitalized) ? capitalized : `${capitalized}.`;
}

function termsFromGuide(): CobolTerm[] {
  return guideTerms.flatMap(([label, sentence]) => {
    if (label.includes(" / ")) {
      const words = label.split(" / ");
      const parts = sentence.split(" / ");
      return words.map((word, index) => ({
        term: word,
        sentence: finishSentence(parts[index] ?? sentence),
      }));
    }
    if (label !== label.toUpperCase()) return [];
    return [{ term: label, sentence }];
  });
}

const overrides = new Map<string, string>(
  [...termsFromGuide(), ...explainedTerms].map((entry) => [
    entry.term,
    entry.sentence,
  ]),
);
const reservedNames = new Set<string>(reservedTerms.map((entry) => entry.term));

export const cobolDictionary: CobolTerm[] = [
  ...reservedTerms.map((entry) => ({
    term: entry.term,
    sentence: overrides.get(entry.term) ?? entry.sentence,
  })),
  ...[...termsFromGuide(), ...explainedTerms].filter(
    (entry) => !reservedNames.has(entry.term),
  ),
].sort((a, b) => a.term.localeCompare(b.term));

function termExpression(term: string, flags: string) {
  const body = term
    .trim()
    .split(/\s+/)
    .map((word) => word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("\\s+");
  return new RegExp(`(?<![A-Z0-9-])${body}(?![A-Z0-9-])`, flags);
}

export function matchingTerms(query: string): CobolTerm[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return cobolDictionary;
  return cobolDictionary.filter((entry) =>
    entry.term.toLowerCase().includes(needle),
  );
}

function codeSource(source: string) {
  const chars = source.split("");
  let index = 0;
  while (index < chars.length) {
    const lineEnd = source.indexOf("\n", index);
    const end = lineEnd === -1 ? source.length : lineEnd;
    const contentEnd = end > index && chars[end - 1] === "\r" ? end - 1 : end;
    blankNonCode(chars, index, contentEnd);
    index = end + 1;
  }
  return chars.join("");
}

function blankNonCode(chars: string[], start: number, end: number) {
  if (
    end - start > 6 &&
    (chars[start + 6] === "*" || chars[start + 6] === "/")
  ) {
    for (let i = start + 6; i < end; i++) chars[i] = " ";
    return;
  }
  let i = start;
  while (i < end) {
    if (chars[i] === "*" && chars[i + 1] === ">") {
      for (let j = i; j < end; j++) chars[j] = " ";
      return;
    }
    const quote = chars[i];
    if (quote === '"' || quote === "'") {
      chars[i] = " ";
      i += 1;
      while (i < end) {
        if (chars[i] === quote) {
          chars[i] = " ";
          if (chars[i + 1] === quote && i + 1 < end) {
            chars[i + 1] = " ";
            i += 2;
            continue;
          }
          i += 1;
          break;
        }
        chars[i] = " ";
        i += 1;
      }
      continue;
    }
    i += 1;
  }
}

export function termsInCobol(source: string): CobolTerm[] {
  const code = codeSource(source);
  return cobolDictionary.filter((entry) =>
    termExpression(entry.term, "i").test(code),
  );
}

export function termRanges(source: string, term: string) {
  return [...codeSource(source).matchAll(termExpression(term, "gi"))].flatMap(
    (match) =>
      match.index === undefined
        ? []
        : [{ from: match.index, to: match.index + match[0].length }],
  );
}
