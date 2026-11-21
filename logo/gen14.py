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
SH=(338,168); EL=(192,462); WR=(240,700)
def silhouette():
    L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
    sh=(SH[0]*K,SH[1]*K); el=(EL[0]*K,EL[1]*K); wr=(WR[0]*K,WR[1]*K)
    limb(d,sh,el,88*K,66*K)
    limb(d,el,wr,66*K,54*K)
    d.ellipse([sh[0]-84*K,sh[1]-78*K,sh[0]+84*K,sh[1]+78*K],fill=255)
    d.ellipse([el[0]-64*K,el[1]-64*K,el[0]+64*K,el[1]+64*K],fill=255)
    dx,dy=el[0]-sh[0],el[1]-sh[1]; N=(dx*dx+dy*dy)**0.5; nx,ny=-dy/N,dx/N
    limb(d,(sh[0]+dx*0.08+nx*22*K, sh[1]+dy*0.08+ny*22*K),
            (sh[0]+dx*0.46+nx*46*K, sh[1]+dy*0.46+ny*46*K), 70*K,56*K)
    # 手：手掌 + 外侧拇指（脚没有拇指，这是关键区分）
    d.rounded_rectangle([wr[0]-74*K, wr[1]-18*K, wr[0]+74*K, wr[1]+44*K], radius=20*K, fill=255)
    d.ellipse([wr[0]+52*K, wr[1]-6*K, wr[0]+112*K, wr[1]+54*K], fill=255)      # 拇指
    d.ellipse([wr[0]-70*K, wr[1]+24*K, wr[0]+10*K, wr[1]+62*K], fill=255)      # 掌根肉垫
    m=Image.fromarray(np.maximum(np.array(L),np.array(L.transpose(Image.FLIP_LEFT_RIGHT))).astype(np.uint8))
    return m
def height_field(mask):
    a=np.array(mask.filter(ImageFilter.GaussianBlur(S*0.024))).astype(np.float32)/255.0
    a=a/max(a.max(),1e-6)
    return np.clip(a,0,1)**0.55
def texture():
    L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
    el=(EL[0]*K,EL[1]*K); sh=(SH[0]*K,SH[1]*K); wr=(WR[0]*K,WR[1]*K)
    d.arc([el[0]-56*K,el[1]-56*K,el[0]+56*K,el[1]+56*K],25,115,fill=110,width=int(5*K))   # 肘窝
    d.arc([sh[0]+14*K,sh[1]+26*K,sh[0]+168*K,sh[1]+186*K],20,140,fill=80,width=int(5*K))    # 二头下缘
    d.line([((EL[0]+WR[0])/2*K, (EL[1]+WR[1])/2*K-20*K),(wr[0]-4*K, wr[1]-34*K)],fill=70,width=int(4*K))
    L=L.filter(ImageFilter.GaussianBlur(S*0.0022))
    return Image.fromarray(np.maximum(np.array(L),np.array(L.transpose(Image.FLIP_LEFT_RIGHT))).astype(np.uint8))
arms=silhouette()
bg=np.broadcast_to(BG[None,None,:],(S,S,3)).copy()
cs=Image.new('L',(S,S),0); cd=ImageDraw.Draw(cs); wr=(WR[0]*K,WR[1]*K)
for cx in (wr[0], S-wr[0]):
    cd.ellipse([cx-104*K, wr[1]+48*K, cx+104*K, wr[1]+120*K], fill=150)
cs=cs.filter(ImageFilter.GaussianBlur(S*0.020))
bg=bg*(1-np.array(cs).astype(np.float32)[...,None]/255.0*0.9)
h=height_field(arms)
gy,gx=np.gradient(h)
nx_,ny_=-gx*9.0,-gy*9.0
ln=np.sqrt(nx_**2+ny_**2+1); nx_,ny_,nz_=nx_/ln,ny_/ln,1/ln
L=np.array([-0.42,-0.55,0.72]); L/=np.linalg.norm(L)
H=(L+np.array([0,0,1.0])); H/=np.linalg.norm(H)
diff=np.clip(nx_*L[0]+ny_*L[1]+nz_*L[2],0,1)
spec=np.clip(nx_*H[0]+ny_*H[1]+nz_*H[2],0,1)**26
rim=(1-np.clip(nz_,0,1))**3.0
col=np.array([0.94,0.95,0.97],np.float32)[None,None,:]*(0.24+0.94*diff[...,None])*255.0
col=col+spec[...,None]*0.5*255.0
col=col+rim[...,None]*np.array([0.30,0.33,0.40],np.float32)*255.0
# 肌肉纹理
tx=np.array(texture()).astype(np.float32)[...,None]/255.0
aa=np.array(arms).astype(np.float32)[...,None]/255.0
col=col*(1-aa*tx*0.6)
out=bg*(1-aa)+np.clip(col,0,255)*aa
img=Image.fromarray(np.clip(out,0,255).astype(np.uint8)).resize((512,512),Image.LANCZOS)
mask=(sq_mask(512,n=4.2)*255).astype(np.uint8)
o=Image.new('RGBA',(512,512),(0,0,0,0)); o.paste(img,(0,0),Image.fromarray(mask))
o.save('/root/workspace/apk/logo/d2.png')
o.resize((96,96),Image.LANCZOS).save('/root/workspace/apk/logo/d2_96.png')
print('ok')
