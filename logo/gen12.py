import numpy as np
from PIL import Image, ImageDraw, ImageFilter
S = 2048; K = S/1000.0
BG = np.array([56, 60, 67], np.float32)
W_TOP = np.array([252, 253, 254], np.float32)
W_BOT = np.array([199, 204, 212], np.float32)

def sq_mask(size, inset=0.0, n=4.2):
    y,x = np.mgrid[0:size,0:size].astype(np.float32)
    c=size/2.0; r=c-inset
    u=np.abs((x-c)/r); v=np.abs((y-c)/r)
    return ((u**n+v**n)<=1.0).astype(np.float32)

def limb(d,p0,p1,r0,r1,n=170):
    for i in range(n+1):
        t=i/n; x=p0[0]+(p1[0]-p0[0])*t; y=p0[1]+(p1[1]-p0[1])*t
        r=r0+(r1-r0)*t
        d.ellipse([x-r,y-r,x+r,y+r],fill=255)

SH=(346,182); EL=(206,452); WR=(250,700)

def build():
    L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
    sh=(SH[0]*K,SH[1]*K); el=(EL[0]*K,EL[1]*K); wr=(WR[0]*K,WR[1]*K)
    limb(d, sh, el, 86*K, 62*K)
    limb(d, el, wr, 62*K, 50*K)
    d.ellipse([sh[0]-82*K, sh[1]-76*K, sh[0]+82*K, sh[1]+76*K], fill=255)
    d.ellipse([el[0]-60*K, el[1]-60*K, el[0]+60*K, el[1]+60*K], fill=255)
    dx,dy=el[0]-sh[0], el[1]-sh[1]; N=(dx*dx+dy*dy)**0.5
    nx,ny=-dy/N, dx/N
    a1=(sh[0]+dx*0.10+nx*20*K, sh[1]+dy*0.10+ny*20*K)
    a2=(sh[0]+dx*0.50+nx*40*K, sh[1]+dy*0.50+ny*40*K)
    limb(d,a1,a2, 66*K, 52*K)
    # 手掌：略扁、前端三指缝
    d.rounded_rectangle([wr[0]-76*K, wr[1]-8*K, wr[0]+76*K, wr[1]+54*K], radius=24*K, fill=255)
    for off in (-44, -14, 16, 46):
        d.line([(wr[0]+off*K, wr[1]+26*K), (wr[0]+off*K, wr[1]+56*K)], fill=0, width=int(7*K))
    L2 = L.transpose(Image.FLIP_LEFT_RIGHT)
    return Image.fromarray(np.maximum(np.array(L),np.array(L2)).astype(np.uint8))

def muscle_lines():
    """手臂的肌肉/关节细节线（很淡）"""
    L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
    # 肘窝：内肘处的弧线
    el=(EL[0]*K, EL[1]*K)
    d.arc([el[0]-52*K, el[1]-52*K, el[0]+52*K, el[1]+52*K], 30, 120, fill=90, width=int(6*K))
    # 二头肌下缘
    sh=(SH[0]*K, SH[1]*K)
    d.arc([sh[0]+10*K, sh[1]+30*K, sh[0]+150*K, sh[1]+170*K], 30, 150, fill=70, width=int(6*K))
    # 前臂中线
    wr=(WR[0]*K, WR[1]*K)
    d.line([((EL[0]+WR[0])/2*K-4*K, (EL[1]+WR[1])/2*K), (wr[0]-2*K, wr[1]-20*K)], fill=60, width=int(5*K))
    L=L.filter(ImageFilter.GaussianBlur(S*0.0026))
    L2=L.transpose(Image.FLIP_LEFT_RIGHT)
    return Image.fromarray(np.maximum(np.array(L),np.array(L2)).astype(np.uint8))

def shade(mask):
    m=np.array(mask).astype(np.float32)/255.0
    hl=np.clip(m-np.roll(m,(7,7),axis=(0,1)),0,1)
    sv=np.clip(m-np.roll(m,(-10,-10),axis=(0,1)),0,1)
    hl=np.array(Image.fromarray((hl*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S*0.007))).astype(np.float32)/255
    sv=np.array(Image.fromarray((sv*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S*0.010))).astype(np.float32)/255
    return hl,sv

def render(name, contact, detail=1.0):
    arms=build()
    bg=np.broadcast_to(BG[None,None,:],(S,S,3)).copy()

    # 接触阴影：手掌压地向两侧散开
    cs=Image.new('L',(S,S),0); cd=ImageDraw.Draw(cs)
    wr=(WR[0]*K, WR[1]*K)
    for mx in (wr[0]-512*K*0, ):  # 掌在镜像位置由绘制两侧完成
        pass
    for side in (-1, 1):
        cx = S/2 + side*(S/2 - wr[0]) if abs(wr[0]-S/2) > 1 else wr[0]
    # 直接画两个掌下阴影
    for cx in (wr[0], S - wr[0]):
        cd.ellipse([cx-96*K, wr[1]+34*K, cx+96*K, wr[1]+92*K], fill=int(255*contact))
    cs=cs.filter(ImageFilter.GaussianBlur(S*0.022))
    cm=np.array(cs).astype(np.float32)[...,None]/255.0
    bg=bg*(1-cm*0.85)

    # 手臂自身投影（更弱）
    shd=arms.filter(ImageFilter.GaussianBlur(S*0.020)); shi=Image.new('L',(S,S),0); shi.paste(shd,(0,int(S*0.012)))
    bg=bg*(1-np.array(shi).astype(np.float32)[...,None]/255.0*0.30)

    yy=np.linspace(0,1,S,dtype=np.float32)[:,None,None]
    white=np.broadcast_to(W_TOP[None,None,:]*(1-yy)+W_BOT[None,None,:]*yy,(S,S,3))
    aa=np.array(arms).astype(np.float32)[...,None]/255.0
    bg=bg*(1-aa)+white*aa

    hl,sv=shade(arms)
    bg=bg+aa*hl[...,None]*np.array([-34,-34,-32],np.float32)[None,None,:]
    bg=bg*(1-aa*sv[...,None]*0.24)

    if detail>0:
        ml=np.array(muscle_lines()).astype(np.float32)[...,None]/255.0
        bg=bg*(1-aa*ml*0.55*detail)

    img=Image.fromarray(np.clip(bg,0,255).astype(np.uint8)).resize((512,512),Image.LANCZOS)
    mask=(sq_mask(512,n=4.2)*255).astype(np.uint8)
    out=Image.new('RGBA',(512,512),(0,0,0,0)); out.paste(img,(0,0),Image.fromarray(mask))
    out.save('/root/workspace/apk/logo/%s.png'%name)
    out.resize((96,96),Image.LANCZOS).save('/root/workspace/apk/logo/%s_96.png'%name)
    return out

a=render('b1', 0.55, 1.0)
b=render('b2', 0.85, 1.4)
sheet=Image.new('RGB',(1120,560),(24,26,30))
for i,o in enumerate((a,b)):
    sheet.paste(o,(i*560+16,24),o)
    ImageDraw.Draw(sheet).text((i*560+28,4),'B%d'%(i+1),fill=(255,255,255))
sheet.save('/root/workspace/apk/logo/sheet_b.png')
print('ok')
