"""Generate one animated SVG card per project and update the README.

Reads projects.json, writes cards/<slug>.svg, then rewrites the block
between the PROJECTS markers in README.md.

Run from the repo root:
    python scripts/make_project_cards.py
"""

import json
import re
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "projects.json"
CARDS_DIR = ROOT / "cards"
README = ROOT / "README.md"

START_MARK = "<!-- PROJECTS:START -->"
END_MARK = "<!-- PROJECTS:END -->"

# Card geometry
WIDTH = 425
HEIGHT = 150
PAD = 20
CARDS_PER_ROW = 2

# Colors
BG = "#0d1117"
BORDER = "#30363d"
TRACK = "#21262d"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
STATUS_COLORS = {
    "active": "#39d353",
    "paused": "#d29922",
    "shipped": "#58a6ff",
}
DEFAULT_COLOR = "#39d353"

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

# Approximate monospace character widths in px for each font size
TITLE_CHAR_W = 9.1
TAG_CHAR_W = 6.7

# Seconds between one card starting and the next
CARD_STAGGER = 0.25


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "project"


def repo_url(repo):
    if not repo:
        return None
    if repo.startswith("http"):
        return repo
    return f"https://github.com/{repo}"


def typing_values(char_count, char_w):
    # One discrete step per character, so the title appears typed
    steps = [round(i * char_w, 1) for i in range(char_count + 1)]
    return ";".join(str(s) for s in steps)


def render_card(project, index):
    name = project["name"]
    blurb = project.get("blurb", "")
    status = project.get("status", "active")
    progress = project.get("progress")
    stack = project.get("stack", [])

    accent = STATUS_COLORS.get(status.lower(), DEFAULT_COLOR)
    base = index * CARD_STAGGER
    inner_w = WIDTH - 2 * PAD

    title = f"~/{name}"
    # Keep the title clear of the status label on the right
    max_title_chars = int((inner_w - 90) / TITLE_CHAR_W)
    if len(title) > max_title_chars:
        title = title[: max_title_chars - 1] + "…"
    title_w = len(title) * TITLE_CHAR_W
    type_dur = round(len(title) * 0.045, 2)
    type_begin = round(base + 0.5, 2)
    type_vals = typing_values(len(title), TITLE_CHAR_W)

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{escape(name)}">'
    )
    parts.append(f"""<style>
  text {{ font-family: {FONT}; }}
  .border {{ stroke-dasharray: 1; stroke-dashoffset: 1; animation: draw 1.1s ease-out both; }}
  .fade {{ animation: fade 0.5s ease-out both; }}
  .pop {{ animation: pop 0.35s ease-out both; }}
  .pulse {{ animation: pulse 1.8s ease-in-out infinite; transform-origin: center; transform-box: fill-box; }}
  @keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
  @keyframes fade {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes pop {{ from {{ opacity: 0; transform: translateY(4px) scale(0.92); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes pulse {{ 0%, 100% {{ opacity: 1; transform: scale(1); }} 50% {{ opacity: 0.35; transform: scale(1.6); }} }}
  @media (prefers-reduced-motion: reduce) {{
    .border, .fade, .pop, .pulse {{ animation: none; stroke-dashoffset: 0; }}
  }}
</style>""")

    # Background and self-drawing border
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" rx="10" fill="{BG}"/>')
    parts.append(
        f'<rect class="border" x="1" y="1" width="{WIDTH - 2}" height="{HEIGHT - 2}" rx="9" '
        f'fill="none" stroke="{BORDER}" stroke-width="1.5" pathLength="1" '
        f'style="animation-delay:{base}s"/>'
    )
    # Accent line that draws along the top edge
    parts.append(
        f'<rect x="{PAD}" y="0" width="0" height="2" fill="{accent}">'
        f'<animate attributeName="width" from="0" to="{inner_w}" dur="0.8s" '
        f'begin="{round(base + 0.2, 2)}s" fill="freeze"/></rect>'
    )

    # Typed title with a block cursor that rides the edge then disappears
    clip_id = f"type-{index}"
    parts.append(
        f'<clipPath id="{clip_id}"><rect x="{PAD}" y="14" width="0" height="26">'
        f'<animate attributeName="width" values="{type_vals}" calcMode="discrete" '
        f'dur="{type_dur}s" begin="{type_begin}s" fill="freeze"/></rect></clipPath>'
    )
    parts.append(
        f'<text x="{PAD}" y="33" font-size="15" font-weight="700" fill="{accent}" '
        f'clip-path="url(#{clip_id})">{escape(title)}</text>'
    )
    cursor_vals = ";".join(
        str(round(PAD + i * TITLE_CHAR_W, 1)) for i in range(len(title) + 1)
    )
    parts.append(
        f'<rect x="{PAD}" y="20" width="8" height="15" fill="{accent}" opacity="0">'
        f'<animate attributeName="x" values="{cursor_vals}" calcMode="discrete" '
        f'dur="{type_dur}s" begin="{type_begin}s" fill="freeze"/>'
        f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.01;0.99;1" '
        f'dur="{round(type_dur + 0.6, 2)}s" begin="{type_begin}s" fill="freeze"/></rect>'
    )

    # Status label and pulsing dot, right aligned
    status_x = WIDTH - PAD
    status_w = len(status) * 6.7
    delay = round(base + 0.7, 2)
    parts.append(
        f'<g class="fade" style="animation-delay:{delay}s">'
        f'<circle class="pulse" cx="{round(status_x - status_w - 10, 1)}" cy="29" r="3.5" fill="{accent}"/>'
        f'<text x="{status_x}" y="33" font-size="11" fill="{MUTED}" text-anchor="end">'
        f"{escape(status)}</text></g>"
    )

    # Blurb, wrapped to at most two lines
    y = 58
    lines = textwrap.wrap(blurb, width=53)[:2]
    if len(textwrap.wrap(blurb, width=53)) > 2:
        lines[1] = lines[1][:52] + "…"
    for i, line in enumerate(lines):
        delay = round(base + 0.9 + i * 0.12, 2)
        parts.append(
            f'<text class="fade" x="{PAD}" y="{y}" font-size="12" fill="{TEXT}" '
            f'style="animation-delay:{delay}s">{escape(line)}</text>'
        )
        y += 17
    y += 6

    # Optional progress bar that fills to the given percent
    if progress is not None:
        pct = max(0, min(100, int(progress)))
        bar_w = inner_w - 44
        fill_w = round(bar_w * pct / 100, 1)
        bar_begin = round(base + 1.2, 2)
        parts.append(
            f'<rect x="{PAD}" y="{y}" width="{bar_w}" height="6" rx="3" fill="{TRACK}"/>'
        )
        parts.append(
            f'<rect x="{PAD}" y="{y}" width="0" height="6" rx="3" fill="{accent}">'
            f'<animate attributeName="width" from="0" to="{fill_w}" dur="1s" '
            f'begin="{bar_begin}s" fill="freeze" calcMode="spline" '
            f'keySplines="0.2 0.8 0.2 1" keyTimes="0;1"/></rect>'
        )
        parts.append(
            f'<text class="fade" x="{WIDTH - PAD}" y="{y + 7}" font-size="11" fill="{MUTED}" '
            f'text-anchor="end" style="animation-delay:{bar_begin}s">{pct}%</text>'
        )
        y += 20

    # Optional private badge with a small lock, right aligned on the tag row
    tags_right = WIDTH - PAD
    if project.get("private"):
        badge_w = 74
        bx = WIDTH - PAD - badge_w
        delay = round(base + 1.5, 2)
        parts.append(
            f'<g class="pop" style="animation-delay:{delay}s; transform-origin:{bx + badge_w / 2}px {y + 10}px">'
            f'<rect x="{bx}" y="{y}" width="{badge_w}" height="20" rx="10" fill="none" '
            f'stroke="{MUTED}" stroke-dasharray="3 2"/>'
            f'<rect x="{bx + 10}" y="{y + 9}" width="8" height="6" rx="1" fill="{MUTED}"/>'
            f'<path d="M{bx + 11.5} {y + 9} v-2 a2.5 2.5 0 0 1 5 0 v2" fill="none" '
            f'stroke="{MUTED}" stroke-width="1.3"/>'
            f'<text x="{bx + 23}" y="{y + 14}" font-size="11" fill="{MUTED}">private</text></g>'
        )
        tags_right = bx - 8

    # Stack tags that pop in one after another
    x = PAD
    for i, tag in enumerate(stack):
        tag_w = round(len(tag) * TAG_CHAR_W + 16, 1)
        # Stop before a tag would spill out of the card
        if x + tag_w > tags_right:
            break
        delay = round(base + 1.5 + i * 0.1, 2)
        parts.append(
            f'<g class="pop" style="animation-delay:{delay}s; transform-origin:{x + tag_w / 2}px {y + 10}px">'
            f'<rect x="{x}" y="{y}" width="{tag_w}" height="20" rx="10" fill="{TRACK}" '
            f'stroke="{BORDER}"/>'
            f'<text x="{round(x + tag_w / 2, 1)}" y="{y + 14}" font-size="11" fill="{MUTED}" '
            f'text-anchor="middle">{escape(tag)}</text></g>'
        )
        x += tag_w + 8

    parts.append("</svg>")
    return "\n".join(parts)


def build_readme_block(entries):
    # entries is a list of (svg_path, url, name).
    # Plain images instead of a table, so GitHub draws no cell borders.
    rows = []
    for i in range(0, len(entries), CARDS_PER_ROW):
        cells = []
        for path, url, name in entries[i : i + CARDS_PER_ROW]:
            img = f'<img src="./{path}" width="49%" alt="{escape(name)}" />'
            if url:
                img = f'<a href="{url}">{img}</a>'
            cells.append(f"  {img}")
        rows.append("\n".join(cells))
    header = '  <img src="./assets/section-building.svg" width="100%" alt="Currently building" />'
    body = "\n  <br />\n".join(rows)
    return f'<p align="center">\n{header}\n  <br />\n{body}\n</p>'


def render_section_header(count):
    # A label strip in the same style as the other section headers
    w, h = 860, 40
    label = f'font-family="{FONT}" font-size="10" fill="{MUTED}" letter-spacing="1.5"'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="Currently building">'
        f'<text x="28" y="24" {label}>CURRENTLY BUILDING // ARM-01</text>'
        f'<text x="{w - 28}" y="24" text-anchor="end" {label}>{count:02d} PROJECTS</text>'
        f'<line x1="28" y1="36" x2="{w - 28}" y2="36" stroke="{BORDER}"/>'
        f"</svg>"
    )


def update_readme(block):
    text = README.read_text(encoding="utf-8")
    if START_MARK not in text or END_MARK not in text:
        raise SystemExit(f"README.md is missing {START_MARK} / {END_MARK}")
    pattern = re.compile(
        re.escape(START_MARK) + r".*?" + re.escape(END_MARK), re.DOTALL
    )
    new_text = pattern.sub(f"{START_MARK}\n{block}\n{END_MARK}", text)
    README.write_text(new_text, encoding="utf-8")


def main():
    projects = json.loads(CONFIG.read_text(encoding="utf-8"))

    # Clear old cards so removed projects do not leave stale files
    CARDS_DIR.mkdir(exist_ok=True)
    for old in CARDS_DIR.glob("*.svg"):
        old.unlink()

    entries = []
    used = set()
    for index, project in enumerate(projects):
        slug = slugify(project["name"])
        # Avoid two projects writing to the same file
        while slug in used:
            slug += "-x"
        used.add(slug)

        svg = render_card(project, index)
        out = CARDS_DIR / f"{slug}.svg"
        out.write_text(svg, encoding="utf-8")
        entries.append((f"cards/{slug}.svg", repo_url(project.get("repo")), project["name"]))
        print(f"wrote {out.relative_to(ROOT)}")

    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "section-building.svg").write_text(render_section_header(len(entries)), encoding="utf-8")
    print("wrote assets/section-building.svg")

    update_readme(build_readme_block(entries))
    print(f"updated README.md with {len(entries)} project(s)")


if __name__ == "__main__":
    main()
