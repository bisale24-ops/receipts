"""Findings first, then the count, then what was refused - in that order.

The not-judged list is part of the report rather than an omission from it: a reader can only trust
the silence if they can see what the tool declined to have an opinion about.
"""
import json


ORDER = ("broken", "renamed", "matches")
TITLE = {"broken": "BROKEN", "renamed": "RENAMED", "matches": "MATCHES"}


def render(findings, unjudged, examples, quiet=False):
    lines = []
    grouped = {verdict: [f for f in findings if f.verdict == verdict] for verdict in ORDER}

    for verdict in ORDER:
        group = grouped[verdict]
        if not group or (quiet and verdict == "matches"):
            continue
        lines.append(f"{TITLE[verdict]}  {len(group)}")
        for finding in sorted(group, key=lambda f: (str(f.reference.example.path), f.reference.example.line)):
            reference = finding.reference
            lines.append(f"  {reference.example.where}  {reference.kind} {reference.name}")
            lines.append(f"      {finding.evidence}")
            if reference.detail:
                lines.append(f"      {reference.detail}")
        lines.append("")

    if unjudged and not quiet:
        lines.append(f"NOT JUDGED  {len(unjudged)}")
        for example, reason in sorted(unjudged, key=lambda pair: (str(pair[0].path), pair[0].line)):
            lines.append(f"  {example.where}  {reason}")
        lines.append("")

    counted = {verdict: len(grouped[verdict]) for verdict in ORDER}
    lines.append(
        f"{len(examples)} examples · {sum(counted.values())} references · "
        f"{counted['broken']} broken · {counted['renamed']} renamed · {len(unjudged)} not judged"
    )
    return "\n".join(lines)


def as_json(findings, unjudged, examples):
    findings = sorted(findings, key=lambda f: (ORDER.index(f.verdict),
                                               str(f.reference.example.path),
                                               f.reference.example.line))
    return json.dumps({
        "examples": len(examples),
        "findings": [
            {"verdict": f.verdict, "kind": f.reference.kind, "name": f.reference.name,
             "path": str(f.reference.example.path), "line": f.reference.example.line,
             "evidence": f.evidence}
            for f in findings
        ],
        "not_judged": [
            {"path": str(example.path), "line": example.line, "reason": reason}
            for example, reason in unjudged
        ],
    }, indent=2)


def exit_code(findings):
    return 1 if any(f.verdict == "broken" for f in findings) else 0
