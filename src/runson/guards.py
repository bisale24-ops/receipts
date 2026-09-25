"""Whether a construct is actually reachable on the oldest supported Python.

Almost every real use of a newer feature in a careful library is deliberate and guarded. Reporting
those is the failure that makes a checker worthless, so the guards come first and the features are
measured against them.
"""
import ast

FALLBACK_ERRORS = {"ImportError", "ModuleNotFoundError"}


def version_test(node):
    """`sys.version_info >= (3, 11)` and friends, anywhere in an `if` test."""
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Compare):
            continue
        left = sub.left
        name = None
        if isinstance(left, ast.Attribute) and left.attr == "version_info":
            name = "version_info"
        elif isinstance(left, ast.Subscript) and isinstance(left.value, ast.Attribute) \
                and left.value.attr == "version_info":
            name = "version_info"
        elif isinstance(left, ast.Name) and left.id == "version_info":
            name = "version_info"
        if name:
            return True
    return False


def import_fallback(node):
    """`try: import tomllib / except ImportError: import tomli as tomllib`."""
    for handler in node.handlers:
        kind = handler.type
        names = []
        if isinstance(kind, ast.Name):
            names = [kind.id]
        elif isinstance(kind, ast.Tuple):
            names = [e.id for e in kind.elts if isinstance(e, ast.Name)]
        elif kind is None:
            names = ["ImportError"]          # bare except catches it too
        if set(names) & FALLBACK_ERRORS:
            return True
    return False


def type_checking(node):
    """`if TYPE_CHECKING:` — the body never runs, so its annotations cost nothing."""
    test = node.test
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
        return True
    return False


def annotate_parents(tree):
    """Give every node a `parent`, so a construct can look upwards for its guard."""
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent
    return tree


def guard_for(node):
    """The reason this node is protected, or None."""
    current = getattr(node, "parent", None)
    child = node
    while current is not None:
        if isinstance(current, ast.If):
            if version_test(current.test):
                return "sys.version_info check"
            if type_checking(current):
                return "if TYPE_CHECKING"
        if isinstance(current, ast.Try) and import_fallback(current):
            return "try/except ImportError fallback"
        child, current = current, getattr(current, "parent", None)
    return None


def postponed_annotations(tree):
    """`from __future__ import annotations` makes every annotation a string."""
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            if any(alias.name == "annotations" for alias in node.names):
                return True
    return False
