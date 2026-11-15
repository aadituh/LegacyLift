**Authors:** Spencer Peloquin, Aaditya Ghimire

# Tasks
Instructions for specific tasks within each interface, aligned with the functional requirements and the live demo script.

* [[Run LegacyLift Locally|Run-LegacyLift-Locally]]  
* [[Load Demo Project|Load-Demo-Project]]  
* [[Upload Project Files|Upload-Project-Files]]  
* [[Convert a Project|Convert-a-Project]]  
* [[Verify COBOL and Python Output|Verify-COBOL-and-Python-Output]]  
* [[Download Generated Python|Download-Generated-Python]]  
* [[Convert Standalone Programs|Convert-Standalone-Programs]]  
* [[Create an Account and Sign In|Create-an-Account-and-Sign-In]]  

## Live demo sequence (design presentation)
1. Upload all 10 sample bank files as one project  
2. Review dependencies (BANKMAIN calls TXNPOST and INTCALC)  
3. Convert — COBOL beside Python, with review notes  
4. Run both — same data, clear result per program (`docker compose up --build`)  
5. Optional AI review — advice by line on top of verify  
