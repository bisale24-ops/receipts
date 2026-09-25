"""Tie the pieces together: history, claims, evidence, verdict."""
import pathlib

from . import history, match, notes


def read_notes(repo, notes_path=None, text=None, between=None):
    """The note under test: given directly, or the section of CHANGELOG.md for this version."""
    if text is not None:
        return text
    path = pathlib.Path(notes_path) if notes_path else pathlib.Path(repo) / "CHANGELOG.md"
    if not path.exists():
        raise history.GitError(f"no release notes at {path}")
    content = path.read_text(errors="replace")
    return section_for(content, between) if between else content


def section_for(content, version):
    """The block of a keep-a-changelog file that belongs to one version."""
    lines = content.splitlines()
    wanted, out = version.lstrip("v"), []
    inside = False
    for line in lines:
        heading = line.startswith("#") and wanted in line
        if heading:
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside:
            out.append(line)
    return "\n".join(out) if out else content


def run(repo, since, until, notes_text, min_strength=2, min_churn=10, notes_path="the notes"):
    commits = history.collect(repo, since, until)
    claim_list = notes.claims(notes_text)
    judged = []
    for line_number, claim in claim_list:
        verdict = match.judge(claim, commits, min_strength=min_strength)
        tokens = match.tokens_of(claim)
        searched = ", ".join(sorted(
            [f"#{i}" for i in tokens["issues"]]
            + [f"--{f}" for f in tokens["flags"]]
            + sorted(tokens["words"] | tokens["quoted"])[:6]))
        judged.append({"line": line_number, "claim": claim, "verdict": verdict,
                       "searched": searched})
    return {
        "range": f"{since}..{until}",
        "notes_path": str(notes_path),
        "commits": commits,
        "claims": judged,
        "unmentioned": match.unmentioned(commits, [j["verdict"] for j in judged],
                                         min_churn=min_churn),
        "insertions": sum(c.insertions for c in commits),
        "deletions": sum(c.deletions for c in commits),
        "shallow": history.shallow(repo),
    }
