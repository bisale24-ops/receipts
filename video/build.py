"""Build the demo video: synthesised narration over real output.

    /tmp/ttsenv/bin/python video/build.py

Every terminal frame is the tool's actual output, captured into `shots/` by running it against
public repositories and against this repository itself. Nothing is retyped for the camera. The
narration is edge-tts; the last card says so.
"""
import asyncio
import base64
import pathlib
import re
import subprocess
import sys

from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).parent
SHOTS = HERE / "shots"
BUILD = HERE / "build"
VOICE = "en-US-AndrewNeural"
W, H, FPS = 1280, 720, 30

SCENES = [
    ("card:title",
     "A repository is full of claims aimed at a stranger. A licence badge. A coverage percentage. "
     "A supported Python version. An example in the README. A line in the changelog. Every one of "
     "them is written once and then drifts, and nothing in a normal pipeline checks a single one."),
    ("card:idea",
     "Receipts asks the question they all share. What does this repository say about itself that "
     "it cannot back up? One command, four checks, one page."),
    ("shot:page",
     "The answer is a page, not a wall of text. Findings first, a score at the top, and a button "
     "that copies them into a pull request comment. One file, with no image, no stylesheet and no "
     "request in it — a badge's URL appears as text, because auditing a claim by loading the thing "
     "that makes it would defeat the point."),
    ("card:badges",
     "Badges are the loudest claim in a project and the least examined. A licence badge is checked "
     "against the LICENSE file. A Python badge against the packaging metadata. And a coverage "
     "percentage typed into a badge URL is checked against nothing, because nothing produced it."),
    ("term:urllib3",
     "Here that is, on urllib3. Its coverage badge reads one hundred percent, and the number is "
     "written into the URL by hand. Nothing measured it and nothing updates it. The other three "
     "checks come back clean, and each says what it confirmed."),
    ("term:docx",
     "Two more, both a promise made twice. Python dash docx tells pip it needs three point nine "
     "while its classifiers advertise three point seven, so PyPI shows support pip refuses. "
     "Pdfplumber is the other way round: pip admits three point eight, the classifiers start at "
     "three point ten. Both are filed upstream."),
    ("card:correction",
     "That check taught me something. I had read the floor as the lowest number stated anywhere, "
     "and written that pip honours the lowest. Both wrong: pip enforces requires-python, the "
     "classifiers only advertise."),
    ("term:scan",
     "Forty-five projects audited, every finding verified by hand against the file it accuses. "
     "Three did not hold up. Everything else came back clean, which is the result that matters: "
     "these are well kept projects, and a tool with an opinion about them would simply be wrong."),
    ("term:checks",
     "And the part that is not a demo. Sixty-nine repositories, three output forms each, a script "
     "that exits non-zero on any stderr or unexpected code. Thirty-six tests on both Pythons, "
     "seventeen of them adversarial: no Python at all, invalid metadata, a symlink loop."),
    ("card:limits",
     "One of those tests had to be rewritten. Written the normal way it passed whether or not the "
     "code was correct, because the test runner swallows warnings before they reach standard error. "
     "A test that cannot fail is not a test."),
    ("card:end",
     "Receipts. Everything this repository claims, and what backs it. M I T licensed, and the "
     "narration in this video is synthesised."),
]

CARDS = {
    "title": """<h1>Who checks the claims?</h1>
    <p class=sub>Tests check behaviour. Linters check style. Nothing checks what the repository says about itself.</p>
    <table>
      <tr><td>a licence badge</td><td class=d>copied in 2019, never read again</td></tr>
      <tr><td>coverage 100%</td><td class=d>a number typed into a URL</td></tr>
      <tr><td>requires-python</td><td class=d>last thought about a year ago</td></tr>
      <tr><td>an example in the README</td><td class=d>the function was renamed</td></tr>
      <tr><td>a line in the changelog</td><td class=d>no commit behind it</td></tr>
    </table>""",
    "idea": """<h1>Receipts</h1>
    <p class=sub>What does this repository say about itself that it cannot back up?</p>
    <table>
      <tr><th>check</th><th>the claim</th><th>what backs it</th></tr>
      <tr><td>badges</td><td>MIT · coverage 100% · Python 3.7+</td><td>the LICENSE file, the metadata, or nothing</td></tr>
      <tr><td>documentation</td><td>call it like this</td><td>what the code defines</td></tr>
      <tr><td>python floor</td><td>requires-python</td><td>the syntax that ships</td></tr>
      <tr><td>release notes</td><td>this release fixed X</td><td>the commits in the range</td></tr>
    </table>
    <p class=foot>Nothing imported, nothing executed, nothing fetched. Exit 1 only when the repository contradicts itself.</p>""",
    "badges": """<h1>What a badge can and cannot prove</h1>
    <table>
      <tr><th>badge</th><th>checked against</th><th>verdict</th></tr>
      <tr><td><code>badge/License-MIT-blue</code></td><td>the LICENSE file</td><td class=ok>checkable</td></tr>
      <tr><td><code>badge/python-3.7%2B</code></td><td><code>requires-python</code></td><td class=ok>checkable</td></tr>
      <tr><td><code>badge/coverage-100%25</code></td><td>nothing — the number is in the URL</td><td class=no>nothing behind it</td></tr>
      <tr><td><code>codecov.io/.../badge.svg</code></td><td>a server</td><td class=d>listed, not judged</td></tr>
    </table>
    <p class=foot>Only a claim written into the badge's own URL is read, which is what keeps the whole audit offline.</p>""",
    "correction": """<h1>A correction, not a feature</h1>
    <pre>before:  floor = the lowest version stated anywhere
         "pip honours the lowest"

after:   floor = requires-python, when it exists
         classifiers advertise; pip enforces</pre>
    <table>
      <tr><td>python-docx</td><td><code>requires-python &gt;=3.9</code> · classifiers from 3.7</td></tr>
      <tr><td>pdfplumber</td><td><code>python_requires &gt;=3.8</code> · classifiers from 3.10</td></tr>
    </table>
    <p class=foot>Fixed here and in the standalone checker, with three tests pinning the orderings.</p>""",
    "limits": """<h1>A test that could not fail</h1>
    <pre>fix reverted  →  test passes   ← useless
fix restored  →  test passes</pre>
    <p class=sub>pytest captures warnings before they reach stderr.</p>
    <pre>run as a subprocess:
fix reverted  →  FAILED          ← now it means something
fix restored  →  passed</pre>
    <p class=foot>Also in the report: what each check confirmed, and every check that could not run, with the reason.</p>""",
    "end": """<h1>Receipts</h1><p class=sub>Everything this repository claims, and what backs it.</p>
    <p class=big>github.com/bisale24-ops/receipts</p>
    <p class=foot>MIT licensed · 36 tests, 69 repositories, no network · planned with the Devpost
    Learn skill pack · the narration in this video is synthesised, there is no presenter.</p>""",
}

SHELL = {
    "urllib3": ("$ receipts --repo urllib3", "urllib3.txt", None, None),
    "docx": ("$ receipts --repo python-docx ; receipts --repo pdfplumber", "docx.txt", None, None),
    "scan": ("$ ./demo/scan.sh", "scan.txt", None, None),
    "checks": ("", "checks.txt", None, None),
}

IMAGES = {"page": "../demo/report.png"}

PAGE = """<!doctype html><meta charset=utf-8><style>
 body {{ margin:0; width:1280px; height:720px; background:#fbfaf7; color:#1a1a18;
   font:20px/1.5 system-ui,-apple-system,sans-serif; display:flex; flex-direction:column;
   justify-content:center; padding:0 64px; box-sizing:border-box; }}
 body:has(img.page) {{ padding:0 12px; }}
 h1 {{ font-size:40px; margin:0 0 6px; letter-spacing:-.02em; }}
 .sub {{ color:#6b6a64; margin:0 0 26px; font-size:22px; }}
 table {{ border-collapse:collapse; font-size:19px; width:100%; }}
 td, th {{ text-align:left; padding:8px 12px; border-bottom:1px solid #e2e0d8; vertical-align:top; }}
 th {{ font-size:14px; text-transform:uppercase; letter-spacing:.06em; color:#6b6a64; }}
 .ok {{ color:#2f6f45; font-weight:600; }} .no {{ color:#8a5a12; font-weight:600; }}
 .d {{ color:#6b6a64; font-weight:600; }}
 .big {{ font-size:28px; }} .foot {{ color:#6b6a64; font-size:16px; margin-top:22px; }}
 pre {{ font:17px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace; background:#fff;
   border:1px solid #e2e0d8; border-left:3px solid #8a5a12; border-radius:10px;
   padding:16px 18px; margin:0; white-space:pre-wrap; }}
 code {{ font-family:ui-monospace,Menlo,monospace; }}
 img.page {{ width:100%; height:auto; max-height:690px; object-fit:contain;
   border:1px solid #e2e0d8; border-radius:12px; background:#fff; }}
 .term {{ background:#14140f; color:#eceae2; border-radius:12px; padding:22px 24px;
   font:16px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace; white-space:pre-wrap;
   overflow:hidden; height:600px; box-sizing:border-box; }}
 .term b {{ color:#fff; }} .term .g {{ color:#7fc79a; }} .term .a {{ color:#e0b063; }}
 .term .d {{ color:#9a988e; }} .term .p {{ color:#7fc79a; }}
</style>{body}"""


def shell_html(command, source, start, end):
    text = (SHOTS / source).read_text().splitlines()
    if start is None:
        start, end = 0, len(text)
    body = []
    if command:
        for piece in command.split("\n"):
            body.append(f"<span class=p>$</span> <b>{piece.lstrip('$ ')}</b>")
        body.append("")
    for line in text[start:end]:
        escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if re.match(r"^(MATCHES|BROKEN|RENAMED|NOT JUDGED)", line):
            escaped = f"<b>{escaped}</b>"
        elif "broken · " in line or "references ·" in line:
            escaped = f"<span class=g>{escaped}</span>"
        elif line.startswith("      "):
            escaped = f"<span class=d>{escaped}</span>"
        elif line.startswith("  "):
            escaped = f"<span class=a>{escaped}</span>"
        body.append(escaped)
    return f'<div class=term>{chr(10).join(body)}</div>'


def run(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


async def render_frames():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        for name, body in CARDS.items():
            await page.set_content(PAGE.format(body=body))
            await page.screenshot(path=str(BUILD / f"card-{name}.png"))
        for name, (command, source, start, end) in SHELL.items():
            await page.set_content(PAGE.format(body=shell_html(command, source, start, end)))
            await page.screenshot(path=str(BUILD / f"term-{name}.png"))
        for name, relative in IMAGES.items():
            # embedded rather than linked: a file:// image is not loaded by set_content
            raw = (HERE / relative).resolve().read_bytes()
            data = "data:image/png;base64," + base64.b64encode(raw).decode()
            await page.set_content(PAGE.format(body=f'<img class=page src="{data}">'))
            await page.wait_for_selector("img.page")
            await page.screenshot(path=str(BUILD / f"shot-{name}.png"))
        await browser.close()


def narrate():
    for index, (_, line) in enumerate(SCENES):
        out = BUILD / f"line-{index:02d}.mp3"
        if not out.exists():
            subprocess.run([sys.executable.replace("python", "edge-tts"), "--voice", VOICE,
                            "--text", line, "--write-media", str(out)], check=True)


def main():
    BUILD.mkdir(exist_ok=True)
    asyncio.run(render_frames())
    narrate()
    segments = []
    for index, (frame, _) in enumerate(SCENES):
        kind, name = frame.split(":")
        image = BUILD / f"{kind}-{name}.png"
        audio = BUILD / f"line-{index:02d}.mp3"
        segment = BUILD / f"seg-{index:02d}.mp4"
        run("-loop", "1", "-i", str(image), "-i", str(audio),
            "-filter_complex",
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:0:color=0xfbfaf7,format=yuv420p[v];"
            f"[1:a]apad=pad_dur=0.8,aresample=48000[a]",
            "-map", "[v]", "-map", "[a]", "-r", str(FPS), "-t", f"{duration(audio) + 0.8:.2f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", str(segment))
        segments.append(segment)
    listing = BUILD / "segments.txt"
    listing.write_text("".join(f"file '{s.name}'\n" for s in segments))
    final = HERE / "receipts-demo.mp4"
    run("-f", "concat", "-safe", "0", "-i", str(listing),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        str(final))
    print(f"{final.name}  {duration(final):.1f}s")


if __name__ == "__main__":
    main()
