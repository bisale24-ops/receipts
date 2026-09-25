"""What this project actually offers, read out of its own source.

The surface is the only thing a documented example is measured against. Everything here comes from
an AST walk of the repository - no import of the project under test, so a README can be checked
without installing anything and without running a line of someone else's code.
"""
import ast
import dataclasses
import pathlib
import warnings

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "build", "dist", "__pycache__", ".tox",
             ".mypy_cache", ".pytest_cache", "site-packages"}
DOC_EXTENSIONS = {".md", ".rst", ".txt", ".py", ".toml", ".cfg", ".yml", ".yaml", ".json", ".sh"}


@dataclasses.dataclass
class Surface:
    modules: set                 # importable dotted paths, e.g. "examplecheck.docs"
    names: dict                  # module path -> set of top-level names it defines
    methods: dict                # class name -> set of method names
    classes: set
    decorated: set               # classes a decorator may add methods to
    bases: dict                  # class name -> the base classes it was declared with
    flags: set                   # every "--flag" any ArgumentParser in the project accepts
    commands: set                # console-script names and package names
    files: set                   # repository-relative paths, as strings
    dynamic: set                 # modules defining a module-level __getattr__
    unknown_cli: set             # CLI frameworks present here whose flags this tool cannot read

    @property
    def roots(self):
        return {module.split(".")[0] for module in self.modules}

    def method_owners(self, klass, seen=None):
        """A class and every base of it this project also defines, nearest first."""
        seen = seen or set()
        if klass in seen:
            return []
        seen.add(klass)
        chain = [klass]
        for base in self.bases.get(klass, ()):  # only bases defined in this project
            chain.extend(self.method_owners(base, seen))
        return chain

    def defines(self, dotted):
        """Is this dotted name defined anywhere in the project?"""
        if dotted in self.modules:
            return True
        module, _, leaf = dotted.rpartition(".")
        if module and module in self.names:
            return leaf in self.names[module]
        return any(leaf in found for found in self.names.values()) if not module else False

    def every_name(self):
        out = set(self.modules)
        for module, found in self.names.items():
            out.update(found)
            out.update(f"{module}.{name}" for name in found)
        return out


def python_files(repo):
    for path in sorted(pathlib.Path(repo).rglob("*.py")):
        if not any(part in SKIP_DIRS for part in path.parts):
            yield path


def module_path(repo, path):
    """src/pkg/mod.py -> pkg.mod ; pkg/__init__.py -> pkg."""
    relative = path.relative_to(repo)
    parts = list(relative.parts)
    if parts and parts[0] in {"src", "lib"}:
        parts = parts[1:]
    if not parts:
        return None
    parts[-1] = parts[-1][:-3]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else None


def _top_level_names(tree):
    names, classes, methods, dynamic, bases = set(), set(), {}, False, {}
    decorated = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
            if node.name == "__getattr__":
                dynamic = True
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
            classes.add(node.name)
            methods[node.name] = {child.name for child in node.body
                                  if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))}
            bases[node.name] = [name for name in map(_base_name, node.bases) if name]
            if node.decorator_list:
                # a decorator can attach methods at import time; an AST walk cannot see them
                decorated.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
                    if target.id == "__all__":
                        names |= _declared(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names, classes, methods, dynamic, bases, decorated


def _base_name(node):
    """The class a base expression names: `Serializer`, `mod.Serializer`, `Serializer[str]`."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):     # Generic bases: Serializer[str]
        return _base_name(node.value)
    return None


def _declared(node):
    """The strings in an `__all__` list: a module saying outright what it exports."""
    if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return set()
    return {element.value for element in node.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)}


def _reexports(tree, package):
    """What an __init__.py pulls in, so a short-form import is not read as missing.

    Returns (names, star_targets). A star import cannot be resolved until every module has been
    read, so its target is recorded and resolved in a second pass - otherwise a package that
    re-exports with `from ._api import *`, as several widely used libraries do, looks empty.
    """
    out, stars = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            target = _absolute(node, package)
            for alias in node.names:
                if alias.name == "*":
                    if target:
                        stars.add(target)
                else:
                    out.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.asname or alias.name.split(".")[0])
    return out, stars


def _absolute(node, package):
    """Resolve `from .mod import x` to its dotted path, given the package it sits in."""
    if not node.level:
        return node.module
    parts = package.split(".") if package else []
    parts = parts[: len(parts) - node.level + 1]
    if node.module:
        parts.append(node.module)
    return ".".join(parts) if parts else None


FLAG_DECLARERS = {"add_argument", "add_option", "option", "Option", "argument", "add_flag",
                  "version_option", "help_option"}
READABLE_CLI = {"argparse", "optparse", "click", "typer"}
UNREADABLE_CLI = {"cleo", "docopt", "fire", "absl", "plac", "clint", "cement", "cliff"}


def _cli_frameworks(tree):
    """Which command-line frameworks this module imports, readable or not."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            found.add(node.module.split(".")[0])
    return found


def _flags(tree):
    """Every way this project declares a command-line flag: argparse, click, typer.

    A project that declares its flags with `@click.option("--code")` is not a project without
    flags, and reading only `add_argument` would turn its whole documented interface into a list
    of accusations.
    """
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = (node.func.attr if isinstance(node.func, ast.Attribute)
                  else node.func.id if isinstance(node.func, ast.Name) else None)
        if target not in FLAG_DECLARERS:
            continue
        if target in {"version_option", "help_option"}:
            out.add(f"--{target.split('_')[0]}")
        for argument in node.args:  # explicit strings: argparse, click, and typer's long form
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                # click writes a boolean flag as one string holding both halves:
                # "--upgrade/--no-upgrade" declares two flags, not one named with a slash
                for piece in argument.value.split("/"):
                    piece = piece.strip()
                    if piece.startswith("-"):
                        out.add(piece)
    out |= _implicit_flags(tree)
    return out


def _implicit_flags(tree):
    """Flags named after the parameter they fill, as Typer declares them.

    `output: Path = typer.Option(None, help=...)` declares `--output` without the string ever
    appearing in the source. Reading only string literals would report a project's own documented
    interface as broken - the one error this tool must not make.
    """
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        arguments = node.args
        positional = arguments.posonlyargs + arguments.args
        defaults = list(arguments.defaults)
        paired = list(zip(positional[len(positional) - len(defaults):], defaults)) if defaults else []
        paired += [(argument, default)
                   for argument, default in zip(arguments.kwonlyargs, arguments.kw_defaults)
                   if default is not None]
        for argument, default in paired:
            if not isinstance(default, ast.Call):
                continue
            callee = default.func
            name = (callee.attr if isinstance(callee, ast.Attribute)
                    else callee.id if isinstance(callee, ast.Name) else None)
            if name in {"Option", "Argument"} and not argument.arg.startswith("_"):
                out.add("--" + argument.arg.replace("_", "-"))
    return out


def _commands(repo):
    """Console scripts a project declares, read as text so no build backend is needed."""
    out = set()
    for name in ("pyproject.toml", "setup.cfg", "setup.py"):
        path = pathlib.Path(repo) / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            stripped = line.strip().strip(",")
            if "=" in stripped and ":" in stripped and not stripped.startswith("#"):
                left = stripped.split("=")[0].strip().strip('"\'')
                if left and all(character.isalnum() or character in "-_" for character in left):
                    out.add(left)
    for path in pathlib.Path(repo).glob("*.sh"):
        out.add(path.name)
        out.add(f"./{path.name}")
    return out


def read(repo):
    repo = pathlib.Path(repo).resolve()
    modules, names, methods, classes, flags, dynamic = set(), {}, {}, set(), set(), set()
    bases, stars, frameworks, decorated = {}, {}, set(), set()
    for path in python_files(repo):
        dotted = module_path(repo, path)
        if dotted is None:
            continue
        try:
            with warnings.catch_warnings():
                # reading someone else's source: its lint warnings are not ours to print
                warnings.simplefilter("ignore")
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        modules.add(dotted)
        found, found_classes, found_methods, is_dynamic, found_bases, found_decorated = \
            _top_level_names(tree)
        if path.name == "__init__.py":
            pulled, star_targets = _reexports(tree, dotted)
            found |= pulled
            if star_targets:
                stars[dotted] = star_targets
        names[dotted] = found
        classes |= found_classes
        for klass, members in found_methods.items():
            methods.setdefault(klass, set()).update(members)
        for klass, declared in found_bases.items():
            bases.setdefault(klass, []).extend(declared)
        decorated |= found_decorated
        flags |= _flags(tree)
        frameworks |= _cli_frameworks(tree)
        if is_dynamic:
            dynamic.add(dotted)

    # second pass: a star re-export can only be resolved once every module has been read, and the
    # target may itself re-export with a star, so run it to a fixed point rather than once.
    for _ in range(len(stars) + 1):
        changed = False
        for package, targets in stars.items():
            before = len(names.setdefault(package, set()))
            for target in targets:
                names[package].update(names.get(target, set()))
            changed |= len(names[package]) != before
        if not changed:
            break

    files = set()
    for path in pathlib.Path(repo).rglob("*"):
        if path.is_file() and not any(part in SKIP_DIRS for part in path.parts):
            files.add(str(path.relative_to(repo)))

    unknown_cli = frameworks & UNREADABLE_CLI
    if flags and not unknown_cli:
        flags.add("--help")   # argparse and click both add it without being asked
    commands = _commands(repo) | {module.split(".")[0] for module in modules}
    bases = {klass: [base for base in declared if base in classes] for klass, declared in bases.items()}
    return Surface(modules=modules, names=names, methods=methods, classes=classes,
                   decorated=decorated, bases=bases,
                   flags=flags, commands=commands, files=files, dynamic=dynamic,
                   unknown_cli=unknown_cli)
