"""Documentation files, split into the examples they contain.

Only fenced blocks are examples. An inline `code` span carries no syntax to parse, and a guess at
one would trade a real miss for a false accusation against a correct README - the expensive
direction. Every block keeps the file and the line it starts on, because a finding nobody can
locate is not a finding.
"""
import dataclasses
import pathlib
import re

FENCE = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>```+|~~~+)[ \t]*(?P<info>[^\n`]*)$")
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "build", "dist", "__pycache__", ".tox"}


@dataclasses.dataclass(frozen=True)
class Example:
    path: pathlib.Path
    line: int          # 1-based line of the opening fence
    lang: str          # normalised, "" when the fence had no info string
    text: str

    @property
    def where(self):
        return f"{self.path}:{self.line}"


def find_docs(repo, patterns=None):
    """README.md and docs/**/*.md by default; explicit globs win when given."""
    repo = pathlib.Path(repo)
    if patterns:
        found = []
        for pattern in patterns:
            found.extend(sorted(repo.glob(pattern)))
        return [p for p in found if p.is_file()]
    found = []
    for candidate in sorted(repo.glob("*.md")):
        if candidate.is_file():
            found.append(candidate)
    docs_dir = repo / "docs"
    if docs_dir.is_dir():
        for path in sorted(docs_dir.rglob("*.md")):
            if not any(part in SKIP_DIRS for part in path.parts):
                found.append(path)
    return found


def normalise(info):
    """`python`, `py`, `python3` and `{.python}` all mean the same fence.

    A MyST directive such as ```{versionadded} is not a language at all, so it normalises to the
    empty string and the block is reported as unjudged rather than mislabelled.
    """
    info = info.strip()
    if info.startswith("{") and not info.startswith("{."):
        return ""
    token = info.strip("{}").lstrip(".").split()[0].lower() if info else ""
    token = token.split(",")[0]
    return {"py": "python", "python3": "python", "shell": "bash", "sh": "bash",
            "console": "bash", "shell-session": "bash", "zsh": "bash"}.get(token, token)


def examples_in(path):
    """Every fenced block in one file, in order."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out, opened, body, info, start = [], None, [], "", 0
    for number, line in enumerate(lines, start=1):
        match = FENCE.match(line)
        if opened is None:
            if match and match.group("info").count("`") == 0:
                opened, info, start, body = match.group("fence")[0] * 3, match.group("info"), number, []
            continue
        if match and match.group("fence")[0] * 3 == opened and not match.group("info").strip():
            out.append(Example(path=path, line=start, lang=normalise(info), text="\n".join(body)))
            opened = None
            continue
        body.append(line)
    return out


def collect(repo, patterns=None):
    """Every example under the repository, with paths reported relative to it."""
    repo = pathlib.Path(repo).resolve()
    examples = []
    for path in find_docs(repo, patterns):
        for example in examples_in(path):
            examples.append(dataclasses.replace(example, path=example.path.relative_to(repo)))
    return examples
