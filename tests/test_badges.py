from receipts import badges

from helpers import APACHE, MIT, make_repo, write


def test_a_static_licence_badge_is_read(tmp_path):
    make_repo(tmp_path, readme="![License](https://img.shields.io/badge/License-MIT-blue.svg)\n")
    found = badges.find(tmp_path / "README.md")
    assert [(b.kind, b.message) for b in found] == [("licence", "MIT")]
    assert found[0].static


def test_a_reference_style_badge_is_read(tmp_path):
    make_repo(tmp_path, readme=(
        "[![License][lic]][home]\n\n"
        "[lic]: https://img.shields.io/badge/license-BSD-green.svg\n"
        "[home]: https://example.com\n"))
    found = badges.find(tmp_path / "README.md")
    assert [(b.kind, b.message) for b in found] == [("licence", "BSD")]


def test_an_html_badge_is_read(tmp_path):
    make_repo(tmp_path, readme='<img src="https://img.shields.io/badge/coverage-100%25-success" alt="cov">\n')
    found = badges.find(tmp_path / "README.md")
    assert [(b.kind, b.message) for b in found] == [("coverage", "100%")]


def test_a_dynamic_badge_is_kept_but_not_claimed(tmp_path):
    make_repo(tmp_path, readme="![cov](https://codecov.io/gh/a/b/branch/main/graph/badge.svg)\n")
    found = badges.find(tmp_path / "README.md")
    assert len(found) == 1 and not found[0].static


def test_escapes_in_a_badge_are_decoded(tmp_path):
    make_repo(tmp_path, readme="![py](https://img.shields.io/badge/python-3.5%2B%20%7C%20PyPy-blue)\n")
    found = badges.find(tmp_path / "README.md")
    assert found[0].kind == "python"
    assert "3.5+" in found[0].message


def test_the_licence_file_is_identified(tmp_path):
    make_repo(tmp_path, licence=MIT)
    assert badges.licence_in(tmp_path)[0] == "mit"
    write(tmp_path, "LICENSE", APACHE)
    assert badges.licence_in(tmp_path)[0] == "apache"


def test_zero_bsd_is_not_the_same_as_bsd():
    assert badges.same_licence("BSD", "bsd") is True
    assert badges.same_licence("MIT", "apache") is False
