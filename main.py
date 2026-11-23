#!/usr/bin/env python3
"""news-image-20261122 -- "The World in One Page".

Renders a one-page newspaper front page summarising the real world news
of Sunday, 22 November 2026, as a 1024x1024 PNG.

Python 3 standard library only: no PIL, no network, no installs.
The PNG encoder is written by hand (zlib + CRC32 chunks) and the
5x7 bitmap font is drawn from tables in this file.

Deterministic: two runs produce byte-identical output (no timestamps,
no randomness, no network access).

Usage:
    python3 main.py
Writes /output/entry.png
"""

import binascii
import os
import struct
import zlib

WIDTH = 1024
HEIGHT = 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 243, 234)   # warm newsprint
INK = (22, 22, 22)        # near-black
RED = (176, 26, 26)       # headline accent / kicker chips
NAVY = (24, 48, 84)       # masthead rule + sport band
OCEAN = (52, 110, 168)    # globe sea
LAND = (74, 148, 84)      # globe land
GREY = (226, 220, 208)    # ticker band
DIMGREY = (110, 106, 96)  # footer text
WHITE = (255, 255, 255)

# ------------------------------------------------------- 5x7 bitmap font
# Each glyph is 7 rows of 5 characters: '#' = ink, '.' = empty.
# Baseline is row 5 for lowercase; descenders use row 6.
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#..##", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "a": (".....", ".....", ".###.", "....#", ".####", "#...#", ".###."),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": (".....", ".....", ".###.", "#...#", "#....", "#...#", ".###."),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    "f": ("..##.", ".#..#", ".#...", "###..", ".#...", ".#...", ".#..."),
    "g": (".....", ".####", "#...#", "#...#", ".####", "....#", ".###."),
    "h": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "i": (".....", "..#..", ".....", ".##..", "..#..", "..#..", ".###."),
    "j": (".....", "...#.", ".....", "..##.", "...#.", "...#.", ".##.."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    "n": (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (".....", ".....", "####.", "#...#", "#...#", "####.", "#...."),
    "q": (".....", ".....", ".####", "#...#", "#...#", ".####", "....#"),
    "r": (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    "t": (".#...", ".#...", "###..", ".#...", ".#...", ".#...", "..##."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#"),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (".....", ".....", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (".....", "#...#", "#...#", "#..##", ".##.#", "....#", ".###."),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".....", ".##..", ".#..."),
    ":": (".....", ".....", ".##..", ".##..", ".....", ".##..", ".##.."),
    ";": (".....", ".....", ".##..", ".##..", ".....", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "%": ("#...#", "#..#.", "...#.", "..#..", ".#...", "#..#.", "#...#"),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "+": (".....", ".....", "..#..", ".###.", "..#..", ".....", "....."),
    "=": (".....", ".....", ".###.", ".....", ".###.", ".....", "....."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "*": (".....", ".#.#.", ".###.", "#####", ".###.", ".#.#.", "....."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    "<": ("....#", "...#.", "..#..", ".#...", "..#..", "...#.", "....#"),
    ">": ("#....", ".#...", "..#..", "...#.", "..#..", ".#...", "#...."),
    "[": (".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
    "]": (".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
    "\\": ("#....", "#....", ".#...", "..#..", "...#.", "....#", "....#"),
    "|": ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
}
UNKNOWN_GLYPH = FONT["?"]


def glyph_for(ch):
    return FONT.get(ch, UNKNOWN_GLYPH)


# ------------------------------------------------------------ drawing
class Canvas:
    """An RGB pixel buffer with tiny drawing primitives."""

    def __init__(self, width, height, background):
        self.w = width
        self.h = height
        self.buf = bytearray(width * height * 3)
        self.fill_rect(0, 0, width, height, background)

    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def set_pixel(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._idx(x, y)
            self.buf[i] = color[0]
            self.buf[i + 1] = color[1]
            self.buf[i + 2] = color[2]

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        r, g, b = color
        for yy in range(y0, y1):
            i = self._idx(x0, yy)
            for xx in range(x0, x1):
                self.buf[i] = r
                self.buf[i + 1] = g
                self.buf[i + 2] = b
                i += 3

    def hline(self, x, y, w, color, thick=1):
        self.fill_rect(x, y, w, thick, color)

    def vline(self, x, y, h, color, thick=1):
        self.fill_rect(x, y, thick, h, color)

    def rect_outline(self, x, y, w, h, color, thick=1):
        self.hline(x, y, w, color, thick)
        self.hline(x, y + h - thick, w, color, thick)
        self.vline(x, y, h, color, thick)
        self.vline(x + w - thick, y, h, color, thick)

    def line(self, x0, y0, x1, y1, color, thick=1):
        """Bresenham line with square brush of `thick` pixels."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        half = thick // 2
        while True:
            self.fill_rect(x0 - half, y0 - half, thick, thick, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def fill_circle(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def circle_outline(self, cx, cy, r, color, thick=2):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.fill_rect(cx - dx, cy + dy, thick, 1, color)
            self.fill_rect(cx + dx - thick + 1, cy + dy, thick, 1, color)

    # ---------------------------------------------------------- text
    def draw_char(self, x, y, ch, scale, color):
        glyph = glyph_for(ch)
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "#":
                    self.fill_rect(x + col * scale, y + row * scale,
                                   scale, scale, color)

    def text_width(self, text, scale):
        return len(text) * 6 * scale - scale

    def draw_text(self, x, y, text, scale, color):
        cx = x
        for ch in text:
            self.draw_char(cx, y, ch, scale, color)
            cx += 6 * scale
        return cx

    def draw_text_centered(self, cx, y, text, scale, color):
        x = cx - self.text_width(text, scale) // 2
        return self.draw_text(x, y, text, scale, color)

    def wrap(self, text, scale, max_w):
        """Greedy word wrap; returns a list of lines that fit max_w."""
        words = text.split(" ")
        lines = []
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if self.text_width(trial, scale) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def draw_block(self, x, y, text, scale, color, max_w, line_h=None):
        """Draw wrapped text; returns the y just below the last line."""
        if line_h is None:
            line_h = 9 * scale
        for line in self.wrap(text, scale, max_w):
            self.draw_text(x, y, line, scale, color)
            y += line_h
        return y


def kicker_chip(canvas, x, y, label, scale=2):
    """Red chip with white label; returns the chip width."""
    pad = 8
    w = canvas.text_width(label, scale) + 2 * pad
    h = 7 * scale + 2 * pad
    canvas.fill_rect(x, y, w, h, RED)
    canvas.draw_text(x + pad, y + pad, label, scale, WHITE)
    return w


# ------------------------------------------------------- PNG encoding
def _png_chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(canvas):
    """Encode the canvas as a deterministic PNG (filter 0, zlib level 9)."""
    w, h = canvas.w, canvas.h
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)  # filter type 0: none
        raw += canvas.buf[y * stride:(y + 1) * stride]
    compressed = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"IDAT", compressed)
    png += _png_chunk(b"IEND", b"")
    return png


# ------------------------------------------------------- the front page
# All stories below are real headlines from Sunday, 22 November 2026,
# gathered from AP / Reuters / Al Jazeera / RFE/RL / The Guardian.

LEAD_KICKER = "CLIMATE"
LEAD_TAG = "COP31 - ANTALYA, TURKEY"
LEAD_HEADLINE = "CLIMATE TALKS COLLAPSE AS NATIONS FAIL TO AGREE"
LEAD_BODY = (
    "Nearly 200 countries ended the COP31 summit in Antalya, Turkey, "
    "with no agreement after two days of overtime. Talks broke down "
    "over fossil fuels and climate finance, leaving the world's "
    "climate plan in pieces."
)
LEAD_STATS = [
    ("200", "NATIONS"),
    ("2", "DAYS OVERTIME"),
    ("0", "DEAL SIGNED"),
]

TICKER = [
    "ALSO TODAY: Nvidia halts licensed Hopper chip shipments to China",
    "Mexico captures cartel boss Chapo Isidro | 34 missing in Indonesia factory fire",
]

# (kicker, headline, body) -- each body is ~115 chars, 5 wrapped lines.
ROW1 = [
    ("WAR AT SEA",
     "DRONES HIT RUSSIAN WARSHIP OFF LIBYA",
     "Sea drones struck the Russian warship Merkury at Benghazi naval "
     "base, injuring 10 crew. Kyiv confirmed the attack."),
    ("GULF TENSIONS",
     "TWO TANKERS STRUCK AS GULF CRISIS DEEPENS",
     "Two tankers were hit near the Strait of Hormuz as Iran struck a "
     "site in Bahrain, injuring two."),
    ("JUSTICE",
     "COURT: MYANMAR COMMITTED GENOCIDE",
     "The International Court of Justice ruled Myanmar committed "
     "genocide against the Rohingya."),
]

ROW2 = [
    ("UKRAINE",
     "KYIV REGION STRIKE KILLS 11",
     "Drones hit a five-storey block in Dymer, north of Kyiv, killing "
     "11 people, including a teenager."),
    ("WEST BANK",
     "WEST BANK SETTLER ATTACKS",
     "Settlers raided Palestinian villages, burning cars and homes. "
     "Eisenkot called it 'Jewish terrorism'."),
    ("EUROPE",
     "UK AND EU STRIKE POST-BREXIT DEAL",
     "Britain and the EU struck new deals on trade and travel, the "
     "biggest step to rebuild ties since Brexit."),
]

SPORT_ITEMS = [
    ("ALCARAZ WINS THE", "ATP FINALS 6-2, 7-6(7)"),
    ("LIVERPOOL 4-0 MAN UTD", "Pochettino debut rout"),
    ("VERSTAPPEN WINS", "LAS VEGAS GP BY 0.6s"),
]

FOOTER = ("Sources: AP, Reuters, Al Jazeera, RFE/RL, The Guardian | "
          "All stories from Sunday 22 November 2026")

MARGIN = 36
RIGHT = WIDTH - MARGIN  # 988


def draw_story(canvas, x, y, w, kicker, headline, body):
    """One column story: kicker chip, headline, body. Returns bottom y."""
    kicker_chip(canvas, x, y, kicker)
    hy = y + 40
    lines = canvas.wrap(headline, 3, w)
    yy = hy
    for line in lines:
        canvas.draw_text(x, yy, line, 3, INK)
        yy += 27
    yy += 6
    yy = canvas.draw_block(x, yy, body, 2, INK, w, line_h=18)
    return yy


def draw_globe(canvas, cx, cy, r):
    """A cracked planet: blue sea, green land, a red jagged crack."""
    canvas.fill_circle(cx, cy, r, OCEAN)
    for (lx, ly, lr) in ((-34, -26, 26), (21, 24, 30),
                         (36, -41, 18), (-24, 39, 16)):
        canvas.fill_circle(cx + lx, cy + ly, lr, LAND)
    canvas.circle_outline(cx, cy, r, INK, 2)
    crack = [(-64, -56), (-34, -16), (-49, 19), (-14, 54), (-24, 84)]
    for (ax, ay), (bx, by) in zip(crack, crack[1:]):
        canvas.line(cx + ax, cy + ay, cx + bx, cy + by, RED, 4)


def build_page():
    c = Canvas(WIDTH, HEIGHT, PAPER)
    c.rect_outline(16, 16, WIDTH - 32, HEIGHT - 40, INK, 2)

    # ---- masthead
    c.hline(MARGIN, 28, RIGHT - MARGIN, INK, 2)
    c.draw_text_centered(WIDTH // 2, 36, "THE WORLD IN ONE PAGE", 6, INK)
    c.draw_text(MARGIN, 90, "SUNDAY, 22 NOVEMBER 2026", 2, INK)
    right_tag = "ONE DAY. ONE PAGE. THE WORLD."
    c.draw_text(RIGHT - c.text_width(right_tag, 2), 90, right_tag, 2, INK)
    c.hline(MARGIN, 112, RIGHT - MARGIN, RED, 3)
    c.hline(MARGIN, 118, RIGHT - MARGIN, INK, 1)

    # ---- lead story
    chip_w = kicker_chip(c, MARGIN, 130, LEAD_KICKER)
    c.draw_text(MARGIN + chip_w + 12, 138, LEAD_TAG, 2, INK)
    c.draw_block(MARGIN, 170, LEAD_HEADLINE, 4, INK, 600, line_h=36)
    c.draw_block(MARGIN, 250, LEAD_BODY, 2, INK, 600, line_h=18)
    for i, (num, label) in enumerate(LEAD_STATS):
        bx = MARGIN + i * 202
        c.rect_outline(bx, 350, 196, 48, INK, 1)
        c.draw_text_centered(bx + 98, 356, num, 3, RED)
        c.draw_text_centered(bx + 98, 380, label, 2, DIMGREY)
    draw_globe(c, 824, 236, 88)
    c.draw_text_centered(824, 334, "NO DEAL IN ANTALYA", 2, INK)

    # ---- ticker band
    c.hline(MARGIN, 408, RIGHT - MARGIN, INK, 1)
    c.fill_rect(MARGIN, 420, RIGHT - MARGIN, 46, GREY)
    c.draw_text_centered(WIDTH // 2, 428, TICKER[0], 2, INK)
    c.draw_text_centered(WIDTH // 2, 446, TICKER[1], 2, INK)
    c.hline(MARGIN, 474, RIGHT - MARGIN, INK, 1)

    # ---- story rows
    col_x = [MARGIN, 348, 660]
    col_w = 292
    for x, (kicker, headline, body) in zip(col_x, ROW1):
        draw_story(c, x, 480, col_w, kicker, headline, body)
    for x in (336, 648):
        c.vline(x, 480, 218, (200, 194, 180), 1)
    c.hline(MARGIN, 710, RIGHT - MARGIN, INK, 1)
    for x, (kicker, headline, body) in zip(col_x, ROW2):
        draw_story(c, x, 724, col_w, kicker, headline, body)
    for x in (336, 648):
        c.vline(x, 724, 190, (200, 194, 180), 1)
    c.hline(MARGIN, 924, RIGHT - MARGIN, INK, 1)

    # ---- sport band
    c.fill_rect(MARGIN, 934, RIGHT - MARGIN, 58, NAVY)
    c.draw_text(52, 952, "SPORT", 3, WHITE)
    for i, (line1, line2) in enumerate(SPORT_ITEMS):
        sx = 170 + i * 285
        c.draw_text(sx, 942, line1, 2, WHITE)
        c.draw_text(sx, 960, line2, 2, WHITE)

    # ---- footer
    c.draw_text_centered(WIDTH // 2, 1006, FOOTER, 1, DIMGREY)
    return c


def main():
    canvas = build_page()
    png = encode_png(canvas)
    out_dir = "/output"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entry.png")
    with open(out_path, "wb") as f:
        f.write(png)
    print("wrote %s (%d bytes, %dx%d)" % (out_path, len(png), WIDTH, HEIGHT))


if __name__ == "__main__":
    main()
