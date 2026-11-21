import numpy as np
from PIL import Image, ImageDraw, ImageFilter
S=2048; K=S/1000.0
BG=np.array([56,60,67],np.float32)
def sq_mask(size,inset=0.0,n=4.2):
    y,x=np.mgrid[0:size,0:size].astype(np.float32)
    c=size/2.0; r=c-inset
    u=np.abs((x-c)/r); v=np.abs((y-c)/r)
    return ((u**n+v**n)<=1.0).astype(np.float32)
def limb(d,p0,p1,r0,r1,n=200):
    for i in range(n+1):
        t=i/n; x=p0[0]+(p1[0]-p0[0])*t; y=p0[1]+(p1[1]-p0[1])*t
        r=r0+(r1-r0)*t
        d.ellipse([x-r,y-r,x+r,y+r],fill=255)
def build(gap, hand_w, thr):
    L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
    sh=(500+gap*K, 300*K)          # 肩（内侧，靠中线留缝）
    el=(820*K, 300*K)              # 肘（外侧，90°）
    wr=(820*K, 690*K)              # 腕
    limb(d, sh, el, 78*K, 58*K)    # 上臂水平
    d.ellipse([el[0]-58*K, el[1]-58*K, el[0]+58*K, el[1]+58*K], fill=255)
    d.ellipse([sh[0]-74*K, sh[1]-70*K, sh[0]+74*K, sh[1]+70*K], fill=255)
    # 二头肌：上臂上缘的隆起
    limb(d, (sh[0]+70*K, sh[1]-24*K), (el[0]-46*K, el[1]-24*K), 50*K, 40*K)
    limb(d, el, wr, 58*K, 50*K)    # 前臂垂直
    # 手：掌 + 拇指
    # 手：掌 + 内侧拇指 + 前端四指圆角
    d.rounded_rectangle([wr[0]-hand_w*K, wr[1]-8*K, wr[0]+hand_w*K, wr[1]+58*K], radius=20*K, fill=255)
    for i,off in enumerate((-hand_w*0.62, -hand_w*0.20, hand_w*0.22, hand_w*0.62)):
        d.ellipse([wr[0]+off*K-15*K, wr[1]+40*K, wr[0]+off*K+15*K, wr[1]+70*K], fill=255)
    d.ellipse([wr[0]-hand_w*K-6*K, wr[1]+6*K, wr[0]-hand_w*K+thr*K, wr[1]+52*K], fill=255)
    m=Image.fromarray(np.maximum(np.array(L),np.array(L.transpose(Image.FLIP_LEFT_RIGHT))).astype(np.uint8))
    return m
def height_field(mask):
    a=np.array(mask.filter(ImageFilter.GaussianBlur(S*0.022))).astype(np.float32)/255.0
    a=a/max(a.max(),1e-6)
    return np.clip(a,0,1)**0.55
def tex():
    L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
    # 肘窝：外侧肘部的弧
    el=(812*K,300*K)
    d.arc([el[0]-50*K,el[1]-30*K,el[0]+40*K,el[1]+60*K], 100, 190, fill=105, width=int(5*K))
    # 前臂中线
    d.line([(812*K, 400*K),(806*K, 640*K)], fill=70, width=int(4*K))
    # 上臂下缘
    d.line([(600*K, 350*K),(780*K, 350*K)], fill=60, width=int(4*K))
    L=L.filter(ImageFilter.GaussianBlur(S*0.0022))
    return Image.fromarray(np.maximum(np.array(L),np.array(L.transpose(Image.FLIP_LEFT_RIGHT))).astype(np.uint8))
def render(name, gap, hw, thr):
    arms=build(gap,hw,thr)
    bg=np.broadcast_to(BG[None,None,:],(S,S,3)).copy()
    cs=Image.new('L',(S,S),0); cd=ImageDraw.Draw(cs)
    for cx in (812*K, S-812*K):
        cd.ellipse([cx-96*K, 724*K, cx+96*K, 790*K], fill=150)
    cs=cs.filter(ImageFilter.GaussianBlur(S*0.020))
    bg=bg*(1-np.array(cs).astype(np.float32)[...,None]/255.0*0.9)
    h=height_field(arms)
    gy,gx=np.gradient(h)
    nx_,ny_=-gx*9.0,-gy*9.0
    ln=np.sqrt(nx_**2+ny_**2+1); nx_,ny_,nz_=nx_/ln,ny_/ln,1/ln
    Ld=np.array([-0.42,-0.55,0.72]); Ld/=np.linalg.norm(Ld)
    H=(Ld+np.array([0,0,1.0])); H/=np.linalg.norm(H)
    diff=np.clip(nx_*Ld[0]+ny_*Ld[1]+nz_*Ld[2],0,1)
    spec=np.clip(nx_*H[0]+ny_*H[1]+nz_*H[2],0,1)**26
    rim=(1-np.clip(nz_,0,1))**3.0
    col=np.array([0.94,0.95,0.97],np.float32)[None,None,:]*(0.24+0.94*diff[...,None])*255.0
    col=col+spec[...,None]*0.5*255.0
    col=col+rim[...,None]*np.array([0.30,0.33,0.40],np.float32)*255.0
    tx=np.array(tex()).astype(np.float32)[...,None]/255.0
    aa=np.array(arms).astype(np.float32)[...,None]/255.0
    col=col*(1-aa*tx*0.6)
    out=bg*(1-aa)+np.clip(col,0,255)*aa
    img=Image.fromarray(np.clip(out,0,255).astype(np.uint8)).resize((512,512),Image.LANCZOS)
    mask=(sq_mask(512,n=4.2)*255).astype(np.uint8)
    o=Image.new('RGBA',(512,512),(0,0,0,0)); o.paste(img,(0,0),Image.fromarray(mask))
    o.save('/root/workspace/apk/logo/%s.png'%name)
    o.resize((96,96),Image.LANCZOS).save('/root/workspace/apk/logo/%s_96.png'%name)
    return o
a=render('e3', 104, 82, 40)
b=render('e4', 128, 86, 36)
sheet=Image.new('RGB',(1120,560),(24,26,30))
for i,o in enumerate((a,b)):
    sheet.paste(o,(i*560+16,24),o)
    ImageDraw.Draw(sheet).text((i*560+28,4),'E%d'%(i+1),fill=(255,255,255))
sheet.save('/root/workspace/apk/logo/sheet_e.png')
print('ok')
