import numpy as np
from PIL import Image, ImageDraw, ImageFilter
S = 2048; K = S/1000.0
BG = np.array([56, 60, 67], np.float32)
W_TOP = np.array([250, 251, 253], np.float32)
W_BOT = np.array([198, 203, 211], np.float32)

def sq_mask(size, inset=0.0, n=4.2):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    c = size/2.0; r = c-inset
    u = np.abs((x-c)/r); v = np.abs((y-c)/r)
    return ((u**n + v**n) <= 1.0).astype(np.float32)

def limb(d, p0, p1, r0, r1, n=170):
    for i in range(n+1):
        t=i/n
        x=p0[0]+(p1[0]-p0[0])*t; y=p0[1]+(p1[1]-p0[1])*t
        r=r0+(r1-r0)*t
        d.ellipse([x-r,y-r,x+r,y+r], fill=255)

def arm(sh, el, wr, rs=84, re=58, rw=40, bulge=1.0):
    L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
    sh=(sh[0]*K,sh[1]*K); el=(el[0]*K,el[1]*K); wr=(wr[0]*K,wr[1]*K)
    limb(d, sh, el, rs*K, re*K)
    limb(d, el, wr, re*K, rw*K)
    # 肩：椭圆而非正圆，避免"两个球"
    d.ellipse([sh[0]-rs*0.95*K, sh[1]-rs*0.80*K, sh[0]+rs*0.95*K, sh[1]+rs*0.80*K], fill=255)
    d.ellipse([el[0]-re*K, el[1]-re*K, el[0]+re*K, el[1]+re*K], fill=255)
    dx,dy=el[0]-sh[0], el[1]-sh[1]
    N=(dx*dx+dy*dy)**0.5; nx,ny=-dy/N, dx/N     # 朝外
    a1=(sh[0]+dx*0.15+nx*18*K, sh[1]+dy*0.15+ny*18*K)
    a2=(sh[0]+dx*0.62+nx*44*K*bulge, sh[1]+dy*0.62+ny*44*K*bulge)
    limb(d, a1, a2, 72*K, 54*K)                  # 二头肌
    # 拳头
    d.rounded_rectangle([wr[0]-58*K, wr[1]-40*K, wr[0]+58*K, wr[1]+52*K], radius=24*K, fill=255)
    return L

def sym(parts):
    L = arm(*parts)
    R = L.transpose(Image.FLIP_LEFT_RIGHT)
    return Image.fromarray(np.maximum(np.array(L), np.array(R)).astype(np.uint8))

def shade(mask):
    m=np.array(mask).astype(np.float32)/255.0
    hl=np.clip(m-np.roll(m,(6,6),axis=(0,1)),0,1)
    sv=np.clip(m-np.roll(m,(-9,-9),axis=(0,1)),0,1)
    hl=np.array(Image.fromarray((hl*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S*0.007))).astype(np.float32)/255
    sv=np.array(Image.fromarray((sv*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S*0.010))).astype(np.float32)/255
    return hl,sv

def render(parts, name, bulge=1.0):
    arms=sym(parts)
    bg=np.broadcast_to(BG[None,None,:],(S,S,3)).copy()
    shd=arms.filter(ImageFilter.GaussianBlur(S*0.022)); shi=Image.new('L',(S,S),0); shi.paste(shd,(0,int(S*0.016)))
    sa=np.array(shi).astype(np.float32)[...,None]/255.0*0.45
    bg=bg*(1-sa)
    yy=np.linspace(0,1,S,dtype=np.float32)[:,None,None]
    white=np.broadcast_to(W_TOP[None,None,:]*(1-yy)+W_BOT[None,None,:]*yy,(S,S,3))
    aa=np.array(arms).astype(np.float32)[...,None]/255.0
    bg=bg*(1-aa)+white*aa
    hl,sv=shade(arms)
    bg=bg+aa*hl[...,None]*np.array([-30,-30,-28],np.float32)[None,None,:]
    bg=bg*(1-aa*sv[...,None]*0.26)
    img=Image.fromarray(np.clip(bg,0,255).astype(np.uint8)).resize((512,512),Image.LANCZOS)
    mask=(sq_mask(512,n=4.2)*255).astype(np.uint8)
    out=Image.new('RGBA',(512,512),(0,0,0,0)); out.paste(img,(0,0),Image.fromarray(mask))
    out.save('/root/workspace/apk/logo/%s.png'%name)
    return out

# S1 大间隙、肩压低    S2 更竖、肘略外    S3 上臂水平、前臂垂直
S1 = ((330, 200), (170, 470), (232, 760))
S2 = ((368, 158), (232, 452), (280, 758))
S3 = ((392, 300), (196, 330), (196, 720))
outs=[render(S1,'s1'), render(S2,'s2'), render(S3,'s3')]
sheet=Image.new('RGB',(1680,560),(24,26,30))
for i,o in enumerate(outs):
    sheet.paste(o,(i*560+16,24),o)
    ImageDraw.Draw(sheet).text((i*560+28,4),'S%d'%(i+1),fill=(255,255,255))
sheet.save('/root/workspace/apk/logo/sheet_s.png')
print('ok')
