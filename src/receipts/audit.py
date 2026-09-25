"""Run every check this repository can answer, and collect one list of findings.

Each check is a separate tool with its own rules; what this adds is the single question they are
all answering — what does this repository claim, and what backs it — and one place to see the
answer. A check that cannot run on a given repository says why, and that reason is part of the
report rather than a silence.
"""
import dataclasses
import pathlib
import subprocess

SEVERITY = {"broken": 0, "unbacked": 1, "drifted": 2}


@dataclasses.dataclass
class Finding:
    check: str           # which check produced it
    severity: str        # broken | unbacked | drifted
    claim: str           # what the repository asserts
    detail: str          # why it is not backed
    where: str = ""      # file:line, when there is one


@dataclasses.dataclass
class Section:
    check: str
    title: str
    question: str
    findings: list
    checked: int = 0
    skipped: str = ""    # why this check could not run
    passed: str = ""     # what it confirmed, in words


def _tags(repo):
    out = subprocess.run(["git", "-C", str(repo), "tag", "--sort=-creatordate"],
                         capture_output=True, text=True)
    return [t for t in out.stdout.split() if t][:2]


def _readme(repo):
    for name in ("README.md", "readme.md", "README.markdown"):
        path = pathlib.Path(repo) / name
        if path.is_file():
            return path
    return None


def badges_section(repo):
    from . import badges
    readme = _readme(repo)
    if readme is None:
        return Section("badges", "Badges", "Do the badges match the repository?", [],
                       skipped="no README.md to read")
    found = badges.find(readme)
    actual, licence_file = badges.licence_in(repo)
    findings, checked = [], 0
    for badge in found:
        if badge.kind == "licence" and badge.static:
            checked += 1
            if actual is None:
                findings.append(Finding(
                    "badges", "unbacked", f"badge: licence is {badge.message}",
                    "no LICENSE file in the repository to check it against",
                    f"{readme.name}:{badge.line}"))
            elif badges.same_licence(badge.message, actual) is False:
                findings.append(Finding(
                    "badges", "broken", f"badge: licence is {badge.message}",
                    f"{licence_file} contains a {actual.upper()} licence",
                    f"{readme.name}:{badge.line}"))
        elif badge.kind == "coverage" and badge.static:
            checked += 1
            findings.append(Finding(
                "badges", "unbacked", f"badge: coverage is {badge.message}",
                "the number is typed into the badge URL, so nothing produced it and nothing "
                "updates it", f"{readme.name}:{badge.line}"))
        elif badge.kind == "python" and badge.static:
            checked += 1
            from . import promises
            declared = promises.declared_floor(repo)
            claimed = promises.first_version(badge.message)
            if declared and claimed and claimed != declared:
                findings.append(Finding(
                    "badges", "drifted", f"badge: Python {badge.message}",
                    f"packaging metadata declares {declared[0]}.{declared[1]}",
                    f"{readme.name}:{badge.line}"))
    dynamic = sum(1 for b in found if not b.static)
    note = (f"{checked} badge(s) carried a claim written into the URL"
            + (f"; {dynamic} resolve remotely and were not checked" if dynamic else ""))
    return Section("badges", "Badges", "Do the badges match the repository?", findings,
                   checked=checked, passed=note)
