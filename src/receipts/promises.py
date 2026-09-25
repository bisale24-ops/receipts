"""A thin seam over the checkers, so the audit never reaches into their internals.

Each function here answers one question for the report and converts whatever that checker returns
into the audit's own Finding shape. Keeping the translation in one file is what lets a checker
change without the report changing with it.
"""
import io
import contextlib
import re

from .audit import Finding, Section

VERSION = re.compile(r"(\d+)\.(\d+)")


def first_version(text):
    match = VERSION.search(text or "")
    return (int(match.group(1)), int(match.group(2))) if match else None


def declared_floor(repo):
    from runson import declared
    return declared.read(repo).floor


def documentation_section(repo):
    """Do the examples in the documentation still name code that exists?"""
    from examplecheck import docs, refs, surface, verdict
    examples = docs.collect(repo)
    if not examples:
        return Section("docs", "Documentation examples",
                       "Do the examples still name code that exists?", [],
                       skipped="no fenced examples found in the documentation")
    known = surface.read(repo)
    findings, references = [], 0
    for example in examples:
        found, skipped = refs.of(example, known)
        if skipped is not None:
            continue
        judged, _ = verdict.judge(found, known)
        references += len(judged)
        for item in judged:
            if item.verdict == "matches":
                continue
            findings.append(Finding(
                "docs", "broken" if item.verdict == "broken" else "drifted",
                f"{item.reference.kind} {item.reference.name}", item.evidence,
                item.reference.example.where))
    return Section("docs", "Documentation examples",
                   "Do the examples still name code that exists?", findings,
                   checked=references,
                   passed=f"{len(examples)} examples, {references} checkable references")


def version_section(repo):
    """Does the code run on the oldest Python the package promises?"""
    from runson import declared, features, shipped
    import ast
    import warnings

    stated = declared.read(repo)
    paths, roots = shipped.files(repo)
    if not paths:
        return Section("version", "Python floor", "Does this run on the Python it promises?", [],
                       skipped="no shipped Python package found")
    if not stated.floor:
        return Section("version", "Python floor", "Does this run on the Python it promises?", [],
                       skipped="the project declares no Python floor to check")
    findings, checked = [], 0
    advertised = stated.advertised
    if advertised and advertised != stated.floor:
        enforced = stated.text()
        shown = f"{advertised[0]}.{advertised[1]}"
        if advertised < stated.floor:
            detail = (f"the classifiers advertise {shown}, but requires-python is {enforced}, "
                      f"so pip refuses to install on the versions the classifiers promise")
        else:
            detail = (f"the classifiers advertise {shown}, but requires-python is {enforced}, "
                      f"so pip installs on versions the project no longer says it supports")
        findings.append(Finding("version", "drifted",
                                f"packaging metadata states two different floors: "
                                f"{enforced} and {shown}", detail, "packaging metadata"))
    for path in paths:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for feature in features.collect(tree, str(path.relative_to(repo))):
            if feature.needs <= stated.floor:
                continue
            checked += 1
            if feature.guard:
                continue
            findings.append(Finding(
                "version", "broken", f"{feature.name} needs {feature.needs_text}",
                f"the package promises {stated.text()}", f"{feature.path}:{feature.line}"))
    return Section("version", "Python floor", "Does this run on the Python it promises?", findings,
                   checked=len(paths),
                   passed=f"{len(paths)} shipped files against a declared floor of {stated.text()}")


def notes_section(repo, since=None, until=None):
    """Is each line of the latest release notes backed by a commit?"""
    from changelogcheck import check, history
    from .audit import _tags
    tags = _tags(repo)
    if not (since and until):
        if len(tags) < 2:
            return Section("notes", "Release notes", "Is each line backed by a commit?", [],
                           skipped="fewer than two tags, so there is no release range to read")
        until, since = tags[0], tags[1]
    try:
        text = check.read_notes(repo, None, between=until)
        with contextlib.redirect_stderr(io.StringIO()):
            result = check.run(repo, since, until, text, notes_path="CHANGELOG.md")
    except (history.GitError, OSError) as error:
        return Section("notes", "Release notes", "Is each line backed by a commit?", [],
                       skipped=str(error))
    findings = []
    for item in result["claims"]:
        if item["verdict"]["supported"]:
            continue
        findings.append(Finding("notes", "unbacked", item["claim"],
                                f"searched for {item['searched'] or 'nothing specific enough'}",
                                f"CHANGELOG.md:{item['line']}"))
    for commit in result["unmentioned"][:20]:
        findings.append(Finding("notes", "drifted", f"shipped unmentioned: {commit.subject}",
                                f"+{commit.insertions} −{commit.deletions}", commit.sha[:8]))
    return Section("notes", "Release notes", "Is each line backed by a commit?", findings,
                   checked=len(result["claims"]),
                   passed=f"{since}..{until}, {len(result['claims'])} claims, "
                          f"{len(result['commits'])} commits")
