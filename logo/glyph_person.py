import numpy as np
from PIL import Image, ImageDraw
S=2048; K=S/1000.0
def cap(d,p0,p1,r0,r1=None,n=220):
    r1=r0 if r1 is None else r1
    p0=(p0[0]*K,p0[1]*K); p1=(p1[0]*K,p1[1]*K)
    for i in range(n+1):
        t=i/n
        x=p0[0]+(p1[0]-p0[0])*t; y=p0[1]+(p1[1]-p0[1])*t
        r=(r0+(r1-r0)*t)*K
        d.ellipse([x-r,y-r,x+r,y+r],fill=255)
L=Image.new('L',(S,S),0); d=ImageDraw.Draw(L)
# 头
d.ellipse([(330-88)*K,(520-88)*K,(330+88)*K,(520+88)*K], fill=255)
# 躯干（头→髋）
cap(d,(390,548),(640,606),96,86)
# 髋 → 大腿 → 小腿（两条腿稍错开）
cap(d,(640,606),(790,646),84,72)
cap(d,(790,646),(930,700),70,52)
cap(d,(650,632),(800,676),76,66)
cap(d,(800,676),(940,730),64,48)
# 脚
for cx,cy in ((930,700),(940,730)):
    d.rounded_rectangle([(cx-20)*K,(cy-16)*K,(cx+64)*K,(cy+34)*K], radius=24*K, fill=255)
# 手臂：肩→肘→手，肘 90°（两条稍错开）
cap(d,(430,572),(392,694),64,60)
cap(d,(392,694),(430,790),58,54)
cap(d,(470,586),(432,706),58,54)
cap(d,(432,706),(470,798),52,48)
# 手
for cx in (430,470):
    d.rounded_rectangle([(cx-36)*K,782*K,(cx+52)*K,824*K], radius=18*K, fill=255)
m=Image.fromarray(np.array(L))
b=m.getbbox(); g=m.crop(b)
w=720; h=int(w*(b[3]-b[1])/(b[2]-b[0]))
g=g.resize((w,h),Image.LANCZOS); g.save('logo/glyph_person.png'); print('glyph', g.size)
