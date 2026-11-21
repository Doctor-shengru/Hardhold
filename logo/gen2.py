import numpy as np
from PIL import Image, ImageDraw, ImageFilter

S = 2048
RED_TOP = np.array([214, 88, 62], np.float32)
RED_BOT = np.array([158, 42, 28], np.float32)

def radial(size, cx, cy, radius, power=2.0):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / radius
    return np.clip(1.0 - d, 0, 1) ** power

def squircle(size, inset=0, n=4.2):
    """超椭圆（iOS 图标形状）mask"""
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    c = size / 2.0
    r = c - inset
    u = np.abs((x - c) / r)
    v = np.abs((y - c) / r)
    m = (u ** n + v ** n) <= 1.0
    return Image.fromarray((m * 255).astype(np.uint8))

def background(size):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    t = (x * 0.35 + y * 0.65) / size
    c1 = np.array([74, 79, 88], np.float32)
    c2 = np.array([20, 22, 26], np.float32)
    img = c1[None, None, :] * (1 - t[..., None]) + c2[None, None, :] * t[..., None]
    img += radial(size, size * 0.30, size * 0.14, size * 0.95, 2.6)[..., None] * np.array([96, 104, 120], np.float32) * 0.42
    img *= (0.62 + 0.42 * radial(size, size * 0.5, size * 0.42, size * 0.95, 1.4))[..., None]
    return img

def glass(size, mask):
    """玻璃反光：两道斜向高光 + 顶部柔光"""
    m = np.zeros((size, size), np.float32)
    layer = Image.new('L', (size, size), 0)
    d = ImageDraw.Draw(layer)
    d.polygon([(size * -0.05, size * 0.62), (size * 0.52, size * -0.08),
               (size * 0.70, size * -0.08), (size * 0.13, size * 0.78)], fill=64)
    d.polygon([(size * 0.02, size * 0.86), (size * 0.46, size * 0.02),
               (size * 0.53, size * 0.02), (size * 0.09, size * 0.90)], fill=34)
    layer = layer.filter(ImageFilter.GaussianBlur(size * 0.035))
    top = radial(size, size * 0.5, size * -0.10, size * 0.9, 1.8) * 0.10
    a = np.array(layer).astype(np.float32) / 255.0 + top
    return np.clip(a, 0, 1)[..., None] * np.array([236, 241, 250], np.float32)[None, None, :]

def limb(d, p0, p1, r0, r1, n=90):
    for i in range(n + 1):
        t = i / n
        x = p0[0] + (p1[0] - p0[0]) * t
        y = p0[1] + (p1[1] - p0[1]) * t
        r = r0 + (r1 - r0) * t
        d.ellipse([x - r, y - r, x + r, y + r], fill=255)

def arm_mask(size):
    """一对 90° 弯曲、撑在地面的肌肉手臂"""
    layer = Image.new('L', (size, size), 0)
    d = ImageDraw.Draw(layer)
    k = size / 1000.0
    # 右臂（左臂镜像）：肩 -> 肘 -> 手
    shoulder = (612 * k, 268 * k)
    elbow    = (800 * k, 486 * k)
    hand     = (772 * k, 742 * k)
    limb(d, shoulder, elbow, 74 * k, 62 * k)          # 上臂
    limb(d, elbow, hand, 58 * k, 46 * k)              # 前臂
    # 二头肌隆起
    bx, by = (shoulder[0] + elbow[0]) / 2 - 18 * k, (shoulder[1] + elbow[1]) / 2 - 6 * k
    d.ellipse([bx - 86 * k, by - 80 * k, bx + 86 * k, by + 80 * k], fill=255)
    # 拳头 / 手掌压地
    d.rounded_rectangle([hand[0] - 62 * k, hand[1] - 48 * k,
                         hand[0] + 62 * k, hand[1] + 52 * k], radius=34 * k, fill=255)
    # 肩部圆润
    d.ellipse([shoulder[0] - 80 * k, shoulder[1] - 74 * k,
               shoulder[0] + 80 * k, shoulder[1] + 74 * k], fill=255)
    left = layer.transpose(Image.FLIP_LEFT_RIGHT)
    return Image.fromarray(np.maximum(np.array(layer), np.array(left)).astype(np.uint8))

def compose():
    bg = background(S)
    mask = squircle(S)
    body = bg * (1 - 1.0)  # placeholder
    # 玻璃
    g = glass(S, mask)
    bg = bg * (1 - g) + g * 0.55 + bg * g * 0.45
    # 边缘光（左上亮、右下暗）
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    edge = np.array(mask).astype(np.float32) / 255.0
    inner = np.array(squircle(S, inset=S * 0.006)).astype(np.float32) / 255.0
    rim = np.clip(edge - inner, 0, 1)
    w = np.clip(1.15 - (x / S * 0.55 + y / S * 0.75), 0, 1)
    rim_rgb = np.array([255, 255, 255], np.float32)
    bg = bg * (1 - rim[..., None] * w[..., None] * 0.85) + \
         rim_rgb[None, None, :] * (rim[..., None] * w[..., None] * 0.85)
    bg = bg * (1 - rim[..., None] * (1 - w)[..., None] * 0.55)  # 右下压暗

    # 手臂
    arms = arm_mask(S)
    shade = arms.filter(ImageFilter.GaussianBlur(S * 0.012))
    off = Image.new('L', (S, S), 0)
    off.paste(shade, (0, int(S * 0.012)))
    sa = np.array(off).astype(np.float32)[..., None] / 255.0 * 0.55
    bg = bg * (1 - sa)

    yy = np.linspace(0, 1, S, dtype=np.float32)[:, None, None]
    red = RED_TOP[None, None, :] * (1 - yy) + RED_BOT[None, None, :] * yy
    red = np.broadcast_to(red, (S, S, 3))
    glow = arms.filter(ImageFilter.GaussianBlur(S * 0.022))
    ga = np.array(glow).astype(np.float32)[..., None] / 255.0 * 0.35
    bg = bg * (1 - ga) + red * ga
    aa = np.array(arms).astype(np.float32)[..., None] / 255.0
    bg = bg * (1 - aa) + red * aa

    # 手臂顶部高光
    hl = Image.new('L', (S, S), 0)
    hl.paste(arms.filter(ImageFilter.GaussianBlur(S * 0.008)), (0, int(-S * 0.006)))
    ha = np.array(hl).astype(np.float32)[..., None] / 255.0
    bg = bg + ha * np.array([70, 26, 14], np.float32)[None, None, :]

    # 地面线
    ground = Image.new('L', (S, S), 0)
    gd = ImageDraw.Draw(ground)
    gy = int(S * 0.795)
    gd.rounded_rectangle([S * 0.175, gy - S * 0.007, S * 0.825, gy + S * 0.007],
                         radius=S * 0.007, fill=90)
    ground = ground.filter(ImageFilter.GaussianBlur(S * 0.002))
    gm = np.array(ground).astype(np.float32)[..., None] / 255.0
    bg = bg * (1 - gm) + np.array([226, 232, 240], np.float32)[None, None, :] * gm

    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
    img = img.resize((1024, 1024), Image.LANCZOS)
    # 圆角裁切（预览用；正式图标按平台分别导出）
    out = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
    out.paste(img, (0, 0), squircle(1024, n=4.2).point(lambda v: v))
    return out

im = compose()
im.save('/root/workspace/apk/logo/arm_v1.png')
im.resize((256, 256), Image.LANCZOS).save('/root/workspace/apk/logo/arm_v1_256.png')
print('saved')
