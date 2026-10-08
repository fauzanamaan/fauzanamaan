"""Generate the looping ASCII robot arm SVG for the profile header.

The arm picks letter blocks from a feeder, lines them up on a shelf to
spell a phrase, idles, then knocks them off so they tumble to the floor.
It alternates NAME with each entry in PHRASES and loops forever.

Run from the repo root:
    python scripts/make_robot_arm.py
"""

import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "robot-arm.svg"

# What the arm spells. The loop is NAME, phrase 1, NAME, phrase 2, ...
NAME = "FAUZAN"
PHRASES = ["BUILDS ROBOTS", "TRAINS MODELS", "WRANGLES DATA"]

# Outer canvas, the same width and frame as the other sections
CANVAS_W = 860
HEADER_H = 44
SCENE_SCALE = 1.15

# The scene the arm works in, before scaling
WIDTH = 460
HEIGHT = 312

# Colors
BG = "#0d1117"
BORDER = "#30363d"
MUTED = "#8b949e"
ARM = "#c9d1d9"
ACCENT = "#39d353"
# Toy block look: a colored frame around a pale face, colors cycle per letter
BLOCK_FACE = "#f4ecd8"
BLOCK_COLORS = ["#e5484d", "#2f9e5b", "#e8590c", "#2b6cd4", "#c79a00"]
BLOCK_SIZE = 21

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

# Arm geometry: shoulder position and the length of each of the two links
SHOULDER = (230, 34)
LINK = 135
# The carried block hangs this far below the wrist joint
GRIP_DROP = 20

# Block layout
SLOT_PITCH = 23
MAX_SLOTS = 18
BLOCK_Y = 196
SHELF_Y = 209
FLOOR_Y = 284

# Where new blocks are picked up, and where the arm waits
FEED = (422, 80)
REST = (230, 128)

# Timing in seconds
T_TRAVEL = 0.20
T_DIP = 0.07
T_HOLD = 2.2
T_SWEEP = 0.7
T_AFTER = 1.3

# Tumble physics in px and seconds
GRAVITY = 900
HOP_SPEED = -120
REST_ON_FLOOR = 0.25
FADE = 0.25

# Fixed seed so the tumble looks the same on every rebuild
random.seed(7)


def solve_angles(x, y):
    # Inverse kinematics for a two link arm with equal links.
    # (x, y) is where the carried block should be, so aim the wrist above it.
    dx = x - SHOULDER[0]
    dy = (y - GRIP_DROP) - SHOULDER[1]
    dist = math.hypot(dx, dy)
    if dist > 2 * LINK:
        raise SystemExit(f"target ({x}, {y}) is out of reach, increase LINK")
    phi = math.atan2(dy, dx)
    alpha = math.acos(dist / (2 * LINK))
    shoulder = math.degrees(phi + alpha)
    elbow = math.degrees(-2 * alpha)
    # The wrist cancels both so the gripper always hangs straight down
    wrist = -(shoulder + elbow)
    return shoulder, elbow, wrist


class Timeline:
    """Collects arm waypoints as (time, x, y)."""

    def __init__(self):
        self.t = 0.0
        self.points = [(0.0, FEED[0], FEED[1])]

    def move(self, x, y, dt):
        self.t += dt
        self.points.append((self.t, x, y))

    def wait(self, dt):
        _, x, y = self.points[-1]
        self.move(x, y, dt)


def slot_x(index, length):
    # Center the phrase on the shelf
    start = (WIDTH - length * SLOT_PITCH) / 2
    return start + index * SLOT_PITCH + SLOT_PITCH / 2


def build_sequence():
    sequence = []
    for phrase in PHRASES:
        sequence.append(NAME)
        sequence.append(phrase)
    for text in sequence:
        if len(text) > MAX_SLOTS:
            raise SystemExit(f'"{text}" is longer than {MAX_SLOTS} characters')
    return sequence


def plan():
    # Walk through the whole loop once and record every event time
    tl = Timeline()
    blocks = []

    for text in build_sequence():
        placed = []
        for i, char in enumerate(text):
            if char == " ":
                continue
            color = BLOCK_COLORS[len(placed) % len(BLOCK_COLORS)]
            x = slot_x(i, len(text))
            pick_t = tl.t
            tl.move(x, BLOCK_Y - 28, T_TRAVEL)
            tl.move(x, BLOCK_Y, T_DIP)
            place_t = tl.t
            tl.move(x, BLOCK_Y - 28, T_DIP)
            tl.move(FEED[0], FEED[1], T_TRAVEL)
            placed.append({"char": char, "x": x, "color": color,
                           "pick": pick_t, "place": place_t})

        # Idle with a slight sway while the phrase is on show
        tl.move(REST[0], REST[1], 0.3)
        sways = 4
        for s in range(sways):
            offset = 9 if s % 2 == 0 else -9
            tl.move(REST[0] + offset, REST[1], T_HOLD / sways)

        # Sweep along the shelf and knock every block off
        x0 = placed[0]["x"] - 16
        x1 = placed[-1]["x"] + 16
        tl.move(x0, BLOCK_Y, 0.35)
        sweep_start = tl.t
        steps = 10
        for s in range(1, steps + 1):
            tl.move(x0 + (x1 - x0) * s / steps, BLOCK_Y, T_SWEEP / steps)
        for b in placed:
            hit = (b["x"] - 12 - x0) / (x1 - x0)
            b["launch"] = sweep_start + hit * T_SWEEP

        # Back to the feeder, then a short pause before the next phrase
        tl.move(FEED[0], FEED[1], 0.4)
        tl.wait(T_AFTER - 0.4)
        blocks.extend(placed)

    return tl, blocks


def block_markup(char, color):
    # A rounded square with a colored frame and the letter inside,
    # drawn centered on (0, 0) so it can spin around its middle
    half = BLOCK_SIZE / 2
    inner = BLOCK_SIZE - 3
    return (
        f'<rect x="{-half}" y="{-half}" width="{BLOCK_SIZE}" height="{BLOCK_SIZE}" '
        f'rx="4" fill="{color}"/>'
        f'<rect x="{-inner / 2}" y="{-inner / 2}" width="{inner}" height="{inner}" '
        f'rx="2.5" fill="{BLOCK_FACE}"/>'
        f'<text class="b" y="4.5" font-size="13" fill="{color}">{char}</text>'
    )


def fmt(value):
    return f"{value:.5f}".rstrip("0").rstrip(".")


def joint_animation(tl, total, which):
    # One rotate animation per joint, all sharing the same clock
    times = []
    values = []
    for t, x, y in tl.points:
        angles = solve_angles(x, y)
        times.append(fmt(t / total))
        values.append(f"{angles[which]:.2f}")
    times[-1] = "1"
    return (
        f'<animateTransform attributeName="transform" type="rotate" '
        f'dur="{total:.2f}s" repeatCount="indefinite" '
        f'keyTimes="{";".join(times)}" values="{";".join(values)}"/>'
    )


def tumble(block, total):
    # Sample a simple projectile path from the shelf down to the floor
    vx = random.uniform(20, 70)
    drop = FLOOR_Y - BLOCK_Y
    disc = HOP_SPEED ** 2 + 2 * GRAVITY * drop
    fall_time = (-HOP_SPEED + math.sqrt(disc)) / GRAVITY
    spin = random.choice([-270, -180, -90, 90, 180, 270])

    launch = block["launch"]
    land = launch + fall_time
    samples = 8
    times = ["0", fmt(launch / total)]
    moves = ["0,0", "0,0"]
    for s in range(1, samples + 1):
        t = fall_time * s / samples
        x = vx * t
        y = HOP_SPEED * t + 0.5 * GRAVITY * t * t
        # Keep the block inside the frame
        x = min(x, WIDTH - 16 - block["x"])
        times.append(fmt((launch + t) / total))
        moves.append(f"{x:.1f},{min(y, drop):.1f}")
    times.append("1")
    moves.append(moves[-1])

    fade_start = land + REST_ON_FLOOR
    fade_end = fade_start + FADE
    if fade_end >= total:
        raise SystemExit("increase T_AFTER, the last blocks have no time to fade")

    return {
        "move_times": ";".join(times),
        "moves": ";".join(moves),
        "spin_times": f"0;{fmt(launch / total)};{fmt(land / total)};1",
        "spins": f"0;0;{spin};{spin}",
        "fade_start": fade_start,
        "fade_end": fade_end,
    }


def render():
    tl, blocks = plan()
    total = tl.t
    dur = f'dur="{total:.2f}s" repeatCount="indefinite"'

    canvas_h = round(HEADER_H + HEIGHT * SCENE_SCALE)
    scene_x = round((CANVAS_W - WIDTH * SCENE_SCALE) / 2)

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{canvas_h}" '
        f'viewBox="0 0 {CANVAS_W} {canvas_h}" role="img" '
        f'aria-label="ASCII robot arm stacking letter blocks that spell {NAME}">'
    )
    parts.append(
        f"<style>text {{ font-family: {FONT}; font-size: 12px; }} "
        f".b {{ font-weight: 700; text-anchor: middle; }}</style>"
    )
    # Frame, corner brackets and header strip, matching the info panel
    w, h, m, s = CANVAS_W, canvas_h, 10, 14
    parts.append(f'<rect width="{w}" height="{h}" rx="10" fill="{BG}"/>')
    parts.append(
        f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="9" '
        f'fill="none" stroke="{BORDER}" stroke-width="1.5"/>'
    )
    corners = (
        f"M{m} {m + s} V{m} H{m + s} M{w - m - s} {m} H{w - m} V{m + s} "
        f"M{w - m} {h - m - s} V{h - m} H{w - m - s} M{m + s} {h - m} H{m} V{h - m - s}"
    )
    parts.append(f'<path d="{corners}" fill="none" stroke="{ACCENT}" stroke-width="1.5" opacity="0.7"/>')
    label = f'font-size="10" fill="{MUTED}" letter-spacing="1.5"'
    parts.append(f'<text x="28" y="32" {label}>WORKCELL // ARM-01</text>')
    parts.append(
        f'<circle cx="{w - 28 - 68}" cy="28" r="4" fill="{ACCENT}">'
        f'<animate attributeName="opacity" values="1;0.3;1" dur="1.8s" repeatCount="indefinite"/></circle>'
    )
    parts.append(f'<text x="{w - 28}" y="32" text-anchor="end" {label}>RUNNING</text>')
    parts.append(f'<line x1="28" y1="44" x2="{w - 28}" y2="44" stroke="{BORDER}"/>')

    # Everything below is drawn in scene coordinates, then scaled and centered
    parts.append(f'<g transform="translate({scene_x},{HEADER_H}) scale({SCENE_SCALE})">')

    # Shelf and floor, drawn with characters
    shelf_w = MAX_SLOTS * SLOT_PITCH + 10
    shelf_x = (WIDTH - shelf_w) / 2
    parts.append(
        f'<text x="{shelf_x}" y="{SHELF_Y + 8}" fill="{MUTED}" textLength="{shelf_w}" '
        f'lengthAdjust="spacingAndGlyphs">{"=" * 60}</text>'
    )
    parts.append(
        f'<text x="14" y="{FLOOR_Y + 16}" fill="{BORDER}" textLength="{WIDTH - 28}" '
        f'lengthAdjust="spacingAndGlyphs">{"_" * 62}</text>'
    )

    # Feeder chute in the top right
    fx, fy = FEED
    parts.append(f'<text x="{fx}" y="{fy - 50}" fill="{MUTED}" text-anchor="middle" font-size="10">FEED</text>')
    for row in range(2):
        parts.append(
            f'<text x="{fx}" y="{fy - 34 + row * 12}" fill="{MUTED}" text-anchor="middle" '
            f'textLength="35" lengthAdjust="spacingAndGlyphs">|   |</text>'
        )

    # Blocks sitting on the shelf, each one later tumbles to the floor
    for b in blocks:
        fall = tumble(b, total)
        show = b["place"] / total
        op_times = ";".join([
            "0", fmt(show - 0.00002), fmt(show),
            fmt(fall["fade_start"] / total), fmt(fall["fade_end"] / total), "1",
        ])
        parts.append(
            f'<g transform="translate({b["x"]:.1f},{BLOCK_Y})" opacity="0">'
            f'<animate attributeName="opacity" {dur} keyTimes="{op_times}" values="0;0;1;1;0;0"/>'
            f'<g><animateTransform attributeName="transform" type="translate" {dur} '
            f'keyTimes="{fall["move_times"]}" values="{fall["moves"]}"/>'
            f'<g><animateTransform attributeName="transform" type="rotate" {dur} '
            f'keyTimes="{fall["spin_times"]}" values="{fall["spins"]}"/>'
            f'{block_markup(b["char"], b["color"])}</g></g></g>'
        )

    # Ceiling mount
    sx, sy = SHOULDER
    parts.append(
        f'<text x="{sx}" y="{sy - 12}" fill="{MUTED}" text-anchor="middle">'
        f"___[ARM-01]___</text>"
    )

    # The arm: shoulder, elbow and wrist are nested so each joint
    # rotates relative to the link before it
    link_text = (
        f'<text x="6" y="4" fill="{ARM}" textLength="{LINK - 12}" '
        f'lengthAdjust="spacingAndGlyphs">{"=" * 18}</text>'
    )
    joint = f'<text class="b" y="5" fill="{ACCENT}" font-size="14">O</text>'

    parts.append(f'<g transform="translate({sx},{sy})">')
    parts.append(f"<g>{joint_animation(tl, total, 0)}{link_text}{joint}")
    parts.append(f'<g transform="translate({LINK},0)">')
    parts.append(f"<g>{joint_animation(tl, total, 1)}{link_text}{joint}")
    parts.append(f'<g transform="translate({LINK},0)">')
    parts.append(f"<g>{joint_animation(tl, total, 2)}")

    # Gripper, always upright
    parts.append(f'<text class="b" y="5" fill="{ACCENT}" font-size="14">O</text>')
    parts.append(f'<text class="b" y="13" fill="{ARM}">_|_</text>')
    parts.append(f'<text class="b" x="-15" y="{GRIP_DROP + 4}" fill="{ARM}">(</text>')
    parts.append(f'<text class="b" x="15" y="{GRIP_DROP + 4}" fill="{ARM}">)</text>')

    # The block being carried, one hidden copy per letter
    for b in blocks:
        times = f'0;{fmt(b["pick"] / total)};{fmt(b["place"] / total)}'
        parts.append(
            f'<g transform="translate(0,{GRIP_DROP})" opacity="0">'
            f'<animate attributeName="opacity" {dur} calcMode="discrete" '
            f'keyTimes="{times}" values="0;1;0"/>'
            f'{block_markup(b["char"], b["color"])}</g>'
        )

    parts.append("</g></g></g></g></g></g>")
    parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts), total


def main():
    svg, total = render()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.relative_to(ROOT)} ({size_kb:.0f} KB, loop is {total:.1f}s)")


if __name__ == "__main__":
    main()
