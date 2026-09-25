"""receipts — everything this repository claims, and what backs it."""
import argparse
import pathlib
import sys

from . import audit, promises, report

CHECKS = {
    "badges": audit.badges_section,
    "docs": promises.documentation_section,
    "version": promises.version_section,
    "notes": promises.notes_section,
}


def build_parser():
    parser = argparse.ArgumentParser(
        prog="receipts",
        description="Audit a repository for claims it cannot back: badges, documentation "
                    "examples, the Python floor it promises, and its release notes.")
    parser.add_argument("--repo", default=".", help="repository to audit (default: current)")
    parser.add_argument("--only", choices=sorted(CHECKS), nargs="*",
                        help="run only these checks")
    parser.add_argument("--html", metavar="PATH", help="write the report as a page")
    parser.add_argument("--json", action="store_true", help="print the findings as JSON")
    parser.add_argument("--quiet", action="store_true", help="print only the summary line")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    repo = pathlib.Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"receipts: {args.repo} is not a directory", file=sys.stderr)
        return 2

    wanted = args.only or list(CHECKS)
    sections = []
    for name in CHECKS:
        if name not in wanted:
            continue
        try:
            sections.append(CHECKS[name](repo))
        except Exception as error:                       # a broken check must not hide the rest
            sections.append(audit.Section(name, name.title(), "", [],
                                          skipped=f"the check failed to run: {error}"))

    if args.json:
        print(report.as_json(sections, repo.name))
    elif args.quiet:
        total = report.counts(sections)
        print(" · ".join(f"{total[k]} {k}" for k in report.ORDER))
    else:
        print(report.render_terminal(sections, repo.name))

    if args.html:
        pathlib.Path(args.html).write_text(report.render_html(sections, repo.name),
                                           encoding="utf-8")
        print(f"\nreport written to {args.html}")
    return report.exit_code(sections)


if __name__ == "__main__":
    sys.exit(main())
