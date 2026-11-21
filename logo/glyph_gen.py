import numpy as np
from PIL import Image, ImageDraw
S=2048; K=S/1000.0
def limb(d,p0,p1,r0,r1,n=200):
    for i in range(n+1):
        t=i/n; x=p0[0]+(p1[0]-p0[0])*t; y=p0[1]+(p1[1]-p0[1])*t
        r=r0+(r1-r0)*t
        d.ellipse([x-r,y-r,x+r,y+r],fill=255)
L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
sh=(600*K,300*K); el=(818*K,300*K); wr=(818*K,700*K)
limb(d, sh, el, 82*K, 66*K)            # 上臂
d.ellipse([sh[0]-76*K, sh[1]-72*K, sh[0]+76*K, sh[1]+72*K], fill=255)
d.ellipse([el[0]-64*K, el[1]-64*K, el[0]+64*K, el[1]+64*K], fill=255)
# 二头肌轻微隆起
limb(d, (sh[0]+60*K, sh[1]-18*K), (el[0]-50*K, el[1]-18*K), 60*K, 48*K)
# 前臂：明显加粗，肘→腕 74→62
limb(d, el, wr, 74*K, 62*K)
# 拳头
d.rounded_rectangle([wr[0]-74*K, wr[1]-10*K, wr[0]+74*K, wr[1]+58*K], radius=26*K, fill=255)
m=Image.fromarray(np.maximum(np.array(L),np.array(L.transpose(Image.FLIP_LEFT_RIGHT))).astype(np.uint8))
b=m.getbbox(); g=m.crop(b).resize((720, int(720*(b[3]-b[1])/(b[2]-b[0]))), Image.LANCZOS)
g.save('logo/glyph_bold.png'); print('glyph', g.size)
