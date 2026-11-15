**Author(s):** Spencer Peloquin

# Interfaces
Dedicated pages for each primary interface in the LegacyLift web app. The design presentation describes three main project screens—Upload, Convert, and Export—plus login. Analyze surfaces dependency and program structure results from the API.

* [[Upload Page|Upload-Page]]  
* [[Analyze Page|Analyze-Page]]  
* [[Convert Page|Convert-Page]]  
* [[Export Page|Export-Page]]  
* [[Login and Registration|Login-and-Registration]]  

## Tech stack (design presentation)
* Frontend — React + Vite (hosted on GitHub Pages)  
* API — Python 3.12 + FastAPI (hosted on Render)  
* Database — PostgreSQL on Neon  
* CI — GitHub Actions  

The web app sends a request; the API checks it, runs one workflow step, saves the result, and answers with JSON.
