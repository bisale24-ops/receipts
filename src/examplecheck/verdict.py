"""Present, absent, or absent with one near neighbour.

`renamed` is kept apart from `broken` because the two need different fixes and because the near
match is a guess. One candidate above the threshold is a suggestion; two or more is an admission
that the tool does not know, and it says so rather than picking.
"""
import dataclasses
import difflib

NEAR = 0.8


@dataclasses.dataclass(frozen=True)
class Finding:
    verdict: str          # matches | broken | renamed
    reference: object
    evidence: str


def _near(name, candidates):
    leaf = name.rpartition(".")[2]
    scored = []
    for candidate in candidates:
        tail = candidate.rpartition(".")[2]
        if tail == leaf:
            continue
        ratio = difflib.SequenceMatcher(None, leaf.lower(), tail.lower()).ratio()
        if ratio >= NEAR:
            scored.append((ratio, candidate))
    scored.sort(reverse=True)
    return [candidate for _, candidate in scored]


def judge(references, surface):
    findings, unjudged = [], []
    for reference in references:
        finding = _one(reference, surface)
        if isinstance(finding, str):
            unjudged.append((reference, finding))
        else:
            findings.append(finding)
    return findings, unjudged


def _one(reference, surface):
    if reference.kind == "module":
        if reference.name in surface.modules:
            return Finding("matches", reference, "module exists")
        return _verdict(reference, surface.modules, "no such module in this project")

    if reference.kind == "symbol":
        module, _, leaf = reference.name.rpartition(".")
        if reference.name in surface.modules:
            # `from pkg import mod` imports a submodule, not a name in pkg/__init__.py
            return Finding("matches", reference, "submodule exists")
        if module in surface.names and leaf in surface.names[module]:
            return Finding("matches", reference, f"defined in {module}")
        if module in surface.dynamic:
            return "module builds its names at runtime (__getattr__)"

        if module in surface.modules:
            elsewhere = sorted(other for other, found in surface.names.items()
                               if leaf in found and other != module)
            if len(elsewhere) == 1:
                return Finding("renamed", reference,
                               f"the name is defined in {elsewhere[0]}, not in {module}")
            if len(elsewhere) > 1:
                return Finding("broken", reference,
                               f"not defined in {module}; the name exists in {', '.join(elsewhere[:3])}")
            return _verdict(reference, surface.names.get(module, set()), f"not defined in {module}")
        # the importer wrote a package path we cannot resolve to a file
        if module not in surface.modules:
            return "the module it is imported from is not in this project"
        return _verdict(reference, surface.every_name(), "not defined in this project")

    if reference.kind == "method":
        klass, _, method = reference.name.rpartition(".")
        if klass not in surface.methods:
            return "class not found in this project"
        for owner in surface.method_owners(klass):
            if method in surface.methods.get(owner, ()):
                evidence = f"{owner} defines it" if owner == klass else f"inherited from {owner}"
                return Finding("matches", reference, evidence)
        chain = surface.method_owners(klass)
        if any(owner in surface.decorated for owner in chain):
            return ("the class carries a decorator, which can add methods at import time - "
                    "an AST walk cannot see them")
        inherited = set()
        for owner in chain:
            inherited |= surface.methods.get(owner, set())
        return _verdict(reference, inherited, f"{klass} has no such method, nor do its base classes")

    if reference.kind == "flag":
        if surface.unknown_cli:
            named = ", ".join(sorted(surface.unknown_cli))
            return (f"this project builds its command line with {named}, which this tool cannot "
                    f"read; its flags are not checked rather than guessed at")
        if not surface.flags:
            return "this project declares no command-line flags to compare against"
        if reference.name in surface.flags:
            return Finding("matches", reference, "accepted by the parser")
        return _verdict(reference, surface.flags, "no parser in this project accepts it")

    if reference.kind == "file":
        if reference.name in surface.files:
            return Finding("matches", reference, "file is in the repository")
        return ("path is not in the repository; documentation names the reader's own files as "
                "often as its own")

    return "unknown reference kind"


def _verdict(reference, candidates, absent_reason):
    near = _near(reference.name, candidates)
    if len(near) == 1:
        return Finding("renamed", reference, f"closest match is {near[0]}")
    if len(near) > 1:
        return Finding("broken", reference, f"{absent_reason}; candidates: {', '.join(near[:3])}")
    return Finding("broken", reference, absent_reason)
