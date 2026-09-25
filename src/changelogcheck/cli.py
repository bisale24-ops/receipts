"""Check a release note against what actually shipped.

  changelog-check --repo . --from v1.2.0 --to v1.3.0
  changelog-check --repo . --from v1.2.0 --to HEAD --notes NOTES.md --strict
  gh release view v1.3.0 --json body -q .body | changelog-check --from v1.2.0 --to v1.3.0 --notes -

Exit codes: 0 every claim supported · 1 a claim with no evidence · 2 something shipped unmentioned
and --strict was given · 3 the repository or the range could not be read.
"""
import argparse
import pathlib
import sys

from . import check, history, report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="changelog-check", description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=".", help="path to the git repository")
    parser.add_argument("--from", dest="since", required=True, help="the previous tag, ref or sha")
    parser.add_argument("--to", dest="until", default="HEAD", help="the release being checked")
    parser.add_argument("--notes", default=None,
                        help="file with the release note, or - for stdin (default CHANGELOG.md)")
    parser.add_argument("--section", default=None,
                        help="take only this version's block out of the notes file")
    parser.add_argument("--strict", action="store_true",
                        help="also fail when a substantial change ships unmentioned")
    parser.add_argument("--html", default=None, help="write the same report to this path")
    parser.add_argument("--no-colour", action="store_true")
    parser.add_argument("--min-churn", type=int, default=10,
                        help="ignore unmentioned commits smaller than this many changed lines")
    args = parser.parse_args(argv)

    try:
        text = sys.stdin.read() if args.notes == "-" else check.read_notes(
            args.repo, args.notes, between=args.section)
        result = check.run(args.repo, args.since, args.until, text,
                           min_churn=args.min_churn,
                           notes_path=(args.notes or "CHANGELOG.md"))
    except history.GitError as e:
        print(f"changelog-check: {e}", file=sys.stderr)
        return report.EXIT_BROKEN

    print(report.render_terminal(result, colour=not args.no_colour and sys.stdout.isatty()))
    if args.html:
        # link every sha back to the forge when there is one; the page stays offline either way
        base = report.commit_url(args.repo)
        pathlib.Path(args.html).write_text(report.render_html(result, base=base))
        print(f"\nreport written to {args.html}")
    return report.exit_code(result, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
