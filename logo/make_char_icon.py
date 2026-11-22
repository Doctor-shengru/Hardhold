#!/usr/bin/env python3
"""生成「硬撑」图标：枫叶红玻璃底 + 白色「撑」字标。
用法：python3 logo/make_char_icon.py   （直接写入 app/src/main/res）
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np, os

RED = np.array([198, 65, 47], np.float32)   # 枫叶红 #C6412F
WHITE = (255, 255, 255, 255)
FONT = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
CHAR = '撑'
WEIGHT = 9          # 字重：膨胀核大小
GLYPH_RATIO = 0.50  # 字在图标中的占比
RADIUS = 0.22
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 1024

def glyph():
    f = ImageFont.truetype(FONT, int(S * 0.62), index=0)
    im = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(im)
    bb = d.textbbox((0, 0), CHAR, font=f)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((S - w) / 2 - bb[0], (S - h) / 2 - bb[1]), CHAR, font=f, fill=255)
    im = im.filter(ImageFilter.MaxFilter(WEIGHT))
    return im.crop(im.getbbox())

GLYPH = glyph()

def rounded_alpha(size, r=RADIUS):
    m = Image.new('L', (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * r), fill=255)
    return np.array(m).astype(np.float32) / 255

def glass_tile(size):
    """轻玻璃：左上柔光 + 边缘受光/内阴影，字保持纯白"""
    rgb = np.broadcast_to(RED[None, None, :], (size, size, 3)).copy()
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    # 左上柔光
    g = np.clip(1 - (x * 0.55 + y * 0.95) / size, 0, 1) ** 2
    rgb = rgb * (1 - g[..., None] * 0.10) + 255 * (g[..., None] * 0.10)
    # 边缘：左上亮、右下暗
    rim = np.clip(rounded_alpha(size) - rounded_alpha(size, RADIUS * 0.965), 0, 1)[..., None]
    w = np.clip(1.3 - (x / size * 0.7 + y / size * 0.8), 0, 1)[..., None]
    rgb = rgb * (1 - rim * w * 0.35) + 255 * (rim * w * 0.35)
    rgb = rgb * (1 - rim * (1 - w) * 0.20)
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert('RGBA')
    gw = int(size * GLYPH_RATIO)
    gh = int(gw * GLYPH.size[1] / GLYPH.size[0])
    gimg = GLYPH.resize((gw, gh), Image.LANCZOS)
    layer = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    layer.paste(Image.new('RGBA', (gw, gh), WHITE), ((size - gw) // 2, (size - gh) // 2), gimg)
    img.alpha_composite(layer)
    return img

def foreground(size):
    gw = int(size * GLYPH_RATIO)
    gh = int(gw * GLYPH.size[1] / GLYPH.size[0])
    g = GLYPH.resize((gw, gh), Image.LANCZOS)
    c = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    c.paste(Image.new('RGBA', (gw, gh), WHITE), ((size - gw) // 2, (size - gh) // 2), g)
    return c

def background(size):
    """自适应图标背景层：满幅玻璃底"""
    rgb = np.broadcast_to(RED[None, None, :], (size, size, 3)).copy()
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    g = np.clip(1 - (x * 0.55 + y * 0.95) / size, 0, 1) ** 2
    rgb = rgb * (1 - g[..., None] * 0.10) + 255 * (g[..., None] * 0.10)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert('RGBA')

DENS = {'mdpi': 1, 'hdpi': 1.5, 'xhdpi': 2, 'xxhdpi': 3, 'xxxhdpi': 4}
for name, scale in DENS.items():
    d = os.path.join(ROOT, 'app/src/main/res/mipmap-%s' % name)
    os.makedirs(d, exist_ok=True)
    sz = int(48 * scale)
    icon = glass_tile(sz)
    mask = Image.fromarray((rounded_alpha(sz) * 255).astype(np.uint8))
    out = Image.new('RGBA', (sz, sz), (0, 0, 0, 0)); out.paste(icon, (0, 0), mask)
    out.convert('RGB').save(os.path.join(d, 'ic_launcher.png'))
    circ = Image.new('L', (sz, sz), 0)
    ImageDraw.Draw(circ).ellipse([0, 0, sz - 1, sz - 1], fill=255)
    rnd = Image.new('RGBA', (sz, sz), (0, 0, 0, 0)); rnd.paste(icon, (0, 0), circ)
    rnd.save(os.path.join(d, 'ic_launcher_round.png'))
    foreground(int(108 * scale)).save(os.path.join(d, 'ic_launcher_foreground.png'))
    background(int(108 * scale)).save(os.path.join(d, 'ic_launcher_background.png'))

open(os.path.join(ROOT, 'app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml'), 'w').write(
'''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@mipmap/ic_launcher_background" />
    <foreground android:drawable="@mipmap/ic_launcher_foreground" />
</adaptive-icon>
''')
open(os.path.join(ROOT, 'app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml'), 'w').write(
'''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@mipmap/ic_launcher_background" />
    <foreground android:drawable="@mipmap/ic_launcher_foreground" />
</adaptive-icon>
''')
print('icons exported')
