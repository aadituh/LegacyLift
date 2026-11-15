**Authors:** Aaditya Ghimire

# Batch Conversion Page
The **Batch conversion** page converts a few standalone COBOL programs without creating a project. Open it from **Batch conversion** in the main navigation.

Use a project instead when your programs share copybooks, call each other, or need verification. The link **Working with dependencies? Use a project** at the top of the page opens Upload.

## Parts of the page
| Part | What it does |
| --- | --- |
| **Choose COBOL files** | Selects up to 5 `.cbl` or `.cob` files, UTF-8 text, 200 KB each. |
| **Load small sample** | Chooses one sample program, `hello_team.cbl`, to try. |
| **Convert files** | Converts the chosen files. |
| File tabs | Switch between the converted programs. |
| Code panel | Shows the COBOL beside the Python draft. The Python side can be edited. |
| **Lines to review** | Lists the COBOL lines the converter did not translate for the selected program. |
| **Downloads** | **Download .py** for each converted program. |

## Limits
* Nothing on this page is saved. Files, results, and edits stay in the browser tab and are cleared on refresh.
* Batch files are not verified and have no audit report.
* Copybooks and data files cannot be added here.

Steps: [[Convert Standalone Programs|Convert-Standalone-Programs]].
