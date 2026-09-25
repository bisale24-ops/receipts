"""Three blocks, always all three, and an exit code a CI job can act on."""
import html as html_module
import re
import subprocess

GREEN, AMBER, GREY, BOLD, OFF = "\033[32m", "\033[33m", "\033[90m", "\033[1m", "\033[0m"

EXIT_OK = 0
EXIT_UNSUPPORTED = 1
EXIT_UNMENTIONED = 2
EXIT_BROKEN = 3


def describe(commit):
    files = ", ".join(commit.files[:3]) + (f" +{len(commit.files) - 3} more" if len(commit.files) > 3 else "")
    return f"{commit.sha[:8]}  {commit.subject}" + (f"\n        {files}" if files else "")


def render_terminal(result, colour=True):
    def paint(text, code):
        return f"{code}{text}{OFF}" if colour else text

    lines = []
    supported = [r for r in result["claims"] if r["verdict"]["supported"]]
    unsupported = [r for r in result["claims"] if not r["verdict"]["supported"]]

    lines.append(paint("SUPPORTED", BOLD) + f"  {len(supported)} of {len(result['claims'])} claims")
    for item in supported:
        lines.append(paint(f"  ✓ {item['claim']}", GREEN))
        for commit, found in item["verdict"]["hits"][:3]:
            why = ", ".join(f"{kind} {value}" for kind, value in found[:3])
            lines.append(paint(f"      {describe(commit)}", GREY))
            lines.append(paint(f"        matched on {why}", GREY))
    if not supported:
        lines.append(paint("  nothing in the notes could be tied to a commit", GREY))

    lines.append("")
    lines.append(paint("SHIPPED WITHOUT A MENTION", BOLD) + f"  {len(result['unmentioned'])} commits")
    for commit in result["unmentioned"][:12]:
        lines.append(paint(f"  ? {describe(commit)}", AMBER))
        lines.append(paint(f"        +{commit.insertions} −{commit.deletions}", GREY))
    if not result["unmentioned"]:
        lines.append(paint("  every substantial commit is covered by a claim", GREY))

    lines.append("")
    lines.append(paint("NO EVIDENCE FOUND", BOLD) + f"  {len(unsupported)} claims")
    for item in unsupported:
        lines.append(paint(f"  ✗ {item['claim']}", AMBER))
        looked = item["searched"]
        lines.append(paint(f"        looked for {looked or 'nothing concrete in this line'}", GREY))
    if not unsupported:
        lines.append(paint("  every claim rests on something in the diff", GREY))

    lines.append("")
    lines.append(paint(f"{result['range']}: {len(result['commits'])} commits, "
                       f"{result['insertions']} insertions, {result['deletions']} deletions", GREY))
    if result.get("shallow"):
        lines.append(paint("  the clone is shallow, so older commits are invisible: "
                           "git fetch --unshallow", AMBER))
    lines.append(paint("Evidence is git history. A claim about behaviour this cannot see "
                       "is reported as unverified, not as false.", GREY))
    return "\n".join(lines)


def exit_code(result, strict=False):
    if result.get("broken"):
        return EXIT_BROKEN
    if any(not r["verdict"]["supported"] for r in result["claims"]):
        return EXIT_UNSUPPORTED
    if strict and result["unmentioned"]:
        return EXIT_UNMENTIONED
    return EXIT_OK


REMOTE = re.compile(r"(?:git@|https://)(?P<host>[^:/]+)[:/](?P<path>[^\s]+?)(?:\.git)?$")


def commit_url(repo):
    """The base URL for linking a sha, read from `git remote`. None when there is nothing to link."""
    try:
        out = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    match = REMOTE.match(out.stdout.strip())
    if not match or out.returncode:
        return None
    host, path = match.group("host"), match.group("path")
    if host not in {"github.com", "gitlab.com", "codeberg.org"}:
        return None
    return f"https://{host}/{path}/commit/"


def render_html(result, base=None):
    """A page a maintainer can send to a reviewer: findings first, evidence attached, no network."""
    esc = html_module.escape
    supported = [r for r in result["claims"] if r["verdict"]["supported"]]
    unsupported = [r for r in result["claims"] if not r["verdict"]["supported"]]
    unmentioned = result["unmentioned"]

    def sha(commit):
        short = esc(commit.sha[:8])
        return (f'<a class=sha href="{esc(base)}{esc(commit.sha)}">{short}</a>' if base
                else f"<code>{short}</code>")

    def chips(found):
        return "".join(f'<span class=chip data-k="{esc(kind)}">{esc(kind)} {esc(str(value))}</span>'
                       for kind, value in found[:4])

    def evidence(item):
        out = []
        for commit, found in item["verdict"]["hits"][:3]:
            files = ", ".join(commit.files[:3])
            out.append(f'<div class=e>{sha(commit)} {esc(commit.subject)}'
                       f'<span class=w>{esc(files)}</span>{chips(found)}</div>')
        return "".join(out)

    def claim_row(item, ok):
        body = evidence(item) if ok else (
            f'<div class=w>searched for {esc(item["searched"]) or "nothing specific enough"}</div>')
        return (f'<li class="{"ok" if ok else "no"}"><b>{esc(item["claim"])}</b>'
                f'<span class=w>{esc(result.get("notes_path", "the notes"))}:{item["line"]}</span>{body}</li>')

    rows_no = "".join(claim_row(item, False) for item in unsupported)
    rows_ok = "".join(claim_row(item, True) for item in supported)
    rows_silent = "".join(
        f'<li class=no><b>{esc(commit.subject)}</b>'
        f'<div class=w>{sha(commit)} +{commit.insertions} &minus;{commit.deletions} · '
        f'{esc(", ".join(commit.files[:3]))}</div></li>'
        for commit in unmentioned[:30])

    def block(title, note, rows, empty):
        return (f'<section><h2>{esc(title)}<span class=count>{note}</span></h2>'
                f'<ul>{rows or empty}</ul></section>')

    verdict = ("nothing to fix" if not unsupported and not unmentioned
               else f"{len(unsupported)} unsupported, {len(unmentioned)} unmentioned")

    return f"""<!doctype html><meta charset=utf-8>
<title>Changelog check — {esc(result['range'])}</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>
 :root {{ --bg:#fbfaf7; --card:#fff; --fg:#1a1a18; --muted:#6b6a64; --line:#e2e0d8;
          --ok:#2f6f45; --no:#8a5a12; }}
 @media (prefers-color-scheme: dark) {{ :root:not([data-theme=light]) {{
   --bg:#14140f; --card:#1b1b15; --fg:#eceae2; --muted:#9a988e; --line:#2c2b24;
   --ok:#7fc79a; --no:#e0b063; }} }}
 * {{ box-sizing:border-box; }}
 body {{ margin:0; background:var(--bg); color:var(--fg);
   font:16px/1.55 system-ui,-apple-system,sans-serif; }}
 .wrap {{ max-width:840px; margin:0 auto; padding:32px 16px 72px; }}
 h1 {{ font-size:25px; margin:0 0 4px; letter-spacing:-.01em; }}
 .sub {{ color:var(--muted); margin:0 0 22px; font-size:15px; }}
 .score {{ display:flex; gap:10px; flex-wrap:wrap; margin:0 0 26px; }}
 .score div {{ flex:1 1 150px; border:1px solid var(--line); border-radius:12px;
   padding:12px 14px; background:var(--card); }}
 .score b {{ display:block; font-size:26px; line-height:1.1; }}
 .score span {{ color:var(--muted); font-size:13px; }}
 .score .bad b {{ color:var(--no); }} .score .good b {{ color:var(--ok); }}
 .bar {{ display:flex; align-items:center; gap:10px; margin:0 0 18px; font-size:14px;
   color:var(--muted); }}
 h2 {{ font-size:12px; text-transform:uppercase; letter-spacing:.09em; margin:28px 0 10px;
   display:flex; gap:8px; align-items:baseline; }}
 .count {{ color:var(--muted); font-weight:400; letter-spacing:0; text-transform:none;
   font-size:13px; }}
 ul {{ list-style:none; padding:0; margin:0; }}
 li {{ border:1px solid var(--line); border-left-width:3px; border-radius:10px;
   padding:12px 14px; margin-bottom:8px; background:var(--card); }}
 li.ok {{ border-left-color:var(--ok); }} li.no {{ border-left-color:var(--no); }}
 .e {{ margin-top:9px; font-size:14px; color:var(--muted); }}
 .w {{ display:block; color:var(--muted); font-size:13px; margin-top:3px; }}
 .chip {{ display:inline-block; font-size:12px; border:1px solid var(--line);
   border-radius:999px; padding:1px 8px; margin:6px 6px 0 0; color:var(--fg); }}
 .chip[data-k="issue"], .chip[data-k="flag"], .chip[data-k="file"] {{ border-color:var(--ok);
   color:var(--ok); }}
 code, .sha {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:13px; }}
 a.sha {{ color:inherit; text-decoration:underline; text-underline-offset:2px; }}
 body.only-problems li.ok, body.only-problems section.clean {{ display:none; }}
 footer {{ color:var(--muted); font-size:13px; margin-top:34px; border-top:1px solid var(--line);
   padding-top:14px; }}
</style>
<div class=wrap>
<h1>Does the release note tell the truth?</h1>
<p class=sub>{esc(result['range'])} · {len(result['commits'])} commits ·
 +{result['insertions']} &minus;{result['deletions']} · {esc(verdict)}</p>

<div class=score>
  <div class="{'bad' if unsupported else 'good'}"><b>{len(unsupported)}</b>
    <span>claims with no evidence</span></div>
  <div class="{'bad' if unmentioned else 'good'}"><b>{len(unmentioned)}</b>
    <span>changes shipped unmentioned</span></div>
  <div class=good><b>{len(supported)}</b><span>claims backed by commits</span></div>
</div>

<div class=bar><label><input type=checkbox id=only> show only what needs fixing</label></div>

{block('No evidence found', f'{len(unsupported)} claims', rows_no,
       '<li class=ok>every claim is tied to a commit</li>')}
{block('Shipped without a mention', f'{len(unmentioned)} commits', rows_silent,
       '<li class=ok>every substantial commit is covered by a claim</li>')}
<section class=clean>{block('Supported', f'{len(supported)} of {len(result["claims"])} claims',
       rows_ok, '<li class=no>nothing in the notes could be tied to a commit</li>')}</section>

<footer>Evidence is git history: issue numbers, command-line flags, identifiers the diff defines
and files it touches. Shared ordinary English is not evidence, so a claim about behaviour git
cannot see is reported as unverified rather than false. Generated offline; this page makes no
network requests.</footer>
</div>
<script>
 document.getElementById('only').addEventListener('change', function (event) {{
   document.body.classList.toggle('only-problems', event.target.checked);
 }});
</script>"""
