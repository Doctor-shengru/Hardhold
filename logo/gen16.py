import numpy as np
from PIL import Image, ImageDraw, ImageFilter
S=2048; K=S/1000.0
BG=np.array([56,60,67],np.float32)
WHITE=np.array([244,245,247],np.float32)
def sq_mask(size,inset=0.0,n=4.2):
    y,x=np.mgrid[0:size,0:size].astype(np.float32)
    c=size/2.0; r=c-inset
    u=np.abs((x-c)/r); v=np.abs((y-c)/r)
    return ((u**n+v**n)<=1.0).astype(np.float32)
def limb(d,p0,p1,r0,r1,n=220):
    for i in range(n+1):
        t=i/n; x=p0[0]+(p1[0]-p0[0])*t; y=p0[1]+(p1[1]-p0[1])*t
        r=r0+(r1-r0)*t
        d.ellipse([x-r,y-r,x+r,y+r],fill=255)
def build(gap, taper):
    L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
    sh=(500+gap*K, 316*K); el=(818*K, 316*K); wr=(818*K, 700*K)
    if taper:
        limb(d, sh, el, 72*K, 56*K)
        limb(d, el, wr, 56*K, 46*K)
    else:
        limb(d, sh, el, 62*K, 62*K)
        limb(d, el, wr, 62*K, 62*K)
    d.ellipse([el[0]-56*K, el[1]-56*K, el[0]+56*K, el[1]+56*K], fill=255)
    d.ellipse([sh[0]-72*K, sh[1]-72*K, sh[0]+72*K, sh[1]+72*K], fill=255)
    d.ellipse([wr[0]-52*K, wr[1]-20*K, wr[0]+52*K, wr[1]+60*K], fill=255)   # 手掌
    m=Image.fromarray(np.maximum(np.array(L),np.array(L.transpose(Image.FLIP_LEFT_RIGHT))).astype(np.uint8))
    return m
def render(name, gap, taper):
    arms=build(gap,taper)
    bg=np.broadcast_to(BG[None,None,:],(S,S,3)).copy()
    cs=Image.new('L',(S,S),0); cd=ImageDraw.Draw(cs)
    for cx in (818*K, S-818*K):
        cd.ellipse([cx-92*K, 726*K, cx+92*K, 788*K], fill=140)
    cs=cs.filter(ImageFilter.GaussianBlur(S*0.018))
    bg=bg*(1-np.array(cs).astype(np.float32)[...,None]/255.0*0.85)
    aa=np.array(arms).astype(np.float32)[...,None]/255.0
    bg=bg*(1-aa)+WHITE[None,None,:]*aa
    img=Image.fromarray(np.clip(bg,0,255).astype(np.uint8)).resize((512,512),Image.LANCZOS)
    mask=(sq_mask(512,n=4.2)*255).astype(np.uint8)
    o=Image.new('RGBA',(512,512),(0,0,0,0)); o.paste(img,(0,0),Image.fromarray(mask))
    o.save('/root/workspace/apk/logo/%s.png'%name)
    o.resize((96,96),Image.LANCZOS).save('/root/workspace/apk/logo/%s_96.png'%name)
    return o
a=render('f1', 118, 0)
b=render('f2', 118, 1)
sheet=Image.new('RGB',(1120,560),(24,26,30))
for i,o in enumerate((a,b)):
    sheet.paste(o,(i*560+16,24),o)
    ImageDraw.Draw(sheet).text((i*560+28,4),'F%d'%(i+1),fill=(255,255,255))
sheet.save('/root/workspace/apk/logo/sheet_f.png')
print('ok')
