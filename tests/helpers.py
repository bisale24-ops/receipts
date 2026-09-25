"""Each test writes the repository it is about."""
import pathlib
import textwrap


def write(root, relative, text):
    path = pathlib.Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
    return path


def make_repo(tmp_path, readme="", licence=None, floor=">=3.9", classifiers=None, module="X = 1\n"):
    if readme:
        write(tmp_path, "README.md", readme)
    if licence:
        write(tmp_path, "LICENSE", licence)
    lines = ["[project]", 'name = "demo"', 'version = "0.1.0"']
    if floor:
        lines.append(f'requires-python = "{floor}"')
    if classifiers:
        lines.append("classifiers = [")
        lines += [f'  "Programming Language :: Python :: {c}",' for c in classifiers]
        lines.append("]")
    write(tmp_path, "pyproject.toml", "\n".join(lines) + "\n")
    write(tmp_path, "demo/__init__.py", "\n")
    write(tmp_path, "demo/core.py", module)
    return tmp_path


MIT = "MIT License\n\nPermission is hereby granted, free of charge, to any person obtaining a copy\n"
APACHE = "Apache License\nVersion 2.0, January 2004\n"
