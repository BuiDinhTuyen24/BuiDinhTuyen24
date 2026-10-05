"""
Turn a profile photo into an animated pixel-art SVG that runs on GitHub.

Pixels rain in top to bottom, then a soft scanline sweeps over the picture
forever. CSS animations only (GitHub renders SVGs in <img>, no JS).
Panel height matches wordmark.svg so the two sit side by side in the README.

    python scripts/make_pixel_avatar_svg.py [photo] [out.svg]
"""
import os
import random
import sys

from PIL import Image, ImageEnhance, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "avatar-source.jpg")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "pixel-avatar.svg")

GRID = int(os.environ.get("PIXEL_GRID", 44))
CELL = 7
GAP = 1
COLORS = int(os.environ.get("PIXEL_COLORS", 28))
PANEL_H = int(os.environ.get("PIXEL_PANEL_H", 356))   # = wordmark.svg height
PAD_X = 18
TITLEBAR_H = 28
BUCKETS = 24
STEP = 0.1          # seconds between buckets
SCAN_DUR = 4.5

BG, BG2, FRAME, TITLE_TEXT = "#0d1117", "#111722", "#30363d", "#7d8590"

img = ImageOps.exif_transpose(Image.open(SRC)).convert("RGB")
# optional square crop "left,top,size" in source pixels, to zoom in on the face
crop = os.environ.get("PIXEL_CROP")
if crop:
    l, t, sz = (int(v) for v in crop.split(","))
    img = img.crop((l, t, l + sz, t + sz))
side = min(img.size)
img = ImageOps.fit(img, (side, side), centering=(0.5, 0.4))
img = ImageEnhance.Contrast(img).enhance(1.35)
img = ImageEnhance.Color(img).enhance(1.4)
img = ImageEnhance.Brightness(img).enhance(1.12)
small = img.resize((GRID, GRID), Image.LANCZOS)
pal_img = small.quantize(colors=COLORS, method=Image.MEDIANCUT)
palette = pal_img.getpalette()[: COLORS * 3]
hexes = ["#%02x%02x%02x" % tuple(palette[i * 3:i * 3 + 3]) for i in range(COLORS)]
px_at = pal_img.load()
idx = [px_at[x, y] for y in range(GRID) for x in range(GRID)]

art = GRID * CELL
W = art + PAD_X * 2
H = PANEL_H
top = TITLEBAR_H + (H - TITLEBAR_H - art) / 2

rng = random.Random(24)
css = [
    "@keyframes pin{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:none}}",
    "@keyframes scan{0%%{transform:translateY(-60px)}100%%{transform:translateY(%dpx)}}" % (art + 60),
    "@keyframes blink{50%{opacity:0}}",
    "rect.p{opacity:0;animation:pin .45s ease-out both}",
    ".s{animation:scan %.1fs linear %.1fs infinite}" % (SCAN_DUR, BUCKETS * STEP + 0.6),
    ".k{animation:blink 1s step-end infinite}",
]
css += [".c%d{fill:%s}" % (i, h) for i, h in enumerate(hexes)]
css += [".d%d{animation-delay:%.2fs}" % (b, b * STEP) for b in range(BUCKETS)]

rows_per_bucket = GRID / (BUCKETS - 4)
rects = []
for y in range(GRID):
    for x in range(GRID):
        b = min(BUCKETS - 1, int(y / rows_per_bucket) + rng.randint(0, 3))
        px = PAD_X + x * CELL
        py = top + y * CELL
        rects.append(f'<rect class="p c{idx[y*GRID+x]} d{b}" x="{px}" y="{py:.0f}" '
                     f'width="{CELL-GAP}" height="{CELL-GAP}"/>')

svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
    "<style>" + "".join(css) + "</style>",
    '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient>'
    '<linearGradient id="sl" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#9fffb0" stop-opacity="0"/>'
    '<stop offset=".5" stop-color="#9fffb0" stop-opacity=".22"/>'
    '<stop offset="1" stop-color="#9fffb0" stop-opacity="0"/></linearGradient>'
    f'<clipPath id="art"><rect x="{PAD_X}" y="{top:.0f}" width="{art}" height="{art}"/></clipPath></defs>',
    f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>',
    f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="{FRAME}"/>',
    f'<line x1="0" y1="{TITLEBAR_H}" x2="{W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
]
for i, dot in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    svg.append(f'<circle cx="{PAD_X + i*15}" cy="{TITLEBAR_H/2}" r="4.5" fill="{dot}"/>')
svg.append(f'<text x="{(W + PAD_X + 30)/2:.0f}" y="{TITLEBAR_H/2 + 4:.0f}" fill="{TITLE_TEXT}" font-size="11.5" '
           'text-anchor="middle">bdt@github: ~$ ./avatar.sh<tspan class="k">_</tspan></text>')
svg.append("<g>" + "".join(rects) + "</g>")
svg.append(f'<g clip-path="url(#art)"><rect class="s" x="{PAD_X}" y="{top:.0f}" width="{art}" '
           'height="60" fill="url(#sl)"/></g>')
svg.append("</svg>")

with open(OUT, "w") as f:
    f.write("\n".join(svg))
print(f"wrote {OUT}  {os.path.getsize(OUT)/1024:.1f} KB  {GRID}x{GRID} px  {W}x{H}")
