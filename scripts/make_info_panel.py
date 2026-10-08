"""Generate the operator panel SVG and the LinkedIn button SVG.

The panel shows who I am, a small neural network for current focus
areas, and a route strip for locations.

Run from the repo root:
    python scripts/make_info_panel.py
"""

from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# Content
NAME = "FAUZAN AMAAN MOHAMMED"
CURRENTLY = "Senior, B.S. Computer Science, Arizona State University"
NEXT_STEP = "M.S. Robotics and Autonomous Systems"
LANGUAGES = ["Python", "Java", "C++"]
FOCUS = [
    "In-context Learning",
    "Neural Networks",
    "Imitation Learning",
    "AI Safety",
    "Robotics and Manufacturing",
]
LOCATIONS = ["Dubai, UAE", "Tempe, AZ, US", "Kochi, Kerala, India"]
LINKEDIN_USER = "fauzanamaan"

# Canvas
WIDTH = 860
HEIGHT = 344
PAD = 28

# Colors
BG = "#0d1117"
BORDER = "#30363d"
TRACK = "#21262d"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
ACCENT = "#39d353"
BLUE = "#58a6ff"

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

# Width of one character of the name at its font size
NAME_CHAR_W = 14.4

STYLE = f"""<style>
  text {{ font-family: {FONT}; }}
  .label {{ font-size: 10px; fill: {MUTED}; letter-spacing: 1.5px; }}
  .value {{ font-size: 13px; fill: {TEXT}; }}
  .fade {{ animation: fade 0.5s ease-out both; }}
  .pop {{ animation: pop 0.35s ease-out both; }}
  @keyframes fade {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes pop {{ from {{ opacity: 0; transform: scale(0.9); }} to {{ opacity: 1; transform: none; }} }}
</style>"""


def frame(parts):
    # Background, border, corner brackets and a one time scan line
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" rx="10" fill="{BG}"/>')
    parts.append(
        f'<rect x="1" y="1" width="{WIDTH - 2}" height="{HEIGHT - 2}" rx="9" '
        f'fill="none" stroke="{BORDER}" stroke-width="1.5"/>'
    )
    w, h, m, s = WIDTH, HEIGHT, 10, 14
    corners = (
        f"M{m} {m + s} V{m} H{m + s} M{w - m - s} {m} H{w - m} V{m + s} "
        f"M{w - m} {h - m - s} V{h - m} H{w - m - s} M{m + s} {h - m} H{m} V{h - m - s}"
    )
    parts.append(f'<path d="{corners}" fill="none" stroke="{ACCENT}" stroke-width="1.5" opacity="0.7"/>')
    parts.append(
        f'<rect x="2" y="0" width="{WIDTH - 4}" height="2" fill="{ACCENT}" opacity="0">'
        f'<animate attributeName="y" from="0" to="{HEIGHT}" dur="1.3s" fill="freeze"/>'
        f'<animate attributeName="opacity" values="0.7;0.7;0" keyTimes="0;0.85;1" dur="1.3s" fill="freeze"/>'
        f"</rect>"
    )


def header(parts):
    parts.append(f'<text class="label" x="{PAD}" y="32">OPERATOR PROFILE // ARM-01</text>')
    # Pulsing status light
    parts.append(
        f'<circle cx="{WIDTH - PAD - 52}" cy="28" r="4" fill="{ACCENT}">'
        f'<animate attributeName="opacity" values="1;0.3;1" dur="1.8s" repeatCount="indefinite"/></circle>'
    )
    parts.append(f'<text class="label" x="{WIDTH - PAD}" y="32" text-anchor="end">ONLINE</text>')
    parts.append(f'<line x1="{PAD}" y1="44" x2="{WIDTH - PAD}" y2="44" stroke="{BORDER}"/>')

    # Name, typed out one character at a time
    name_w = len(NAME) * NAME_CHAR_W
    steps = ";".join(str(round(i * NAME_CHAR_W, 1)) for i in range(len(NAME) + 1))
    dur = round(len(NAME) * 0.05, 2)
    parts.append(
        f'<clipPath id="name-clip"><rect x="{PAD}" y="56" width="0" height="36">'
        f'<animate attributeName="width" values="{steps}" calcMode="discrete" '
        f'dur="{dur}s" begin="0.4s" fill="freeze"/></rect></clipPath>'
    )
    parts.append(
        f'<text x="{PAD}" y="84" font-size="24" font-weight="700" fill="{ACCENT}" '
        f'textLength="{name_w}" lengthAdjust="spacingAndGlyphs" '
        f'clip-path="url(#name-clip)">{escape(NAME)}</text>'
    )


def left_column(parts):
    rows = [("CURRENTLY", CURRENTLY), ("NEXT STEP", NEXT_STEP)]
    y = 122
    for i, (label, value) in enumerate(rows):
        delay = round(1.5 + i * 0.2, 2)
        parts.append(
            f'<g class="fade" style="animation-delay:{delay}s">'
            f'<text class="label" x="{PAD}" y="{y}">{label}</text>'
            f'<text class="value" x="{PAD}" y="{y + 19}">{escape(value)}</text></g>'
        )
        y += 50

    # Languages as ranked chips
    parts.append(
        f'<text class="label fade" x="{PAD}" y="{y}" style="animation-delay:1.9s">LANGUAGES</text>'
    )
    x = PAD
    for i, lang in enumerate(LANGUAGES):
        chip_w = round((len(lang) + 3) * 7.8 + 18, 1)
        delay = round(2.0 + i * 0.12, 2)
        parts.append(
            f'<g class="pop" style="animation-delay:{delay}s; transform-origin:{x + chip_w / 2}px {y + 21}px">'
            f'<rect x="{x}" y="{y + 9}" width="{chip_w}" height="24" rx="12" fill="{TRACK}" stroke="{BORDER}"/>'
            f'<text x="{x + 10}" y="{y + 25.5}" font-size="13">'
            f'<tspan fill="{ACCENT}">0{i + 1}</tspan><tspan fill="{TEXT}"> {escape(lang)}</tspan></text></g>'
        )
        x += chip_w + 8


def focus_network(parts):
    # A small network: one input, three hidden nodes, one output per focus area
    parts.append(f'<text class="label fade" x="500" y="122" style="animation-delay:1.6s">CURRENT FOCUS</text>')

    src = (512, 201)
    hidden = [(558, 171), (558, 201), (558, 231)]
    out_x = 606
    outs = [(out_x, 143 + i * 29) for i in range(len(FOCUS))]

    parts.append('<g class="fade" style="animation-delay:1.8s">')

    # Every connection, drawn faintly
    for hx, hy in hidden:
        parts.append(f'<line x1="{src[0]}" y1="{src[1]}" x2="{hx}" y2="{hy}" stroke="{BORDER}"/>')
        for ox, oy in outs:
            parts.append(f'<line x1="{hx}" y1="{hy}" x2="{ox}" y2="{oy}" stroke="{BORDER}" opacity="0.7"/>')

    # A signal travels to each focus area in turn, and its node lights up
    cycle = len(FOCUS) * 0.7 + 0.8
    for i, (ox, oy) in enumerate(outs):
        hx, hy = hidden[i % len(hidden)]
        begin = round(2.4 + i * 0.7, 2)
        path = f"M{src[0]} {src[1]} L{hx} {hy} L{ox} {oy}"
        parts.append(
            f'<circle r="2.5" fill="{ACCENT}" opacity="0">'
            f'<animateMotion path="{path}" dur="{cycle}s" begin="{begin}s" repeatCount="indefinite" '
            f'keyPoints="0;1;1" keyTimes="0;0.2;1" calcMode="linear"/>'
            f'<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.02;0.19;0.2;1" '
            f'dur="{cycle}s" begin="{begin}s" repeatCount="indefinite"/></circle>'
        )
        parts.append(
            f'<circle cx="{ox}" cy="{oy}" r="4.5" fill="{BG}" stroke="{BLUE}" stroke-width="1.5">'
            f'<animate attributeName="fill" values="{BG};{BG};{ACCENT};{BG};{BG}" '
            f'keyTimes="0;0.19;0.22;0.5;1" dur="{cycle}s" begin="{begin}s" repeatCount="indefinite"/>'
            f'<animate attributeName="r" values="4.5;4.5;6.5;4.5;4.5" '
            f'keyTimes="0;0.19;0.22;0.5;1" dur="{cycle}s" begin="{begin}s" repeatCount="indefinite"/></circle>'
        )
        parts.append(f'<text class="value" x="{ox + 16}" y="{oy + 4.5}">{escape(FOCUS[i])}</text>')

    for hx, hy in hidden:
        parts.append(f'<circle cx="{hx}" cy="{hy}" r="4" fill="{BG}" stroke="{MUTED}" stroke-width="1.5"/>')
    parts.append(f'<circle cx="{src[0]}" cy="{src[1]}" r="5" fill="{ACCENT}"/>')
    parts.append("</g>")


def route_strip(parts):
    parts.append(f'<line x1="{PAD}" y1="286" x2="{WIDTH - PAD}" y2="286" stroke="{BORDER}"/>')
    parts.append(f'<g class="fade" style="animation-delay:2.2s">')
    parts.append(f'<text class="label" x="{PAD}" y="310">LOCATIONS</text>')

    y = 306
    x0, x1 = 190, 730
    xs = [x0 + (x1 - x0) * i / (len(LOCATIONS) - 1) for i in range(len(LOCATIONS))]

    # Dashed route with dashes that drift along it
    parts.append(
        f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{MUTED}" stroke-dasharray="4 6">'
        f'<animate attributeName="stroke-dashoffset" from="0" to="-20" dur="1.2s" repeatCount="indefinite"/></line>'
    )
    # A pulse that travels out and back, so no direction is implied
    parts.append(
        f'<circle r="3.5" fill="{ACCENT}">'
        f'<animateMotion path="M{x0} {y} L{x1} {y}" dur="7s" repeatCount="indefinite" '
        f'keyPoints="0;1;0" keyTimes="0;0.5;1" calcMode="linear"/></circle>'
    )
    for i, (x, place) in enumerate(zip(xs, LOCATIONS)):
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="5" fill="none" stroke="{BLUE}" opacity="0">'
            f'<animate attributeName="r" values="5;12" dur="2.4s" begin="{i * 0.8}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0.8;0" dur="2.4s" begin="{i * 0.8}s" repeatCount="indefinite"/></circle>'
        )
        parts.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{BG}" stroke="{BLUE}" stroke-width="1.5"/>')
        parts.append(
            f'<text class="value" x="{x}" y="{y + 24}" text-anchor="middle" font-size="12">{escape(place)}</text>'
        )
    parts.append("</g>")


def render_panel():
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="Operator profile for {escape(NAME.title())}">',
        STYLE,
    ]
    frame(parts)
    header(parts)
    left_column(parts)
    focus_network(parts)
    route_strip(parts)
    parts.append("</svg>")
    return "\n".join(parts)


def render_linkedin():
    # A full width strip in the same frame style, the README wraps it in the profile link
    w, h = WIDTH, 48
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="LinkedIn profile">',
        STYLE,
        f'<rect width="{w}" height="{h}" rx="10" fill="{BG}"/>',
        f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="9" fill="none" stroke="{BORDER}" '
        f'stroke-width="1.5"/>',
        f'<text class="label" x="{PAD}" y="28">LINKS</text>',
        f'<text class="value" x="{PAD + 80}" y="29">'
        f'<tspan fill="{BLUE}">LinkedIn</tspan>  /in/{escape(LINKEDIN_USER)}</text>',
        f'<text class="value" x="{w - PAD - 16}" y="29" fill="{BLUE}" style="fill:{BLUE}">-&gt;'
        f'<animateTransform attributeName="transform" type="translate" values="0,0;6,0;0,0" '
        f'dur="1.4s" repeatCount="indefinite"/></text>',
        "</svg>",
    ])


def main():
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "info-panel.svg").write_text(render_panel(), encoding="utf-8")
    (ASSETS / "linkedin.svg").write_text(render_linkedin(), encoding="utf-8")
    print("wrote assets/info-panel.svg")
    print("wrote assets/linkedin.svg")


if __name__ == "__main__":
    main()
