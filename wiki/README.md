# LegacyLift GitHub Wiki (Lab 3)

These Markdown pages are the source for the repository [GitHub Wiki](https://github.com/aadituh/LegacyLift/wiki).

Style follows [Team Copper's CreditTrax wiki](https://github.com/bnguyen117/s25-Team-Copper/wiki): Home, Table of Contents, Glossary, References, Team Members, plus Process / Interface / Task collections.

Content is derived from:
* Lab 1 – LegacyLift (product description, glossary, references, case study)
* Product requirements §3 (functional / non-functional / design constraints)
* Formal design presentation (MFCD, process flow, GUI, verify vs AI review, demo script)

## Publish / refresh the live wiki

GitHub creates `LegacyLift.wiki.git` only after the first wiki page exists. Once that exists:

```bash
git clone git@github.com:aadituh/LegacyLift.wiki.git
cp wiki/*.md LegacyLift.wiki/
cd LegacyLift.wiki
git add .
git commit -m "Sync Lab 3 wiki pages from main."
git push
```
