"""Broken promises first, then what the tool looked at and let pass.

The guarded list is printed rather than dropped, because a reader can only trust the silence if
they can see that the newer constructs were found and understood.
"""
import json


def render(broken, guarded, unjudged, declared, scanned, roots, quiet=False):
    lines = []
    floor = declared.text()

    if declared.contradiction:
        stated = ", ".join(f"{major}.{minor}" for major, minor in declared.contradiction)
        lines.append(f"CONTRADICTION  this project states two different floors: {stated}")
        for where, version, raw in declared.sources:
            lines.append(f"  {where}: {raw}  →  {version[0]}.{version[1]}")
        lines.append(f"  pip enforces requires-python and nothing else, so {floor} is what is "
                     f"checked below; the classifiers only advertise.")
        lines.append("")

    if broken:
        lines.append(f"BREAKS ITS PROMISE  {len(broken)}")
        for feature in broken:
            lines.append(f"  {feature.path}:{feature.line}  {feature.name}")
            lines.append(f"      needs {feature.needs_text}, this package promises {floor}")
        lines.append("")

    if guarded and not quiet:
        lines.append(f"GUARDED  {len(guarded)}")
        for feature in guarded:
            lines.append(f"  {feature.path}:{feature.line}  {feature.name} "
                         f"(needs {feature.needs_text})")
            lines.append(f"      {feature.guard}")
        lines.append("")

    if unjudged and not quiet:
        lines.append(f"NOT JUDGED  {len(unjudged)}")
        for path, reason in unjudged:
            lines.append(f"  {path}  {reason}")
        lines.append("")

    if not quiet:
        where = ", ".join(roots) or "nothing that looks like a package"
        lines.append(f"read: {where}")
    lines.append(f"promises {floor} · {scanned} files · {len(broken)} broken · "
                 f"{len(guarded)} guarded · {len(unjudged)} not judged")
    return "\n".join(lines)


def as_json(broken, guarded, unjudged, declared, scanned, roots):
    def record(feature):
        return {"name": feature.name, "needs": feature.needs_text, "path": feature.path,
                "line": feature.line, "guard": feature.guard}
    return json.dumps({
        "promises": declared.text(),
        "declared": [{"where": where, "version": f"{v[0]}.{v[1]}", "raw": raw}
                     for where, v, raw in declared.sources],
        "contradiction": [f"{a}.{b}" for a, b in (declared.contradiction or [])],
        "files": scanned,
        "roots": [str(root) for root in roots],
        "broken": [record(f) for f in broken],
        "guarded": [record(f) for f in guarded],
        "not_judged": [{"path": path, "reason": reason} for path, reason in unjudged],
    }, indent=2)
