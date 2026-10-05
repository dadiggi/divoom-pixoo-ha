#!/usr/bin/env python3
"""
Pixoo 64 animated dashboard + weather renderer for Home Assistant.

Called by HA's shell_command with a base64-encoded JSON payload:
    python3 /config/pixoo/pixoo_render.py <base64-json>
Writes animated 64x64 GIFs to /config/www/pixoo/ (served as /local/pixoo/...),
which the divoom_pixoo integration shows with `page_type: gif`.

Only needs Pillow, which ships with Home Assistant.
"""
import base64
import datetime, functools, inspect, json, math, os, sys, traceback
from PIL import Image, ImageEnhance

OUT_DIR = os.environ.get("PIXOO_OUT", "/config/www/pixoo")
FRAMES = 16          # design frames per animation cycle (GIF length follows the motion helpers)
FRAME_MS = 125       # GIF frame time; 16 x 125 ms = 2 s cycle at motion speed 3
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
# --- purist fonts: maximum legibility, every glyph unambiguous -------------------------------
# plain (3x5 labels): square 0 vs round O, diagonal S vs square 5, diagonal Z vs 2, B vs 8,
# open-top 4, wide M/N/W.
FONTS["plain"] = {
    "A": ".#./#.#/###/#.#/#.#", "B": "##./#.#/##./#.#/##.", "C": ".##/#../#../#../.##",
    "D": "##./#.#/#.#/#.#/##.", "E": "###/#../##./#../###", "F": "###/#../##./#../#..",
    "G": ".##/#../#.#/#.#/.##", "H": "#.#/#.#/###/#.#/#.#", "I": "###/.#./.#./.#./###",
    "J": "..#/..#/..#/#.#/.#.", "K": "#.#/#.#/##./#.#/#.#", "L": "#../#../#../#../###",
    "M": "#...#/##.##/#.#.#/#...#/#...#", "N": "#..#/##.#/#.##/#..#/#..#", "O": ".#./#.#/#.#/#.#/.#.",
    "P": "##./#.#/##./#../#..", "Q": ".#./#.#/#.#/##./.##", "R": "##./#.#/##./#.#/#.#",
    "S": ".##/#../.#./..#/##.", "T": "###/.#./.#./.#./.#.", "U": "#.#/#.#/#.#/#.#/###",
    "V": "#.#/#.#/#.#/#.#/.#.", "W": "#...#/#...#/#.#.#/##.##/#...#", "X": "#.#/#.#/.#./#.#/#.#",
    "Y": "#.#/#.#/.#./.#./.#.", "Z": "###/..#/.#./#../###",
    "0": "###/#.#/#.#/#.#/###", "1": ".#./##./.#./.#./###", "2": "###/..#/###/#../###",
    "3": "###/..#/.##/..#/###", "4": "#.#/#.#/###/..#/..#", "5": "###/#../###/..#/###",
    "6": "###/#../###/#.#/###", "7": "###/..#/..#/.#./.#.", "8": "###/#.#/###/#.#/###",
    "9": "###/#.#/###/..#/###", "%": "#.#/..#/.#./#../#.#", "°": "##/##/../../..",
    ":": "./#/./#/.", ".": "././././#", "-": ".../.../###/.../...", "/": "..#/..#/.#./#../#..",
    "↑": ".#./###/.#./.#./.#.", "↓": ".#./.#./.#./###/.#.", "·": "./././#/./.", " ": "../../../../..",
    "(": ".#/#./#./#./.#", ")": "#./.#/.#/.#/#.", "!": "#/#/#/./#", "'": "#/#/./././.",
    "+": ".../.#./###/.#./...", ",": "././././#", "?": "##./..#/.#./.../.#.",
}
# clear (4x7 values)
FONTS["clear"] = {
    "0": ".##./#..#/#..#/#..#/#..#/#..#/.##.", "1": "..#./.##./..#./..#./..#./..#./.###",
    "2": ".##./#..#/...#/..#./.#../#.../####", "3": ".##./#..#/...#/.##./...#/#..#/.##.",
    "4": "#..#/#..#/#..#/####/...#/...#/...#", "5": "####/#.../###./...#/...#/#..#/.##.",
    "6": ".##./#.../#.../###./#..#/#..#/.##.", "7": "####/...#/...#/..#./.#../.#../.#..",
    "8": ".##./#..#/#..#/.##./#..#/#..#/.##.", "9": ".##./#..#/#..#/.###/...#/...#/.##.",
    ".": "././././././#", "°": ".#./#.#/.#./.../.../.../...", "%": "##../##.#/..#./.#../#.##/..##/....",
    "-": ".../.../.../###/.../.../...", ":": "./././#/./#/.", " ": "../../../../../../..",
    "/": "...#/...#/..#./..#./.#../.#../#...",
}
FONTS["clear2"] = {k: "/".join("".join(c * 2 for c in row) for row in v.split("/") for _ in (0, 1))
                   for k, v in FONTS["clear"].items()}
# --- kid font: a five-year-old's careful but lopsided handwriting ---------------------------
FONTS["crayon"] = {
    "0": ".###./#...#/#...#/#...#/#...#/#..#./.##..", "1": "..#../.##../#.#../..#../..#../..#../.###.",
    "2": ".###./#...#/....#/...#./..#../.#.../#####", "3": "####./....#/...#./.###./....#/#...#/.###.",
    "4": "#..#./#..#./#..#./#####/...#./...#./...#.", "5": "#####/#..../####./....#/....#/#...#/.###.",
    "6": "..##./.#.../#..../####./#...#/#...#/.###.", "7": "#####/....#/...#./..#../..#../.#.../.#...",
    "8": ".###./#...#/#..#./.###./#...#/#...#/.###.", "9": ".###./#...#/#...#/.####/....#/...#./.##..",
    "°": ".#./#.#/.#./.../.../.../...", "%": "##.../##..#/...#./..#../.#.../#..##/...##",
    "-": "..../..../..../###./..../..../....", ":": "./././#/./#/.", " ": "../../../../../../..",
    ".": "/".join(["."] * 6 + ["#"]),
}
FONTS["crayon2"] = {k: "/".join("".join(c * 2 for c in row) for row in v.split("/") for _ in (0, 1))
                    for k, v in FONTS["crayon"].items()}
# accents for the wider fonts (caron centred over 4-5 px glyphs)
ACCENTS_FONT = {
    "plain": {"Č": ("C", [(0, -2), (2, -2), (1, -1)]), "Ć": ("C", [(2, -2), (1, -1)]),
              "Š": ("S", [(0, -2), (2, -2), (1, -1)]), "Ž": ("Z", [(0, -2), (2, -2), (1, -1)]),
              "Đ": ("D", [(0, 2)])},
}
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    FONTS["pico"][_c.lower()] = FONTS["pico"][_c]
for _fname, _font in FONTS.items():
    _GLYPHS[_fname] = {}
    for _ch, _rows in _font.items():
        _r = _rows.split("/")
        _GLYPHS[_fname][_ch] = (len(_r[0]), len(_r), [[c == "#" for c in row] for row in _r])


_LAST_CANVAS = None
_SEMANTIC = set()


def protects(fn):
    """Decorator: everything drawn by fn(cv, ...) is data/indicator - themes must not recolour it."""
    def wrapper(cv, *a, **k):
        prev, cv._protect = cv._protect, True
        try:
            return fn(cv, *a, **k)
        finally:
            cv._protect = prev
    functools.update_wrapper(wrapper, fn)
    return wrapper          # colours that carry meaning (AQI scale...) - never recoloured by themes


class Canvas:
    def __init__(self):
        global _LAST_CANVAS
        self.img = Image.new("RGB", (64, 64), BG)
        self.p = self.img.load()
        self.bgl = [row[:] for row in BACKDROP["pix"]] if BACKDROP else None
        if self.bgl:
            for y in range(64):
                for x in range(64):
                    self.p[x, y] = self.bgl[y][x]
        self.tiles = []
        self.umbrella = False
        self.mask = set()        # pixels belonging to text/data: themes leave them alone
        self._protect = False
        self.free_mode = False   # decorations: avoid self.mask instead of classic tile colours
        _LAST_CANVAS = self

    def is_bg(self, x, y):
        """True where nothing but background/tile fill is drawn (used for 'behind content' decor)."""
        if not (0 <= x < 64 and 0 <= y < 64):
            return False
        if self.free_mode:
            return (x, y) not in self.mask and self.p[x, y] not in _SEMANTIC
        if self.bgl and self.p[x, y] == self.bgl[y][x]:
            return True
        return self.p[x, y] in (BG, TILE, ZEBRA, BRUSH)

    def behind(self, x, y, c):
        if self.is_bg(int(x), int(y)):
            self.px(x, y, c)

    def px(self, x, y, c):
        if 0 <= x < 64 and 0 <= y < 64:
            self.p[int(x), int(y)] = tuple(int(max(0, min(255, v))) for v in c[:3])
            if self._protect:
                self.mask.add((int(x), int(y)))

    def get(self, x, y):
        return self.p[x, y] if 0 <= x < 64 and 0 <= y < 64 else BG

    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.px(xx, yy, c)

    def tile(self, x, y, w, h):
        self.tiles.append((x, y, w, h))
        if self.bgl:      # translucent tile: the chosen background shows through
            for yy in range(max(0, y), min(64, y + h)):
                for xx in range(max(0, x), min(64, x + w)):
                    c = mix(self.bgl[yy][xx], TILE, 0.35)
                    self.bgl[yy][xx] = c
                    self.px(xx, yy, c)
        else:
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
        acc = ACCENTS_FONT.get(font, ACCENTS)
        if ch.upper() in acc:
            ch = acc[ch.upper()][0]
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
        prev_protect, self._protect = self._protect, True
        try:
            return self._text(x, y, s, color, font, shadow, grad, glint, outline, colfn, shadow_c, w)
        finally:
            self._protect = prev_protect

    def _text(self, x, y, s, color, font, shadow, grad, glint, outline, colfn, shadow_c, w):
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
                pts = [(ax, ay) for (ax, ay) in ACCENTS_FONT.get(font, ACCENTS).get(ch.upper(), (None, []))[1]]
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


# ----------------------------------------------------------------------------
# Motion: how much moves, how fast, how often effects happen (4 helpers in HA)
# ----------------------------------------------------------------------------
# Every animated thing is either a MOVING PART or an EFFECT.
#   Moving parts have a tier; "motion level" N animates tiers 1..N, the rest freeze in a rest pose:
#     1 meaningful indicators (running/blinking appliances, current weather icon, rain umbrella)
#     2 small life (forecast icons, sun cards, gauges, hearts, needles, rings)
#     3 scenery (skies, waves, clouds, fields, mosaics, room grid, falling code)
#     4 characters and decor (fox hero, swinging signs, boogie blips, comic bursts, hazard stripes)
#     5 everything else (incl. hand-drawn "line boil")
#   Effects are glints, shimmer sweeps, glitches, sparkles, scan lines, CRT bands and theme
#   particles (snow, embers, bats...). Frequency 0 = never ... 5 = constantly.
# Design code still works in 16 "design frames" per animation cycle; the GIF length (L frames of
# FRAME_MS) and the mapping GIF frame -> design frame follow the chosen speeds, loops stay seamless.
class Motion:
    SPEED_P = (32, 24, 20, 16, 12, 8)      # GIF frames per 16-frame design cycle (speed 0..5)
    EVENT_LEN = (16, 12, 10, 8, 6, 4)      # GIF frames one effect event lasts (effect speed 0..5)
    DENSITY = (0.0, 0.45, 0.7, 1.0, 1.25, 1.6)

    def __init__(self):
        self.configure()

    @staticmethod
    def _lvl(v, default):
        try:
            return max(0, min(5, int(round(float(v)))))
        except (TypeError, ValueError):
            return default

    def configure(self, level=5, mspeed=3, freq=3, espeed=3, seed=0):
        self.level = self._lvl(level, 5)
        self.mspeed = self._lvl(mspeed, 3)
        self.freq = self._lvl(freq, 3)
        self.espeed = self._lvl(espeed, 3)
        if self.level == 0 and self.freq == 0:
            L, P = 1, 1
        elif self.level == 0:
            L, P = max(16, self.SPEED_P[self.espeed]), 0
        else:
            P = self.SPEED_P[self.mspeed]
            L = P if P >= 16 else 2 * P
        self.L = L
        self.km = (L // P) if P else 0
        self.ke = max(1, round(L / self.SPEED_P[self.espeed]))
        n = {0: 0, 1: 1, 2: 1, 3: max(1, round(L / 16)), 4: max(1, round(2 * L / 16)),
             5: max(1, round(3 * L / 16))}[self.freq]
        gate = {1: seed % 4 == 0, 2: seed % 2 == 0}.get(self.freq, True)
        self.n_ev = n if (gate and L > 1) else 0
        self.ev_len = min(self.EVENT_LEN[self.espeed], max(3, L // max(1, n)))
        self.g = 0
        self.stack = []
        self._cache = {}

    # --- clocks ---
    @property
    def fx(self):
        """Effects enabled at all (frequency > 0)."""
        return self.freq > 0 and self.L > 1

    def density(self):
        return self.DENSITY[self.freq]

    def mclock(self):
        return (self.g * FRAMES * self.km // self.L) % FRAMES if self.km else 0

    def m(self, tier, rest=0):
        """Design frame for a moving part of this tier (rest pose when the level is below it)."""
        return self.mclock() if self.level >= tier else rest

    def still(self, tier):
        return self.level < tier

    def e(self):
        """Continuous effect clock (design frames)."""
        return (self.g * FRAMES * self.ke // self.L) % FRAMES if self.fx else 0

    def event(self, salt=0):
        """Progress 0..1 of an effect event happening now (glint sweep, glitch...), else None."""
        key = (self.g, salt)
        if key in self._cache:
            return self._cache[key]
        out = None
        for i in range(self.n_ev):
            start = (i * self.L) // self.n_ev + salt * 3
            k = (self.g - start) % self.L
            if k < self.ev_len:
                out = k / max(1, self.ev_len - 1)
                break
        self._cache[key] = out
        return out


MO = Motion()


def glint_pos(f, width, salt=0):
    """Highlight sweep position across a value while an effect event runs, else None."""
    p = MO.event(salt)
    if p is None:
        return None
    return -4 + (width + 8) * p


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
    c = AQI_STOPS[-1][1]
    for (a0, c0), (a1, c1) in zip(AQI_STOPS, AQI_STOPS[1:]):
        if a <= a1:
            c = mix(c0, c1, (a - a0) / (a1 - a0))
            break
    _SEMANTIC.add(tuple(int(v) for v in c))
    return c


def aqi_gauge(cv, a, f):
    """60-px pill gauge: lit up to the current value (with a travelling shine), the rest of the
    scale stays visible in its own colours but dimmed and dotted, plus a pointer under the value."""
    X0, W, Y = 2, 60, 34
    mx = None if a is None else X0 + int(min(max(a, 0), 299) * W / 300)
    shine = None
    if mx is not None and mx > X0:
        sp = MO.event(1)
        shine = None if sp is None else X0 + int(sp * (mx - X0 + 8)) - 4
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
    wm = APPLIANCE_STATES.get(str(d.get("wm")), ("--", "off"))[1]
    td = APPLIANCE_STATES.get(str(d.get("td")), ("--", "off"))[1]
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
    """Theme decorations. Particles/sweeps are effects (follow the effect settings); static
    ornaments (rivets, light strings, coin) stay even when effects are off."""
    f = MO.e()
    fx = MO.fx
    dens = MO.density()

    def nn(n):
        return max(1, round(n * dens))
    if DECOR == "christmas":
        for x, y, h in (_field(f, nn(3), 1) if fx else ()):
            wob = round(math.sin(2 * math.pi * f / FRAMES + h))
            cv.behind(x + wob, y, (170, 185, 210) if h % 3 else (230, 240, 255))
        cols = [(255, 40, 40), (40, 255, 80), (255, 200, 40), (60, 140, 255)]
        for (x, y, w, h) in cv.tiles:
            for n, i in enumerate(range(x + 2, x + w - 1, 4)):
                c = cols[(n + f // 4) % 4]
                cv.px(i, y, c if (n + f // 2) % 3 else shade(c, -0.5))
    elif DECOR == "embers":
        for x, y, h in (_field(f, nn(5), 2, speed=-1) if fx else ()):
            c = (255, 150, 40) if (f + h) % 4 else (255, 70, 10)
            cv.behind(x + round(math.sin(f * 0.8 + h)), y, shade(c, -0.2 * (h % 3)))
    elif DECOR == "bats":
        for x, y, h in _field(0, 2, 3):
            cv.behind(x, y, (190, 120, 255) if fx and (f + h) % 8 < 2 else (60, 30, 90))
        for n, by in enumerate((18 if page == "weather" else 31, 6)[:nn(2) if fx else 0]):
            bx = -8 + (f * 80 // FRAMES + n * 37) % 80
            rows = BAT_UP if (f // 2 + n) % 2 else BAT_DOWN
            for j, r in enumerate(rows):
                for i, ch in enumerate(r):
                    if ch == "#":
                        cv.behind(bx + i, by + j, (150, 80, 230))
    elif DECOR == "synth":
        for x, y, h in _field(0, 2, 4):
            cv.behind(x, y, (90, 240, 255) if fx and (f + h) % 8 < 2 else (70, 20, 90))
        sy = (f * 4) % 64 if fx else -9
        for x in range(64 if fx else 0):
            cv.behind(x, sy, shade(TILE, 0.45))
            cv.behind(x, sy - 1, shade(TILE, 0.2))
    elif DECOR == "steel":
        # rivets in the plate corners + a specular glint sliding along every top bevel
        for (x, y, w, h) in cv.tiles:
            for (rx, ry) in ((x + 2, y + 2), (x + w - 3, y + 2), (x + 2, y + h - 3), (x + w - 3, y + h - 3)):
                if all(cv.is_bg(rx + dx, ry + dy) for dx in (-1, 0, 1, 2) for dy in (-1, 0, 1, 2)):
                    cv.px(rx, ry, (175, 185, 200)); cv.px(rx + 1, ry + 1, (12, 13, 16))
            pos = x + (f * (w + 10) // FRAMES) - 5 if fx else -99
            for d in range(-2, 3):
                if x <= pos + d < x + w:
                    cv.px(pos + d, y, mix(BEV_TOP, (255, 255, 255), 1 - abs(d) / 3))
            ly = y + (f * (h + 6) // FRAMES) - 3 if fx else -99
            for d in range(-1, 2):
                if y <= ly + d < y + h:
                    cv.px(x, ly + d, mix(BEV_LEFT, (255, 255, 255), 0.7 - abs(d) * 0.3))
    elif DECOR == "coins":
        # drifting clouds in the sky gaps + a spinning coin in the AQI tile
        for x0, y0 in (((5, 24), (40, 39), (22, 9 if page == "weather" else 24)) if fx else ()):
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
    w = d.get("weather") if isinstance(d.get("weather"), dict) else {}
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

    fc = d.get("forecast") if isinstance(d.get("forecast"), list) else []
    fc = [x for x in fc if isinstance(x, dict)]
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
        label, k = APPLIANCE_STATES.get(str(d.get(key)), ("--", "off"))
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
    """Diagonal gold shimmer band crossing the surface while an effect event runs."""
    p = MO.event(2)
    if p is None:
        return False
    pos = (x + y - p * (width + 8) + 4) % (width + 8)
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
                    if ch == "T" and MO.fx and (MO.e() // 2 + cx + cy) % 16 == 0:
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


# ============================================================================
# FX DESIGNS  (digital_rain, block_3d, hud) - new fonts + new layouts
# ============================================================================
def _scale_glyphs(src, sx, sy_rows=None):
    """Build a new bitmap font from pico: sx = horizontal scale, sy_rows = per-source-row repeat."""
    out = {}
    for ch, (gw, gh, m) in _GLYPHS[src].items():
        reps = sy_rows or [2] * gh
        rows = []
        for j in range(gh):
            row = [b for b in m[j] for _ in range(sx)]
            rows += [row] * (reps[j] if j < len(reps) else 1)
        out[ch] = (gw * sx, len(rows), rows)
    return out


_GLYPHS["block"] = _scale_glyphs("pico", 2, [2, 2, 2, 2, 2])          # 6x10 chunky
_GLYPHS["tall"] = _scale_glyphs("pico", 1, [1, 2, 1, 2, 1])           # 3x7 terminal


SEG = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
       "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", " ": "",
       "E": "afged", "R": "eg", "H": "fbgec", "L": "fed", "O": "abcdef", "F": "afge", "P": "abfge"}


def seg_width(s, w=5, gap=2, t=1):
    n = 0
    for ch in str(s):
        n += (t + gap) if ch in ".:" else (w - 1 if ch == "°" else w + gap)
    return n - gap


def seg7(cv, x, y, s, w=5, h=9, t=1, color=(0, 230, 255), dim=None, glow=None, gap=2, align="left"):
    """Seven-segment digits. dim = colour of unlit segments; glow = 1-px halo colour."""
    s = str(s)
    total = seg_width(s, w, gap, t)
    if align == "center": x -= total // 2
    elif align == "right": x -= total
    m = (h - t) // 2
    pts_on, pts_off = [], []
    cx = x
    for ch in s:
        if ch in ".:":
            if ch == ".":
                pts_on += [(cx + i, y + h - t + j) for i in range(t) for j in range(t)]
            else:
                for yy in (y + h // 3, y + 2 * h // 3):
                    pts_on += [(cx + i, yy + j) for i in range(t) for j in range(t)]
            cx += t + gap
            continue
        if ch == "°":
            for (i, j) in ((0, 0), (1, 0), (2, 0), (0, 1), (2, 1), (0, 2), (1, 2), (2, 2)):
                pts_on.append((cx + i, y + j))
            cx += w - 1
            continue
        segs = {
            "a": [(cx + i, y + j) for i in range(t, w - t) for j in range(t)],
            "d": [(cx + i, y + h - t + j) for i in range(t, w - t) for j in range(t)],
            "g": [(cx + i, y + m + j) for i in range(t, w - t) for j in range(t)],
            "f": [(cx + i, y + j) for i in range(t) for j in range(t, m + 1)],
            "b": [(cx + w - t + i, y + j) for i in range(t) for j in range(t, m + 1)],
            "e": [(cx + i, y + j) for i in range(t) for j in range(m + t - 1, h - t)],
            "c": [(cx + w - t + i, y + j) for i in range(t) for j in range(m + t - 1, h - t)],
        }
        lit = SEG.get(ch.upper(), "")
        for k, p in segs.items():
            (pts_on if k in lit else pts_off).extend(p)
        cx += w + gap
    prev, cv._protect = cv._protect, True
    if dim is not None:
        for p in pts_off:
            cv.px(*p, dim)
    if glow is not None:
        on = set(pts_on)
        for (px_, py_) in pts_on:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (px_ + dx, py_ + dy)
                if q not in on:
                    cv.px(*q, mix(cv.get(*q), glow, 0.6))
    for p in pts_on:
        cv.px(*p, color)
    cv._protect = prev
    return total


def ext_text(cv, x, y, s, face, font="block", depth=3, side=None, align="left", grad=None, d=(1, 1)):
    """Extruded 3D text: stacked darker copies give real depth, glossy gradient front face."""
    side = side or shade(face, -0.55)
    for k in range(depth, 0, -1):
        cv.text(x + k * d[0], y + k * d[1], s, shade(side, -0.12 * k), font, align, shadow=False)
    return cv.text(x, y, s, face, font, align, shadow=False,
                   grad=grad if grad is not None else [0.55, 0.4, 0.25, 0.1, 0, 0, -0.05, -0.12, -0.2, -0.28])


# ----------------------------------------------------------------------------
# HUD  - futuristic holographic interface: ring gauges, radar, 7-segment digits, line chart
# ----------------------------------------------------------------------------
H_BG, H_C1, H_C2, H_C3 = (0, 5, 14), (0, 230, 255), (0, 95, 125), (0, 34, 48)
H_MG, H_AM, H_W, H_RD = (255, 60, 190), (255, 185, 40), (215, 250, 255), (255, 60, 60)


def hud_bg(cv, f):
    if not cv.bgl:
        cv.rect(0, 0, 64, 64, H_BG)
    for y in range(1, 64, 4):
        for x in range(1 + (y // 4) % 2 * 2, 64, 4):
            cv.px(x, y, H_C3)
    sy = (MO.e() * 64 // FRAMES) % 64                               # scan line sweeping down
    for x in range(64 if MO.fx else 0):
        cv.px(x, sy, mix(cv.get(x, sy), H_C1, 0.35))
        cv.px(x, sy - 1, mix(cv.get(x, sy - 1), H_C1, 0.15))


def hud_glitch(cv, f):
    p = MO.event(3)
    k = None if p is None else round(p * (MO.ev_len - 1))
    if k in (0, 1):                                                 # brief holographic glitch
        y0 = 27 if k == 0 else 48
        row = [[cv.get(x, y) for x in range(64)] for y in range(y0, y0 + 2)]
        for j, r in enumerate(row):
            for x in range(64):
                cv.px((x + 2) % 64, y0 + j, mix(r[x], H_MG, 0.25))


def bracket(cv, x, y, w, h, c, L=3):
    for (cx, cy, dx, dy) in ((x, y, 1, 1), (x + w - 1, y, -1, 1), (x, y + h - 1, 1, -1), (x + w - 1, y + h - 1, -1, -1)):
        for i in range(L):
            cv.px(cx + dx * i, cy, c); cv.px(cx, cy + dy * i, c)


def hud_ring(cv, cx, cy, r, frac, f, color, ticks=True):
    """270-degree arc gauge with glowing tip and a rotating outer tick ring."""
    a0, sweep = math.radians(135), math.radians(270)
    n = int(2 * math.pi * r * 1.6)
    for k in range(n + 1):
        a = a0 + sweep * k / n
        x, y = round(cx + r * math.cos(a)), round(cy + r * math.sin(a))
        lit = frac is not None and k / n <= frac
        cv.px(x, y, color if lit else H_C3)
    if frac is not None:
        a = a0 + sweep * max(0, min(1, frac))
        tx, ty = round(cx + r * math.cos(a)), round(cy + r * math.sin(a))
        g = pulse(f, 0.4, 1.0)
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            cv.px(tx + dx, ty + dy, mix(color, H_W, g) if (dx, dy) == (0, 0) else mix(cv.get(tx + dx, ty + dy), color, 0.6))
    if ticks:
        rot = 2 * math.pi * f / FRAMES / 4
        for k in range(12):
            a = rot + k * math.pi / 6
            if k % 3 == 0:
                continue
            cv.px(round(cx + (r + 2) * math.cos(a)), round(cy + (r + 2) * math.sin(a)), H_C2)


def hud_tcolor(v, scale):
    if v is None: return H_C2
    return {BLUE: (80, 160, 255), CYAN: H_C1, GREEN: (60, 255, 170), AMBER: H_AM, RED: H_RD}[temp_color(v, *scale)]


@protects
def hud_wire_icon(cv, x, y, kind, k, f):
    c = H_C1 if k not in ("idle", "off") else H_C2
    ang = 2 * math.pi * f / FRAMES
    if kind in ("washer", "dryer"):
        for i in range(11):
            cv.px(x + i, y, c); cv.px(x + i, y + 10, c); cv.px(x, y + i, c); cv.px(x + 10, y + i, c)
        cv.rect(x + 1, y + 2, 9, 1, H_C3 if k in ("idle", "off") else H_C2)
        for n in range(20):
            t = 2 * math.pi * n / 20
            cv.px(round(x + 5 + 3 * math.cos(t)), round(y + 6 + 3 * math.sin(t)), c)
        if k == "run":
            for q in range(3):
                t = ang * 2 + q * 2.1
                cv.px(round(x + 5 + 1.7 * math.cos(t)), round(y + 6 + 1.7 * math.sin(t)),
                      H_W if kind == "washer" else H_AM)
    else:
        for i in range(11):
            cv.px(x + i, y, c); cv.px(x, y + i, c); cv.px(x + 10, y + i, c)
        cv.rect(x, y + 10, 11, 1, c)
        cv.rect(x + 1, y + 3, 9, 1, H_C2)
        hx = x + 3 + (round(2 + 2 * math.sin(ang)) if k == "run" else 2)
        cv.rect(hx, y + 4, 3, 1, H_AM if k == "run" else c)
        if k == "run" and f % 2 == 0:
            cv.px(hx + 1, y + 5, H_W)
        cv.rect(x + 3, y + 8, 5, 2, c)


def hud_umbrella(cv, x, y, out, f):
    if out is None:
        return
    rain = out[0]
    c = H_C1 if rain else H_C2
    for i in range(9):
        h = int(3.2 * math.sin(math.pi * (i + 0.5) / 9))
        cv.px(x + i, y + 3 - h, c)
    cv.rect(x, y + 3, 9, 1, c)
    cv.rect(x + 4, y + 4, 1, 4, c); cv.px(x + 3, y + 7, c)
    if rain:
        for n, dx in enumerate((0, 3, 6, 9)):
            yy = y - 2 + (f + n * 3) % 5
            if yy < y - 0:
                cv.px(x + dx, yy, H_W)
    else:
        cv.px(x + 4, y - 1 + (f // 4) % 2, H_AM)


def _hhmm(s):
    try:
        h, m = str(s).split(":")[:2]
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def hud_sun_arc(cv, d, f, y0=44):
    """Sun travelling along a dashed day-arc between sunrise and sunset (real position)."""
    rise, sett, now = _hhmm(d.get("sunrise")), _hhmm(d.get("sunset")), _hhmm(d.get("time"))
    cx, cy, R = 32, 61, 22
    bracket(cv, 0, y0, 64, 64 - y0, H_C2)
    cv.rect(2, cy, 60, 1, H_C2)                                     # horizon
    for k in range(48):
        a = math.pi + math.pi * k / 47
        if k % 2 == 0:
            cv.px(round(cx + R * math.cos(a)), round(cy + R * 0.75 * math.sin(a)), H_C3)
    day = rise is not None and sett is not None and now is not None and rise <= now <= sett
    if rise is not None and sett is not None and now is not None:
        if day:
            p = (now - rise) / max(1, sett - rise)
        else:
            span = (rise + 1440 - sett) % 1440 or 1
            p = ((now - sett) % 1440) / span
        a = math.pi + math.pi * p
        for k in range(int(48 * p)):
            aa = math.pi + math.pi * k / 47
            if k % 2 == 0:
                cv.px(round(cx + R * math.cos(aa)), round(cy + R * 0.75 * math.sin(aa)), H_AM if day else H_C2)
        sx, sy = cx + R * math.cos(a), cy + R * 0.75 * math.sin(a)
        if day:
            disc(cv, sx, sy, 2.4, lambda t, i, j: mix((255, 250, 200), H_AM, t))
            for n in range(8):
                aa = n * math.pi / 4 + f * math.pi / 4 / FRAMES * 2
                cv.px(round(sx + 4 * math.cos(aa)), round(sy + 4 * math.sin(aa)), H_AM if n % 2 else (255, 230, 150))
        else:
            disc(cv, sx, sy, 2.2, lambda t, i, j: (200, 220, 240) if i < sx + 0.6 else H_BG)
    tri(cv, 3, 50, UP[0], H_AM)
    cv.text(3, 55, str(d.get("sunrise") or "--:--"), H_AM, shadow=False)
    tri(cv, 56, 50, DOWN[0], H_MG)
    cv.text(61, 55, str(d.get("sunset") or "--:--"), H_MG, align="right", shadow=False)


def render_dashboard_hud(d, f, variant=0):
    cv = Canvas()
    hud_bg(cv, f)
    for cx, label, v, h, scale, lo, hi in [(15, "IN", num(d.get("t_in")), d.get("h_in"), IN_SCALE, 10, 35),
                                           (48, "OUT", num(d.get("t_out")), d.get("h_out"), OUT_SCALE, -15, 40)]:
        col = hud_tcolor(v, scale)
        frac = None if v is None else (v - lo) / (hi - lo)
        hud_ring(cv, cx, 16, 13, frac, f, col)
        cv.text(cx, 7, label, H_C2, align="center", shadow=False)
        if v is not None:
            s = ("%.1f" % v) if -10 < v < 100 else "%d" % round(v)
            seg7(cv, cx, 13, s, w=4, h=7, t=1, gap=1, color=col, dim=mix(H_BG, col, 0.12),
                 glow=mix(H_BG, col, 0.35), align="center")
        hv = num(h)
        if hv is not None:
            cv.text(cx, 23, "%d%%" % round(hv), (90, 200, 255), align="center", shadow=False)
    # AQI strip
    a = num(d.get("aqi"))
    bracket(cv, 0, 33, 64, 10, H_C2, 2)
    cv.text(2, 36, "AQI", H_C2, shadow=False)
    if a is not None:
        col = aqi_color(a)
        cv.text(14, 36, str(int(round(a))), col, shadow=False)
        lit = int(min(a, 299) / 300 * 10) + 1
        for i in range(10):
            c = aqi_color(i * 30 + 15)
            x = 27 + i * 2
            on = i < lit
            cc = c if on else mix(H_BG, c, 0.22)
            if on and i == lit - 1 and (f // 2) % 2:
                cc = mix(c, H_W, 0.6)
            cv.rect(x, 35, 1, 5, cc)
    hud_umbrella(cv, 49, 36, rain_outlook(d), f)
    # bottom
    if show_sun_card(d, variant):
        hud_sun_arc(cv, d, f)
    else:
        for x, a2 in zip((0, 22, 43), appl_list(d)):
            bracket(cv, x, 45, 21, 19, H_C2)
            hud_wire_icon(cv, x + 5, 46, a2["kind"], a2["k"], f)
            c = {"run": H_C1, "done": (60, 255, 170), "err": H_RD, "pause": H_AM}.get(a2["k"], H_C2)
            if a2["k"] == "err" and (f // 4) % 2:
                c = H_C3
            cv.text(x + 10, 58, a2["label"], c, align="center", shadow=False)
            if a2["kind"] == "printer" and a2["pct"] is not None and a2["k"] in ("run", "pause"):
                n = round(19 * max(0, min(100, a2["pct"])) / 100)
                cv.rect(x + 1, 63, 19, 1, H_C3); cv.rect(x + 1, 63, n, 1, H_C1)
    hud_glitch(cv, f)
    return cv.img


def hud_cond_icon(cv, cx, cy, grp, f, s=1.0):
    ph = 2 * math.pi * f / FRAMES
    if grp in ("sun", "partly"):
        sx, sy = (cx, cy) if grp == "sun" else (cx - 3 * s, cy - 3 * s)
        for n in range(24):
            t = 2 * math.pi * n / 24
            cv.px(round(sx + 3.5 * s * math.cos(t)), round(sy + 3.5 * s * math.sin(t)), H_AM)
        for n in range(8):
            t = n * math.pi / 4 + ph / 4
            L = 5.5 * s + (1 if (n + f // 4) % 2 else 0)
            cv.px(round(sx + L * math.cos(t)), round(sy + L * math.sin(t)), H_AM)
    if grp == "night":
        for n in range(30):
            t = 2 * math.pi * n / 30
            x, y = cx + 4 * s * math.cos(t), cy + 4 * s * math.sin(t)
            if math.hypot(x - (cx + 2.2 * s), y - (cy - 1.5 * s)) > 3.6 * s:
                cv.px(round(x), round(y), (200, 220, 255))
    if grp in ("partly", "cloud", "rain", "snow", "storm"):
        ox = cx + (2 * s if grp == "partly" else 0) + round(math.sin(ph))
        oy = cy + (1 * s if grp == "partly" else -1)
        pts = []
        for n in range(40):
            t = 2 * math.pi * n / 40
            for (bx, by, r) in ((-3, 0, 2.6), (0, -2, 3.2), (3, 0, 2.6)):
                x, y = ox + (bx + r * math.cos(t)) * s, oy + (by + r * math.sin(t)) * s
                inside = any(math.hypot(x - (ox + bx2 * s), y - (oy + by2 * s)) < r2 * s - 0.4
                             for (bx2, by2, r2) in ((-3, 0, 2.6), (0, -2, 3.2), (3, 0, 2.6)))
                if not inside and y <= oy + 2.6 * s:
                    pts.append((round(x), round(y)))
        for p in pts:
            cv.px(*p, H_C1 if grp != "storm" else H_C2)
        cv.rect(round(ox - 5.5 * s), round(oy + 2.6 * s), round(11 * s), 1, H_C1 if grp != "storm" else H_C2)
        if grp in ("rain", "snow", "storm"):
            for n in range(4):
                xx = round(ox - 4 * s + n * 2.7 * s)
                yy = round(oy + 4 * s) + (f // (2 if grp == "snow" else 1) + n * 2) % max(2, round(4 * s))
                cv.px(xx, yy, H_W if grp == "snow" else H_C1)
                if grp == "rain" and s > 1:
                    cv.px(xx, yy - 1, H_C2)
            if grp == "storm" and f % 8 < 3:
                for j, dx in enumerate((1, 0, -1, 0, 1)):
                    cv.px(round(ox + dx), round(oy + 3 * s) + j, H_AM)
    if grp in ("fog", "wind"):
        for n in range(3):
            y = round(cy - 3 * s + n * 3 * s)
            for i in range(round(9 * s)):
                if (i + f * (1 if grp == "wind" else 0) + n * 3) % 6 < 4:
                    cv.px(round(cx - 4.5 * s) + i, y, H_C1)


def render_weather_hud(d, f):
    cv = Canvas()
    hud_bg(cv, f)
    bracket(cv, 0, 0, 64, 12, H_C2)
    cv.text(2, 4, str(d.get("date", "")), H_C2, shadow=False)
    seg7(cv, 32, 2, str(d.get("time", "")), w=5, h=8, t=1, gap=2, color=H_C1, dim=(0, 22, 32),
         glow=(0, 60, 80), align="center")
    cv.text(62, 4, str(d.get("dow", "")), H_MG, align="right", shadow=False)
    # radar with condition hologram
    rcx, rcy = 13, 25
    sweep = 2 * math.pi * f / FRAMES
    for rr in (11, 7):
        for n in range(int(rr * 7)):
            t = 2 * math.pi * n / (rr * 7)
            cv.px(round(rcx + rr * math.cos(t)), round(rcy + rr * math.sin(t)), H_C3 if rr == 7 else H_C2)
    for k in range(6):
        a = sweep - k * 0.18
        for r in range(1, 11):
            x, y = round(rcx + r * math.cos(a)), round(rcy + r * math.sin(a))
            cv.px(x, y, mix(cv.get(x, y), H_C1, 0.5 - k * 0.08))
    hud_cond_icon(cv, rcx, rcy, cond_group(cur_cond(d)), f, 1.15)
    v = cur_temp(d)
    col = hud_tcolor(v, OUT_SCALE)
    if v is not None:
        s = ("%.1f" % v) if -10 < v < 100 else "%d" % round(v)
        seg7(cv, 44, 15, s + "°", w=6, h=11, t=1, gap=2, color=col, dim=mix(H_BG, col, 0.12),
             glow=mix(H_BG, col, 0.35), align="center")
    today, nxt = today_and_next(d)
    if today:
        hi, lo = num(today.get("hi")), num(today.get("lo"))
        if hi is not None:
            tri(cv, 28, 30, UP[0], H_AM); cv.text(34, 29, "%d" % round(hi), H_AM, shadow=False)
        if lo is not None:
            tri(cv, 46, 30, DOWN[0], H_C1); cv.text(52, 29, "%d" % round(lo), H_C1, shadow=False)
    # 4-day forecast as a glowing line chart
    bracket(cv, 0, 38, 64, 26, H_C2)
    pts = []
    for n, day in enumerate(nxt[:4]):
        pts.append((8 + n * 16, num(day.get("hi")), num(day.get("lo")), day))
    vals = [v2 for p in pts for v2 in (p[1], p[2]) if v2 is not None]
    if vals:
        tmin, tmax = min(vals), max(vals)
        rng = max(1.0, tmax - tmin)
        ymap = lambda t: round(51 - (t - tmin) / rng * 6)
        for key, colr in ((1, H_AM), (2, H_C1)):
            prev = None
            for p in pts:
                if p[key] is None:
                    prev = None
                    continue
                cur = (p[0], ymap(p[key]))
                if prev:
                    n_ = max(abs(cur[0] - prev[0]), 1)
                    for t in range(n_ + 1):
                        x = prev[0] + (cur[0] - prev[0]) * t / n_
                        y = prev[1] + (cur[1] - prev[1]) * t / n_
                        cv.px(round(x), round(y), mix(H_BG, colr, 0.55))
                prev = cur
            for i, p in enumerate(pts):
                if p[key] is None:
                    continue
                y = ymap(p[key])
                bright = (f // 2) % 4 == i
                cv.rect(p[0] - 1, y - 1, 3, 3, mix(colr, H_W, 0.5) if bright else colr)
        for p in pts:
            if p[1] is not None:
                cv.text(p[0], 39, "%d" % round(p[1]), H_AM, align="center", shadow=False)
            if p[2] is not None:
                cv.text(p[0], 53, "%d" % round(p[2]), H_C1, align="center", shadow=False)
            day = p[3]
            weekend = int(num(day.get("wd")) or 0) in (6, 7)
            cv.text(p[0] - 2, 59, str(day.get("d", ""))[:2], H_MG if weekend else (110, 200, 230), align="center", shadow=False)
            hud_cond_icon(cv, p[0] + 5, 61, cond_group(day.get("c")), f, 0.42)
    hud_glitch(cv, f)
    return cv.img


# ----------------------------------------------------------------------------
# BLOCK 3D  - deep perspective room, extruded numbers, isometric boxes, shaded spheres, 3D bars
# ----------------------------------------------------------------------------
B_WALL_T, B_WALL_B = (22, 12, 58), (60, 20, 90)
B_FLOOR, B_GRID = (14, 8, 34), (150, 60, 200)
B_LIGHT = (-0.55, -0.65, 0.52)          # light from top-left-front


def b_room(cv, f, horizon=40):
    for y in range(64):
        if y < horizon:
            if not cv.bgl:
                cv.rect(0, y, 64, 1, mix(B_WALL_T, B_WALL_B, y / horizon))
        else:
            cv.rect(0, y, 64, 1, mix(B_FLOOR, (40, 14, 70), (y - horizon) / (64 - horizon) * 0.5))
    cv.rect(0, horizon, 64, 1, (230, 120, 255))                      # glowing horizon
    vx = 32
    for k in range(-9, 10):                                          # converging floor lines
        x_far = vx + k * 4
        x_near = vx + k * 16
        for y in range(horizon + 1, 64):
            t = (y - horizon) / (64 - horizon)
            x = round(x_far + (x_near - x_far) * t)
            if 0 <= x < 64:
                cv.px(x, y, mix(cv.get(x, y), B_GRID, 0.35 + 0.4 * t))
    for n in range(6):                                               # rows rushing toward viewer
        t = ((n + f / FRAMES) / 6) ** 2
        y = round(horizon + 1 + t * (64 - horizon))
        if y < 64:
            for x in range(64):
                cv.px(x, y, mix(cv.get(x, y), B_GRID, 0.25 + 0.5 * t))


def sphere(cv, cx, cy, r, base, spec=True, rim=None):
    """Lambert-shaded sphere with specular highlight."""
    lx, ly, lz = B_LIGHT
    for j in range(int(cy - r) - 1, int(cy + r) + 2):
        for i in range(int(cx - r) - 1, int(cx + r) + 2):
            dx, dy = (i + 0.5 - cx) / r, (j + 0.5 - cy) / r
            q = dx * dx + dy * dy
            if q > 1:
                continue
            dz = math.sqrt(1 - q)
            lam = max(0.0, dx * lx + dy * ly + dz * lz)
            c = shade(base, -0.75 + 1.05 * lam)
            if spec:
                sp = max(0.0, lam) ** 18
                c = mix(c, (255, 255, 255), min(1, sp * 1.2))
            if rim and q > 0.8:
                c = mix(c, rim, 0.35)
            cv.px(i, j, c)


def iso_box(cv, x, y, w, h, dep, front, top=None, side=None):
    """Front face (w x h) at x,y with a top face and right face receding up-right by dep px."""
    top = top or shade(front, 0.35)
    side = side or shade(front, -0.45)
    for k in range(1, dep + 1):
        cv.rect(x + k, y - k, w, 1, top)
        cv.rect(x + w - 1 + k, y - k + 1, 1, h, side)
    cv.rect(x, y, w, h, front)


def floor_shadow(cv, x, y, w):
    for i in range(w + 4):
        xx = x + i - 1
        cv.px(xx, y, mix(cv.get(xx, y), (0, 0, 0), 0.55))
        cv.px(xx + 1, y + 1, mix(cv.get(xx + 1, y + 1), (0, 0, 0), 0.3))


def b_temp_face(v, scale):
    if v is None: return (150, 150, 170)
    return {BLUE: (90, 160, 255), CYAN: (60, 230, 255), GREEN: (90, 255, 140), AMBER: (255, 200, 60),
            RED: (255, 80, 70)}[temp_color(v, *scale)]


def b_appliance(cv, x, y, a, f):
    """Isometric appliance box standing on the floor, x,y = front-face top-left (11x11)."""
    k, kind = a["k"], a["kind"]
    on = k == "run"
    front = (235, 235, 245) if k not in ("idle", "off") else (120, 120, 140)
    floor_shadow(cv, x, y + 11, 13)
    iso_box(cv, x, y, 11, 11, 3, front)
    ang = 2 * math.pi * f / FRAMES
    if kind in ("washer", "dryer"):
        cv.rect(x + 1, y + 1, 3, 1, shade(front, -0.3))
        cv.px(x + 9, y + 1, (60, 255, 120) if on and (f // 4) % 2 else shade(front, -0.4))
        glass = (40, 140, 255) if kind == "washer" else (255, 130, 30)
        for j in range(11):
            for i in range(11):
                d0 = math.hypot(i - 5, j - 6)
                if 2.9 < d0 <= 3.9:
                    cv.px(x + i, y + j, shade(front, -0.5))
                elif d0 <= 2.9:
                    if on:
                        t = math.atan2(j - 6, i - 5)
                        c = glass if math.sin(2 * t - 3 * ang) > 0 else shade(glass, 0.35)
                    else:
                        c = (40, 40, 55)
                    if (i, j) == (4, 5):
                        c = (255, 255, 255)
                    cv.px(x + i, y + j, c)
    else:
        win = {"run": (30, 120, 70), "pause": (130, 100, 10), "done": (30, 140, 70), "err": (160, 30, 30)}.get(k, (40, 40, 60))
        cv.rect(x + 2, y + 2, 7, 7, win)
        hx = x + 3 + (round(2 + 2 * math.sin(ang)) if on else 2)
        cv.rect(hx, y + 3, 3, 1, (255, 255, 255))
        ph = 1 + (round(3 * max(0, min(100, a["pct"])) / 100) if a["pct"] is not None and k in ("run", "pause") else 1)
        cv.rect(x + 4, y + 9 - ph, 3, ph, (255, 220, 120))


def b_label_color(k):
    return {"run": (90, 220, 255), "done": (110, 255, 140), "err": (255, 80, 70), "pause": (255, 200, 60),
            "prep": (90, 220, 255)}.get(k, (170, 150, 200))


def render_dashboard_block_3d(d, f, variant=0):
    cv = Canvas()
    b_room(cv, f)
    # floating extruded temperatures with labels
    for x, v, h, sprite, scale in [(1, num(d.get("t_in")), d.get("h_in"), HOUSE, IN_SCALE),
                                   (33, num(d.get("t_out")), d.get("h_out"), TREE, OUT_SCALE)]:
        cv.sprite(x + 1, 1, *sprite)
        hv = num(h)
        if hv is not None:
            ext_text(cv, x + 28, 2, "%d%%" % round(hv), (120, 210, 255), "pico", depth=1, align="right",
                     grad=[0.4, 0.2, 0, -0.1, -0.2])
        s = temp_str(v)
        if s:
            bob = round(math.sin(2 * math.pi * f / FRAMES + (0 if x == 1 else 2)))
            ext_text(cv, x + 14, 10 + bob, s, b_temp_face(v, scale), "block", depth=2, align="center")
    # AQI: value + five isometric cubes, the current one floating
    a = num(d.get("aqi"))
    if a is not None:
        col = aqi_color(a)
        ext_text(cv, 2, 27, str(int(round(a))), col, "block", depth=2)
        cat = 0 if a < 50 else 1 if a < 101 else 2 if a < 151 else 3 if a < 201 else 4
        for i in range(5):
            c = aqi_color(i * 50 + 25)
            lift = round(2 + 1.5 * math.sin(2 * math.pi * f / FRAMES)) if i == cat else 0
            x, y = 26 + i * 6, 32 - lift
            if i == cat:
                floor_shadow(cv, x, 37, 4)
            iso_box(cv, x, y, 4, 4, 2, c if i <= cat else shade(c, -0.7))
    out = rain_outlook(d)
    if out is not None:
        ux, uy = 57, 30
        if out[0]:
            for j in range(-6, 1):                                   # shaded dome canopy
                for i in range(-6, 7):
                    if i * i + (j * 1.6) ** 2 <= 36:
                        dx, dy = i / 6, j / 6
                        lam = max(0, -0.6 * dx - 0.7 * dy + 0.4)
                        cv.px(ux + i, uy + j, shade((60, 140, 255), -0.5 + lam))
            cv.rect(ux, uy + 1, 1, 6, (220, 220, 230)); cv.px(ux - 1, uy + 6, (220, 220, 230))
            for n, dx in enumerate((-6, 6, -3)):
                yy = uy + 1 + (f + n * 4) % 7
                sphere(cv, ux + dx, yy, 0.9, (120, 190, 255), spec=False)
        else:
            sphere(cv, ux, uy - 1, 4.2, (255, 190, 40))
    # bottom row
    if show_sun_card(d, variant):
        for x, rising, t in [(16, True, d.get("sunrise")), (48, False, d.get("sunset"))]:
            prog = f / (FRAMES - 1)
            sy = (46 - 4 * prog) if rising else (42 + 4 * prog)
            sphere(cv, x, sy, 5, (255, 170, 40) if rising else (255, 90, 50), rim=(255, 230, 150))
            cv.rect(x - 14, 40, 29, 1, (230, 120, 255))
            ext_text(cv, x, 53, str(t or "--:--"), (255, 210, 90) if rising else (255, 140, 110),
                     "tall", depth=2, align="center", grad=[0.5, 0.35, 0.2, 0.05, -0.1, -0.2, -0.3])
    else:
        for x, a2 in zip((3, 25, 47), appl_list(d)):
            b_appliance(cv, x, 44, a2, f)
            ext_text(cv, x + 6, 58, a2["label"], b_label_color(a2["k"]), "pico", depth=1, align="center",
                     grad=[0.4, 0.2, 0, -0.1, -0.2])
    return cv.img


def b_icon(cv, cx, cy, grp, f, s=1.0):
    ph = 2 * math.pi * f / FRAMES
    drift = math.sin(ph) * 1.5 * s

    def puffs(ox, oy, base, dark=False):
        for (bx, by, r) in ((-3.5, 1, 3.2), (3.5, 1.5, 2.8), (0, -1.5, 4.0)):
            sphere(cv, ox + bx * s, oy + by * s, r * s, base if not dark else (90, 90, 120), spec=not dark)

    if grp in ("sun", "partly"):
        sx, sy = (cx, cy) if grp == "sun" else (cx - 3 * s, cy - 3 * s)
        for n in range(8):
            a = n * math.pi / 4 + ph / 8
            for L in range(int(6 * s), int(8.5 * s) + (1 if (n + f // 4) % 2 else 0)):
                cv.px(round(sx + L * math.cos(a)), round(sy + L * math.sin(a)), (255, 200, 60))
        sphere(cv, sx, sy, 5 * s, (255, 170, 30), rim=(255, 240, 160))
        if grp == "partly":
            puffs(cx + 2 * s + drift, cy + 3 * s, (225, 230, 245))
    elif grp == "night":
        sphere(cv, cx, cy + math.sin(ph) * s, 5.5 * s, (210, 215, 230))
        for (dx, dy, r) in ((-1.5, -1.5, 1.1), (2, 1, 0.9), (-1, 2.5, 0.7)):
            disc(cv, cx + dx * s, cy + dy * s + math.sin(ph) * s, r * s, lambda t, i, j: (150, 155, 175))
    elif grp in ("cloud",):
        puffs(cx + 2 * s - drift, cy - 2 * s, (170, 175, 200))
        puffs(cx - 1 * s + drift, cy + 2 * s, (235, 238, 250))
    elif grp in ("rain", "snow", "storm"):
        puffs(cx + drift * 0.5, cy - 2 * s, (225, 230, 245), dark=(grp == "storm"))
        for n in range(4):
            xx = cx + (-5 + n * 3.4) * s
            yy = cy + 4 * s + ((f // (2 if grp == "snow" else 1) + n * 3) % 6) * s
            if grp == "snow":
                sphere(cv, xx, yy, 0.9 * s + 0.2, (255, 255, 255), spec=False)
            else:
                sphere(cv, xx, yy, 0.8 * s + 0.2, (90, 170, 255), spec=False)
        if grp == "storm" and f % 8 < 3:
            for j, dx in enumerate((1, 0, -1, 0, 1, 0)):
                cv.px(round(cx + dx), round(cy + 3 * s) + j, (255, 240, 120))
    elif grp in ("fog", "wind"):
        for n in range(3):
            y = round(cy - 4 * s + n * 4 * s)
            off = round(2 * math.sin(ph + n)) if grp == "fog" else (f + n * 3) % 6 - 3
            for i in range(round(12 * s)):
                cv.px(round(cx - 6 * s) + i + off, y, shade((200, 210, 235), 0.2 - 0.05 * n))
                cv.px(round(cx - 6 * s) + i + off + 1, y + 1, (60, 40, 90))


B_COND_COL = {"sun": (255, 190, 50), "partly": (230, 200, 120), "cloud": (170, 175, 200), "rain": (70, 150, 255),
              "snow": (235, 240, 255), "storm": (150, 90, 220), "night": (180, 190, 220), "fog": (160, 165, 180),
              "wind": (120, 220, 220), "unknown": (150, 150, 150)}


def render_weather_block_3d(d, f):
    cv = Canvas()
    b_room(cv, f, horizon=42)
    ext_text(cv, 32, 1, str(d.get("time", "")), (240, 240, 255), "block", depth=2, align="center")
    cv.text(1, 14, str(d.get("date", "")), (200, 160, 255), shadow=False)
    cv.text(62, 14, str(d.get("dow", "")), (255, 140, 200), align="right", shadow=False)
    b_icon(cv, 12, 28, cond_group(cur_cond(d)), f, 1.0)
    v = cur_temp(d)
    s = temp_str(v)
    if s:
        ext_text(cv, 44, 20, s, b_temp_face(v, OUT_SCALE), "block", depth=3, align="center")
    today, nxt = today_and_next(d)
    if today:
        hi, lo = num(today.get("hi")), num(today.get("lo"))
        if hi is not None:
            tri(cv, 28, 35, UP[0], (255, 160, 90))
            ext_text(cv, 34, 34, "%d°" % round(hi), (255, 160, 90), "pico", depth=1, grad=[0.4, 0.2, 0, -0.1, -0.2])
        if lo is not None:
            tri(cv, 46, 35, DOWN[0], (110, 190, 255))
            ext_text(cv, 52, 34, "%d°" % round(lo), (110, 190, 255), "pico", depth=1, grad=[0.4, 0.2, 0, -0.1, -0.2])
    # 3D bar chart: pillar height = day's high, colour = condition, low printed on the floor
    his = [num(x.get("hi")) for x in nxt if num(x.get("hi")) is not None]
    tmin = min(his) - 4 if his else 0
    tmax = max(his) if his else 1
    for n, day in enumerate(nxt[:4]):
        x = 4 + n * 15
        hi, lo = num(day.get("hi")), num(day.get("lo"))
        col = B_COND_COL[cond_group(day.get("c"))]
        hgt = 3 if hi is None else round(3 + 6 * (hi - tmin) / max(1.0, tmax - tmin))
        grow = 1.0 if MO.still(2) else min(1.0, (f + 1) / 6)          # bars grow in at loop start
        hgt = max(2, round(hgt * (0.6 + 0.4 * grow)))
        base = 58
        floor_shadow(cv, x, base, 8)
        iso_box(cv, x, base - hgt, 8, hgt, 3, col)
        if hi is not None:
            ext_text(cv, x + 5, base - hgt - 9, "%d" % round(hi), (255, 255, 255), "pico", depth=1,
                     align="center", grad=[0.3, 0.1, 0, -0.1, -0.2])
        weekend = int(num(day.get("wd")) or 0) in (6, 7)
        cv.text(x + 4, 59, str(day.get("d", ""))[:2], (255, 140, 200) if weekend else (220, 200, 255),
                align="center", shadow=False)
    return cv.img


# ----------------------------------------------------------------------------
# DIGITAL RAIN  - falling glyph code, terminal readouts, data "decoding" out of the rain
# ----------------------------------------------------------------------------
R_BG, R_HEAD, R_HI, R_MID, R_LOW = (0, 3, 0), (215, 255, 215), (60, 255, 110), (0, 170, 60), (0, 60, 22)
R_TXT, R_DIM, R_WARN = (140, 255, 160), (40, 150, 70), (255, 255, 255)


def _rglyph(seed):
    """Random 3x5 code glyph (looks like an alien alphabet, changes over time)."""
    h = _hash(seed, seed * 7, 99)
    rows = []
    for j in range(5):
        bits = (h >> (j * 3)) & 7
        if j == 0: bits |= 2
        rows.append(bits)
    return rows


def rain_bg(cv, f, density=1.0, speed_mix=True):
    if not cv.bgl:
        cv.rect(0, 0, 64, 64, R_BG)
    for col in range(16):
        x = col * 4
        hsh = _hash(col, 3, 17)
        if (hsh % 100) / 100 > density:
            continue
        period = 16 if (hsh % 3 or not speed_mix) else 8               # rows per loop: fast / slow
        trail = 5 + hsh % 6
        head = ((hsh % 16) + f * period // FRAMES) % 16                  # virtual 16-row column (96 px)
        for r in range(16):
            dist = (head - r) % 16
            if dist > trail:
                continue
            y = r * 6 - 6
            if y > 63:
                continue
            seed = col * 31 + r * 7 + (f // 4 if dist == 0 else (f // 8) * (r % 3 == 0))
            g = _rglyph(seed)
            c = R_HEAD if dist == 0 else mix(R_HI, R_LOW, dist / trail) if dist < trail else R_LOW
            for j, bits in enumerate(g):
                for i in range(3):
                    if bits >> (2 - i) & 1:
                        cv.px(x + i, y + j, c)


def r_panel(cv, x, y, w, h):
    """Terminal window: rain dimmed behind it, thin green frame with corner ticks."""
    for j in range(y, y + h):
        for i in range(x, x + w):
            cv.px(i, j, mix(cv.get(i, j), R_BG, 0.72))
    for i in range(x, x + w):
        cv.px(i, y, R_LOW); cv.px(i, y + h - 1, R_LOW)
    for j in range(y, y + h):
        cv.px(x, j, R_LOW); cv.px(x + w - 1, j, R_LOW)
    for (cx, cy) in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
        cv.px(cx, cy, R_HI)


def decode(s, f, salt=0):
    """Values are never scrambled (a glance must always show the true number)."""
    return str(s)


def r_scan(f, salt=0):
    """A bright 'decode' sweep across a value, staggered per value so they don't all flash at once."""
    return glint_pos(f, 24, salt=salt * 2 + 1)


def r_text(cv, x, y, s, c=R_TXT, font="tall", align="left", glow=True):
    if glow:
        cv.text(x, y, s, c, font, align, outline=(0, 40, 14))
    else:
        cv.text(x, y, s, c, font, align, shadow=False)


def render_dashboard_digital_rain(d, f, variant=0):
    cv = Canvas()
    rain_bg(cv, f)
    # top: IN / OUT terminal windows
    for x, lab, v, h in [(0, "IN", num(d.get("t_in")), d.get("h_in")), (32, "OUT", num(d.get("t_out")), d.get("h_out"))]:
        r_panel(cv, x, 0, 32, 21)
        r_text(cv, x + 2, 2, lab, R_DIM, glow=False)
        hv = num(h)
        if hv is not None:
            r_text(cv, x + 30, 2, "%d%%" % round(hv), R_DIM, align="right", glow=False)
        s = temp_str(v)
        if s:
            cv.text(x + 16, 10, s, R_HI, "block", "center", outline=(0, 45, 16),
                    grad=[0.6, 0.45, 0.3, 0.15, 0.05, 0, 0, -0.1, -0.2, -0.3], glint=r_scan(f, x // 32))
    # AQI line
    r_panel(cv, 0, 22, 64, 12)
    a = num(d.get("aqi"))
    r_text(cv, 2, 24, "AQI", R_DIM, glow=False)
    if a is not None:
        r_text(cv, 15, 24, decode(str(int(round(a))), f, 7), R_TXT)
        lit = int(min(a, 299) / 300 * 8) + 1
        for i in range(8):
            on = i < lit
            c = R_HI if on else R_LOW
            if on and i == lit - 1 and (f // 2) % 2:
                c = R_HEAD
            cv.rect(28 + i * 3, 25, 2, 5, c)
    out = rain_outlook(d)
    if out is not None:
        r_text(cv, 62, 24, "RAIN" if out[0] else "DRY", R_WARN if out[0] and (f // 4) % 2 else R_TXT,
               align="right", glow=False)
    # bottom terminal
    r_panel(cv, 0, 35, 64, 29)
    if show_sun_card(d, variant):
        rise, sett, now = _hhmm(d.get("sunrise")), _hhmm(d.get("sunset")), _hhmm(d.get("time"))
        r_text(cv, 2, 37, "RISE", R_DIM, glow=False); r_text(cv, 62, 37, str(d.get("sunrise") or "--:--"), R_TXT, align="right")
        r_text(cv, 2, 46, "SET", R_DIM, glow=False); r_text(cv, 62, 46, str(d.get("sunset") or "--:--"), R_TXT, align="right")
        r_text(cv, 2, 55, "DAY", R_DIM, glow=False)
        p = 0.0
        if None not in (rise, sett, now) and sett > rise:
            p = max(0.0, min(1.0, (now - rise) / (sett - rise)))
        n = round(p * 12)
        for i in range(12):
            cv.rect(17 + i * 3, 56, 2, 5, R_HI if i < n else R_LOW)
        if n < 12 and (f // 4) % 2:
            cv.rect(17 + n * 3, 56, 2, 5, R_HEAD)
    else:
        spin = "|/-\\"[f % 4]
        for row, (name, a2) in enumerate(zip(("WASH", "DRY", "3DP"), appl_list(d))):
            y = 37 + row * 9
            k = a2["k"]
            active = k not in ("idle", "off")
            r_text(cv, 2, y, name, R_TXT if active else R_DIM, glow=False)
            if k == "run":
                r_text(cv, 19, y, spin, R_HEAD, glow=False)
            elif k == "err" and (f // 4) % 2:
                r_text(cv, 19, y, "!", R_WARN, glow=False)
            lab = a2["label"]
            c = {"done": R_WARN, "err": R_WARN}.get(k, R_TXT if active else R_DIM)
            r_text(cv, 62, y, decode(lab, f, row) if active else lab, c, align="right", glow=active)
            if a2["kind"] == "printer" and a2["pct"] is not None and k in ("run", "pause"):
                n = round(max(0, min(100, a2["pct"])) / 100 * 20)
                for i in range(20):
                    cv.px(23 + i, y + 7, R_HI if i < n else R_LOW)
    # blinking cursor
    if (f // 4) % 2 == 0:
        cv.rect(60, 61, 2, 1, R_HEAD)
    return cv.img


COND_WORD = {"sun": "CLEAR", "night": "NIGHT", "partly": "PARTLY", "cloud": "CLOUDY", "rain": "RAIN",
             "snow": "SNOW", "storm": "STORM", "fog": "FOG", "wind": "WIND", "unknown": "----"}


def r_mini_icon(cv, x, y, grp, f):
    """5x5 code-glyph pictograms."""
    pats = {"sun": ["#.#.#", ".###.", "##.##", ".###.", "#.#.#"], "night": [".##..", "##...", "##...", "##..#", ".##.."],
            "partly": ["#.##.", ".####", "#####", ".....", "....."], "cloud": [".##..", "####.", "#####", ".....", "....."],
            "rain": [".##..", "####.", ".....", "#.#.#", ".#.#."], "snow": [".##..", "####.", ".....", "#.#.#", "....."],
            "storm": [".##..", "####.", "..#..", ".#...", "..#.."], "fog": ["####.", ".....", ".####", ".....", "####."],
            "wind": ["###..", "....#", "####.", "....#", "##..."], "unknown": [".###.", "...#.", "..#..", ".....", "..#.."]}
    rows = pats.get(grp, pats["unknown"])
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch == "#":
                c = R_HEAD if (grp in ("rain", "snow") and j >= 3 and (f // 4 + i) % 2) else R_HI
                cv.px(x + i, y + j, c)


def render_weather_digital_rain(d, f):
    cv = Canvas()
    grp = cond_group(cur_cond(d))
    dens = {"rain": 1.0, "storm": 1.0, "snow": 0.85, "cloud": 0.7, "fog": 0.6}.get(grp, 0.45)
    rain_bg(cv, f, density=dens)
    r_panel(cv, 0, 0, 64, 14)
    cv.text(32, 2, str(d.get("time", "")), R_HI, "block", "center", outline=(0, 45, 16),
            grad=[0.6, 0.45, 0.3, 0.15, 0.05, 0, 0, -0.1, -0.2, -0.3], glint=r_scan(f, 0))
    r_panel(cv, 0, 15, 64, 20)
    r_text(cv, 2, 17, str(d.get("dow", "")) + " " + str(d.get("date", "")), R_DIM, glow=False)
    word = COND_WORD.get(grp, "----")
    r_text(cv, 2, 26, word, R_TXT)
    if (f // 4) % 2 == 0:                                                  # terminal cursor
        cv.rect(4 + cv.text_width(word, "tall"), 32, 3, 1, R_HEAD)
    v = cur_temp(d)
    s = temp_str(v)
    if s:
        cv.text(62, 17, s, R_HI, "block", "right", outline=(0, 45, 16),
                grad=[0.6, 0.45, 0.3, 0.15, 0.05, 0, 0, -0.1, -0.2, -0.3], glint=r_scan(f, 2))
    today, nxt = today_and_next(d)
    if today:
        hi, lo = num(today.get("hi")), num(today.get("lo"))
        txt = "%s/%s" % ("%d" % round(hi) if hi is not None else "-", "%d" % round(lo) if lo is not None else "-")
        r_text(cv, 62, 28, txt, R_DIM, align="right", glow=False)
    r_panel(cv, 0, 36, 64, 28)
    for n, day in enumerate(nxt[:4]):
        y = 38 + n * 6
        weekend = int(num(day.get("wd")) or 0) in (6, 7)
        cv.text(2, y, str(day.get("d", ""))[:2], R_WARN if weekend else R_DIM, shadow=False)
        r_mini_icon(cv, 12, y, cond_group(day.get("c")), (f + n * 3) % FRAMES)
        hi, lo = num(day.get("hi")), num(day.get("lo"))
        cv.text(44, y, "%d" % round(hi) if hi is not None else "-", R_TXT, align="right", shadow=False)
        cv.text(48, y, "/", R_LOW, shadow=False)
        cv.text(62, y, "%d" % round(lo) if lo is not None else "-", R_DIM, align="right", shadow=False)
        # mini temperature bar between icon and numbers
        if hi is not None:
            L = max(1, min(14, round((hi + 5) / 3)))
            for i in range(L):
                cv.px(20 + i, y + 2, R_HI if i < L - 1 else R_HEAD)
    return cv.img


# ----------------------------------------------------------------------------
# COMIC  - halftone panels, slanted gutters, thick ink, speech bubbles, action bursts
# ----------------------------------------------------------------------------
C_PAPER, C_INK = (250, 244, 226), (12, 10, 14)
C_YEL, C_RED, C_BLU, C_CYA, C_MAG = (255, 214, 0), (232, 36, 44), (30, 105, 230), (0, 186, 230), (232, 40, 140)


def _in_poly(x, y, pts):
    inside = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            if x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1:
                inside = not inside
    return inside


def c_panel(cv, pts, base, dot, f=0, grad=(0, 1)):
    """Comic panel: flat colour + Ben-Day halftone dots that grow along a direction, ink border."""
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, x1, y0, y1 = int(min(xs)), int(max(xs)), int(min(ys)), int(max(ys))
    cells = set()
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if _in_poly(x + 0.5, y + 0.5, pts):
                cells.add((x, y))
    for (x, y) in cells:
        t = ((x - x0) * grad[0] + (y - y0) * grad[1]) / max(1, (x1 - x0) * abs(grad[0]) + (y1 - y0) * abs(grad[1]))
        big = t > 0.55
        on = (x % 3 == 1 and y % 3 == 1) or (big and ((x % 3 == 1 and y % 3 in (0, 1)) or (x % 3 == 2 and y % 3 == 1)))
        cv.px(x, y, dot if on else base)
    for (x, y) in cells:
        if any((x + dx, y + dy) not in cells for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            cv.px(x, y, C_INK)
    return cells


def c_burst(cv, cx, cy, r_in, r_out, color, f, spikes=10, rot=True):
    ang0 = (2 * math.pi * f / FRAMES / spikes) if rot else 0
    pts = []
    for k in range(spikes * 2):
        a = ang0 + math.pi * k / spikes
        r = r_out if k % 2 == 0 else r_in
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    cells = set()
    for y in range(int(cy - r_out) - 1, int(cy + r_out) + 2):
        for x in range(int(cx - r_out) - 1, int(cx + r_out) + 2):
            if _in_poly(x + 0.5, y + 0.5, pts):
                cells.add((x, y))
    for (x, y) in cells:
        edge = any((x + dx, y + dy) not in cells for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        cv.px(x, y, C_INK if edge else color)


def c_bubble(cv, x, y, w, h, tail=None):
    """Speech bubble with rounded corners and an optional tail (tx, ty)."""
    for j in range(h):
        for i in range(w):
            corner = (i in (0, w - 1) and j in (0, h - 1))
            if corner:
                continue
            edge = i in (0, w - 1) or j in (0, h - 1) or ((i in (1, w - 2)) and (j in (0, h - 1)))
            cv.px(x + i, y + j, C_INK if edge else (255, 255, 255))
    for (i, j) in ((1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)):
        cv.px(x + i, y + j, C_INK)
    if tail:
        tx, ty = tail
        bx, by = x + w // 2, y + h - 1
        n = max(abs(tx - bx), abs(ty - by), 1)
        for k in range(n + 1):
            px_, py_ = round(bx + (tx - bx) * k / n), round(by + (ty - by) * k / n)
            cv.px(px_, py_, C_INK)
            if k < n - 1:
                cv.px(px_ + 1, py_, (255, 255, 255))


@protects
def c_caption(cv, x, y, text, fill=C_YEL, tc=C_INK, align="left"):
    w = cv.text_width(text) + 4
    if align == "right": x -= w
    cv.rect(x, y, w, 9, C_INK)
    cv.rect(x + 1, y + 1, w - 2, 7, fill)
    cv.text(x + 2, y + 2, text, tc, shadow=False)


def c_letters(cv, cx, y, s, color=C_INK, font="block", align="center", pop=(255, 255, 255)):
    """Comic lettering: ink letters, white outline, offset colour drop."""
    cv.text(cx + 1, y + 1, s, C_RED, font, align, outline=C_RED)
    return cv.text(cx, y, s, color, font, align, outline=pop)


def c_outlined(cv, cells, fill_fn):
    for (x, y) in cells:
        edge = any((x + dx, y + dy) not in cells for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        cv.px(x, y, C_INK if edge else fill_fn(x, y))


def c_cloud_cells(cx, cy, s=1.0):
    cells = set()
    circles = [(-4, 1, 3.2), (0, -1.5, 4.2), (4, 1, 3.2)]
    for y in range(int(cy - 7 * s), int(cy + 6 * s)):
        for x in range(int(cx - 9 * s), int(cx + 9 * s)):
            if any(math.hypot(x + 0.5 - (cx + bx * s), y + 0.5 - (cy + by * s)) <= r * s for bx, by, r in circles) \
                    and y + 0.5 <= cy + 3.5 * s:
                cells.add((x, y))
    return cells


def c_icon(cv, cx, cy, grp, f, s=1.0):
    ph = 2 * math.pi * f / FRAMES
    drift = round(math.sin(ph) * 1.5 * s)
    if grp in ("sun", "partly"):
        sx, sy = (cx, cy) if grp == "sun" else (cx - 3 * s, cy - 3 * s)
        c_burst(cv, sx, sy, 4.5 * s, 7.5 * s, C_YEL, f, spikes=8)
        cells = {(x, y) for y in range(int(sy - 5 * s), int(sy + 5 * s) + 1) for x in range(int(sx - 5 * s), int(sx + 5 * s) + 1)
                 if math.hypot(x + 0.5 - sx, y + 0.5 - sy) <= 3.8 * s}
        c_outlined(cv, cells, lambda x, y: (255, 170, 0) if (x + y) % 3 else (255, 230, 120))
        if grp == "partly":
            c_outlined(cv, c_cloud_cells(cx + 3 * s + drift, cy + 3 * s, 0.8 * s),
                       lambda x, y: (255, 255, 255) if (x % 3 or y % 3) else (190, 210, 235))
    elif grp == "night":
        cells = {(x, y) for y in range(int(cy - 6 * s), int(cy + 7 * s)) for x in range(int(cx - 6 * s), int(cx + 7 * s))
                 if math.hypot(x + 0.5 - cx, y + 0.5 - cy) <= 5 * s and math.hypot(x + 0.5 - (cx + 3 * s), y + 0.5 - (cy - 2 * s)) > 4.2 * s}
        c_outlined(cv, cells, lambda x, y: C_YEL)
        for n, (dx, dy) in enumerate(((6, -5), (-6, 4), (7, 4))):
            if (f // 4 + n) % 2:
                cv.px(round(cx + dx * s), round(cy + dy * s), (255, 255, 255))
    elif grp in ("cloud", "rain", "snow", "storm", "fog", "wind"):
        dark = grp == "storm"
        if grp == "cloud":
            c_outlined(cv, c_cloud_cells(cx + 3 * s - drift, cy - 3 * s, 0.7 * s), lambda x, y: (200, 210, 230))
        c_outlined(cv, c_cloud_cells(cx + drift, cy, s),
                   lambda x, y: ((120, 120, 140) if dark else (255, 255, 255)) if (x % 3 or y % 3) else (170, 190, 220))
        if grp in ("rain", "snow"):
            for n in range(5):
                x = round(cx - 7 * s + n * 3.5 * s)
                y = round(cy + 5 * s) + (f + n * 2) % max(2, round(5 * s))
                if grp == "rain":
                    cv.px(x, y, C_BLU); cv.px(x - 1, y - 1, C_CYA)
                else:
                    cv.px(x, y, (255, 255, 255)); cv.px(x + 1, y, C_INK)
        if grp == "storm" and f % 8 < 4:
            c_burst(cv, cx + 2 * s, cy + 6 * s, 2 * s, 4 * s, C_YEL, f, spikes=5)
        if grp in ("fog", "wind"):
            for n in range(3):
                y = round(cy + 4 * s + n * 2 * s)
                for i in range(round(14 * s)):
                    if (i + f + n * 4) % 7 < 5:
                        cv.px(round(cx - 7 * s) + i, y, C_INK)


def c_appliance(cv, x, y, a, f):
    k, kind = a["k"], a["kind"]
    on = k == "run"
    cx, cy = x + 6, y + 6
    if on or k in ("done", "err"):
        c_burst(cv, cx, cy, 6, 9, C_YEL if k != "err" else C_RED, f, spikes=9)
    body = (255, 255, 255) if k not in ("idle", "off") else (200, 196, 186)
    cv.rect(x, y, 13, 13, C_INK)
    cv.rect(x + 1, y + 1, 11, 11, body)
    ang = 2 * math.pi * f / FRAMES
    if kind in ("washer", "dryer"):
        cv.rect(x + 1, y + 3, 11, 1, C_INK)
        for j in range(13):
            for i in range(13):
                d0 = math.hypot(i - 6, j - 7.5)
                if 2.6 < d0 <= 3.6:
                    cv.px(x + i, y + j, C_INK)
                elif d0 <= 2.6:
                    if on:
                        t = math.atan2(j - 7.5, i - 6)
                        c = (C_BLU if kind == "washer" else C_RED) if math.sin(2 * t - 3 * ang) > 0 else (C_CYA if kind == "washer" else C_YEL)
                    else:
                        c = (150, 150, 160)
                    cv.px(x + i, y + j, c)
    else:
        cv.rect(x + 2, y + 3, 9, 1, C_INK)
        hx = x + 4 + (round(2 + 2 * math.sin(ang)) if on else 2)
        cv.rect(hx - 1, y + 4, 3, 2, C_RED if on else C_INK)
        cv.rect(x + 4, y + 9, 5, 2, C_INK)
    if on:                                                          # speed lines
        for n, (dx, dy) in enumerate(((-3, 2), (-3, 6), (-3, 10))):
            L = 2 + (f + n) % 2
            cv.rect(x + dx - L + 1, y + dy, L, 1, C_INK)


def c_sun_panel(cv, pts, rising, t, f):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, max(ys) - 6
    rot = 2 * math.pi * f / FRAMES / 6
    cells = set()
    for y in range(int(min(ys)), int(max(ys)) + 1):
        for x in range(int(min(xs)), int(max(xs)) + 1):
            if _in_poly(x + 0.5, y + 0.5, pts):
                cells.add((x, y))
    c1, c2 = ((255, 200, 60), (255, 150, 40)) if rising else ((240, 90, 60), (160, 40, 110))
    for (x, y) in cells:
        a = math.atan2(y + 0.5 - cy, x + 0.5 - cx) + (rot if rising else -rot)
        cv.px(x, y, c1 if int(a / (math.pi / 8)) % 2 else c2)
    for (x, y) in cells:
        if any((x + dx, y + dy) not in cells for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            cv.px(x, y, C_INK)
    prog = f / (FRAMES - 1)
    sy = (cy + 3 - 4 * prog) if rising else (cy - 1 + 4 * prog)
    sun = {(x, y) for (x, y) in cells if math.hypot(x + 0.5 - cx, y + 0.5 - sy) <= 4.5 and y < max(ys) - 3}
    c_outlined(cv, sun, lambda x, y: (255, 250, 200) if rising else (255, 210, 120))
    hz = int(max(ys)) - 3
    for x in range(int(min(xs)) + 1, int(max(xs))):
        if (x, hz) in cells:
            cv.px(x, hz, C_INK)
    c_caption(cv, int(min(xs)) + 2, int(min(ys)) + 2, str(t or "--:--"), fill=(255, 255, 255))


def render_dashboard_comic(d, f, variant=0):
    cv = Canvas()
    cv.rect(0, 0, 64, 64, C_PAPER)
    P1 = [(0, 0), (33, 0), (29, 23), (0, 23)]
    P2 = [(35, 0), (64, 0), (64, 23), (31, 23)]
    c_panel(cv, P1, (255, 236, 120), (240, 170, 0), grad=(1, 1))
    c_panel(cv, P2, (150, 225, 245), (40, 150, 220), grad=(-1, 1))
    for x0, v, h, sprite, cx in [(0, num(d.get("t_in")), d.get("h_in"), HOUSE, 15),
                                 (32, num(d.get("t_out")), d.get("h_out"), TREE, 48)]:
        ix = x0 + (2 if x0 == 0 else 5)
        cv.sprite(ix, 1, *sprite, shadow=False)
        hv = num(h)
        if hv is not None:
            c_caption(cv, x0 + (29 if x0 == 0 else 32), 0, "%d%%" % round(hv), fill=(255, 255, 255), align="right")
        s = (temp_str(v) or "").rstrip("°")
        if s:
            bx, bw = (x0 + 0, 30) if x0 == 0 else (x0 + 2, 31)
            c_bubble(cv, bx, 8, bw, 15, tail=(ix + 3, 7))
            cv.text(bx + bw // 2, 10, s, C_INK, "big", "center", shadow=False)
    P3 = [(0, 25), (45, 25), (41, 41), (0, 41)]
    P4 = [(47, 25), (64, 25), (64, 41), (43, 41)]
    c_panel(cv, P3, (255, 190, 210), (230, 60, 130), grad=(1, 0))
    a = num(d.get("aqi"))
    c_caption(cv, 1, 26, "AIR")
    if a is not None:
        col = aqi_color(a)
        sc = 1 + 0.12 * math.sin(2 * math.pi * f / FRAMES)
        c_burst(cv, 26, 33, 5.5 * sc, 8.5 * sc, col, f, spikes=11)
        cv.text(26, 31, str(int(round(a))), C_INK, align="center", outline=(255, 255, 255))
        word = "OK!" if a < 50 else "MEH" if a < 101 else "UGH!"
        cv.text(2, 35, word, C_INK, shadow=False)
    out = rain_outlook(d)
    if out is None:
        c_panel(cv, P4, (230, 230, 230), (200, 200, 200))
    elif out[0]:
        c_panel(cv, P4, (120, 170, 245), (40, 90, 200), grad=(0, 1))
        for n in range(6):                                           # diagonal rain streaks
            x0_ = 44 + (n * 4 + f) % 20
            y0_ = 26 + (n * 5 + f * 2) % 13
            for t in range(3):
                if _in_poly(x0_ - t + 0.5, y0_ + t * 1.5 + 0.5, P4):
                    cv.px(x0_ - t, int(y0_ + t * 1.5), (255, 255, 255))
        um = ["...###...", ".#rrrrr#.", "#rrrrrrr#", "#########", "....#....", "....#....", "...##...."]
        sway = round(math.sin(2 * math.pi * f / FRAMES))
        for j, r in enumerate(um):
            for i, ch in enumerate(r):
                if ch != ".":
                    cv.px(50 + i + (sway if j < 4 else 0), 29 + j, C_INK if ch == "#" else C_RED)
    else:
        c_panel(cv, P4, (255, 236, 120), (240, 170, 0))
        c_burst(cv, 55, 33, 3.5, 6, C_YEL, f, spikes=8)
        cv.rect(54, 32, 3, 3, (255, 140, 0))
    if show_sun_card(d, variant):
        c_sun_panel(cv, [(0, 43), (31, 43), (29, 64), (0, 64)], True, d.get("sunrise"), f)
        c_sun_panel(cv, [(33, 43), (64, 43), (64, 64), (31, 64)], False, d.get("sunset"), f)
    else:
        panels = [[(0, 43), (21, 43), (19, 64), (0, 64)], [(23, 43), (42, 43), (40, 64), (21, 64)],
                  [(44, 43), (64, 43), (64, 64), (42, 64)]]
        cols = [((235, 245, 255), (170, 200, 240)), ((255, 235, 220), (240, 170, 140)), ((235, 255, 225), (160, 220, 150))]
        for pts, (b, dt), a2 in zip(panels, cols, appl_list(d)):
            c_panel(cv, pts, b, dt, grad=(0, -1))
            x = int(min(p[0] for p in pts))
            c_appliance(cv, x + 4, 43, a2, f)
            fill = {"run": C_YEL, "done": (120, 230, 120), "err": C_RED, "pause": (255, 180, 80)}.get(a2["k"], (220, 220, 220))
            lab = a2["label"]
            wl = cv.text_width(lab) + 4
            c_caption(cv, x + max(1, (19 - wl) // 2), 55, lab, fill=fill)
    return cv.img


def render_weather_comic(d, f):
    cv = Canvas()
    cv.rect(0, 0, 64, 64, C_PAPER)
    c_panel(cv, [(0, 0), (64, 0), (64, 12), (0, 12)], C_YEL, (240, 170, 0), grad=(1, 0))
    cv.text(32, 3, str(d.get("time", "")), C_INK, "gicko", "center", shadow=False)
    cv.text(2, 4, str(d.get("date", "")), C_INK, shadow=False)
    cv.text(62, 4, str(d.get("dow", "")), C_RED, align="right", shadow=False)
    grp = cond_group(cur_cond(d))
    bg = {"sun": ((150, 215, 255), (60, 150, 230)), "night": ((40, 40, 110), (20, 20, 70)),
          "rain": ((150, 170, 200), (90, 110, 150)), "storm": ((110, 100, 140), (60, 50, 90)),
          "snow": ((220, 235, 250), (160, 190, 230))}.get(grp, ((170, 220, 250), (90, 170, 230)))
    c_panel(cv, [(0, 14), (31, 14), (27, 38), (0, 38)], bg[0], bg[1], grad=(0, 1))
    c_icon(cv, 14, 26, grp, f, 1.0)
    c_panel(cv, [(33, 14), (64, 14), (64, 38), (29, 38)], (255, 255, 255), (230, 225, 210))
    s = temp_str(cur_temp(d))
    if s:
        c_bubble(cv, 30, 14, 34, 15, tail=(28, 31))
        cv.text(47, 16, s, C_INK, "big", "center", shadow=False)
    today, nxt = today_and_next(d)
    if today:
        hi, lo = num(today.get("hi")), num(today.get("lo"))
        txt = ""
        if hi is not None: txt += "%d" % round(hi)
        if lo is not None: txt += "/%d" % round(lo)
        if txt:
            c_caption(cv, 63, 29, txt, fill=C_YEL, align="right")
    pan = [[(0, 40), (16, 40), (14, 64), (0, 64)], [(18, 40), (32, 40), (30, 64), (16, 64)],
           [(34, 40), (48, 40), (46, 64), (32, 64)], [(50, 40), (64, 40), (64, 64), (48, 64)]]
    tints = [((255, 240, 200), (245, 200, 120)), ((220, 240, 255), (160, 200, 240)),
             ((255, 225, 235), (240, 160, 190)), ((225, 250, 225), (160, 220, 160))]
    for n, pts in enumerate(pan):
        c_panel(cv, pts, tints[n][0], tints[n][1], grad=(0, 1))
        if n >= len(nxt):
            continue
        day = nxt[n]
        x = int(min(p[0] for p in pts))
        cx = x + 8
        weekend = int(num(day.get("wd")) or 0) in (6, 7)
        cv.text(cx, 42, str(day.get("d", ""))[:2], C_RED if weekend else C_INK, align="center", shadow=False)
        c_icon(cv, cx, 50, cond_group(day.get("c")), (f + n * 3) % FRAMES, 0.5)
        hi, lo = num(day.get("hi")), num(day.get("lo"))
        if hi is not None:
            cv.text(cx, 54, "%d" % round(hi), C_INK, align="center", shadow=False)
        if lo is not None:
            cv.text(cx, 59, "%d" % round(lo), C_BLU, align="center", shadow=False)
    return cv.img


# ----------------------------------------------------------------------------
# MECH COCKPIT  - steel bulkhead, rivets, hazard stripes, amber CRT screens, analog gauge, lamps
# ----------------------------------------------------------------------------
X_STEEL, X_STEEL_L, X_STEEL_D = (62, 66, 72), (120, 126, 134), (26, 28, 32)
X_AMB, X_AMB_D, X_AMB_DD, X_CRT = (255, 170, 30), (150, 85, 10), (60, 32, 4), (14, 8, 2)
X_HAZ, X_RED, X_GRN = (240, 190, 20), (255, 50, 40), (70, 230, 90)


def x_bulkhead(cv, f):
    if cv.bgl:
        return
    for y in range(64):
        for x in range(64):
            v = (_hash(x // 6, y, 41) % 7) - 3                          # brushed steel streaks
            cv.px(x, y, shade(X_STEEL, v * 0.025))
    for y in range(0, 64, 21):                                      # panel seams
        cv.rect(0, y, 64, 1, X_STEEL_D)


def x_screen(cv, x, y, w, h, f, label=None):
    """Recessed amber CRT: bevelled bezel, dark glass, scanlines, rolling refresh band, rivets."""
    cv.rect(x - 1, y - 1, w + 2, h + 2, X_STEEL_D)
    cv.rect(x - 1, y - 1, w + 2, 1, X_STEEL_D)
    cv.rect(x - 1, y + h, w + 2, 1, X_STEEL_L)
    cv.rect(x + w, y - 1, 1, h + 2, X_STEEL_L)
    roll = y + (MO.e() * (h + 6) // FRAMES) - 3 if MO.fx else -99
    for j in range(h):
        base = X_CRT if (j % 2 == 0) else shade(X_CRT, 0.3)
        if abs(y + j - roll) <= 1:
            base = mix(base, X_AMB_DD, 0.8)
        cv.rect(x, y + j, w, 1, base)
    for (rx, ry) in ((x - 1, y - 1), (x + w, y - 1), (x - 1, y + h), (x + w, y + h)):
        cv.px(rx, ry, X_STEEL_L)
    if label:
        cv.text(x + 1, y + 1, label, X_AMB_D, shadow=False)


def x_crt_text(cv, x, y, s, font="pico", align="left", color=X_AMB, glow=True):
    """Amber phosphor text: soft halo + scanline-darkened odd rows."""
    if glow:
        cv.text(x, y, s, X_AMB_DD, font, align, outline=X_AMB_DD)
    return cv.text(x, y, s, color, font, align, shadow=False,
                   colfn=lambda xx, yy, j: color if yy % 2 == 0 else shade(color, -0.25))


def x_hazard(cv, x, y, w, h, f):
    off = f // 2
    for j in range(h):
        for i in range(w):
            cv.px(x + i, y + j, X_HAZ if ((i + j + off) // 3) % 2 == 0 else (20, 18, 14))


@protects
def x_needle_gauge(cv, cx, cy, r, frac, f, col):
    """Analog dial: tick arc, coloured zones, needle with a little mechanical jitter."""
    for k in range(25):
        a = math.pi + math.pi * k / 24
        c = aqi_color(k / 24 * 300)
        cv.px(round(cx + r * math.cos(a)), round(cy + r * math.sin(a)), shade(c, -0.25))
        if k % 6 == 0:
            cv.px(round(cx + (r - 1) * math.cos(a)), round(cy + (r - 1) * math.sin(a)), X_AMB_D)
    if frac is None:
        return
    jitter = 0.03 * math.sin(2 * math.pi * f / FRAMES * 3)
    a = math.pi + math.pi * max(0, min(1, frac + jitter))
    for t in range(r - 1):
        cv.px(round(cx + t * math.cos(a)), round(cy + t * math.sin(a)), X_AMB if t > 1 else X_AMB_D)
    cv.rect(cx - 1, cy - 1, 3, 2, X_STEEL_L)


@protects
def x_lamp(cv, x, y, w, h, text, state, f):
    """Annunciator push-lamp: lit amber/green/red with label, or dark."""
    col = {"run": X_AMB, "done": X_GRN, "err": X_RED, "pause": X_HAZ, "prep": X_AMB, "rain": (90, 170, 255),
           "dry": X_GRN}.get(state)
    if state == "err" and (f // 4) % 2:
        col = None
    if state == "run" and (f // 4) % 4 == 3:
        col = shade(X_AMB, -0.25)
    cv.rect(x, y, w, h, X_STEEL_D)
    cv.rect(x + 1, y + 1, w - 2, h - 2, col if col else (34, 30, 26))
    if col:
        cv.rect(x + 1, y + 1, w - 2, 1, mix(col, (255, 255, 255), 0.45))
    cv.text(x + w // 2, y + (h - 5) // 2, text, (20, 12, 0) if col else (85, 78, 66), align="center", shadow=False)


def render_dashboard_mech(d, f, variant=0):
    cv = Canvas()
    x_bulkhead(cv, f)
    for x, lab, v, h, scale in [(2, "INT", num(d.get("t_in")), d.get("h_in"), IN_SCALE),
                                (34, "EXT", num(d.get("t_out")), d.get("h_out"), OUT_SCALE)]:
        x_screen(cv, x, 2, 28, 18, f, lab)
        hv = num(h)
        if hv is not None:
            x_crt_text(cv, x + 27, 3, "%d%%" % round(hv), align="right", color=X_AMB_D, glow=False)
        s = temp_str(v)
        if s:
            warn = v is not None and temp_color(v, *scale) in (RED, BLUE)
            x_crt_text(cv, x + 14, 9, s, "big", "center", color=X_RED if warn and (f // 4) % 2 else X_AMB)
    # AIR screen with analog dial + rain lamp
    x_screen(cv, 2, 23, 36, 16, f, "AIR")
    a = num(d.get("aqi"))
    x_needle_gauge(cv, 27, 37, 9, None if a is None else min(a, 300) / 300, f, X_AMB)
    if a is not None:
        x_crt_text(cv, 3, 31, str(int(round(a))), "gicko", color=aqi_color(a))
    out = rain_outlook(d)
    if out is None:
        x_lamp(cv, 41, 22, 21, 9, "RAIN?", None, f)
    else:
        x_lamp(cv, 41, 22, 21, 9, "RAIN" if out[0] else "DRY", "rain" if out[0] else "dry", f)
    x_screen(cv, 42, 33, 19, 6, f)
    if out is not None:
        x_crt_text(cv, 51, 34, ("%d%%" % round(out[1])) if out[1] else "--", align="center",
                   color=X_AMB if out[0] else X_AMB_D, glow=False)
    x_hazard(cv, 0, 40, 64, 1, f)
    if show_sun_card(d, variant):
        x_screen(cv, 2, 43, 60, 19, f, "NAV")
        rise, sett, now = _hhmm(d.get("sunrise")), _hhmm(d.get("sunset")), _hhmm(d.get("time"))
        base = 55
        cv.rect(4, base, 56, 1, X_AMB_D)
        for i in range(0, 56, 2):
            p = i / 55
            cv.px(4 + i, round(base - 9 * math.sin(math.pi * p)), X_AMB_DD)
        if None not in (rise, sett, now) and sett > rise:
            p = (now - rise) / (sett - rise)
            if 0 <= p <= 1:
                sx, sy = 4 + 55 * p, base - 9 * math.sin(math.pi * p)
                disc(cv, sx, sy, 2.2, lambda t, i, j: X_AMB)
                if (f // 2) % 2:
                    cv.rect(round(sx) - 4, round(sy), 9, 1, X_AMB_D)
        x_crt_text(cv, 3, 57, str(d.get("sunrise") or "--:--"))
        x_crt_text(cv, 61, 57, str(d.get("sunset") or "--:--"), align="right", color=(255, 120, 40))
    else:
        for i, (lab, a2) in enumerate(zip(("WASH", "DRY", "PRNT"), appl_list(d))):
            x = 2 + i * 21
            k = a2["k"]
            x_lamp(cv, x, 42, 19, 9, lab, k if k not in ("idle", "off") else None, f)
            x_screen(cv, x + 1, 53, 17, 8, f)
            x_crt_text(cv, x + 10, 54, a2["label"], align="center",
                       color=X_AMB if k not in ("idle", "off") else X_AMB_D, glow=k not in ("idle", "off"))
            if a2["kind"] == "printer" and a2["pct"] is not None and k in ("run", "pause"):
                n = round(17 * max(0, min(100, a2["pct"])) / 100)
                cv.rect(x + 1, 62, n, 1, X_AMB)
    return cv.img


def x_vector_icon(cv, cx, cy, grp, f, s=1.0):
    """Amber vector-graphics weather symbol."""
    ph = 2 * math.pi * f / FRAMES
    c, cd = X_AMB, X_AMB_D

    def ring(x0, y0, r, col, start=0, end=2 * math.pi, n=None):
        n = n or max(8, int(r * 7))
        for k in range(n + 1):
            a = start + (end - start) * k / n
            cv.px(round(x0 + r * math.cos(a)), round(y0 + r * math.sin(a)), col)

    if grp in ("sun", "partly"):
        sx, sy = (cx, cy) if grp == "sun" else (cx - 3 * s, cy - 3 * s)
        ring(sx, sy, 3.5 * s, c)
        for n in range(8):
            a = n * math.pi / 4 + ph / 8
            for L in (5 * s, 6 * s, 7 * s if (n + f // 4) % 2 else 6 * s):
                cv.px(round(sx + L * math.cos(a)), round(sy + L * math.sin(a)), cd if L < 6 * s else c)
    if grp == "night":
        ring(cx, cy, 5 * s, c, math.pi * 0.35, math.pi * 1.65)
        ring(cx + 2.5 * s, cy, 3.6 * s, c, math.pi * 0.62, math.pi * 1.38)
    if grp in ("partly", "cloud", "rain", "snow", "storm"):
        ox = cx + (3 * s if grp == "partly" else 0) + round(math.sin(ph))
        oy = cy + (2 * s if grp == "partly" else -1 * s)
        ring(ox - 3 * s, oy, 2.6 * s, c, math.pi * 0.5, math.pi * 1.5)
        ring(ox, oy - 1.5 * s, 3.2 * s, c, math.pi, 2 * math.pi)
        ring(ox + 3 * s, oy, 2.6 * s, c, -math.pi * 0.5, math.pi * 0.5)
        cv.rect(round(ox - 3 * s), round(oy + 2.6 * s), round(6 * s) + 1, 1, c)
        if grp in ("rain", "snow", "storm"):
            for n in range(4):
                xx = round(ox - 4 * s + n * 2.6 * s)
                yy = round(oy + 4 * s) + (f // (2 if grp == "snow" else 1) + n * 2) % max(2, round(4 * s))
                cv.px(xx, yy, c if grp != "snow" else (255, 230, 180))
            if grp == "storm" and f % 8 < 3:
                for j, dx in enumerate((1, 0, -1, 0, 1)):
                    cv.px(round(ox + dx), round(oy + 3 * s) + j, X_RED)
    if grp in ("fog", "wind"):
        for n in range(3):
            y = round(cy - 3 * s + n * 3 * s)
            for i in range(round(10 * s)):
                if (i + (f if grp == "wind" else 0) + n * 3) % 6 < 4:
                    cv.px(round(cx - 5 * s) + i, y, c)


def render_weather_mech(d, f):
    cv = Canvas()
    x_bulkhead(cv, f)
    x_screen(cv, 2, 2, 60, 10, f)
    x_crt_text(cv, 32, 4, str(d.get("time", "")), "gicko", "center")
    x_crt_text(cv, 3, 5, str(d.get("date", "")), color=X_AMB_D, glow=False)
    x_crt_text(cv, 61, 5, str(d.get("dow", "")), align="right", color=X_AMB_D, glow=False)
    x_screen(cv, 2, 15, 24, 22, f, "WX")
    grp = cond_group(cur_cond(d))
    x_vector_icon(cv, 14, 27, grp, f, 1.0)
    x_screen(cv, 29, 15, 33, 22, f, "TMP")
    v = cur_temp(d)
    s = temp_str(v)
    if s:
        x_crt_text(cv, 46, 20, s, "big", "center")
    today, nxt = today_and_next(d)
    if today:
        hi, lo = num(today.get("hi")), num(today.get("lo"))
        txt = ("%d" % round(hi) if hi is not None else "-") + "/" + ("%d" % round(lo) if lo is not None else "-")
        x_crt_text(cv, 46, 32, txt, align="center", color=X_AMB_D, glow=False)
    x_hazard(cv, 0, 38, 64, 1, f)
    for n in range(4):
        x = 2 + n * 15
        x_screen(cv, x, 41, 13, 22, f)
        if n >= len(nxt):
            continue
        day = nxt[n]
        weekend = int(num(day.get("wd")) or 0) in (6, 7)
        x_crt_text(cv, x + 7, 42, str(day.get("d", ""))[:2], align="center",
                   color=X_RED if weekend else X_AMB_D, glow=False)
        x_vector_icon(cv, x + 6, 49, cond_group(day.get("c")), (f + n * 3) % FRAMES, 0.42)
        hi, lo = num(day.get("hi")), num(day.get("lo"))
        if hi is not None:
            x_crt_text(cv, x + 7, 53, "%d" % round(hi), align="center", glow=False)
        if lo is not None:
            x_crt_text(cv, x + 7, 58, "%d" % round(lo), align="center", color=X_AMB_D, glow=False)
    return cv.img


# ----------------------------------------------------------------------------
# PLATFORMER  - original 8-bit world: parallax hills, wooden signs, health hearts, robot hero, gems
# ----------------------------------------------------------------------------
PL_INK = (20, 14, 24)
PL_WOOD, PL_WOOD_D, PL_WOOD_L = (200, 140, 78), (96, 58, 26), (236, 190, 120)
PL_GRASS, PL_GRASS_L, PL_DIRT, PL_DIRT_D = (60, 190, 70), (140, 240, 110), (150, 92, 50), (110, 64, 34)
# Original hero: a little fox adventurer with a teal scarf (10x8, facing right)
FOX = {
    "stand": ["...o...o..", "...oo.oo..", "...ooooo..", "...oooko..", "...owwwwwn", "..tttttt..",
              "woooooo...", "...k..k..."],
    "walk":  ["...o...o..", "...oo.oo..", "...ooooo..", "...oooko..", "...owwwwwn", "..tttttt..",
              "woooooo...", "....kk...."],
    "jump":  ["...o...o..", "...oo.oo..", "...ooooo..", "...oooko..", "wo.owwwwwn", ".otttttt..",
              "...oooo...", "..k....k.."],
}
FOX_HOOD = ["...tttt...", "..tttttt..", "..toooot.."]          # hood up when rain is expected
HEART = [".#.#.", "#####", "#####", ".###.", "..#.."]


def pl_sky(cv, y0, y1, d, f, grp=None):
    """Sky colour follows time of day and weather; parallax clouds & hills scroll seamlessly."""
    night = str(d.get("sun", "")) == "below_horizon"
    now, rise, sett = _hhmm(d.get("time")), _hhmm(d.get("sunrise")), _hhmm(d.get("sunset"))
    golden = (None not in (now, rise, sett)) and (abs(now - rise) < 50 or abs(now - sett) < 50)
    if night:
        top, bot = (10, 14, 50), (40, 40, 100)
    elif grp in ("rain", "storm"):
        top, bot = (80, 95, 125), (140, 150, 170)
    elif golden:
        top, bot = (90, 110, 200), (255, 170, 110)
    else:
        top, bot = (70, 150, 255), (170, 220, 255)
    for y in range(y0, y1):
        cv.rect(0, y, 64, 1, mix(top, bot, (y - y0) / max(1, y1 - y0 - 1)))
    if night:
        for n in range(14):
            x, y = (_hash(n, 1, 61) % 64), y0 + (_hash(n, 2, 61) % max(1, (y1 - y0) // 2))
            if (f // 4 + n) % 3:
                cv.px(x, y, (255, 255, 230))
    # far hills (period 16, 0.5 px/frame) and near hills (period 32, 2 px/frame)
    for x in range(64):
        xf = (x + f // 2) % 16
        h1 = round(5 + 3 * math.sin(xf / 16 * 2 * math.pi))
        for y in range(y1 - h1 - 4, y1):
            cv.px(x, y, mix((60, 130, 120), top, 0.35) if not night else (20, 30, 60))
        xn = (x + f * 2) % 32
        h2 = round(3 + 3 * abs(math.sin(xn / 32 * 2 * math.pi)))
        for y in range(y1 - h2, y1):
            cv.px(x, y, (40, 150, 80) if not night else (15, 40, 40))
    # clouds (period 32, 2 px/frame)
    if not night:
        for base_x, cy in ((4, y0 + 3), (22, y0 + 8)):
            cx = (base_x + f * 2) % 64 - 8
            for (dx, dy, w) in ((1, 0, 4), (0, 1, 7), (2, -1, 2)):
                for i in range(w):
                    for xx in (cx + dx + i, cx + dx + i - 64, cx + dx + i + 64):
                        if 0 <= xx < 64:
                            cv.px(xx, cy + dy, (250, 250, 255))


def pl_ground(cv, y, f):
    for x in range(64):
        cv.px(x, y, PL_GRASS_L if (x + 1) % 4 else PL_GRASS)
        cv.px(x, y + 1, PL_GRASS)
        for yy in range(y + 2, 64):
            c = PL_DIRT if ((x // 4 + yy // 3) % 2) else PL_DIRT_D
            if _hash(x // 2, yy // 2, 71) % 11 == 0:
                c = (170, 160, 150)                                   # pebbles
            cv.px(x, yy, c)


def pl_sign(cv, x, y, w, h, ropes=True):
    if ropes:
        for rx in (x + 3, x + w - 4):
            for yy in range(0, y):
                cv.px(rx, yy, (110, 80, 50))
    cv.rect(x, y, w, h, PL_WOOD_D)
    cv.rect(x + 1, y + 1, w - 2, h - 2, PL_WOOD)
    cv.rect(x + 1, y + 1, w - 2, 1, PL_WOOD_L)
    for j in range(y + 3, y + h - 1, 4):                            # wood grain
        for i in range(x + 2, x + w - 2):
            if (i * 7 + j) % 9 < 3:
                cv.px(i, j, shade(PL_WOOD, -0.08))
    for (nx, ny) in ((x + 2, y + 2), (x + w - 3, y + 2)):
        cv.px(nx, ny, (90, 90, 100))                                 # nails


def pl_hero(cv, x, y, pose, f, flip=False, night=False, hood=False):
    """The fox: fluttering scarf, glowing lantern at night, hood up when rain is coming."""
    pal = {"o": (240, 130, 40), "w": (250, 240, 225), "k": (40, 25, 20), "n": (30, 20, 20),
           "t": (40, 195, 185)}
    rows = list(FOX[pose])
    if hood:
        rows[0:3] = FOX_HOOD
    W = len(rows[0])
    # scarf tail streams behind (left) and flutters
    tail_row = 5 if (f // 2) % 2 else 6
    tail = [(1, tail_row), (0, tail_row + (1 if (f // 2) % 2 else -1))]
    lamp = None
    if night:
        lamp = (8, 6)

    def put(i, j, c):
        xx = x + (W - 1 - i if flip else i)
        cv.px(xx, y + j, c)

    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch in pal:
                put(i, j, pal[ch])
    for (i, j) in tail:
        if 0 <= j < 8:
            put(i, j, shade(pal["t"], -0.15))
    if lamp:
        lx = x + (W - 1 - lamp[0] if flip else lamp[0])
        ly = y + lamp[1]
        g = pulse(f, 0.25, 0.65)
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                dd = math.hypot(dx, dy)
                if 0 < dd <= 3:
                    cv.px(lx + dx, ly + dy, mix(cv.get(lx + dx, ly + dy), (255, 210, 90), g * (1 - dd / 3.5)))
        cv.px(lx, ly - 1, (90, 70, 40))
        cv.px(lx, ly, (255, 235, 140))


def pl_gem(cv, x, y, f, col=(80, 230, 255)):
    w = [5, 3, 1, 3][(f // 2) % 4]
    for j, ww in enumerate([1, 3, 5, 3, 1]):
        ww = min(ww, w)
        for i in range(ww):
            c = col if i else mix(col, (255, 255, 255), 0.6)
            cv.px(x + 2 - ww // 2 + i, y + j, c)


def pl_machine(cv, x, y, a, f):
    """In-world machine prop (11x13) + its effects (bubbles, steam, progress)."""
    k, kind = a["k"], a["kind"]
    on = k == "run"
    body = (240, 240, 248) if k not in ("idle", "off") else (170, 170, 185)
    cv.rect(x - 1, y - 1, 13, 14, PL_INK)
    cv.rect(x, y, 11, 12, body)
    cv.rect(x, y, 11, 1, (255, 255, 255))
    ang = 2 * math.pi * f / FRAMES
    if kind in ("washer", "dryer"):
        cv.rect(x, y + 2, 11, 1, shade(body, -0.25))
        for j in range(12):
            for i in range(11):
                d0 = math.hypot(i - 5, j - 7)
                if 2.6 < d0 <= 3.6:
                    cv.px(x + i, y + j, PL_INK)
                elif d0 <= 2.6:
                    if on:
                        t = math.atan2(j - 7, i - 5)
                        c = ((60, 140, 255) if kind == "washer" else (255, 120, 40)) if math.sin(2 * t - 3 * ang) > 0 \
                            else ((150, 210, 255) if kind == "washer" else (255, 210, 90))
                    else:
                        c = (70, 70, 90)
                    cv.px(x + i, y + j, c)
        if on:
            for n in range(3):                                       # bubbles / steam rising
                by = y - 2 - ((f + n * 5) % 10)
                bx = x + 2 + n * 3 + round(math.sin(f / 2 + n))
                cv.px(bx, by, (200, 235, 255) if kind == "washer" else (235, 235, 235))
    else:
        cv.rect(x + 1, y + 2, 9, 1, PL_INK)
        hx = x + 3 + (round(2 + 2 * math.sin(ang)) if on else 2)
        cv.rect(hx, y + 3, 3, 2, (255, 120, 40) if on else PL_INK)
        cv.rect(x + 3, y + 8, 5, 3, (90, 200, 255) if k not in ("idle", "off") else (120, 120, 140))
        if a["pct"] is not None and k in ("run", "pause"):
            n = round(11 * max(0, min(100, a["pct"])) / 100)
            cv.rect(x, y - 3, 11, 2, PL_INK); cv.rect(x, y - 3, n, 2, (90, 255, 120))
    if k == "done" and (f // 4) % 2 == 0:
        pl_gem(cv, x + 3, y - 7, f, (255, 220, 60))
    if k == "err" and (f // 4) % 2 == 0:
        cv.rect(x + 5, y - 8, 1, 4, (255, 60, 60)); cv.px(x + 5, y - 3, (255, 60, 60))


@protects
def pl_status_bar(cv, d, f):
    cv.rect(0, 0, 64, 8, PL_INK)
    a = num(d.get("aqi"))
    lives = 0 if a is None else (5 if a < 50 else 4 if a < 101 else 3 if a < 151 else 2 if a < 201 else 1)
    for i in range(5):
        x = 1 + i * 6
        full = i < lives
        beat = full and i == lives - 1 and (f // 4) % 2 == 0
        for j, r in enumerate(HEART):
            for k, ch in enumerate(r):
                if ch == "#":
                    c = (235, 40, 70) if full else (70, 60, 75)
                    if full and (j, k) == (1, 1):
                        c = (255, 190, 200)
                    cv.px(x + k, 1 + j - (1 if beat else 0), c)
    if a is not None:
        cv.text(33, 2, str(int(round(a))), aqi_color(a), shadow=False)
    out = rain_outlook(d)
    if out is not None:
        if out[0]:
            um = ["..###..", ".#####.", "#######", "...#...", "..##..."]
            for j, r in enumerate(um):
                for k, ch in enumerate(r):
                    if ch == "#":
                        cv.px(55 + k, 1 + j, (90, 170, 255) if j < 3 else (220, 220, 230))
        else:
            disc(cv, 58.5, 3.5, 2.6, lambda t, i, j: (255, 210, 50))


def render_dashboard_platformer(d, f, variant=0):
    cv = Canvas()
    pl_sky(cv, 8, 48, d, f)
    pl_ground(cv, 48, f)
    pl_status_bar(cv, d, f)
    for x, v, h, sprite in [(1, num(d.get("t_in")), d.get("h_in"), HOUSE), (33, num(d.get("t_out")), d.get("h_out"), TREE)]:
        swing = round(0.6 * math.sin(2 * math.pi * f / FRAMES + x))
        pl_sign(cv, x + swing, 10, 30, 19)
        cv.sprite(x + swing + 2, 12, *sprite, shadow=False)
        hv = num(h)
        if hv is not None:
            cv.text(x + swing + 27, 13, "%d%%" % round(hv), PL_WOOD_D, align="right", shadow=False)
        s = temp_str(v)
        if s:
            cv.text(x + swing + 15, 17, s, (70, 36, 14), "big", "center", shadow=False)
    pl_gem(cv, 30, 33 + round(math.sin(2 * math.pi * f / FRAMES)), f)
    if show_sun_card(d, variant):
        rise, sett, now = _hhmm(d.get("sunrise")), _hhmm(d.get("sunset")), _hhmm(d.get("time"))
        if None not in (rise, sett, now) and sett > rise and rise <= now <= sett:
            p = (now - rise) / (sett - rise)
            sx, sy = 6 + 52 * p, 46 - 14 * math.sin(math.pi * p)
            disc(cv, sx, sy, 3.2, lambda t, i, j: mix((255, 250, 180), (255, 180, 30), t))
        for x, t, col in ((2, d.get("sunrise"), (255, 200, 60)), (42, d.get("sunset"), (255, 120, 70))):
            cv.rect(x + 9, 45, 2, 3, (110, 80, 50))
            pl_sign(cv, x, 37, 20, 9, ropes=False)
            cv.text(x + 10, 39, str(t or "--:--"), (70, 36, 14), align="center", shadow=False)
            tri(cv, x + 8, 51, (UP if x == 2 else DOWN)[0], col)
        hx = 22 + round(8 * math.sin(2 * math.pi * f / FRAMES))
        out = rain_outlook(d)
        pl_hero(cv, hx, 40, "walk" if f % 2 else "stand", f, flip=math.cos(2 * math.pi * f / FRAMES) < 0,
                night=str(d.get("sun", "")) == "below_horizon", hood=bool(out and out[0]))
    else:
        for x, a2 in zip((4, 26, 48), appl_list(d)):
            pl_machine(cv, x, 35, a2, f)
            c = {"run": (120, 230, 255), "done": (255, 230, 80), "err": (255, 80, 80)}.get(a2["k"], (230, 230, 230))
            cv.text(x + 5, 54, a2["label"], c, align="center", outline=PL_INK)
        # the fox hops between washer and dryer - and does a happy spin when a load is finished
        apps = appl_list(d)
        happy = any(a2["k"] == "done" for a2 in apps[:2])
        out = rain_outlook(d)
        hood = bool(out and out[0])
        night = str(d.get("sun", "")) == "below_horizon"
        jump = [0, 0, 0, 0, 2, 4, 5, 5, 4, 2, 0, 0, 0, 0, 0, 0][f]
        flip = happy and (f // 2) % 2 == 1
        pl_hero(cv, 15, 40 - jump, "jump" if jump else "stand", f, flip=flip, night=night, hood=hood)
        if happy and jump:
            for k_, (dx, dy) in enumerate(((-2, -2), (11, -1), (5, -4))):
                if (f + k_) % 2:
                    cv.px(15 + dx, 40 - jump + dy, (255, 230, 90))
        elif 4 <= f <= 8:
            pl_gem(cv, 18, 31, f, (255, 220, 60))
    return cv.img


def render_weather_platformer(d, f):
    cv = Canvas()
    grp = cond_group(cur_cond(d))
    pl_sky(cv, 9, 59, d, f, grp)
    pl_ground(cv, 59, f)
    cv.rect(0, 0, 64, 9, PL_INK)
    cv.text(32, 1, str(d.get("time", "")), (255, 255, 255), "gicko", "center", shadow=False)
    cv.text(1, 2, str(d.get("date", "")), (180, 180, 200), shadow=False)
    cv.text(63, 2, str(d.get("dow", "")), (255, 210, 80), align="right", shadow=False)
    night = str(d.get("sun", "")) == "below_horizon"
    cond = cur_cond(d)
    weather_icon(cv, 3, 10, 20, cond, night, f)
    # weather happens in the whole world
    if grp in ("rain", "storm", "snow"):
        for n in range(14):
            x = (_hash(n, 3, 5) % 64)
            y = 10 + (_hash(n, 4, 5) % 48 + f * (3 if grp != "snow" else 1)) % 48
            c = (180, 210, 255) if grp != "snow" else (255, 255, 255)
            cv.px(x, y, c)
            if grp != "snow":
                cv.px(x, y - 1, mix(c, (90, 110, 150), 0.5))
    pl_sign(cv, 28, 10, 35, 21, ropes=False)
    s = temp_str(cur_temp(d))
    if s:
        cv.text(45, 12, s, (70, 36, 14), "big", "center", shadow=False)
    today, nxt = today_and_next(d)
    if today:
        hi, lo = num(today.get("hi")), num(today.get("lo"))
        if hi is not None:
            tri(cv, 32, 25, UP[0], (200, 60, 30)); cv.text(38, 24, "%d" % round(hi), (150, 40, 20), shadow=False)
        if lo is not None:
            tri(cv, 47, 25, DOWN[0], (40, 80, 170)); cv.text(53, 24, "%d" % round(lo), (40, 80, 170), shadow=False)
    for n, day in enumerate(nxt[:4]):
        x = n * 16
        bob = round(math.sin(2 * math.pi * f / FRAMES + n * 1.5))
        iy = 47 + bob
        weekend = int(num(day.get("wd")) or 0) in (6, 7)
        cv.text(x + 8, 32 + bob, str(day.get("d", ""))[:2], (255, 220, 80) if weekend else (255, 255, 255),
                align="center", outline=PL_INK)
        weather_icon(cv, x + 3, 37 + bob, 10, day.get("c"), False, (f + n * 3) % FRAMES)
        for i in range(15):                                          # floating island
            depth = 2 + round(4 * math.sin(math.pi * (i + 0.5) / 15))
            cv.px(x + i, iy, PL_GRASS_L if i % 3 else PL_GRASS)
            for j in range(1, depth + 4):
                cv.px(x + i, iy + j, PL_DIRT if (i + j) % 3 else PL_DIRT_D)
        hi, lo = num(day.get("hi")), num(day.get("lo"))
        cv.text(x + 7, iy + 2, ("%d" % round(hi) if hi is not None else "-"), (255, 255, 255),
                align="center", outline=PL_INK)
        if lo is not None:
            cv.text(x + 7, 59, "%d" % round(lo), (150, 210, 255), align="center", outline=PL_INK)
    return cv.img


# ----------------------------------------------------------------------------
# Themes for every design: colour grade (data protected) + theme decorations
# ----------------------------------------------------------------------------
THEME_NAMES = ["neon", "steel", "synthwave", "crimson_desert", "christmas", "halloween", "retro_platformer"]
GRADES = {   # luminance ramp: dark -> light
    "neon": [(2, 4, 14), (20, 50, 140), (70, 160, 255), (225, 245, 255)],
    "steel": [(4, 5, 7), (48, 54, 64), (135, 145, 160), (235, 240, 248)],
    "synthwave": [(8, 0, 22), (90, 10, 120), (255, 60, 200), (140, 245, 255)],
    "crimson_desert": [(10, 1, 1), (110, 16, 16), (225, 120, 40), (255, 228, 160)],
    "christmas": [(0, 10, 4), (20, 95, 45), (205, 40, 40), (250, 250, 245)],
    "halloween": [(4, 0, 8), (75, 20, 115), (255, 120, 0), (255, 225, 160)],
    "retro_platformer": [(12, 20, 60), (40, 110, 255), (235, 120, 50), (255, 240, 180)],
}


def _ramp(stops, t):
    t = max(0.0, min(1.0, t)) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    return mix(stops[i], stops[i + 1], t - i)


def theme_post(cv, theme, f, page, strength=0.82):
    """Recolour everything except text/data towards the theme palette, then add its decorations."""
    stops = GRADES.get(theme)
    if not stops:
        return
    p = cv.p
    for y in range(64):
        for x in range(64):
            if (x, y) in cv.mask:
                continue
            c = p[x, y]
            if c in _SEMANTIC:
                continue
            t = (0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]) / 255
            p[x, y] = mix(c, _ramp(stops, t), strength)
    apply_theme(theme)
    cv.free_mode = True
    decorate(cv, f, page)
    if DECOR == "christmas" and not cv.tiles:                          # lights along the top edge
        cols = [(255, 40, 40), (40, 255, 80), (255, 200, 40), (60, 140, 255)]
        for n, x in enumerate(range(2, 64, 4)):
            if cv.is_bg(x, 0):
                cv.px(x, 0, cols[(n + MO.e() // 4) % 4])
    cv.free_mode = False


def resolve_theme(data, design):
    """'original' = the design's own look. 'seasonal (auto)', 'rotate' and legacy 'auto' supported."""
    name = str(data.get("theme") or "original").lower().strip()
    if name.startswith("seasonal") or name == "auto":
        md = str(data.get("today") or "")[5:10]
        if "12-01" <= md <= "12-31" or md <= "01-06":
            return "christmas"
        if "10-24" <= md <= "10-31":
            return "halloween"
        return "original"
    if name.startswith("rotate"):
        pool = ["original"] + THEME_NAMES
        return pool[(rotation_slot(data) + 3) % len(pool)]
    name = name.replace(" ", "_")
    return name if name in THEME_NAMES or name == "original" else "original"


def rotation_slot(data, override=None):
    """Integer that advances every rotation interval (hourly / every 6 hours / daily)."""
    interval = str(override or data.get("rotation") or "daily").lower()
    today = str(data.get("today") or "")
    try:
        day_no = datetime.date.fromisoformat(today[:10]).toordinal()
    except ValueError:
        day_no = datetime.date.today().toordinal()
    t = str(data.get("time") or "")
    hour = int(t.split(":")[0]) if t[:2].strip().isdigit() else 0
    if "hour" in interval and "6" not in interval:
        return day_no * 24 + hour
    if "6" in interval:
        return day_no * 4 + hour // 6
    return day_no


# ----------------------------------------------------------------------------
# STARSHIP  - original starship bridge: viewport onto space, violet hull, teal & gold console
# ----------------------------------------------------------------------------
SS_SPACE, SS_HULL, SS_HULL_L, SS_HULL_D = (1, 1, 8), (34, 30, 54), (78, 72, 112), (14, 12, 26)
SS_TEAL, SS_GOLD, SS_VIO, SS_TXT, SS_DIM = (40, 228, 210), (255, 188, 64), (150, 105, 255), (228, 240, 250), (120, 128, 165)
SS_STATE = {"run": SS_TEAL, "prep": SS_TEAL, "done": (80, 235, 110), "pause": SS_GOLD, "err": (255, 70, 70),
            "idle": (70, 72, 100), "off": (50, 50, 70)}


def ss_hull(cv):
    for y in range(64):
        for x in range(64):
            v = ((_hash(x // 8, y // 5, 51) % 5) - 2) * 0.03          # hull plating
            cv.px(x, y, shade(SS_HULL, v))
            if y % 5 == 0 and _hash(x // 8, y // 5, 52) % 3 == 0:
                cv.px(x, y, SS_HULL_D)


def ss_frame(cv, x, y, w, h):
    """Bevelled hull frame around a viewport or console pane (corners cut at 45 degrees)."""
    for i in range(x, x + w):
        cv.px(i, y, SS_HULL_L); cv.px(i, y + h - 1, SS_HULL_D)
    for j in range(y, y + h):
        cv.px(x, j, SS_HULL_L); cv.px(x + w - 1, j, SS_HULL_D)
    for (cx, cy) in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
        cv.px(cx, cy, SS_HULL)


def ss_space(cv, x0, y0, w, h, f, seed=1, vx=None, vy=None, n=34):
    """Viewport: deep space with a faint nebula; near stars rush outwards from the vanishing point."""
    vx = x0 + w / 2 if vx is None else vx
    vy = y0 + h / 2 if vy is None else vy
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            neb = math.sin(x * 0.17 + y * 0.09 + seed) + math.sin(x * 0.05 - y * 0.21 + 2 * seed)
            c = mix(SS_SPACE, (40, 14, 70), max(0.0, neb - 0.8) * 0.35)
            if _hash(x, y, 53 + seed) % 97 == 0:                      # distant fixed stars
                c = (90, 95, 130) if _hash(x, y, 54) % 3 else (170, 175, 210)
            cv.px(x, y, c)
    m = MO.m(3)
    rmax = math.hypot(w, h) * 0.6
    for i in range(n):
        hs = _hash(i, seed, 55)
        a = (hs % 628) / 100.0
        t = ((m / FRAMES) + (hs % 97) / 97.0) % 1.0                   # seamless: one pass per cycle
        r = 2 + rmax * t * t
        for k in range(2 if t > 0.55 else 1):                         # streak when close
            rr = r - k * 1.6
            x, y = round(vx + rr * math.cos(a)), round(vy + rr * math.sin(a) * 0.8)
            if x0 <= x < x0 + w and y0 <= y < y0 + h:
                cv.px(x, y, mix((90, 110, 170), (235, 245, 255), min(1.0, t * 1.4 - k * 0.4)))


def ss_planet(cv, cx, cy, r, f, x0=0, y0=0, x1=64, y1=64):
    """Ringed gas giant with drifting cloud bands, lit from the upper left."""
    m = MO.m(3)
    ring = []
    for k in range(int(r * 9)):
        a = 2 * math.pi * k / (r * 9)
        ring.append((cx + 1.75 * r * math.cos(a), cy + 0.42 * r * math.sin(a), math.sin(a)))
    def draw_ring(front):
        for (x, y, z) in ring:
            if (z > 0) == front and x0 <= x < x1 and y0 <= y < y1:
                cv.px(round(x), round(y), (200, 170, 120) if front else (110, 92, 70))
    draw_ring(False)
    for j in range(int(cy - r) - 1, int(cy + r) + 2):
        for i in range(int(cx - r) - 1, int(cx + r) + 2):
            if not (x0 <= i < x1 and y0 <= j < y1):
                continue
            dx, dy = (i + 0.5 - cx) / r, (j + 0.5 - cy) / r
            q = dx * dx + dy * dy
            if q > 1:
                continue
            dz = math.sqrt(1 - q)
            lon = math.asin(max(-1, min(1, dx / math.sqrt(max(1e-6, 1 - dy * dy))))) + m * 2 * math.pi / FRAMES
            band = math.sin(dy * 9 + 0.6 * math.sin(lon * 2))
            base = mix((150, 95, 200), (70, 200, 200), 0.5 + 0.5 * band)
            if band > 0.85: base = (235, 210, 255)
            lam = max(0.0, -0.55 * dx - 0.55 * dy + 0.62 * dz)
            cv.px(i, j, shade(base, -0.8 + 1.0 * lam))
    draw_ring(True)


def ss_running_lights(cv, y):
    """Effect: hull running lights chasing along an edge."""
    e = MO.e()
    for n, x in enumerate(range(3, 64, 6)):
        on = MO.fx and (n + e // 2) % 4 == 0
        cv.px(x, y, SS_GOLD if on else shade(SS_GOLD, -0.7))


def ss_shooting_star(cv, x0, y0, w, h, salt=5):
    """Effect: a comet crossing the viewport now and then."""
    p = MO.event(salt)
    if p is None:
        return
    x, y = x0 + w - round(p * (w + 10)), y0 + 2 + round(p * (h - 6) * 0.5)
    for k in range(5):
        if x0 <= x + k < x0 + w and y0 <= y - k // 2 < y0 + h:
            cv.px(x + k, y - k // 2, mix((255, 255, 255), (60, 120, 200), k / 5))


@protects
def ss_station(cv, x, y, w, h, a, f):
    """Crew station for one machine: status header, animated glyph, readout, console buttons."""
    cv.rect(x, y, w, h, SS_HULL_D)
    ss_frame(cv, x, y, w, h)
    k = a["k"]
    col = SS_STATE.get(k, SS_DIM)
    f1 = MO.m(1)
    hdr = col if not (k == "err" and (f1 // 4) % 2) else shade(col, -0.6)
    cv.rect(x + 1, y + 1, w - 2, 2, hdr)
    cx, cy = x + w // 2, y + 10
    run = k == "run"
    if a["kind"] in ("washer", "dryer"):
        for t in range(24):
            ang = 2 * math.pi * t / 24
            cv.px(round(cx + 4 * math.cos(ang)), round(cy + 4 * math.sin(ang)), SS_DIM)
        ang = (f1 if run else 0) * math.pi / 4
        for k2 in range(3):
            aa = ang + k2 * 2 * math.pi / 3
            cv.px(round(cx + 2.2 * math.cos(aa)), round(cy + 2.2 * math.sin(aa)), col if run else SS_DIM)
        cv.px(cx, cy, SS_TXT if run else SS_DIM)
        if a["kind"] == "dryer" and run:
            for n in range(2):
                cv.px(cx - 2 + n * 4 + ((f1 // 2) % 2), cy - 6, SS_GOLD)
    else:
        cv.rect(cx - 5, cy - 4, 11, 1, SS_DIM)
        nx = cx - 3 + ((f1 // 2) % 7 if run else 3)
        cv.px(nx, cy - 3, SS_GOLD); cv.px(nx, cy - 2, SS_GOLD if run else SS_DIM)
        pct = a.get("pct")
        hgt = 0 if pct is None else max(1, round(5 * pct / 100))
        if k == "done": hgt = 5
        cv.rect(cx - 2, cy + 4 - hgt + 1, 5, hgt, col)
        cv.rect(cx - 5, cy + 5, 11, 1, SS_DIM)
    cv.text(cx, y + h - 9, str(a["label"])[:5], col if k not in ("idle", "off") else SS_DIM, align="center", shadow=False)
    f2 = MO.m(2)
    for n in range(3):                                                # console buttons
        lit = (n + f2 // 4 + (1 if run else 0)) % 3 == 0
        cv.rect(x + 3 + n * 5, y + h - 3, 3, 1, [SS_TEAL, SS_GOLD, SS_VIO][n] if lit else shade([SS_TEAL, SS_GOLD, SS_VIO][n], -0.7))


def ss_readout(cv, x, y, w, label, temp, hum, salt):
    cv.text(x + 2, y, label, SS_TEAL, shadow=False)
    hv = num(hum)
    if hv is not None:
        cv.text(x + w - 2, y, "%d%%" % round(hv), SS_GOLD, align="right", shadow=False)
    s_ = temp_str(num(temp))
    if s_:
        tw = cv.text_width(s_, "big")
        cv.text(x + w // 2, y + 7, s_, SS_TXT, "big", "center", outline=(4, 4, 16),
                grad=[0.35, 0.25, 0.15, 0.05, 0, 0, -0.05, -0.1, -0.15, -0.2, -0.25], glint=glint_pos(0, tw, salt))


def render_dashboard_starship(d, f, variant=0):
    cv = Canvas()
    ss_hull(cv)
    # viewport with both temperatures
    ss_space(cv, 1, 1, 62, 22, f, seed=1)
    ss_shooting_star(cv, 1, 1, 62, 22)
    cv.rect(31, 1, 2, 22, SS_HULL)                                     # window strut
    cv.px(31, 1, SS_HULL_L); cv.px(32, 22, SS_HULL_D)
    ss_frame(cv, 0, 0, 64, 24)
    ss_readout(cv, 1, 2, 30, "IN", d.get("t_in"), d.get("h_in"), 0)
    ss_readout(cv, 33, 2, 30, "OUT", d.get("t_out"), d.get("h_out"), 1)
    # sensor strip: air quality cells + precipitation
    cv.rect(0, 25, 64, 12, SS_HULL_D)
    ss_frame(cv, 0, 25, 64, 12)
    cv.text(2, 29, "AQI", SS_TEAL, shadow=False)
    a = num(d.get("aqi"))
    if a is not None:
        a = max(0, a)
        cv.text(15, 28, "%d" % round(a), aqi_color(a), "gicko", shadow=False)
        lit = min(8, max(1, math.ceil(a / 300 * 8)))
        for n in range(8):
            c = aqi_color((n + 0.5) * 300 / 8)
            cv.rect(32 + n * 3, 29, 2, 4, c if n < lit else shade(c, -0.78))
    out = rain_outlook(d)
    if out is not None:
        f1 = MO.m(1)
        if out[0]:
            cv.sprite(57, 28, DROP[0], {"C": (60, 170, 255), "W": (220, 240, 255), "c": (30, 100, 200)}, shadow=False)
            cv.px(59, 34 + (f1 // 4) % 2, (60, 170, 255))
        else:
            for t in range(12):
                ang = 2 * math.pi * t / 12
                cv.px(round(59 + 2.5 * math.cos(ang)), round(31 + 2.5 * math.sin(ang)), SS_GOLD)
            cv.px(59, 31, SS_GOLD)
    # crew stations or sunrise / sunset
    if show_sun_card(d, variant):
        for n, (key, lab, rising) in enumerate((("sunrise", "RISE", True), ("sunset", "SET", False))):
            x = n * 32
            cv.rect(x, 38, 32, 26, SS_HULL_D)
            ss_space(cv, x + 1, 39, 30, 14, f, seed=3 + n, vx=x + 16, vy=52, n=10)
            for i in range(x + 1, x + 31):                             # planet horizon from orbit
                hy = 50 + round(((i - x - 16) / 15) ** 2 * 3)
                for j in range(hy, 53):
                    cv.px(i, j, mix((20, 60, 120), (60, 150, 220), (j - hy) / 3) if j > hy else (140, 210, 255))
            bob = 0 if MO.still(2) else round(math.sin(2 * math.pi * MO.m(2) / FRAMES))
            sy = (48 if rising else 49) + bob
            sx = x + (10 if rising else 22)
            for j in range(-2, 3):
                for i in range(-2, 3):
                    if i * i + j * j <= 5 and sy + j < 50 + round(((sx + i - x - 16) / 15) ** 2 * 3):
                        cv.px(sx + i, sy + j, (255, 230, 140) if i * i + j * j <= 2 else SS_GOLD)
            ss_frame(cv, x, 38, 32, 26)
            cv.text(x + 3, 41, lab, SS_TEAL, shadow=False)
            cv.text(x + 16, 55, str(d.get(key) or "--:--")[:5], SS_TXT, align="center", shadow=False)
    else:
        for n, ap in enumerate(appl_list(d)):
            ss_station(cv, n * 21 + (1 if n == 2 else 0), 38, 21, 26, ap, f)
    ss_running_lights(cv, 24)
    return cv.img


def render_weather_starship(d, f):
    cv = Canvas()
    ss_hull(cv)
    cv.rect(0, 0, 64, 10, SS_HULL_D)
    ss_frame(cv, 0, 0, 64, 10)
    cv.text(2, 3, str(d.get("date") or ""), SS_DIM, shadow=False)
    cv.text(32, 2, str(d.get("time") or ""), SS_TXT, "gicko", "center", shadow=False)
    today_ = today_date(d)
    weekend = today_ is not None and today_.weekday() >= 5
    cv.text(62, 3, str(d.get("dow") or ""), SS_GOLD if weekend else SS_TEAL, align="right", shadow=False)
    # viewport: space, ringed planet, current weather as a hologram
    ss_space(cv, 1, 12, 62, 23, f, seed=2, vx=20, vy=22)
    ss_planet(cv, 57, 18, 5, f, 48, 12, 63, 35)
    ss_shooting_star(cv, 1, 12, 62, 23)
    ss_frame(cv, 0, 11, 64, 25)
    weather_icon(cv, 2, 13, 14, cur_cond(d), str(d.get("sun", "")) == "below_horizon", f)
    s_ = temp_str(cur_temp(d))
    if s_:
        tw = cv.text_width(s_, "big")
        cv.text(33, 14, s_, SS_TXT, "big", "center", outline=(4, 4, 16),
                grad=[0.35, 0.25, 0.15, 0.05, 0, 0, -0.05, -0.1, -0.15, -0.2, -0.25], glint=glint_pos(0, tw))
    today, nxt = today_and_next(d)
    if today:
        hi, lo = num(today.get("hi")), num(today.get("lo"))
        x = 20
        if hi is not None:
            cv.sprite(x, 28, UP[0], {"#": SS_GOLD}, shadow=False)
            x += 6 + cv.text(x + 6, 27, "%d" % round(hi), SS_GOLD, outline=(4, 4, 16)) + 3
        if lo is not None:
            cv.sprite(x, 28, DOWN[0], {"#": SS_TEAL}, shadow=False)
            cv.text(x + 6, 27, "%d" % round(lo), SS_TEAL, outline=(4, 4, 16))
    ss_running_lights(cv, 36)
    # forecast consoles
    for n, day in enumerate(nxt[:4]):
        x = n * 16
        cv.rect(x, 38, 16, 26, SS_HULL_D)
        ss_frame(cv, x, 38, 16, 26)
        wd = fc_weekday(day)
        cv.text(x + 8, 40, str(day.get("d") or "")[:2], SS_GOLD if wd is not None and wd >= 5 else SS_TEAL,
                align="center", shadow=False)
        weather_icon(cv, x + 3, 46, 10, day.get("c"), False, (f + n * 3) % FRAMES)
        hi, lo = num(day.get("hi")), num(day.get("lo"))
        cv.text(x + 8, 57, "%d" % round(hi) if hi is not None else "-", SS_TXT, align="center", shadow=False)
    return cv.img


# ----------------------------------------------------------------------------
# Labels for the purist and kid designs (English / Hrvatski, selectable in HA)
# ----------------------------------------------------------------------------
LANGS = {
    "en": {
        "temp": "TEMP", "hum": "HUMID", "in": "IN", "out": "OUT", "aqi": "AQI",
        "rain": "RAIN TODAY", "no": "NO", "na": "--", "sunrise": "SUNRISE", "sunset": "SUNSET",
        "washer": "WASHER", "dryer": "DRYER", "printer": "PRINTER",
        "state": {"run": "RUNNING", "done": "DONE", "pause": "PAUSED", "err": "ERROR",
                  "prep": "STARTING", "off": "OFF", "idle": "IDLE"},
        "idle_for": ["IDLE FOR {a}", "IDLE {a}", "IDLE"],
        "aqi_words": [["GOOD"], ["MODERATE", "MEDIUM"], ["POOR"], ["UNHEALTHY", "BAD"],
                      ["VERY BAD", "V. BAD"], ["HAZARD"]],
        "days": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"],
        "days3": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
        "months": ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"],
        "date": "{d} {m}",
        "cond": {"sunny": "SUNNY", "clear-night": "CLEAR", "partlycloudy": "PARTLY CLOUDY",
                 "cloudy": "CLOUDY", "rainy": "RAIN", "pouring": "HEAVY RAIN", "lightning": "THUNDER",
                 "lightning-rainy": "THUNDERSTORM", "snowy": "SNOW", "snowy-rainy": "SLEET", "hail": "HAIL",
                 "fog": "FOG", "windy": "WINDY", "windy-variant": "WINDY", "exceptional": "WARNING"},
        "kid_in": "IN", "kid_out": "OUT",
        "kid_state": {"run": "RUN", "done": "DONE", "pause": "WAIT", "err": "OOPS", "prep": "...",
                      "off": "ZZZ", "idle": "ZZZ"},
    },
    "hr": {
        "temp": "TEMP.", "hum": "VLAGA", "in": "SOBA", "out": "VANI", "aqi": "ZRAK",
        "rain": "KIŠA DANAS", "no": "NE", "na": "--", "sunrise": "IZLAZAK", "sunset": "ZALAZAK",
        "washer": "PERILICA", "dryer": "SUŠILICA", "printer": "PISAČ",
        "state": {"run": "RADI", "done": "GOTOVO", "pause": "PAUZA", "err": "GREŠKA",
                  "prep": "PRIPREMA", "off": "UGAŠEN", "idle": "MIRUJE"},
        "idle_for": ["MIRUJE {a}", "MIRUJE"],
        "aqi_words": [["DOBAR"], ["UMJEREN"], ["SLAB"], ["NEZDRAV", "LOŠ"], ["VRLO LOŠ", "LOŠ"],
                      ["OPASAN"]],
        "days": ["PONEDJELJAK", "UTORAK", "SRIJEDA", "ČETVRTAK", "PETAK", "SUBOTA", "NEDJELJA"],
        "days3": ["PON", "UTO", "SRI", "ČET", "PET", "SUB", "NED"],
        "months": ["SIJ", "VELJ", "OŽU", "TRA", "SVI", "LIP", "SRP", "KOL", "RUJ", "LIS", "STU", "PRO"],
        "date": "{d}. {m}",
        "cond": {"sunny": "SUNČANO", "clear-night": "VEDRO", "partlycloudy": "DJEL. OBLAČNO",
                 "cloudy": "OBLAČNO", "rainy": "KIŠA", "pouring": "PLJUSAK", "lightning": "GRMLJAVINA",
                 "lightning-rainy": "OLUJA", "snowy": "SNIJEG", "snowy-rainy": "SUSNJEŽICA", "hail": "TUČA",
                 "fog": "MAGLA", "windy": "VJETROVITO", "windy-variant": "VJETROVITO", "exceptional": "UPOZORENJE"},
        "kid_in": "KUĆA", "kid_out": "VANI",
        "kid_state": {"run": "RADI", "done": "GOTOV", "pause": "ČEKA", "err": "JOJ!", "prep": "...",
                      "off": "ZZZ", "idle": "ZZZ"},
    },
}


def tr(d):
    v = str(d.get("lang") or "english").lower()
    return LANGS["hr" if v.startswith(("hr", "cro")) else "en"]


def aqi_level(a):
    """0..5 = US AQI category."""
    for i, lim in enumerate((50, 100, 150, 200, 300)):
        if a <= lim:
            return i
    return 5


def age_short(sec):
    sec = num(sec)
    if sec is None or sec < 0:
        return None
    if sec < 3600: return "%dMIN" % max(1, sec // 60)
    if sec < 172800: return "%dH" % (sec // 3600)
    return "%dD" % min(99, sec // 86400)


def first_rain_hour(d):
    """'HH:00' of the first hour with expected rain later today, False if dry, None if unknown."""
    out = rain_outlook(d)
    if out is None:
        return None
    if not out[0]:
        return False
    for h in (d.get("hourly") if isinstance(d.get("hourly"), list) else []):
        if not isinstance(h, dict):
            continue
        p, mm, c = num(h.get("p")), num(h.get("mm")), str(h.get("c") or "").lower()
        if (p is not None and p >= RAIN_PROB) or (mm is not None and mm >= RAIN_MM) or c in RAINY:
            t = str(h.get("t") or "")[:2]
            return (t + ":00") if t.isdigit() else True
    return True


def today_date(d):
    try:
        return datetime.date.fromisoformat(str(d.get("today") or "")[:10])
    except ValueError:
        return None


def fc_weekday(day):
    """0 = Monday ... from a forecast entry (date, then 'wd' 1..7)."""
    try:
        return datetime.date.fromisoformat(str(day.get("date") or "")[:10]).weekday()
    except ValueError:
        wd = num(day.get("wd"))
        return int(wd) - 1 if wd and 1 <= wd <= 7 else None


def fit(cv, options, font, maxw):
    """First text option that fits in maxw pixels (last one as a fallback)."""
    options = [o for o in options if o]
    for o in options:
        if cv.text_width(o, font) <= maxw:
            return o
    return options[-1] if options else ""


# ----------------------------------------------------------------------------
# PURIST  - clean and clear: labelled values, units on everything, words not codes
# ----------------------------------------------------------------------------
PU_ICONS = {   # 7x7, letters = colour roles
    "sun": ["...y...", ".y...y.", "..yyy..", "y.yyy.y", "..yyy..", ".y...y.", "...y..."],
    "sun2": ["...y...", "...y...", "..yyy..", "yyyyyyy", "..yyy..", "...y...", "...y..."],
    "night": ["..mmm..", ".mmm...", "mmm....", "mmm....", "mmm....", ".mmm...", "..mmm.."],
    "partly": [".y.y...", "..y....", "y.yccc.", "..ccccc", ".cccccc", "ccccccc", "......."],
    "cloud": [".......", "...cc..", "..cccc.", ".cccccc", "ccccccc", "ccccccc", "......."],
    "rain": ["..ccc..", ".ccccc.", "ccccccc", ".......", ".b..b..", "b..b..b", "..b..b."],
    "rain2": ["..ccc..", ".ccccc.", "ccccccc", ".......", "b..b..b", "..b..b.", ".b..b.."],
    "storm": ["..ccc..", ".ccccc.", "ccccccc", "...a...", "..aa...", "...a...", "..a...."],
    "snow": ["..ccc..", ".ccccc.", "ccccccc", ".......", "w..w..w", ".......", ".w..w.."],
    "snow2": ["..ccc..", ".ccccc.", "ccccccc", ".......", ".w..w..", ".......", "w..w..w"],
    "fog": [".......", "ccccc..", ".......", "..ccccc", ".......", "ccccc..", "......."],
    "wind": [".......", "cccc.c.", "....c..", "ccccc..", ".......", "ccc.c..", "....c.."],
    "unknown": ["..ccc..", ".c...c.", ".....c.", "...cc..", "...c...", ".......", "...c..."],
}


def pu_pal():
    """Ink colours that suit the chosen background (dark ink on light paper, light ink on dark)."""
    light = bool(BACKDROP and BACKDROP["light"])
    mean = tuple(int(v) for v in BACKDROP["mean"]) if BACKDROP else (0, 0, 0)
    if light:
        return {"light": True, "bg": mean, "ink": (16, 18, 24), "label": mix((16, 18, 24), mean, 0.4),
                "rule": mix((16, 18, 24), mean, 0.75),
                "ok": (20, 120, 50), "warn": (170, 95, 0), "err": (190, 20, 20), "info": (20, 90, 175),
                "y": (190, 130, 0), "m": (90, 90, 130), "c": (110, 115, 130), "b": (30, 100, 210),
                "a": (200, 120, 0), "w": (120, 140, 175)}
    return {"light": False, "bg": mean, "ink": (238, 238, 232), "label": mix((215, 222, 235), mean, 0.36),
            "rule": mix((150, 160, 180), mean, 0.7),
            "ok": (90, 220, 120), "warn": (255, 190, 70), "err": (255, 85, 70), "info": (110, 190, 255),
            "y": (255, 205, 80), "m": (200, 205, 235), "c": (165, 172, 190), "b": (90, 165, 255),
            "a": (255, 190, 60), "w": (235, 240, 255)}


def pu_text(cv, x, y, s, c, font="plain", align="left", glint=None):
    """Flat text with a halo in the background colour (keeps letters clean on patterns)."""
    P = pu_pal()
    return cv.text(x, y, s, c, font, align, shadow=False, outline=P["bg"] if BACKDROP else None,
                   glint=glint)


def pu_icon_name(cond, f):
    g = cond_group(cond)
    step = (f // 4) % 2
    if g == "sun": return "sun2" if step else "sun"
    if g == "rain": return "rain2" if step else "rain"
    if g == "snow": return "snow2" if step else "snow"
    return g if g in PU_ICONS else "unknown"


@protects
def pu_icon(cv, x, y, cond, f, rows=7):
    P = pu_pal()
    name = pu_icon_name(cond, f)
    grid = PU_ICONS[name]
    if rows < 7:                      # compact forecast version: drop blank / sparse rows
        grid = [r for r in grid if r.strip(".")][:rows]
    storm_dim = cond_group(cond) == "storm" and (f // 2) % 4 == 3
    for j, r in enumerate(grid):
        for i, ch in enumerate(r):
            if ch != ".":
                c = P[ch]
                if ch == "a" and storm_dim:
                    c = shade(c, -0.5)
                cv.px(x + i, y + j, c)


def pu_rule(cv, y, P):
    for x in range(64):
        cv.px(x, y, P["rule"])


def pu_state_color(P, k):
    return {"run": P["info"], "prep": P["info"], "done": P["ok"], "pause": P["warn"], "err": P["err"]}.get(k, P["label"])


def render_dashboard_purist(d, f, variant=0):
    cv = Canvas()
    P, T = pu_pal(), tr(d)
    f1 = MO.m(1)
    TCOL = 38                                         # right edge of the temperature column
    pu_text(cv, TCOL, 0, T["temp"], P["label"], align="right")       # column headers
    pu_text(cv, 63, 0, T["hum"], P["label"], align="right")
    for y, lab, t, h, salt in ((7, T["in"], d.get("t_in"), d.get("h_in"), 0),
                               (16, T["out"], d.get("t_out"), d.get("h_out"), 1)):
        pu_text(cv, 0, y + 2, lab, P["label"])
        ts = temp_str(num(t)) or "--"
        pu_text(cv, TCOL, y, ts, P["ink"], "clear", "right", glint=glint_pos(f, 20, salt))
        hv = num(h)
        pu_text(cv, 63, y, ("%d%%" % round(hv)) if hv is not None else "--", P["ink"], "clear", "right")
    pu_rule(cv, 25, P)
    # air quality: number in its category colour + the category in words
    a = num(d.get("aqi"))
    vx = pu_text(cv, 0, 29, T["aqi"], P["label"]) + 3
    if a is None:
        pu_text(cv, vx, 27, "--", P["ink"], "clear")
    else:
        a = max(0, a)
        col = aqi_color(a)
        if P["light"]:
            col = shade(col, -0.45)
        _SEMANTIC.add(col)
        vw = pu_text(cv, vx, 27, "%d" % round(a), col, "clear")
        word = fit(cv, T["aqi_words"][aqi_level(a)], "plain", 63 - (vx + vw + 3))
        pu_text(cv, 63, 29, word, col, align="right")
    # rain later today
    pu_text(cv, 0, 38, T["rain"], P["label"])
    rh = first_rain_hour(d)
    if rh is None:
        pu_text(cv, 63, 38, T["na"], P["label"], align="right")
    elif rh is False:
        pu_text(cv, 63, 38, T["no"], P["ink"], align="right")
    elif rh is True:
        pu_text(cv, 63, 38, "!", P["info"], align="right")
    else:
        pu_text(cv, 63, 36, rh, P["info"], "clear", "right")
    pu_rule(cv, 45, P)
    # bottom: appliances, or sunrise / sunset
    if show_sun_card(d, variant):
        for y, lab, key in ((47, T["sunrise"], "sunrise"), (56, T["sunset"], "sunset")):
            pu_text(cv, 0, y + 2, lab, P["label"])
            pu_text(cv, 63, y, str(d.get(key) or "--:--")[:5], P["ink"], "clear", "right")
        return cv.img
    names = {"washer": T["washer"], "dryer": T["dryer"], "printer": T["printer"]}
    ages = {"washer": d.get("wm_age"), "dryer": d.get("td_age"), "printer": d.get("pr_age")}
    for n, ap in enumerate(appl_list(d)):
        y = 47 + n * 6
        name = names[ap["kind"]]
        pu_text(cv, 0, y, name, P["label"])
        k = ap["k"]
        room = 63 - cv.text_width(name, "plain") - 4
        if k == "idle":
            age = age_short(ages[ap["kind"]])
            opts = [o.format(a=age) for o in T["idle_for"]] if age else [T["state"]["idle"]]
        elif k == "run" and ap["kind"] == "printer":
            mins = int(num(d.get("pr_left")) or 0)
            if mins >= 60:
                lefts = ["%dH%02dM" % (mins // 60, mins % 60), "%dH%02d" % (mins // 60, mins % 60)]
            else:
                lefts = ["%dMIN" % mins, "%dM" % mins]
            pct = ap["pct"]
            if pct is not None:
                opts = ["%d%% %s" % (round(pct), lf) for lf in lefts] + ["%d%%" % round(pct)]
            else:
                opts = lefts + [T["state"]["run"]]
        else:
            opts = [T["state"].get(k, k.upper())]
        txt = fit(cv, opts, "plain", room)
        col = pu_state_color(P, k)
        if k == "err" and (f1 // 4) % 2:
            col = shade(col, -0.5) if not P["light"] else mix(col, P["bg"], 0.6)
        elif k in ("run", "prep"):
            col = mix(col, P["ink"], pulse(f1, 0.0, 0.35))
        pu_text(cv, 63, y, txt, col, align="right")
    return cv.img


def render_weather_purist(d, f):
    cv = Canvas()
    P, T = pu_pal(), tr(d)
    f1, f2 = MO.m(1), MO.m(2)
    pu_text(cv, 32, 0, str(d.get("time") or "--:--")[:5], P["ink"], "clear2", "center")
    dt = today_date(d)
    if dt:
        line = T["days"][dt.weekday()] + " " + T["date"].format(d=dt.day, m=T["months"][dt.month - 1])
    else:
        line = str(d.get("dow") or "") + " " + str(d.get("date") or "")
    pu_text(cv, 32, 16, fit(cv, [line, line.split(" ", 1)[-1]], "plain", 64), P["label"], align="center")
    cond = cur_cond(d)
    pu_icon(cv, 0, 23, cond, f1)
    pu_text(cv, 9, 23, temp_str(cur_temp(d)) or "--", P["ink"], "clear", glint=glint_pos(f, 20))
    today, nxt = today_and_next(d)
    if today:
        hi, lo = num(today.get("hi")), num(today.get("lo"))
        hs = "↑" + (("%d°" % round(hi)) if hi is not None else "--")
        ls = "↓" + (("%d°" % round(lo)) if lo is not None else "--")
        lw = pu_text(cv, 63, 25, ls, P["label"], align="right")
        pu_text(cv, 63 - lw - 3, 25, hs, P["ink"], align="right")
    word = T["cond"].get(cond, cond.upper()[:14] if cond else T["na"])
    pu_text(cv, 32, 32, fit(cv, [word, word.split(" ")[-1]], "plain", 64), P["ink"], align="center")
    pu_rule(cv, 38, P)
    for n, day in enumerate(nxt[:4]):
        y = 40 + n * 6
        wd = fc_weekday(day)
        name = T["days3"][wd] if wd is not None else str(day.get("d") or "")[:3]
        pu_text(cv, 0, y, name, P["label"])
        pu_icon(cv, 16, y, day.get("c"), (f2 + n * 3) % FRAMES, rows=5)
        hi, lo = num(day.get("hi")), num(day.get("lo"))
        pu_text(cv, 44, y, "↑" + (("%d°" % round(hi)) if hi is not None else "--"), P["ink"], align="right")
        pu_text(cv, 63, y, "↓" + (("%d°" % round(lo)) if lo is not None else "--"), P["label"], align="right")
    return cv.img


# ----------------------------------------------------------------------------
# KID  - drawn by a five-year-old with crayons on white paper
# ----------------------------------------------------------------------------
KID_C = {"red": (225, 45, 45), "orange": (245, 135, 25), "yellow": (240, 196, 20), "green": (50, 165, 60),
         "lgreen": (120, 205, 80), "blue": (40, 100, 220), "lblue": (100, 175, 240), "purple": (140, 70, 200),
         "brown": (140, 85, 45), "pink": (240, 110, 170), "ink": (40, 40, 50), "grey": (140, 140, 150),
         "white": (250, 250, 250)}
KID_RAINBOW = ["red", "orange", "green", "blue", "purple", "pink"]
# kid_dark: gel pens on black paper - saturated colours bright enough to read on black, but no
# pastel/white wash, and sparser scribbles so far fewer LEDs are lit than on white paper.
KID_DARK_C = {"red": (255, 70, 70), "orange": (255, 150, 40), "yellow": (255, 214, 50), "green": (70, 210, 80),
              "lgreen": (110, 225, 95), "blue": (70, 140, 255), "lblue": (100, 180, 255), "purple": (185, 110, 255),
              "brown": (195, 125, 70), "pink": (255, 115, 190), "ink": (225, 225, 215), "grey": (150, 152, 168),
              "white": (95, 100, 118), "cloud": (95, 135, 200)}
KID_STYLE = "paper"


def kid_pal():
    """Crayon box for the current paper: crayons on light paper, chalk on dark backgrounds,
    gel pens for the kid_dark design."""
    paper = tuple(int(v) for v in BACKDROP["mean"]) if BACKDROP else (238, 234, 224)
    light = bool(BACKDROP["light"]) if BACKDROP else True
    if KID_STYLE == "dark":
        K = dict(KID_DARK_C)
        K["paper"], K["light"], K["sparse"] = paper, False, True
        K["boil"] = (MO.m(5) // 3) % 3
        return K
    K = dict(KID_C) if light else {k: mix(v, (255, 255, 255), 0.45) for k, v in KID_C.items()}
    if not light:
        K["ink"] = (240, 240, 232)
        K["white"] = (200, 205, 215)
    else:
        K["yellow"] = (232, 180, 0)          # a yellow you can read on white paper
    K["paper"], K["light"], K["sparse"] = paper, light, False
    K["cloud"] = K["lblue"] if light else K["white"]
    K["boil"] = (MO.m(5) // 3) % 3        # hand-drawn "line boil" (motion level 5 only)
    return K


def kpx(cv, x, y, c, K, seed=0):
    """A crayon pixel: wax with gaps where the paper grain shows through."""
    x, y = int(round(x)), int(round(y))
    if _hash(x, y, 77 + seed) % 6 == 0:
        c = mix(c, K["paper"], 0.45)
    cv.px(x, y, c)


def kline(cv, x0, y0, x1, y1, c, K, wob=0.6, seed=0):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(int(n) + 1):
        t = i / n
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        w = wob * math.sin(t * 3.1 + seed + K["boil"] * 1.7)
        if abs(x1 - x0) >= abs(y1 - y0):
            y += w
        else:
            x += w
        kpx(cv, x, y, c, K, seed)


def kfill(cv, inside, x0, y0, x1, y1, c, K, seed=0, dens=3):
    """Scribble fill: diagonal crayon strokes with gaps, sometimes going over the line."""
    b = K["boil"]
    for y in range(int(y0), int(y1) + 1):
        for x in range(int(x0), int(x1) + 1):
            if inside(x, y):
                if K["sparse"]:            # gel-pen hatching: half the pixels, follows the strokes
                    if (x - y + seed + b) % 2 == 0 and _hash(x, y, seed + 5) % 6:
                        kpx(cv, x, y, c, K, seed)
                elif (x - y + seed + b) % dens != 0 or _hash(x, y, seed + 5) % 4 == 0:
                    kpx(cv, x, y, c, K, seed)
            elif inside(x - 1, y + 1) and _hash(x, y, seed + b) % 7 == 0:
                kpx(cv, x, y, c, K, seed)                         # coloured outside the lines


def kring(cv, cx, cy, r, c, K, seed=0, fill=None, start=0.0, end=2 * math.pi):
    if fill is not None:
        kfill(cv, lambda x, y: (x - cx) ** 2 + (y - cy) ** 2 <= (r - 0.6) ** 2,
              cx - r, cy - r, cx + r, cy + r, fill, K, seed)
    steps = int(2 * math.pi * r * 1.7) + 8
    for i in range(steps):
        a = start + (end - start) * i / steps
        rr = r + 0.45 * math.sin(a * 3 + seed + K["boil"] * 2.1)
        kpx(cv, cx + rr * math.cos(a), cy + rr * math.sin(a), c, K, seed)


def ktext(cv, x, y, s, c, K, font="plain", align="left", rainbow=False, seed=0, jitter=True):
    """Hand-written text: every letter sits a little differently on the line."""
    s = str(s)
    w = cv.text_width(s, font)
    if align == "center": x -= w // 2
    elif align == "right": x -= w
    cx = x
    for i, ch in enumerate(s):
        gw = cv.glyph(font, ch)[0]
        dy = -1 if (jitter and ch != " " and _hash(i, seed, 5 + K["boil"]) % 3 == 0) else 0
        col = K[KID_RAINBOW[(i + seed) % len(KID_RAINBOW)]] if rainbow else c
        cv.text(cx, y + dy, ch, col, font, shadow=False,
                colfn=lambda xx, yy, j, col=col: col if _hash(xx, yy, 91) % 7 else mix(col, K["paper"], 0.4))
        cx += gw + 1
    return w


def kid_temp_color(v, K):
    if v is None: return K["grey"]
    if v < 0: return K["purple"]
    if v < 10: return K["blue"]
    if v < 18: return K["green"]
    if v < 25: return K["orange"]
    return K["red"]


def kid_house(cv, x, y, K, f):
    f3 = MO.m(3)
    kfill(cv, lambda i, j: 2 <= i - x <= 12 and 6 <= j - y <= 13, x + 2, y + 6, x + 12, y + 13, K["yellow"], K, 1)
    for (a, b, c_, d_) in ((x + 2, y + 6, x + 2, y + 13), (x + 12, y + 6, x + 12, y + 13), (x + 2, y + 13, x + 12, y + 13)):
        kline(cv, a, b, c_, d_, K["brown"], K, 0.3, 2)
    kfill(cv, lambda i, j: 10 <= i - x <= 11 and 1 <= j - y <= 4, x + 10, y + 1, x + 11, y + 4, K["brown"], K, 3, 9)
    roof = lambda i, j: 0 <= j - y <= 6 and abs(i - x - 7) <= (j - y) * 7 / 6 + 0.3
    kfill(cv, roof, x, y, x + 14, y + 6, K["red"], K, 4)
    kline(cv, x, y + 6, x + 7, y, K["red"], K, 0.3, 5)
    kline(cv, x + 7, y, x + 14, y + 6, K["red"], K, 0.3, 6)
    kfill(cv, lambda i, j: 4 <= i - x <= 6 and 10 <= j - y <= 13, x + 4, y + 10, x + 6, y + 13, K["brown"], K, 7, 9)
    for i in range(3):
        for j in range(3):
            if i == 1 or j == 1 or (i, j) in ((0, 0), (2, 2), (0, 2), (2, 0)):
                kpx(cv, x + 8 + i, y + 8 + j, K["blue"], K)
    for n in range(2):                                              # chimney smoke
        ph = (f3 + n * 8) % FRAMES
        sx, sy = x + 11 + round(math.sin(ph * 0.6)), y - 1 - ph // 4
        if sy >= 0 and (MO.level >= 3 or n == 0):
            kpx(cv, sx, sy, K["grey"], K)


def kid_tree(cv, x, y, K, f):
    sway = round(math.sin(2 * math.pi * MO.m(3) / FRAMES)) if MO.level >= 3 else 0
    kline(cv, x + 7, y + 8, x + 7, y + 14, K["brown"], K, 0.2, 1)
    kline(cv, x + 8, y + 8, x + 8, y + 14, K["brown"], K, 0.2, 2)
    kring(cv, x + 7 + sway, y + 5, 5, K["green"], K, 3, fill=K["lgreen"])
    for (ax, ay) in ((4, 4), (9, 3), (7, 7)):
        kpx(cv, x + ax + sway, y + ay, K["red"], K)


def kid_drop(cv, x, y, K):
    for j, row in enumerate(["..#..", ".###.", "#####", "#####", ".###."]):
        for i, ch in enumerate(row):
            if ch == "#":
                kpx(cv, x + i, y + j, K["blue"] if (i, j) != (1, 2) else K["white"], K)


def kid_face(cv, cx, cy, r, level, K, f):
    """AQI as a crayon face: big smile when the air is good, frown when it is bad."""
    fills = [K["lgreen"], K["yellow"], K["orange"], K["red"], K["purple"], K["brown"]]
    mood = fills[min(level, 5)]
    if K["sparse"]:          # dark paper: mood-coloured outline, dim hatching, bright features
        kfill(cv, lambda x, y: (x - cx) ** 2 + (y - cy) ** 2 <= (r - 0.6) ** 2,
              cx - r, cy - r, cx + r, cy + r, shade(mood, -0.6), K, 11)
        kring(cv, cx, cy, r, mood, K, 11)
    else:
        kring(cv, cx, cy, r, K["ink"], K, 11, fill=mood)
    blink = MO.m(2) == 13
    for ex in (cx - 2, cx + 2):
        if blink:
            kpx(cv, ex - 1, cy - 2, K["ink"], K); kpx(cv, ex, cy - 2, K["ink"], K)
        elif level >= 4:
            kpx(cv, ex - 1, cy - 3, K["ink"], K); kpx(cv, ex, cy - 2, K["ink"], K)
            kpx(cv, ex - 1, cy - 1, K["ink"], K); kpx(cv, ex, cy - 3, K["ink"], K); kpx(cv, ex - 1, cy - 1, K["ink"], K)
        else:
            kpx(cv, ex, cy - 2, K["ink"], K); kpx(cv, ex, cy - 1, K["ink"], K)
    if level <= 1:
        mouth = [(-3, 1), (-2, 2), (-1, 3), (0, 3), (1, 3), (2, 2), (3, 1)]
    elif level == 2:
        mouth = [(-2, 2), (-1, 2), (0, 2), (1, 2), (2, 2)]
    else:
        mouth = [(-3, 3), (-2, 2), (-1, 1), (0, 1), (1, 1), (2, 2), (3, 3)]
    for (dx, dy) in mouth:
        kpx(cv, cx + dx, cy + dy, K["ink"], K)


def kid_sun(cv, cx, cy, r, K, f, face=True, shades=False, ray=3.5):
    rot = (f // 2) % 2
    for k in range(8):
        a = (k + 0.5 * rot) * math.pi / 4
        kline(cv, round(cx + (r + 1.5) * math.cos(a)), round(cy + (r + 1.5) * math.sin(a)),
              round(cx + (r + ray) * math.cos(a)), round(cy + (r + ray) * math.sin(a)), K["orange"], K, 0, k)
    kring(cv, cx, cy, r, K["orange"], K, 21, fill=K["yellow"])
    if not face:
        return
    if shades:
        for i in range(-3, 4):
            kpx(cv, cx + i, cy - 1, K["ink"], K)
        for dx in (-3, -2, 2, 3):
            kpx(cv, cx + dx, cy, K["ink"], K)
    else:
        kpx(cv, cx - 2, cy - 1, K["ink"], K); kpx(cv, cx + 2, cy - 1, K["ink"], K)
    if r >= 4:
        for dx, dy in ((-2, 2), (-1, 3), (0, 3), (1, 3), (2, 2)):
            kpx(cv, cx + dx, cy + dy, K["red"], K)


def kid_moon(cv, cx, cy, r, K, f):
    inside = lambda x, y: (x - cx) ** 2 + (y - cy) ** 2 <= r * r and (x - cx - r * 0.6) ** 2 + (y - cy + r * 0.3) ** 2 > (r * 0.85) ** 2
    kfill(cv, inside, cx - r, cy - r, cx + r, cy + r, K["yellow"], K, 31)
    kpx(cv, cx - r // 2, cy, K["ink"], K)
    if r >= 5:
        z = MO.m(1)
        ktext(cv, cx + r - 1, cy - r - 1 - (z // 8), "Z", K["blue"], K, jitter=False)


def kid_cloud(cv, cx, cy, S, K, col=None, out=None, seed=0):
    col = col or K["cloud"]
    out = out or K["blue"]
    blobs = [(-0.28, 0.05, 0.22), (0.0, -0.12, 0.3), (0.28, 0.06, 0.22)]
    inside = lambda x, y: any((x - (cx + bx * S)) ** 2 + (y - (cy + by * S)) ** 2 <= (br * S) ** 2
                              for bx, by, br in blobs) and y <= cy + 0.24 * S
    x0, x1, y0, y1 = cx - 0.52 * S, cx + 0.52 * S, cy - 0.44 * S, cy + 0.26 * S
    kfill(cv, inside, x0, y0, x1, y1, col, K, 41 + seed)
    for y in range(int(y0), int(y1) + 2):                          # crayon outline
        for x in range(int(x0) - 1, int(x1) + 2):
            if not inside(x, y) and any(inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                kpx(cv, x, y, out, K, seed)


def kid_weather(cv, cx, cy, S, cond, K, f):
    """Weather drawn with crayons, S = drawing size (18 big, 9 mini)."""
    g = cond_group(cond)
    big = S >= 14
    if g == "sun":
        kid_sun(cv, cx, cy, max(2, round(S * 0.28)), K, f, face=big)
    elif g == "night":
        kid_moon(cv, cx, cy, max(3, round(S * 0.36)), K, f)
        if big:
            for n, (sx, sy) in enumerate(((-7, -6), (6, 5), (7, -7))):
                if (f // 4 + n) % 3:
                    kpx(cv, cx + sx, cy + sy, K["yellow"], K)
    elif g == "partly":
        kid_sun(cv, round(cx - S * 0.18), round(cy - S * 0.18), max(2, round(S * 0.2)), K, f, face=False)
        kid_cloud(cv, round(cx + S * 0.08), round(cy + S * 0.1), S * 0.8, K)
    elif g in ("cloud", "fog", "wind", "unknown"):
        kid_cloud(cv, cx, cy, S, K, col=K["white"] if g != "cloud" else None, out=K["grey"] if g != "cloud" else None)
        if g == "fog":
            for n in range(2):
                y = round(cy + S * 0.32) + n * 2
                for i in range(-S // 2, S // 2):
                    if (i + n * 2 + f // 2) % 5 < 3:
                        kpx(cv, cx + i, y, K["grey"], K)
        if g == "wind":
            for n in range(2):
                y = round(cy + S * 0.32) + n * 2
                off = (f + n * 3) % 6
                for i in range(-S // 2 + off, S // 2 - 3 + off):
                    kpx(cv, cx + i, y, K["blue"], K)
    else:
        kid_cloud(cv, cx, round(cy - S * 0.12), S, K, col=K["grey"] if g == "storm" else None,
                  out=K["ink"] if g == "storm" else None)
        top, n_ = round(cy + S * 0.18), (4 if big else 2)
        for n in range(n_):
            x = round(cx - S * 0.32 + n * (S * 0.64 / max(1, n_ - 1)))
            if g == "snow":
                y = top + (f // 2 + n * 3) % max(2, S // 3)
                for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)) if big else ((0, 0),):
                    kpx(cv, x + dx, y + dy, K["lblue"] if K["light"] else K["ink"], K)
            else:
                y = top + (f + n * 3) % max(2, S // 3)
                kpx(cv, x, y, K["blue"], K); kpx(cv, x - 1, y + 1, K["blue"], K)
        if g == "storm" and (f // 2) % 4 != 3:
            bx, by = cx, round(cy + S * 0.05)
            for i, (dx, dy) in enumerate(((1, 0), (0, 1), (-1, 2), (1, 2), (0, 3), (-1, 4)) if big else ((0, 0), (-1, 1), (0, 2))):
                kpx(cv, bx + dx, by + dy, K["yellow"], K)


def kid_umbrella(cv, x, y, rain, K, f):
    """Rain later today: open umbrella in the rain. Dry: the sun wears sunglasses."""
    if not rain:
        kid_sun(cv, x + 9, y + 7, 4, K, f, shades=True)
        return
    cx, cy = x + 9, y + 7
    canopy = lambda i, j: (i - cx) ** 2 + (j - cy) ** 2 <= 49 and j <= cy
    kfill(cv, canopy, cx - 7, cy - 7, cx + 7, cy, K["purple"], K, 51)
    for i in range(-7, 8):
        if canopy(cx + i, cy - 1) and abs(i) % 4 == 2:
            for j in range(-6, 1):
                if canopy(cx + i, cy + j):
                    kpx(cv, cx + i, cy + j, K["pink"], K)
    kline(cv, cx, cy, cx, cy + 7, K["ink"], K, 0, 3)
    kpx(cv, cx - 1, cy + 7, K["ink"], K); kpx(cv, cx - 2, cy + 6, K["ink"], K)
    for n in range(5):                                              # rain falling around
        dx = (-8, -5, 5, 8, -10)[n]
        dy = (f + n * 3) % 10 - 7
        if not canopy(cx + dx, cy + dy):
            kpx(cv, cx + dx, cy + dy, K["blue"], K); kpx(cv, cx + dx, cy + dy + 1, K["blue"], K)


def kid_appliance(cv, x, y, a, K, f):
    """13x10 crayon machine; animations only while it works."""
    k = a["k"]
    f1 = MO.m(1)
    kfill(cv, lambda i, j: 0 < i - x < 12 and 0 < j - y < 9, x, y, x + 12, y + 9, K["white"], K, 61, 4)
    for (a0, b0, a1, b1) in ((x, y, x + 12, y), (x, y + 9, x + 12, y + 9), (x, y, x, y + 9), (x + 12, y, x + 12, y + 9)):
        kline(cv, a0, b0, a1, b1, K["ink"], K, 0.3, a0 + b0)
    run = k == "run"
    if a["kind"] in ("washer", "dryer"):
        cx, cy = x + 6, y + 5
        col = K["blue"] if a["kind"] == "washer" else K["orange"]
        kring(cv, cx, cy, 3, K["grey"], K, 63)
        if a["kind"] == "washer":
            lvl = cy + (0 if not run else (1 if (f1 // 2) % 2 else 0))
            for i in range(-2, 3):
                for j in range(-2, 3):
                    if i * i + j * j <= 5 and cy + j >= lvl:
                        kpx(cv, cx + i, cy + j, col, K)
            if run:
                for n in range(2):                                  # bubbles
                    by = y - 1 - ((f1 + n * 4) % 8) // 2
                    kpx(cv, x + 3 + n * 6, by, K["lblue"], K)
        else:
            if run:
                ang = f1 * math.pi / 4
                kpx(cv, round(cx + 1.5 * math.cos(ang)), round(cy + 1.5 * math.sin(ang)), col, K)
                kpx(cv, round(cx - 1.5 * math.cos(ang)), round(cy - 1.5 * math.sin(ang)), col, K)
                for n in range(2):                                  # warm wiggles
                    for j in range(3):
                        kpx(cv, x + 4 + n * 4 + ((j + f1 // 2) % 2), y - 1 - j, K["orange"], K)
            else:
                kpx(cv, cx, cy, col, K)
        kpx(cv, x + 2, y + 1, K["red"], K)
    else:                                                           # 3D printer: frame, nozzle, growing toy
        kline(cv, x + 1, y + 2, x + 11, y + 2, K["ink"], K, 0, 71)
        nx = x + 3 + ((f1 // 2) % 6 if run else 3)
        kpx(cv, nx, y + 3, K["red"], K); kpx(cv, nx + 1, y + 3, K["red"], K)
        pct = a.get("pct")
        h = 0 if pct is None else max(1, round(4 * pct / 100))
        if k == "done": h = 4
        for j in range(h):
            for i in range(3):
                kpx(cv, x + 5 + i, y + 8 - j, K["green"], K)
    if k == "done":                                                 # gold star sticker
        for (dx, dy) in ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)):
            kpx(cv, x + 12 + dx, y + dy, K["yellow"], K)
    if k == "err" and (f1 // 4) % 2 == 0:
        kline(cv, x + 13, y - 1, x + 13, y + 2, K["red"], K, 0, 9); kpx(cv, x + 13, y + 4, K["red"], K)


def kid_glitter(cv, K, spots, salt=4):
    """Effect: twinkling crayon stars that pop up now and then."""
    p = MO.event(salt)
    if p is None:
        return
    size = 1 if p < 0.25 or p > 0.75 else 2
    for n, (x, y) in enumerate(spots):
        c = K[("yellow", "pink", "lblue")[n % 3]]
        kpx(cv, x, y, c, K)
        for d in range(1, size + 1):
            for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
                if cv.is_bg(x + dx, y + dy) or True:
                    cv.px(x + dx, y + dy, mix(c, (255, 255, 255), 0.3 * (d - 1)))


def render_dashboard_kid(d, f, variant=0):
    cv = Canvas()
    K, T = kid_pal(), tr(d)
    f1 = MO.m(1)
    for row, (y, t, h) in enumerate(((1, d.get("t_in"), d.get("h_in")), (17, d.get("t_out"), d.get("h_out")))):
        (kid_house if row == 0 else kid_tree)(cv, 1, y, K, f)
        v = num(t)
        ktext(cv, 18, y + 3, ("%d°" % round(v)) if v is not None else "?", kid_temp_color(v, K), K, "crayon", seed=row)
        ktext(cv, 18, y + 11, T["kid_in"] if row == 0 else T["kid_out"], K["grey"], K, seed=row + 3)
        hv = num(h)
        kid_drop(cv, 42, y + 4, K)
        ktext(cv, 49, y + 5, ("%d%%" % round(hv)) if hv is not None else "?", K["blue"], K, seed=row + 7)
    a = num(d.get("aqi"))
    if a is not None:
        kid_face(cv, 8, 40, 6, aqi_level(max(0, a)), K, f)
        ktext(cv, 17, 37, "%d" % round(max(0, a)), K["ink"], K, "crayon", seed=9)
    out = rain_outlook(d)
    if out is not None:
        kid_umbrella(cv, 42, 32, out[0], K, f1)
    if show_sun_card(d, variant):
        for n, (key, rising) in enumerate((("sunrise", True), ("sunset", False))):
            x0 = n * 32
            bob = 0 if MO.still(2) else round(math.sin(2 * math.pi * MO.m(2) / FRAMES))
            sy = (52 if rising else 53) + bob * (-1 if rising else 1)
            kid_sun(cv, x0 + 13, sy, 3, K, MO.m(2), face=True, ray=2.5)
            for i in range(0, 32):                                  # hill / horizon
                hy = 55 + round(1.0 * math.sin((i + x0) * 0.3))
                for j in range(hy, 57):
                    kpx(cv, x0 + i, j, K["green"], K)
            ax, ay = x0 + 25, 51
            col = K["red"] if rising else K["purple"]
            sgn = -1 if rising else 1
            for j in range(-2, 3):                                  # big up / down arrow
                kpx(cv, ax, ay + j, col, K)
            for dx in (-1, 1):
                kpx(cv, ax + dx, ay + 2 * sgn - sgn, col, K)
            for dx in (-2, 2):
                kpx(cv, ax + dx, ay + 2 * sgn - 2 * sgn, col, K)
            ktext(cv, x0 + 16, 58, str(d.get(key) or "--:--")[:5], K["orange"] if rising else K["purple"],
                  K, align="center", seed=n + 11)
    else:
        words = T["kid_state"]
        for n, ap in enumerate(appl_list(d)):
            x = 1 + n * 21
            kid_appliance(cv, x + 3, 47, ap, K, f)
            k = ap["k"]
            word = ("%d%%" % round(ap["pct"])) if (ap["kind"] == "printer" and k == "run" and ap["pct"] is not None) else words.get(k, "?")
            col = {"run": K["blue"], "done": K["green"], "err": K["red"], "pause": K["orange"]}.get(k, K["grey"])
            ktext(cv, x + 9, 59, word, col, K, align="center", seed=n + 13)
    kid_glitter(cv, K, ((34, 2), (60, 30), (30, 45), (14, 18)))
    return cv.img


def render_dashboard_kid_dark(d, f, variant=0):
    global KID_STYLE
    KID_STYLE = "dark"
    try:
        return render_dashboard_kid(d, f, variant)
    finally:
        KID_STYLE = "paper"


def render_weather_kid_dark(d, f):
    global KID_STYLE
    KID_STYLE = "dark"
    try:
        return render_weather_kid(d, f)
    finally:
        KID_STYLE = "paper"


def render_weather_kid(d, f):
    cv = Canvas()
    K, T = kid_pal(), tr(d)
    f1, f2 = MO.m(1), MO.m(2)
    tm = str(d.get("time") or "--:--")[:5]
    x = 32 - cv.text_width(tm, "crayon2") // 2
    for i, ch in enumerate(tm):                                     # big colourful clock digits
        col = K[("blue", "red", "ink", "green", "purple")[i % 5]] if ch != ":" else K["ink"]
        ktext(cv, x, 1 + (1 if _hash(i, 3, K["boil"]) % 3 == 0 else 0), ch, col, K, "crayon2", jitter=False)
        x += cv.glyph("crayon2", ch)[0] + 1
    dt = today_date(d)
    day = T["days"][dt.weekday()] if dt else str(d.get("dow") or "")
    ktext(cv, 32, 17, day, None, K, align="center", rainbow=True)
    cond = cur_cond(d)
    kid_weather(cv, 12, 32, 18, cond, K, f1)
    v = cur_temp(d)
    ktext(cv, 24, 25, ("%d°" % round(v)) if v is not None else "?", kid_temp_color(v, K), K, "crayon", seed=2)
    today, nxt = today_and_next(d)
    if today:
        hi, lo = num(today.get("hi")), num(today.get("lo"))
        hs = "↑%d" % round(hi) if hi is not None else "↑?"
        ls = "↓%d" % round(lo) if lo is not None else "↓?"
        w = ktext(cv, 24, 35, hs, K["red"], K, seed=4)
        ktext(cv, 24 + w + 3, 35, ls, K["blue"], K, seed=5)
    if MO.level >= 4:                                               # a bird flies past
        m4 = MO.m(4)
        bx = -4 + m4 * 72 // FRAMES
        by = 40 + (1 if (m4 // 2) % 2 else 0)
        for dx, dy in ((0, 0), (1, 1), (2, 0), (3, 1), (4, 0)) if (m4 // 2) % 2 else ((0, 1), (1, 0), (2, 1), (3, 0), (4, 1)):
            if 0 <= bx + dx < 64 and cv.is_bg(bx + dx, by + dy):
                kpx(cv, bx + dx, by + dy, K["ink"], K)
    for n, fd in enumerate(nxt[:4]):
        cx = 8 + n * 16
        wd = fc_weekday(fd)
        name = T["days3"][wd] if wd is not None else str(fd.get("d") or "")[:3]
        ktext(cv, cx, 45, name, K[KID_RAINBOW[n % len(KID_RAINBOW)]], K, align="center", seed=n + 20)
        kid_weather(cv, cx, 53, 9, fd.get("c"), K, (f2 + n * 3) % FRAMES)
        hi = num(fd.get("hi"))
        ktext(cv, cx, 59, ("%d°" % round(hi)) if hi is not None else "?", kid_temp_color(hi, K), K, align="center", seed=n + 30)
    kid_glitter(cv, K, ((60, 18), (2, 16), (50, 40)))
    return cv.img


# ----------------------------------------------------------------------------
# Backgrounds (selectable; used by classic, hud, digital_rain, block_3d, mech, purist, kid)
# ----------------------------------------------------------------------------
def _vgrad(top, bot):
    return lambda x, y: mix(top, bot, y / 63)


def _grain(base, amp, seed, streak=1):
    def fn(x, y):
        v = (_hash(x // streak, y, seed) % (2 * amp + 1)) - amp
        return tuple(max(0, min(255, c + v)) for c in base)
    return fn


def _bg_paper(x, y, base=(238, 234, 224), seed=3):
    c = _grain(base, 5, seed)(x, y)
    if _hash(x, y, seed + 9) % 53 == 0:                      # paper fibres
        c = shade(c, -0.06)
    return c


def _bg_black_paper(x, y):
    c = _grain((14, 14, 17), 2, 13)(x, y)
    if _hash(x, y, 14) % 61 == 0:                           # a few paper fibres
        c = shade(c, 0.5)
    return c


def _bg_kraft(x, y):
    c = _grain((176, 134, 86), 7, 11)(x, y)
    if _hash(x // 3, y, 12) % 29 == 0:
        c = shade(c, 0.1)
    return c


def _bg_notebook(x, y):
    c = _bg_paper(x, y, (240, 238, 230), 4)
    if y % 6 == 5 and y > 4:
        c = mix(c, (120, 165, 225), 0.55)
    if x == 6:
        c = mix(c, (225, 90, 90), 0.6)
    return c


def _bg_graph(x, y):
    c = _bg_paper(x, y, (242, 244, 238), 5)
    if x % 16 == 0 or y % 16 == 0:
        return mix(c, (90, 170, 150), 0.45)
    if x % 4 == 0 or y % 4 == 0:
        return mix(c, (120, 190, 170), 0.22)
    return c


def _bg_blueprint(x, y):
    c = _grain((22, 62, 128), 3, 6)(x, y)
    if x % 16 == 0 or y % 16 == 0:
        return mix(c, (170, 205, 245), 0.45)
    if x % 4 == 0 or y % 4 == 0:
        return mix(c, (120, 165, 225), 0.18)
    return c


def _bg_chalk(x, y):
    smudge = math.sin(x * 0.11 + y * 0.05) * 0.5 + math.sin(x * 0.04 - y * 0.13 + 1) * 0.5
    c = shade((34, 58, 44), 0.05 * smudge)
    v = (_hash(x, y, 21) % 7) - 3
    return tuple(max(0, ch + v) for ch in c)


def _bg_wood(x, y):
    plank = y // 8
    off = (_hash(plank, 1, 31) % 64)
    g = math.sin((x + off) * 0.21 + math.sin((y + plank * 5) * 0.9) * 1.6)
    c = mix((150, 98, 56), (112, 70, 38), 0.5 + 0.5 * g)
    c = shade(c, ((plank * 37) % 5 - 2) * 0.04)
    if y % 8 == 7:
        c = (66, 40, 22)
    elif (x + plank * 23) % 40 == 0:
        c = shade(c, -0.35)
    return c


def _bg_brick(x, y):
    row = y // 5
    xo = x + (4 if row % 2 else 0)
    if y % 5 == 4 or xo % 9 == 8:
        return (178, 170, 158)
    base = [(150, 58, 42), (164, 70, 48), (138, 52, 40), (170, 82, 56)][_hash(xo // 9, row, 41) % 4]
    return _grain(base, 6, 43)(x, y)


def _bg_carbon(x, y):
    cell = ((x // 2) + (y // 2)) % 2
    a, b = (34, 36, 40), (18, 19, 22)
    c = a if cell else b
    if (x + y) % 2 == 0:
        c = shade(c, 0.12)
    return c


def _bg_denim(x, y):
    c = (40, 70, 120) if (x + y * 2) % 4 < 2 else (30, 52, 96)
    return _grain(c, 6, 51)(x, y)


def _bg_stars(x, y):
    c = mix((2, 3, 14), (14, 6, 30), 0.5 + 0.5 * math.sin(x * 0.07 + y * 0.05))
    h = _hash(x, y, 61) % 1000
    if h < 6:
        return (230, 235, 255) if h < 2 else (120, 130, 175)
    return c


def _bg_polka(x, y):
    cx, cy = (x // 8) * 8 + (4 if (y // 8) % 2 else 0), (y // 8) * 8
    for ox in (-8, 0, 8):
        dx, dy = x - (cx + ox + 3.5), y - (cy + 3.5)
        if dx * dx + dy * dy <= 4.0:
            return (238, 160, 170)
    return (250, 228, 222)


def _bg_stripes(x, y):
    return (70, 112, 150) if ((x + y) // 4) % 2 else (54, 88, 122)


def _bg_linen(x, y):
    c = (226, 214, 190)
    if x % 2 == 0: c = shade(c, -0.03)
    if y % 2 == 0: c = shade(c, -0.03)
    return _grain(c, 3, 71)(x, y)


def _bg_terrazzo(x, y):
    c = _grain((222, 216, 206), 3, 81)(x, y)
    h = _hash(x // 3, y // 3, 82) % 100
    if h < 9 and _hash(x, y, 83) % 3:
        c = [(196, 120, 96), (110, 140, 120), (70, 80, 96), (210, 180, 110)][h % 4]
    return c


BACKGROUNDS = {
    "black": lambda x, y: (0, 0, 0),
    "midnight": _vgrad((4, 8, 28), (10, 20, 52)),
    "charcoal": _grain((24, 25, 28), 2, 1),
    "forest": _vgrad((10, 44, 26), (4, 24, 14)),
    "burgundy": _vgrad((62, 10, 24), (32, 4, 12)),
    "ocean": _vgrad((0, 46, 76), (0, 18, 40)),
    "white_paper": _bg_paper,
    "black_paper": _bg_black_paper,
    "kraft_paper": _bg_kraft,
    "notebook": _bg_notebook,
    "graph_paper": _bg_graph,
    "blueprint": _bg_blueprint,
    "chalkboard": _bg_chalk,
    "wood": _bg_wood,
    "brick": _bg_brick,
    "carbon": _bg_carbon,
    "denim": _bg_denim,
    "linen": _bg_linen,
    "terrazzo": _bg_terrazzo,
    "starfield": _bg_stars,
    "day_sky": _vgrad((70, 150, 230), (200, 228, 250)),
    "sunset": _vgrad((60, 30, 110), (250, 140, 70)),
    "polka_dots": _bg_polka,
    "stripes": _bg_stripes,
}
BG_DESIGNS = {"classic": "dark", "hud": "dark", "digital_rain": "dark", "block_3d": "dark",
              "mech": "dark", "purist": "quiet", "kid": "raw", "kid_dark": "dark"}
BG_DEFAULT = {"purist": "black", "kid": "white_paper", "kid_dark": "black_paper"}
BACKDROP = None          # active background: {"name", "pix" [y][x], "light", "mean"} or None


def make_backdrop(name, tone):
    """64x64 background layer. tone: raw (as is), dark (dimmed for dark designs so text stays
    readable), quiet (low-contrast pattern for the purist design)."""
    fn = BACKGROUNDS.get(name)
    if fn is None:
        return None
    pix = [[tuple(int(v) for v in fn(x, y)) for x in range(64)] for y in range(64)]
    flat = [c for row in pix for c in row]
    mean = tuple(sum(c[i] for c in flat) / len(flat) for i in range(3))
    ml = lum(mean)
    if tone == "dark" and ml > 52:
        k = 52 / ml
        pix = [[tuple(int(v * k) for v in c) for c in row] for row in pix]
        mean = tuple(v * k for v in mean)
    elif tone == "quiet":
        pix = [[mix(c, mean, 0.5) for c in row] for row in pix]
    return {"name": name, "pix": pix, "mean": mean, "light": lum(mean) > 110}


def resolve_background(data, design):
    """Background for this design, or None when the design keeps its own backdrop."""
    if design not in BG_DESIGNS:
        return None
    name = str(data.get("background") or "design default").lower().strip().replace(" ", "_")
    if name not in BACKGROUNDS:
        name = BG_DEFAULT.get(design)
        if name is None:
            return None
    return make_backdrop(name, BG_DESIGNS[design])


# ----------------------------------------------------------------------------
# Motion tiers: wrap every animated helper so its time argument follows the motion level
# ----------------------------------------------------------------------------
def _timed(fn, tier, rest=0):
    """Replace fn's `f` argument by the moving-part clock of its tier. Phase offsets the caller
    added (e.g. (f + n * 3) % FRAMES for staggered forecast icons) are preserved, and a part never
    moves while the part it is drawn inside is frozen."""
    sig = inspect.signature(fn)
    names = list(sig.parameters)
    idx = names.index("f")

    def wrapper(*a, **k):
        if idx < len(a):
            passed = a[idx]
        elif "f" in k:
            passed = k["f"]
        else:
            return fn(*a, **k)
        if not isinstance(passed, int) or isinstance(passed, bool):
            return fn(*a, **k)
        top, ptier, phase = MO.stack[-1] if MO.stack else (passed, 0, 0)
        t = tier
        if callable(tier):
            try:
                t = tier(sig.bind(*a, **k).arguments)
            except TypeError:
                t = 1
        t = max(t, ptier)
        base = MO.m(t, rest)
        new = base + phase + (passed - top)
        if 0 <= passed < FRAMES:
            new %= FRAMES
        if idx < len(a):
            a = a[:idx] + (new,) + a[idx + 1:]
        else:
            k["f"] = new
        MO.stack.append((new, t, new - base))
        try:
            return fn(*a, **k)
        finally:
            MO.stack.pop()
    functools.update_wrapper(wrapper, fn)
    wrapper._motion = True
    return wrapper


def _by_size(key, big, cut):
    """Tier 1 for the big 'current' icon, tier 2 for small forecast icons."""
    return lambda args: 1 if float(args.get(key, big) or 0) >= cut else 2


MOTION_TIERS = {
    # classic
    "appliance": 1, "printer": 1, "draw_umbrella": 1, "appliance_row": 1, "status_strip": 1,
    "aqi_gauge": 2, "_scene": 2, "card_sun": 2, "weather_icon": _by_size("S", 12, 12),
    # mondrian
    "m_appliance": 1, "m_weather_icon": 1, "m_small_icon": 2, "m_sun_cells": 2, "m_blips": 4,
    # van gogh
    "vg_appliance": 1, "vg_icon": _by_size("S", 12, 12), "vg_orb": 2, "vg_sun_card": 2,
    "vg_sky": 3, "vg_field": 3,
    # hokusai
    "hk_appliance": 1, "hk_icon": lambda a: 2 if a.get("small") else 1, "hk_sun_card": 2, "hk_waves": 3,
    # klimt
    "k_appliance": 1, "k_icon": 1, "k_small_icon": 2, "k_spiral_disc": 2, "k_sun_card": 2,
    "k_mosaic": 3, "k_meadow": 3,
    # hud
    "hud_wire_icon": 1, "hud_umbrella": 1, "hud_cond_icon": _by_size("s", 1.0, 0.8), "hud_ring": 2,
    "hud_sun_arc": 2,
    # block 3d
    "b_appliance": 1, "b_icon": _by_size("s", 1.0, 0.8), "b_room": 3,
    # digital rain
    "r_mini_icon": 2, "rain_bg": 3,
    # comic
    "c_appliance": 1, "c_icon": _by_size("s", 1.0, 0.8), "c_sun_panel": 2, "c_burst": 4,
    # mech
    "x_lamp": 1, "x_vector_icon": _by_size("s", 1.0, 0.8), "x_needle_gauge": 2, "x_hazard": 4,
    # platformer
    "pl_machine": 1, "pl_status_bar": 2, "pl_sky": 3, "pl_ground": 3, "pl_hero": 4, "pl_gem": 4,
}
RENDER_TIER = {"platformer": 4, "comic": 4}      # tier of motion written inline in page functions


def _install_motion_tiers():
    g = globals()
    for name, tier in MOTION_TIERS.items():
        fn = g.get(name)
        if fn is not None and not getattr(fn, "_motion", False):
            g[name] = _timed(fn, tier)


# ----------------------------------------------------------------------------
# Design selection
# ----------------------------------------------------------------------------
ART_DESIGNS = ["mondrian", "van_gogh", "hokusai", "klimt", "digital_rain", "block_3d", "hud",
               "comic", "mech", "platformer", "purist", "kid", "kid_dark", "starship"]
ALL_DESIGNS = ["classic"] + ART_DESIGNS


def resolve_design(data):
    """A design name, 'rotate' (all designs) or 'rotate (no classic)'. Legacy 'rotate daily/hourly' work too."""
    name = str(data.get("design") or "classic").lower().strip()
    key = name.replace(" ", "_")
    if key in ALL_DESIGNS:
        return key
    if name.startswith("rotate"):
        pool = ART_DESIGNS if ("art" in name or "no classic" in name) else ALL_DESIGNS
        legacy = "hourly" if "hourly" in name else ("daily" if "daily" in name else None)
        return pool[rotation_slot(data, legacy) % len(pool)]
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
    out[0].save(tmp, save_all=True, append_images=out[1:], duration=FRAME_MS if len(out) > 1 else 1000, loop=0,
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
    design = resolve_design(data)
    theme = resolve_theme(data, design)
    classic_theme = "neon" if theme == "original" else theme
    preset = str(data.get("vivid") or "vivid").lower().split("(")[0].strip()
    gamma, sat = VIVID.get(preset, VIVID["vivid"])

    motion = dict(level=data.get("motion", 5), mspeed=data.get("motion_speed", 3),
                  freq=data.get("fx", 3), espeed=data.get("fx_speed", 3))
    t = str(data.get("time") or "")
    minute = int(t[:2]) * 60 + int(t[3:5]) if (t[:2].isdigit() and t[3:5].isdigit()) else 0
    _install_motion_tiers()
    global BACKDROP
    BACKDROP = resolve_background(data, design)
    render_tier = RENDER_TIER.get(design, 3)

    def render(fn, path, page_no=0):
        """Render one page; on failure write a visible error screen so the Pixoo still shows something."""
        page = "weather" if "weather" in path else "dashboard"
        MO.configure(seed=minute + page_no, **motion)

        def frame(g):
            _SEMANTIC.clear()
            apply_theme(classic_theme if design == "classic" else "neon")
            MO.g = g
            MO._cache = {}
            f = MO.m(render_tier)
            MO.stack = [(f, 0, 0)]
            img = fn(f)
            if design != "classic" and theme != "original" and _LAST_CANVAS is not None:
                theme_post(_LAST_CANVAS, theme, f, page)
                img = _LAST_CANVAS.img
            return img

        try:
            frames = [frame(g) for g in range(MO.L)]
        except Exception:
            errors.append(os.path.basename(path) + ": " + traceback.format_exc())
            frames = [error_frame(os.path.basename(path))] * 2
        save_gif(frames, path, gamma, sat)
        return path

    dash_fn, weather_fn = page_renderers(design)
    render(lambda f: weather_fn(data, f), os.path.join(OUT_DIR, "weather.gif"), 0)
    # dashboard_0.gif = appliances (or sunrise/sunset when everything is idle),
    # dashboard_1.gif = sunrise/sunset. The Pixoo page alternates between them (see gif_url).
    # dashboard_2.gif is a copy of dashboard_1.gif for older page configs using "% 3".
    try:
        all_idle = all(k in ("idle", "off") for k, _ in _appliance_states(data))
    except Exception:
        all_idle = False
    first = render(lambda f: dash_fn(data, f, 0), os.path.join(OUT_DIR, "dashboard_0.gif"), 1)
    second = os.path.join(OUT_DIR, "dashboard_1.gif")
    if all_idle:
        _copy(first, second)
    else:
        render(lambda f: dash_fn(data, f, 1), second, 2)
    _copy(second, os.path.join(OUT_DIR, "dashboard_2.gif"))
    _copy(first, os.path.join(OUT_DIR, "dashboard.gif"))

    status = "%s  design=%s  theme=%s  colours=%s  all_idle=%s\n" % (
        data.get("time"), design, theme, preset, all_idle)
    status += "background=%s  " % (BACKDROP["name"] if BACKDROP else "design's own")
    status += "motion level=%d speed=%d  effects frequency=%d speed=%d  frames=%d\n" % (
        MO.level, MO.mspeed, MO.freq, MO.espeed, MO.L)
    status += ("ERRORS:\n" + "\n".join(errors)) if errors else "OK\n"
    with open(os.path.join(OUT_DIR, "status.txt"), "w") as fh:
        fh.write(status)
    if errors:
        print(status, file=sys.stderr)
        sys.exit(1)
    print("ok design=%s theme=%s vivid=%s" % (design, theme, preset))


if __name__ == "__main__":
    main()
