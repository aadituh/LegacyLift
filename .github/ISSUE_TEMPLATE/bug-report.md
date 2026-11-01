---
name: Bug report
about: Something that works differently from what it should
title: ""
labels: [bug]
assignees: []
---

**What happened:** <one sentence>

## Steps to reproduce

1. <a step anyone can follow, with the file or request used>

## Expected

<what should happen, such as the GnuCOBOL output>

## Actual

<what happens instead: output, error message, or traceback>

## Definition of done

- [ ] A test fails before the fix and passes after it.
- [ ] Work is on a branch named `<area>/<issue number>-<short-name>`.
- [ ] The pull request says `Closes #<this issue>` and a teammate was asked to review it.
- [ ] Checks pass (backend: pytest, ruff, mypy; frontend: `npm run lint` and `npm run build`).
