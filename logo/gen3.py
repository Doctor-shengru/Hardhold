import numpy as np
from PIL import Image, ImageDraw, ImageFilter

S = 2048
RED_TOP = np.array([218, 92, 66], np.float32)
RED_BOT = np.array([160, 44, 30], np.float32)

def sq_mask(size, inset=0.0, n=4.2):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    c = size / 2.0
    r = c - inset
    u = np.abs((x - c) / r); v = np.abs((y - c) / r)
    return ((u ** n + v ** n) <= 1.0).astype(np.float32)

def radial(size, cx, cy, radius, power=2.0):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / radius
    return np.clip(1.0 - d, 0, 1) ** power

def background():
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    t = (x * 0.30 + y * 0.70) / S
    c1 = np.array([92, 98, 108], np.float32)
    c2 = np.array([30, 33, 39], np.float32)
    img = c1[None, None, :] * (1 - t[..., None]) + c2[None, None, :] * t[..., None]
    img += radial(S, S * 0.28, S * 0.10, S * 1.05, 2.4)[..., None] * np.array([120, 128, 145], np.float32) * 0.55
    img *= (0.80 + 0.30 * radial(S, S * 0.5, S * 0.35, S * 1.05, 1.5))[..., None]
    return np.clip(img, 0, 255)

def glass_alpha():
    layer = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(layer)
    d.polygon([(S * -0.10, S * 0.66), (S * 0.50, S * -0.10),
               (S * 0.66, S * -0.10), (S * 0.06, S * 0.80)], fill=150)
    d.polygon([(S * 0.00, S * 0.88), (S * 0.40, S * 0.00),
               (S * 0.47, S * 0.00), (S * 0.06, S * 0.94)], fill=70)
    layer = layer.filter(ImageFilter.GaussianBlur(S * 0.030))
    a = np.array(layer).astype(np.float32) / 255.0
    return np.clip(a + radial(S, S * 0.5, S * -0.06, S * 0.95, 1.7) * 0.13, 0, 1)

def limb(d, p0, p1, r0, r1, n=110):
    for i in range(n + 1):
        t = i / n
        x = p0[0] + (p1[0] - p0[0]) * t
        y = p0[1] + (p1[1] - p0[1]) * t
        r = r0 + (r1 - r0) * t
        d.ellipse([x - r, y - r, x + r, y + r], fill=255)

def arms_mask():
    layer = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(layer)
    k = S / 1000.0
    shoulder = (640 * k, 300 * k)     # 肩在中间偏上
    elbow    = (806 * k, 520 * k)     # 肘向外下，夹角≈90°
    hand     = (800 * k, 742 * k)     # 前臂竖直压地
    limb(d, shoulder, elbow, 76 * k, 60 * k)
    limb(d, elbow, hand, 58 * k, 50 * k)
    # 二头肌
    mid = ((shoulder[0] + elbow[0]) / 2 - 14 * k, (shoulder[1] + elbow[1]) / 2 - 10 * k)
    d.ellipse([mid[0] - 84 * k, mid[1] - 78 * k, mid[0] + 84 * k, mid[1] + 78 * k], fill=255)
    # 掌心压地
    d.rounded_rectangle([hand[0] - 66 * k, hand[1] - 34 * k,
                         hand[0] + 66 * k, hand[1] + 52 * k], radius=30 * k, fill=255)
    # 肩头
    d.ellipse([shoulder[0] - 78 * k, shoulder[1] - 76 * k,
               shoulder[0] + 78 * k, shoulder[1] + 76 * k], fill=255)
    left = layer.transpose(Image.FLIP_LEFT_RIGHT)
    m = np.maximum(np.array(layer), np.array(left)).astype(np.uint8)
    return Image.fromarray(m)

def compose():
    bg = background()
    a = glass_alpha()[..., None]
    bg = bg * (1 - a * 0.85) + np.array([240, 244, 250], np.float32)[None, None, :] * (a * 0.85)

    # 圆角/超椭圆边缘光
    edge = sq_mask(S)
    inner = sq_mask(S, inset=S * 0.010)
    rim = np.clip(edge - inner, 0, 1)[..., None]
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    w = np.clip(1.25 - (x / S * 0.6 + y / S * 0.8), 0, 1)[..., None]
    bg = bg * (1 - rim * w * 0.95) + np.array([255, 255, 255], np.float32)[None, None, :] * (rim * w * 0.95)
    bg = bg * (1 - rim * (1 - w) * 0.65)

    arms = arms_mask()
    # 投影
    sh = arms.filter(ImageFilter.GaussianBlur(S * 0.016))
    sh_img = Image.new('L', (S, S), 0)
    sh_img.paste(sh, (0, int(S * 0.016)))
    sa = np.array(sh_img).astype(np.float32)[..., None] / 255.0 * 0.50
    bg = bg * (1 - sa)

    yy = np.linspace(0, 1, S, dtype=np.float32)[:, None, None]
    red = np.broadcast_to(RED_TOP[None, None, :] * (1 - yy) + RED_BOT[None, None, :] * yy, (S, S, 3))
    glow = np.array(arms.filter(ImageFilter.GaussianBlur(S * 0.026))).astype(np.float32)[..., None] / 255.0 * 0.30
    bg = bg * (1 - glow) + red * glow
    aa = np.array(arms).astype(np.float32)[..., None] / 255.0
    bg = bg * (1 - aa) + red * aa

    # 顶部高光（玻璃上的凸起效果）
    hl = Image.new('L', (S, S), 0)
    hl.paste(arms.filter(ImageFilter.GaussianBlur(S * 0.006)), (0, int(-S * 0.008)))
    ha = np.array(hl).astype(np.float32)[..., None] / 255.0
    bg = bg + ha * np.array([84, 34, 18], np.float32)[None, None, :]

    # 地面线
    gl = Image.new('L', (S, S), 0)
    gd = ImageDraw.Draw(gl)
    gy = S * 0.760
    gd.rounded_rectangle([S * 0.215, gy - S * 0.006, S * 0.785, gy + S * 0.006], radius=S * 0.006, fill=120)
    gl = gl.filter(ImageFilter.GaussianBlur(S * 0.0035))
    gm = np.array(gl).astype(np.float32)[..., None] / 255.0
    bg = bg * (1 - gm) + np.array([235, 240, 248], np.float32)[None, None, :] * gm

    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
    return img.resize((1024, 1024), Image.LANCZOS)

# 用超椭圆裁切，导出圆角预览
im = compose()
mask = (sq_mask(1024, n=4.2) * 255).astype(np.uint8)
out = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
out.paste(im, (0, 0), Image.fromarray(mask))
out.save('/root/workspace/apk/logo/arm_v2.png')
out.resize((256, 256), Image.LANCZOS).save('/root/workspace/apk/logo/arm_v2_256.png')
print('saved v2')
