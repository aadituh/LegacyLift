**Authors:** Spencer Peloquin

# Convert a Project
## Steps
1. Open a project that already has source files.  
2. Go to **Convert** and start **Convert project**.  
3. Review the generated Python beside the COBOL.  
4. Read review notes for lines without a conversion rule (for example file READ or some edited PIC formats on BANKMAIN).  
5. Optionally request AI review for matches and concerns by line.

## What “good” looks like on the sample bank
* Four of five programs can convert with no review notes; BANKMAIN may still show notes for file I/O and some number formats.  
* Status `draft` means every line translated; `review_required` means at least one note or AI-generated line remains.
