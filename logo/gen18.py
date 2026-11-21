import numpy as np
from PIL import Image, ImageDraw, ImageFilter
S=2048; K=S/1000.0
BG=np.array([56,60,67],np.float32)
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
def build(gap, hand, m=1.0):
    L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
    sh=(500+gap*K, 300*K); el=(818*K, 300*K); wr=(818*K, 690*K)
    limb(d, sh, el, 76*K*m, 58*K*m)
    d.ellipse([sh[0]-72*K*m, sh[1]-68*K*m, sh[0]+72*K*m, sh[1]+68*K*m], fill=255)
    d.ellipse([el[0]-58*K, el[1]-58*K, el[0]+58*K, el[1]+58*K], fill=255)
    # 二头肌：只在轮廓上做一点起伏
    limb(d, (sh[0]+70*K, sh[1]-24*K*m), (el[0]-50*K, el[1]-24*K*m), 46*K*m, 38*K*m)
    limb(d, el, wr, 58*K*min(m,1.15), 50*K)
    if hand == 'plain':
        d.ellipse([wr[0]-62*K, wr[1]-14*K, wr[0]+62*K, wr[1]+64*K], fill=255)
    else:   # 掌 + 拇指
        d.rounded_rectangle([wr[0]-58*K, wr[1]-12*K, wr[0]+58*K, wr[1]+62*K], radius=26*K, fill=255)
        d.ellipse([wr[0]-92*K, wr[1]+6*K, wr[0]-30*K, wr[1]+60*K], fill=255)
    m=Image.fromarray(np.maximum(np.array(L),np.array(L.transpose(Image.FLIP_LEFT_RIGHT))).astype(np.uint8))
    return m
def hfield(mask):
    a=np.array(mask.filter(ImageFilter.GaussianBlur(S*0.024))).astype(np.float32)/255.0
    a=a/max(a.max(),1e-6)
    return np.clip(a,0,1)**0.55
def render(name, gap, hand, m=1.0):
    arms=build(gap,hand,m)
    bg=np.broadcast_to(BG[None,None,:],(S,S,3)).copy()
    cs=Image.new('L',(S,S),0); cd=ImageDraw.Draw(cs)
    for cx in (818*K, S-818*K):
        cd.ellipse([cx-92*K, 726*K, cx+92*K, 792*K], fill=140)
    cs=cs.filter(ImageFilter.GaussianBlur(S*0.018))
    bg=bg*(1-np.array(cs).astype(np.float32)[...,None]/255.0*0.85)
    h=hfield(arms)
    gy,gx=np.gradient(h)
    nx_,ny_=-gx*9.0,-gy*9.0
    ln=np.sqrt(nx_**2+ny_**2+1); nx_,ny_,nz_=nx_/ln,ny_/ln,1/ln
    Ld=np.array([-0.42,-0.55,0.72]); Ld/=np.linalg.norm(Ld)
    H=(Ld+np.array([0,0,1.0])); H/=np.linalg.norm(H)
    diff=np.clip(nx_*Ld[0]+ny_*Ld[1]+nz_*Ld[2],0,1)
    spec=np.clip(nx_*H[0]+ny_*H[1]+nz_*H[2],0,1)**26
    rim=(1-np.clip(nz_,0,1))**3.0
    alb=np.array([244,245,247],np.float32)
    col=alb[None,None,:]*(0.26+0.92*diff[...,None])
    col=col+spec[...,None]*0.55*255.0
    col=col+rim[...,None]*np.array([0.28,0.31,0.38],np.float32)*255.0
    aa=np.array(arms).astype(np.float32)[...,None]/255.0
    out=bg*(1-aa)+np.clip(col,0,255)*aa
    img=Image.fromarray(np.clip(out,0,255).astype(np.uint8)).resize((512,512),Image.LANCZOS)
    mask=(sq_mask(512,n=4.2)*255).astype(np.uint8)
    o=Image.new('RGBA',(512,512),(0,0,0,0)); o.paste(img,(0,0),Image.fromarray(mask))
    o.save('/root/workspace/apk/logo/%s.png'%name)
    o.resize((96,96),Image.LANCZOS).save('/root/workspace/apk/logo/%s_96.png'%name)
    return o
a=render('h1', 120, 'thumb', 1.0)
b=render('h2', 120, 'thumb', 1.3)
c=render('h3', 120, 'thumb', 1.6)
sheet=Image.new('RGB',(1740,620),(24,26,30))
for i,o in enumerate((a,b,c)):
    sheet.paste(o,(i*580+16,24),o)
    sm=o.resize((96,96),Image.LANCZOS); sheet.paste(sm,(i*580+242,540),sm)
    ImageDraw.Draw(sheet).text((i*580+26,4),'H%d'%(i+1),fill=(255,255,255))
sheet.save('/root/workspace/apk/logo/sheet_h.png')
print('ok')
