import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

S = 2048
RED_TOP = (207, 74, 53)
RED_BOT = (162, 44, 30)

def radial(size, cx, cy, radius, power=2.0):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / radius
    return np.clip(1.0 - d, 0, 1) ** power

def base_bg(size):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    t = (x + y) / (2.0 * size)
    c1 = np.array([64, 69, 78], np.float32)
    c2 = np.array([17, 19, 23], np.float32)
    img = c1[None, None, :] * (1 - t[..., None]) + c2[None, None, :] * t[..., None]
    glow = radial(size, size * 0.22, size * 0.16, size * 0.85, 2.4)
    img += glow[..., None] * np.array([120, 128, 142], np.float32) * 0.30
    v = radial(size, size / 2, size / 2, size * 0.80, 1.5)
    img *= (0.55 + 0.5 * v[..., None])
    return img

def glass_layer(size):
    """斜向玻璃反光带 + 顶部高光"""
    layer = Image.new('L', (size, size), 0)
    d = ImageDraw.Draw(layer)
    d.polygon([(size * 0.02, size * 0.58), (size * 0.55, size * -0.05),
               (size * 0.78, size * -0.05), (size * 0.25, size * 0.78)], fill=42)
    d.polygon([(size * 0.05, size * 0.72), (size * 0.42, size * 0.08),
               (size * 0.48, size * 0.08), (size * 0.11, size * 0.74)], fill=26)
    layer = layer.filter(ImageFilter.GaussianBlur(size * 0.045))
    m = np.array(layer).astype(np.float32)[..., None] / 255.0
    return m

def mark_mask(kind, size):
    layer = Image.new('L', (size, size), 0)
    d = ImageDraw.Draw(layer)
    w = int(0.070 * size)
    def cap(p):
        d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill=255)
    def line(p1, p2):
        d.line([p1, p2], fill=255, width=w, joint='curve')
        cap(p1); cap(p2)
    if kind == 'chevron':
        line((0.29 * size, 0.575 * size), (0.50 * size, 0.335 * size))
        line((0.50 * size, 0.335 * size), (0.71 * size, 0.575 * size))
        line((0.345 * size, 0.715 * size), (0.655 * size, 0.715 * size))
    elif kind == 'ring':
        box = [0.255 * size, 0.255 * size, 0.745 * size, 0.745 * size]
        d.arc(box, 300, 360, fill=255, width=w)
        d.arc(box, 0, 240, fill=255, width=w)
        line((0.50 * size, 0.665 * size), (0.50 * size, 0.415 * size))
        line((0.415 * size, 0.485 * size), (0.50 * size, 0.415 * size))
        line((0.585 * size, 0.485 * size), (0.50 * size, 0.415 * size))
    elif kind == 'stack':
        bars = [(0.335, 0.215), (0.505, 0.290), (0.675, 0.365)]
        for cy, half in bars:
            y = cy * size
            h = 0.075 * size
            d.rounded_rectangle([(0.5 - half) * size, y - h / 2,
                                 (0.5 + half) * size, y + h / 2],
                                radius=h / 2, fill=255)
    else:
        raise SystemExit('unknown kind')
    return layer

def compose(kind):
    bg = base_bg(S)
    glass = glass_layer(S)
    bg = bg * (1 - glass) + np.array([225, 232, 245], np.float32)[None, None, :] * glass

    mask = mark_mask(kind, S)

    # 红色纵向渐变填充
    y = np.linspace(0, 1, S, dtype=np.float32)[:, None, None]
    red = np.array(RED_TOP, np.float32)[None, None, :] * (1 - y) + \
          np.array(RED_BOT, np.float32)[None, None, :] * y

    # 外发光
    glow = mask.filter(ImageFilter.GaussianBlur(S * 0.030))
    ga = np.array(glow).astype(np.float32)[..., None] / 255.0 * 0.42
    red_full = np.broadcast_to(red, (S, S, 3))
    bg = bg * (1 - ga) + red_full * ga

    # 主体
    ma = np.array(mask).astype(np.float32)[..., None] / 255.0
    img = bg * (1 - ma) + red_full * ma

    # 主体内侧顶部高光（让"玻璃上的红色"更有层次）
    hi = mask.filter(ImageFilter.GaussianBlur(S * 0.012))
    ha = np.array(hi).astype(np.float32)[..., None] / 255.0
    img = img + ha * np.array([40, 14, 8], np.float32)[None, None, :]

    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return out.resize((512, 512), Image.LANCZOS)

for kind in ('chevron', 'ring', 'stack'):
    im = compose(kind)
    im.save('/root/workspace/apk/logo/v_%s.png' % kind)
    im.resize((96, 96), Image.LANCZOS).save('/root/workspace/apk/logo/small_%s.png' % kind)
    print('ok', kind)
