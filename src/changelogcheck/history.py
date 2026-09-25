"""What actually shipped between two refs, straight out of git.

No network, no API, no key: the evidence is the repository on the machine running this. Every
commit is reduced to the things a release note could honestly be matched against - the files it
touched, the identifiers it added or removed, the issue numbers it mentions - and never to the
ordinary English in its subject line.
"""
import dataclasses
import pathlib
import re
import subprocess

NOISE_PATHS = re.compile(
    r"(^|/)(package-lock\.json|yarn\.lock|poetry\.lock|uv\.lock|Cargo\.lock|go\.sum|"
    r"\.min\.(js|css)|dist/|build/|vendor/|node_modules/)", re.I)
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
ISSUE = re.compile(r"#(\d+)")
# a diff line that adds or removes a definition, a flag, or a constant
DEFINITION = re.compile(
    r"^[+-]\s*(?:def|class|func|fn|type|interface|const|let|var|public|private|export)?\s*"
    r"([A-Za-z_][A-Za-z0-9_]{2,})\s*[=(:{]|^[+-].*?--([a-z][a-z0-9-]{2,})")


CODE_LIKE = re.compile(r"`([^`]{2,40})`|\b([A-Za-z_][A-Za-z0-9_]*(?:[._][A-Za-z0-9_]+)+)\b"
                       r"|\b([a-z]+[A-Z][A-Za-z0-9]*)\b|--([a-z][a-z0-9-]{2,})")


def code_like(text):
    """Tokens in a commit message that are not ordinary English: `verify=False`, foo.bar, --flag.

    A commit subject is written by a person, like the release note is, so matching the two is
    only fair when the token could not have been shared by accident.
    """
    found = set()
    for groups in CODE_LIKE.findall(text or ""):
        for piece in groups:
            piece = piece.strip().lower()
            if len(piece) > 2:
                found.add(piece)
                for part in re.split(r"[^a-z0-9]+", piece):
                    if len(part) > 2:
                        found.add(part)
    return found


@dataclasses.dataclass
class Commit:
    sha: str
    subject: str
    body: str
    files: list
    identifiers: set
    issues: set
    insertions: int
    deletions: int
    merge: bool

    @property
    def churn(self):
        return self.insertions + self.deletions

    @property
    def noisy(self):
        return bool(self.files) and all(NOISE_PATHS.search(f) for f in self.files)


class GitError(RuntimeError):
    pass


def git(repo, *args, allow_fail=False):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode and not allow_fail:
        raise GitError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def resolve(repo, ref):
    out = git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}", allow_fail=True).strip()
    if not out:
        raise GitError(f"cannot resolve {ref!r} in {repo}")
    return out


def shallow(repo):
    return (pathlib.Path(repo) / ".git" / "shallow").exists()


def collect(repo, since, until):
    """Every commit reachable from `until` and not from `since`, with its evidence."""
    resolve(repo, since)
    resolve(repo, until)
    raw = git(repo, "log", "--no-decorate", "--numstat", "--parents",
              "--format=%x00%H%x1f%P%x1f%s%x1f%b%x02", f"{since}..{until}")
    commits = []
    for chunk in raw.split("\x00")[1:]:
        head, _, stat = chunk.partition("\x02")
        sha, parents, subject, body = (head.split("\x1f") + ["", "", "", ""])[:4]
        files, insertions, deletions = [], 0, 0
        for line in stat.splitlines():
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            added, removed, path = parts
            files.append(path)
            insertions += int(added) if added.isdigit() else 0
            deletions += int(removed) if removed.isdigit() else 0
        commits.append(Commit(
            sha=sha.strip(), subject=subject.strip(), body=body.strip(), files=files,
            identifiers=(identifiers_of(repo, sha.strip()) if files else set())
                        | code_like(f"{subject} {body}"),
            issues=set(ISSUE.findall(f"{subject} {body}")),
            insertions=insertions, deletions=deletions,
            merge=len(parents.split()) > 1))
    return commits


def identifiers_of(repo, sha, cap=4000):
    """Names the commit defines, removes or flags - the vocabulary of the change itself."""
    diff = git(repo, "show", "--unified=0", "--format=", sha, allow_fail=True)
    names = set()
    for line in diff.splitlines()[:cap]:
        if match := DEFINITION.match(line):
            names.add((match.group(1) or match.group(2)).lower())
    return names


def file_tokens(files):
    """Path pieces a release note might plausibly name: stems and directory names."""
    tokens = set()
    for path in files:
        parts = pathlib.PurePath(path).parts
        tokens.update(p.lower() for p in parts[:-1] if len(p) > 2)
        stem = pathlib.PurePath(path).stem.lower()
        if len(stem) > 2:
            tokens.add(stem)
            tokens.update(piece for piece in re.split(r"[-_.]", stem) if len(piece) > 2)
    return tokens
