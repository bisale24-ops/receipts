"""example-check - does the documentation still describe this code?"""
import argparse
import pathlib
import sys

from . import docs, refs, report, surface, verdict


def build_parser():
    parser = argparse.ArgumentParser(
        prog="example-check",
        description="Check that the examples in the documentation still refer to code that exists.")
    parser.add_argument("--repo", default=".", help="repository to check (default: the current directory)")
    parser.add_argument("--docs", nargs="*", default=None, metavar="GLOB",
                        help="documentation globs, relative to the repository "
                             "(default: *.md plus docs/**/*.md)")
    parser.add_argument("--strict", action="store_true",
                        help="also fail when an example is reported as renamed")
    parser.add_argument("--json", action="store_true", help="print the findings as JSON")
    parser.add_argument("--quiet", action="store_true",
                        help="print only what is wrong, without the matches and the not-judged list")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    root = pathlib.Path(args.repo).resolve()
    if not root.is_dir():
        print(f"example-check: {args.repo} is not a directory", file=sys.stderr)
        return 2

    examples = docs.collect(root, args.docs)
    if not examples:
        print(f"example-check: no fenced examples found under {root}", file=sys.stderr)
        return 2

    known = surface.read(root)
    findings, unjudged = [], []
    for example in examples:
        references, skipped = refs.of(example, known)
        if skipped is not None:
            unjudged.append((skipped.example, skipped.reason))
            continue
        judged, refused = verdict.judge(references, known)
        findings.extend(judged)
        unjudged.extend((reference.example, reason) for reference, reason in refused)

    if args.json:
        print(report.as_json(findings, unjudged, examples))
    else:
        print(report.render(findings, unjudged, examples, quiet=args.quiet))

    code = report.exit_code(findings)
    if code == 0 and args.strict and any(f.verdict == "renamed" for f in findings):
        return 1
    return code


if __name__ == "__main__":
    sys.exit(main())
