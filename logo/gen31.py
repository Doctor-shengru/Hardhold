import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
S=2048; K=S/1000.0
BG=np.array([56,60,67],np.float32)
SH=(620*K,300*K); EL=(818*K,300*K); WR=(818*K,660*K)

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

def arm_mask():
    L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
    sh, el, wr = SH, EL, WR
    dx, dy = el[0]-sh[0], el[1]-sh[1]
    def at(t, lift=0):
        return (sh[0]+dx*t, sh[1]+dy*t-lift)
    # 上臂基干
    limb(d, sh, el, 58*K, 52*K)
    # 二头肌：峰（0.22 起鼓，0.50 最高，0.72 收束到肌腱）
    p1 = at(0.14, 6*K); p2 = at(0.52, 12*K); p3 = at(0.80, 4*K)
    limb(d, p1, p2, 62*K, 70*K)
    limb(d, p2, p3, 70*K, 44*K)
    # 肩头
    d.ellipse([sh[0]-66*K, sh[1]-62*K, sh[0]+66*K, sh[1]+62*K], fill=255)
    # 肘
    d.ellipse([el[0]-52*K, el[1]-52*K, el[0]+52*K, el[1]+52*K], fill=255)
    # 前臂：肘粗腕细
    limb(d, el, wr, 56*K, 42*K)
    # 手掌：底部压平（接触形变）
    hy = wr[1]+18*K
    d.rounded_rectangle([wr[0]-66*K, hy-16*K, wr[0]+66*K, hy+52*K], radius=22*K, fill=255)
    d.rectangle([wr[0]-66*K, hy+30*K, wr[0]+66*K, hy+52*K], fill=255)
    return Image.fromarray(np.maximum(np.array(L),np.array(L.transpose(Image.FLIP_LEFT_RIGHT))).astype(np.uint8))

def hfield(mask, sigma=0.024):
    a=np.array(mask.filter(ImageFilter.GaussianBlur(S*sigma))).astype(np.float32)/255.0
    a=a/max(a.max(),1e-6)
    return np.clip(a,0,1)**0.55

def shade(arms):
    h=hfield(arms)
    gy,gx=np.gradient(h)
    nx_,ny_=-gx*9.0,-gy*9.0
    ln=np.sqrt(nx_**2+ny_**2+1); nx_,ny_,nz_=nx_/ln,ny_/ln,1/ln
    Ld=np.array([-0.42,-0.55,0.72]); Ld/=np.linalg.norm(Ld)
    H=(Ld+np.array([0,0,1.0])); H/=np.linalg.norm(H)
    diff=np.clip(nx_*Ld[0]+ny_*Ld[1]+nz_*Ld[2],0,1)
    spec=np.clip(nx_*H[0]+ny_*H[1]+nz_*H[2],0,1)**28
    rim=(1-np.clip(nz_,0,1))**3.0
    col=np.array([244,245,247],np.float32)[None,None,:]*(0.24+0.93*diff[...,None])
    col=col+spec[...,None]*0.5*255.0
    col=col+rim[...,None]*np.array([0.26,0.29,0.36],np.float32)*255.0
    return col

def build(text, ground, name):
    arms=arm_mask(); col=shade(arms)
    bg=np.broadcast_to(BG[None,None,:],(S,S,3)).copy()

    # 紧凑接触阴影（贴合手掌，不再是散开的大团）
    cs=Image.new('L',(S,S),0); cd=ImageDraw.Draw(cs)
    hy=WR[1]+18*K+52*K
    for cx in (WR[0], S-WR[0]):
        cd.ellipse([cx-78*K, hy-10*K, cx+78*K, hy+26*K], fill=190)
    cs=cs.filter(ImageFilter.GaussianBlur(S*0.009))
    bg=bg*(1-np.array(cs).astype(np.float32)[...,None]/255.0*0.9)

    # 可选的极淡地面线
    if ground:
        gl=Image.new('L',(S,S),0); gd=ImageDraw.Draw(gl)
        gd.rounded_rectangle([300*K, hy+22*K, S-300*K, hy+30*K], radius=4*K, fill=34)
        gl=gl.filter(ImageFilter.GaussianBlur(S*0.004))
        gm=np.array(gl).astype(np.float32)[...,None]/255.0
        bg=bg*(1-gm)+np.array([210,216,226],np.float32)[None,None,:]*gm

    aa=np.array(arms).astype(np.float32)[...,None]/255.0
    bg=bg*(1-aa)+np.clip(col,0,255)*aa
    img=Image.fromarray(np.clip(bg,0,255).astype(np.uint8))

    if text:
        canvas=Image.new('RGB',(S,S),tuple(BG.astype(int)))
        art=img.resize((int(S*0.84),int(S*0.84)),Image.LANCZOS)
        canvas.paste(art,((S-art.size[0])//2,int(S*0.06)))
        d=ImageDraw.Draw(canvas)
        f=ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf', int(266))
        t='SUM'; track=30
        ws=[f.getlength(c) for c in t]; total=sum(ws)+track*(len(t)-1)
        x=(S-total)/2; y=int(S*0.585)
        for c,w in zip(t,ws):
            d.text((x,y),c,font=f,fill=(246,247,250)); x+=w+track
        img=canvas

    mask=(sq_mask(S,n=4.2)*255).astype(np.uint8)
    out=Image.new('RGBA',(S,S),(0,0,0,0)); out.paste(img,(0,0),Image.fromarray(mask))
    big=out.resize((512,512),Image.LANCZOS); big.save('/root/workspace/apk/logo/%s.png'%name)
    out.resize((96,96),Image.LANCZOS).save('/root/workspace/apk/logo/%s_96.png'%name)
    return big

a=build(True, False, 'n1')
b=build(True, True, 'n2')
c=build(False, True, 'n3')
sheet=Image.new('RGB',(1740,640),(24,26,30))
for i,o in enumerate((a,b,c)):
    sheet.paste(o,(i*580+16,40))
    sm=o.resize((96,96),Image.LANCZOS); sheet.paste(sm,(i*580+236,556),sm)
    ImageDraw.Draw(sheet).text((i*580+26,12),['N1 big SUM','N2 +ground','N3 no SUM'][i],fill=(255,255,255))
sheet.save('/root/workspace/apk/logo/sheet_n.png')
print('ok')
