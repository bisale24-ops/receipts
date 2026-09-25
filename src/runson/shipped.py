"""Which files actually ship, and which are only ever run by the maintainer.

A `noxfile.py` or a test may use whatever syntax it likes: no installer will ever import it on an
old Python. Scanning them would produce findings nobody could hit, which is a louder tool and a
less useful one.
"""
import pathlib
import re

NEVER = {".git", ".venv", "venv", "build", "dist", "__pycache__", ".tox", ".mypy_cache",
         ".pytest_cache", "site-packages", "node_modules", ".nox"}
TOOLING = {"tests", "test", "testing", "docs", "doc", "examples", "example", "scripts",
           "benchmarks", "bench", "tools", "ci", "action"}
TOOLING_FILES = {"noxfile.py", "conftest.py", "tasks.py", "fabfile.py", "setup.py"}
PACKAGE_DIR = re.compile(r'packages\s*=\s*\[([^\]]*)\]|where\s*=\s*\[?["\']([^"\']+)')


def roots(repo):
    """The directories that contain the shipped package, most specific first."""
    repo = pathlib.Path(repo)
    found = []
    for layout in ("src", "lib"):
        base = repo / layout
        if base.is_dir():
            for child in sorted(base.iterdir()):
                # a package under src/ counts even without __init__.py: implicit namespace
                # packages are a normal layout, and poetry itself ships as one.
                if child.is_dir() and child.name not in NEVER and any(child.rglob("*.py")):
                    found.append(child)
    if not found:
        for child in sorted(repo.iterdir()):
            if child.is_dir() and child.name not in NEVER | TOOLING \
                    and (child / "__init__.py").is_file():
                found.append(child)
    if not found:
        # a single-module distribution: records.py, requests_html.py and friends
        loose = [child for child in sorted(repo.glob("*.py"))
                 if child.name not in TOOLING_FILES and not child.name.startswith("test_")]
        if loose:
            found.append(repo)
    return found


def files(repo, include_tests=False):
    """Every module that ships, with the directories they came from."""
    found, where = [], roots(repo)
    for root in where:
        for path in sorted(root.rglob("*.py")):
            if root == pathlib.Path(repo) and path.parent != root:
                continue          # single-module layout: only the top level ships
            parts = set(path.parts)
            if parts & NEVER:
                continue
            if not include_tests and (parts & TOOLING or path.name in TOOLING_FILES):
                continue
            found.append(path)
    return found, where
