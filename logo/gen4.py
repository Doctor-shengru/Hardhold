import numpy as np
from PIL import Image, ImageDraw, ImageFilter

S = 2048
K = S / 1000.0
RED_TOP = np.array([222, 96, 68], np.float32)
RED_BOT = np.array([158, 42, 28], np.float32)

def sq_mask(size, inset=0.0, n=4.2):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    c = size / 2.0; r = c - inset
    u = np.abs((x - c) / r); v = np.abs((y - c) / r)
    return ((u ** n + v ** n) <= 1.0).astype(np.float32)

def radial(size, cx, cy, radius, power=2.0):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / radius
    return np.clip(1.0 - d, 0, 1) ** power

def background():
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    t = (x * 0.30 + y * 0.70) / S
    c1 = np.array([96, 102, 112], np.float32); c2 = np.array([28, 31, 37], np.float32)
    img = c1[None, None, :] * (1 - t[..., None]) + c2[None, None, :] * t[..., None]
    img += radial(S, S * 0.28, S * 0.08, S * 1.05, 2.4)[..., None] * np.array([124, 132, 150], np.float32) * 0.55
    img *= (0.80 + 0.30 * radial(S, S * 0.5, S * 0.35, S * 1.05, 1.5))[..., None]
    return np.clip(img, 0, 255)

def glass_alpha():
    layer = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(layer)
    d.polygon([(S * -0.10, S * 0.66), (S * 0.50, S * -0.10),
               (S * 0.66, S * -0.10), (S * 0.06, S * 0.80)], fill=150)
    d.polygon([(S * 0.00, S * 0.88), (S * 0.40, S * 0.00),
               (S * 0.47, S * 0.00), (S * 0.06, S * 0.94)], fill=70)
    d.polygon([(S * 0.30, S * 0.00), (S * 0.46, S * 0.00),
               (S * 0.20, S * 0.20), (S * 0.14, S * 0.20)], fill=90)
    layer = layer.filter(ImageFilter.GaussianBlur(S * 0.026))
    a = np.array(layer).astype(np.float32) / 255.0
    return np.clip(a + radial(S, S * 0.5, S * -0.06, S * 0.95, 1.7) * 0.13, 0, 1)

def limb(d, p0, p1, r0, r1, n=140):
    for i in range(n + 1):
        t = i / n
        x = p0[0] + (p1[0] - p0[0]) * t
        y = p0[1] + (p1[1] - p0[1]) * t
        r = r0 + (r1 - r0) * t
        d.ellipse([x - r, y - r, x + r, y + r], fill=255)

def build_arms():
    layer = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(layer)
    # 右臂：肩 → 肘 → 腕（下坠）→ 手掌压地
    sh  = (632 * K, 286 * K)
    el  = (818 * K, 512 * K)
    wr  = (806 * K, 716 * K)
    limb(d, sh, el, 80 * K, 60 * K)        # 上臂：肩粗肘细
    limb(d, el, wr, 60 * K, 42 * K)        # 前臂：肘粗腕细
    d.ellipse([el[0]-62*K, el[1]-60*K, el[0]+62*K, el[1]+60*K], fill=255)   # 肘关节
    d.ellipse([sh[0]-82*K, sh[1]-80*K, sh[0]+82*K, sh[1]+80*K], fill=255)   # 肩头

    # 二头肌：沿上臂内侧的隆起
    dx, dy = el[0]-sh[0], el[1]-sh[1]
    L = (dx*dx+dy*dy) ** 0.5
    nx, ny = -dy/L, dx/L            # 左法线（指向内侧）
    a1 = (sh[0] + dx*0.20 + nx*10*K, sh[1] + dy*0.20 + ny*10*K)
    a2 = (sh[0] + dx*0.62 + nx*26*K, sh[1] + dy*0.62 + ny*26*K)
    limb(d, a1, a2, 72 * K, 56 * K)

    # 手掌：压在地上，比腕宽、扁平
    d.rounded_rectangle([wr[0]-74*K, wr[1]+16*K, wr[0]+74*K, wr[1]+86*K], radius=30*K, fill=255)
    d.rounded_rectangle([wr[0]-52*K, wr[1]-6*K, wr[0]+52*K, wr[1]+40*K], radius=22*K, fill=255)

    left = layer.transpose(Image.FLIP_LEFT_RIGHT)
    m = np.maximum(np.array(layer), np.array(left)).astype(np.uint8)
    return Image.fromarray(m)

def compose():
    bg = background()
    a = glass_alpha()[..., None]
    bg = bg * (1 - a * 0.85) + np.array([240, 244, 250], np.float32)[None, None, :] * (a * 0.85)

    edge = sq_mask(S); inner = sq_mask(S, inset=S * 0.010)
    rim = np.clip(edge - inner, 0, 1)[..., None]
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    w = np.clip(1.25 - (x / S * 0.6 + y / S * 0.8), 0, 1)[..., None]
    bg = bg * (1 - rim * w * 0.95) + np.array([255,255,255], np.float32)[None, None, :] * (rim * w * 0.95)
    bg = bg * (1 - rim * (1 - w) * 0.65)

    # 地面
    floor = Image.new('L', (S, S), 0)
    fd = ImageDraw.Draw(floor)
    fy = 800 * K
    fd.rounded_rectangle([186*K, fy-9*K, 814*K, fy+9*K], radius=9*K, fill=110)
    floor = floor.filter(ImageFilter.GaussianBlur(S*0.003))
    fm = np.array(floor).astype(np.float32)[..., None] / 255.0
    bg = bg * (1 - fm) + np.array([232, 238, 246], np.float32)[None, None, :] * fm

    arms = build_arms()
    # 地面上的红色反光
    refl = Image.new('L', (S, S), 0)
    refl.paste(arms, (0, 0))
    refl = refl.crop((0, int(fy), S, int(fy + 150*K))).resize((S, int(150*K)), Image.LANCZOS)
    refl = Image.eval(refl, lambda v: int(v * 0.55)).filter(ImageFilter.GaussianBlur(S*0.02))
    canvas = Image.new('L', (S, S), 0)
    canvas.paste(refl, (0, int(fy + 8*K)))
    ra = np.array(canvas).astype(np.float32)[..., None] / 255.0 * 0.22
    bg = bg * (1 - ra) + np.array([200, 70, 50], np.float32)[None, None, :] * ra

    # 手臂投影
    sh = arms.filter(ImageFilter.GaussianBlur(S * 0.016))
    shi = Image.new('L', (S, S), 0)
    shi.paste(sh, (0, int(S * 0.014)))
    sa = np.array(shi).astype(np.float32)[..., None] / 255.0 * 0.45
    bg = bg * (1 - sa)

    yy = np.linspace(0, 1, S, dtype=np.float32)[:, None, None]
    red = np.broadcast_to(RED_TOP[None, None, :] * (1 - yy) + RED_BOT[None, None, :] * yy, (S, S, 3))
    glow = np.array(arms.filter(ImageFilter.GaussianBlur(S * 0.026))).astype(np.float32)[..., None] / 255.0 * 0.28
    bg = bg * (1 - glow) + red * glow
    aa = np.array(arms).astype(np.float32)[..., None] / 255.0
    bg = bg * (1 - aa) + red * aa

    hl = Image.new('L', (S, S), 0)
    hl.paste(arms.filter(ImageFilter.GaussianBlur(S * 0.006)), (0, int(-S * 0.008)))
    ha = np.array(hl).astype(np.float32)[..., None] / 255.0
    bg = bg + ha * np.array([86, 36, 20], np.float32)[None, None, :]

    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS)
    mask = (sq_mask(1024, n=4.2) * 255).astype(np.uint8)
    out = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
    out.paste(img, (0, 0), Image.fromarray(mask))
    return out

im = compose()
im.save('/root/workspace/apk/logo/arm_v3.png')
im.resize((48, 48), Image.LANCZOS).save('/root/workspace/apk/logo/arm_v3_48.png')
im.resize((96, 96), Image.LANCZOS).save('/root/workspace/apk/logo/arm_v3_96.png')
print('saved v3')
