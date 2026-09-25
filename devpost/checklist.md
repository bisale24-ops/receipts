---
doc: checklist
status: approved
---

# Build checklist

1. **Badges** — markdown, reference-style and HTML; static claims read, dynamic ones listed. *done, 7 tests*
2. **Seam** — one function per check returning a Section, so the report never touches a checker's internals. *done*
3. **Audit** — licence, coverage and python badges against the repository. *done*
4. **Report** — terminal, JSON and a self-contained page with severities, a filter and a copy-for-PR button. *done*
5. **CLI** — `--only`, `--html`, `--json`, exit code, and a failing check that does not stop the others. *done, 12 tests*
6. **Real repositories** — thirty public projects. *done*
7. **Findings verified by hand** — urllib3's hardcoded coverage badge, python-docx's classifiers below its own requires-python. *done*
8. **A correction found while building** — pip enforces requires-python, not the lowest number stated anywhere. Fixed here and in the standalone checker. *done*
9. **Video and submission.** *in progress*
