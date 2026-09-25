"""The claims a README makes in its first ten lines, before anyone reads a word.

A badge is the loudest claim in a project and the least checked. It is an image URL, so nothing in
any pipeline compares what it says to what the repository contains: a licence badge outlives the
LICENSE file it was copied from, and a coverage percentage typed into a URL outlives the run that
produced it — if a run ever produced it.

Only a badge whose claim is written into the URL can be read here. A badge that resolves remotely
— `pypi/pyversions`, `codecov/c/github/...`, a workflow status — asserts something about a server,
and is listed as unverifiable rather than guessed at.
"""
import dataclasses
import pathlib
import re

MARKDOWN = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)\s]+)")
REFERENCE = re.compile(r"!\[(?P<alt>[^\]]*)\]\[(?P<ref>[^\]]+)\]")
DEFINITION = re.compile(r"^\s*\[(?P<ref>[^\]]+)\]:\s*(?P<url>\S+)", re.M)
HTML_IMG = re.compile(r"<img[^>]+src=[\"'](?P<url>[^\"']+)[\"'][^>]*?(?:alt=[\"'](?P<alt>[^\"']*)[\"'])?",
                      re.I)
STATIC = re.compile(r"shields\.io/badge/(?P<rest>[^?\s\"')]+)")
DYNAMIC_HOSTS = ("pypi/", "codecov", "coveralls", "actions/workflow", "travis", "appveyor",
                 "circleci", "github/", "readthedocs", "badge.fury.io", "img.shields.io/pypi")
LICENCE_WORDS = re.compile(r"^(licen[cs]e)$", re.I)
PYTHON_WORDS = re.compile(r"^(python|python versions?|py)$", re.I)
COVERAGE_WORDS = re.compile(r"^(coverage|cov|test coverage)$", re.I)
VERSION = re.compile(r"(\d+)\.(\d+)")

LICENCE_MARKS = {
    "mit": ["MIT License", "Permission is hereby granted, free of charge"],
    "apache": ["Apache License"],
    "bsd": ["Redistribution and use in source and binary forms", "BSD"],
    "0bsd": ["Permission to use, copy, modify, and/or distribute this software"],
    "gpl": ["GNU GENERAL PUBLIC LICENSE"],
    "lgpl": ["GNU LESSER GENERAL PUBLIC LICENSE"],
    "agpl": ["GNU AFFERO GENERAL PUBLIC LICENSE"],
    "mpl": ["Mozilla Public License"],
    "isc": ["ISC License"],
    "unlicense": ["This is free and unencumbered software"],
}


@dataclasses.dataclass(frozen=True)
class Badge:
    kind: str            # licence | python | coverage | other
    label: str           # the left half of a static badge
    message: str         # the right half: the claim itself
    url: str
    line: int
    static: bool


def _unescape(piece):
    out = piece.replace("--", "\x00").replace("-", " ").replace("\x00", "-")
    for code, char in (("%20", " "), ("%25", "%"), ("%2B", "+"), ("%7C", "|"), ("%3A", ":")):
        out = out.replace(code, char).replace(code.lower(), char)
    return out.replace("_", " ").strip()


def _classify(label, message, url, line, static):
    if LICENCE_WORDS.match(label):
        return Badge("licence", label, message, url, line, static)
    if PYTHON_WORDS.match(label):
        return Badge("python", label, message, url, line, static)
    if COVERAGE_WORDS.match(label):
        return Badge("coverage", label, message, url, line, static)
    return Badge("other", label, message, url, line, static)


def _from_url(url, alt, line):
    static = STATIC.search(url)
    if static:
        parts = [p for p in static.group("rest").split("-") if p != ""]
        # shields writes badge/<label>-<message>-<colour>; the colour is the last piece
        if len(parts) >= 3:
            label, message = _unescape(parts[0]), _unescape("-".join(parts[1:-1]))
        elif len(parts) == 2:
            label, message = _unescape(parts[0]), _unescape(parts[1])
        else:
            label, message = _unescape(parts[0]) if parts else "", ""
        return _classify(label, message, url, line, True)
    if any(host in url for host in DYNAMIC_HOSTS):
        return Badge("other", alt or "", "", url, line, False)
    return None


def find(readme_path):
    """Every badge in a README: markdown, reference-style and HTML, in that order of frequency."""
    path = pathlib.Path(readme_path)
    text = path.read_text(encoding="utf-8", errors="replace")
    definitions = {m.group("ref").lower(): m.group("url") for m in DEFINITION.finditer(text)}
    found, seen = [], set()
    for number, line in enumerate(text.splitlines(), start=1):
        candidates = [(m.group("alt"), m.group("url")) for m in MARKDOWN.finditer(line)]
        candidates += [(m.group("alt"), definitions.get(m.group("ref").lower(), ""))
                       for m in REFERENCE.finditer(line)]
        candidates += [(m.group("alt") or "", m.group("url")) for m in HTML_IMG.finditer(line)]
        for alt, url in candidates:
            if not url or url in seen:
                continue
            badge = _from_url(url, alt, number)
            if badge:
                seen.add(url)
                found.append(badge)
    return found


def licence_in(repo):
    """Which licence the repository actually ships, read from the LICENSE file itself."""
    repo = pathlib.Path(repo)
    for name in ("LICENSE", "LICENSE.txt", "LICENSE.md", "LICENCE", "LICENCE.txt", "COPYING"):
        path = repo / name
        if path.is_file():
            body = path.read_text(encoding="utf-8", errors="replace")
            for key, marks in LICENCE_MARKS.items():
                if any(mark.lower() in body.lower() for mark in marks):
                    return key, name
            return None, name
    return None, None


def same_licence(claim, actual):
    """Does a badge's word name the licence the file contains? '0BSD' and 'BSD' are not the same."""
    if actual is None:
        return None
    wanted = claim.lower().replace(" ", "").replace("licence", "").replace("license", "")
    wanted = wanted.replace("v2.0", "").replace("2.0", "").strip()
    return wanted.startswith(actual) or actual.startswith(wanted) if wanted else None
