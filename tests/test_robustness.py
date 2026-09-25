"""Adversarial repositories: the tool must degrade, never crash, and never print to stderr.

Every case here was a guess about what a real repository might contain. They are asserted rather
than eyeballed, because a check nobody can re-run is not a check.
"""
import pathlib
import sys

import pytest

from receipts import cli

from helpers import MIT, make_repo, write


def audit(tmp_path, capsys, *extra):
    code = cli.main(["--repo", str(tmp_path), *extra])
    captured = capsys.readouterr()
    assert captured.err == "", f"wrote to stderr: {captured.err[:400]}"
    assert code in (0, 1), f"unexpected exit code {code}"
    return captured.out


def test_an_empty_directory(tmp_path, capsys):
    audit(tmp_path, capsys)


def test_a_repository_with_no_readme(tmp_path, capsys):
    make_repo(tmp_path, readme="")
    out = audit(tmp_path, capsys)
    assert "no README.md" in out


def test_a_repository_with_no_python_at_all(tmp_path, capsys):
    write(tmp_path, "README.md", "# a javascript project\n")
    write(tmp_path, "index.js", "console.log(1)\n")
    out = audit(tmp_path, capsys)
    assert "not checked" in out.lower()


def test_a_pyproject_that_is_not_valid_toml(tmp_path, capsys):
    make_repo(tmp_path, licence=MIT)
    write(tmp_path, "pyproject.toml", "[project\nname = broken\n")
    audit(tmp_path, capsys)


def test_a_source_file_that_does_not_parse(tmp_path, capsys):
    make_repo(tmp_path, licence=MIT)
    write(tmp_path, "demo/broken.py", "def f(:\n    pass\n")
    audit(tmp_path, capsys)


def run_as_a_subprocess(tmp_path, *extra):
    """pytest swallows warnings before they reach stderr, so real stderr needs a real process."""
    import subprocess
    root = pathlib.Path(__file__).resolve().parents[1]
    return subprocess.run(
        [sys.executable, "-m", "receipts.cli", "--repo", str(tmp_path), "--quiet", *extra],
        cwd=root, capture_output=True, text=True,
        env={"PYTHONPATH": str(root / "src"), "PATH": "/usr/bin:/bin", "HOME": str(root)})


def test_a_source_file_with_a_syntax_warning_stays_quiet(tmp_path):
    """black's own source raises SyntaxWarning while parsing; it is not ours to print."""
    make_repo(tmp_path, licence=MIT)
    write(tmp_path, "demo/warns.py", 'PATTERN = "\\ a"\n')
    write(tmp_path, "README.md", "# demo\n\n```python\nfrom demo.core import X\n```\n")
    result = run_as_a_subprocess(tmp_path)
    assert result.stderr == "", f"wrote to stderr: {result.stderr[:400]}"
    assert result.returncode in (0, 1)


def test_bytes_that_are_not_utf8(tmp_path, capsys):
    make_repo(tmp_path, licence=MIT)
    (tmp_path / "demo" / "latin.py").write_bytes(b"VALUE = '\xff\xfe binary'\n")
    (tmp_path / "README.md").write_bytes(b"# title \xff\xfe\n")
    audit(tmp_path, capsys)


def test_a_readme_full_of_unicode(tmp_path, capsys):
    make_repo(tmp_path, licence=MIT,
              readme="# проверка 🎉\n\n![License](https://img.shields.io/badge/License-MIT-blue.svg)\n")
    audit(tmp_path, capsys)


def test_a_badge_url_with_no_message_part(tmp_path, capsys):
    make_repo(tmp_path, licence=MIT, readme="![x](https://img.shields.io/badge/onlylabel)\n")
    audit(tmp_path, capsys)


def test_a_reference_style_badge_with_a_missing_definition(tmp_path, capsys):
    make_repo(tmp_path, licence=MIT, readme="[![License][nope]][home]\n")
    audit(tmp_path, capsys)


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need a privilege on Windows")
def test_a_symlink_loop(tmp_path, capsys):
    make_repo(tmp_path, licence=MIT)
    (tmp_path / "demo" / "loop").symlink_to(tmp_path, target_is_directory=True)
    audit(tmp_path, capsys)


def test_a_dangling_symlink(tmp_path, capsys):
    make_repo(tmp_path, licence=MIT)
    (tmp_path / "demo" / "gone.py").symlink_to(tmp_path / "nowhere.py")
    audit(tmp_path, capsys)


def test_deeply_nested_packages(tmp_path, capsys):
    make_repo(tmp_path, licence=MIT)
    deep = pathlib.Path("demo")
    for level in range(25):
        deep = deep / f"level{level}"
        write(tmp_path, deep / "__init__.py", "\n")
    audit(tmp_path, capsys)


def test_a_readme_that_is_one_enormous_line(tmp_path, capsys):
    make_repo(tmp_path, licence=MIT, readme="x" * 200_000 + "\n")
    audit(tmp_path, capsys)


def test_every_output_format_on_a_repository_with_findings(tmp_path, capsys):
    make_repo(tmp_path, readme="![cov](https://img.shields.io/badge/coverage-99%25-green)\n")
    for extra in ([], ["--json"], ["--quiet"]):
        audit(tmp_path, capsys, *extra)
    target = tmp_path / "out.html"
    audit(tmp_path, capsys, "--html", str(target))
    page = target.read_text()
    assert "coverage" in page and "<script" in page


def test_only_selects_a_subset(tmp_path, capsys):
    make_repo(tmp_path, licence=MIT)
    out = audit(tmp_path, capsys, "--only", "badges")
    assert "PYTHON FLOOR" not in out


def test_a_missing_directory_exits_two(tmp_path, capsys):
    assert cli.main(["--repo", str(tmp_path / "nowhere")]) == 2
    assert "not a directory" in capsys.readouterr().err
