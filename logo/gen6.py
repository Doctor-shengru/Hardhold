import numpy as np
from PIL import Image, ImageDraw, ImageFilter
S = 2048; K = S/1000.0
RED_TOP = np.array([226, 100, 72], np.float32)
RED_BOT = np.array([154, 38, 24], np.float32)
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

def arm90():
    """水平上臂 + 垂直前臂，肘部 90°，拳头压地"""
    layer = Image.new('L', (S,S), 0)
    d = ImageDraw.Draw(layer)
    sh = (452*K, 366*K)
    el = (772*K, 366*K)
    wr = (772*K, 706*K)
    limb(d, sh, el, 74*K, 56*K)
    d.ellipse([sh[0]-76*K, sh[1]-76*K, sh[0]+76*K, sh[1]+76*K], fill=255)   # 肩
    d.ellipse([el[0]-58*K, el[1]-58*K, el[0]+58*K, el[1]+58*K], fill=255)   # 肘
    # 二头肌：上臂中段向上鼓
    limb(d, (sh[0]+46*K, sh[1]-6*K), (el[0]-54*K, el[1]-6*K), 78*K, 62*K)
    # 前臂
    limb(d, (el[0], el[1]+20*K), wr, 56*K, 40*K)
    # 拳头压地
    d.rounded_rectangle([wr[0]-72*K, wr[1]+8*K, wr[0]+72*K, wr[1]+96*K], radius=28*K, fill=255)
    left = layer.transpose(Image.FLIP_LEFT_RIGHT)
    return Image.fromarray(np.maximum(np.array(layer), np.array(left)).astype(np.uint8))

def bevels(mask):
    m = np.array(mask).astype(np.float32)/255.0
    hl = np.clip(m - np.roll(m,(5,5),axis=(0,1)),0,1)
    sv = np.clip(m - np.roll(m,(-7,-7),axis=(0,1)),0,1)
    hl = np.array(Image.fromarray((hl*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S*0.009))).astype(np.float32)/255
    sv = np.array(Image.fromarray((sv*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S*0.011))).astype(np.float32)/255
    return hl, sv

def compose(arms, name):
    bg = np.broadcast_to(BG[None,None,:], (S,S,3)).copy()
    edge = sq_mask(S); inner = sq_mask(S, inset=S*0.008)
    rim = np.clip(edge-inner,0,1)[...,None]
    y,x = np.mgrid[0:S,0:S].astype(np.float32)
    w = np.clip(1.25-(x/S*0.6+y/S*0.8),0,1)[...,None]
    bg = bg*(1-rim*w*0.9)+np.array([255,255,255],np.float32)[None,None,:]*(rim*w*0.9)
    bg = bg*(1-rim*(1-w)*0.45)

    floor = Image.new('L',(S,S),0); fd=ImageDraw.Draw(floor)
    fy = 795*K
    fd.rounded_rectangle([196*K, fy-12*K, 804*K, fy+12*K], radius=12*K, fill=120)
    floor = floor.filter(ImageFilter.GaussianBlur(S*0.0035))
    fm = np.array(floor).astype(np.float32)[...,None]/255.0
    bg = bg*(1-fm)+np.array([226,232,240],np.float32)[None,None,:]*fm

    shd = arms.filter(ImageFilter.GaussianBlur(S*0.016))
    shi = Image.new('L',(S,S),0); shi.paste(shd,(0,int(S*0.014)))
    sa = np.array(shi).astype(np.float32)[...,None]/255.0*0.5
    bg = bg*(1-sa)

    yy = np.linspace(0,1,S,dtype=np.float32)[:,None,None]
    red = np.broadcast_to(RED_TOP[None,None,:]*(1-yy)+RED_BOT[None,None,:]*yy,(S,S,3))
    aa = np.array(arms).astype(np.float32)[...,None]/255.0
    bg = bg*(1-aa)+red*aa
    hl,sv = bevels(arms)
    bg = bg + aa*hl[...,None]*np.array([90,40,26],np.float32)[None,None,:]
    bg = bg*(1-aa*sv[...,None]*0.32)

    # 地面上的红色反光
    refl = Image.new('L',(S,S),0); refl.paste(arms,(0,0))
    crop = refl.crop((0,int(fy),S,int(fy+170*K)))
    crop = Image.eval(crop, lambda v:int(v*0.5)).resize((S,int(170*K)),Image.LANCZOS).filter(ImageFilter.GaussianBlur(S*0.02))
    canvas = Image.new('L',(S,S),0); canvas.paste(crop,(0,int(fy+10*K)))
    ra = np.array(canvas).astype(np.float32)[...,None]/255.0*0.20
    bg = bg*(1-ra)+np.array([190,64,44],np.float32)[None,None,:]*ra

    img = Image.fromarray(np.clip(bg,0,255).astype(np.uint8)).resize((1024,1024),Image.LANCZOS)
    mask = (sq_mask(1024,n=4.2)*255).astype(np.uint8)
    out = Image.new('RGBA',(1024,1024),(0,0,0,0))
    out.paste(img,(0,0),Image.fromarray(mask))
    out.save('/root/workspace/apk/logo/%s.png'%name)
    out.resize((96,96),Image.LANCZOS).save('/root/workspace/apk/logo/%s_96.png'%name)
    print('saved',name)

compose(arm90(), 'arm90')
