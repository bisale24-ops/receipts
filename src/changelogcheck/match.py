"""Claim against commits, decided on evidence rather than vocabulary.

The rule the whole tool rests on: shared ordinary English is not evidence. "improves the export"
and a commit called "tidy up exports" have a word in common and prove nothing. A claim is
supported only when something concrete ties it to the change - an issue number, a command-line
flag, a quoted string, an identifier the diff defines, or a file the diff touches.

That rule misses real matches. Missing them is the acceptable failure here: the cost of a false
"supported" is a release note nobody checks again.
"""
import re

from . import history

FLAG = re.compile(r"--([a-z][a-z0-9-]{2,})")
QUOTED = re.compile(r"[\"'`]([^\"'`]{3,60})[\"'`]")
ISSUE = re.compile(r"#(\d+)")
WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{2,}")
# English that carries no evidence, however often it appears in both the note and the commit
COMMON = {
    "the", "and", "for", "with", "that", "this", "when", "from", "into", "are", "was", "has",
    "have", "not", "now", "but", "use", "used", "using", "add", "adds", "added", "fix", "fixes",
    "fixed", "update", "updates", "updated", "improve", "improves", "improved", "change",
    "changes", "changed", "support", "supports", "supported", "remove", "removes", "removed",
    "make", "makes", "made", "new", "old", "better", "faster", "more", "less", "all", "any",
    "can", "could", "would", "should", "also", "only", "still", "yet", "than", "then", "there",
    "their", "they", "you", "your", "our", "its", "it's", "one", "two", "some", "many", "much",
    "bug", "bugs", "issue", "issues", "error", "errors", "crash", "crashes", "feature",
    "features", "release", "version", "code", "file", "files", "test", "tests", "user", "users",
    "api", "cli", "app", "docs", "doc", "readme", "performance", "behaviour", "behavior",
}


FILENAME = re.compile(r"\b([\w./-]+\.(?:py|js|ts|tsx|jsx|go|rs|rb|java|kt|swift|c|h|cpp|cs|"
                      r"php|sh|sql|yml|yaml|json|toml|md|html|css))\b", re.I)


def tokens_of(claim):
    """The concrete things a claim names, kept apart by kind so they can be weighted.

    A filename spelled out in the note - "hours.py" - is the strongest signal a human ever
    leaves in a release note, so it is kept apart from the bare word "hours".
    """
    words = set()
    for raw in WORD.findall(claim):
        word = raw.lower().strip(".,;:")
        if len(word) > 2 and word not in COMMON:
            words.add(word)
            stem = word.split(".")[0]                  # hours.py also means hours
            if len(stem) > 2 and stem not in COMMON:
                words.add(stem)
    return {
        "issues": set(ISSUE.findall(claim)),
        "flags": {f.lower() for f in FLAG.findall(claim)},
        "quoted": {q.lower() for q in QUOTED.findall(claim)},
        "files": {f.lower() for f in FILENAME.findall(claim)},
        "words": words,
    }


def evidence(claim, commit, repo=None):
    """What actually ties this claim to this commit. Empty means: nothing does."""
    claim_tokens = tokens_of(claim)
    paths = history.file_tokens(commit.files)
    found = []

    for number in claim_tokens["issues"] & commit.issues:
        found.append(("issue", f"#{number}"))
    for named in claim_tokens["files"]:
        if any(f.lower().endswith(named) or named.endswith(f.lower()) for f in commit.files):
            found.append(("file", named))
    for flag in claim_tokens["flags"]:
        if flag in commit.identifiers or any(flag in f.lower() for f in commit.files):
            found.append(("flag", f"--{flag}"))
    for word in claim_tokens["words"] | claim_tokens["quoted"]:
        if word in COMMON:
            continue
        if word in commit.identifiers:
            found.append(("identifier", word))
        elif word in paths:
            found.append(("path", word))
    return found


STRENGTH = {"issue": 3, "flag": 3, "file": 3, "identifier": 2, "path": 1}


def judge(claim, commits, min_strength=2):
    """Supported when the evidence across commits reaches the strength threshold."""
    hits = []
    for commit in commits:
        found = evidence(claim, commit)
        if found:
            hits.append((commit, found))
    strength = max((max(STRENGTH[kind] for kind, _ in found) for _, found in hits), default=0)
    hits.sort(key=lambda pair: (-max(STRENGTH[k] for k, _ in pair[1]), pair[0].churn))
    return {"supported": strength >= min_strength, "strength": strength, "hits": hits}


BUMP = re.compile(r"^(?:bump|chore\(deps\)|build\(deps\)|update)\b.*\b(?:from|to|group|dependenc|"
                  r"requirement|version)", re.I)
TEST_PATH = re.compile(r"(^|/)(tests?|testing|spec)/|(^|/)(conftest|noxfile)\.py$|"
                       r"(^|/)test_[^/]+\.py$|_test\.py$", re.I)
NOTES_PATH = re.compile(r"(^|/)(CHANGELOG|CHANGES|NEWS|HISTORY|RELEASE[-_]?NOTES)"
                        r"(\.(md|rst|txt))?$", re.I)


def user_facing(commit):
    """Did this commit change anything a release note would be expected to mention?

    A dependency bump and a test-only change both ship, and neither belongs in a changelog. Calling
    them unmentioned turns a correct changelog into a list of complaints, which is the failure that
    makes the whole report ignorable.
    """
    if BUMP.match(commit.subject or ""):
        return False
    if commit.files and all(TEST_PATH.search(path) or NOTES_PATH.search(path)
                            for path in commit.files):
        # tests and the notes file itself: a commit that edited the changelog cannot have
        # shipped without a mention in it
        return False
    return True


def unmentioned(commits, judged, min_churn=10):
    """Commits no claim reached, ignoring lockfile noise, dependency bumps and test-only work."""
    claimed = {commit.sha for verdict in judged for commit, _ in verdict["hits"]}
    out = []
    for commit in commits:
        if commit.sha in claimed or commit.merge or commit.noisy:
            continue
        if commit.churn < min_churn or not user_facing(commit):
            continue
        out.append(commit)
    out.sort(key=lambda c: -c.churn)
    return out
