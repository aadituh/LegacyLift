**Authors:** Spencer Peloquin

# Processes
Key processes users and operators engage with in LegacyLift. Each linked page describes a workflow from the product requirements and design presentation.

* [[Project Upload and Analysis|Project-Upload-and-Analysis]] — create projects, upload files, list divisions/fields/dependencies  
* [[COBOL to Python Conversion|COBOL-to-Python-Conversion]] — rule-based translation, review notes, optional Gemini assist  
* [[Verification Against GnuCOBOL|Verification-Against-GnuCOBOL]] — run both programs, compare stdout, interpret statuses  
* [[Demo Project Walkthrough|Demo-Project-Walkthrough]] — October month-end close sample bank  
* [[Account and Authentication|Account-and-Authentication]] — register, login, private projects  

## Solution process flow (design presentation)
Legacy source → upload checks → project service → analysis / conversion → storage → output check (and optional AI review) → download. The API is the only layer that touches the converter and the database; uploaded code runs only in the runner service.
