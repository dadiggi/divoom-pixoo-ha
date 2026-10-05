#!/usr/bin/env python3
"""
Pixoo 64 animated dashboard + weather renderer for Home Assistant.

Called by HA's shell_command with a base64-encoded JSON payload:
    python3 /config/pixoo/pixoo_render.py <base64-json>
Writes animated 64x64 GIFs to /config/www/pixoo/ (served as /local/pixoo/...),
which the divoom_pixoo integration shows with `page_type: gif`.

Only needs Pillow, which ships with Home Assistant.
"""
import base64, datetime, json, math, os, sys, traceback
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
             grad=None, glint=None, outline=None, colfn=None, shadow_c=None):
        """grad: per-row shade factors. glint: diagonal highlight position.
        outline: colour of a 1-px outline (for busy art backgrounds) - replaces the drop shadow.
        colfn(x, y, row) -> colour: per-pixel colouring (e.g. gold shimmer)."""
        w = self.text_width(s, font)
        if align == "center": x -= w // 2
        elif align == "right": x -= w
        s = str(s)
        if outline is not None:
            layers = [((dx, dy), outline) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
        elif shadow:
            layers = [((1, 1), shadow_c or SHADOW)]
        else:
            layers = []
        layers.append(((0, 0), None))
        for (ox, oy), lc in layers:
            cx = x
            for ch in s:
                gw, gh, m = self.glyph(font, ch)
                pts = [(ax, ay) for (ax, ay) in ACCENTS.get(ch.upper(), (None, []))[1]]
                pts += [(i, j) for j in range(gh) for i in range(gw) if m[j][i]]
                for (i, j) in pts:
                    if lc is not None:
                        self.px(cx + i + ox, y + j + oy, lc)
                        continue
                    c = color
                    if colfn is not None:
                        c = colfn(cx + i, y + j, max(0, j))
                    elif grad:
                        c = shade(color, grad[min(max(j, 0), len(grad) - 1)])
                    if glint is not None:
                        dd = abs((cx + i - x) - j * 0.6 - glint)
                        if dd < 2.0: c = shade(c, 0.75 - dd * 0.3)
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


# ============================================================================
# ART DESIGNS  (mondrian, van_gogh, hokusai, klimt)
# Same data and behaviour as the classic design, each with its own layout and drawing style.
# ============================================================================
def temp_str(v):
    if v is None:
        return None
    s = ("%d" % round(abs(v))) if (v < 0 or v >= 100) else ("%.1f" % v)
    return ("-" if v < 0 else "") + s + "°"


def appl_list(d):
    """Washer, dryer, printer as dicts: kind, k (state key), label, pct."""
    out = []
    for kind, key, agek in (("washer", "wm", "wm_age"), ("dryer", "td", "td_age")):
        label, k = APPLIANCE_STATES.get(d.get(key), ("--", "off"))
        if k in ("idle", "off"):
            label = age_text(d.get(agek)) or ("IDLE" if k == "idle" else "OFF")
        out.append({"kind": kind, "k": k, "label": label, "pct": None})
    k = PRINTER_MAP.get(str(d.get("pr", "")).lower(), "off")
    pct = num(d.get("pr_pct"))
    mins = int(num(d.get("pr_left")) or 0)
    left = ("%dh%02d" % (mins // 60, mins % 60)) if mins >= 60 else ("%dm" % mins)
    if k in ("idle", "off"):
        label = age_text(d.get("pr_age")) or ("IDLE" if k == "idle" else "OFF")
    else:
        label = {"run": left, "pause": "PAUS", "prep": "PREP", "done": "DONE", "err": "ERR"}[k]
    out.append({"kind": "printer", "k": k, "label": label, "pct": pct})
    return out


def show_sun_card(d, variant):
    try:
        all_idle = all(a["k"] in ("idle", "off") for a in appl_list(d))
    except Exception:
        all_idle = False
    return all_idle or variant == 1


def today_and_next(d):
    fc = d.get("forecast") or []
    fc = [x for x in fc if isinstance(x, dict)] if isinstance(fc, list) else []
    today = None
    if fc and str(fc[0].get("date")) == str(d.get("today")):
        today, fc = fc[0], fc[1:]
    return today, fc[:4]


def cur_temp(d):
    v = num(d.get("t_out"))
    if v is None:
        w = d.get("weather") if isinstance(d.get("weather"), dict) else {}
        v = num(w.get("temperature"))
    return v


def cur_cond(d):
    w = d.get("weather") if isinstance(d.get("weather"), dict) else {}
    c = str(w.get("condition") or "").lower()
    if str(d.get("sun", "")) == "below_horizon" and c == "sunny":
        c = "clear-night"
    return c


def cond_group(c):
    c = str(c or "").lower()
    if c in ("sunny",): return "sun"
    if c == "clear-night": return "night"
    if c == "partlycloudy": return "partly"
    if c in ("cloudy",): return "cloud"
    if c in ("rainy", "pouring"): return "rain"
    if c in ("snowy", "snowy-rainy", "hail"): return "snow"
    if c in ("lightning", "lightning-rainy"): return "storm"
    if c == "fog": return "fog"
    if c in ("windy", "windy-variant"): return "wind"
    return "unknown"


def lum(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def ink_for(bg, dark=(15, 15, 18), light=(245, 242, 235)):
    return dark if lum(bg) > 120 else light


def disc(cv, cx, cy, r, colfn):
    for j in range(int(cy - r) - 1, int(cy + r) + 2):
        for i in range(int(cx - r) - 1, int(cx + r) + 2):
            dd = math.hypot(i + 0.5 - cx, j + 0.5 - cy)
            if dd <= r:
                cv.px(i, j, colfn(dd / max(r, 0.01), i, j))


# ----------------------------------------------------------------------------
# MONDRIAN  - De Stijl grid: black lines, white & primary cells, travelling colour blips
# ----------------------------------------------------------------------------
M_W, M_K = (232, 228, 214), (12, 12, 14)
M_R, M_B, M_Y, M_G = (214, 36, 30), (28, 72, 178), (250, 204, 22), (190, 188, 180)
M_HOUSE = ["...#...", "..###..", ".#####.", "#######", ".#...#.", ".#.#.#.", ".#.#.#."]
M_TREE = ["..###..", ".#####.", "#######", ".#####.", "..###..", "...#...", "..###.."]
M_DROP = ["..#..", ".###.", "#####", "#####", ".###."]


def m_cell(cv, x, y, w, h, c):
    cv.rect(x, y, w, h, c)


def m_blips(cv, f, hlines, vlines):
    """Mondrian's 'boogie-woogie': little colour squares running along the black lines."""
    cols = [M_Y, M_R, M_B, M_Y]
    for n, (y, x0, x1) in enumerate(hlines):
        L = x1 - x0
        for k in range(2):
            pos = x0 + int((f * L / FRAMES * (1 if n % 2 else -1) + k * L / 2 + n * 7)) % L
            c = cols[(n + k) % 4]
            for dx in (0, 1):
                for dy in (0, 1):
                    if cv.get(pos + dx, y + dy) == M_K:
                        cv.px(pos + dx, y + dy, c)
    for n, (x, y0, y1) in enumerate(vlines):
        L = y1 - y0
        pos = y0 + int(f * L / FRAMES + n * 5) % L
        c = cols[(n + 2) % 4]
        for dx in (0, 1):
            for dy in (0, 1):
                if cv.get(x + dx, pos + dy) == M_K:
                    cv.px(x + dx, pos + dy, c)


def m_sprite(cv, x, y, rows, c):
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch == "#":
                cv.px(x + i, y + j, c)


def m_appliance(cv, x, y, w, h, a, f):
    k = a["k"]
    fill = {"run": {"washer": M_B, "dryer": M_R, "printer": M_W}[a["kind"]], "done": M_Y,
            "err": M_R if (f // 4) % 2 == 0 else M_W, "pause": M_G, "prep": M_G}.get(k, M_W)
    m_cell(cv, x, y, w, h, fill)
    if a["kind"] == "printer" and k in ("run", "pause") and a["pct"] is not None:
        ph = round(h * max(0, min(100, a["pct"])) / 100)            # yellow fill = progress
        m_cell(cv, x, y + h - ph, w, ph, M_Y)
    ink = ink_for(fill) if k not in ("idle", "off") else M_K
    if k in ("idle", "off"):
        ink = (70, 70, 74)
    ix, iy = x + (w - 11) // 2, y + 2
    # geometric icons
    for i in range(11):
        cv.px(ix + i, iy, ink); cv.px(ix + i, iy + 10, ink)
        cv.px(ix, iy + i, ink); cv.px(ix + 10, iy + i, ink)
    ang = 2 * math.pi * f / FRAMES
    if a["kind"] in ("washer", "dryer"):
        cv.rect(ix + 1, iy + 2, 9, 1, ink)
        for n in range(16):
            t = 2 * math.pi * n / 16
            cv.px(round(ix + 5 + 3 * math.cos(t)), round(iy + 6 + 3 * math.sin(t)), ink)
        if k == "run":
            for q in (0, math.pi):
                cv.px(round(ix + 5 + 1.6 * math.cos(ang * 2 + q)), round(iy + 6 + 1.6 * math.sin(ang * 2 + q)), ink)
        if a["kind"] == "dryer":
            cv.px(ix + 2, iy + 1, ink); cv.px(ix + 4, iy + 1, ink)
    else:
        cv.rect(ix + 1, iy + 3, 9, 1, ink)                          # gantry
        hx = ix + 3 + (round(2 + 2 * math.sin(ang)) if k == "run" else 2)
        cv.rect(hx, iy + 4, 3, 2, ink)
        cv.rect(ix + 3, iy + 8, 5, 2, ink)                          # print
    cv.text(x + w // 2, y + h - 7, a["label"], ink, align="center", shadow=False)


def m_sun_cells(cv, d, f, x0=0, y0=41, h=23):
    for n, (x, w, rising, sky, sunc, t) in enumerate([
            (x0, 31, True, M_Y, M_R, d.get("sunrise")), (x0 + 33, 31, False, M_R, M_Y, d.get("sunset"))]):
        m_cell(cv, x, y0, w, 14, sky)
        m_cell(cv, x, y0 + 16, w, h - 16, M_W)
        prog = f / (FRAMES - 1)
        sy = (y0 + 11 - 7 * prog) if rising else (y0 + 4 + 7 * prog)
        sx = x + w // 2 - 3
        for j in range(6):
            if y0 <= sy + j < y0 + 14:
                cv.rect(sx, int(sy) + j, 6, 1, sunc)
        cv.rect(x, y0 + 14, w, 2, M_K)                              # horizon line
        cv.text(x + w // 2, y0 + h - 6, str(t or "--:--"), M_K, "pico", "center", shadow=False)


def render_dashboard_mondrian(d, f, variant=0):
    cv = Canvas()
    cv.rect(0, 0, 64, 64, M_K)
    # --- indoor (white) / outdoor (colour by temperature) ---
    tin, tout = num(d.get("t_in")), num(d.get("t_out"))
    out_bg = M_W if tout is None else (M_B if tout < 10 else M_Y if tout <= 25 else M_R)
    for x, bg, v, h, icon in [(0, M_W, tin, d.get("h_in"), M_HOUSE), (33, out_bg, tout, d.get("h_out"), M_TREE)]:
        m_cell(cv, x, 0, 31, 21, bg)
        ink = ink_for(bg)
        m_sprite(cv, x + 2, 2, icon, ink)
        hv = num(h)
        if hv is not None:
            cv.text(x + 29, 3, "%d%%" % round(hv), ink, align="right", shadow=False)
            m_sprite(cv, x + 29 - cv.text_width("%d%%" % round(hv)) - 6, 3, M_DROP,
                     M_B if bg != M_B else M_W)
        s = temp_str(v)
        if s:
            cv.text(x + 15, 9, s, ink, "big", "center", shadow=False)
    # --- AQI: value + stepped blocks ---
    m_cell(cv, 0, 23, 45, 16, M_W)
    a = num(d.get("aqi"))
    cv.text(3, 25, "AQI", M_K, shadow=False)
    if a is not None:
        cv.text(3, 31, str(int(round(a))), M_K, "gicko", shadow=False)
        cat = 0 if a < 50 else 1 if a < 101 else 2 if a < 151 else 3 if a < 201 else 4
        for i in range(5):
            bh = 3 + i * 2
            bx, by = 24 + i * 4, 37 - bh
            c = aqi_color(i * 50 + 25)
            if i < cat:
                cv.rect(bx, by, 3, bh, c)
            elif i == cat:
                cv.rect(bx, by, 3, bh, c if (f // 4) % 4 else shade(c, 0.4))
                cv.rect(bx, by - 2, 3, 1, M_K)                      # pointer tick
            else:
                cv.rect(bx, by, 3, bh, M_G)
    # --- umbrella cell ---
    out = rain_outlook(d)
    ux, uy = 47, 23
    if out is None:
        m_cell(cv, ux, uy, 17, 16, M_W)
    elif out[0]:
        m_cell(cv, ux, uy, 17, 16, M_B)
        canopy = ["....###....", "..#######..", ".#########.", "###########"]
        m_sprite(cv, ux + 3, uy + 3, canopy, M_W)
        cv.rect(ux + 8, uy + 7, 1, 5, M_W); cv.rect(ux + 6, uy + 11, 2, 1, M_W)
        for n, cx in enumerate((ux + 2, ux + 14, ux + 4, ux + 12)):
            yy = uy + 7 + (f + n * 4) % 8
            cv.rect(cx, yy, 1, 2, M_W)
    else:
        m_cell(cv, ux, uy, 17, 16, M_Y)
        sz = 6 + (1 if (f // 4) % 2 else 0)
        cv.rect(ux + 8 - sz // 2, uy + 8 - sz // 2, sz, sz, M_R)
    # --- bottom row ---
    if show_sun_card(d, variant):
        m_sun_cells(cv, d, f)
        vl = [(31, 41, 63)]
    else:
        for x, a in zip((0, 22, 44), appl_list(d)):
            m_appliance(cv, x, 41, 20, 23, a, f)
        vl = [(20, 41, 63), (42, 41, 63)]
    m_blips(cv, f, [(21, 0, 64), (39, 0, 64)], [(31, 0, 21), (45, 23, 39)] + vl)
    return cv.img


def m_weather_icon(cv, x, y, w, h, grp, f):
    """Geometric weather in a Mondrian cell (cell colour carries the weather too)."""
    bg = {"sun": M_Y, "night": M_B, "partly": M_Y, "cloud": M_G, "rain": M_B, "snow": M_B,
          "storm": (60, 60, 66), "fog": M_W, "wind": M_W}.get(grp, M_W)
    m_cell(cv, x, y, w, h, bg)
    cx, cy = x + w // 2, y + h // 2
    drift = round(2 * math.sin(2 * math.pi * f / FRAMES))
    rot = (f // 4) % 2

    def cloud_blocks(ox, oy, c=M_W):
        for (bx, by, bw, bh) in [(2, 3, 14, 5), (5, 0, 7, 4), (0, 5, 18, 4)]:
            cv.rect(ox + bx - 1, oy + by - 1, bw + 2, bh + 2, M_K)
        for (bx, by, bw, bh) in [(2, 3, 14, 5), (5, 0, 7, 4), (0, 5, 18, 4)]:
            cv.rect(ox + bx, oy + by, bw, bh, c)

    if grp in ("sun", "partly"):
        sx, sy = (cx, cy) if grp == "sun" else (cx - 5, cy - 5)
        cv.rect(sx - 4, sy - 4, 8, 8, M_R)
        rays = [(0, -8), (0, 6), (-8, 0), (6, 0)] if rot else [(-7, -7), (5, -7), (-7, 5), (5, 5)]
        for (dx, dy) in rays:
            cv.rect(sx + dx, sy + dy, 2, 2, M_K)
        if grp == "partly":
            cloud_blocks(cx - 7 + drift, cy + 1)
    elif grp == "night":
        for j in range(-6, 7):
            for i in range(-6, 7):
                if i * i + j * j <= 36 and (i - 3) ** 2 + (j + 2) ** 2 > 25:
                    cv.px(cx - 2 + i, cy + j, M_Y)
        for n, (sx, sy) in enumerate([(x + 3, y + 3), (x + w - 5, y + 5), (x + w - 7, y + h - 5)]):
            if (f // 4 + n) % 3:
                cv.rect(sx, sy, 2, 2, M_W)
    elif grp in ("cloud", "rain", "snow", "storm"):
        cloud_blocks(cx - 9 + drift, y + 3, M_W if grp != "storm" else M_G)
        if grp == "cloud":
            cloud_blocks(cx - 6 - drift, y + 12)
        elif grp == "rain":
            for n in range(5):
                cv.rect(x + 4 + n * 4, y + 15 + (f + n * 3) % 7, 1, 2, M_W)
        elif grp == "snow":
            for n in range(4):
                cv.rect(x + 4 + n * 5, y + 15 + (f // 2 + n * 2) % 7, 2, 2, M_W)
        else:
            if f % 8 < 3:
                for j, dx in enumerate([3, 2, 1, 2, 3, 2, 1]):
                    cv.rect(cx - 2 + dx, y + 14 + j, 2, 1, M_Y)
    elif grp == "fog":
        for n in range(4):
            off = round(3 * math.sin(2 * math.pi * f / FRAMES + n))
            cv.rect(x + 3 + off, y + 4 + n * 5, w - 8, 2, M_G)
    elif grp == "wind":
        for n in range(3):
            L = w - 6 - n * 4
            off = (f * 2 + n * 5) % (w - 4)
            cv.rect(x + 2, y + 5 + n * 6, L, 2, M_B)
            cv.rect(x + 2 + off % L, y + 5 + n * 6, 2, 2, M_R)
    else:
        cv.rect(cx - 1, cy - 6, 2, 8, M_K); cv.rect(cx - 1, cy + 4, 2, 2, M_K)


def m_small_icon(cv, x, y, grp, f):
    """10x4 colour block with a tiny moving glyph (the colour alone also tells the weather)."""
    bg = {"sun": M_Y, "night": M_B, "partly": M_Y, "cloud": M_G, "rain": M_B, "snow": M_B,
          "storm": (60, 60, 66), "fog": M_W, "wind": M_W}.get(grp, M_W)
    cv.rect(x - 1, y - 1, 12, 6, M_K)
    cv.rect(x, y, 10, 4, bg)
    t = (f // 4) % 2
    if grp == "sun":
        cv.rect(x + 4 - t, y + 1 - t, 2 + 2 * t, 2 + 2 * t, M_R)
    elif grp == "partly":
        cv.rect(x + 1, y + 1, 2, 2, M_R); cv.rect(x + 4 + t, y + 2, 5, 2, M_W)
    elif grp == "cloud":
        cv.rect(x + 2 + t, y + 1, 6, 2, M_W)
    elif grp in ("rain", "snow"):
        for n in range(4):
            cv.px(x + 1 + n * 2 + (n % 2), y + (f // 2 + n) % 4, M_W)
    elif grp == "storm":
        if f % 8 < 4:
            for j, dx in enumerate([4, 3, 5, 4]):
                cv.px(x + dx, y + j, M_Y)
    elif grp == "night":
        cv.rect(x + 3, y, 3, 4, M_Y); cv.rect(x + 5, y, 1, 3, M_B)
        if t: cv.px(x + 8, y + 1, M_W)
    elif grp in ("fog", "wind"):
        for n in range(2):
            cv.rect(x + 1 + ((f // 4 + n) % 2), y + n * 2, 7, 1, M_G if grp == "fog" else M_B)


def render_weather_mondrian(d, f):
    cv = Canvas()
    cv.rect(0, 0, 64, 64, M_K)
    m_cell(cv, 0, 0, 17, 11, M_W)
    cv.text(8, 4, str(d.get("date", "")), M_K, align="center", shadow=False)
    m_cell(cv, 19, 0, 29, 11, M_W)
    cv.text(33, 3, str(d.get("time", "")), M_K, "gicko", "center", shadow=False)
    m_cell(cv, 50, 0, 14, 11, M_R)
    cv.text(57, 4, str(d.get("dow", "")), M_W, align="center", shadow=False)
    m_weather_icon(cv, 0, 13, 28, 24, cond_group(cur_cond(d)), f)
    m_cell(cv, 30, 13, 34, 24, M_W)
    s = temp_str(cur_temp(d))
    if s:
        cv.text(47, 15, s, M_K, "big", "center", shadow=False)
    today, nxt = today_and_next(d)
    if today:
        hi, lo = num(today.get("hi")), num(today.get("lo"))
        if hi is not None:
            tri(cv, 33, 30, UP[0], M_R); cv.text(39, 29, "%d" % round(hi), M_K, shadow=False)
        if lo is not None:
            tri(cv, 49, 30, DOWN[0], M_B); cv.text(55, 29, "%d" % round(lo), M_K, shadow=False)
    xs = [(0, 15), (17, 14), (33, 14), (49, 15)]
    for n, (x, w) in enumerate(xs):
        m_cell(cv, x, 39, w, 25, M_W)
        if n >= len(nxt):
            continue
        day = nxt[n]
        weekend = int(num(day.get("wd")) or 0) in (6, 7)
        cv.text(x + w // 2, 41, str(day.get("d", ""))[:2], M_R if weekend else M_K, align="center", shadow=False)
        m_small_icon(cv, x + (w - 10) // 2, 47, cond_group(day.get("c")), (f + n * 3) % FRAMES)
        hi, lo = num(day.get("hi")), num(day.get("lo"))
        if hi is not None:
            cv.text(x + w // 2, 53, "%d" % round(hi), M_K, align="center", shadow=False)
        if lo is not None:
            cv.text(x + w // 2, 59, "%d" % round(lo), M_B, align="center", shadow=False)
    m_blips(cv, f, [(11, 0, 64), (37, 0, 64)], [(17, 0, 11), (48, 0, 11), (28, 13, 37), (15, 39, 64), (31, 39, 64), (47, 39, 64)])
    return cv.img


# ----------------------------------------------------------------------------
# VAN GOGH  - swirling brushstroke sky, star orbs, wind-swept golden field
# ----------------------------------------------------------------------------
VG_SKY = [(14, 28, 88), (28, 62, 150), (64, 118, 200), (150, 190, 232), (225, 230, 200)]
VG_FIELD = [(120, 95, 25), (190, 140, 30), (232, 182, 50), (250, 220, 110), (95, 120, 45)]
VG_INK = (10, 16, 48)
VG_YEL = (255, 216, 72)
VG_CREAM = (245, 232, 190)


def _hash(x, y, s=0):
    return ((x * 73856093) ^ (y * 19349663) ^ (s * 83492791)) & 0xffff


def vg_sky(cv, x0, y0, w, h, f, vortices=()):
    ph = 2 * math.pi * f / FRAMES
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            v = math.sin(0.5 * x + 2.4 * math.sin(0.21 * y + 0.7) - ph)
            for (cx, cy, R) in vortices:
                r = math.hypot(x - cx, y - cy)
                if r < R:
                    t = math.atan2(y - cy, x - cx)
                    k = (1 - r / R) ** 0.7
                    v = v * (1 - k) + math.sin(2 * t + 0.95 * r - 2 * ph) * k
            n = ((_hash(x // 2, y) % 100) / 100 - 0.5) * 0.55        # brush-dash texture
            lvl = int((v + n + 1.2) / 2.4 * 4)
            cv.px(x, y, VG_SKY[max(0, min(3, lvl))])


def vg_field(cv, x0, y0, w, h, f):
    ph = 2 * math.pi * f / FRAMES
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            sway = 1.6 * math.sin(ph + y * 0.45)
            u = x + sway + (y - y0) * 0.6                             # diagonal wheat strokes
            v = math.sin(u * 1.1) + ((_hash(int(u) // 2, y, 3) % 100) / 100 - 0.5) * 0.9
            lvl = int((v + 1.5) / 3 * 4)
            c = VG_FIELD[max(0, min(3, lvl))]
            if _hash(x, y, 7) % 23 == 0:
                c = VG_FIELD[4]                                       # green flecks
            cv.px(x, y, c)


def vg_calm(cv, x, y, w, h, k=0.72, tint=(12, 20, 58)):
    """Darkened 'calm zone' behind data so it stays readable on the busy painting."""
    for j in range(y, y + h):
        for i in range(x, x + w):
            if (i in (x, x + w - 1)) and (j in (y, y + h - 1)):
                continue
            cv.px(i, j, mix(cv.get(i, j), tint, k))


def vg_orb(cv, cx, cy, r, core, ring, f, rings=3):
    """Van Gogh star/sun: bright core with concentric, outward-flowing halo strokes."""
    ph = f / FRAMES * 2
    R = r + rings * 1.4
    for j in range(int(cy - R) - 1, int(cy + R) + 2):
        for i in range(int(cx - R) - 1, int(cx + R) + 2):
            d0 = math.hypot(i + 0.5 - cx, j + 0.5 - cy)
            if d0 <= r:
                cv.px(i, j, mix((255, 252, 220), core, (d0 / r) ** 1.5))
            elif d0 <= R:
                band = (d0 - r - ph) % 2.8
                if band < 1.2:
                    a = 1 - (d0 - r) / (R - r)
                    cv.px(i, j, mix(cv.get(i, j), ring, 0.35 + 0.6 * a))


def vg_temp(cv, cx, y, v, warm=True):
    s = temp_str(v)
    if not s:
        return
    top, bot = ((255, 248, 190), (240, 140, 25)) if warm else ((235, 245, 255), (90, 150, 230))
    cv.text(cx, y, s, VG_YEL, "big", "center", outline=VG_INK,
            colfn=lambda x, yy, j: mix(top, bot, j / 10))


VG_HOUSE = ["...r...", "..rrr..", ".rrrrr.", "rrrrrrr", ".ccccc.", ".cyccc.", ".cyccc."]
VG_TREE = ["..ggg..", ".gGggg.", "gggGggg", ".ggggg.", "..ggg..", "...b...", "...b..."]


def vg_sprite(cv, x, y, rows, pal):
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch in pal:
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    if cv.get(x + i + dx, y + j + dy) != pal[ch]:
                        pass
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch in pal:
                cv.px(x + i, y + j, pal[ch])


def vg_appliance(cv, x, y, a, f):
    """Painterly appliance: cream body, dark outline, swirling drum."""
    k, kind = a["k"], a["kind"]
    on = k == "run"
    body = VG_CREAM if k not in ("idle", "off") else (150, 145, 125)
    cv.rect(x - 1, y - 1, 15, 15, VG_INK)
    cv.rect(x, y, 13, 13, body)
    ang = 2 * math.pi * f / FRAMES
    if kind in ("washer", "dryer"):
        cv.rect(x, y + 2, 13, 1, VG_INK)
        for j in range(13):
            for i in range(13):
                d0 = math.hypot(i - 6, j - 7.5)
                if d0 <= 4.4:
                    if d0 > 3.3:
                        cv.px(x + i, y + j, VG_INK)
                    else:
                        t = math.atan2(j - 7.5, i - 6)
                        sw = math.sin(2 * t + 1.6 * d0 - (3 * ang if on else 0))
                        if kind == "washer":
                            c = [(30, 70, 170), (80, 150, 230), (200, 225, 250)][int((sw + 1) * 1.49)]
                        else:
                            c = [(200, 80, 20), (250, 160, 40), (255, 235, 140)][int((sw + 1) * 1.49)]
                        if not on:
                            c = mix(c, (60, 60, 70), 0.75)
                        cv.px(x + i, y + j, c)
        cv.px(x + 10, y + 1, (60, 230, 120) if on and (f // 4) % 2 else VG_INK)
    else:
        cv.rect(x + 2, y + 3, 9, 8, VG_INK)
        win = {"run": (40, 120, 90), "pause": (150, 110, 20), "done": (40, 140, 80), "err": (170, 30, 30)}.get(k, (40, 45, 70))
        cv.rect(x + 3, y + 4, 7, 6, win)
        hx = x + 4 + (round(2 + 2 * math.sin(ang)) if on else 2)
        cv.rect(x + 3, y + 5, 7, 1, mix(win, VG_CREAM, 0.4))
        cv.rect(hx - 1, y + 5, 3, 1, VG_CREAM)
        cv.rect(x + 5, y + 8, 3, 2, VG_YEL if k != "off" else (110, 105, 90))


def vg_status_color(k):
    return {"run": (120, 230, 255), "done": (140, 255, 140), "pause": VG_YEL, "err": (255, 90, 70),
            "prep": (120, 230, 255)}.get(k, (190, 180, 150))


def vg_sun_card(cv, d, f, y0=41):
    for x, w, rising, t in [(0, 32, True, d.get("sunrise")), (32, 32, False, d.get("sunset"))]:
        ph = 2 * math.pi * f / FRAMES
        top, hz = ((40, 110, 170), (250, 200, 90)) if rising else ((70, 30, 90), (250, 100, 40))
        for j in range(y0, y0 + 14):
            for i in range(x, x + w):
                v = math.sin(0.6 * i + 1.8 * math.sin(0.4 * j) - ph)
                tt = (j - y0) / 13
                c = mix(top, hz, tt ** 1.3)
                cv.px(i, j, shade(c, 0.12 * v))
        prog = f / (FRAMES - 1)
        sy = (y0 + 13 - 6 * prog) if rising else (y0 + 7 + 6 * prog)
        vg_orb(cv, x + w // 2, sy, 3, (255, 190, 40) if rising else (255, 120, 30),
               (255, 230, 120) if rising else (255, 150, 80), f, rings=2)
        vg_field(cv, x, y0 + 14, w, 23 - 14, f)
        cv.text(x + w // 2, y0 + 16, str(t or "--:--"), VG_YEL if rising else (255, 160, 90),
                "gicko", "center", outline=VG_INK)
    cv.rect(31, y0, 1, 23, VG_INK)


def render_dashboard_van_gogh(d, f, variant=0):
    cv = Canvas()
    vg_sky(cv, 0, 0, 64, 41, f, vortices=[(31, 23, 15), (58, 6, 7)])
    for (sx, sy, ph) in [(3, 22, 0), (61, 22, 3), (25, 38, 6)]:
        vg_orb(cv, sx, sy, 1, (255, 230, 120), (255, 240, 160), (f + ph) % FRAMES, rings=1)
    # temperatures
    for x, v, h, icon, warm in [(1, num(d.get("t_in")), d.get("h_in"), "house", True),
                                (33, num(d.get("t_out")), d.get("h_out"), "tree", False)]:
        vg_calm(cv, x, 1, 30, 20)
        if icon == "house":
            vg_sprite(cv, x + 2, 2, VG_HOUSE, {"r": (235, 110, 40), "c": VG_CREAM, "y": (255, 200, 40)})
        else:
            vg_sprite(cv, x + 2, 2, VG_TREE, {"g": (40, 130, 70), "G": (120, 200, 90), "b": (120, 80, 40)})
        hv = num(h)
        if hv is not None:
            cv.text(x + 28, 3, "%d%%" % round(hv), (150, 210, 255), align="right", outline=VG_INK)
        vg_temp(cv, x + 15, 9, v, warm)
    # AQI orb + value, umbrella
    a = num(d.get("aqi"))
    if a is not None:
        col = aqi_color(a)
        vg_orb(cv, 7, 31, 3, col, mix(col, (255, 255, 255), 0.3), f, rings=2)
        cv.text(15, 28, str(int(round(a))), col, "gicko", outline=VG_INK,
                colfn=lambda x, y, j: mix(mix(col, (255, 255, 255), 0.5), col, j / 5))
        cv.text(15, 35, "AQI", VG_CREAM, outline=VG_INK)
    out = rain_outlook(d)
    if out is not None:
        ux, uy = 44, 25
        vg_calm(cv, ux - 3, uy - 2, 19, 15, k=0.6)
        if out[0]:
            canopy = ["....####....", "..########..", ".##########.", "############"]
            for j, r in enumerate(canopy):
                for i, ch in enumerate(r):
                    if ch == "#":
                        edge = i == 0 or i == len(r) - 1 or r[i - 1] == "." or r[i + 1] == "." or j == 0
                        cv.px(ux + i, uy + j, VG_INK if edge else
                              [(255, 200, 50), (240, 140, 30)][((i + j) // 2) % 2])
            cv.rect(ux + 6, uy + 4, 1, 6, VG_CREAM); cv.rect(ux + 4, uy + 9, 2, 1, VG_CREAM)
            for n, dx in enumerate((-2, 13, 1, 10)):
                yy = uy + 1 + (f + n * 4) % 11
                cv.px(ux + dx, yy, (210, 235, 255)); cv.px(ux + dx, yy - 1, (110, 170, 240))
        else:
            vg_orb(cv, ux + 6, uy + 6, 2, (255, 200, 40), (255, 230, 120), f, rings=2)
    # bottom
    if show_sun_card(d, variant):
        vg_sun_card(cv, d, f)
    else:
        vg_field(cv, 0, 41, 64, 23, f)
        for x, a2 in zip((3, 25, 47), appl_list(d)):
            vg_calm(cv, x - 2, 42, 19, 21, k=0.6, tint=(40, 25, 10))
            vg_appliance(cv, x + 1, 43, a2, f)
            cv.text(x + 7, 57, a2["label"], vg_status_color(a2["k"]), align="center", outline=VG_INK)
    return cv.img


def vg_icon(cv, x, y, S, grp, f):
    k = S / 20.0
    ph = 2 * math.pi * f / FRAMES
    drift = round((2 if S > 12 else 1) * math.sin(ph))

    def swirl_cloud(sc, ox, oy, dark=False):
        m = _cloud_mask(S, sc, ox, oy)
        for (i, j) in m:
            if (i + 1, j) not in m or (i, j + 1) not in m or (i - 1, j) not in m or (i, j - 1) not in m:
                cv.px(x + i, y + j, VG_INK)
            else:
                v = math.sin(0.9 * i + 1.3 * math.sin(0.7 * j) - ph * 2)
                base = [(200, 215, 235), (240, 245, 250), (160, 185, 220)] if not dark else \
                       [(80, 90, 120), (120, 130, 160), (60, 70, 100)]
                cv.px(x + i, y + j, base[int((v + 1) * 1.49)])

    if grp in ("sun", "partly"):
        if grp == "sun":
            vg_orb(cv, x + S / 2, y + S / 2, 4.5 * k, (255, 170, 30), (255, 220, 90), f, rings=3 if S > 12 else 1)
        else:
            vg_orb(cv, x + S * 0.35, y + S * 0.35, 3.5 * k, (255, 170, 30), (255, 220, 90), f, rings=2 if S > 12 else 1)
            swirl_cloud(0.75, S * 0.25 + drift, S * 0.3)
    elif grp == "night":
        cx, cy, r = x + S * 0.45, y + S * 0.45 + (round(math.sin(ph)) if S > 12 else 0), 5.5 * k
        vg_orb(cv, cx, cy, r, (250, 220, 90), (255, 230, 130), f, rings=2 if S > 12 else 1)
        for j in range(S):
            for i in range(S):
                if math.hypot(x + i + 0.5 - (cx + r * 0.6), y + j + 0.5 - (cy - r * 0.4)) <= r * 0.85 and \
                        math.hypot(x + i + 0.5 - cx, y + j + 0.5 - cy) <= r:
                    cv.px(x + i, y + j, VG_SKY[0])
    elif grp in ("cloud", "rain", "snow", "storm", "wind", "fog"):
        if grp == "cloud":
            swirl_cloud(0.7, S * 0.3 - drift, 0)
            swirl_cloud(0.85, drift, S * 0.2)
        elif grp in ("fog", "wind"):
            for n in range(4):
                yy = y + int(S * (0.2 + n * 0.2))
                for i in range(int(S * 0.9)):
                    v = math.sin(i * 0.8 - ph * 2 + n)
                    if v > -0.3:
                        cv.px(x + i + 1, yy + (1 if grp == "wind" and v > 0.6 else 0),
                              (230, 235, 245) if v > 0.4 else (150, 175, 215))
        else:
            swirl_cloud(0.9, S * 0.03 + drift, -S * 0.12, dark=(grp == "storm"))
            top = int(S * 0.72)
            for n in range(4 if S > 12 else 3):
                xx = x + 2 + n * int(S / 4.2)
                yy = y + top + (f + n * 3) % max(2, S - top)
                if grp == "snow":
                    cv.px(xx, yy, (255, 255, 255))
                elif grp == "rain":
                    cv.px(xx, yy, (225, 240, 255)); cv.px(xx - 1, yy - 1, (150, 200, 255))
                    if S > 12: cv.px(xx - 2, yy - 2, (90, 150, 230))
            if grp == "storm" and f % 8 < 3:
                for j, dx in enumerate([2, 1, 0, 1, 2, 1, 0][: max(3, S - top)]):
                    cv.px(x + S // 2 + dx, y + top - 1 + j, (255, 240, 100))
    else:
        cv.text(x + S // 2, y + S // 2 - 2, "?", VG_YEL, align="center", outline=VG_INK)


def render_weather_van_gogh(d, f):
    cv = Canvas()
    vg_sky(cv, 0, 0, 64, 40, f, vortices=[(40, 20, 13), (8, 8, 6)])
    vg_field(cv, 0, 40, 64, 24, f)
    cv.text(32, 1, str(d.get("time", "")), VG_YEL, "gicko", "center", outline=VG_INK,
            colfn=lambda x, y, j: mix((255, 250, 200), (240, 160, 30), j / 5))
    cv.text(2, 2, str(d.get("date", "")), VG_CREAM, outline=VG_INK)
    cv.text(61, 2, str(d.get("dow", "")), VG_CREAM, align="right", outline=VG_INK)
    vg_icon(cv, 2, 11, 20, cond_group(cur_cond(d)), f)
    vg_calm(cv, 26, 11, 37, 25)
    vg_temp(cv, 44, 13, cur_temp(d), warm=(cur_temp(d) or 0) >= 15)
    today, nxt = today_and_next(d)
    if today:
        hi, lo = num(today.get("hi")), num(today.get("lo"))
        if hi is not None:
            tri(cv, 29, 28, UP[0], (255, 140, 60)); cv.text(36, 27, "%d°" % round(hi), (255, 170, 90), outline=VG_INK)
        if lo is not None:
            tri(cv, 46, 28, DOWN[0], (120, 180, 255)); cv.text(53, 27, "%d°" % round(lo), (150, 200, 255), outline=VG_INK)
    for n in range(4):
        x = n * 16
        vg_calm(cv, x + 1, 37, 14, 26, k=0.62, tint=(40, 25, 10))
        if n >= len(nxt):
            continue
        day = nxt[n]
        weekend = int(num(day.get("wd")) or 0) in (6, 7)
        cv.text(x + 8, 40, str(day.get("d", ""))[:2], (255, 150, 110) if weekend else VG_CREAM, align="center", outline=VG_INK)
        vg_icon(cv, x + 3, 45, 10, cond_group(day.get("c")), (f + n * 3) % FRAMES)
        hi, lo = num(day.get("hi")), num(day.get("lo"))
        if hi is not None:
            cv.text(x + 8, 52, "%d" % round(hi), VG_YEL, align="center", outline=VG_INK)
        if lo is not None:
            cv.text(x + 8, 58, "%d" % round(lo), (150, 200, 255), align="center", outline=VG_INK)
    return cv.img


# ----------------------------------------------------------------------------
# HOKUSAI  - ukiyo-e woodblock: paper, bokashi skies, cartouches, red seal, rolling waves
# ----------------------------------------------------------------------------
HK_P, HK_P2 = (232, 216, 178), (212, 194, 152)
HK_PB, HK_IN, HK_LB = (30, 62, 128), (16, 28, 66), (120, 162, 204)
HK_FO, HK_RD = (246, 244, 232), (196, 48, 34)
HK_CAT = [(110, 150, 70), (215, 168, 40), (222, 112, 40), (182, 40, 40), (112, 62, 132)]


def hk_bokashi(cv, x0, y0, w, h, top, bottom, f=None):
    for j in range(h):
        t = (j / max(1, h - 1)) ** 0.8
        c = mix(top, bottom, t)
        for i in range(w):
            g = c
            if (_hash(x0 + i, y0 + j, 11) % 9) == 0:                    # woodgrain speckle
                g = shade(c, -0.06)
            cv.px(x0 + i, y0 + j, g)


def hk_waves(cv, x0, y0, w, h, f, deep=HK_PB):
    """Two layers of stylised waves scrolling sideways, foam 'claws' on the crests."""
    L = 16
    for layer, (base, amp, col, sp) in enumerate([(y0 + 3, 2.0, HK_LB, 1), (y0 + 7, 2.5, deep, -1)]):
        sc = (f * L / FRAMES) * sp
        for i in range(w):
            x = x0 + i
            ph = 2 * math.pi * (x + sc + layer * 5) / L
            crest = base + amp * math.sin(ph) + 0.8 * math.sin(2 * ph + 1)
            ci = int(round(crest))
            for y in range(ci, y0 + h):
                stripe = (y - ci) % 3 == 1 and layer == 1
                cv.px(x, y, mix(col, HK_FO, 0.25) if stripe else col)
            cv.px(x, ci, HK_FO)
            if math.cos(ph) > 0.75:                                  # curling foam fingers
                cv.px(x, ci - 1, HK_FO)
                if (x + layer) % 2 == 0 and x0 <= x + sp < x0 + w:
                    cv.px(x + sp, ci - 2, HK_FO)


def hk_cartouche(cv, x, y, w, h, fill=HK_P):
    cv.rect(x, y, w, h, HK_IN)
    cv.rect(x + 1, y + 1, w - 2, h - 2, fill)
    cv.rect(x + 2, y + 1, w - 4, 1, mix(fill, HK_RD, 0.35))         # thin red inner rule


def hk_seal(cv, x, y, w, h, text, font="pico", tc=HK_P, col=HK_RD):
    cv.rect(x, y, w, h, col)
    for (i, j) in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (2, 0), (w - 3, h - 1)]:
        cv.px(x + i, y + j, mix(col, HK_P, 0.6))                     # worn stamp edges
    cv.text(x + w // 2, y + (h - (6 if font == "gicko" else 5)) // 2 + (0 if font == "gicko" else 0),
            text, tc, font, "center", shadow=False)


HK_MINKA = ["...k...", "..kkk..", ".kkkkk.", "kkkkkkk", ".pppip.", ".pdpip.", ".pdppp."]
HK_PINE = ["..ggg..", "ggggg..", "...gggg", ".ggg...", "gggggg.", "...b...", "...b..."]


def hk_sprite(cv, x, y, rows, pal):
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch in pal:
                cv.px(x + i, y + j, pal[ch])


def hk_appliance(cv, x, y, a, f):
    k, kind = a["k"], a["kind"]
    on = k == "run"
    ink = HK_IN if k not in ("idle", "off") else mix(HK_IN, HK_P, 0.55)
    for i in range(13):
        cv.px(x + i, y, ink); cv.px(x + i, y + 12, ink); cv.px(x, y + i, ink); cv.px(x + 12, y + i, ink)
    ang = 2 * math.pi * f / FRAMES
    if kind in ("washer", "dryer"):
        cv.rect(x + 1, y + 3, 11, 1, ink)
        fillc = HK_PB if kind == "washer" else HK_RD
        for j in range(13):
            for i in range(13):
                d0 = math.hypot(i - 6, j - 7.5)
                if 3.0 < d0 <= 4.1:
                    cv.px(x + i, y + j, ink)
                elif d0 <= 3.0 and on:
                    t = math.atan2(j - 7.5, i - 6)
                    cv.px(x + i, y + j, HK_FO if math.sin(3 * t + 2 * d0 - 3 * ang) > 0.55 else fillc)
        cv.px(x + 10, y + 1, HK_RD if on and (f // 4) % 2 else ink)
    else:
        cv.rect(x + 2, y + 3, 9, 1, ink)
        hx = x + 4 + (round(2 + 2 * math.sin(ang)) if on else 2)
        cv.rect(hx - 1, y + 4, 3, 2, HK_RD if on else ink)
        cv.rect(x + 4, y + 9, 5, 2, ink)
        if a["pct"] is not None and k in ("run", "pause"):
            cv.rect(x + 1, y + 11, max(0, round(11 * max(0, min(100, a["pct"])) / 100)), 1, HK_RD)


def hk_label_color(k):
    return {"done": (40, 110, 40), "err": HK_RD, "pause": (170, 110, 0)}.get(
        k, HK_IN if k not in ("idle", "off") else mix(HK_IN, HK_P, 0.5))


def hk_sun_card(cv, d, f, y0=41):
    for x, w, rising, t in [(0, 32, True, d.get("sunrise")), (32, 32, False, d.get("sunset"))]:
        top, bot = ((240, 220, 160), (245, 170, 120)) if rising else ((40, 50, 110), (235, 120, 70))
        hk_bokashi(cv, x, y0, w, 15, top, bot)
        prog = f / (FRAMES - 1)
        sy = (y0 + 14 - 6 * prog) if rising else (y0 + 8 + 6 * prog)
        disc(cv, x + w // 2, sy, 4, lambda t_, i, j: HK_RD)
        hk_waves(cv, x, y0 + 11, w, 12, f)
        hk_cartouche(cv, x + 5, y0, w - 10, 8)
        cv.text(x + w // 2, y0 + 2, str(t or "--:--"), HK_IN if rising else HK_RD, "pico", "center", shadow=False)
    cv.rect(31, y0, 2, 23, HK_IN)


def render_dashboard_hokusai(d, f, variant=0):
    cv = Canvas()
    hk_bokashi(cv, 0, 0, 64, 41, HK_PB, HK_P)
    # drifting mist band
    off = (f * 64 // FRAMES)
    for i in range(64):
        x = (i + off) % 64
        if (i // 6) % 3 != 2:
            cv.px(x, 22, mix(cv.get(x, 22), HK_FO, 0.55))
    for x, v, h, rows, pal in [(1, num(d.get("t_in")), d.get("h_in"), HK_MINKA,
                                {"k": (120, 80, 40), "p": HK_P, "d": HK_IN, "i": HK_RD}),
                               (33, num(d.get("t_out")), d.get("h_out"), HK_PINE,
                                {"g": (40, 90, 60), "b": (100, 60, 30)})]:
        hk_cartouche(cv, x, 1, 30, 20)
        hk_sprite(cv, x + 2, 3, rows, pal)
        hv = num(h)
        if hv is not None:
            cv.text(x + 27, 4, "%d%%" % round(hv), HK_PB, align="right", shadow=False)
        s = temp_str(v)
        if s:
            cv.text(x + 15, 9, s, HK_IN, "big", "center", shadow=False)
    # AQI seal + gauge of woodblock colour chips
    a = num(d.get("aqi"))
    if a is not None:
        col = aqi_color(a)
        hk_seal(cv, 2, 25, 17, 12, str(int(round(a))), "gicko")
        cv.text(22, 26, "AQI", HK_IN, shadow=False)
        cat = 0 if a < 50 else 1 if a < 101 else 2 if a < 151 else 3 if a < 201 else 4
        for i in range(5):
            c = HK_CAT[i] if i <= cat else mix(HK_CAT[i], HK_P, 0.7)
            cv.rect(22 + i * 4, 33, 3, 3 if i != cat else 4, c)
        cv.px(22 + cat * 4 + 1, 37 if (f // 4) % 2 else 32, HK_IN)
    out = rain_outlook(d)
    if out is not None:
        ux, uy = 46, 24
        if out[0]:
            # Hiroshige-style slanting rain across the middle band + an open wagasa
            for n in range(9):
                x0 = (n * 7 + f * 2) % 70 - 6
                for t in range(5):
                    xx, yy = x0 + t, 23 + ((n * 5 + f * 3) % 16) + t * 2
                    if 23 <= yy <= 39 and cv.get(xx, yy) not in (HK_RD,):
                        cv.px(xx, yy, mix(cv.get(xx, yy), HK_IN, 0.55))
            sway = round(math.sin(2 * math.pi * f / FRAMES))
            for j, r in enumerate(["....rrrr....", "..rrprrprr..", ".rrrprrprrr.", "rrrrprrprrrr"]):
                for i, ch in enumerate(r):
                    if ch != ".":
                        cv.px(ux + i + sway, uy + 2 + j, HK_RD if ch == "r" else HK_P)
            cv.rect(ux + 6, uy + 6, 1, 7, (100, 60, 30)); cv.rect(ux + 4, uy + 12, 2, 1, (100, 60, 30))
        else:
            disc(cv, ux + 11, uy + 5, 3.5, lambda t_, i, j: HK_RD)
            for j in range(9):
                cv.px(ux + 2 + (1 if j > 6 else 0), uy + 3 + j, HK_RD if j < 6 else (100, 60, 30))
            cv.rect(ux + 1, uy + 4, 3, 4, HK_RD)
    if show_sun_card(d, variant):
        hk_sun_card(cv, d, f)
    else:
        hk_bokashi(cv, 0, 40, 64, 6, HK_P, HK_LB)
        hk_waves(cv, 0, 44, 64, 20, f)
        for x, a2 in zip((1, 23, 45), appl_list(d)):
            hk_cartouche(cv, x, 41, 18, 22)
            hk_appliance(cv, x + 3, 43, a2, f)
            cv.text(x + 9, 56, a2["label"], hk_label_color(a2["k"]), align="center", shadow=False)
    return cv.img


def hk_icon(cv, x, y, w, h, grp, f, small=False):
    """Woodblock weather vignette inside a w x h panel."""
    ph = 2 * math.pi * f / FRAMES
    drift = round((2 if not small else 1) * math.sin(ph))
    night = grp == "night"
    top, bot = {"sun": ((120, 170, 215), (240, 220, 170)), "night": (HK_IN, HK_PB),
                "storm": ((50, 50, 70), (110, 110, 120)), "rain": ((90, 105, 130), (180, 180, 170)),
                "snow": ((150, 165, 185), (230, 230, 225))}.get(grp, ((140, 175, 210), (235, 225, 195)))
    hk_bokashi(cv, x, y, w, h, top, bot)
    if not small:   # a distant snow-capped mountain
        mx, base = x + w // 2 + 3, y + h - 1
        for j in range(9):
            for i in range(-j - 1, j + 2):
                c = HK_FO if j < 3 else (HK_PB if not night else HK_IN)
                cv.px(mx + i, base - 8 + j, c)

    def bands(yy, c=HK_FO, n=2):
        for k in range(n):
            L = (w // 2) if not small else w - 3
            bx = x + 1 + ((k * w // 3 + drift) % max(1, w - L))
            cv.rect(bx, yy + k * (3 if not small else 2), L, 1 if small else 2, c)
            cv.px(bx - 1, yy + k * (3 if not small else 2), c)

    if grp in ("sun", "partly"):
        r = 5 if not small else 2.2
        disc(cv, x + (w * 0.38), y + h * 0.38, r + (0.4 if (f // 4) % 2 else 0), lambda t_, i, j: HK_RD)
        if grp == "partly":
            bands(y + int(h * 0.45))
    elif grp == "night":
        disc(cv, x + w * 0.35, y + h * 0.35 + (0 if small else round(math.sin(ph))), 4.5 if not small else 2,
             lambda t_, i, j: (245, 225, 140))
        bands(y + int(h * 0.42), (90, 110, 160))
    elif grp in ("cloud", "fog", "wind"):
        bands(y + int(h * 0.2), HK_FO, 3)
        if grp == "wind":
            lx = x + (f * w // FRAMES)
            cv.px(lx, y + int(h * 0.3) + round(math.sin(ph * 2)), (200, 120, 40))
    elif grp in ("rain", "storm", "snow"):
        bands(y + 1, (200, 205, 210) if grp != "storm" else (80, 80, 95), 2)
        if grp == "snow":
            for n in range(6 if not small else 3):
                cv.px(x + 2 + n * (w // 6 if not small else 3), y + 4 + (f // 2 + n * 3) % (h - 5), HK_FO)
        else:
            for n in range(7 if not small else 3):
                x0 = x + (n * 5 + f) % w
                yy = y + 3 + (n * 4 + f * 2) % max(1, h - 4)
                for t in range(3 if not small else 2):
                    if x0 + t < x + w and yy + t * 2 < y + h:
                        cv.px(x0 + t, yy + t * 2, HK_IN)
        if grp == "storm" and f % 8 < 3:
            for j, dx in enumerate([2, 1, 0, 1, 2, 1][: (6 if not small else 3)]):
                cv.px(x + w // 2 + dx, y + 3 + j, (255, 230, 80))


def render_weather_hokusai(d, f):
    cv = Canvas()
    cv.rect(0, 0, 64, 64, HK_P)
    hk_cartouche(cv, 0, 0, 50, 11)
    cv.text(5, 4, str(d.get("date", "")), HK_PB, shadow=False)
    cv.text(34, 3, str(d.get("time", "")), HK_IN, "gicko", "center", shadow=False)
    hk_seal(cv, 51, 0, 13, 11, str(d.get("dow", "")))
    cv.rect(0, 12, 28, 25, HK_IN)
    hk_icon(cv, 1, 13, 26, 23, cond_group(cur_cond(d)), f)
    hk_cartouche(cv, 29, 12, 35, 25)
    s = temp_str(cur_temp(d))
    if s:
        cv.text(46, 15, s, HK_IN, "big", "center", shadow=False)
    today, nxt = today_and_next(d)
    if today:
        hi, lo = num(today.get("hi")), num(today.get("lo"))
        if hi is not None:
            tri(cv, 32, 30, UP[0], HK_RD); cv.text(38, 29, "%d°" % round(hi), HK_RD, shadow=False)
        if lo is not None:
            tri(cv, 48, 30, DOWN[0], HK_PB); cv.text(54, 29, "%d°" % round(lo), HK_PB, shadow=False)
    hk_bokashi(cv, 0, 37, 64, 8, HK_P, HK_LB)
    hk_waves(cv, 0, 44, 64, 20, f)
    for n in range(4):
        x = n * 16
        hk_cartouche(cv, x + 1, 38, 14, 26)
        if n >= len(nxt):
            continue
        day = nxt[n]
        weekend = int(num(day.get("wd")) or 0) in (6, 7)
        if weekend:
            hk_seal(cv, x + 3, 39, 10, 7, str(day.get("d", ""))[:2])
        else:
            cv.text(x + 8, 40, str(day.get("d", ""))[:2], HK_IN, align="center", shadow=False)
        hk_icon(cv, x + 3, 46, 10, 6, cond_group(day.get("c")), (f + n * 3) % FRAMES, small=True)
        hi, lo = num(day.get("hi")), num(day.get("lo"))
        if hi is not None:
            cv.text(x + 8, 53, "%d" % round(hi), HK_RD, align="center", shadow=False)
        if lo is not None:
            cv.text(x + 8, 58, "%d" % round(lo), HK_PB, align="center", shadow=False)
    return cv.img


# ----------------------------------------------------------------------------
# KLIMT  - gold-leaf mosaic, spirals & gem tiles, black panels, shimmering glint
# ----------------------------------------------------------------------------
K_G, K_GL, K_GD = (214, 166, 46), (252, 218, 112), (146, 102, 24)
K_K, K_CR = (14, 11, 8), (244, 230, 192)
K_GEMS = [(40, 172, 160), (196, 46, 46), (74, 152, 82), (190, 196, 205), (120, 70, 150)]
K_MOTIFS = {
    "ring": ".DD./D..D/D..D/.DD.", "eye": "KKKK/KLLK/KLLK/KKKK", "spiral": "DDDD/...D/DD.D/D..D",
    "gem": "DDDD/DTTD/DTTD/DDDD", "check": "KK../KK../..CC/..CC", "dots": "L.../..L./.L../...L",
}


def k_glint(x, y, f, width=46):
    pos = (x + y - f * width / FRAMES) % width
    return pos < 3


def k_mosaic(cv, x0, y0, w, h, f):
    for cy in range(y0, y0 + h, 4):
        for cx in range(x0, x0 + w, 4):
            hsh = _hash(cx // 4, cy // 4, 5) % 100
            motif = (None if hsh < 34 else "ring" if hsh < 52 else "spiral" if hsh < 66 else
                     "gem" if hsh < 78 else "eye" if hsh < 88 else "check" if hsh < 94 else "dots")
            gem = K_GEMS[_hash(cx, cy, 9) % len(K_GEMS)]
            rows = K_MOTIFS[motif].split("/") if motif else ["....", "....", "....", "...."]
            for j in range(4):
                for i in range(4):
                    x, y = cx + i, cy + j
                    if not (x0 <= x < x0 + w and y0 <= y < y0 + h):
                        continue
                    ch = rows[j][i]
                    c = {"D": K_GD, "K": K_K, "L": K_GL, "T": gem, "C": K_CR}.get(ch, K_G)
                    if ch == "." and _hash(x, y, 2) % 7 == 0:
                        c = shade(K_G, -0.12)
                    if ch in (".", "D", "L") and k_glint(x, y, f):
                        c = mix(c, (255, 250, 220), 0.6)
                    if ch == "T" and (f // 2 + cx + cy) % 16 == 0:
                        c = mix(c, (255, 255, 255), 0.6)                 # gem sparkle
                    cv.px(x, y, c)


def k_panel(cv, x, y, w, h, f=0):
    cv.rect(x, y, w, h, K_GD)
    cv.rect(x + 1, y + 1, w - 2, h - 2, K_K)
    for j in range(y + 2, y + h - 2):                                 # gold flecks in the black
        for i in range(x + 2, x + w - 2):
            hh = _hash(i, j, 21) % 29
            if hh == 0:
                cv.px(i, j, mix(K_K, K_G, 0.42))
            elif hh == 1:
                cv.px(i, j, mix(K_K, K_GEMS[_hash(i, j, 3) % 3], 0.35))
    for (i, j) in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
        cv.px(i, j, K_GL)
    for i in range(x + 2, x + w - 2, 3):                              # dotted gold inner rule
        cv.px(i, y + 1, mix(K_K, K_G, 0.45))


def k_gold(top=(255, 236, 160), bot=(190, 128, 30)):
    return lambda x, y, j: mix(top, bot, j / 10)


def k_temp(cv, cx, y, v, scale):
    s = temp_str(v)
    if not s:
        return
    if v < scale[0][1]:
        top, bot = (230, 240, 255), (120, 160, 210)                  # silver-blue
    elif v > scale[1][0]:
        top, bot = (255, 200, 150), (200, 60, 40)                    # red gold
    else:
        top, bot = (255, 238, 160), (190, 128, 30)                   # gold leaf
    cv.text(cx, y, s, K_G, "big", "center", shadow=False, colfn=k_gold(top, bot))


def k_spiral_disc(cv, cx, cy, r, f, c1=K_GL, c2=K_GD):
    ang = 2 * math.pi * f / FRAMES
    disc(cv, cx, cy, r, lambda t, i, j: c1 if math.sin(
        3.2 * t * r - math.atan2(j + 0.5 - cy, i + 0.5 - cx) - ang * 2) > 0 else c2)


def k_appliance(cv, x, y, a, f):
    k, kind = a["k"], a["kind"]
    on = k == "run"
    line = K_G if k not in ("idle", "off") else K_GD
    for i in range(13):
        cv.px(x + i, y, line); cv.px(x + i, y + 12, line); cv.px(x, y + i, line); cv.px(x + 12, y + i, line)
    ang = 2 * math.pi * f / FRAMES
    if kind in ("washer", "dryer"):
        cv.rect(x + 1, y + 3, 11, 1, line)
        gem = K_GEMS[0] if kind == "washer" else K_GEMS[1]
        for j in range(13):
            for i in range(13):
                d0 = math.hypot(i - 6, j - 7.5)
                if 3.0 < d0 <= 4.1:
                    cv.px(x + i, y + j, line)
                elif d0 <= 3.0:
                    t = math.atan2(j - 7.5, i - 6)
                    v = math.sin(2 * t + 2.2 * d0 - (3 * ang if on else 0))
                    c = (gem if v > 0 else K_GL) if on else (mix(gem, K_K, 0.6) if v > 0 else K_K)
                    cv.px(x + i, y + j, c)
        for i in range(2, 6, 2):
            cv.px(x + i, y + 1, K_GEMS[2] if on else K_GD)
    else:
        cv.rect(x + 2, y + 3, 9, 1, line)
        hx = x + 4 + (round(2 + 2 * math.sin(ang)) if on else 2)
        cv.rect(hx - 1, y + 4, 3, 2, K_GL if on else K_GD)
        for n in range(3):
            cv.rect(x + 4 + n * 2, y + 9, 1, 2, K_GEMS[n] if k not in ("idle", "off") else K_GD)
        if a["pct"] is not None and k in ("run", "pause"):
            for n in range(5):
                lit = n < round(5 * max(0, min(100, a["pct"])) / 100)
                cv.px(x + 2 + n * 2, y + 11, K_GL if lit else K_GD)


def k_label_color(k):
    return {"run": K_GEMS[0], "done": (140, 220, 120), "err": (240, 80, 70), "pause": K_GL,
            "prep": K_GEMS[0]}.get(k, mix(K_CR, K_K, 0.45))


def k_meadow(cv, x0, y0, w, h, f):
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            hsh = _hash(x, y, 13) % 100
            c = (40, 90, 50) if hsh < 55 else (70, 130, 60)
            if hsh > 86:
                c = [(240, 200, 60), (220, 70, 90), (250, 250, 240), (120, 90, 200)][hsh % 4]
                if (f // 4 + x) % 5 == 0:
                    c = mix(c, (255, 255, 255), 0.4)
            cv.px(x, y, c)


def k_sun_card(cv, d, f, y0=41):
    for x, w, rising, t in [(0, 32, True, d.get("sunrise")), (32, 32, False, d.get("sunset"))]:
        top, bot = ((30, 120, 120), (230, 190, 90)) if rising else ((90, 20, 30), (230, 120, 40))
        for j in range(14):
            cv.rect(x, y0 + j, w, 1, mix(top, bot, j / 13))
        prog = f / (FRAMES - 1)
        sy = (y0 + 13 - 6 * prog) if rising else (y0 + 7 + 6 * prog)
        k_spiral_disc(cv, x + w // 2, sy, 4.2, f)
        k_meadow(cv, x, y0 + 13, w, 10, f)
        cv.rect(x + 6, y0 + 15, w - 12, 7, K_K)
        cv.text(x + w // 2, y0 + 16, str(t or "--:--"), K_GL, align="center", shadow=False,
                colfn=k_gold())
    cv.rect(31, y0, 2, 23, K_GD)


K_HOUSE = ["...G...", "..GGG..", ".GTTTG.", "GGGGGGG", ".CCCCC.", ".CKCRC.", ".CKCCC."]
K_TREE = [".GG.GG.", "G..G..G", "G.GGG.G", ".G.G.G.", "..GGG..", "...G...", "..GGG.."]


def k_sprite(cv, x, y, rows):
    pal = {"G": K_GL, "T": K_GEMS[0], "C": K_CR, "K": K_K, "R": K_GEMS[1]}
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch in pal:
                cv.px(x + i, y + j, pal[ch])


def render_dashboard_klimt(d, f, variant=0):
    cv = Canvas()
    k_mosaic(cv, 0, 0, 64, 64, f)
    for x, v, h, icon, scale in [(1, num(d.get("t_in")), d.get("h_in"), K_HOUSE, IN_SCALE),
                                 (33, num(d.get("t_out")), d.get("h_out"), K_TREE, OUT_SCALE)]:
        k_panel(cv, x, 1, 30, 21)
        k_sprite(cv, x + 2, 3, icon)
        hv = num(h)
        if hv is not None:
            cv.text(x + 27, 4, "%d%%" % round(hv), K_GEMS[0], align="right", shadow=False)
        k_temp(cv, x + 15, 10, v, scale)
    k_panel(cv, 1, 24, 46, 16)
    a = num(d.get("aqi"))
    cv.text(4, 33, "AQI", mix(K_CR, K_K, 0.3), shadow=False)
    if a is not None:
        col = aqi_color(a)
        cv.text(4, 26, str(int(round(a))), col, "gicko", shadow=False,
                colfn=lambda x, y, j: mix(mix(col, (255, 255, 255), 0.55), col, j / 5))
        cat = 0 if a < 50 else 1 if a < 101 else 2 if a < 151 else 3 if a < 201 else 4
        for i in range(5):
            gx, gy = 23 + i * 4, 29
            c = aqi_color(i * 50 + 25)
            if i <= cat:
                cv.rect(gx, gy, 3, 3, c)
                cv.px(gx, gy, mix(c, (255, 255, 255), 0.6))
                if i == cat and (f // 4) % 2:
                    cv.rect(gx - 1, gy - 1, 5, 1, K_GL); cv.rect(gx - 1, gy + 3, 5, 1, K_GL)
            else:
                cv.rect(gx, gy, 3, 3, (40, 32, 20)); cv.px(gx + 1, gy + 1, K_GD)
    k_panel(cv, 49, 24, 14, 16)
    out = rain_outlook(d)
    if out is not None:
        if out[0]:
            sway = round(math.sin(2 * math.pi * f / FRAMES))
            for j, r in enumerate(["...GGG...", ".GGTGTGG.", "GGTGGGTGG"]):
                for i, ch in enumerate(r):
                    if ch != ".":
                        cv.px(51 + i + sway, 27 + j, K_GL if ch == "G" else K_GEMS[0])
            cv.rect(55, 30, 1, 6, K_G); cv.rect(53, 35, 2, 1, K_G)
            for n, dx in enumerate((51, 59, 53, 61)):
                yy = 30 + (f + n * 3) % 8
                cv.px(dx, yy, K_GEMS[0] if n % 2 else K_GL)
        else:
            k_spiral_disc(cv, 56, 32, 4.2, f)
    if show_sun_card(d, variant):
        k_sun_card(cv, d, f)
    else:
        for x, a2 in zip((1, 22, 43), appl_list(d)):
            k_panel(cv, x, 42, 20, 22)
            k_appliance(cv, x + 4, 43, a2, f)
            cv.text(x + 10, 57, a2["label"], k_label_color(a2["k"]), align="center", shadow=False)
    return cv.img


def k_icon(cv, x, y, S, grp, f):
    ph = 2 * math.pi * f / FRAMES
    drift = round((2 if S > 12 else 1) * math.sin(ph))
    small = S <= 12

    def silver_cloud(sc, ox, oy, dark=False):
        m = _cloud_mask(S, sc, ox, oy)
        for (i, j) in m:
            edge = any(n not in m for n in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)))
            if edge:
                c = K_GL if not dark else K_GD
            else:
                c = [(205, 210, 220), (170, 178, 192), (230, 232, 238)][(_hash(i // 2, j // 2, 4)) % 3]
                if dark:
                    c = shade(c, -0.45)
                if not small and k_glint(x + i, y + j, f, 30):
                    c = mix(c, (255, 255, 255), 0.6)
            cv.px(x + i, y + j, c)

    if grp in ("sun", "partly"):
        if grp == "sun":
            k_spiral_disc(cv, x + S / 2, y + S / 2, S * 0.28, f)
            for n in range(8):
                a = n * math.pi / 4 + ph / 8
                rr = S * 0.42
                cv.px(round(x + S / 2 + rr * math.cos(a)), round(y + S / 2 + rr * math.sin(a)),
                      K_GL if (n + f // 4) % 2 else K_GEMS[1])
        else:
            k_spiral_disc(cv, x + S * 0.36, y + S * 0.36, S * 0.22, f)
            silver_cloud(0.75, S * 0.25 + drift, S * 0.3)
    elif grp == "night":
        cx, cy, r = x + S * 0.45, y + S * 0.45 + (0 if small else round(math.sin(ph))), S * 0.28
        disc(cv, cx, cy, r, lambda t, i, j: K_CR if math.hypot(i + 0.5 - (cx + r * 0.6), j + 0.5 - (cy - r * 0.4)) > r * 0.85 else K_K)
        for n, (sx, sy) in enumerate([(0.8, 0.15), (0.85, 0.7), (0.15, 0.85)][: (1 if small else 3)]):
            if (f // 4 + n) % 3:
                cv.px(x + int(S * sx), y + int(S * sy), K_GL)
    elif grp in ("cloud", "rain", "snow", "storm"):
        if grp == "cloud":
            silver_cloud(0.7, S * 0.3 - drift, 0)
            silver_cloud(0.85, drift, S * 0.2)
        else:
            silver_cloud(0.9, S * 0.03 + drift, -S * 0.12, dark=(grp == "storm"))
            top = int(S * 0.72)
            for n in range(4 if not small else 3):
                xx = x + 2 + n * int(S / 4.2)
                yy = y + top + (f // (2 if grp == "snow" else 1) + n * 3) % max(2, S - top)
                c = {"rain": K_GEMS[0], "snow": (250, 250, 250), "storm": K_GEMS[0]}[grp]
                cv.px(xx, yy, c)
                if not small and grp == "rain":
                    cv.px(xx, yy - 1, mix(c, K_K, 0.4))
            if grp == "storm" and f % 8 < 3:
                for j, dx in enumerate([2, 1, 0, 1, 2, 1][: max(3, S - top)]):
                    cv.px(x + S // 2 + dx, y + top - 1 + j, K_GL)
    elif grp in ("fog", "wind"):
        for n in range(4 if not small else 3):
            yy = y + int(S * (0.2 + n * 0.22))
            for i in range(int(S * 0.85)):
                xx = x + 1 + (i + (f // 2 if grp == "wind" else 0) * (1 if n % 2 else -1)) % int(S * 0.85)
                cv.px(xx, yy, K_GL if (i // 2) % 2 else (190, 196, 205))
    else:
        cv.text(x + S // 2, y + S // 2 - 2, "?", K_GL, align="center", shadow=False)


def k_small_icon(cv, x, y, grp, f):
    """10x5 jewel-like forecast glyphs."""
    t = (f // 4) % 2
    silver = [(205, 210, 220), (230, 232, 238)]
    if grp in ("sun", "partly"):
        k_spiral_disc(cv, x + (5 if grp == "sun" else 3), y + 2.5, 2.6, f)
        if grp == "partly":
            cv.rect(x + 4 + t, y + 2, 6, 3, silver[0]); cv.rect(x + 5 + t, y + 1, 3, 1, silver[1])
        elif t:
            for (dx, dy) in ((0, -1), (10, 2), (5, 5)):
                cv.px(x + dx, y + dy, K_GEMS[1])
    elif grp == "night":
        disc(cv, x + 4, y + 2.5, 2.6, lambda tt, i, j: K_CR if i < x + 4 + (j % 2) else K_K)
        if t: cv.px(x + 8, y, K_GL)
    elif grp in ("cloud", "rain", "snow", "storm"):
        c = silver if grp != "storm" else [(110, 112, 120), (140, 142, 150)]
        cv.rect(x + 1 + (t if grp == "cloud" else 0), y + 1, 8, 2, c[0])
        cv.rect(x + 3 + (t if grp == "cloud" else 0), y, 4, 1, c[1])
        for n in range(3):
            if grp in ("rain", "snow"):
                cv.px(x + 2 + n * 3, y + 3 + (f // 2 + n) % 3, K_GEMS[0] if grp == "rain" else (255, 255, 255))
        if grp == "storm" and f % 8 < 4:
            cv.px(x + 5, y + 3, K_GL); cv.px(x + 4, y + 4, K_GL)
    elif grp in ("fog", "wind"):
        for n in range(3):
            cv.rect(x + ((f // 4 + n) % 2), y + n * 2, 9, 1, K_GL if n % 2 else (190, 196, 205))


def render_weather_klimt(d, f):
    cv = Canvas()
    k_mosaic(cv, 0, 0, 64, 64, f)
    k_panel(cv, 0, 0, 64, 11)
    cv.text(3, 3, str(d.get("date", "")), mix(K_CR, K_K, 0.2), shadow=False)
    cv.text(32, 3, str(d.get("time", "")), K_GL, "gicko", "center", shadow=False, colfn=k_gold())
    cv.text(60, 3, str(d.get("dow", "")), K_GEMS[0], align="right", shadow=False)
    k_panel(cv, 0, 12, 26, 25)
    k_icon(cv, 3, 15, 20, cond_group(cur_cond(d)), f)
    k_panel(cv, 27, 12, 37, 25)
    k_temp(cv, 45, 15, cur_temp(d), OUT_SCALE)
    today, nxt = today_and_next(d)
    if today:
        hi, lo = num(today.get("hi")), num(today.get("lo"))
        if hi is not None:
            tri(cv, 31, 30, UP[0], K_GEMS[1]); cv.text(37, 29, "%d°" % round(hi), (240, 130, 90), shadow=False)
        if lo is not None:
            tri(cv, 47, 30, DOWN[0], K_GEMS[0]); cv.text(53, 29, "%d°" % round(lo), K_GEMS[0], shadow=False)
    for n in range(4):
        x = n * 16
        k_panel(cv, x, 38, 16, 26)
        if n >= len(nxt):
            continue
        day = nxt[n]
        weekend = int(num(day.get("wd")) or 0) in (6, 7)
        cv.text(x + 8, 41, str(day.get("d", ""))[:2], K_GEMS[1] if weekend else K_CR, align="center", shadow=False)
        k_small_icon(cv, x + 3, 47, cond_group(day.get("c")), (f + n * 3) % FRAMES)
        hi, lo = num(day.get("hi")), num(day.get("lo"))
        if hi is not None:
            cv.text(x + 8, 52, "%d" % round(hi), K_GL, align="center", shadow=False, colfn=k_gold())
        if lo is not None:
            cv.text(x + 8, 58, "%d" % round(lo), K_GEMS[0], align="center", shadow=False)
    return cv.img


# ----------------------------------------------------------------------------
# Design selection
# ----------------------------------------------------------------------------
ART_DESIGNS = ["mondrian", "van_gogh", "hokusai", "klimt"]
ALL_DESIGNS = ["classic"] + ART_DESIGNS


def resolve_design(data):
    """'classic', an art design, or a rotation: 'rotate daily', 'rotate hourly', 'rotate daily (art only)'."""
    name = str(data.get("design") or "classic").lower().strip()
    key = name.replace(" ", "_")
    if key in ALL_DESIGNS:
        return key
    if name.startswith("rotate"):
        pool = ART_DESIGNS if "art" in name else ALL_DESIGNS
        today = str(data.get("today") or "")
        try:
            day_no = datetime.date.fromisoformat(today[:10]).toordinal()
        except ValueError:
            day_no = datetime.date.today().toordinal()
        hour = int(str(data.get("time") or "0:0").split(":")[0] or 0) if str(data.get("time") or "")[:2].isdigit() else 0
        idx = day_no * 24 + hour if "hour" in name else day_no
        return pool[idx % len(pool)]
    return "classic"


def page_renderers(design):
    if design == "classic":
        return render_dashboard, render_weather
    return globals()["render_dashboard_" + design], globals()["render_weather_" + design]


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
    "theme": "neon", "vivid": "vivid", "design": "classic", "wm_age": 7200, "td_age": 190000, "pr_age": 400000,
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

    design = resolve_design(data)
    dash_fn, weather_fn = page_renderers(design)
    render(lambda f: weather_fn(data, f), os.path.join(OUT_DIR, "weather.gif"))
    # dashboard_0.gif = appliances (or sunrise/sunset when everything is idle),
    # dashboard_1.gif = sunrise/sunset. The Pixoo page alternates between them (see gif_url).
    # dashboard_2.gif is a copy of dashboard_1.gif for older page configs using "% 3".
    try:
        all_idle = all(k in ("idle", "off") for k, _ in _appliance_states(data))
    except Exception:
        all_idle = False
    first = render(lambda f: dash_fn(data, f, 0), os.path.join(OUT_DIR, "dashboard_0.gif"))
    second = os.path.join(OUT_DIR, "dashboard_1.gif")
    if all_idle:
        _copy(first, second)
    else:
        render(lambda f: dash_fn(data, f, 1), second)
    _copy(second, os.path.join(OUT_DIR, "dashboard_2.gif"))
    _copy(first, os.path.join(OUT_DIR, "dashboard.gif"))

    status = "%s  design=%s  theme=%s  colours=%s  all_idle=%s\n" % (
        data.get("time"), design, THEME_NAME, preset, all_idle)
    status += ("ERRORS:\n" + "\n".join(errors)) if errors else "OK\n"
    with open(os.path.join(OUT_DIR, "status.txt"), "w") as fh:
        fh.write(status)
    if errors:
        print(status, file=sys.stderr)
        sys.exit(1)
    print("ok design=%s theme=%s vivid=%s" % (design, THEME_NAME, preset))


if __name__ == "__main__":
    main()
