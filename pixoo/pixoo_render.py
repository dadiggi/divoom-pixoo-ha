#!/usr/bin/env python3
"""
Pixoo 64 animated dashboard + weather renderer for Home Assistant.

Called by HA's shell_command with a base64-encoded JSON payload:
    python3 /config/pixoo/pixoo_render.py <base64-json>
Writes animated 64x64 GIFs to /config/www/pixoo/ (served as /local/pixoo/...),
which the divoom_pixoo integration shows with `page_type: gif`.

Only needs Pillow, which ships with Home Assistant.
"""
import base64, json, math, os, sys, traceback
from PIL import Image, ImageEnhance

OUT_DIR = os.environ.get("PIXOO_OUT", "/config/www/pixoo")
FRAMES = 16          # frames per loop
FRAME_MS = 125       # 16 x 125 ms = 2 s loop
NIGHT_DIM = 1.0      # set e.g. 0.6 to render darker GIFs (or use the Pixoo light entity)

FONTS = {"pico": {" ": ".../.../.../...", "!": ".#./.#./.#./...", "$": "###/##./.##/###", "%": "#.#/..#/.#./#../#.#", "'": ".#.", "(": ".#./#../#../#..", ")": ".#./..#/..#/..#", "+": ".../.#./###", ",": ".../.../.../.#.", "-": "../../##", ".": ".../.../.../...", "/": "..#/.#./.#./.#.", "0": "###/#.#/#.#/#.#/###", "1": "##./.#./.#./.#./###", "2": "###/..#/###/#../###", "3": "###/..#/.##/..#/###", "4": "#.#/#.#/###/..#/..#", "5": "###/#../###/..#/###", "6": "###/#../###/#.#/###", "7": "###/..#/..#/..#/..#", "8": "###/#.#/###/#.#/###", "9": "###/#.#/###/..#/..#", ":": ".../.#./.../.#./...", ";": ".../.#./.../.#.", "<": "..#/.#./#../.#./..#", "=": ".../###/.../###", ">": "#../.#./..#/.#.", "?": "###/..#/.##/...", "@": ".#./#.#/#.#/#../.##", "A": "###/#.#/###/#.#/#.#", "B": "###/#.#/##./#.#/###", "C": ".##/#../#../#../.##", "D": "##./#.#/#.#/#.#/###", "E": "###/#../##./#../###", "F": "###/#../##./#..", "G": ".##/#../#../#.#/###", "H": "#.#/#.#/###/#.#/#.#", "I": "###/.#./.#./.#./###", "J": "###/.#./.#./.#.", "K": "#.#/#.#/##./#.#/#.#", "L": "#../#../#../#../###", "M": "###/###/#.#/#.#/#.#", "N": "##./#.#/#.#/#.#/#.#", "O": ".##/#.#/#.#/#.#", "P": "###/#.#/###/#..", "Q": ".#./#.#/#.#/##./.##", "R": "###/#.#/##./#.#/#.#", "S": ".##/#../###/..#", "T": "###/.#./.#./.#.", "U": "#.#/#.#/#.#/#.#/.##", "V": "#.#/#.#/#.#/###", "W": "#...#/#...#/#.#.#/#.#.#/.#.#.", "X": "#.#/#.#/.#./#.#/#.#", "Y": "#.#/#.#/###/..#/###", "Z": "###/..#/.#./#../###", "[": "##./#../#../#..", "]": ".##/..#/..#/..#/.##", "^": ".#./#.#", "_": ".../.../.../.../###", "a": ".../.##/#.#/###/#.#", "b": ".../##./##./#.#/###", "c": ".../.##/#../#../.##", "d": ".../##./#.#/#.#", "e": ".../###/##./#../.##", "f": ".../###/##./#..", "g": ".../.##/#../#.#/###", "h": ".../#.#/#.#/###/#.#", "i": ".../###/.#./.#./###", "j": ".../###/.#./.#.", "k": ".../#.#/##./#.#/#.#", "l": ".../#../#../#../.##", "m": ".../###/###/#.#/#.#", "n": ".../##./#.#/#.#/#.#", "o": ".../.##/#.#/#.#", "p": ".../.##/#.#/###", "q": ".../.#./#.#/##./.##", "r": ".../##./#.#/##./#.#", "s": ".../.##/#../..#", "t": ".../###/.#./.#.", "u": ".../#.#/#.#/#.#/.##", "v": ".../#.#/#.#/###", "w": ".../#.#/#.#/###/###", "x": ".../#.#/.#./.#./#.#", "y": ".../#.#/###/..#", "z": ".../###/..#/#../###", "{": ".##/.#./##./.#./.##", "|": ".#./.#./.#./.#.", "}": "##./.#./.##/.#.", "~": ".../..#/###", "°": "##/##/../../.."}, "gicko": {"0": ".####./##..##/##..##/##..##/##..##/.####.", "1": ".##./###./.##./.##./.##./####", "2": ".####./#..###/...###/.####./###.../######", "3": "#####./...###/#####./...###/...###/#####.", "4": ".####./##.##./#..##./#..##./######/...##.", "5": "#####./#...../#####./...###/#..###/.####.", "6": ".####./##..../#####./##..##/##..##/.####.", "7": "######/....##/...##./..##../.###../.###..", "8": ".####./##..##/.####./##..##/##..##/.####.", "9": ".####./#..###/#..###/.#####/...###/.####.", ":": "../##/##/../##/##", "-": ".../.../.../###/...", ".": "../../../../##/##", " ": "../../../../../.."}, "big": {"0": ".####./##..##/##..##/##..##/##..##/##..##/##..##/##..##/##..##/##..##/.####.", "1": "..##../.###../#.##../..##../..##../..##../..##../..##../..##../..##../######", "2": ".####./#..###/...###/...###/...###/.####./###.../###.../###.../###.../######", "3": "#####./...###/...###/...###/...###/#####./...###/...###/...###/...###/#####.", "4": ".####./##.##./#..##./#..##./#..##./#..##./#..##./######/...##./...##./...##.", "5": "#####./#...../#...../#...../#...../#####./...###/...###/...###/#..###/.####.", "6": ".####./##..../##..../##..../##..../#####./##..##/##..##/##..##/##..##/.####.", "7": "######/....##/....##/...##./...##./..##../..##../.###../.###../.###../.###..", "8": ".####./#..###/#..###/#..###/#..###/.####./#..###/#..###/#..###/#..###/.####.", "9": ".####./######/##..##/##..##/##..##/######/.#####/....##/....##/....##/.####.", ".": "../../../../../../../##/##/../..", " ": "", "-": "..../..../..../..../..../####/####/..../..../..../....", "°": "###/#.#/###/.../.../.../.../.../.../.../..."}}

# ----------------------------------------------------------------------------
# Palette & colour helpers
# ----------------------------------------------------------------------------
# Theme-dependent colours (overwritten by apply_theme)
BG = (2, 3, 7)
TILE = (20, 25, 46)
ZEBRA = (38, 43, 62)
BRUSH = (30, 35, 52)
BEV_TOP = (62, 74, 120)
BEV_LEFT = (44, 53, 90)
BEV_DARK = (8, 10, 20)
LABEL = (150, 175, 230)
LABEL2 = (150, 158, 190)
TIME_C = (120, 200, 255)
WEEKEND = (255, 150, 120)
TILE_STYLE = "plain"
DECOR = None
THEME_NAME = "neon"

THEMES = {
    "neon": dict(bg=(2, 3, 7), tile=(20, 25, 46), bev_top=(62, 74, 120), bev_left=(44, 53, 90),
                 bev_dark=(8, 10, 20), label=(150, 175, 230), label2=(150, 158, 190),
                 time=(120, 200, 255), weekend=(255, 150, 120), style="plain", decor=None),
    "retro_platformer": dict(bg=(40, 110, 255), tile=(26, 12, 6), bev_top=(235, 120, 50),
                 bev_left=(190, 85, 30), bev_dark=(70, 25, 5), label=(255, 255, 255),
                 label2=(255, 220, 120), time=(255, 210, 60), weekend=(255, 120, 90),
                 style="brick", decor="coins"),
    "crimson_desert": dict(bg=(10, 1, 1), tile=(42, 7, 9), bev_top=(215, 150, 60), bev_left=(150, 95, 35),
                 bev_dark=(14, 2, 2), label=(240, 190, 110), label2=(200, 140, 90),
                 time=(255, 170, 70), weekend=(255, 90, 70), style="plain", decor="embers"),
    "christmas": dict(bg=(0, 4, 2), tile=(6, 34, 18), bev_top=(235, 245, 255), bev_left=(25, 90, 45),
                 bev_dark=(0, 10, 5), label=(255, 255, 255), label2=(255, 120, 120),
                 time=(255, 90, 90), weekend=(255, 215, 80), style="snow", decor="christmas"),
    "halloween": dict(bg=(4, 0, 8), tile=(30, 10, 42), bev_top=(255, 120, 0), bev_left=(170, 70, 0),
                 bev_dark=(6, 0, 10), label=(255, 160, 40), label2=(190, 120, 255),
                 time=(255, 140, 20), weekend=(190, 120, 255), style="plain", decor="bats"),
    "steel": dict(bg=(4, 5, 7), tile=(34, 38, 45), bev_top=(190, 200, 215), bev_left=(125, 134, 150),
                 bev_dark=(10, 11, 14), label=(200, 210, 225), label2=(150, 165, 185),
                 time=(160, 205, 255), weekend=(255, 175, 90), style="steel", decor="steel"),
    "synthwave": dict(bg=(8, 0, 18), tile=(28, 6, 48), bev_top=(255, 50, 200), bev_left=(0, 200, 255),
                 bev_dark=(10, 0, 25), label=(90, 240, 255), label2=(255, 120, 230),
                 time=(255, 80, 220), weekend=(255, 220, 90), style="plain", decor="synth"),
}

VIVID = {  # (gamma, saturation) presets, selectable from HA
    "vivid": (1.8, 1.3), "extra vivid": (2.2, 1.5), "soft": (1.4, 1.15), "off": (1.0, 1.0),
}


def apply_theme(name, today=""):
    global BG, TILE, ZEBRA, BEV_TOP, BEV_LEFT, BEV_DARK, LABEL, LABEL2, TIME_C, WEEKEND
    global TILE_STYLE, DECOR, THEME_NAME, BRUSH
    name = (name or "auto").lower().replace(" ", "_")
    if name == "auto":
        md = str(today)[5:10]          # "MM-DD"
        name = ("christmas" if "12-01" <= md <= "12-31" or md <= "01-06"
                else "halloween" if "10-24" <= md <= "10-31" else "neon")
    t = THEMES.get(name, THEMES["neon"])
    THEME_NAME = name if name in THEMES else "neon"
    BG, TILE, BEV_TOP, BEV_LEFT, BEV_DARK = t["bg"], t["tile"], t["bev_top"], t["bev_left"], t["bev_dark"]
    LABEL, LABEL2, TIME_C, WEEKEND = t["label"], t["label2"], t["time"], t["weekend"]
    TILE_STYLE, DECOR = t["style"], t["decor"]
    ZEBRA = shade(TILE, 0.08)
    BRUSH = shade(TILE, 0.12)
SHADOW = (3, 4, 9)
GREY = (115, 122, 150)
DIM = (80, 85, 110)

GREEN = (70, 255, 110)
CYAN = (30, 225, 255)
BLUE = (70, 150, 255)
AMBER = (255, 200, 30)
RED = (255, 70, 55)
WATER = (60, 170, 255)
HEAT = (255, 140, 30)


def shade(c, f):
    """f > 0 mixes toward white, f < 0 darkens."""
    if f >= 0:
        return tuple(int(v + (255 - v) * f) for v in c)
    return tuple(int(v * (1 + f)) for v in c)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def num(v):
    try:
        if v is None or str(v).lower() in ("unknown", "unavailable", "none", ""):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def temp_color(v, lo, hi):
    if v < lo[0]: return BLUE
    if v < lo[1]: return CYAN
    if v <= hi[0]: return GREEN
    if v <= hi[1]: return AMBER
    return RED


IN_SCALE = ((18, 20), (24, 26))
OUT_SCALE = ((0, 10), (25, 30))

# ----------------------------------------------------------------------------
# Canvas
# ----------------------------------------------------------------------------
_GLYPHS = {}
# The integration's pico_8 table has ~36 glyphs truncated to 4 rows (O, F, S, P, T, ...).
# Repaired 3x5 versions:
PICO_FIX = {
    "O": ".##/#.#/#.#/#.#/##.", "F": "###/#../##./#../#..", "S": ".##/#../###/..#/##.",
    "P": "###/#.#/###/#../#..", "T": "###/.#./.#./.#./.#.", "V": "#.#/#.#/#.#/#.#/.#.",
    "J": "###/.#./.#./.#./##.", "W": "#...#/#...#/#.#.#/#.#.#/.#.#.",
    ".": "././././#", "-": ".../.../###/.../...", "+": ".../.#./###/.#./...",
    "/": "..#/..#/.#./#../#..", "?": "###/..#/.##/.../.#.", "!": ".#./.#./.#./.../.#.",
    " ": ".../.../.../.../...", "'": ".#./.#./.../.../...", "(": ".#./#../#../#../.#.",
    ")": ".#./..#/..#/..#/.#.", ",": ".../.../.../.#./#..", ";": ".../.#./.../.#./#..",
    "=": ".../###/.../###/...", ">": "#../.#./..#/.#./#..", "<": "..#/.#./#../.#./..#",
    "D": "##./#.#/#.#/#.#/##.",   # rounded so "2D" is not read as "20"
    "[": "##./#../#../#../##.", "]": ".##/..#/..#/..#/.##", "|": ".#./.#./.#./.#./.#.",
}
FONTS["pico"].update(PICO_FIX)
# Open-topped 4s so they can't be mistaken for 9s; small 9 gets a closed bottom.
FONTS["big"]["4"] = "...##./..###./.#.##./#..##./#..##./#..##./######/...##./...##./...##./...##."
FONTS["gicko"]["4"] = "...##./..###./.#.##./#..##./######/...##."
FONTS["pico"]["9"] = "###/#.#/###/..#/###"
# Croatian letters: base glyph + accent pixels drawn ABOVE the glyph (dx, dy with dy < 0)
ACCENTS = {
    "Č": ("C", [(0, -2), (2, -2), (1, -1)]), "Ć": ("C", [(2, -2), (1, -1)]),
    "Š": ("S", [(0, -2), (2, -2), (1, -1)]), "Ž": ("Z", [(0, -2), (2, -2), (1, -1)]),
    "Đ": ("D", []),
}
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    FONTS["pico"][_c.lower()] = FONTS["pico"][_c]
for _fname, _font in FONTS.items():
    _GLYPHS[_fname] = {}
    for _ch, _rows in _font.items():
        _r = _rows.split("/")
        _GLYPHS[_fname][_ch] = (len(_r[0]), len(_r), [[c == "#" for c in row] for row in _r])


class Canvas:
    def __init__(self):
        self.img = Image.new("RGB", (64, 64), BG)
        self.p = self.img.load()
        self.tiles = []
        self.umbrella = False

    def is_bg(self, x, y):
        """True where nothing but background/tile fill is drawn (used for 'behind content' decor)."""
        return 0 <= x < 64 and 0 <= y < 64 and self.p[x, y] in (BG, TILE, ZEBRA, BRUSH)

    def behind(self, x, y, c):
        if self.is_bg(int(x), int(y)):
            self.px(x, y, c)

    def px(self, x, y, c):
        if 0 <= x < 64 and 0 <= y < 64:
            self.p[int(x), int(y)] = tuple(int(max(0, min(255, v))) for v in c[:3])

    def get(self, x, y):
        return self.p[x, y] if 0 <= x < 64 and 0 <= y < 64 else BG

    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.px(xx, yy, c)

    def tile(self, x, y, w, h):
        self.tiles.append((x, y, w, h))
        self.rect(x, y, w, h, TILE)
        self.rect(x, y, w, 1, BEV_TOP)
        self.rect(x, y, 1, h, BEV_LEFT)
        self.rect(x, y + h - 1, w, 1, BEV_DARK)
        self.rect(x + w - 1, y + 1, 1, h - 1, BEV_DARK)
        if TILE_STYLE == "brick":       # mortar joints in the bevels
            for i in range(x, x + w):
                if (i - x) % 4 == 3: self.px(i, y, BEV_DARK)
            for j in range(y, y + h):
                if (j - y) % 3 == 2: self.px(x, j, BEV_DARK)
        elif TILE_STYLE == "steel":     # brushed-metal streaks inside the plate
            for j in range(y + 1, y + h - 1):
                hsh = (j * 131 + x * 7) % 97
                sx = x + 1 + hsh % max(1, w - 2)
                for i in range(sx, min(x + w - 1, sx + 6 + hsh % 11)):
                    self.px(i, j, BRUSH)
        elif TILE_STYLE == "snow":      # snow caps dripping over the top edge
            for i in range(x + 1, x + w - 1):
                if (i * 37 + y * 11) % 7 in (0, 3):
                    self.px(i, y + 1, (200, 215, 235))

    def sprite(self, x, y, rows, pal, shadow=True):
        if shadow:
            for j, r in enumerate(rows):
                for i, ch in enumerate(r):
                    if ch != ".":
                        self.px(x + i + 1, y + j + 1, SHADOW)
        for j, r in enumerate(rows):
            for i, ch in enumerate(r):
                if ch != ".":
                    self.px(x + i, y + j, pal[ch])

    # --- text ---
    @staticmethod
    def glyph(font, ch):
        """Glyph lookup that never fails: falls back to upper-case, then the pico font, then blank."""
        ch = str(ch)
        if ch.upper() in ACCENTS:
            ch = ACCENTS[ch.upper()][0]
        g = _GLYPHS[font]
        got = g.get(ch) or g.get(str(ch).upper())
        if got is None and font != "pico":
            p = _GLYPHS["pico"].get(ch) or _GLYPHS["pico"].get(str(ch).upper())
            if p is not None:
                return p
        return got or (3, 5, [[False] * 3 for _ in range(5)])

    def text_width(self, s, font="pico"):
        w = sum(self.glyph(font, ch)[0] + 1 for ch in str(s))
        return max(0, w - 1)

    def text(self, x, y, s, color, font="pico", align="left", shadow=True,
             grad=None, glint=None):
        """grad: list of per-row shade factors. glint: diagonal highlight position."""
        w = self.text_width(s, font)
        if align == "center": x -= w // 2
        elif align == "right": x -= w
        s = str(s)
        layers = ([(1, True)] if shadow else []) + [(0, False)]
        for off, is_shadow in layers:
            cx = x
            for ch in s:
                gw, gh, m = self.glyph(font, ch)
                for (ax, ay) in ACCENTS.get(ch.upper(), (None, []))[1]:
                    if is_shadow:
                        self.px(cx + ax + 1, y + ay + 1, SHADOW)
                    else:
                        self.px(cx + ax, y + ay, color)
                for j in range(gh):
                    for i in range(gw):
                        if m[j][i]:
                            if is_shadow:
                                self.px(cx + i + 1, y + j + 1, SHADOW)
                            else:
                                c = color
                                if grad: c = shade(color, grad[min(j, len(grad) - 1)])
                                if glint is not None:
                                    d = abs((cx + i - x) - j * 0.6 - glint)
                                    if d < 2.0: c = shade(c, 0.75 - d * 0.3)
                                self.px(cx + i, y + j, c)
                cx += gw + 1
        return w


GRAD_BIG = [0.65, 0.45, 0.25, 0.1, 0, 0, -0.1, -0.2, -0.3, -0.4, -0.5]
GRAD_MID = [0.6, 0.3, 0.05, -0.1, -0.2, -0.32]
GRAD_SMALL = [0.45, 0.2, 0, -0.15, -0.3]


def pulse(f, lo=0.0, hi=1.0, period=FRAMES, phase=0.0):
    return lo + (hi - lo) * (0.5 + 0.5 * math.sin(2 * math.pi * (f / period) + phase))


def glint_pos(f, width):
    """Glint sweeps across during the first half of the loop, then rests off-text."""
    half = FRAMES // 2
    if f >= half:
        return None
    return -4 + (width + 8) * f / (half - 1)


# ----------------------------------------------------------------------------
# Small sprites
# ----------------------------------------------------------------------------
HOUSE = (["...h...", "..hRr..", ".hRRRr.", "hRRRRRr", ".WWWWS.", ".WWDWS.", ".WWDWS."],
         {"h": (255, 190, 120), "R": (255, 110, 50), "r": (190, 60, 30),
          "W": (255, 225, 175), "S": (215, 160, 110), "D": (110, 55, 25)})
TREE = (["..LGG..", ".LLGGg.", "LLGGGGg", "LGGGGgg", ".GGGgg.", "...B...", "...b..."],
        {"L": (150, 255, 160), "G": (50, 210, 100), "g": (25, 140, 70),
         "B": (180, 120, 70), "b": (130, 80, 45)})
DROP = (["..C..", ".WCC.", "CWCCc", "CCCcc", ".ccc."],
        {"C": (70, 180, 255), "W": (230, 245, 255), "c": (30, 110, 220)})
UP = (["..#..", ".###.", "#####"], None)
DOWN = (["#####", ".###.", "..#.."], None)


def tri(cv, x, y, rows, c):
    cv.sprite(x, y, rows, {"#": c})


# ----------------------------------------------------------------------------
# Appliance icons (13x13, animated)
# ----------------------------------------------------------------------------
def appliance(cv, x, y, kind, state, f):
    on = state == "run"
    if on:
        hi, body, sh, dk = (255, 255, 255), (220, 226, 240), (150, 158, 185), (90, 96, 120)
    else:
        hi, body, sh, dk = (135, 142, 165), (100, 106, 128), (70, 75, 95), (48, 52, 68)
    # shadow
    for j in range(13):
        for i in range(13):
            if not (i in (0, 12) and j in (0, 12)):
                cv.px(x + i + 1, y + j + 1, SHADOW)
    for j in range(13):
        for i in range(13):
            if i in (0, 12) and j in (0, 12):
                continue
            c = body
            if j == 0 or i == 0: c = hi
            if i == 12 or j == 12: c = sh
            cv.px(x + i, y + j, c)
    for i in range(1, 12): cv.px(x + i, y + 3, sh)
    if kind == "washer":
        for (i, j) in [(2, 1), (3, 1), (2, 2), (3, 2)]: cv.px(x + i, y + j, sh)
        for (i, j) in [(9, 1), (10, 1), (9, 2), (10, 2)]: cv.px(x + i, y + j, dk)
        led = (60, 255, 120)
    else:
        for i in (2, 3, 4): cv.px(x + i, y + 1, dk); cv.px(x + i, y + 2, sh)
        cv.px(x + 10, y + 1, dk); cv.px(x + 10, y + 2, dk)
        led = (255, 170, 40)
    blink = on and (f // 4) % 2 == 0
    cv.px(x + 7, y + 1, led if blink else ((60, 62, 76) if not on else shade(led, -0.6)))
    if state == "done" and (f // 4) % 2 == 0:
        cv.px(x + 7, y + 1, GREEN)
    cx, cy = 6, 7.5
    ang = 2 * math.pi * f / FRAMES
    for j in range(4, 12):
        for i in range(13):
            d = math.hypot(i - cx, j - cy)
            if d > 4.3:
                continue
            if d > 3.0:
                c = (60, 66, 90) if (i + j) > (cx + cy) else (125, 133, 160)
                if not on: c = (42, 45, 60)
            elif not on:
                c = (25, 28, 40)
                if kind == "washer" and j == 10: c = (60, 66, 88)
                if kind == "dryer" and 1.2 < d < 2.2: c = (55, 60, 80)
            elif kind == "washer":
                wave = 7.5 + 0.8 * math.sin(i * 1.3 + ang * 2)
                c = (40, 140, 255) if j >= wave else (20, 55, 130)
                if abs(j - wave) < 0.6: c = (130, 215, 255)
                if j >= 10: c = (20, 90, 210)
            else:
                swirl = (math.atan2(j - cy, i - cx) - ang * 2) % (2 * math.pi)
                c = (255, 150, 40) if swirl < math.pi else (230, 80, 20)
                if d < 1.2: c = (255, 230, 120)
            cv.px(x + i, y + j, c)
    if on:
        # tumbling laundry: two items orbiting the drum centre
        for k, col in enumerate([(255, 80, 120), (255, 240, 120)] if kind == "washer"
                                else [(255, 255, 255), (140, 220, 255)]):
            a = ang + k * math.pi
            cv.px(x + round(cx + 2 * math.cos(a)), y + round(cy + 2 * math.sin(a)), col)
        cv.px(x + 4, y + 5, (255, 255, 255))   # glass glint
        if kind == "washer":
            by = 10 - (f % 6)
            if 5 <= by <= 10: cv.px(x + 8, y + by, (210, 240, 255))


def printer(cv, x, y, k, pct, f):
    dim = k in ("idle", "off")
    pal = {"L": (225, 230, 245), "H": (255, 255, 255), "F": (165, 172, 195), "S": (100, 106, 130),
           "B": (80, 85, 105)}
    if dim:
        pal = {"L": (125, 130, 152), "H": (130, 136, 158), "F": (95, 100, 122), "S": (60, 64, 82),
               "B": (55, 58, 74)}
    win = {"run": (25, 120, 70), "pause": (120, 90, 0), "prep": (10, 90, 110), "done": (25, 120, 70),
           "err": (150, 25, 25), "idle": (34, 38, 56), "off": (24, 27, 40)}[k]
    rows = [".LLLLLLLLLLL.", "LHHHHHHHHHHHF", "LFFFFFFFFFFFS", "LF.........FS", "LF.........FS",
            "LF.........FS", "LF.........FS", "LF.........FS", "LF.........FS", "LF.........FS",
            "LFBBBBBBBBBFS", "LSSSSSSSSSSSS", ".SS.......SS."]
    cv.sprite(x, y, rows, pal)
    cv.rect(x + 2, y + 3, 9, 7, win)
    # printed object, height follows progress
    obj = (255, 255, 255) if not dim else (85, 90, 110)
    h = 3 if k == "done" else max(1, round(3 * (pct or 0) / 100)) if k in ("run", "pause") else 2
    for r in range(h):
        cv.rect(x + 5, y + 9 - r, 4 if r == 0 else 3, 1, obj if r < h - 1 or k != "run" else shade(obj, -0.2))
    # toolhead: sweeps while printing
    if k == "run":
        hx = 3 + round(3 + 3 * math.sin(2 * math.pi * f / FRAMES))
    else:
        hx = 6
    head = (240, 240, 250) if not dim else (115, 120, 140)
    cv.rect(x + 2, y + 4, 9, 1, shade(win, 0.25))           # gantry rail
    cv.rect(x + hx - 1, y + 4, 3, 1, head)
    nozzle = (255, 230, 120) if k == "run" and f % 2 == 0 else head
    cv.px(x + hx, y + 5, nozzle)
    if k == "err" and (f // 4) % 2 == 0:
        cv.rect(x + 2, y + 3, 9, 1, (255, 90, 70))


# ----------------------------------------------------------------------------
# AQI gauge
# ----------------------------------------------------------------------------
AQI_STOPS = [(0, (0, 225, 90)), (50, (255, 225, 0)), (100, (255, 130, 0)),
             (150, (255, 40, 40)), (200, (190, 70, 255)), (300, (150, 20, 100))]


def aqi_color(a):
    a = max(0.0, min(300.0, float(a)))
    for (a0, c0), (a1, c1) in zip(AQI_STOPS, AQI_STOPS[1:]):
        if a <= a1:
            return mix(c0, c1, (a - a0) / (a1 - a0))
    return AQI_STOPS[-1][1]


def aqi_gauge(cv, a, f):
    """60-px pill gauge: lit up to the current value (with a travelling shine), the rest of the
    scale stays visible in its own colours but dimmed and dotted, plus a pointer under the value."""
    X0, W, Y = 2, 60, 34
    mx = None if a is None else X0 + int(min(max(a, 0), 299) * W / 300)
    shine = None
    if mx is not None and mx > X0:
        shine = X0 + (f * (mx - X0 + 8) // FRAMES) - 4
    for i in range(W):
        x = X0 + i
        c = aqi_color(i * 300 / W)
        lit = mx is not None and x <= mx
        if lit:
            top, mid, bot = mix(c, (255, 255, 255), 0.45), c, shade(c, -0.45)
            if shine is not None and abs(x - shine) <= 1:
                top, mid = (255, 255, 255), mix(c, (255, 255, 255), 0.5)
        else:
            k = -0.5 if i % 2 == 0 else -0.62           # dotted texture = "not reached"
            top, mid, bot = shade(c, k - 0.05), shade(c, k), shade(c, -0.8)
        cv.px(x, Y, top); cv.px(x, Y + 1, mid); cv.px(x, Y + 2, bot)
    for (x, y) in [(X0, Y), (X0, Y + 2), (X0 + W - 1, Y), (X0 + W - 1, Y + 2)]:
        cv.px(x, y, TILE)                                 # rounded pill ends
    if mx is not None:
        glow = mix(aqi_color(a), (255, 255, 255), pulse(f, 0.3, 0.9))
        cv.rect(mx, Y - 1, 1, 4, (255, 255, 255))
        cv.px(mx - 1, Y - 1, SHADOW); cv.px(mx + 1, Y - 1, SHADOW)
        cv.rect(mx - 1, Y + 3, 3, 1, glow)               # pointer under the gauge
        cv.px(mx, Y + 3, (255, 255, 255))


# ----------------------------------------------------------------------------
# Umbrella forecast (rest of today)
# ----------------------------------------------------------------------------
RAIN_PROB = 40          # % chance per hour that counts as "rain expected"
RAIN_MM = 0.2           # or this much precipitation in an hour
RAINY = {"rainy", "pouring", "lightning-rainy", "snowy-rainy", "hail"}


def rain_outlook(d):
    """None = no hourly data; otherwise (rain_expected, max_probability)."""
    if not d.get("hourly_ok"):
        return None
    rain, best = False, 0
    hourly = d.get("hourly")
    for h in (hourly if isinstance(hourly, list) else []):
        if not isinstance(h, dict):
            continue
        p, mm, c = num(h.get("p")), num(h.get("mm")), str(h.get("c") or "").lower()
        best = max(best, p or 0)
        if (p is not None and p >= RAIN_PROB) or (mm is not None and mm >= RAIN_MM) or c in RAINY:
            rain = True
    return rain, best


UMBRELLA_OPEN = ["....lll....", "..llalall..", ".aaabababa.", "dadddhdddad", "d.d..h..d.d",
                 ".....h.....", "...hhh....."]
UMBRELLA_SHUT = ["..a..", ".aba.", ".aba.", ".aba.", "..a..", "..h..", ".hh.."]


def draw_umbrella(cv, d, f):
    """In the free space of the AQI tile: open umbrella with dripping rain when rain is expected
    later today, a closed umbrella next to a twinkling sun when it isn't."""
    out = rain_outlook(d)
    if out is None:
        return False
    rain, best = out
    x, y = 36, 26
    if rain:
        sway = round(math.sin(2 * math.pi * f / FRAMES))
        pal = {"l": (150, 205, 255), "a": (60, 150, 255), "b": (110, 185, 255), "d": (30, 95, 210),
               "h": (210, 210, 225)}
        for j, r in enumerate(UMBRELLA_OPEN):
            dx = sway if j < 4 else 0
            for i, ch in enumerate(r):
                if ch != ".":
                    cv.px(x + i + dx + 1, y + j + 1, SHADOW)
            for i, ch in enumerate(r):
                if ch != ".":
                    cv.px(x + i + dx, y + j, pal[ch])
        drops = 3 if best >= 70 else 2
        for n, (dxp, ph) in enumerate([(-1, 0), (11, 5), (5, 10)][:drops]):
            yy = y + 3 + ((f + ph) % 8) // 2 if dxp != 5 else y - 1 + ((f + ph) % 4)
            if dxp == 5:     # drop landing on the canopy, splashing
                if (f + ph) % 4 == 3:
                    cv.px(x + 4 + sway, y, (200, 235, 255)); cv.px(x + 6 + sway, y, (200, 235, 255))
                continue
            if yy <= y + 6:
                cv.px(x + dxp + sway, yy, (120, 200, 255))
    else:
        pal = {"a": (110, 120, 145), "b": (150, 160, 185), "h": (150, 150, 165)}
        cv.sprite(x, y, UMBRELLA_SHUT, pal)
        cx, cy = x + 9, y + 3                       # little sun: "no umbrella needed"
        cv.rect(cx - 1, cy - 1, 3, 3, (255, 200, 40)); cv.px(cx, cy, (255, 245, 170))
        on = (f // 4) % 2 == 0
        for (dx, dy) in ([(0, -3), (0, 3), (-3, 0), (3, 0)] if on else [(-2, -2), (2, -2), (-2, 2), (2, 2)]):
            cv.px(cx + dx, cy + dy, (255, 210, 60))
    cv.umbrella = True
    return True


# ----------------------------------------------------------------------------
# Bottom row helpers
# ----------------------------------------------------------------------------
CLOCK = ([".###.", "#.#.#", "#.###", "#...#", ".###."], None)


def age_text(sec):
    sec = num(sec)
    if sec is None or sec < 0:
        return None
    if sec < 3600: return "%dM" % max(1, sec // 60)
    if sec < 172800: return "%dH" % (sec // 3600)
    return "%dD" % min(99, sec // 86400)


def _appliance_states(d):
    wm = APPLIANCE_STATES.get(d.get("wm"), ("--", "off"))[1]
    td = APPLIANCE_STATES.get(d.get("td"), ("--", "off"))[1]
    pr = PRINTER_MAP.get(str(d.get("pr", "")).lower(), "off")
    return [(wm, "wm"), (td, "td"), (pr, "pr")]


def idle_label(cv, cx, y, k, age):
    """Idle/off tiles show how long ago the machine was last active (clock + '2D')."""
    a = age_text(age)
    c = GREY if k == "idle" else DIM
    if not a:
        cv.text(cx, y, "IDLE" if k == "idle" else "OFF", c, align="center")
        return
    w = 6 + cv.text_width(a)
    x = cx - w // 2
    tri(cv, x, y, CLOCK[0], c)
    cv.text(x + 6, y, a, c)


def appliance_row(cv, d, f, states_):
    for t in [(0, 41, 20, 23), (22, 41, 20, 23), (44, 41, 20, 23)]:
        cv.tile(*t)
    for x, s, kind, runc, agek in [(0, d.get("wm"), "washer", WATER, "wm_age"), (22, d.get("td"), "dryer", HEAT, "td_age")]:
        label, k = APPLIANCE_STATES.get(s, ("--", "off"))
        c = runc if k == "run" else STATE_COLOR.get(k, DIM)
        if k == "run": status_strip(cv, x, 20, c, "run", f)
        elif k in ("done", "pause"): status_strip(cv, x, 20, c, "pulse", f)
        elif k == "err": status_strip(cv, x, 20, c, "blink", f)
        appliance(cv, x + 3, 43, kind, k, f)
        if k in ("idle", "off"):
            idle_label(cv, x + 10, 57, k, d.get(agek))
            continue
        tc = c
        if k == "err" and (f // 4) % 2: tc = shade(c, -0.55)
        if k == "done": tc = shade(c, pulse(f, -0.25, 0.15))
        cv.text(x + 10, 57, label, tc, align="center", grad=GRAD_SMALL)

    k = PRINTER_MAP.get(str(d.get("pr", "")).lower(), "off")
    pct = num(d.get("pr_pct"))
    mins = int(num(d.get("pr_left")) or 0)
    left = ("%dh%02d" % (mins // 60, mins % 60)) if mins >= 60 else ("%dm" % mins)
    c = GREEN if k == "run" else STATE_COLOR.get(k, DIM)
    if k in ("run", "pause") and pct is not None:
        status_strip(cv, 44, 20, c, "progress", f, fill=round(max(0, min(100, pct)) * 20 / 100))
    elif k == "run": status_strip(cv, 44, 20, c, "run", f)
    elif k == "done": status_strip(cv, 44, 20, c, "pulse", f)
    elif k == "err": status_strip(cv, 44, 20, c, "blink", f)
    printer(cv, 47, 43, k, pct, f)
    if k in ("idle", "off"):
        idle_label(cv, 54, 57, k, d.get("pr_age"))
        return
    label = {"run": left, "pause": "PAUS", "prep": "PREP", "done": "DONE", "err": "ERR"}[k]
    tc = c
    if k == "err" and (f // 4) % 2: tc = shade(c, -0.55)
    if k == "prep": tc = shade(c, pulse(f, -0.35, 0.1))
    cv.text(54, 57, label, tc, align="center", grad=GRAD_SMALL)


def _scene(cv, x0, w, rising, f, t_str):
    """Mini landscape: sky gradient, sun moving across the horizon, shimmering water, time below."""
    y0, hz = 43, 51                                  # sky rows 43..50, water 51..54
    if rising:
        sky_top, sky_hz = (25, 35, 110), (255, 150, 60)
        sun_c, sun_edge, water = (255, 230, 120), (255, 140, 30), (20, 40, 110)
        sy = 54 - 7 * f / (FRAMES - 1)               # 54 -> 47 (rising)
    else:
        sky_top, sky_hz = (45, 10, 70), (255, 70, 40)
        sun_c, sun_edge, water = (255, 170, 70), (230, 50, 30), (40, 15, 60)
        sy = 47 + 7 * f / (FRAMES - 1)               # 47 -> 54 (setting)
    for j in range(y0, hz):
        cv.rect(x0, j, w, 1, mix(sky_top, sky_hz, ((j - y0) / (hz - 1 - y0)) ** 1.6))
    cx = x0 + w // 2
    # glow on the horizon
    for i in range(w):
        d = abs(x0 + i - cx)
        if d < 9:
            cv.px(x0 + i, hz - 1, mix(cv.get(x0 + i, hz - 1), (255, 220, 140), 0.6 * (1 - d / 9)))
    r = 3.2
    for j in range(int(sy - r) - 1, int(sy + r) + 2):
        for i in range(cx - 4, cx + 5):
            dd = math.hypot(i + 0.5 - (cx + 0.5), j + 0.5 - sy)
            if dd <= r and y0 <= j < hz:
                cv.px(i, j, mix(sun_c, sun_edge, dd / r))
    if sy < hz - 2:                                 # short rays once the sun is up
        for n in range(5):
            a = math.pi + n * math.pi / 4
            L = r + 1.5 + pulse(f, 0, 1.2, phase=n)
            px_, py_ = cx + 0.5 + math.cos(a) * L, sy + math.sin(a) * L
            if y0 <= py_ < hz - 1:
                cv.px(int(px_), int(py_), shade(sun_c, -0.1))
    # water with shimmering sun reflection
    for j in range(hz, hz + 4):
        cv.rect(x0, j, w, 1, shade(water, -0.15 * (j - hz)))
        spread = 5 - (j - hz)
        for i in range(-spread, spread + 1):
            if (i + j + f // 2) % 3 == 0:
                cv.px(cx + i, j, mix(water, sun_c, 0.75 - 0.15 * (j - hz)))
    cv.rect(x0, hz, w, 1, mix(water, sky_hz, 0.6))    # bright horizon line
    if rising:                                      # a bird crossing the dawn sky
        bx = x0 + (f * (w + 4) // FRAMES) - 2
        by = 45 + (1 if (f // 2) % 2 else 0)
        for (dx, dy) in ([(0, 0), (1, 1), (2, 0)] if (f // 2) % 2 else [(0, 1), (1, 0), (2, 1)]):
            if x0 <= bx + dx < x0 + w:
                cv.px(bx + dx, by + dy, (40, 30, 60))
    else:                                           # first stars appearing at dusk
        for (sx, sy2, ph) in [(x0 + 3, 44, 0), (x0 + w - 4, 45, 2), (x0 + 9, 46, 4)]:
            cv.px(sx, sy2, shade((255, 240, 200), pulse(f, -0.8, 0, phase=ph)))
    tc = AMBER if rising else (255, 110, 60)
    cv.text(cx, 56, t_str, tc, "gicko", "center", grad=GRAD_MID)


def card_sun(cv, d, f):
    cv.tile(0, 41, 64, 23)
    _scene(cv, 2, 28, True, f, str(d.get("sunrise") or "--:--"))
    _scene(cv, 34, 28, False, f, str(d.get("sunset") or "--:--"))
    cv.rect(31, 43, 2, 18, BEV_DARK)


# ----------------------------------------------------------------------------
# Theme decorations (drawn "behind" content: only on empty tile/background pixels)
# ----------------------------------------------------------------------------
BAT_UP = ["#.....#", "##.#.##", ".#####.", "...#..."]
BAT_DOWN = ["...#...", ".#####.", "##.#.##", "#.....#"]


def _field(f, n, seed, speed=1):
    """Seamless looping particle field: yields (x, y, phase) for n particles per 16-px band."""
    for band in range(4):
        for i in range(n):
            h = (i * 73 + band * 41 + seed * 17) % 997
            x = (h * 7) % 64
            y = (h + f * speed) % 16 + band * 16
            yield x, y, h


def decorate(cv, f, page):
    if DECOR == "christmas":
        for x, y, h in _field(f, 3, 1):
            wob = round(math.sin(2 * math.pi * f / FRAMES + h))
            cv.behind(x + wob, y, (170, 185, 210) if h % 3 else (230, 240, 255))
        cols = [(255, 40, 40), (40, 255, 80), (255, 200, 40), (60, 140, 255)]
        for (x, y, w, h) in cv.tiles:
            for n, i in enumerate(range(x + 2, x + w - 1, 4)):
                c = cols[(n + f // 4) % 4]
                cv.px(i, y, c if (n + f // 2) % 3 else shade(c, -0.5))
    elif DECOR == "embers":
        for x, y, h in _field(f, 5, 2, speed=-1):
            c = (255, 150, 40) if (f + h) % 4 else (255, 70, 10)
            cv.behind(x + round(math.sin(f * 0.8 + h)), y, shade(c, -0.2 * (h % 3)))
    elif DECOR == "bats":
        for x, y, h in _field(0, 2, 3):
            cv.behind(x, y, (190, 120, 255) if (f + h) % 8 < 2 else (60, 30, 90))
        for n, by in enumerate((18 if page == "weather" else 31, 6)):
            bx = -8 + (f * 80 // FRAMES + n * 37) % 80
            rows = BAT_UP if (f // 2 + n) % 2 else BAT_DOWN
            for j, r in enumerate(rows):
                for i, ch in enumerate(r):
                    if ch == "#":
                        cv.behind(bx + i, by + j, (150, 80, 230))
    elif DECOR == "synth":
        for x, y, h in _field(0, 2, 4):
            cv.behind(x, y, (90, 240, 255) if (f + h) % 8 < 2 else (70, 20, 90))
        sy = (f * 4) % 64
        for x in range(64):
            cv.behind(x, sy, shade(TILE, 0.45))
            cv.behind(x, sy - 1, shade(TILE, 0.2))
    elif DECOR == "steel":
        # rivets in the plate corners + a specular glint sliding along every top bevel
        for (x, y, w, h) in cv.tiles:
            for (rx, ry) in ((x + 2, y + 2), (x + w - 3, y + 2), (x + 2, y + h - 3), (x + w - 3, y + h - 3)):
                if all(cv.is_bg(rx + dx, ry + dy) for dx in (-1, 0, 1, 2) for dy in (-1, 0, 1, 2)):
                    cv.px(rx, ry, (175, 185, 200)); cv.px(rx + 1, ry + 1, (12, 13, 16))
            pos = x + (f * (w + 10) // FRAMES) - 5
            for d in range(-2, 3):
                if x <= pos + d < x + w:
                    cv.px(pos + d, y, mix(BEV_TOP, (255, 255, 255), 1 - abs(d) / 3))
            ly = y + (f * (h + 6) // FRAMES) - 3
            for d in range(-1, 2):
                if y <= ly + d < y + h:
                    cv.px(x, ly + d, mix(BEV_LEFT, (255, 255, 255), 0.7 - abs(d) * 0.3))
    elif DECOR == "coins":
        # drifting clouds in the sky gaps + a spinning coin in the AQI tile
        for x0, y0 in ((5, 24), (40, 39), (22, 9 if page == "weather" else 24)):
            x = (x0 + f) % 72 - 4
            for dx in range(4):
                cv.behind(x + dx, y0, (255, 255, 255))
        if page == "dashboard" and not cv.umbrella:
            widths = [5, 4, 2, 1, 2, 4, 5, 5]
            w = widths[(f // 2) % 8]
            cx = 42
            for j in range(7):
                ww = w if j not in (0, 6) else max(1, w - 2)
                for i in range(ww):
                    xx = cx - ww // 2 + i
                    c = (255, 210, 40)
                    if i == 0 and ww > 2: c = (255, 250, 170)
                    if i == ww - 1 and ww > 2: c = (200, 120, 0)
                    cv.behind(xx, 27 + j, c)


# ----------------------------------------------------------------------------
# DASHBOARD
# ----------------------------------------------------------------------------
APPLIANCE_STATES = {
    "job_ongoing": ("RUN", "run"), "job_completed": ("DONE", "done"), "paused": ("PAUS", "pause"),
    "detached_overload": ("ERR", "err"), "unplugged": ("OFF", "off"), "idle": ("IDLE", "idle"),
}
PRINTER_MAP = {
    "printing": "run", "running": "run", "busy": "run",
    "paused": "pause", "pausing": "pause", "pause": "pause",
    "preparing": "prep", "prepare": "prep", "slicing": "prep", "init": "prep", "initializing": "prep",
    "finished": "done", "finish": "done", "completed": "done", "done": "done",
    "error": "err", "failed": "err", "idle": "idle", "offline": "off",
}
STATE_COLOR = {"done": GREEN, "pause": AMBER, "err": RED, "off": DIM, "idle": GREY, "prep": CYAN}


def status_strip(cv, x, w, c, mode, f, fill=None):
    """2-row 3D strip on top of a tile. mode: run (scanning light), pulse, blink, progress."""
    light, dark = mix(c, (255, 255, 255), 0.5), shade(c, -0.45)
    if mode == "blink" and (f // 4) % 2:
        light, dark = shade(c, -0.5), shade(c, -0.75)
    if mode == "pulse":
        k = pulse(f, 0.55, 1.0)
        light, dark = shade(light, k - 1), shade(dark, k - 1)
    if fill is None:
        fill = w
    if mode == "progress":
        cv.rect(x, 41, w, 2, shade(c, -0.82))
    cv.rect(x, 41, fill, 1, light)
    cv.rect(x, 42, fill, 1, dark)
    if mode in ("run", "progress") and fill > 0:
        pos = (f * (fill + 6) // FRAMES) - 3
        for d in range(-1, 2):
            if 0 <= pos + d < fill:
                cv.px(x + pos + d, 41, (255, 255, 255))
                cv.px(x + pos + d, 42, light)


def big_temp(cv, cx, y, v, scale, f, unit_gap=True):
    if v is None:
        for dx in (-8, 1):
            cv.rect(cx + dx + 1, y + 6, 6, 2, SHADOW)
            cv.rect(cx + dx, y + 5, 6, 2, DIM)
        return
    s = ("%d" % round(abs(v))) if (v < 0 or v >= 100) else ("%.1f" % v)
    if v < 0: s = "-" + s
    s += "°"
    c = temp_color(v, *scale)
    w = cv.text_width(s, "big")
    cv.text(cx, y, s, c, "big", "center", grad=GRAD_BIG, glint=glint_pos(f, w))


def render_dashboard(d, f, variant=0):
    cv = Canvas()
    for t in [(0, 0, 31, 23), (33, 0, 31, 23), (0, 25, 64, 14)]:
        cv.tile(*t)

    # --- temperatures + humidity ---
    cv.sprite(2, 2, *HOUSE)
    cv.sprite(35, 2, *TREE)
    for t, h, cx, x1, scale, judge in [(d.get("t_in"), d.get("h_in"), 15, 30, IN_SCALE, True),
                                         (d.get("t_out"), d.get("h_out"), 48, 63, OUT_SCALE, False)]:
        big_temp(cv, cx, 10, num(t), scale, f)
        hv = num(h)
        if hv is not None:
            hv = round(hv)
            hc = (90, 200, 255) if (not judge or 35 <= hv <= 65) else AMBER
            s = "%d%%" % hv
            w = cv.text_width(s)
            cv.text(x1 - 1, 3, s, hc, align="right")
            cv.sprite(x1 - 1 - w - 7, 2, *DROP)

    # --- AQI: continuous colour gauge ---
    a = num(d.get("aqi"))
    aqi_gauge(cv, a, f)
    col = aqi_color(a) if a is not None else GREY
    if a is not None:
        a = int(round(a))
        cv.rect(3, 28, 7, 7, SHADOW)
        cv.rect(2, 27, 7, 7, col)
        cv.rect(2, 33, 7, 1, shade(col, -0.4))
        cv.rect(8, 27, 1, 7, shade(col, -0.25))
        for (i, j) in [(0, 0), (6, 0), (0, 6), (6, 6)]: cv.px(2 + i, 27 + j, TILE)
        cv.px(3, 28, (255, 255, 255))
        K = (10, 10, 16)
        cv.px(4, 29, K); cv.px(6, 29, K)
        if f in (10, 11):  # blink
            cv.px(4, 29, shade(col, -0.5)); cv.px(6, 29, shade(col, -0.5))
        mouth = ({"good": [(3, 31), (7, 31), (4, 32), (5, 32), (6, 32)],
                  "meh": [(4, 32), (5, 32), (6, 32)],
                  "bad": [(4, 31), (5, 31), (6, 31), (3, 32), (7, 32)]}
                 ["good" if a < 50 else "meh" if a < 101 else "bad"])
        for p in mouth: cv.px(*p, K)
        s = str(a)
        cv.text(12, 27, s, col, "gicko", grad=GRAD_MID, glint=glint_pos(f, cv.text_width(s, "gicko")))
    else:
        for x in (3, 12, 19):
            cv.rect(x + 1, 31, 5, 2, SHADOW)
            cv.rect(x, 30, 5, 2, DIM)
    cv.text(61, 28, "AQI", LABEL2, align="right")
    draw_umbrella(cv, d, f)

    # --- bottom row: appliances, or info cards when everything is idle ---
    states_ = _appliance_states(d)
    all_idle = all(k in ("idle", "off") for k, _ in states_)
    # All idle/off -> sunrise/sunset only. Something active -> variant 0 shows the appliances,
    # variant 1 the sunrise/sunset card (the Pixoo page alternates between them).
    if all_idle or variant == 1:
        card_sun(cv, d, f)
    else:
        appliance_row(cv, d, f, states_)
    decorate(cv, f, "dashboard")
    return cv.img


# ----------------------------------------------------------------------------
# WEATHER ICONS (procedural, any size; S=22 big, S=9 small)
# ----------------------------------------------------------------------------
def _cloud_mask(S, sc=1.0, ox=0.0, oy=0.0):
    k = S / 22.0 * sc
    circles = [(7, 12, 5), (12, 9, 6), (17, 13, 4)]
    m = set()
    for j in range(S):
        for i in range(S):
            px_, py_ = (i + 0.5 - ox) / k, (j + 0.5 - oy) / k
            inside = any((px_ - cx) ** 2 + (py_ - cy) ** 2 <= r * r for cx, cy, r in circles)
            inside = inside or (2.5 <= px_ <= 19.5 and 12 <= py_ <= 17.5)
            if inside and py_ <= 17.5:
                m.add((i, j))
    return m


def cloud(cv, x, y, S, base, sc=1.0, ox=0.0, oy=0.0, flash=0.0):
    m = _cloud_mask(S, sc, ox, oy)
    if not m:
        return
    js = [j for _, j in m]
    top, bot = min(js), max(js)
    for (i, j) in m:
        if (i + 1, j + 1) not in m:
            cv.px(x + i + 1, y + j + 1, SHADOW)
    for (i, j) in m:
        rel = (j - top) / max(1, bot - top)
        c = shade(base, 0.35 - rel * 0.75)
        if (i, j - 1) not in m or (i - 1, j) not in m:
            c = shade(base, 0.6)
        if (i, j + 1) not in m or (i + 1, j) not in m:
            c = shade(base, -0.45)
        if flash: c = shade(c, flash)
        cv.px(x + i, y + j, c)


def sun(cv, x, y, S, f, cx=None, cy=None, r=None):
    k = S / 22.0
    cx = 11 * k if cx is None else cx
    cy = 11 * k if cy is None else cy
    r = 5 * k if r is None else r
    # rays
    for n in range(8):
        a = n * math.pi / 4 + (math.pi / 8 if S < 12 else (math.pi / 4) * f / FRAMES)
        if S < 12:
            on = (n + f // 4) % 2 == 0
            L0, L1 = r + 1.2, r + 2.2
            col = (255, 220, 70) if on else (200, 110, 20)
        else:
            L0 = r + 2
            L1 = r + 3 + 2.0 * pulse(f, 0, 1, phase=n * math.pi / 2)
            col = (255, 215, 60)
        t = L0
        while t <= L1:
            px_, py_ = cx + math.cos(a) * t, cy + math.sin(a) * t
            cv.px(x + int(px_), y + int(py_), col)
            t += 0.5
    # halo + disc with radial gradient
    for j in range(int(cy - r - 2), int(cy + r + 3)):
        for i in range(int(cx - r - 2), int(cx + r + 3)):
            d = math.hypot(i + 0.5 - cx, j + 0.5 - cy)
            if d <= r:
                t = d / r
                c = mix((255, 245, 150), (255, 150, 10), t ** 1.3)
                if (i + 0.5 - cx) + (j + 0.5 - cy) > r * 0.9:
                    c = shade(c, -0.15)
                cv.px(x + i, y + j, c)
            elif d <= r + 1 and S >= 12:
                cv.px(x + i, y + j, shade((255, 140, 20), -0.55 + 0.25 * pulse(f)))


def moon(cv, x, y, S, f, cx=None, cy=None, r=None, stars=True):
    k = S / 22.0
    cx = 11 * k if cx is None else cx
    cy = 11 * k if cy is None else cy
    r = 6 * k if r is None else r
    for j in range(S):
        for i in range(S):
            px_, py_ = i + 0.5, j + 0.5
            if math.hypot(px_ - cx, py_ - cy) <= r and math.hypot(px_ - (cx + r * 0.55), py_ - (cy - r * 0.35)) > r * 0.85:
                t = (py_ - (cy - r)) / (2 * r)
                cv.px(x + i, y + j, mix((255, 250, 215), (220, 190, 110), t))
    if S >= 12:   # soft pulsing halo on the lit edge
        g = pulse(f, 0.0, 0.35)
        for j in range(S):
            for i in range(S):
                d0 = math.hypot(i + 0.5 - cx, j + 0.5 - cy)
                if r < d0 <= r + 1.2 and (i + 0.5 - cx) < r * 0.3:
                    cv.px(x + i, y + j, mix(cv.get(x + i, y + j), (255, 240, 170), g))
    if stars:
        pts = [(0.75, 0.15, 0.0), (0.88, 0.55, 2.0), (0.6, 0.85, 4.0), (0.15, 0.1, 1.0)] if S >= 12 else [(0.85, 0.15, 0.0)]
        for sx, sy, ph in pts:
            b = pulse(f, 0.15, 1.0, phase=ph)
            c = shade((255, 255, 220), b - 1)
            X, Y = x + int(sx * S), y + int(sy * S)
            cv.px(X, Y, c)
            if S >= 12 and b > 0.7:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    cv.px(X + dx, Y + dy, shade(c, -0.55))


def precip(cv, x, y, S, f, kind):
    k = S / 22.0
    if S < 12:   # compact version for forecast icons
        cols = [2, 5, 8] if kind != "pour" else [1, 3, 5, 7, 9]
        for n, cx in enumerate(cols):
            yy = 7 + ((f // 2 + n * 2) % 3)
            c = {"rain": (110, 200, 255), "pour": (90, 170, 255), "snow": (255, 255, 255),
                 "hail": (200, 235, 255), "sleet": (255, 255, 255) if n % 2 else (110, 200, 255)}[kind]
            cv.px(x + cx, y + yy, c)
        return
    top = int(15 * k)
    span = S - top
    if kind in ("rain", "pour"):
        cols = [5, 9, 13, 17] if kind == "rain" else [3, 6, 9, 12, 15, 18]
        speed = 1 if kind == "rain" else 2
        for n, cx in enumerate(cols):
            X = x + int(cx * k) - (1 if S >= 12 else 0)
            period = max(2, span)
            yy = top + ((f * speed // (1 if S >= 12 else 2) + n * 3) % period)
            cv.px(X, y + yy, (150, 215, 255))
            if S >= 12:
                cv.px(X, y + yy - 1, (50, 130, 240))
    elif kind in ("snow", "hail", "sleet"):
        cols = [5, 11, 17] if S >= 12 else [6, 14]
        for n, cx in enumerate(cols):
            period = max(2, span)
            yy = top + ((f // 2 + n * 3) % period)
            wob = round(math.sin(2 * math.pi * f / FRAMES + n)) if S >= 12 else 0
            X = x + int(cx * k) + wob
            if kind == "sleet" and n % 2:
                cv.px(X, y + yy, (120, 200, 255)); continue
            c = (255, 255, 255) if kind != "hail" else (200, 235, 255)
            cv.px(X, y + yy, c)
            if S >= 12 and kind == "snow":
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    cv.px(X + dx, y + yy + dy, (150, 180, 220))


def bolt(cv, x, y, S, f):
    if f not in (0, 1, 2, 8, 9):
        return
    k = S / 22.0
    pts = [(12, 12), (10, 15), (12, 15), (9, 20)] if S >= 12 else [(5, 5), (4, 7), (5, 7), (4, 8)]
    col = (255, 245, 120) if f not in (2, 9) else (255, 190, 40)
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        ax_, ay_, bx_, by_ = (ax * k, ay * k, bx * k, by * k) if S >= 12 else (ax, ay, bx, by)
        n = int(max(abs(bx_ - ax_), abs(by_ - ay_)) * 2) + 1
        for t in range(n + 1):
            cv.px(x + round(ax_ + (bx_ - ax_) * t / n), y + round(ay_ + (by_ - ay_) * t / n), col)


def fog(cv, x, y, S, f):
    k = S / 22.0
    rows = [5, 9, 13, 17] if S >= 12 else [2, 4, 6, 8]
    for n, r in enumerate(rows):
        off = round(2 * math.sin(2 * math.pi * f / FRAMES + n * 1.3)) if S >= 12 else ((f // 4 + n) % 2)
        c = shade((190, 200, 220), -0.1 * n)
        x0, x1 = (3, 19) if S >= 12 else (1, 8)
        for i in range(x0, x1):
            if S >= 12 and (i + n * 3) % 9 == 0:
                continue
            cv.px(x + i + off, y + (r if S < 12 else int(r)), c)


def wind(cv, x, y, S, f):
    rows = [6, 11, 16] if S >= 12 else [2, 5, 7]
    for n, r in enumerate(rows):
        L = (16 if S >= 12 else 7) - n * (3 if S >= 12 else 1)
        for i in range(L):
            yy = r + (1 if S >= 12 and i > L - 3 else 0) * -1
            c = (180, 215, 255)
            if S >= 12 and ((i - f * 2 + n * 5) % 12) < 3:
                c = (255, 255, 255)
            cv.px(x + 2 + i, y + yy, c)


def warning(cv, x, y, S, f):
    on = (f // 4) % 2 == 0
    c = AMBER if on else shade(AMBER, -0.5)
    h = S - 2
    for j in range(h):
        w = j
        for i in range(-w // 2, w // 2 + 1):
            cv.px(x + S // 2 + i, y + 1 + j, c)
    cv.rect(x + S // 2, y + h // 2, 1, h // 3, (20, 10, 0))
    cv.px(x + S // 2, y + h - 1, (20, 10, 0))


def weather_icon(cv, x, y, S, cond, night, f):
    cond = (cond or "").lower()
    big = S >= 12
    # Every icon moves: clouds drift (big: +-2 px, small: +-1 px), moons bob, sun rays turn.
    ph = 2 * math.pi * f / FRAMES
    drift = round((2 if big else 1) * math.sin(ph))
    drift2 = round((1.5 if big else 1) * math.sin(ph + math.pi * 0.7))
    bob = round(math.sin(ph)) if big else (1 if (f // 4) % 2 else 0)
    WHITE, GREYC, DARKC = (225, 232, 245), (150, 160, 185), (95, 100, 125)
    if cond in ("sunny",):
        sun(cv, x, y, S, f)
    elif cond == "clear-night":
        moon(cv, x, y + bob, S, f)
    elif cond == "partlycloudy":
        if night:
            moon(cv, x, y + (bob if big else 0), S, f, cx=S * 0.38, cy=S * 0.36, r=S * 0.25, stars=big)
        else:
            sun(cv, x, y, S, f, cx=S * (0.36 if big else 0.32), cy=S * (0.36 if big else 0.32),
                r=S * (0.19 if big else 0.26))
        cloud(cv, x, y, S, WHITE, sc=0.78 if big else 0.72, ox=S * (0.22 if big else 0.3) + drift,
              oy=S * (0.25 if big else 0.32))
    elif cond == "cloudy":
        cloud(cv, x, y, S, GREYC, sc=0.7, ox=S * 0.3 + drift2, oy=S * 0.02)
        cloud(cv, x, y, S, WHITE, sc=0.85, ox=drift, oy=S * 0.2)
    elif cond in ("rainy", "pouring", "snowy", "snowy-rainy", "hail"):
        base = GREYC if cond in ("pouring", "hail") else WHITE
        cloud(cv, x, y, S, base, sc=0.9, ox=S * 0.03 + drift, oy=-S * 0.12)
        kind = {"rainy": "rain", "pouring": "pour", "snowy": "snow", "snowy-rainy": "sleet", "hail": "hail"}[cond]
        precip(cv, x, y, S, f, kind)
    elif cond in ("lightning", "lightning-rainy"):
        flash = 0.35 if f in (0, 8) else 0.0
        cloud(cv, x, y, S, DARKC, sc=0.9, ox=S * 0.03 + drift, oy=-S * 0.12, flash=flash)
        if cond == "lightning-rainy":
            precip(cv, x, y, S, f, "rain")
        bolt(cv, x, y, S, f)
    elif cond == "fog":
        fog(cv, x, y, S, f)
    elif cond in ("windy", "windy-variant"):
        if cond == "windy-variant":
            cloud(cv, x, y, S, GREYC, sc=0.6, ox=S * 0.35 + drift, oy=-S * 0.15)
        wind(cv, x, y, S, f)
    else:
        warning(cv, x, y, S, f)


# ----------------------------------------------------------------------------
# WEATHER PAGE
# ----------------------------------------------------------------------------
def render_weather(d, f):
    cv = Canvas()
    w = d.get("weather", {}) or {}
    cv.tile(0, 0, 64, 9)
    cv.tile(0, 10, 64, 22)
    cv.tile(0, 33, 64, 31)

    # --- top bar: date | time | weekday ---
    cv.text(2, 2, str(d.get("date", "")), LABEL)
    cv.text(61, 2, str(d.get("dow", "")), LABEL, align="right")
    t = str(d.get("time", ""))
    cv.text(32, 1, t, TIME_C, "gicko", "center", grad=GRAD_MID)

    # --- current conditions ---
    night = str(d.get("sun", "")) == "below_horizon"
    cond = w.get("condition")
    if night and str(cond).lower() == "sunny":
        cond = "clear-night"
    weather_icon(cv, 2, 11, 20, cond, night, f)
    cur = num(d.get("t_out"))
    if cur is None:
        cur = num(w.get("temperature"))
    big_temp(cv, 44, 12, cur, OUT_SCALE, f)

    fc = d.get("forecast") or []
    today = None
    if fc and str(fc[0].get("date")) == str(d.get("today")):
        today, fc = fc[0], fc[1:]
    if today:
        hi, lo = num(today.get("hi")), num(today.get("lo"))
        parts = []
        if hi is not None: parts.append((UP[0], "%d°" % round(hi), RED if hi > 30 else AMBER if hi > 25 else (255, 160, 110)))
        if lo is not None: parts.append((DOWN[0], "%d°" % round(lo), (110, 180, 255)))
        widths = [5 + 2 + cv.text_width(s) for _, s, _ in parts]
        total = sum(widths) + 4 * (len(parts) - 1)
        x = 44 - total // 2
        for (arrow, s, c), wd in zip(parts, widths):
            tri(cv, x, 26, arrow, c)
            cv.text(x + 7, 25, s, c, grad=GRAD_SMALL)
            x += wd + 4

    # --- 4-day forecast ---
    for n in range(4):
        x = n * 16
        if n % 2:
            cv.rect(x, 34, 16 if n < 3 else 15, 29, ZEBRA)
        if n >= len(fc):
            continue
        day = fc[n]
        weekend = int(day.get("wd", 0) or 0) in (6, 7)
        cv.text(x + 8, 36, str(day.get("d", ""))[:2], WEEKEND if weekend else LABEL, align="center")
        weather_icon(cv, x + 3, 41, 10, day.get("c"), False, (f + n * 3) % FRAMES)
        hi, lo = num(day.get("hi")), num(day.get("lo"))
        if hi is not None:
            cv.text(x + 8, 52, "%d" % round(hi), temp_color(hi, *OUT_SCALE), align="center", grad=GRAD_SMALL)
        if lo is not None:
            cv.text(x + 8, 58, "%d" % round(lo), (140, 160, 210), align="center")
    decorate(cv, f, "weather")
    return cv.img


# ----------------------------------------------------------------------------
# GIF output
# ----------------------------------------------------------------------------
def led_correct(img, gamma, sat):
    """Compensate for LED response: deepen darks (gamma) and boost saturation so colours stay
    vivid at low panel brightness instead of washing out to pastel."""
    if sat != 1.0:
        img = ImageEnhance.Color(img).enhance(sat)
    if gamma != 1.0:
        lut = [min(255, round(255 * (i / 255) ** gamma)) for i in range(256)]
        img = img.point(lut * 3)
    return img


def _copy(src, dst):
    with open(src, "rb") as a, open(dst + ".tmp", "wb") as b:
        b.write(a.read())
    os.replace(dst + ".tmp", dst)


def error_frame(name):
    cv = Canvas()
    cv.tile(0, 0, 64, 64)
    cv.text(32, 20, "RENDER", RED, align="center")
    cv.text(32, 28, "ERROR", RED, align="center")
    cv.text(32, 40, name.split(".")[0][:15].upper(), GREY, align="center")
    return cv.img


def save_gif(frames, path, gamma=1.0, sat=1.0):
    frames = [led_correct(fr, gamma, sat) for fr in frames]
    if NIGHT_DIM != 1.0:
        frames = [Image.eval(fr, lambda v: int(v * NIGHT_DIM)) for fr in frames]
    strip = Image.new("RGB", (64, 64 * len(frames)))
    for i, fr in enumerate(frames):
        strip.paste(fr, (0, 64 * i))
    pal = strip.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = [pal.crop((0, 64 * i, 64, 64 * (i + 1))) for i in range(len(frames))]
    tmp = path + ".tmp.gif"
    out[0].save(tmp, save_all=True, append_images=out[1:], duration=FRAME_MS, loop=0,
                optimize=False, disposal=1)
    os.replace(tmp, path)


DEMO = {
    "t_in": 23.8, "t_out": 19.9, "h_in": 41, "h_out": 32, "aqi": 72,
    "wm": "job_ongoing", "td": "job_completed", "pr": "printing", "pr_left": 85, "pr_pct": 62,
    "time": "10:31", "date": "4.10", "dow": "NE", "today": "2026-10-04", "sun": "above_horizon",
    "theme": "neon", "vivid": "vivid", "wm_age": 7200, "td_age": 190000, "pr_age": 400000,
    "sunrise": "07:02", "sunset": "18:41", "hourly_ok": True,
    "hourly": [{"t": "14", "p": 10, "mm": 0, "c": "cloudy"}, {"t": "17", "p": 60, "mm": 0.8, "c": "rainy"}], "wind_speed": 12, "wind_unit": "km/h", "wind_bearing": 225,
    "weather": {"condition": "partlycloudy", "temperature": 25},
    "forecast": [
        {"d": "NE", "wd": 7, "date": "2026-10-04", "c": "partlycloudy", "hi": 25, "lo": 10},
        {"d": "PO", "wd": 1, "date": "2026-10-05", "c": "rainy", "hi": 24, "lo": 8},
        {"d": "UT", "wd": 2, "date": "2026-10-06", "c": "sunny", "hi": 18, "lo": 9},
        {"d": "SR", "wd": 3, "date": "2026-10-07", "c": "cloudy", "hi": 20, "lo": 14},
        {"d": "ČE", "wd": 4, "date": "2026-10-08", "c": "lightning-rainy", "hi": 19, "lo": 12},
    ],
}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        data = DEMO
    elif len(sys.argv) > 1:
        data = json.loads(base64.b64decode(sys.argv[1]).decode("utf-8"))
    else:
        print("usage: pixoo_render.py <base64-json> | --demo", file=sys.stderr)
        sys.exit(2)
    os.makedirs(OUT_DIR, exist_ok=True)
    errors = []
    try:
        apply_theme(data.get("theme"), data.get("today", ""))
    except Exception:
        errors.append("theme: " + traceback.format_exc())
        apply_theme("neon")
    preset = str(data.get("vivid") or "vivid").lower().split("(")[0].strip()
    gamma, sat = VIVID.get(preset, VIVID["vivid"])

    def render(fn, path):
        """Render one page; on failure write a visible error screen so the Pixoo still shows something."""
        try:
            frames = [fn(f) for f in range(FRAMES)]
        except Exception:
            errors.append(os.path.basename(path) + ": " + traceback.format_exc())
            frames = [error_frame(os.path.basename(path))] * 2
        save_gif(frames, path, gamma, sat)
        return path

    render(lambda f: render_weather(data, f), os.path.join(OUT_DIR, "weather.gif"))
    # dashboard_0.gif = appliances (or sunrise/sunset when everything is idle),
    # dashboard_1.gif = sunrise/sunset. The Pixoo page alternates between them (see gif_url).
    # dashboard_2.gif is a copy of dashboard_1.gif for older page configs using "% 3".
    try:
        all_idle = all(k in ("idle", "off") for k, _ in _appliance_states(data))
    except Exception:
        all_idle = False
    first = render(lambda f: render_dashboard(data, f, 0), os.path.join(OUT_DIR, "dashboard_0.gif"))
    second = os.path.join(OUT_DIR, "dashboard_1.gif")
    if all_idle:
        _copy(first, second)
    else:
        render(lambda f: render_dashboard(data, f, 1), second)
    _copy(second, os.path.join(OUT_DIR, "dashboard_2.gif"))
    _copy(first, os.path.join(OUT_DIR, "dashboard.gif"))

    status = "%s  theme=%s  colours=%s  all_idle=%s\n" % (data.get("time"), THEME_NAME, preset, all_idle)
    status += ("ERRORS:\n" + "\n".join(errors)) if errors else "OK\n"
    with open(os.path.join(OUT_DIR, "status.txt"), "w") as fh:
        fh.write(status)
    if errors:
        print(status, file=sys.stderr)
        sys.exit(1)
    print("ok theme=%s vivid=%s" % (THEME_NAME, preset))


if __name__ == "__main__":
    main()
