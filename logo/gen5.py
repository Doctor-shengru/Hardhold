import numpy as np
from PIL import Image, ImageDraw, ImageFilter

S = 2048
K = S / 1000.0
RED_TOP = np.array([224, 98, 70], np.float32)
RED_BOT = np.array([156, 40, 26], np.float32)
BG_FLAT = np.array([56, 60, 67], np.float32)   # 纯色高级灰

def sq_mask(size, inset=0.0, n=4.2):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    c = size / 2.0; r = c - inset
    u = np.abs((x - c) / r); v = np.abs((y - c) / r)
    return ((u ** n + v ** n) <= 1.0).astype(np.float32)

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
    sh = (598 * K, 268 * K)     # 肩：更靠内、更高，中间留大空隙
    el = (812 * K, 498 * K)     # 肘：更外，夹角约 90°
    wr = (800 * K, 700 * K)     # 腕
    limb(d, sh, el, 82 * K, 58 * K)
    limb(d, el, wr, 58 * K, 40 * K)
    d.ellipse([el[0]-60*K, el[1]-58*K, el[0]+60*K, el[1]+58*K], fill=255)
    d.ellipse([sh[0]-80*K, sh[1]-78*K, sh[0]+80*K, sh[1]+78*K], fill=255)

    # 二头肌隆起（沿上臂内侧）
    dx, dy = el[0]-sh[0], el[1]-sh[1]
    L = (dx*dx+dy*dy) ** 0.5
    nx, ny = -dy/L, dx/L
    a1 = (sh[0] + dx*0.18 + nx*12*K, sh[1] + dy*0.18 + ny*12*K)
    a2 = (sh[0] + dx*0.60 + nx*30*K, sh[1] + dy*0.60 + ny*30*K)
    limb(d, a1, a2, 74 * K, 54 * K)

    # 手掌压平贴地
    d.rounded_rectangle([wr[0]-78*K, wr[1]+18*K, wr[0]+78*K, wr[1]+92*K], radius=26*K, fill=255)
    d.rounded_rectangle([wr[0]-54*K, wr[1]-8*K, wr[0]+54*K, wr[1]+44*K], radius=20*K, fill=255)

    left = layer.transpose(Image.FLIP_LEFT_RIGHT)
    return Image.fromarray(np.maximum(np.array(layer), np.array(left)).astype(np.uint8))

def bevels(mask):
    m = np.array(mask).astype(np.float32) / 255.0
    hl = np.clip(m - np.roll(m, (4, 4), axis=(0, 1)), 0, 1)
    shv = np.clip(m - np.roll(m, (-6, -6), axis=(0, 1)), 0, 1)
    hl = np.array(Image.fromarray((hl*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S*0.008))).astype(np.float32)/255
    shv = np.array(Image.fromarray((shv*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S*0.010))).astype(np.float32)/255
    return hl, shv

def compose(glass_strength):
    bg = np.broadcast_to(BG_FLAT[None, None, :], (S, S, 3)).copy()

    if glass_strength > 0:
        # 只有一道很淡的镜面高光，不做整片渐变
        g = Image.new('L', (S, S), 0)
        gd = ImageDraw.Draw(g)
        gd.ellipse([S*-0.30, S*-0.55, S*0.62, S*0.18], fill=int(70*glass_strength))
        g = g.filter(ImageFilter.GaussianBlur(S*0.10))
        ga = np.array(g).astype(np.float32)[..., None]/255.0
        bg = bg * (1 - ga*0.55) + np.array([240,244,250], np.float32)[None,None,:] * (ga*0.55)

    # 边缘光：左上亮、右下暗（玻璃边缘）
    edge = sq_mask(S); inner = sq_mask(S, inset=S*0.008)
    rim = np.clip(edge - inner, 0, 1)[..., None]
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    w = np.clip(1.25 - (x/S*0.6 + y/S*0.8), 0, 1)[..., None]
    bg = bg*(1 - rim*w*0.9) + np.array([255,255,255], np.float32)[None,None,:]*(rim*w*0.9)
    bg = bg*(1 - rim*(1-w)*0.45)

    # 地面线
    floor = Image.new('L', (S, S), 0)
    fd = ImageDraw.Draw(floor)
    fy = 792 * K
    fd.rounded_rectangle([200*K, fy-11*K, 800*K, fy+11*K], radius=11*K, fill=125)
    floor = floor.filter(ImageFilter.GaussianBlur(S*0.003))
    fm = np.array(floor).astype(np.float32)[..., None]/255.0
    bg = bg*(1 - fm) + np.array([225,231,240], np.float32)[None,None,:]*fm

    arms = build_arms()
    # 投影压在地面上一点
    shd = arms.filter(ImageFilter.GaussianBlur(S*0.018))
    shi = Image.new('L', (S, S), 0); shi.paste(shd, (0, int(S*0.016)))
    sa = np.array(shi).astype(np.float32)[..., None]/255.0*0.50
    bg = bg*(1-sa)

    yy = np.linspace(0, 1, S, dtype=np.float32)[:, None, None]
    red = np.broadcast_to(RED_TOP[None,None,:]*(1-yy) + RED_BOT[None,None,:]*yy, (S,S,3))
    aa = np.array(arms).astype(np.float32)[..., None]/255.0
    bg = bg*(1-aa) + red*aa

    # 体积：左上提亮、右下压暗
    hl, sv = bevels(arms)
    bg = bg + aa*0 + (aa * hl[..., None]) * np.array([80, 34, 22], np.float32)[None,None,:]
    bg = bg * (1 - aa * sv[..., None] * 0.35)

    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS)
    mask = (sq_mask(1024, n=4.2)*255).astype(np.uint8)
    out = Image.new('RGBA', (1024, 1024), (0,0,0,0))
    out.paste(img, (0,0), Image.fromarray(mask))
    return out

for name, strength in (('flat', 0.0), ('glass', 1.0)):
    im = compose(strength)
    im.save('/root/workspace/apk/logo/arm_%s.png' % name)
    im.resize((96,96), Image.LANCZOS).save('/root/workspace/apk/logo/arm_%s_96.png' % name)
    print('saved', name)
