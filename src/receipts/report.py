"""One page a maintainer can send to a reviewer, and one line a CI job can act on.

Findings first, then what each check confirmed, then what it could not check and why. The last of
those is not padding: a reader can only trust the silence if they can see which questions were
asked and which were skipped.
"""
import html as html_module
import json

ORDER = ("broken", "unbacked", "drifted")
WORDS = {
    "broken": "contradicted by the repository",
    "unbacked": "nothing behind it",
    "drifted": "no longer matches",
}


def counts(sections):
    out = {key: 0 for key in ORDER}
    for section in sections:
        for finding in section.findings:
            out[finding.severity] = out.get(finding.severity, 0) + 1
    return out


def exit_code(sections):
    return 1 if any(f.severity == "broken" for s in sections for f in s.findings) else 0


def render_terminal(sections, name):
    total = counts(sections)
    lines = [f"{name}: {sum(total.values())} claims this repository cannot back", ""]
    for section in sections:
        if section.skipped:
            lines.append(f"{section.title.upper()}  not checked — {section.skipped}")
            lines.append("")
            continue
        head = f"{section.title.upper()}  {len(section.findings)} finding(s)"
        lines.append(head)
        for finding in sorted(section.findings, key=lambda f: ORDER.index(f.severity)):
            lines.append(f"  [{finding.severity}] {finding.claim}")
            lines.append(f"      {finding.detail}")
            if finding.where:
                lines.append(f"      {finding.where}")
        if not section.findings:
            lines.append(f"  nothing unbacked — {section.passed}")
        lines.append("")
    lines.append(" · ".join(f"{total[k]} {k}" for k in ORDER))
    return "\n".join(lines)


def as_json(sections, name):
    return json.dumps({
        "repository": name,
        "totals": counts(sections),
        "checks": [
            {"check": s.check, "title": s.title, "question": s.question,
             "skipped": s.skipped, "confirmed": s.passed, "checked": s.checked,
             "findings": [{"severity": f.severity, "claim": f.claim, "detail": f.detail,
                           "where": f.where} for f in s.findings]}
            for s in sections
        ],
    }, indent=2)


def render_html(sections, name, base=None):
    esc = html_module.escape
    total = counts(sections)
    everything = sum(total.values())
    ran = [s for s in sections if not s.skipped]
    skipped = [s for s in sections if s.skipped]

    def finding_row(finding):
        where = (f'<span class=w>{esc(finding.where)}</span>' if finding.where else "")
        return (f'<li class="{finding.severity}"><b>{esc(finding.claim)}</b>'
                f'<span class=tag>{esc(WORDS[finding.severity])}</span>'
                f'<div class=d>{esc(finding.detail)}</div>{where}</li>')

    def section_block(section):
        rows = "".join(finding_row(f) for f in
                       sorted(section.findings, key=lambda f: ORDER.index(f.severity)))
        clean = "" if section.findings else " clean"
        body = rows or f'<li class=ok>nothing unbacked <span class=w>{esc(section.passed)}</span></li>'
        return (f'<section class="check{clean}"><h2>{esc(section.title)}'
                f'<span class=q>{esc(section.question)}</span>'
                f'<span class=count>{len(section.findings)}</span></h2>'
                f'<ul>{body}</ul></section>')

    skipped_rows = "".join(
        f'<li class=skip><b>{esc(s.title)}</b><div class=d>{esc(s.skipped)}</div></li>'
        for s in skipped)

    verdict = ("every claim this tool can check is backed" if everything == 0
               else f"{everything} claim(s) with nothing behind them")

    plain = "\n".join(
        f"- [{f.severity}] {f.claim} — {f.detail}" + (f" ({f.where})" if f.where else "")
        for s in ran for f in s.findings) or "- nothing unbacked"

    return f"""<!doctype html><meta charset=utf-8>
<title>Receipts — {esc(name)}</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>
 :root {{ --bg:#fbfaf7; --card:#fff; --fg:#1a1a18; --muted:#6b6a64; --line:#e2e0d8;
   --ok:#2f6f45; --broken:#a33a2a; --unbacked:#8a5a12; --drifted:#5c5a86; }}
 @media (prefers-color-scheme: dark) {{ :root:not([data-theme=light]) {{
   --bg:#14140f; --card:#1b1b15; --fg:#eceae2; --muted:#9a988e; --line:#2c2b24;
   --ok:#7fc79a; --broken:#e08b7a; --unbacked:#e0b063; --drifted:#a8a5d8; }} }}
 * {{ box-sizing:border-box; }}
 body {{ margin:0; background:var(--bg); color:var(--fg);
   font:16px/1.55 system-ui,-apple-system,sans-serif; }}
 .wrap {{ max-width:880px; margin:0 auto; padding:34px 16px 80px; }}
 h1 {{ font-size:26px; margin:0 0 4px; letter-spacing:-.015em; }}
 .sub {{ color:var(--muted); margin:0 0 24px; }}
 .score {{ display:flex; gap:10px; flex-wrap:wrap; margin:0 0 20px; }}
 .score div {{ flex:1 1 170px; border:1px solid var(--line); border-radius:12px; padding:12px 14px;
   background:var(--card); }}
 .score b {{ display:block; font-size:28px; line-height:1.1; }}
 .score span {{ color:var(--muted); font-size:13px; }}
 .score .broken b {{ color:var(--broken); }} .score .unbacked b {{ color:var(--unbacked); }}
 .score .drifted b {{ color:var(--drifted); }}
 .bar {{ display:flex; gap:16px; align-items:center; margin:0 0 22px; font-size:14px;
   color:var(--muted); flex-wrap:wrap; }}
 button {{ font:inherit; font-size:13px; border:1px solid var(--line); background:var(--card);
   color:var(--fg); border-radius:8px; padding:5px 10px; cursor:pointer; }}
 h2 {{ font-size:13px; text-transform:uppercase; letter-spacing:.08em; margin:26px 0 10px;
   display:flex; gap:10px; align-items:baseline; flex-wrap:wrap; }}
 .q {{ text-transform:none; letter-spacing:0; font-weight:400; color:var(--muted); font-size:13px; }}
 .count {{ margin-left:auto; color:var(--muted); font-weight:400; }}
 ul {{ list-style:none; padding:0; margin:0; }}
 li {{ border:1px solid var(--line); border-left-width:3px; border-radius:10px; padding:12px 14px;
   margin-bottom:8px; background:var(--card); }}
 li.broken {{ border-left-color:var(--broken); }}
 li.unbacked {{ border-left-color:var(--unbacked); }}
 li.drifted {{ border-left-color:var(--drifted); }}
 li.ok {{ border-left-color:var(--ok); }} li.skip {{ border-left-color:var(--line); }}
 .tag {{ font-size:12px; color:var(--muted); margin-left:8px; }}
 .d {{ margin-top:5px; color:var(--muted); font-size:14px; }}
 .w {{ display:block; color:var(--muted); font-size:13px; margin-top:4px;
   font-family:ui-monospace,Menlo,monospace; }}
 body.only-problems section.clean {{ display:none; }}
 footer {{ color:var(--muted); font-size:13px; margin-top:34px; border-top:1px solid var(--line);
   padding-top:14px; }}
 textarea {{ position:absolute; left:-9999px; }}
</style>
<div class=wrap>
<h1>Receipts — {esc(name)}</h1>
<p class=sub>Everything this repository claims, and what backs it. {esc(verdict)}.</p>

<div class=score>
  <div class=broken><b>{total['broken']}</b><span>contradicted by the repository</span></div>
  <div class=unbacked><b>{total['unbacked']}</b><span>nothing behind them</span></div>
  <div class=drifted><b>{total['drifted']}</b><span>no longer matching</span></div>
  <div><b>{len(ran)}</b><span>checks that could run</span></div>
</div>

<div class=bar>
  <label><input type=checkbox id=only> hide the checks that found nothing</label>
  <button id=copy>copy findings for a pull request</button>
</div>

{''.join(section_block(s) for s in ran)}

{('<section><h2>Not checked<span class=q>and why</span></h2><ul>' + skipped_rows + '</ul></section>') if skipped else ''}

<footer>Every check reads the repository on disk. Nothing is imported, nothing is executed, and no
request leaves this machine — including for the badges, whose claims are read out of their own
URLs. A claim this tool cannot check is listed as not checked rather than passed.</footer>
</div>
<textarea id=plain>{esc(plain)}</textarea>
<script>
 document.getElementById('only').addEventListener('change', function (event) {{
   document.body.classList.toggle('only-problems', event.target.checked);
 }});
 document.getElementById('copy').addEventListener('click', function () {{
   var box = document.getElementById('plain');
   box.select();
   document.execCommand('copy');
   this.textContent = 'copied';
   setTimeout(function () {{ document.getElementById('copy').textContent =
     'copy findings for a pull request'; }}, 1400);
 }});
</script>"""
