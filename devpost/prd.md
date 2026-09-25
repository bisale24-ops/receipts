---
doc: prd
status: approved
---

# PRD — Receipts

## User

A maintainer before a release, or a reviewer on a pull request that touches metadata or docs. They
want one answer, not four tools.

## Core loop

1. Read the repository on disk. Nothing is imported, executed, installed or fetched.
2. Run each check that can run: badges, documentation examples, Python floor, release notes.
3. Collect findings into one list with a severity and a location.
4. Print a terminal report, write a page, return an exit code CI can act on.
5. Name every check that could not run, and why.

## The checks

| Check | Question | Runs when |
|---|---|---|
| badges | Do the badges match the repository? | there is a README |
| docs | Do the examples still name code that exists? | the docs contain fenced examples |
| version | Does the code run on the Python it promises? | a floor is declared and a package ships |
| notes | Is each line of the release notes backed by a commit? | there are at least two tags |

## What the badge check will and will not read

Only a claim written into the badge's own URL. `img.shields.io/badge/License-MIT-blue` states its
claim; `codecov.io/.../badge.svg` resolves against a server, so it is listed and not judged. This
keeps the whole tool offline and keeps it from guessing.

## Acceptance criteria

1. A licence badge contradicting the LICENSE file is *contradicted*, naming both.
2. A licence badge matching the LICENSE file is silent.
3. A coverage percentage written into a badge URL is *nothing behind it*.
4. A coverage badge that resolves remotely is never accused.
5. Trove classifiers below `requires-python` are reported as drift, saying pip refuses the versions
   the classifiers advertise — because pip enforces `requires-python` and nothing else.
6. A check that raises does not stop the others; its failure appears as a skipped check.
7. Exit 1 only for *contradicted*; unbacked and drifted do not fail a build on their own.
8. The page contains no network requests.

## Non-goals

Autofix, hosted service, fetching badges, judging prose, non-Python repositories.

## Risks

- **Four checkers, one surface.** A change in any of them can change the report. Mitigated by the
  seam in `promises.py`: the audit never reaches into a checker's internals.
- **A badge vocabulary that is not standardised.** Mitigated by reading only shields.io's documented
  static form and declaring everything else unchecked.
