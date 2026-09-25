---
doc: scope
status: approved
---

# Scope — Everything this repository claims, and what backs it

## The idea in one line

Point it at a repository and it audits the claims the repository makes about itself — badges,
documentation examples, the Python version it promises, its release notes — and reports the ones
nothing backs.

## Why this, and why as one thing

A repository is full of assertions aimed at a stranger: a licence badge, a coverage percentage, a
`requires-python`, an example in the README, a line in the changelog. Every one of them is written
once and then drifts, and none of them is checked by anything in a normal pipeline. Tests check
behaviour. Linters check style. Nothing checks the claims.

I have four separate tools that each check one of these. Separately they are scripts a maintainer
has to know about, install and remember. Together they answer a question a maintainer actually
has, in one run: *what does this repository say about itself that it cannot back up?*

## The claims and their evidence

| Claim | Where it lives | What backs it |
|---|---|---|
| this project is MIT licensed | a badge URL | the LICENSE file |
| coverage is 100% | a badge URL | nothing, when the number is typed into the URL |
| supports Python 3.7+ | a badge, and `requires-python` | the syntax the code actually uses |
| call it like this | a fenced example | the functions and flags the code defines |
| this release fixed X | the changelog | the commits in the range |

## Three severities, and a fourth list

- **contradicted** — the repository itself disproves it: a badge says MIT, the LICENSE says Apache.
- **nothing behind it** — the claim has no source at all: a coverage number typed into a URL.
- **no longer matches** — two statements of the same fact disagree: classifiers say 3.7,
  `requires-python` says 3.9.
- **not checked** — the question could not be asked here, with the reason. This is part of the
  report, not an omission from it.

## What "done" means for the proof of concept

- One command, one exit code, one self-contained page with no network requests in it.
- Runs on a repository the author did not write, and the findings survive manual checking.
- On a well-kept repository, nothing is reported.
- Every check that cannot run names itself and says why.
- A check that crashes does not take the others down with it.

## Deliberately out of scope

- Fixing anything. This is the audit, not the editor.
- Anything requiring the network: no badge is fetched, no index is queried, nothing is installed.
- Judging behaviour. Every claim here is checked against a file in the repository.

## Why it is a proof of concept

It checks the claims it knows how to check. A repository can assert a hundred other things — in
prose, in a website, in a video — and this reads none of them, which is why the report ends with
what it did not ask rather than with a score.
