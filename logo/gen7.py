import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
S = 2048; K = S/1000.0
RED_TOP = np.array([230, 104, 74], np.float32)
RED_BOT = np.array([152, 36, 22], np.float32)
BG = np.array([56, 60, 67], np.float32)

def sq_mask(size, inset=0.0, n=4.2):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    c = size/2.0; r = c - inset
    u = np.abs((x-c)/r); v = np.abs((y-c)/r)
    return ((u**n + v**n) <= 1.0).astype(np.float32)

def limb(d, p0, p1, r0, r1, n=160):
    for i in range(n+1):
        t = i/n
        x = p0[0]+(p1[0]-p0[0])*t; y = p0[1]+(p1[1]-p0[1])*t
        r = r0+(r1-r0)*t
        d.ellipse([x-r,y-r,x+r,y+r], fill=255)

def build_arms():
    layer = Image.new('L', (S,S), 0)
    d = ImageDraw.Draw(layer)
    sh = (566*K, 232*K)     # 肩更高更内
    el = (812*K, 498*K)     # 肘更外
    wr = (752*K, 742*K)     # 腕向内下方收，弯得更"往下"
    limb(d, sh, el, 82*K, 58*K)
    limb(d, el, wr, 58*K, 42*K)
    d.ellipse([sh[0]-78*K, sh[1]-78*K, sh[0]+78*K, sh[1]+78*K], fill=255)
    d.ellipse([el[0]-60*K, el[1]-60*K, el[0]+60*K, el[1]+60*K], fill=255)

    dx, dy = el[0]-sh[0], el[1]-sh[1]
    L = (dx*dx+dy*dy)**0.5
    nx, ny = -dy/L, dx/L
    a1 = (sh[0]+dx*0.16+nx*12*K, sh[1]+dy*0.16+ny*12*K)
    a2 = (sh[0]+dx*0.60+nx*30*K, sh[1]+dy*0.60+ny*30*K)
    limb(d, a1, a2, 76*K, 56*K)     # 二头肌

    # 拳头：不要横杠，靠自身圆润立住
    ang = math.degrees(math.atan2(wr[1]-el[1], wr[0]-el[0])) + 90
    fist = Image.new('L', (S,S), 0)
    fd = ImageDraw.Draw(fist)
    fd.rounded_rectangle([wr[0]-66*K, wr[1]-52*K, wr[0]+66*K, wr[1]+62*K], radius=30*K, fill=255)
    fist = fist.rotate(ang*0 , center=(wr[0], wr[1]))
    layer = Image.fromarray(np.maximum(np.array(layer), np.array(fist)).astype(np.uint8))

    left = layer.transpose(Image.FLIP_LEFT_RIGHT)
    return Image.fromarray(np.maximum(np.array(layer), np.array(left)).astype(np.uint8))

def bevels(mask):
    m = np.array(mask).astype(np.float32)/255.0
    hl = np.clip(m - np.roll(m,(5,5),axis=(0,1)),0,1)
    sv = np.clip(m - np.roll(m,(-7,-7),axis=(0,1)),0,1)
    hl = np.array(Image.fromarray((hl*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S*0.008))).astype(np.float32)/255
    sv = np.array(Image.fromarray((sv*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S*0.010))).astype(np.float32)/255
    return hl, sv

def ticks():
    """很淡的刻度环，呼应参考图的仪表感"""
    layer = Image.new('L', (S,S), 0)
    d = ImageDraw.Draw(layer)
    c = S/2.0; r_out = 0.415*S; r_in = 0.390*S
    for i in range(60):
        a = math.radians(i*6)
        x0, y0 = c+r_in*math.cos(a), c+r_in*math.sin(a)
        x1, y1 = c+r_out*math.cos(a), c+r_out*math.sin(a)
        d.line([x0,y0,x1,y1], fill=26, width=int(0.004*S))
    return layer.filter(ImageFilter.GaussianBlur(S*0.0012))

def compose(name, with_ticks):
    bg = np.broadcast_to(BG[None,None,:], (S,S,3)).copy()
    if with_ticks:
        t = np.array(ticks()).astype(np.float32)[...,None]/255.0
        bg = bg*(1-t)+np.array([235,240,248],np.float32)[None,None,:]*t

    arms = build_arms()
    # 柔和投影（无横杠，只让手臂离背景一点）
    shd = arms.filter(ImageFilter.GaussianBlur(S*0.020))
    shi = Image.new('L',(S,S),0); shi.paste(shd,(0,int(S*0.015)))
    sa = np.array(shi).astype(np.float32)[...,None]/255.0*0.38
    bg = bg*(1-sa)

    yy = np.linspace(0,1,S,dtype=np.float32)[:,None,None]
    red = np.broadcast_to(RED_TOP[None,None,:]*(1-yy)+RED_BOT[None,None,:]*yy,(S,S,3))
    aa = np.array(arms).astype(np.float32)[...,None]/255.0
    bg = bg*(1-aa)+red*aa

    hl, sv = bevels(arms)
    bg = bg + aa*hl[...,None]*np.array([96,44,28],np.float32)[None,None,:]
    bg = bg*(1-aa*sv[...,None]*0.30)

    img = Image.fromarray(np.clip(bg,0,255).astype(np.uint8)).resize((1024,1024),Image.LANCZOS)
    mask = (sq_mask(1024,n=4.2)*255).astype(np.uint8)
    out = Image.new('RGBA',(1024,1024),(0,0,0,0))
    out.paste(img,(0,0),Image.fromarray(mask))
    out.save('/root/workspace/apk/logo/%s.png'%name)
    out.resize((96,96),Image.LANCZOS).save('/root/workspace/apk/logo/%s_96.png'%name)
    print('saved',name)

compose('arm7', False)
compose('arm7t', True)
