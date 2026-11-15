**Authors:** Spencer Peloquin

# COBOL to Python Conversion
Conversion walks each program and emits a Python draft. Supported constructs become runnable Python; unsupported lines become review notes so humans know what still needs work. The same COBOL with the same copybooks always produces the same Python—nothing is guessed by the rule engine.

## Rule-based conversion (requirements §3.1.6)
* Translate each COBOL program into a `.py` file with the same base name.  
* Expand each COPY from the project copybook before translating.  
* Keep each untranslated line as a review note (original text + COBOL line number).  
* Mark a program `draft` when every line was translated; `review_required` when any review note remains.  
* Optionally convert 1 to 5 programs without creating a project.

## Converter behaviour (design presentation)
The converter cleans lines, tokenizes statements, and maps them to Python. DISPLAY becomes a display helper; MOVE / ADD / SUBTRACT become assignments. Unsupported code is rendered as review notes / `#TODO`-style markers. COBOL-style output is preserved (for example, 14 in `PIC 9(4)` prints as `0014`) so verify can compare character for character.

## AI-assisted translation (requirements §3.1.7)
* Send each review note to Gemini with the program’s data fields and up to three similar verified examples (RAG / pgvector).  
* Replace the note with an `AI-generated` proposal when the model returns a translation; leave the note unchanged on error.  
* Programs with AI-generated lines remain `review_required`.

## Features and limitations (design presentation)
* Preserve core logic and structure; identify dependencies; transform into modern Python constructs.  
* Maintain documentation/comments and support human validation.  
* Limitation: cannot invent missing functionality or generate entirely new business rules.
