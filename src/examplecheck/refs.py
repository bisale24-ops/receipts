"""What one example actually claims about this project.

The whole design lives in what this file refuses to extract. A call to the standard library, a
variable the snippet defines itself, a third-party helper - none of those are claims about this
project, and reporting one would be a false accusation against a correct README. When a block
cannot be read this way, it is declared unjudged with a reason instead of being guessed at.
"""
import ast
import dataclasses
import re
import shlex
import warnings

FLAG = re.compile(r"^--[A-Za-z][A-Za-z0-9-]*$")
PATHLIKE = {".py", ".md", ".rst", ".toml", ".cfg", ".yml", ".yaml", ".sh", ".txt", ".json"}
PROMPT = ("$ ", "> ", "% ")


@dataclasses.dataclass(frozen=True)
class Reference:
    kind: str            # module | symbol | method | flag | file
    name: str
    example: object
    detail: str = ""


@dataclasses.dataclass(frozen=True)
class NotJudged:
    example: object
    reason: str


def of(example, surface):
    """(references, not_judged_or_None) for one example.

    An unlabelled fence gets both readings attempted, because plenty of READMEs open a block with
    bare ``` and put Python or a command inside it. It is only reported on when one of those
    readings finds a reference to this project; otherwise it stays unjudged.
    """
    if example.lang == "python":
        return _python(example, surface)
    if example.lang == "bash":
        return _shell(example, surface)
    if example.lang == "":
        for reading in (_python, _shell):
            found, _ = reading(example, surface)
            if found:
                return found, None
        return [], NotJudged(example, "unlabelled block: reads as neither Python nor a command "
                                      "that touches this project")
    return [], NotJudged(example, f"{example.lang} block: nothing to check against")


def _python(example, surface):
    try:
        with warnings.catch_warnings():
            # a documentation snippet is not this project's code; its lint warnings are not ours
            warnings.simplefilter("ignore")
            tree = ast.parse(example.text)
    except (SyntaxError, ValueError):
        return [], NotJudged(example, "fragment does not parse as Python")

    roots = surface.roots
    bound = {}          # local name -> dotted project path
    found = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in roots:
                    found.append(Reference("module", alias.name, example))
                    bound[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if not node.module or node.module.split(".")[0] not in roots:
                continue
            found.append(Reference("module", node.module, example))
            for alias in node.names:
                if alias.name == "*":
                    continue
                dotted = f"{node.module}.{alias.name}"
                found.append(Reference("symbol", dotted, example, detail=f"imported as {alias.asname or alias.name}"))
                bound[alias.asname or alias.name] = dotted

    # x = SomeProjectClass(...)  ->  x carries that class, so x.method() is checkable
    carries = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            callee = node.value.func
            name = callee.id if isinstance(callee, ast.Name) else (
                callee.attr if isinstance(callee, ast.Attribute) else None)
            if name and (name in bound or name in surface.classes):
                leaf = bound.get(name, name).rpartition(".")[2]
                if leaf in surface.classes:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            carries[target.id] = leaf

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        if isinstance(callee, ast.Attribute) and isinstance(callee.value, ast.Name):
            owner = callee.value.id
            if owner in bound:
                root = bound[owner]
                kind = "symbol" if root in surface.modules else "method"
                if kind == "symbol":
                    found.append(Reference("symbol", f"{root}.{callee.attr}", example))
                else:
                    found.append(Reference("method", f"{root.rpartition('.')[2]}.{callee.attr}", example))
            elif owner in carries:
                found.append(Reference("method", f"{carries[owner]}.{callee.attr}", example,
                                       detail=f"on {owner}"))

    seen, unique = set(), []
    for reference in found:
        key = (reference.kind, reference.name)
        if key not in seen:
            seen.add(key)
            unique.append(reference)
    if not unique:
        return [], NotJudged(example, "Python block, but it never touches this project")
    return unique, None


def _shell(example, surface):
    found, ours = [], False
    for raw in example.text.splitlines():
        line = raw.strip()
        for prompt in PROMPT:
            if line.startswith(prompt):
                line = line[len(prompt):]
                break
        else:
            if raw.startswith(" ") or not line:
                continue
        if not line or line.startswith("#"):
            continue
        try:
            tokens = shlex.split(line, comments=True)
        except ValueError:
            continue
        if not tokens:
            continue
        head = tokens[0]
        rest = tokens[1:]
        if head in {"python", "python3"} and "-m" in rest:
            module = rest[rest.index("-m") + 1] if rest.index("-m") + 1 < len(rest) else ""
            if module.split(".")[0] not in surface.roots:
                continue
            found.append(Reference("module", module, example))
        elif head not in surface.commands:
            continue
        ours = True
        for token in rest:
            if FLAG.match(token.split("=")[0]):
                found.append(Reference("flag", token.split("=")[0], example))
            elif "." in token and not token.startswith("-") and not any(c in token for c in "*?["):
                suffix = token[token.rfind("."):]
                if suffix in PATHLIKE:
                    found.append(Reference("file", token, example))

    if not ours and not found:
        return [], NotJudged(example, "shell block, but it does not run this project")
    seen, unique = set(), []
    for reference in found:
        key = (reference.kind, reference.name)
        if key not in seen:
            seen.add(key)
            unique.append(reference)
    if not unique:
        return [], NotJudged(example, "runs this project, but passes nothing checkable")
    return unique, None
