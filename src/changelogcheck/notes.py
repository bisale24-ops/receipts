"""A release note cut into claims.

A claim is a line that asserts something shipped. Headings are structure, not claims; so are
link definitions, code fences and the version line itself. Getting this wrong in either
direction is visible in the report, so the rules are few and stated here rather than tuned.
"""
import re

BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
HEADING = re.compile(r"^\s*#{1,6}\s")
SETEXT = re.compile(r"^\s*(=+|-+)\s*$")
LINK_DEF = re.compile(r"^\s*\[[^\]]+\]:\s*\S+")
FENCE = re.compile(r"^\s*(```|~~~)")
VERSION_ONLY = re.compile(r"^\s*\[?v?\d+\.\d+[\w.\-]*\]?\s*[-–—]?\s*(\d{4}-\d{2}-\d{2})?\s*$")
TRAILING_CREDIT = re.compile(r"\s*\(?(?:by\s+)?@[\w-]+\)?\s*$")


def claims(text):
    """Return [(line_number, claim_text)] for the lines that assert something."""
    out, in_fence = [], False
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or not line.strip():
            continue
        if HEADING.match(line) or SETEXT.match(line) or LINK_DEF.match(line):
            continue
        if VERSION_ONLY.match(line):
            continue
        if match := BULLET.match(line):
            body = match.group(1)
        elif line.startswith(("  ", "\t")):
            continue                                   # continuation of the bullet above
        else:
            body = line.strip()
            if len(body.split()) < 3:
                continue                               # a stray word is not a claim
        body = TRAILING_CREDIT.sub("", body).strip()
        body = re.sub(r"`([^`]+)`", r"\1", body)       # keep the code span, drop the backticks
        if body:
            out.append((number, body))
    return out
