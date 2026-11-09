export const cobolTerms = [
  [
    "IDENTIFICATION DIVISION",
    "Names the program. PROGRAM-ID is its identifier.",
  ],
  ["ENVIRONMENT DIVISION", "Describes the environment and file connections."],
  [
    "DATA DIVISION",
    "Defines records, fields, and working storage. PIC describes a field's representation.",
  ],
  [
    "PROCEDURE DIVISION",
    "Contains the work. Named paragraphs collect related instructions.",
  ],
  [
    "COPY / CALL / PERFORM",
    "Include shared definitions / invoke another program / run a local routine or loop.",
  ],
  [
    "Fixed-format source",
    "Columns matter. A comment marker can appear in column 7; the viewer preserves the original spacing.",
  ],
];
export const pythonTerms = [
  [
    "def and indentation",
    "def introduces a function. Indented lines form its body; indentation also groups conditions and loops.",
  ],
  [
    "if / elif / else",
    "Choose which branch runs. Check the conditions against the original business rules.",
  ],
  [
    "for / while",
    "Repeat work. Review the start, stop condition, and number of repetitions.",
  ],
  [
    "Imports and helpers",
    "Generated drafts can import the LegacyLift runtime. Helpers such as cobol_number and cobol_text preserve aspects of COBOL values.",
  ],
  [
    "Comments and TODOs",
    "# starts a comment. A generated TODO marks work that still needs review; it is not implemented behavior.",
  ],
  [
    "Names and records",
    "COBOL-style field names may become Python names or dictionary keys. Follow the values rather than matching line numbers.",
  ],
];
export const guideCobol = `       IDENTIFICATION DIVISION.
       PROGRAM-ID. TOTAL-DEMO.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 TOTAL PIC 9(3) VALUE 100.
       PROCEDURE DIVISION.
           DISPLAY TOTAL
           STOP RUN.
`;
export const guidePython = `# A simplified illustration
def main():
    total = 100
    print(total)

main()
`;
