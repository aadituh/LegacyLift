**Author(s):** Spencer Peloquin

# Upload Project Files
## Steps
1. Create or select a project on the Upload page (name 1–100 characters).  
2. Choose **Upload project files** and select COBOL, copybook, and data files.  
3. Wait for success, or read the error that names the file and the check that failed.  
4. Open Analyze or Convert when the files appear on the project.

## Checks that reject an upload (requirements §3.1.4)
* Wrong extension (must be `.cbl` / `.cob`, `.cpy`, or `.dat`)  
* Larger than 100 KB  
* Not UTF-8 text  
* Duplicate name in the project  
* More than 10 files total  
* Name longer than 255 characters or containing a non-printable character  

If any file fails, none of the files in that upload are added.
