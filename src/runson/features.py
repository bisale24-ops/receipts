"""Constructs that carry a Python version floor, and nothing else.

The table below is short on purpose. Every entry is decidable from the syntax tree with no
inference about what a name refers to. `a | b` outside an annotation could be integers, sets, or a
class with its own `__or__`; `d1 | d2` could be anything at all. A tool that guessed there would be
wrong on ordinary correct code, which is the single failure a checker cannot afford.
"""
import ast
import dataclasses

from . import guards

STDLIB_SINCE = {
    "tomllib": (3, 11),
    "zoneinfo": (3, 9),
    "graphlib": (3, 9),
    "importlib.metadata": (3, 8),
    "importlib.resources": (3, 7),
    "contextvars": (3, 7),
    "dataclasses": (3, 7),
    "asyncio.taskgroups": (3, 11),
}
BUILTIN_GENERICS = {"list", "dict", "set", "frozenset", "tuple", "type"}


@dataclasses.dataclass
class Feature:
    name: str
    needs: tuple
    path: str
    line: int
    guard: str = None        # the reason it is safe, when it is

    @property
    def needs_text(self):
        return f"{self.needs[0]}.{self.needs[1]}"


def _inside_a_function(node):
    """Annotations in a function body are never evaluated, so they carry no version floor.

    Established by running it: at module level, in a class body and in a function signature the
    annotation is evaluated and an undefined name raises. Inside a function body - simple target
    or attribute target alike - it is not. `self.result: list[str] = []` therefore costs nothing
    on an old Python, and reporting it would be a false accusation.
    """
    parent = getattr(node, "parent", None)
    while parent is not None:
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return True
        parent = getattr(parent, "parent", None)
    return False


def _annotations_of(node):
    if isinstance(node, ast.AnnAssign) and node.annotation:
        if not _inside_a_function(node):
            yield node.annotation
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.returns:
            yield node.returns
        arguments = node.args
        for argument in (list(arguments.posonlyargs) + list(arguments.args)
                         + list(arguments.kwonlyargs)
                         + [arguments.vararg, arguments.kwarg]):
            if argument is not None and argument.annotation:
                yield argument.annotation


def collect(tree, path):
    """Every version-bearing construct in one parsed module."""
    guards.annotate_parents(tree)
    postponed = guards.postponed_annotations(tree)
    found = []

    def add(name, needs, node):
        found.append(Feature(name=name, needs=needs, path=path, line=node.lineno,
                             guard=guards.guard_for(node)))

    for node in ast.walk(tree):
        # compared by class name, not isinstance: ast.Match does not exist before 3.10, and this
        # tool promises 3.9. Found by running it on 3.9, which is the only way to find it - the
        # tool reads syntax and imports, not attribute access, so it cannot catch this in itself.
        kind = node.__class__.__name__
        if kind == "Match":
            add("match statement", (3, 10), node)
        elif kind == "TryStar":
            add("except* group", (3, 11), node)
        elif kind == "TypeAlias":
            add("type alias statement", (3, 12), node)
        elif isinstance(node, ast.NamedExpr):
            add("walrus :=", (3, 8), node)
        elif isinstance(node, ast.JoinedStr):
            add("f-string", (3, 6), node)
        elif isinstance(node, ast.AnnAssign):
            add("variable annotation", (3, 6), node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if getattr(node, "type_params", None):
                add("PEP 695 type parameters", (3, 12), node)
            if getattr(getattr(node, "args", None), "posonlyargs", None):
                add("positional-only parameters", (3, 8), node)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                needs = STDLIB_SINCE.get(alias.name)
                if needs:
                    add(f"import {alias.name}", needs, node)
        elif isinstance(node, ast.ImportFrom):
            needs = STDLIB_SINCE.get(node.module or "")
            if needs:
                add(f"from {node.module} import …", needs, node)

    if not postponed:
        for node in ast.walk(tree):
            for annotation in _annotations_of(node):
                for piece in ast.walk(annotation):
                    if isinstance(piece, ast.BinOp) and isinstance(piece.op, ast.BitOr):
                        add("X | Y in a runtime annotation", (3, 10), piece)
                    elif isinstance(piece, ast.Subscript) and isinstance(piece.value, ast.Name) \
                            and piece.value.id in BUILTIN_GENERICS:
                        add(f"{piece.value.id}[…] in a runtime annotation", (3, 9), piece)

    unique, seen = [], set()
    for feature in sorted(found, key=lambda f: (f.line, f.name)):
        key = (feature.name, feature.line)
        if key not in seen:
            seen.add(key)
            unique.append(feature)
    return unique
