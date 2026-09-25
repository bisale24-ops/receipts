"""runs-on - does this actually run on the Python it promises?"""
import argparse
import ast
import pathlib
import sys
import warnings

from . import declared as declared_module
from . import features, report, shipped


def build_parser():
    parser = argparse.ArgumentParser(
        prog="runs-on",
        description="Check that a package's code runs on the oldest Python it claims to support.")
    parser.add_argument("--repo", default=".", help="repository to check (default: current directory)")
    parser.add_argument("--floor", metavar="X.Y",
                        help="check against this version instead of the declared one")
    parser.add_argument("--include-tests", action="store_true",
                        help="also read tests, docs and tooling, which normally never ship")
    parser.add_argument("--json", action="store_true", help="print the findings as JSON")
    parser.add_argument("--quiet", action="store_true", help="print only what is wrong")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    root = pathlib.Path(args.repo).resolve()
    if not root.is_dir():
        print(f"runs-on: {args.repo} is not a directory", file=sys.stderr)
        return 2

    stated = declared_module.read(root)
    if args.floor:
        try:
            major, minor = (int(piece) for piece in args.floor.split("."))
        except ValueError:
            print(f"runs-on: --floor wants a version like 3.9, not {args.floor!r}", file=sys.stderr)
            return 2
        stated = declared_module.Declared(floor=(major, minor),
                                          sources=[("--floor", (major, minor), args.floor)])

    paths, package_roots = shipped.files(root, include_tests=args.include_tests)
    roots = [str(item.relative_to(root)) for item in package_roots]
    if not paths:
        print(f"runs-on: found no shipped Python package under {root}", file=sys.stderr)
        return 2

    broken, guarded, unjudged = [], [], []
    for path in paths:
        relative = str(path.relative_to(root))
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as error:
            unjudged.append((relative, f"does not parse here (line {error.lineno}); it may need a "
                                       f"newer Python than the one running this tool"))
            continue
        for feature in features.collect(tree, relative):
            if not stated.floor or feature.needs <= stated.floor:
                continue          # nothing to say: the promise already covers it
            if feature.guard:
                guarded.append(feature)
            else:
                broken.append(feature)

    if not stated.floor:
        unjudged.append((str(root.name), "the project declares no Python floor at all, so there is "
                                         "no promise to check"))

    if args.json:
        print(report.as_json(broken, guarded, unjudged, stated, len(paths), roots))
    else:
        print(report.render(broken, guarded, unjudged, stated, len(paths), roots, quiet=args.quiet))
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
