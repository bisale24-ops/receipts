"""The audit's own rules: what each check reports, and what it refuses to report."""
from receipts import audit, cli, promises, report

from helpers import APACHE, MIT, make_repo, write


def badges_of(tmp_path):
    return audit.badges_section(tmp_path).findings


def test_a_licence_badge_that_matches_the_file_is_silent(tmp_path):
    make_repo(tmp_path, licence=MIT,
              readme="![License](https://img.shields.io/badge/License-MIT-blue.svg)\n")
    assert badges_of(tmp_path) == []


def test_a_licence_badge_that_contradicts_the_file_is_broken(tmp_path):
    make_repo(tmp_path, licence=APACHE,
              readme="![License](https://img.shields.io/badge/License-MIT-blue.svg)\n")
    found = badges_of(tmp_path)
    assert [f.severity for f in found] == ["broken"]
    assert "APACHE" in found[0].detail.upper()


def test_a_licence_badge_with_no_licence_file_is_unbacked(tmp_path):
    make_repo(tmp_path, readme="![License](https://img.shields.io/badge/License-MIT-blue.svg)\n")
    assert [f.severity for f in badges_of(tmp_path)] == ["unbacked"]


def test_a_hardcoded_coverage_badge_is_unbacked(tmp_path):
    make_repo(tmp_path, licence=MIT,
              readme="![cov](https://img.shields.io/badge/coverage-100%25-success)\n")
    found = badges_of(tmp_path)
    assert [f.severity for f in found] == ["unbacked"]
    assert "typed into the badge URL" in found[0].detail


def test_a_dynamic_coverage_badge_is_not_accused(tmp_path):
    make_repo(tmp_path, licence=MIT,
              readme="![cov](https://codecov.io/gh/a/b/branch/main/graph/badge.svg)\n")
    assert badges_of(tmp_path) == []


def test_a_python_badge_that_disagrees_with_metadata_has_drifted(tmp_path):
    make_repo(tmp_path, licence=MIT, floor=">=3.9",
              readme="![py](https://img.shields.io/badge/python-3.7%2B-blue)\n")
    found = badges_of(tmp_path)
    assert [f.severity for f in found] == ["drifted"]


def test_classifiers_below_requires_python_are_reported(tmp_path):
    """python-docx ships this: pip refuses the versions the classifiers advertise."""
    make_repo(tmp_path, floor=">=3.9", classifiers=["3.7", "3.8", "3.9"])
    found = promises.version_section(tmp_path).findings
    assert [f.severity for f in found] == ["drifted"]
    assert "refuses to install" in found[0].detail


def test_a_check_that_cannot_run_says_why(tmp_path):
    make_repo(tmp_path, floor=None)
    section = promises.version_section(tmp_path)
    assert section.findings == []
    assert "no Python floor" in section.skipped


def test_a_broken_check_does_not_hide_the_others(tmp_path, capsys, monkeypatch):
    make_repo(tmp_path, licence=MIT)
    monkeypatch.setitem(cli.CHECKS, "docs",
                        lambda repo: (_ for _ in ()).throw(RuntimeError("boom")))
    assert cli.main(["--repo", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "boom" in out and "PYTHON FLOOR" in out


def test_the_exit_code_is_one_only_for_a_contradiction(tmp_path, capsys):
    make_repo(tmp_path, licence=MIT,
              readme="![cov](https://img.shields.io/badge/coverage-100%25-success)\n")
    assert cli.main(["--repo", str(tmp_path)]) == 0        # unbacked is not a contradiction
    write(tmp_path, "LICENSE", APACHE)
    write(tmp_path, "README.md", "![License](https://img.shields.io/badge/License-MIT-blue.svg)\n")
    assert cli.main(["--repo", str(tmp_path)]) == 1


def test_the_html_report_holds_the_findings_and_makes_no_requests(tmp_path):
    make_repo(tmp_path, licence=APACHE,
              readme="![License](https://img.shields.io/badge/License-MIT-blue.svg)\n")
    sections = [audit.badges_section(tmp_path)]
    page = report.render_html(sections, "demo")
    assert "License-MIT" not in page or "badge: licence is MIT" in page
    assert "http://" not in page.replace("https://img.shields.io", "")
    assert "<script" in page and "fetch(" not in page


def test_json_output_is_machine_readable(tmp_path, capsys):
    import json
    make_repo(tmp_path, licence=APACHE,
              readme="![License](https://img.shields.io/badge/License-MIT-blue.svg)\n")
    cli.main(["--repo", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["totals"]["broken"] == 1
    assert any(c["check"] == "badges" for c in payload["checks"])
