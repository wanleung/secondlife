#!/usr/bin/env python3
"""Draw the 1200x630 link-preview images (og.png) for each language edition.

Needs Pillow and the LXGW WenKai TC font (OFL, from Google Fonts):
  python3 tools/og_image.py /path/to/LXGWWenKaiTC-Bold.ttf /path/to/LXGWWenKaiTC-Regular.ttf
"""
import math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1200, 630
NIGHT, NIGHT2 = (17, 21, 28), (26, 33, 48)
GOLD, CINNABAR, JADE, GLOW, MIST, PAPER = (201, 162, 76), (181, 53, 43), (61, 138, 114), (233, 227, 210), (147, 160, 182), (233, 220, 182)

# out dir -> (title, accent char index, tagline, line 1, line 2)
EDITIONS = {
    '':   ('輪迴', 1, '德孽隨身，再世為人', '按全球真實出生統計投胎・218 個國家', '你前世積落嘅德同孽，會跟住你落下一世'),
    'zh': ('輪迴', 1, '德孽隨身，再世為人', '依全球真實出生統計投胎・218 個國家', '你前世累積的德與孽，會跟著你到下一世'),
    'ja': ('輪廻', 1, '徳も業も、来世へ', '実際の出生統計で転生・218の国と地域', '前世で積んだ徳と業が、来世までついてくる'),
    'en': ('Samsara', None, 'Your karma follows you into the next life', 'Reborn by real-world birth statistics · 218 countries', 'Free browser game · English · 中文 · 日本語'),
}

def wheel(d, cx, cy, r):
    """A dharma-wheel-like ring: two gold circles, eight spokes, red hub."""
    for rr, w in ((r, 6), (r - 26, 2)):
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=GOLD, width=w)
    for i in range(8):
        a = i * math.pi / 4
        d.line((cx + 40 * math.cos(a), cy + 40 * math.sin(a), cx + (r - 26) * math.cos(a), cy + (r - 26) * math.sin(a)), fill=GOLD, width=4)
    d.ellipse((cx - 40, cy - 40, cx + 40, cy + 40), outline=GOLD, width=4)
    d.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=CINNABAR)

def draw(out, title, accent, tag, l1, l2, bold, reg):
    im = Image.new('RGB', (W, H), NIGHT)
    d = ImageDraw.Draw(im)
    for y in range(H):  # soft vertical gradient
        t = y / H
        d.line((0, y, W, y), fill=tuple(round(NIGHT[i] + (NIGHT2[i] - NIGHT[i]) * t) for i in range(3)))
    d.rectangle((24, 24, W - 25, H - 25), outline=(60, 52, 36), width=2)
    wheel(d, 1000, 300, 165)

    x = 80
    size = 150 if accent is not None else 120
    ft = ImageFont.truetype(bold, size)
    if accent is None:
        d.text((x, 90), title, font=ft, fill=PAPER)
    else:
        cx = x
        for i, ch in enumerate(title):
            d.text((cx, 80), ch, font=ft, fill=CINNABAR if i == accent else PAPER)
            cx += ft.getlength(ch) + 20
    d.text((x, 270), tag, font=ImageFont.truetype(bold, 46 if accent is not None else 36), fill=GOLD)
    fs = ImageFont.truetype(reg, 30 if accent is not None else 27)
    d.text((x, 370), l1, font=fs, fill=GLOW)
    d.text((x, 420), l2, font=fs, fill=GLOW)
    d.line((x, 500, x + 60, 500), fill=JADE, width=4)
    d.text((x, 520), 'wanleung.net/secondlife' + (f'/{out}/' if out else '/'), font=ImageFont.truetype(reg, 28), fill=MIST)
    path = ROOT / out / 'og.png'
    im.save(path, optimize=True)
    print(path.relative_to(ROOT), path.stat().st_size // 1024, 'KB')

if __name__ == '__main__':
    bold, reg = sys.argv[1], sys.argv[2]
    for out, (title, accent, tag, l1, l2) in EDITIONS.items():
        draw(out, title, accent, tag, l1, l2, bold, reg)
