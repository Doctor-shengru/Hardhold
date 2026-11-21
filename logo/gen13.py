import numpy as np
from PIL import Image, ImageDraw, ImageFilter
S = 2048; K = S/1000.0
BG = np.array([56, 60, 67], np.float32)

def sq_mask(size, inset=0.0, n=4.2):
    y,x = np.mgrid[0:size,0:size].astype(np.float32)
    c=size/2.0; r=c-inset
    u=np.abs((x-c)/r); v=np.abs((y-c)/r)
    return ((u**n+v**n)<=1.0).astype(np.float32)

def limb(d,p0,p1,r0,r1,n=200):
    for i in range(n+1):
        t=i/n; x=p0[0]+(p1[0]-p0[0])*t; y=p0[1]+(p1[1]-p0[1])*t
        r=r0+(r1-r0)*t
        d.ellipse([x-r,y-r,x+r,y+r],fill=255)

SH=(344,176); EL=(198,462); WR=(246,704)
def silhouette():
    L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
    sh=(SH[0]*K,SH[1]*K); el=(EL[0]*K,EL[1]*K); wr=(WR[0]*K,WR[1]*K)
    limb(d, sh, el, 88*K, 64*K)
    limb(d, el, wr, 64*K, 54*K)
    d.ellipse([sh[0]-84*K, sh[1]-78*K, sh[0]+84*K, sh[1]+78*K], fill=255)
    d.ellipse([el[0]-62*K, el[1]-62*K, el[0]+62*K, el[1]+62*K], fill=255)
    dx,dy=el[0]-sh[0], el[1]-sh[1]; N=(dx*dx+dy*dy)**0.5
    nx,ny=-dy/N, dx/N
    limb(d,(sh[0]+dx*0.10+nx*20*K, sh[1]+dy*0.10+ny*20*K),
            (sh[0]+dx*0.50+nx*42*K, sh[1]+dy*0.50+ny*42*K), 68*K, 54*K)
    # 拳头：圆润，无指缝
    d.rounded_rectangle([wr[0]-74*K, wr[1]-14*K, wr[0]+74*K, wr[1]+58*K], radius=34*K, fill=255)
    m=Image.fromarray(np.maximum(np.array(L),np.array(L.transpose(Image.FLIP_LEFT_RIGHT))).astype(np.uint8))
    return m

def height_field(mask):
    h = mask.filter(ImageFilter.GaussianBlur(S*0.026))
    a = np.array(h).astype(np.float32)/255.0
    a = a/ max(a.max(),1e-6)
    return np.clip(a,0,1)**0.55

def render(name, gloss, shadow):
    arms=silhouette()
    bg=np.broadcast_to(BG[None,None,:],(S,S,3)).copy()

    # 接触阴影：拳头下方
    cs=Image.new('L',(S,S),0); cd=ImageDraw.Draw(cs)
    wr=(WR[0]*K, WR[1]*K)
    for cx in (wr[0], S-wr[0]):
        cd.ellipse([cx-100*K, wr[1]+40*K, cx+100*K, wr[1]+110*K], fill=int(255*shadow))
    cs=cs.filter(ImageFilter.GaussianBlur(S*0.020))
    bg=bg*(1-np.array(cs).astype(np.float32)[...,None]/255.0*0.9)

    h=height_field(arms)
    gy,gx=np.gradient(h)
    nz=1.0
    nx_,ny_ = -gx*8.0, -gy*8.0
    ln=np.sqrt(nx_**2+ny_**2+nz**2)
    nx_,ny_,nz_ = nx_/ln, ny_/ln, nz/ln

    # 光：左上前方
    L=np.array([-0.42,-0.55,0.72]); L/=np.linalg.norm(L)
    V=np.array([0,0,1.0])
    H=(L+V); H/=np.linalg.norm(H)
    diff=np.clip(nx_*L[0]+ny_*L[1]+nz_*L[2],0,1)
    spec=np.clip(nx_*H[0]+ny_*H[1]+nz_*H[2],0,1)**(28*gloss)
    rim=(1-np.clip(nz_,0,1))**3.0

    albedo=np.array([0.93,0.94,0.96],np.float32)*255.0
    col = albedo[None,None,:]*(0.26+0.92*diff[...,None])
    col = col + spec[...,None]*0.55*gloss*255.0
    col = col + rim[...,None]*np.array([0.35,0.38,0.45],np.float32)*255.0

    aa=np.array(arms).astype(np.float32)[...,None]/255.0
    out=bg*(1-aa)+col*aa
    img=Image.fromarray(np.clip(out,0,255).astype(np.uint8)).resize((512,512),Image.LANCZOS)
    mask=(sq_mask(512,n=4.2)*255).astype(np.uint8)
    o=Image.new('RGBA',(512,512),(0,0,0,0)); o.paste(img,(0,0),Image.fromarray(mask))
    o.save('/root/workspace/apk/logo/%s.png'%name)
    o.resize((96,96),Image.LANCZOS).save('/root/workspace/apk/logo/%s_96.png'%name)
    return o

a=render('c1', 1.0, 0.6)
b=render('c2', 0.55, 0.6)
sheet=Image.new('RGB',(1120,560),(24,26,30))
for i,o in enumerate((a,b)):
    sheet.paste(o,(i*560+16,24),o)
    ImageDraw.Draw(sheet).text((i*560+28,4),'C%d'%(i+1),fill=(255,255,255))
sheet.save('/root/workspace/apk/logo/sheet_c.png')
print('ok')
