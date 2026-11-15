**Author(s):** Spencer Peloquin

# Project Upload and Analysis
Users create or open a project and add COBOL programs, copybooks, and data files. LegacyLift stores the project with the owning account and can list structure and dependency links so reviewers see how files connect.

## Create a project and upload files (requirements §3.1.3–3.1.4)
* Create a project with a name of 1 to 100 characters; list, open, and delete saved projects.  
* Deleting a project also deletes its files and runs.  
* Accept only `.cbl` / `.cob` (programs), `.cpy` (copybooks), and `.dat` (data).  
* Reject files larger than 100 KB, non–UTF-8 text, duplicate names, names over 255 characters or with non-printable characters, and uploads that would exceed 10 files.  
* If any file in an upload fails a check, add none of the files and return an error naming the file and the failed check.

## Program analysis (requirements §3.1.5)
* List the divisions of each uploaded COBOL program.  
* List each data field with level number, name, and PICTURE clause.  
* List paragraphs and every COPY, CALL, and PERFORM reference.  
* Flag each reference whose copybook, program, or paragraph is not in the project.

## Why analysis first (design presentation)
You need to know which files belong together before converting them. On the sample bank, dependency analysis reports 16 links with none unresolved.
