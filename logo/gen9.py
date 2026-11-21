import numpy as np
from PIL import Image, ImageDraw, ImageFilter
S = 2048; K = S/1000.0
BG = np.array([56, 60, 67], np.float32)
W_TOP = np.array([248, 249, 251], np.float32)
W_BOT = np.array([196, 201, 209], np.float32)

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

def one_arm(sh, el, wr):
    """一只 90° 弯曲的手臂，带二头肌与前臂收细"""
    L = Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
    sh=(sh[0]*K, sh[1]*K); el=(el[0]*K, el[1]*K); wr=(wr[0]*K, wr[1]*K)
    limb(d, sh, el, 84*K, 60*K)
    lim = limb(d, el, wr, 58*K, 40*K)
    d.ellipse([sh[0]-76*K, sh[1]-76*K, sh[0]+76*K, sh[1]+76*K], fill=255)
    d.ellipse([el[0]-56*K, el[1]-56*K, el[0]+56*K, el[1]+56*K], fill=255)
    # 二头肌：朝外侧鼓
    dx,dy = el[0]-sh[0], el[1]-sh[1]
    Ln=(dx*dx+dy*dy)**0.5; nx,ny=-dy/Ln, dx/Ln
    a1=(sh[0]+dx*0.14+nx*16*K, sh[1]+dy*0.14+ny*16*K)
    a2=(sh[0]+dx*0.58+nx*38*K, sh[1]+dy*0.58+ny*38*K)
    limb(d, a1, a2, 74*K, 58*K)
    # 拳头
    d.rounded_rectangle([wr[0]-60*K, wr[1]-44*K, wr[0]+60*K, wr[1]+54*K], radius=26*K, fill=255)
    return L

def place(layer, parts):
    out = Image.new('L',(S,S),0)
    for sh, el, wr in parts:
        a = one_arm(sh, el, wr)
        out = Image.fromarray(np.maximum(np.array(out), np.array(a)).astype(np.uint8))
    return out

def bevels(mask, r=6):
    m=np.array(mask).astype(np.float32)/255.0
    hl=np.clip(m-np.roll(m,(r,r),axis=(0,1)),0,1)
    sv=np.clip(m-np.roll(m,(-r-2,-r-2),axis=(0,1)),0,1)
    hl=np.array(Image.fromarray((hl*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S*0.007))).astype(np.float32)/255
    sv=np.array(Image.fromarray((sv*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S*0.009))).astype(np.float32)/255
    return hl,sv

def render(parts, name):
    arms = place(None, parts)
    bg = np.broadcast_to(BG[None,None,:],(S,S,3)).copy()
    shd=arms.filter(ImageFilter.GaussianBlur(S*0.022)); shi=Image.new('L',(S,S),0); shi.paste(shd,(0,int(S*0.016)))
    sa=np.array(shi).astype(np.float32)[...,None]/255.0*0.45
    bg=bg*(1-sa)
    yy=np.linspace(0,1,S,dtype=np.float32)[:,None,None]
    white=np.broadcast_to(W_TOP[None,None,:]*(1-yy)+W_BOT[None,None,:]*yy,(S,S,3))
    aa=np.array(arms).astype(np.float32)[...,None]/255.0
    bg=bg*(1-aa)+white*aa
    hl,sv=bevels(arms)
    bg=bg+aa*hl[...,None]*np.array([-26,-26,-24],np.float32)[None,None,:]  # 顶部微暗，模拟体积
    bg=bg*(1-aa*sv[...,None]*0.22)
    img=Image.fromarray(np.clip(bg,0,255).astype(np.uint8)).resize((512,512),Image.LANCZOS)
    mask=(sq_mask(512,n=4.2)*255).astype(np.uint8)
    out=Image.new('RGBA',(512,512),(0,0,0,0)); out.paste(img,(0,0),Image.fromarray(mask))
    out.save('/root/workspace/apk/logo/%s.png'%name)
    return out

# P1 两条平行前臂竖直下压，上臂冲出顶部
P1 = [((700,-120),(760,260),(700,740)), ((420,-120),(480,260),(420,740))]
# P2 两只同向弯臂并排（肘朝外、拳朝下）
P2 = [((560,220),(800,470),(740,760)), ((300,220),(540,470),(480,760))]
# P3 前臂竖直、上臂向后倾斜（更像撑在桌面/地面）
P3 = [((740,150),(700,470),(700,760)), ((460,150),(420,470),(420,760))]

outs=[render(P1,'p1'), render(P2,'p2'), render(P3,'p3')]
sheet=Image.new('RGB',(1680,560),(24,26,30))
for i,o in enumerate(outs):
    sheet.paste(o,(i*560+16,24),o)
    ImageDraw.Draw(sheet).text((i*560+28,4),'P%d'%(i+1),fill=(255,255,255))
sheet.save('/root/workspace/apk/logo/sheet_p.png')
print('ok')
