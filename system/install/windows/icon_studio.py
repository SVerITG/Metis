#!/usr/bin/env python3
"""
icon_studio.py — vector (SVG) Metis icon studio.

Why SVG: real icon designs are vector paths, not ellipse blobs. SVG renders crisp
in the browser gallery AND rasterises faithfully to a multi-resolution .ico via
cairosvg — so the preview you pick is exactly what gets installed.

Concepts (all "simple wired" / line style): brain, brain-circuit, brain-network,
neural-network, lightbulb-brain, AI-chip, neuron, half-brain/circuit, … crossed
with many background shapes + colours = 100 options.

Usage:
  python icon_studio.py gallery     # -> icon-previews/index.html  (open, pick a number)
  python icon_studio.py build N     # rasterise option N -> metis.ico (installed)
"""
import io
import sys
from pathlib import Path

import cairosvg
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
INSTALL_TARGETS = [HERE / "metis.ico", ROOT / "system" / "app-py" / "static" / "metis.ico"]

# ── palettes (dashboard themes + muted extras) : bg, bg2(grad), fg, accent ─────
PALETTES = {
    "forest":      ("#2d4a3a", "#223b2e", "#f5f2ea", "#7fb0a0"),
    "observatory": ("#15130f", "#241d12", "#f3ead6", "#d99a4c"),
    "fieldwork":   ("#2d4480", "#1a2040", "#f0eff8", "#7ab0e8"),
    "teal":        ("#16403b", "#0f2e2a", "#eafaf6", "#4ad4c4"),
    "sienna":      ("#3a2614", "#27190d", "#f5ead9", "#e0b07a"),
    "slate":       ("#334155", "#1e293b", "#f1f5f9", "#93b3c5"),
    "plum":        ("#3b2a4d", "#271a34", "#efe9f5", "#b79be0"),
    "paper":       ("#f5f2ea", "#e8e2d2", "#2d4a3a", "#4a6a54"),
    "navy":        ("#1e293b", "#0f172a", "#e2e8f0", "#7dd3fc"),
    "charcoal":    ("#1f2428", "#14181b", "#eceff1", "#84c1b4"),
}

SW = 5.5  # stroke width in the 100×100 viewBox ("wired" weight)


# ── backgrounds (return svg markup for a 100×100 canvas) ───────────────────────
def bg_markup(shape, fill, pal, idx):
    bg, bg2 = pal[0], pal[1]
    defs = ""
    paint = bg
    if fill == "grad":
        gid = f"g{idx}"
        defs = (f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
                f'<stop offset="0" stop-color="{bg}"/><stop offset="1" stop-color="{bg2}"/>'
                f'</linearGradient></defs>')
        paint = f"url(#{gid})"
    if shape == "circle":
        body = f'<circle cx="50" cy="50" r="49" fill="{paint}"/>'
    elif shape == "round":
        body = f'<rect x="1" y="1" width="98" height="98" rx="16" fill="{paint}"/>'
    else:  # squircle
        body = f'<rect x="1" y="1" width="98" height="98" rx="26" fill="{paint}"/>'
    return defs + body


# ── glyphs (wired line style); each returns inner svg markup given fg, accent ──
def _stroke(fg, w=SW):
    return f'fill="none" stroke="{fg}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"'


def g_brain(fg, ac):  # anatomical side profile, wired
    return (f'<g {_stroke(fg)}>'
            '<path d="M50 24 C44 16 31 17 28 26 C19 25 15 34 21 40 C14 45 16 56 25 56 '
            'C24 66 34 72 42 67 C47 75 58 74 61 66 C71 70 81 61 76 53 C84 48 82 37 74 37 '
            'C73 26 60 18 50 24 Z"/>'
            '<path d="M50 25 V66"/>'
            '<path d="M34 31 C40 34 40 40 34 43"/><path d="M30 48 C37 50 39 56 33 59"/>'
            '<path d="M66 32 C60 35 60 41 66 44"/><path d="M70 50 C63 52 61 58 67 61"/></g>')


def g_brain_top(fg, ac):  # top view, two hemispheres
    return (f'<g {_stroke(fg)}>'
            '<path d="M50 21 C29 21 19 33 19 50 C19 68 31 79 50 79 C69 79 81 68 81 50 '
            'C81 33 71 21 50 21 Z"/><line x1="50" y1="23" x2="50" y2="77"/>'
            '<path d="M50 33 C41 33 39 39 45 43"/><path d="M50 49 C40 49 38 56 46 59"/>'
            '<path d="M50 64 C42 64 40 69 46 72"/>'
            '<path d="M50 33 C59 33 61 39 55 43"/><path d="M50 49 C60 49 62 56 54 59"/>'
            '<path d="M50 64 C58 64 60 69 54 72"/></g>')


def g_brain_circuit(fg, ac):  # brain outline + circuit pads
    nodes = [(34, 32), (30, 52), (44, 67), (66, 32), (70, 52), (58, 67)]
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="3.4" fill="{ac}"/>' for x, y in nodes)
    return (g_brain(fg, ac) + dots +
            f'<g {_stroke(ac, 3)}><path d="M50 45 H66"/><path d="M50 45 H34"/>'
            '<path d="M50 45 V67"/></g>'
            f'<circle cx="50" cy="45" r="4" fill="{ac}"/>')


def g_brain_network(fg, ac):  # nodes laid out in a brain shape, connected
    pts = [(30, 34), (46, 27), (62, 31), (24, 48), (40, 46), (58, 47), (72, 46),
           (33, 64), (50, 68), (66, 63)]
    edges = [(0, 1), (1, 2), (0, 3), (0, 4), (1, 4), (2, 5), (2, 6), (4, 5),
             (3, 7), (4, 8), (5, 8), (6, 9), (7, 8), (8, 9)]
    lines = "".join(f'<line x1="{pts[a][0]}" y1="{pts[a][1]}" x2="{pts[b][0]}" y2="{pts[b][1]}"/>'
                    for a, b in edges)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="4" fill="{ac}"/>' for x, y in pts)
    return f'<g {_stroke(fg, 2.6)}>{lines}</g>{dots}'


def g_neural_net(fg, ac):  # classic 3-layer NN
    L = [[(28, 36), (28, 64)], [(50, 28), (50, 50), (50, 72)], [(72, 36), (72, 64)]]
    lines = ""
    for a in range(2):
        for p in L[a]:
            for q in L[a + 1]:
                lines += f'<line x1="{p[0]}" y1="{p[1]}" x2="{q[0]}" y2="{q[1]}"/>'
    dots = ""
    for i, col in enumerate(L):
        for x, y in col:
            dots += f'<circle cx="{x}" cy="{y}" r="5.5" fill="{ac if i==1 else fg}"/>'
    return f'<g {_stroke(fg, 2.4)}>{lines}</g>{dots}'


def g_deep_net(fg, ac):  # 4-layer deep net
    xs = [24, 42, 58, 76]
    L = [[(xs[0], 38), (xs[0], 62)], [(xs[1], 30), (xs[1], 50), (xs[1], 70)],
         [(xs[2], 30), (xs[2], 50), (xs[2], 70)], [(xs[3], 38), (xs[3], 62)]]
    lines = ""
    for a in range(3):
        for p in L[a]:
            for q in L[a + 1]:
                lines += f'<line x1="{p[0]}" y1="{p[1]}" x2="{q[0]}" y2="{q[1]}"/>'
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="4.6" fill="{ac if 0<i<3 else fg}"/>'
                   for i, col in enumerate(L) for x, y in col)
    return f'<g {_stroke(fg, 2)}>{lines}</g>{dots}'


def g_lightbulb_brain(fg, ac):  # bulb with brain folds as filament
    return (f'<g {_stroke(fg)}>'
            '<path d="M50 18 C36 18 26 28 26 41 C26 50 31 56 36 61 C39 64 40 67 40 71 H60 '
            'C60 67 61 64 64 61 C69 56 74 50 74 41 C74 28 64 18 50 18 Z"/>'
            '<line x1="42" y1="77" x2="58" y2="77"/><line x1="44" y1="83" x2="56" y2="83"/>'
            '<path d="M50 30 V58"/><path d="M40 38 C46 40 46 46 40 49"/>'
            '<path d="M60 38 C54 40 54 46 60 49"/></g>')


def g_lightbulb_rays(fg, ac):  # bulb + radiating rays + filament
    rays = ('<g %s><line x1="50" y1="6" x2="50" y2="13"/><line x1="83" y1="20" x2="78" y2="25"/>'
            '<line x1="17" y1="20" x2="22" y2="25"/><line x1="90" y1="44" x2="83" y2="44"/>'
            '<line x1="10" y1="44" x2="17" y2="44"/></g>') % _stroke(ac, 4)
    return (f'<g {_stroke(fg)}>'
            '<circle cx="50" cy="42" r="22"/>'
            '<line x1="42" y1="70" x2="58" y2="70"/><line x1="44" y1="76" x2="56" y2="76"/>'
            '<path d="M44 34 L50 48 L56 34"/><line x1="50" y1="48" x2="50" y2="56"/></g>' + rays)


def g_chip(fg, ac):  # AI chip / CPU with circuit traces
    pins = ""
    for t in (34, 50, 66):
        pins += (f'<line x1="{t}" y1="14" x2="{t}" y2="26"/><line x1="{t}" y1="74" x2="{t}" y2="86"/>'
                 f'<line x1="14" y1="{t}" x2="26" y2="{t}"/><line x1="74" y1="{t}" x2="86" y2="{t}"/>')
    return (f'<g {_stroke(fg)}>{pins}<rect x="26" y="26" width="48" height="48" rx="8"/></g>'
            f'<g {_stroke(ac, 3)}><path d="M40 40 H50 V52 H60"/><path d="M40 60 H52"/></g>'
            f'<circle cx="50" cy="52" r="3.6" fill="{ac}"/><circle cx="40" cy="40" r="3" fill="{ac}"/>')


def g_chip_brain(fg, ac):  # chip with a small brain inside
    pins = ""
    for t in (34, 50, 66):
        pins += (f'<line x1="{t}" y1="14" x2="{t}" y2="26"/><line x1="{t}" y1="74" x2="{t}" y2="86"/>'
                 f'<line x1="14" y1="{t}" x2="26" y2="{t}"/><line x1="74" y1="{t}" x2="86" y2="{t}"/>')
    brain = ('<g %s transform="translate(31,33) scale(0.40)">'
             '<path d="M50 24 C44 16 31 17 28 26 C19 25 15 34 21 40 C14 45 16 56 25 56 '
             'C24 66 34 72 42 67 C47 75 58 74 61 66 C71 70 81 61 76 53 C84 48 82 37 74 37 '
             'C73 26 60 18 50 24 Z"/><path d="M50 25 V66"/></g>') % _stroke(ac, 9)
    return f'<g {_stroke(fg)}>{pins}<rect x="26" y="26" width="48" height="48" rx="8"/></g>{brain}'


def g_half(fg, ac):  # half organic brain / half circuit
    return (f'<g {_stroke(fg)}>'
            '<path d="M50 24 C44 16 31 17 28 26 C19 25 15 34 21 40 C14 45 16 56 25 56 '
            'C24 66 34 72 42 67 C47 73 50 74 50 74"/>'
            '<path d="M50 24 V74"/>'
            '<path d="M34 31 C40 34 40 40 34 43"/><path d="M30 48 C37 50 39 56 33 59"/></g>'
            f'<g {_stroke(ac, 3.4)}><path d="M50 36 H64 V48"/><path d="M50 52 H60 V64"/>'
            '<path d="M50 44 H70"/></g>'
            f'<circle cx="64" cy="36" r="3.4" fill="{ac}"/><circle cx="64" cy="48" r="3.4" fill="{ac}"/>'
            f'<circle cx="60" cy="64" r="3.4" fill="{ac}"/><circle cx="70" cy="44" r="3.4" fill="{ac}"/>')


def g_neuron(fg, ac):  # single neuron with dendrites
    import math
    arms = ""
    for k in range(7):
        a = 2 * math.pi * k / 7
        x, y = 50 + math.cos(a) * 33, 50 + math.sin(a) * 33
        mx, my = 50 + math.cos(a) * 16, 50 + math.sin(a) * 16
        arms += f'<path d="M50 50 L{mx:.1f} {my:.1f} L{x:.1f} {y:.1f}"/>'
        for s in (-0.5, 0.5):
            bx, by = x + math.cos(a + s) * 7, y + math.sin(a + s) * 7
            arms += f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{bx:.1f}" y2="{by:.1f}"/>'
    tips = ""
    for k in range(7):
        a = 2 * math.pi * k / 7
        x, y = 50 + math.cos(a) * 33, 50 + math.sin(a) * 33
        tips += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{ac}"/>'
    return (f'<g {_stroke(fg, 3)}>{arms}</g>{tips}'
            f'<circle cx="50" cy="50" r="9" fill="none" stroke="{fg}" stroke-width="4"/>'
            f'<circle cx="50" cy="50" r="3.5" fill="{ac}"/>')


def g_synapse(fg, ac):  # connected-node cloud
    pts = [(28, 30), (50, 24), (70, 32), (22, 52), (44, 48), (64, 52),
           (36, 70), (58, 70), (78, 56)]
    edges = [(0, 1), (1, 2), (0, 4), (1, 4), (2, 5), (3, 4), (4, 5), (5, 8),
             (3, 6), (4, 7), (6, 7), (7, 8)]
    lines = "".join(f'<line x1="{pts[a][0]}" y1="{pts[a][1]}" x2="{pts[b][0]}" y2="{pts[b][1]}"/>'
                    for a, b in edges)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{fg}"/>' for x, y in pts)
    glow = "".join(f'<circle cx="{pts[i][0]}" cy="{pts[i][1]}" r="4.5" fill="{ac}"/>' for i in (1, 4, 7))
    return f'<g {_stroke(fg, 2.4)}>{lines}</g>{dots}{glow}'


GLYPHS = [
    ("Brain (wired)", g_brain), ("Brain top-view", g_brain_top),
    ("Brain circuit", g_brain_circuit), ("Brain network", g_brain_network),
    ("Neural network", g_neural_net), ("Deep net", g_deep_net),
    ("Lightbulb brain", g_lightbulb_brain), ("Lightbulb rays", g_lightbulb_rays),
    ("AI chip", g_chip), ("Chip + brain", g_chip_brain),
    ("Half brain/circuit", g_half), ("Neuron", g_neuron), ("Synapse cloud", g_synapse),
]

# background variants: (shape, fill, palette-key) — spread of shapes/colours
BG_VARIANTS = [
    ("squircle", "solid", "forest"), ("circle", "solid", "observatory"),
    ("squircle", "grad", "fieldwork"), ("squircle", "solid", "teal"),
    ("circle", "solid", "sienna"), ("squircle", "grad", "plum"),
    ("round", "solid", "slate"), ("squircle", "solid", "paper"),
]

# 100 combos: every glyph across every background, capped at 100
COMBOS = [(g, bg) for bg in BG_VARIANTS for g in GLYPHS][:100]


def svg_for(combo, idx, size=100):
    (gname, gfn), (shape, fill, palkey) = combo
    pal = PALETTES[palkey]
    inner = gfn(pal[2], pal[3])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
            f'width="{size}" height="{size}">{bg_markup(shape, fill, pal, idx)}{inner}</svg>')


def build_gallery():
    out_dir = HERE / "icon-previews"
    out_dir.mkdir(exist_ok=True)
    cards = []
    for i, combo in enumerate(COMBOS):
        (gname, _), (shape, fill, palkey) = combo
        svg = svg_for(combo, i, size=104)
        cards.append(f'<div class="c">{svg}<div class="l"><b>{i+1}.</b> {gname} · {palkey}</div></div>')
    html = (
        "<!doctype html><meta charset=utf-8><title>Metis icon studio — 100</title>"
        "<style>body{background:#0f172a;color:#e2e8f0;font-family:Segoe UI,system-ui,sans-serif;"
        "margin:0;padding:26px}h1{font-size:20px;margin:0 0 2px}p{color:#94a3b8;margin:4px 0 20px}"
        ".g{display:grid;grid-template-columns:repeat(5,1fr);gap:16px}.c{background:#1e293b;"
        "border:1px solid #334155;border-radius:14px;padding:12px;text-align:center}"
        ".c svg{width:104px;height:104px;border-radius:12px;box-shadow:0 3px 10px rgba(0,0,0,.35)}"
        ".l{margin-top:9px;font-size:12px;color:#cbd5e1}.l b{color:#fff}</style>"
        "<h1>Metis icon studio — 100 options</h1>"
        "<p>Brain · brain-circuit · brain-network · neural-net · lightbulb · AI-chip · neuron, "
        "wired style, across background shapes &amp; colours. Pick a number → tell Claude "
        "<b>“use icon N”</b>. Previews are the exact vector that gets installed.</p>"
        f'<div class="g">{"".join(cards)}</div>')
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    return out_dir / "index.html"


def build_ico(n):
    combo = COMBOS[n - 1]
    png = cairosvg.svg2png(bytestring=svg_for(combo, n - 1, size=256).encode(),
                           output_width=256, output_height=256)
    base = Image.open(io.BytesIO(png)).convert("RGBA")
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    written = []
    for t in INSTALL_TARGETS:
        t.parent.mkdir(parents=True, exist_ok=True)
        base.save(t, format="ICO", sizes=sizes)
        written.append(t)
    (gname, _), (_, _, palkey) = combo
    return f"{gname} · {palkey}", written


# ── focused set: option 88 (chip+brain on slate) wiring colours + more concepts ─
def _pins(fg):
    s = ""
    for t in (34, 50, 66):
        s += (f'<line x1="{t}" y1="14" x2="{t}" y2="26"/><line x1="{t}" y1="74" x2="{t}" y2="86"/>'
              f'<line x1="14" y1="{t}" x2="26" y2="{t}"/><line x1="74" y1="{t}" x2="86" y2="{t}"/>')
    return s


def g_brain_on_chip(fg, ac):
    brain = ('<g %s transform="translate(20,-2) scale(0.6)">'
             '<path d="M50 24 C44 16 31 17 28 26 C19 25 15 34 21 40 C14 45 16 56 25 56 '
             'C24 66 34 72 42 67 C47 75 58 74 61 66 C71 70 81 61 76 53 C84 48 82 37 74 37 '
             'C73 26 60 18 50 24 Z"/><path d="M50 25 V62"/></g>') % _stroke(fg)
    base = (f'<g {_stroke(fg)}><rect x="34" y="68" width="32" height="13" rx="3"/>'
            '<line x1="42" y1="81" x2="42" y2="89"/><line x1="50" y1="81" x2="50" y2="89"/>'
            '<line x1="58" y1="81" x2="58" y2="89"/></g>')
    return brain + base + f'<circle cx="42" cy="74" r="2.6" fill="{ac}"/><circle cx="58" cy="74" r="2.6" fill="{ac}"/>'


def g_chip_brain_net(fg, ac):
    nodes = [(38, 40), (58, 38), (34, 58), (52, 54), (64, 62)]
    edges = [(0, 1), (0, 3), (1, 3), (2, 3), (3, 4), (1, 4)]
    lines = "".join(f'<line x1="{nodes[a][0]}" y1="{nodes[a][1]}" x2="{nodes[b][0]}" y2="{nodes[b][1]}"/>'
                    for a, b in edges)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="3.4" fill="{ac}"/>' for x, y in nodes)
    return (f'<g {_stroke(fg)}>{_pins(fg)}<rect x="26" y="26" width="48" height="48" rx="8"/></g>'
            f'<g {_stroke(ac, 2.4)}>{lines}</g>{dots}')


def g_lightbulb_chip(fg, ac):
    bulb = (f'<g {_stroke(fg)}><circle cx="50" cy="36" r="20"/>'
            '<path d="M43 33 L50 45 L57 33"/><line x1="50" y1="45" x2="50" y2="54"/></g>')
    chip = (f'<g {_stroke(fg)}><rect x="38" y="58" width="24" height="20" rx="4"/>'
            '<line x1="44" y1="78" x2="44" y2="86"/><line x1="50" y1="78" x2="50" y2="86"/>'
            '<line x1="56" y1="78" x2="56" y2="86"/></g>')
    return bulb + chip + f'<circle cx="50" cy="68" r="3" fill="{ac}"/>'


def g_lightbulb_net(fg, ac):
    net = ('<g %s><line x1="42" y1="30" x2="50" y2="38"/><line x1="58" y1="30" x2="50" y2="38"/>'
           '<line x1="42" y1="46" x2="50" y2="38"/><line x1="58" y1="46" x2="50" y2="38"/></g>') % _stroke(ac, 2.4)
    nodes = (f'<circle cx="42" cy="30" r="3" fill="{ac}"/><circle cx="58" cy="30" r="3" fill="{ac}"/>'
             f'<circle cx="50" cy="38" r="3.4" fill="{ac}"/>'
             f'<circle cx="42" cy="46" r="3" fill="{ac}"/><circle cx="58" cy="46" r="3" fill="{ac}"/>')
    return (f'<g {_stroke(fg)}><path d="M50 14 C36 14 26 24 26 37 C26 46 31 52 36 57 C39 60 40 63 40 67 H60 '
            'C60 63 61 60 64 57 C69 52 74 46 74 37 C74 24 64 14 50 14 Z"/>'
            '<line x1="42" y1="73" x2="58" y2="73"/><line x1="44" y1="79" x2="56" y2="79"/></g>'
            + net + nodes)


def g_brain_bulb(fg, ac):
    bulb = (f'<g {_stroke(fg)}><path d="M50 14 C35 14 24 25 24 39 C24 49 30 56 36 61 '
            'C40 65 41 68 41 72 H59 C59 68 60 65 64 61 C70 56 76 49 76 39 C76 25 65 14 50 14 Z"/>'
            '<line x1="43" y1="78" x2="57" y2="78"/><line x1="45" y1="84" x2="55" y2="84"/></g>')
    folds = (f'<g {_stroke(ac, 3.4)}><path d="M50 26 V60"/><path d="M40 34 C46 37 46 43 40 46"/>'
             '<path d="M60 34 C54 37 54 43 60 46"/><path d="M38 50 C44 52 45 57 39 59"/>'
             '<path d="M62 50 C56 52 55 57 61 59"/></g>')
    return bulb + folds


# ── procedurally-detailed brain (top-down, many gyri) — closer to the references ─
import math as _m


def _smooth_closed(pts):
    mx0 = (pts[0][0] + pts[-1][0]) / 2; my0 = (pts[0][1] + pts[-1][1]) / 2
    d = f"M {mx0:.1f} {my0:.1f} "
    for i in range(len(pts)):
        p = pts[i]; q = pts[(i + 1) % len(pts)]
        d += f"Q {p[0]:.1f} {p[1]:.1f} {(p[0]+q[0])/2:.1f} {(p[1]+q[1])/2:.1f} "
    return d + "Z"


def _dbrain_outline(cx=50, cy=50, rx=33, ry=30, lobes=9, amp=0.11, n=80):
    pts = []
    for i in range(n):
        th = 2 * _m.pi * i / n
        r = 1 + amp * _m.sin(lobes * th + 0.4) + 0.03 * _m.sin(4 * th)
        pts.append((cx + _m.cos(th) * rx * r, cy + _m.sin(th) * ry * r))
    return _smooth_closed(pts)


def _dbrain_sulci(cx=50, cy=50, rx=33, ry=30, side=0):
    """Swirled, hooked gyri folds (not parallel ribs). side: -1/1 one lobe, 0 both."""
    paths = []
    pts = []  # wavy central fissure
    for k in range(26):
        t = k / 25
        pts.append((cx + _m.sin(t * _m.pi * 2.4) * rx * 0.05, cy - ry * 0.82 + t * ry * 1.64))
    paths.append("M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts))
    signs = (-1, 1) if side == 0 else (side,)
    for sgn in signs:
        for j, fy in enumerate((-0.56, -0.30, -0.05, 0.20, 0.46)):
            hook = 1 if j % 2 == 0 else -1            # alternate curl direction
            sx, sy = cx + sgn * rx * 0.10, cy + ry * fy
            mx1, my1 = cx + sgn * rx * 0.34, cy + ry * (fy - hook * 0.16)
            mx2, my2 = cx + sgn * rx * 0.66, cy + ry * (fy + hook * 0.18)
            ex, ey = cx + sgn * rx * 0.58, cy + ry * (fy + hook * 0.30)   # hooks back in
            paths.append(f"M {sx:.1f} {sy:.1f} C {mx1:.1f} {my1:.1f} {mx2:.1f} {my2:.1f} {ex:.1f} {ey:.1f}")
    return paths


def g_dbrain(fg, ac):  # detailed brain, line/wired — pure anatomical
    sulci = "".join(f'<path d="{d}"/>' for d in _dbrain_sulci())
    return f'<g {_stroke(fg, 3.2)}><path d="{_dbrain_outline()}"/>{sulci}</g>'


def g_dbrain_elec(fg, ac):  # detailed brain, left gyri + right circuit (electronic)
    left = "".join(f'<path d="{d}"/>' for d in _dbrain_sulci(side=-1))
    out = f'<g {_stroke(fg, 3.2)}><path d="{_dbrain_outline()}"/>{left}</g>'
    cx, cy, rx, ry = 50, 51, 34, 28
    nodes = [(cx + rx * 0.18, cy - ry * 0.5), (cx + rx * 0.5, cy - ry * 0.34),
             (cx + rx * 0.30, cy - ry * 0.05), (cx + rx * 0.60, cy + ry * 0.12),
             (cx + rx * 0.22, cy + ry * 0.38), (cx + rx * 0.52, cy + ry * 0.5)]
    edges = [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 5), (4, 5)]
    seg = "".join(f'<line x1="{nodes[a][0]:.1f}" y1="{nodes[a][1]:.1f}" '
                  f'x2="{nodes[b][0]:.1f}" y2="{nodes[b][1]:.1f}"/>' for a, b in edges)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.1" fill="{ac}"/>' for x, y in nodes)
    return out + f'<g {_stroke(ac, 2.4)}>{seg}</g>{dots}'


def g_dbrain_nodes(fg, ac):  # detailed brain + synapse nodes at gyri tips
    out = g_dbrain(fg, ac)
    cx, cy, rx, ry = 50, 51, 34, 28
    tips = [(cx + sgn * rx * 0.74, cy + ry * (fy + 0.08))
            for sgn in (-1, 1) for fy in (-0.60, -0.20, 0.20, 0.60)]
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.8" fill="{ac}"/>' for x, y in tips)
    return out + dots


def g_dbrain_filled(fg, ac):  # detailed solid brain with engraved sulci + node accents
    sulci = "".join(f'<path d="{d}"/>' for d in _dbrain_sulci())
    return (f'<path d="{_dbrain_outline()}" fill="{fg}"/>'
            f'<g fill="none" stroke="{ac}" stroke-width="2.6" stroke-linecap="round" '
            f'stroke-linejoin="round" opacity="0.85">{sulci}</g>')


DBRAINS = [("Detailed brain (line)", g_dbrain), ("Electronic (detailed)", g_dbrain_elec),
           ("Detailed + synapses", g_dbrain_nodes), ("Detailed (filled)", g_dbrain_filled)]


# ── side-profile detailed brain (the iconic brain shape) ──────────────────────
# Silhouette: frontal lobe (front/left), bumpy cerebrum top, occipital (back),
# temporal lobe (bottom), cerebellum (lower-back ball) + brain stem.
_SBRAIN = ("M31 31 C24 22 12 26 14 37 C5 39 7 52 17 53 C13 61 20 69 30 65 "
           "C32 72 41 72 44 66 C48 72 56 71 57 64 C63 70 73 67 72 58 "
           "C82 61 90 52 83 44 C91 40 88 28 78 30 C78 21 65 17 59 25 "
           "C53 18 43 18 39 25 C36 21 33 24 31 31 Z")
# cerebellum + brain-stem (drawn as extra strokes)
_SBRAIN_STEM = ("M64 64 C70 66 74 70 72 75 M60 67 C62 73 60 78 55 79")


def _sbrain_folds():
    # swirled internal sulci following the brain's flow (hand-tuned, varied)
    return [
        "M30 34 C36 33 40 38 36 43 C32 47 38 51 33 55",
        "M22 40 C28 41 30 46 25 49",
        "M44 30 C49 33 48 40 42 42 C48 46 47 54 41 56 C46 60 44 66 40 66",
        "M54 32 C58 36 56 43 51 44 C56 49 55 57 50 59",
        "M66 34 C70 38 68 45 63 46 C68 50 67 57 62 58",
        "M76 40 C80 43 79 49 74 50",
    ]


def g_sbrain(fg, ac):
    folds = "".join(f'<path d="{d}"/>' for d in _sbrain_folds())
    return (f'<g {_stroke(fg, 3.2)}><path d="{_SBRAIN}"/>'
            f'<path d="{_SBRAIN_STEM}"/>{folds}</g>')


def g_sbrain_elec(fg, ac):  # side-profile, back half circuit
    fr = _sbrain_folds()[:3]
    folds = "".join(f'<path d="{d}"/>' for d in fr)
    out = (f'<g {_stroke(fg, 3.2)}><path d="{_SBRAIN}"/><path d="{_SBRAIN_STEM}"/>{folds}</g>')
    nodes = [(58, 34), (70, 38), (62, 48), (76, 46), (60, 60), (72, 58)]
    edges = [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 5), (4, 5)]
    seg = "".join(f'<line x1="{nodes[a][0]}" y1="{nodes[a][1]}" x2="{nodes[b][0]}" y2="{nodes[b][1]}"/>'
                  for a, b in edges)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="3" fill="{ac}"/>' for x, y in nodes)
    return out + f'<g {_stroke(ac, 2.4)}>{seg}</g>{dots}'


def g_sbrain_filled(fg, ac):
    folds = "".join(f'<path d="{d}"/>' for d in _sbrain_folds())
    return (f'<path d="{_SBRAIN}" fill="{fg}"/>'
            f'<g fill="none" stroke="{ac}" stroke-width="2.6" stroke-linecap="round" '
            f'stroke-linejoin="round" opacity="0.9"><path d="{_SBRAIN_STEM}"/>{folds}</g>')


SBRAINS = [("Side brain (line)", g_sbrain), ("Side electronic", g_sbrain_elec),
           ("Side filled", g_sbrain_filled)]


# ── "electronic brain" base: a detailed brain silhouette, chip/circuit integrated
# Brain is the hero shape; the chip/circuit from option 88 is folded INTO it
# (right-hemisphere traces, node pads, connector pins).
EBRAIN = ('<path d="M37 23 C31 16 20 18 18 27 C10 28 8 38 16 42 '
          'C9 48 13 58 22 57 C21 66 29 72 37 67 C41 73 50 73 54 68 '
          'C60 72 70 68 70 60 C80 63 88 54 81 47 C89 42 86 30 78 31 '
          'C77 21 65 16 59 23 C52 17 44 17 37 23 Z"/>')
_LFOLDS = ('<path d="M37 30 C43 33 42 39 36 41"/><path d="M31 46 C38 48 39 54 32 56"/>'
           '<path d="M42 28 C47 34 45 42 39 45 C45 50 44 58 39 61"/>')
_RFOLDS = ('<path d="M63 30 C57 33 58 39 64 41"/><path d="M69 46 C62 48 61 54 68 56"/>'
           '<path d="M58 28 C53 34 55 42 61 45 C55 50 56 58 61 61"/>')


def g_ebrain_half(fg, ac):  # left organic gyri, right circuit — classic AI brain
    out = f'<g {_stroke(fg)}>{EBRAIN}<path d="M50 23 V67"/>{_LFOLDS}</g>'
    cir = (f'<g {_stroke(ac, 3)}><path d="M50 35 H63"/><path d="M63 35 V47 H71"/>'
           '<path d="M50 50 H60 V62"/><path d="M50 43 H68"/></g>')
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="3.3" fill="{ac}"/>'
                   for x, y in [(63, 35), (71, 47), (60, 62), (68, 43)])
    return out + cir + dots


def g_ebrain_pins(fg, ac):  # full brain + connector pins (chip integrated as pins)
    pins = ("".join(f'<line x1="{x}" y1="68" x2="{x}" y2="80"/>' for x in (38, 50, 62)) +
            "".join(f'<line x1="14" y1="{y}" x2="6" y2="{y}"/><line x1="86" y1="{y}" x2="94" y2="{y}"/>'
                    for y in (38, 50)))
    out = f'<g {_stroke(fg)}>{EBRAIN}<path d="M50 23 V67"/>{_LFOLDS}{_RFOLDS}{pins}</g>'
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="2.8" fill="{ac}"/>'
                   for x, y in [(38, 80), (50, 80), (62, 80), (6, 38), (94, 38), (6, 50), (94, 50)])
    return out + dots


def g_ebrain_chip(fg, ac):  # brain with a processor chip at its core
    out = f'<g {_stroke(fg)}>{EBRAIN}{_LFOLDS}{_RFOLDS}</g>'
    chip = (f'<g {_stroke(ac, 3)}><rect x="41" y="41" width="18" height="18" rx="3"/>'
            '<line x1="46" y1="36" x2="46" y2="41"/><line x1="54" y1="36" x2="54" y2="41"/>'
            '<line x1="46" y1="59" x2="46" y2="64"/><line x1="54" y1="59" x2="54" y2="64"/>'
            '<line x1="36" y1="46" x2="41" y2="46"/><line x1="36" y1="54" x2="41" y2="54"/>'
            '<line x1="59" y1="46" x2="64" y2="46"/><line x1="59" y1="54" x2="64" y2="54"/></g>')
    return out + chip + f'<circle cx="50" cy="50" r="3.6" fill="{ac}"/>'


def g_ebrain_traces(fg, ac):  # brain outline + circuit traces through both lobes + edge pads
    out = f'<g {_stroke(fg)}>{EBRAIN}<path d="M50 23 V67"/></g>'
    tr = (f'<g {_stroke(ac, 2.8)}><path d="M30 38 H40 V50"/><path d="M28 56 H38"/>'
          '<path d="M70 38 H60 V50"/><path d="M72 56 H62"/><path d="M50 50 V60"/></g>')
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="3" fill="{ac}"/>'
                   for x, y in [(30, 38), (40, 50), (38, 56), (70, 38), (60, 50), (62, 56), (50, 60)])
    return out + tr + dots


EBRAINS = [("Electronic brain (half)", g_ebrain_half), ("Brain + pins", g_ebrain_pins),
           ("Brain + core chip", g_ebrain_chip), ("Brain + traces", g_ebrain_traces)]

SLATE_BG, SLATE_BG2, SLATE_FG = "#334155", "#1e293b", "#f1f5f9"
WIRING = [
    ("teal", "#4ad4c4"), ("amber", "#d99a4c"), ("sky", "#7dd3fc"), ("royal blue", "#5b9bd8"),
    ("sage", "#7fb0a0"), ("lime", "#a3e635"), ("emerald", "#34d399"), ("cyan", "#22d3ee"),
    ("rose", "#fb7185"), ("orange", "#fb923c"), ("violet", "#b79be0"), ("magenta", "#e879f9"),
    ("gold", "#fbbf24"), ("mint", "#6ee7b7"), ("ice", "#bae6fd"), ("white", "#f1f5f9"),
    ("red", "#ef4444"), ("yellow", "#facc15"), ("aqua", "#5eead4"), ("coral", "#f97316"),
]
EXTRA = [
    ("Chip + brain", g_chip_brain), ("Brain on chip", g_brain_on_chip),
    ("Network in chip", g_chip_brain_net), ("Lightbulb + chip", g_lightbulb_chip),
    ("Lightbulb + net", g_lightbulb_net), ("Brain bulb", g_brain_bulb),
]

FOCUS = [(f"Chip+brain · {nm} wiring", g_chip_brain, ac) for nm, ac in WIRING]
for _gn, _gf in EXTRA:
    for _an, _ac in (("teal", "#4ad4c4"), ("amber", "#d99a4c")):
        FOCUS.append((f"{_gn} · {_an}", _gf, _ac))


def _svg_focus(entry, idx, size=104):
    _label, gfn, accent = entry
    pal = (SLATE_BG, SLATE_BG2, SLATE_FG, accent)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{size}" height="{size}">'
            f'{bg_markup("round", "solid", pal, 9000+idx)}{gfn(SLATE_FG, accent)}</svg>')


def build_focus_gallery():
    out_dir = HERE / "icon-previews"; out_dir.mkdir(exist_ok=True)
    cards = []
    for i, e in enumerate(FOCUS):
        cards.append(f'<div class="c">{_svg_focus(e, i, 104)}<div class="l"><b>{i+1}.</b> {e[0]}</div></div>')
    html = (
        "<!doctype html><meta charset=utf-8><title>Metis icon — option 88 variants</title>"
        "<style>body{background:#0f172a;color:#e2e8f0;font-family:Segoe UI,system-ui,sans-serif;"
        "margin:0;padding:26px}h1{font-size:20px;margin:0 0 2px}h2{font-size:15px;color:#cbd5e1;"
        "margin:24px 0 10px}p{color:#94a3b8;margin:4px 0 12px}.g{display:grid;"
        "grid-template-columns:repeat(5,1fr);gap:16px}.c{background:#1e293b;border:1px solid #334155;"
        "border-radius:14px;padding:12px;text-align:center}.c svg{width:104px;height:104px;"
        "border-radius:12px;box-shadow:0 3px 10px rgba(0,0,0,.35)}.l{margin-top:9px;font-size:12px;"
        "color:#cbd5e1}.l b{color:#fff}</style>"
        "<h1>Option 88 — chip+brain, wiring colours + more concepts</h1>"
        "<p>Same slate background. 1–20 = chip+brain with different wiring colours. "
        "21–32 = more chip / brain / lightbulb concepts. Pick: <b>“use focus N”</b>.</p>"
        f'<div class="g">{"".join(cards)}</div>')
    (out_dir / "option88.html").write_text(html, encoding="utf-8")
    return out_dir / "option88.html"


def build_focus_ico(n):
    e = FOCUS[n - 1]
    png = cairosvg.svg2png(bytestring=_svg_focus(e, n - 1, 256).encode(),
                           output_width=256, output_height=256)
    base = Image.open(io.BytesIO(png)).convert("RGBA")
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    written = []
    for t in INSTALL_TARGETS:
        t.parent.mkdir(parents=True, exist_ok=True)
        base.save(t, format="ICO", sizes=sizes)
        written.append(t)
    return e[0], written


# ── electronic-brain focused set (brain-first, option 88 integrated) ───────────
# entry = (label, glyph_fn, shape, fill, bg, bg2, fg, accent)
_EBG = {
    "slate":       ("round", "#334155", "#1e293b", "#f1f5f9"),
    "observatory": ("circle", "#15130f", "#241d12", "#f3ead6"),
    "forest":      ("squircle", "#2d4a3a", "#223b2e", "#f5f2ea"),
    "navy":        ("squircle", "#1e293b", "#0f172a", "#e2e8f0"),
    "paper":       ("squircle", "#f5f2ea", "#e8e2d2", "#2d4a3a"),
}


def _e(label, gfn, bgkey, accent):
    sh, bg, bg2, fg = _EBG[bgkey]
    return (label, gfn, sh, bg, bg2, fg, accent)


EFOCUS = [_e(f"Side electronic brain · {nm}", g_sbrain_elec, "slate", ac) for nm, ac in WIRING]
for _gn, _gf in (("Side brain (line)", g_sbrain), ("Side brain (filled)", g_sbrain_filled),
                 ("Top-down electronic", g_dbrain_elec)):
    for _an, _ac in (("teal", "#4ad4c4"), ("amber", "#d99a4c"), ("sky", "#7dd3fc"), ("sage", "#7fb0a0")):
        EFOCUS.append(_e(f"{_gn} · {_an}", _gf, "slate", _ac))
for _bk in ("observatory", "forest", "navy", "paper"):
    for _an, _ac in (("teal", "#4ad4c4"), ("amber", "#d99a4c")):
        EFOCUS.append(_e(f"Side electronic · {_bk} · {_an}", g_sbrain_elec, _bk,
                         "#2d4480" if _bk == "paper" else _ac))


def _svg_e(entry, idx, size=104):
    _label, gfn, sh, bg, bg2, fg, accent = entry
    pal = (bg, bg2, fg, accent)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{size}" height="{size}">'
            f'{bg_markup(sh, "solid", pal, 7000+idx)}{gfn(fg, accent)}</svg>')


def build_ebrain_gallery():
    out_dir = HERE / "icon-previews"; out_dir.mkdir(exist_ok=True)
    cards = [f'<div class="c">{_svg_e(e, i, 104)}<div class="l"><b>{i+1}.</b> {e[0]}</div></div>'
             for i, e in enumerate(EFOCUS)]
    html = (
        "<!doctype html><meta charset=utf-8><title>Metis — electronic brain</title>"
        "<style>body{background:#0f172a;color:#e2e8f0;font-family:Segoe UI,system-ui,sans-serif;"
        "margin:0;padding:26px}h1{font-size:20px;margin:0 0 2px}p{color:#94a3b8;margin:4px 0 14px}"
        ".g{display:grid;grid-template-columns:repeat(5,1fr);gap:16px}.c{background:#1e293b;"
        "border:1px solid #334155;border-radius:14px;padding:12px;text-align:center}.c svg{width:104px;"
        "height:104px;border-radius:12px;box-shadow:0 3px 10px rgba(0,0,0,.35)}.l{margin-top:9px;"
        "font-size:12px;color:#cbd5e1}.l b{color:#fff}</style>"
        "<h1>Electronic brain — brain-first, option 88 integrated</h1>"
        "<p>1–20: brain (organic left / circuit right) in 20 wiring colours. "
        "21–32: pins / core-chip / traces integrations. 33–40: background options. "
        "Pick: <b>“use ebrain N”</b>.</p>"
        f'<div class="g">{"".join(cards)}</div>')
    (out_dir / "electronic-brain.html").write_text(html, encoding="utf-8")
    return out_dir / "electronic-brain.html"


def build_ebrain_ico(n):
    e = EFOCUS[n - 1]
    png = cairosvg.svg2png(bytestring=_svg_e(e, n - 1, 256).encode(), output_width=256, output_height=256)
    base = Image.open(io.BytesIO(png)).convert("RGBA")
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    written = []
    for t in INSTALL_TARGETS:
        t.parent.mkdir(parents=True, exist_ok=True)
        base.save(t, format="ICO", sizes=sizes)
        written.append(t)
    return e[0], written


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gallery"
    if cmd == "gallery":
        print("Gallery written:", build_gallery())
    elif cmd == "ebrain":
        print("Electronic-brain gallery written:", build_ebrain_gallery())
    elif cmd == "builde":
        name, written = build_ebrain_ico(int(sys.argv[2]))
        print(f"Built '{name}' -> {len(written)} files")
        for w in written:
            print("  -", w)
    elif cmd == "focus":
        print("Focus gallery written:", build_focus_gallery())
    elif cmd == "buildf":
        name, written = build_focus_ico(int(sys.argv[2]))
        print(f"Built '{name}' -> {len(written)} files")
        for w in written:
            print("  -", w)
    elif cmd == "build":
        name, written = build_ico(int(sys.argv[2]))
        print(f"Built '{name}' -> {len(written)} files")
        for w in written:
            print("  -", w)
    else:
        print(__doc__)
