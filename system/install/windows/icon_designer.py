#!/usr/bin/env python3
"""
icon_designer.py — generate Metis desktop-icon options and build the chosen .ico.

Why this exists: every Metis icon is rendered HERE with Pillow, so the preview
thumbnails in the gallery are pixel-identical to the .ico that gets installed
(no SVG-vs-raster surprises). 20 distinct designs, all with backgrounds, none of
them the blue brain.

Usage:
  python icon_designer.py gallery          # build icon-previews/index.html (open it, pick a number)
  python icon_designer.py build N          # build metis.ico from design N and install it everywhere
"""

import base64
import io
import math
import os
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

try:
    import numpy as np
except Exception:
    np = None

SS = 4  # supersample factor for crisp anti-aliased edges
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent  # windows -> install -> system -> repo root

# Where the live icon must land (matches create-shortcut/repair-shortcut/base.html/main.py).
INSTALL_TARGETS = [
    HERE / "metis.ico",
    ROOT / "system" / "app-py" / "static" / "metis.ico",
]

# ── colours ──────────────────────────────────────────────────────────────────
WHITE = (255, 255, 255)
CREAM = (255, 248, 237)
INK = (17, 24, 39)

TEAL = (15, 118, 110)
INDIGO = (67, 56, 202)
VIOLET = (124, 58, 237)
AMBER = (217, 119, 6)
SLATE = (51, 65, 85)
NAVY = (30, 41, 59)
FOREST = (21, 128, 61)
ROYAL = (29, 78, 216)
SKY1, SKY2 = (14, 165, 233), (125, 211, 252)
TERRA = (194, 65, 12)
PLUM = (126, 34, 206)
CORAL = (225, 29, 72)
GRAPHITE = (31, 41, 55)
DTEAL = (15, 61, 62)
EMERALD = (16, 185, 129)
SUN1, SUN2 = (244, 63, 94), (249, 115, 22)
MIDNIGHT = (15, 23, 42)
STAR = (226, 232, 240)


# ── helpers ──────────────────────────────────────────────────────────────────
def _mask_squircle(S, radius_frac=0.255, inset=0.0):
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    pad = int(S * inset)
    d.rounded_rectangle([pad, pad, S - 1 - pad, S - 1 - pad],
                        radius=int(S * radius_frac), fill=255)
    return m


def _mask_circle(S, inset=0.0):
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    pad = int(S * inset)
    d.ellipse([pad, pad, S - 1 - pad, S - 1 - pad], fill=255)
    return m


def _solid(S, color):
    return Image.new("RGBA", (S, S), color + (255,))


def _gradient(S, c1, c2, diagonal=True):
    if np is None:
        return _solid(S, c1)
    if diagonal:
        ax = (np.add.outer(np.arange(S), np.arange(S)) / (2 * (S - 1)))
    else:
        ax = np.tile(np.linspace(0, 1, S).reshape(S, 1), (1, S))
    arr = np.zeros((S, S, 4), dtype=np.uint8)
    for i, (a, b) in enumerate(zip(c1, c2)):
        arr[:, :, i] = (a + (b - a) * ax).astype(np.uint8)
    arr[:, :, 3] = 255
    return Image.fromarray(arr, "RGBA")


def _bg(S, fill, shape="squircle"):
    """fill: color tuple OR ('grad', c1, c2[, diagonal]) OR ('split', cL, cR)."""
    if isinstance(fill, tuple) and fill and fill[0] == "grad":
        base = _gradient(S, fill[1], fill[2], fill[3] if len(fill) > 3 else True)
    elif isinstance(fill, tuple) and fill and fill[0] == "split":
        base = Image.new("RGBA", (S, S), fill[1] + (255,))
        ImageDraw.Draw(base).rectangle([S // 2, 0, S, S], fill=fill[2] + (255,))
    else:
        base = _solid(S, fill)
    mask = _mask_circle(S) if shape == "circle" else _mask_squircle(S)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(base, (0, 0), mask)
    return out


def _font(size, serif=False):
    return ImageFont.truetype(FONT_SERIF if serif else FONT_BOLD, size)


def _M(d, S, color, serif=False, dy=0.0):
    d.text((S / 2, S / 2 + S * dy), "M", font=_font(int(S * 0.6), serif),
           fill=color + (255,), anchor="mm")


def _poly(d, pts, **kw):
    d.polygon(pts, **kw)


def _ngon(cx, cy, r, n, rot=0):
    return [(cx + r * math.cos(rot + 2 * math.pi * k / n),
             cy + r * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]


def _dot(d, cx, cy, r, color):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (255,))


# ── brain renderer ────────────────────────────────────────────────────────────
def _brain_mask(S):
    """Lumpy brain silhouette as an L mask. Returns (mask, (cx,cy,W,H))."""
    cx = cy = S / 2
    W, H = S * 0.62, S * 0.54
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    d.ellipse([cx - W*0.5, cy - H*0.30, cx + W*0.5, cy + H*0.50], fill=255)  # body
    n = 6
    for i in range(n):  # top gyri bumps
        t = i / (n - 1)
        bx = cx - W*0.40 + t*W*0.80
        by = cy - H*0.24 - math.sin(t*math.pi)*H*0.22
        r = W*0.175
        d.ellipse([bx-r, by-r, bx+r, by+r], fill=255)
    for sgn in (-1, 1):  # temporal lobe cheeks
        r = W*0.19; bx = cx + sgn*W*0.40; by = cy + H*0.06
        d.ellipse([bx-r, by-r, bx+r, by+r], fill=255)
    return m, (cx, cy, W, H)


def _brain_grooves(cx, cy, W, H):
    paths = []
    pts = []  # central wavy division
    for k in range(25):
        t = k/24; y = cy - H*0.28 + t*H*0.66; x = cx + math.sin(t*math.pi*1.6)*W*0.05
        pts.append((x, y))
    paths.append(pts)
    for sgn in (-1, 1):  # folds per hemisphere
        for j, yy in enumerate((-0.15, 0.01, 0.17)):
            pts = []
            for k in range(16):
                t = k/15
                x = cx + sgn*(W*0.08 + t*W*0.32)
                y = cy + yy*H + math.sin(t*math.pi*2 + j*1.2)*H*0.05
                pts.append((x, y))
            paths.append(pts)
    return paths


def _brain(base, fill, groove, style="solid", grooves=True):
    """Draw a brain onto bg image `base`. fill: RGB or Image (gradient). style:
    solid | line | twotone(fill=(cA,cB)). groove: RGB used for the folds."""
    S = base.size[0]
    m, (cx, cy, W, H) = _brain_mask(S)
    gw = max(2, int(S*0.024))
    if style == "twotone":
        a = Image.new("RGBA", (S, S), fill[0]+(255,))
        b = Image.new("RGBA", (S, S), fill[1]+(255,))
        half = Image.new("L", (S, S), 0)
        ImageDraw.Draw(half).rectangle([0, 0, int(cx), S], fill=255)
        base.paste(Image.composite(a, b, half), (0, 0), m)
    elif style == "line":
        k = max(3, int(S*0.03)) | 1
        edge = ImageChops.subtract(m, m.filter(ImageFilter.MinFilter(k)))
        base.paste(Image.new("RGBA", (S, S), fill+(255,)), (0, 0), edge)
    else:  # solid or gradient
        if isinstance(fill, Image.Image):
            base.paste(fill, (0, 0), m)
        else:
            base.paste(Image.new("RGBA", (S, S), fill+(255,)), (0, 0), m)
    if grooves:
        gl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        gd = ImageDraw.Draw(gl)
        alpha = 255 if style == "line" else 210
        for p in _brain_grooves(cx, cy, W, H):
            gd.line(p, fill=groove+(alpha,), width=gw, joint="curve")
        base.alpha_composite(Image.composite(gl, Image.new("RGBA", (S, S), (0,0,0,0)), m))
    return cx, cy, W, H


def _circuit_right(base, cx, cy, W, H, color):
    """Replace the right hemisphere folds with a circuit/synapse motif."""
    S = base.size[0]; d = ImageDraw.Draw(base)
    nodes = [(cx+W*0.14, cy-H*0.16), (cx+W*0.34, cy-H*0.02),
             (cx+W*0.16, cy+H*0.16), (cx+W*0.37, cy+H*0.20)]
    for a, b in ((0,1),(0,2),(1,3),(2,3)):
        d.line([nodes[a], nodes[b]], fill=color+(220,), width=max(2,int(S*0.016)))
    for nx, ny in nodes:
        _dot(d, nx, ny, S*0.028, color)


# ── dashboard palette (system/app-py/static/styles.css theme tokens) ───────────
M_FOREST    = (45, 74, 58)    # --m-accent (default)
M_FOREST_DK = (34, 59, 46)    # --m-accent-hover
M_SAGE      = (74, 106, 84)   # --m-accent-soft
M_PAPER     = (245, 242, 234) # --m-bg
M_INKG      = (31, 42, 36)    # --m-ink
OBS_BG      = (21, 19, 15)    # observatory bg
OBS_FG      = (243, 234, 214) # observatory ink
OBS_AMBER   = (217, 154, 76)  # observatory accent
FW_BLUE     = (45, 68, 128)   # fieldwork accent
FW_PAPER    = (240, 239, 248) # fieldwork bg
FW_SOFT     = (122, 176, 232) # fieldwork hover
TEAL_DK     = (26, 58, 53)
TEAL_HOVER  = (74, 212, 196)
BROWN_DK    = (58, 38, 20)
BROWN_SOFT  = (224, 176, 122)


# ── shared brain primitives (top-view silhouette) ─────────────────────────────
def _tv_mask_k(S, k=1.0):
    cx = cy = S/2; W = S*0.64*k; H = S*0.50*k
    m = Image.new("L", (S, S), 0); d = ImageDraw.Draw(m)
    d.ellipse([cx-W/2, cy-H/2, cx+W/2, cy+H/2], fill=255)
    if k > 0.5:
        for i in range(7):
            t = i/6; x = cx-W*0.38+t*W*0.76; r = W*0.105
            d.ellipse([x-r, cy-H*0.5-r*0.5, x+r, cy-H*0.5+r*1.5], fill=255)
            d.ellipse([x-r, cy+H*0.5-r*1.5, x+r, cy+H*0.5+r*0.5], fill=255)
    return m, (cx, cy, W, H)

def _tv_gyri(cx, cy, W, H):
    paths = [[(cx, cy-H*0.46), (cx, cy+H*0.46)]]
    for sgn in (-1, 1):
        for j, yy in enumerate((-0.30, -0.10, 0.10, 0.30)):
            pts = []
            for k in range(12):
                t = k/11
                x = cx + sgn*(W*0.05 + t*W*0.40)
                y = cy + yy*H + math.sin(t*math.pi*1.1)*H*0.07
                pts.append((x, y))
            paths.append(pts)
    return paths

def _fill(im, mask, color):
    im.paste(Image.new("RGBA", im.size, color+(255,)), (0, 0), mask)

def _edge(mask, S):
    k = max(3, int(S*0.026)) | 1
    return ImageChops.subtract(mask, mask.filter(ImageFilter.MinFilter(k)))

def _clip(im, layer, mask):
    im.alpha_composite(Image.composite(layer, Image.new("RGBA", im.size, (0,0,0,0)), mask))


# ── 14 distinct brain engines ─────────────────────────────────────────────────
def e_topview(im, fg, accent, filled=False):
    S = im.size[0]; m, (cx, cy, W, H) = _tv_mask_k(S)
    if filled: _fill(im, m, fg); gcol = accent
    else:      _fill(im, _edge(m, S), fg); gcol = fg
    gl = Image.new("RGBA", (S, S), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
    for pth in _tv_gyri(cx, cy, W, H):
        gd.line(pth, fill=gcol+(220,), width=max(2, int(S*0.02)), joint="curve")
    _clip(im, gl, m); return cx, cy, W, H

def e_circuit(im, fg, accent):
    S = im.size[0]; m, (cx, cy, W, H) = _tv_mask_k(S); _fill(im, _edge(m, S), fg)
    gl = Image.new("RGBA", (S, S), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
    for x, y in [(cx-W*0.26, cy-H*0.22), (cx+W*0.22, cy-H*0.26),
                 (cx-W*0.28, cy+H*0.20), (cx+W*0.26, cy+H*0.22)]:
        gd.line([(cx, cy), (x, cy), (x, y)], fill=fg+(210,), width=max(2, int(S*0.014)))
        _dot(gd, x, y, S*0.026, accent)
    _dot(gd, cx, cy, S*0.032, accent); _clip(im, gl, m)

def e_neuralnet(im, fg, accent):
    S = im.size[0]; d = ImageDraw.Draw(im)
    cols = [(0.28, (0.34, 0.66)), (0.5, (0.22, 0.5, 0.78)), (0.72, (0.34, 0.66))]
    nodes = [[(S*lx, S*yy) for yy in ys] for lx, ys in cols]
    for a in range(len(nodes)-1):
        for p in nodes[a]:
            for q in nodes[a+1]:
                d.line([p, q], fill=fg+(110,), width=max(1, int(S*0.009)))
    for i, col in enumerate(nodes):
        for pnt in col:
            _dot(d, pnt[0], pnt[1], S*0.036, accent if i == 1 else fg)

def e_halfcircuit(im, fg, accent):
    S = im.size[0]; m, (cx, cy, W, H) = _tv_mask_k(S)
    half = Image.new("L", (S, S), 0); ImageDraw.Draw(half).rectangle([0, 0, int(cx), S], fill=255)
    lm = ImageChops.multiply(m, half); _fill(im, lm, fg)
    _fill(im, _edge(m, S), fg)
    gl = Image.new("RGBA", (S, S), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
    for pth in _tv_gyri(cx, cy, W, H):
        if sum(x for x, _ in pth)/len(pth) <= cx:
            gd.line(pth, fill=accent+(220,), width=max(2, int(S*0.02)), joint="curve")
    _clip(im, gl, lm)
    d = ImageDraw.Draw(im)
    for x, y in [(cx+W*0.16, cy-H*0.20), (cx+W*0.34, cy), (cx+W*0.16, cy+H*0.20)]:
        d.line([(cx+W*0.05, cy), (x, y)], fill=fg+(220,), width=max(2, int(S*0.013))); _dot(d, x, y, S*0.026, accent)

def e_neuron(im, fg, accent):
    S = im.size[0]; d = ImageDraw.Draw(im); cx = cy = S/2
    for k in range(7):
        a = 2*math.pi*k/7
        x, y = cx+math.cos(a)*S*0.34, cy+math.sin(a)*S*0.34
        mx, my = cx+math.cos(a)*S*0.18, cy+math.sin(a)*S*0.18
        d.line([(cx, cy), (mx, my), (x, y)], fill=fg+(230,), width=max(2, int(S*0.014)))
        for s in (-0.5, 0.5):
            bx, by = x+math.cos(a+s)*S*0.06, y+math.sin(a+s)*S*0.06
            d.line([(x, y), (bx, by)], fill=fg+(200,), width=max(1, int(S*0.01))); _dot(d, bx, by, S*0.013, accent)
    _dot(d, cx, cy, S*0.085, fg); _dot(d, cx, cy, S*0.04, accent)

def e_maze(im, fg, accent):
    S = im.size[0]
    for k in (1.0, 0.72, 0.46, 0.22):
        _fill(im, _edge(_tv_mask_k(S, k)[0], S), fg)

def e_hex(im, fg, accent):
    S = im.size[0]; m, _ = _tv_mask_k(S)
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    r = S*0.085; dx = r*1.5; dy = r*math.sqrt(3)
    for row in range(-1, 13):
        for col in range(-1, 13):
            x = col*dx; y = row*dy + (col % 2)*dy/2
            d.polygon(_ngon(x, y, r, 6, rot=math.pi/6), outline=fg+(220,), width=max(1, int(S*0.011)))
    _clip(im, layer, m); _fill(im, _edge(m, S), fg)

def e_chip(im, fg, accent):
    S = im.size[0]; d = ImageDraw.Draw(im); a, b = S*0.27, S*0.73
    for t in (0.38, 0.5, 0.62):
        for x0, y0, x1, y1 in [(S*t-S*0.013, S*0.15, S*t+S*0.013, a),
                               (S*t-S*0.013, b, S*t+S*0.013, S*0.85),
                               (S*0.15, S*t-S*0.013, a, S*t+S*0.013),
                               (b, S*t-S*0.013, S*0.85, S*t+S*0.013)]:
            d.rounded_rectangle([x0, y0, x1, y1], radius=S*0.006, fill=fg+(255,))
    d.rounded_rectangle([a, a, b, b], radius=S*0.045, outline=fg+(255,), width=max(2, int(S*0.02)))
    cx = cy = S/2; W = (b-a)*0.78; H = (b-a)*0.56
    gl = Image.new("RGBA", (S, S), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
    for pth in _tv_gyri(cx, cy, W, H):
        gd.line(pth, fill=accent+(235,), width=max(2, int(S*0.015)), joint="curve")
    inner = Image.new("L", (S, S), 0); ImageDraw.Draw(inner).rounded_rectangle([a, a, b, b], radius=S*0.045, fill=255)
    _clip(im, gl, inner)

def e_dots(im, fg, accent):
    S = im.size[0]; m, (cx, cy, W, H) = _tv_mask_k(S)
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    step = S*0.066; y = step*0.5
    while y < S:
        x = step*0.5
        while x < S:
            _dot(d, x, y, S*0.016, fg); x += step
        y += step
    _clip(im, layer, m); _fill(im, _edge(m, S), fg)
    ImageDraw.Draw(im).line([(cx, cy-H*0.44), (cx, cy+H*0.44)], fill=accent+(235,), width=max(2, int(S*0.018)))

def e_constellation(im, fg, accent):
    S = im.size[0]; cx = cy = S/2; W = S*0.6; H = S*0.46; d = ImageDraw.Draw(im); n = 12
    pts = [(cx+math.cos(2*math.pi*i/n)*W*(0.5+0.06*math.sin(i*1.7)),
            cy+math.sin(2*math.pi*i/n)*H*(0.5+0.06*math.sin(i*1.7))) for i in range(n)]
    for i in range(n):
        d.line([pts[i], pts[(i+1) % n]], fill=fg+(140,), width=max(1, int(S*0.009)))
    inner = [(cx, cy-H*0.3), (cx, cy), (cx, cy+H*0.3)]
    for i in range(len(inner)-1):
        d.line([inner[i], inner[i+1]], fill=fg+(140,), width=max(1, int(S*0.009)))
    for pnt in pts: _dot(d, pnt[0], pnt[1], S*0.022, fg)
    for pnt in inner: _dot(d, pnt[0], pnt[1], S*0.024, accent)

def e_bulb(im, fg, accent):
    S = im.size[0]; d = ImageDraw.Draw(im); cx = S/2
    d.ellipse([S*0.27, S*0.14, S*0.73, S*0.60], outline=fg+(255,), width=max(2, int(S*0.022)))
    d.rounded_rectangle([S*0.44, S*0.62, S*0.56, S*0.76], radius=S*0.02, outline=fg+(255,), width=max(2, int(S*0.016)))
    cy = S*0.37; W = S*0.30; H = S*0.24
    gl = Image.new("RGBA", (S, S), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
    for pth in _tv_gyri(cx, cy, W, H):
        gd.line(pth, fill=accent+(235,), width=max(2, int(S*0.014)), joint="curve")
    inner = Image.new("L", (S, S), 0); ImageDraw.Draw(inner).ellipse([S*0.27, S*0.14, S*0.73, S*0.60], fill=255)
    _clip(im, gl, inner)

def e_spiral(im, fg, accent):
    S = im.size[0]; d = ImageDraw.Draw(im)
    for sgn, ox in ((-1, 0.345), (1, 0.655)):
        cx = S*ox; cy = S*0.5; pts = []
        for k in range(64):
            t = k/63; ang = sgn*t*math.pi*3.2; r = S*0.018+t*S*0.155
            pts.append((cx+math.cos(ang)*r, cy+math.sin(ang)*r))
        d.line(pts, fill=fg+(255,), width=max(2, int(S*0.02)), joint="curve")
    _dot(d, S*0.345, S*0.5, S*0.02, accent); _dot(d, S*0.655, S*0.5, S*0.02, accent)

def e_gear(im, fg, accent):
    S = im.size[0]; d = ImageDraw.Draw(im); cx = cy = S/2; teeth = 12; R = S*0.34; r = S*0.27
    pts = []
    for i in range(teeth*2):
        ang = math.pi*i/teeth; rad = R if i % 2 == 0 else r
        pts.append((cx+math.cos(ang)*rad, cy+math.sin(ang)*rad))
    d.polygon(pts, outline=fg+(255,), width=max(2, int(S*0.017)))
    W = S*0.34; H = S*0.28
    gl = Image.new("RGBA", (S, S), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
    for pth in _tv_gyri(cx, cy, W, H):
        gd.line(pth, fill=accent+(235,), width=max(2, int(S*0.016)), joint="curve")
    inner = Image.new("L", (S, S), 0); ImageDraw.Draw(inner).ellipse([cx-r, cy-r, cx+r, cy+r], fill=255)
    _clip(im, gl, inner)

def e_spark(im, fg, accent):
    cx, cy, W, H = e_topview(im, fg, accent, filled=True)
    S = im.size[0]; d = ImageDraw.Draw(im)
    for k in range(6):
        a = math.pi*k/3; L = S*0.085
        d.line([(cx, cy-H*0.60), (cx+math.cos(a)*L, cy-H*0.60+math.sin(a)*L)],
               fill=accent+(255,), width=max(2, int(S*0.018)))


# ── 20 DIFFERENT brain designs (distinct engines, dashboard palette) ───────────
def m01(S): im=_bg(S,("grad",M_FOREST,M_FOREST_DK)); e_topview(im,M_PAPER,M_SAGE); return im
def m02(S): im=_bg(S,M_FOREST); e_topview(im,M_PAPER,M_FOREST_DK,filled=True); return im
def m03(S): im=_bg(S,OBS_BG); e_circuit(im,OBS_FG,OBS_AMBER); return im
def m04(S): im=_bg(S,FW_BLUE); e_neuralnet(im,FW_PAPER,FW_SOFT); return im
def m05(S): im=_bg(S,M_FOREST); e_halfcircuit(im,M_PAPER,M_SAGE); return im
def m06(S): im=_bg(S,TEAL_DK); e_neuron(im,M_PAPER,TEAL_HOVER); return im
def m07(S): im=_bg(S,BROWN_DK); e_maze(im,M_PAPER,BROWN_SOFT); return im
def m08(S): im=_bg(S,M_FOREST); e_hex(im,M_PAPER,M_SAGE); return im
def m09(S): im=_bg(S,OBS_BG); e_chip(im,OBS_FG,OBS_AMBER); return im
def m10(S): im=_bg(S,M_FOREST); e_dots(im,M_PAPER,M_SAGE); return im
def m11(S): im=_bg(S,OBS_BG); e_constellation(im,OBS_FG,OBS_AMBER); return im
def m12(S): im=_bg(S,M_PAPER); e_topview(im,M_FOREST,M_SAGE,filled=True); return im
def m13(S): im=_bg(S,M_FOREST); e_bulb(im,M_PAPER,M_SAGE); return im
def m14(S): im=_bg(S,FW_BLUE); e_spiral(im,FW_PAPER,FW_SOFT); return im
def m15(S): im=_bg(S,BROWN_DK); e_gear(im,M_PAPER,BROWN_SOFT); return im
def m16(S): im=_bg(S,M_FOREST); e_spark(im,M_PAPER,M_SAGE); return im
def m17(S): im=_bg(S,M_FOREST); e_neuralnet(im,M_PAPER,M_SAGE); return im
def m18(S): im=_bg(S,TEAL_DK); e_maze(im,M_PAPER,TEAL_HOVER); return im
def m19(S): im=_bg(S,OBS_BG); e_neuron(im,OBS_FG,OBS_AMBER); return im
def m20(S): im=_bg(S,M_FOREST); e_chip(im,M_PAPER,M_SAGE); return im


DESIGNS = [
    ("Top-view brain (line)", m01), ("Top-view brain (solid)", m02),
    ("Circuit-trace brain", m03), ("Neural network", m04),
    ("Half-organic / half-circuit", m05), ("Neuron cell", m06),
    ("Contour brain", m07), ("Hexagon-mesh brain", m08),
    ("Chip brain", m09), ("Dotted brain", m10),
    ("Constellation brain", m11), ("Top-view on paper", m12),
    ("Brain in lightbulb", m13), ("Spiral hemispheres", m14),
    ("Gear brain", m15), ("Brain + spark", m16),
    ("Neural net (forest)", m17), ("Contour brain (teal)", m18),
    ("Neuron (observatory)", m19), ("Chip brain (forest)", m20),
]


# ── the canonical Metis icon ──────────────────────────────────────────────────
# Matches the dashboard's default identity (warm paper + deep forest-green accent,
# styles.css :root) and keeps the digital/circuit "AI brain" the previous icon had —
# restrained to two greens + cream + subtle sage synapse nodes. Not colourful.
M_FOREST = (45, 74, 58)     # --m-accent  #2d4a3a
M_FOREST_DK = (34, 59, 46)  # --m-accent-hover #223b2e
M_SAGE = (74, 106, 84)      # --m-accent-soft #4a6a54
M_PAPER = (245, 242, 234)   # --m-bg #f5f2ea


def metis_brand(S):
    """Cream wireframe brain with sage synapse nodes on a deep forest-green card."""
    im = _bg(S, ("grad", M_FOREST, M_FOREST_DK))
    cx, cy, W, H = _brain(im, M_PAPER, M_PAPER, style="line")
    d = ImageDraw.Draw(im)
    paths = _brain_grooves(cx, cy, W, H)
    ends = [p[-1] for p in paths[1:]] + [p[0] for p in paths[1:]]
    for i, (x, y) in enumerate(ends):
        _dot(d, x, y, S * 0.024, M_SAGE if i % 5 == 0 else M_PAPER)
    return im


def render(idx, out_size):
    name, fn = DESIGNS[idx]
    big = fn(out_size * SS)
    return big.resize((out_size, out_size), Image.LANCZOS)


def build_gallery():
    out_dir = HERE / "icon-previews"
    out_dir.mkdir(exist_ok=True)
    cards = []
    for i, (name, _) in enumerate(DESIGNS):
        img = render(i, 180)
        chk = Image.new("RGBA", img.size, (255, 255, 255, 255))  # white card behind
        chk.alpha_composite(img)
        buf = io.BytesIO(); chk.convert("RGB").save(buf, "PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        cards.append(
            f'<div class="card"><img src="data:image/png;base64,{b64}">'
            f'<div class="lbl"><b>{i+1}.</b> {name}</div></div>'
        )
    html = (
        "<!doctype html><meta charset=utf-8><title>Metis icon options</title>"
        "<style>body{background:#0f172a;color:#e2e8f0;font-family:Segoe UI,system-ui,"
        "sans-serif;margin:0;padding:28px}h1{font-size:20px;font-weight:600}"
        "p{color:#94a3b8;margin:4px 0 22px}.grid{display:grid;grid-template-columns:"
        "repeat(5,1fr);gap:18px}.card{background:#1e293b;border:1px solid #334155;"
        "border-radius:14px;padding:14px;text-align:center}.card img{width:120px;"
        "height:120px;border-radius:12px;box-shadow:0 4px 14px rgba(0,0,0,.35)}"
        ".lbl{margin-top:10px;font-size:13px;color:#cbd5e1}.lbl b{color:#fff}</style>"
        "<h1>Metis desktop icon — 20 options</h1>"
        "<p>Pick a number and tell Claude, e.g. <b>“use icon 8”</b>. "
        "Previews are pixel-identical to the installed icon.</p>"
        f'<div class="grid">{"".join(cards)}</div>'
    )
    idx_path = out_dir / "index.html"
    idx_path.write_text(html, encoding="utf-8")
    return idx_path


_ICO_SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]


def _install(base, label):
    written = []
    for target in INSTALL_TARGETS:
        target.parent.mkdir(parents=True, exist_ok=True)
        base.save(target, format="ICO", sizes=_ICO_SIZES)
        written.append(target)
    return label, written


def build_ico(n):
    idx = n - 1
    return _install(render(idx, 256), DESIGNS[idx][0])


def build_brand():
    return _install(metis_brand(256 * SS).resize((256, 256), Image.LANCZOS),
                    "Metis brand — forest wireframe brain")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gallery"
    if cmd == "gallery":
        p = build_gallery()
        print("Gallery written:", p)
    elif cmd == "build":
        name, written = build_ico(int(sys.argv[2]))
        print(f"Built icon '{name}' ({len(written)} files):")
        for w in written:
            print("  -", w)
    elif cmd == "brand":
        name, written = build_brand()
        print(f"Built icon '{name}' ({len(written)} files):")
        for w in written:
            print("  -", w)
    else:
        print(__doc__)
