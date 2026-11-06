#!/usr/bin/env python3
"""Animated ASCII banner for the README: docs/media/banner.gif.

The paper plane uses the silhouette from assets/make_icon.py, the title is the figlet "ANSI Shadow" style.
Glyphs are drawn with a Windows monospace font. Needs Pillow and ffmpeg on PATH.

    python docs/showcase/ascii_banner.py
"""
from __future__ import annotations

import math
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "docs" / "media" / "banner.gif"
MONO_FONTS = (Path("C:/Windows/Fonts/CascadiaMono.ttf"), Path("C:/Windows/Fonts/consola.ttf"))

WIDTH, HEIGHT = 960, 300
FPS = 20
SECONDS = 6.4
GLYPH_SIZE = 11
LINE_HEIGHT = 12
SEED = 17

# Theme colors from src/TGManager/Themes/Scarp.xaml.
BG = (10, 10, 10)
DOTS = (26, 26, 26)
NOISE = ((42, 42, 42), (64, 64, 64), (90, 90, 90))
SUBTLE = (115, 115, 115)
MUTED = (163, 163, 163)
FG = (212, 212, 212)
WHITE = (255, 255, 255)
GREEN = (74, 222, 128)

RAMP = " .:-=+*#%@"
NOISE_GLYPHS = "01<>/\\|-+*#%=~:;"

# Same silhouette as assets/make_icon.py, in fractions of the icon square.
PLANE_BODY = [(0.205, 0.520), (0.820, 0.255), (0.660, 0.760), (0.470, 0.605)]
PLANE_FOLD = [(0.470, 0.605), (0.660, 0.760), (0.470, 0.855)]
PLANE_BOX = (44, -30, 336)  # left, top, size in pixels
FOLD_SHADE = 0.55

LETTERS = {
    "T": ["████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "],
    "G": [" ██████╗ ", "██╔════╝ ", "██║  ███╗", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "M": ["███╗   ███╗", "████╗ ████║", "██╔████╔██║", "██║╚██╔╝██║", "██║ ╚═╝ ██║", "╚═╝     ╚═╝"],
    "A": [" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "N": ["███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"],
    "E": ["███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"],
    "R": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"],
    " ": ["  "] * 6,
}
BLOCK = "█"
TITLE = "TG MANAGER"
TITLE_COL, TITLE_ROW = 59, 5

# (text, color, row, typing start in seconds); lines start at the title column.
TERMINAL = [
    ("multi-account telegram workspace · portable · windows 10/11", MUTED, 13, 1.7),
    ("$ tg-manager launch --all", FG, 16, 2.6),
    ("[ok] 10 containers running · own tdata · own proxy", GREEN, 17, 3.3),
]
TYPE_RATE = 40  # characters per second

REVEAL_START, REVEAL_SPAN, REVEAL_JITTER = 0.1, 1.1, 0.35
SCRAMBLE_LEAD = 0.3
SHINE_START, SHINE_DURATION, SHINE_WIDTH = 3.0, 1.1, 90
GLITCH_RATE = 0.004
DISSOLVE_START, DISSOLVE_SPAN = 5.2, 0.9


def mono_font() -> ImageFont.FreeTypeFont:
    for path in MONO_FONTS:
        if path.exists():
            return ImageFont.truetype(str(path), GLYPH_SIZE)
    raise SystemExit("No monospace font found: " + ", ".join(map(str, MONO_FONTS)))


def plane_map() -> Image.Image:
    """Grayscale plane in pixel space: body white, fold shaded."""
    art = Image.new("L", (WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(art)
    left, top, size = PLANE_BOX
    for polygon, shade in ((PLANE_BODY, 1.0), (PLANE_FOLD, FOLD_SHADE)):
        draw.polygon([(left + x * size, top + y * size) for x, y in polygon], fill=int(255 * shade))
    return art


def build_cells(cols: int, rows: int) -> dict[tuple[int, int], tuple[str, tuple[int, int, int]]]:
    """Maps grid cells to their final glyph and color: plane by area coverage, title and terminal verbatim."""
    art = plane_map().resize((cols, rows), Image.Resampling.BOX)
    cells = {}
    for row in range(rows):
        for col in range(cols):
            level = art.getpixel((col, row)) / 255
            if level < 0.08:
                continue
            glyph = RAMP[min(len(RAMP) - 1, 1 + int(level * (len(RAMP) - 1)))]
            color = WHITE if level > 0.8 else FG if level > 0.5 else MUTED if level > 0.3 else SUBTLE
            cells[(col, row)] = (glyph, color)

    col = TITLE_COL
    for letter in TITLE:
        lines = LETTERS[letter]
        for dy, line in enumerate(lines):
            for dx, char in enumerate(line):
                if char != " ":
                    cells[(col + dx, TITLE_ROW + dy)] = (char, WHITE if char == BLOCK else SUBTLE)
        col += len(lines[0])

    for text, color, row, _ in TERMINAL:
        for i, char in enumerate(text):
            if char != " ":
                cells[(TITLE_COL + i, row)] = (char, color)
    return cells


def typed_at(col: int, row: int) -> float | None:
    """Time at which a terminal character appears, or None for art cells."""
    for _, _, line_row, start in TERMINAL:
        if row == line_row:
            return start + (col - TITLE_COL) / TYPE_RATE
    return None


def render() -> None:
    rng = random.Random(SEED)
    font = mono_font()
    cell_w = math.ceil(font.getlength("M"))
    cols, rows = WIDTH // cell_w, HEIGHT // LINE_HEIGHT
    cells = build_cells(cols, rows)

    reveal = {}
    dissolve = {}
    for (col, row) in cells:
        sweep = (col / cols) * 0.8 + (row / rows) * 0.2
        typed = typed_at(col, row)
        reveal[(col, row)] = typed if typed is not None else REVEAL_START + sweep * REVEAL_SPAN + rng.random() * REVEAL_JITTER
        dissolve[(col, row)] = DISSOLVE_START + (1 - sweep) * DISSOLVE_SPAN * 0.6 + rng.random() * DISSOLVE_SPAN * 0.4

    tiles: dict[tuple[str, tuple[int, int, int]], Image.Image] = {}

    def tile(char: str, color: tuple[int, int, int]) -> Image.Image:
        key = (char, color)
        if key not in tiles:
            image = Image.new("RGB", (cell_w, LINE_HEIGHT), BG)
            ImageDraw.Draw(image).text((0, -1), char, font=font, fill=color)
            tiles[key] = image
        return tiles[key]

    backdrop = Image.new("RGB", (cols * cell_w, rows * LINE_HEIGHT), BG)
    for row in range(1, rows, 2):
        for col in range(2, cols, 4):
            backdrop.paste(tile(".", DOTS), (col * cell_w, row * LINE_HEIGHT))

    frames_dir = Path(tempfile.mkdtemp(prefix="tg-manager-banner-"))
    try:
        for index in range(int(SECONDS * FPS)):
            now = index / FPS
            frame = backdrop.copy()
            shine_x = (now - SHINE_START) / SHINE_DURATION * (WIDTH + 2 * SHINE_WIDTH) - SHINE_WIDTH
            for (col, row), (glyph, color) in cells.items():
                shown, gone = reveal[(col, row)], dissolve[(col, row)]
                typed = typed_at(col, row) is not None
                if now < shown - (0 if typed else SCRAMBLE_LEAD) or now >= gone + SCRAMBLE_LEAD:
                    continue
                if now < shown or now >= gone:
                    char, ink = rng.choice(NOISE_GLYPHS), rng.choice(NOISE)
                elif not typed and abs(col * cell_w + row * 3 - shine_x) < SHINE_WIDTH / 2:
                    char, ink = (RAMP[-1] if glyph in RAMP else glyph), (GREEN if glyph == BLOCK else WHITE)
                elif not typed and rng.random() < GLITCH_RATE:
                    char, ink = rng.choice(NOISE_GLYPHS), GREEN
                else:
                    char, ink = glyph, color
                frame.paste(tile(char, ink), (col * cell_w, row * LINE_HEIGHT))
            cursor = terminal_cursor(now)
            if cursor is not None:
                frame.paste(tile(BLOCK, GREEN), (cursor[0] * cell_w, cursor[1] * LINE_HEIGHT))
            canvas = Image.new("RGB", (WIDTH, HEIGHT), BG)
            canvas.paste(frame, ((WIDTH - frame.width) // 2, (HEIGHT - frame.height) // 2))
            canvas.save(frames_dir / f"f{index:04d}.png")
        encode(frames_dir)
    finally:
        shutil.rmtree(frames_dir, ignore_errors=True)


def terminal_cursor(now: float) -> tuple[int, int] | None:
    """Blinking block after the line being typed; hidden before typing and after the dissolve."""
    if now < TERMINAL[0][3] or now >= DISSOLVE_START or int(now * 2.5) % 2:
        return None
    text, _, row, start = [line for line in TERMINAL if now >= line[3]][-1]
    typed = min(len(text), int((now - start) * TYPE_RATE) + 1)
    return TITLE_COL + typed + 1, row


def encode(frames_dir: Path) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    palette = "split[a][b];[a]palettegen=max_colors=64:stats_mode=full[p];[b][p]paletteuse=dither=none:diff_mode=rectangle"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames_dir / "f%04d.png"),
         "-vf", palette, "-loop", "0", str(OUTPUT)],
        check=True,
    )
    print(f"{OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    render()
