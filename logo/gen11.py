import numpy as np
from PIL import Image, ImageDraw, ImageFilter
S = 2048; K = S/1000.0
BG = np.array([56, 60, 67], np.float32)
W_TOP = np.array([252, 253, 254], np.float32)
W_BOT = np.array([200, 205, 213], np.float32)

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

def arm(sh, el, wr):
    L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
    sh=(sh[0]*K,sh[1]*K); el=(el[0]*K,el[1]*K); wr=(wr[0]*K,wr[1]*K)
    limb(d, sh, el, 86*K, 62*K)           # 上臂：厚
    limb(d, el, wr, 62*K, 52*K)           # 前臂：不收到很细，保持肌肉感
    d.ellipse([sh[0]-82*K, sh[1]-74*K, sh[0]+82*K, sh[1]+74*K], fill=255)
    d.ellipse([el[0]-60*K, el[1]-60*K, el[0]+60*K, el[1]+60*K], fill=255)
    # 二头肌峰：靠上、朝外
    dx,dy=el[0]-sh[0], el[1]-sh[1]; N=(dx*dx+dy*dy)**0.5
    nx,ny=-dy/N, dx/N
    a1=(sh[0]+dx*0.10+nx*20*K, sh[1]+dy*0.10+ny*20*K)
    a2=(sh[0]+dx*0.52+nx*40*K, sh[1]+dy*0.52+ny*40*K)
    limb(d,a1,a2, 66*K, 52*K)
    # 手掌：扁、宽、贴地（不是脚块）
    d.rounded_rectangle([wr[0]-78*K, wr[1]-6*K, wr[0]+78*K, wr[1]+52*K], radius=26*K, fill=255)
    return L

def sym(L):
    R=L.transpose(Image.FLIP_LEFT_RIGHT)
    return Image.fromarray(np.maximum(np.array(L),np.array(R)).astype(np.uint8))

def fingers(mask):
    """在手掌前缘压出指缝"""
    L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
    for dx in (-30,30):
        x=512*K+dx*K; 
    return L

def shade(mask):
    m=np.array(mask).astype(np.float32)/255.0
    hl=np.clip(m-np.roll(m,(7,7),axis=(0,1)),0,1)
    sv=np.clip(m-np.roll(m,(-10,-10),axis=(0,1)),0,1)
    hl=np.array(Image.fromarray((hl*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S*0.007))).astype(np.float32)/255
    sv=np.array(Image.fromarray((sv*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S*0.010))).astype(np.float32)/255
    return hl,sv

def render(parts,name):
    L=arm(*parts); arms=sym(L)
    bg=np.broadcast_to(BG[None,None,:],(S,S,3)).copy()
    shd=arms.filter(ImageFilter.GaussianBlur(S*0.020)); shi=Image.new('L',(S,S),0); shi.paste(shd,(0,int(S*0.014)))
    bg=bg*(1-np.array(shi).astype(np.float32)[...,None]/255.0*0.42)
    yy=np.linspace(0,1,S,dtype=np.float32)[:,None,None]
    white=np.broadcast_to(W_TOP[None,None,:]*(1-yy)+W_BOT[None,None,:]*yy,(S,S,3))
    aa=np.array(arms).astype(np.float32)[...,None]/255.0
    bg=bg*(1-aa)+white*aa

    # 指缝：手掌下缘三条短竖缝，压暗
    fg=Image.new('L',(S,S),0); fd=ImageDraw.Draw(fg)
    wr=(parts[2][0]*K, parts[2][1]*K)
    for off in (-52,-18,16,50):
        x=wr[0]+off*K
        fd.line([(x, wr[1]+8*K),(x, wr[1]+44*K)], fill=150, width=int(5*K))
    fg=Image.new('L',(S,S),0)  # 先不画，保持干净
    hl,sv=shade(arms)
    bg=bg+aa*hl[...,None]*np.array([-34,-34,-32],np.float32)[None,None,:]
    bg=bg*(1-aa*sv[...,None]*0.24)
    img=Image.fromarray(np.clip(bg,0,255).astype(np.uint8)).resize((512,512),Image.LANCZOS)
    mask=(sq_mask(512,n=4.2)*255).astype(np.uint8)
    out=Image.new('RGBA',(512,512),(0,0,0,0)); out.paste(img,(0,0),Image.fromarray(mask))
    out.save('/root/workspace/apk/logo/%s.png'%name)
    out.resize((96,96),Image.LANCZOS).save('/root/workspace/apk/logo/%s_96.png'%name)
    return out

# T1 对称、间隙大、肩在顶部两端
T1=((352,168),(214,470),(262,742))
# T2 对称、上臂更短更粗、肘更高
T2=((336,196),(196,430),(248,742))
outs=[render(T1,'t1'),render(T2,'t2')]
sheet=Image.new('RGB',(1120,560),(24,26,30))
for i,o in enumerate(outs):
    sheet.paste(o,(i*560+16,24),o)
    ImageDraw.Draw(sheet).text((i*560+28,4),'T%d'%(i+1),fill=(255,255,255))
sheet.save('/root/workspace/apk/logo/sheet_t.png')
print('ok')
