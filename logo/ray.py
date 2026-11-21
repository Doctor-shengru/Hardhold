import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import sys

RES = int(sys.argv[1]) if len(sys.argv) > 1 else 256
BG = np.array([56,60,67],np.float32)/255.0
FLOOR_Y = -0.62

def norm(v):
    return v/np.linalg.norm(v)

def sd_capsule(p, a, b, r):
    a=np.array(a,float); b=np.array(b,float)
    ba=b-a; pa=p-a
    h=np.clip(pa@ba/(ba@ba),0,1)
    q=pa-h[...,None]*ba
    return np.linalg.norm(q,axis=-1)-r

def sd_sphere(p,c,r):
    return np.linalg.norm(p-np.array(c,float),axis=-1)-r

def sd_box(p,c,half,r=0.05):
    q=np.abs(p-np.array(c,float))-np.array(half,float)+r
    out=np.linalg.norm(np.maximum(q,0),axis=-1)
    inn=np.minimum(np.max(q,axis=-1),0)
    return out+inn-r

def sdf(p):
    d = np.full(p.shape[0], 1e9)
    for s in (1,-1):
        S=(s*0.46, 0.44, 0.0)
        E=(s*0.84, 0.44, 0.0)
        W=(s*0.84,-0.28, 0.0)
        d=np.minimum(d, sd_capsule(p,S,E,0.085))
        d=np.minimum(d, sd_capsule(p,E,W,0.075))
        d=np.minimum(d, sd_sphere(p,E,0.095))
        d=np.minimum(d, sd_sphere(p,S,0.105))
        d=np.minimum(d, sd_sphere(p,(s*0.60,0.30,0.02),0.10))    # 二头肌
        d=np.minimum(d, sd_box(p,(s*0.84,-0.42,0.0),(0.11,0.055,0.09)))  # 手
    d=np.minimum(d, p[:,1]-FLOOR_Y)
    return d

def render(res):
    f=1.55
    ys,xs=np.mgrid[0:res,0:res].astype(np.float32)
    px=(xs-res/2)/(res/2); py=-(ys-res/2)/(res/2)
    # 相机：轻微 3/4 视角
    cam=np.array([0.55,0.55,2.7]); fwd=norm(np.array([0,0,0])-cam)
    right=norm(np.cross(fwd,np.array([0,1,0]))); up=np.cross(right,fwd)
    dirs=(fwd[None,None,:]+(px[...,None]*right[None,None,:]+py[...,None]*up[None,None,:])*(1/f))
    dirs/=np.linalg.norm(dirs,axis=-1,keepdims=True)
    o=np.broadcast_to(cam,(res,res,3)).reshape(-1,3)
    d=dirs.reshape(-1,3)
    t=np.zeros(res*res); alive=np.ones(res*res,bool)
    for step in range(110):
        p=o+d*t[:,None]
        dd=sdf(p)
        hit=dd<0.0015
        t=np.where(alive,np.maximum(t+np.minimum(dd,0.12),0.0),t)
        alive=alive&~hit
        if not alive.any(): break
    p=o+d*t[:,None]
    # 法线
    eps=0.0015
    n=np.stack([sdf(p+np.array([eps,0,0]))-sdf(p-np.array([eps,0,0])),
                sdf(p+np.array([0,eps,0]))-sdf(p-np.array([0,eps,0])),
                sdf(p+np.array([0,0,eps]))-sdf(p-np.array([0,0,eps]))],axis=-1)
    n/=np.linalg.norm(n,axis=-1,keepdims=True)+1e-9
    L=norm(np.array([-0.45,0.85,0.65]))
    V=-d
    Hh=norm(L[None,:]+V)
    onfloor=np.abs(p[:,1]-FLOOR_Y)<0.004
    alb=np.where(onfloor[:,None],np.array([0.16,0.17,0.19]),np.array([0.95,0.96,0.97]))
    diff=np.clip((n*L).sum(-1),0,1)
    spec=np.clip((n*Hh).sum(-1),0,1)**40
    ao=np.clip(1-1.4*np.abs(sdf(p- L*0.06 + np.array([0,0.0,0]))),0.35,1)
    rim=np.clip(1-np.abs((n*V).sum(-1)),0,1)**3
    col=alb*(0.20+0.85*diff[...,None])*ao[...,None]
    col=col+spec[...,None]*0.55
    col=col+rim[...,None]*0.12
    hit_mask=(~alive).reshape(res,res)
    img=BG[None,None,:]*np.ones((res,res,3))
    img[hit_mask]=col.reshape(res,res,3)[hit_mask]
    return np.clip(img,0,1)

img=render(RES)
im=Image.fromarray((img*255).astype(np.uint8))
im.save('/root/workspace/apk/logo/ray.png')
print('rendered',RES)
