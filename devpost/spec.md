---
doc: spec
status: approved
---

# Spec — Receipts

## Command

```
receipts [--repo PATH] [--only badges docs version notes] [--html PATH] [--json] [--quiet]
```

## Modules

| Module | Responsibility |
|---|---|
| `badges.py` | Find badges in markdown, reference and HTML form; read the claim out of a static shields URL; identify the licence the repository ships. |
| `audit.py` | The `Finding` and `Section` shapes, and the badge check. |
| `promises.py` | The seam over the four checkers: each function returns a `Section`. |
| `report.py` | Terminal, JSON and HTML renderings; severities; exit code. |
| `cli.py` | Arguments, orchestration, and the guarantee that one failing check does not stop the rest. |

## Data

```python
Finding = (check, severity, claim, detail, where)     # severity: broken | unbacked | drifted
Section = (check, title, question, findings, checked, skipped, passed)
```

## Rules

1. A check is skipped, never silently empty: `Section.skipped` carries the reason and the report
   prints it.
2. `broken` is the only severity that changes the exit code.
3. The page is self-contained: no stylesheet, script or image is fetched, and badge URLs appear as
   text rather than as images.
4. Every checker is vendored as a library under `src/`, so one clone runs everything with no
   install step.

## Tests

Temporary repositories written by the tests, one per acceptance criterion, plus the rule that a
raising check is reported rather than fatal.

## CI

Run the suite on the floor and a current Python, then run the tool against this repository.
