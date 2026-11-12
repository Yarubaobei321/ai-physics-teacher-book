#!/usr/bin/env python3
"""第 16、17 章的解释图。坐标由公式计算，文字说明写在正文图注里。"""
from pathlib import Path
from math import pi,cos,sin,radians,sqrt
R=Path(__file__).resolve().parents[2]/'正文'
F='font-family="PingFang SC,Hiragino Sans GB,Microsoft YaHei,sans-serif"'
INK='#22313a';RED='#b8382c';BLUE='#1f6aa5';GR='#7c8a93'
def wrap(w,h,b): return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" {F}><rect width="{w}" height="{h}" fill="#fff"/>{b}</svg>\n'
def L(x1,y1,x2,y2,c=INK,w=2.4,d=''): return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{c}" stroke-width="{w}"{d}/>'
def T(x,y,s,c=INK,z=20,a='middle',st=''): return f'<text x="{x:.1f}" y="{y:.1f}" fill="{c}" font-size="{z}" text-anchor="{a}"{st}>{s}</text>'
def res(x,y,c=INK): return f'<rect x="{x-44}" y="{y-15}" width="88" height="30" fill="#fff" stroke="{c}" stroke-width="2.4"/>'
def meter(x,y,s,c=INK): return f'<circle cx="{x}" cy="{y}" r="24" fill="#fff" stroke="{c}" stroke-width="2.4"/>'+T(x,y+8,s,c,24)
def dot(x,y): return f'<circle cx="{x}" cy="{y}" r="5" fill="{INK}"/>'
def circuit(ox,inner):
    y=170;x1,x2=ox+20,ox+400
    b=L(x1,y,x2,y)
    if inner:
        rx,ax=ox+130,ox+285;vx1,vx2=ox+60,ox+360
    else:
        ax,rx=ox+70,ox+265;vx1,vx2=ox+160,ox+360
    b+=L(vx1,y,vx1,70)+L(vx1,70,vx2,70)+L(vx2,70,vx2,y)
    if inner:
        b+=res(rx,y)+meter(ax,y,'A',RED)+meter((vx1+vx2)/2,70,'V')
        b+=T(rx,y+46,'Rₓ',z=20)+T(ax,y+52,'电流表也分到电压',RED,17)
        b+=T(ox+210,y+92,'电压表读数偏大：R测＝Rₓ＋R_A',RED,19)
    else:
        b+=meter(ax,y,'A')+res(rx,y)+meter((vx1+vx2)/2,70,'V',RED)
        b+=T(rx,y+46,'Rₓ',z=20)+T((vx1+vx2)/2,40,'电压表也分走电流',RED,17)
        b+=T(ox+210,y+92,'电流表读数偏大：R测＝Rₓ∥R_V',RED,19)
    b+=dot(vx1,y)+dot(vx2,y)+T(ox+210,y+128,'内接法：电流表在电压表两接点之内' if inner else '外接法：电流表在电压表两接点之外',INK,18)
    return b
(R/'第16章-测量电路与系统误差/assets/内接外接.svg').write_text(wrap(880,320,circuit(10,True)+circuit(450,False)),encoding='utf8')
# U-I 图：电压表分流。E=1.5,r=1,RV=8（夸张内阻，便于看清）
ox,oy,sx,sy=90,370,330,200
X=lambda i:ox+i*sx;Y=lambda u:oy-u*sy
E,r,RV=1.5,1,8;Em=E*RV/(RV+r);rm=RV*r/(RV+r)
b=L(ox,oy,X(1.75),oy)+L(ox,oy,ox,Y(1.72))
b+=T(X(1.75)+12,oy+7,'I/A',z=19,a='start')+T(ox-8,Y(1.72)-10,'U/V',z=19)
for i in (.5,1,1.5): b+=L(X(i),oy,X(i),oy+7)+T(X(i),oy+30,str(i),GR,17)
for u in (.5,1,1.5): b+=L(ox-7,Y(u),ox,Y(u))+T(ox-14,Y(u)+6,str(u),GR,17,'end')
b+=L(X(0),Y(E),X(E/r),Y(0),BLUE,3.2)+L(X(0),Y(Em),X(Em/rm),Y(0),RED,3.2,' stroke-dasharray="9 6"')
U=1.0;It=(E-U)/r;Im=(Em-U)/rm
b+=L(X(Im),Y(U),X(It),Y(U),RED,6)
b+=T(X(It)+10,Y(U)-10,'这段长度是电压表分走的电流',RED,17,'start')
b+=f'<circle cx="{X(E/r):.1f}" cy="{Y(0):.1f}" r="7" fill="{INK}"/>'+T(X(1.36),Y(.26),'两线在此相交',INK,17,'start')
b+=T(X(.52),Y(1.33),'真实线 E＝1.5 V，r＝1 Ω',BLUE,17,'start')+T(X(.05),Y(.24),'测量线 E测＝1.33 V，r测＝0.89 Ω',RED,17,'start')
(R/'第16章-测量电路与系统误差/assets/电压表分流UI图.svg').write_text(wrap(760,420,b),encoding='utf8')
# 磁聚焦：r=R 时 O A C P 组成菱形
cx,cy,Rr=400,250,150;a=radians(200)
Ax,Ay=cx-Rr,cy
th=radians(-35)  # 入射方向相对水平（上为负的屏幕坐标）
# 向上偏转：圆心在入射点沿速度左法向一侧，半径 R
vx,vy=cos(th),sin(th)
Cx,Cy=Ax+Rr*vy,Ay-Rr*vx
# 出射点 P 为圆 O 与圆 C 的另一交点
dx,dy=Cx-cx,Cy-cy;d=sqrt(dx*dx+dy*dy)
Px,Py=cx+dx,cy+dy   # 菱形对顶：O+C-A
Px,Py=cx+Cx-Ax,cy+Cy-Ay
b=f'<circle cx="{cx}" cy="{cy}" r="{Rr}" fill="#eef4f8" stroke="{BLUE}" stroke-width="2.4"/>'
b+=f'<circle cx="{Cx:.1f}" cy="{Cy:.1f}" r="{Rr}" fill="none" stroke="{GR}" stroke-width="1.6" stroke-dasharray="6 6"/>'
b+=f'<path d="M{Ax:.1f} {Ay:.1f} A{Rr} {Rr} 0 0 0 {Px:.1f} {Py:.1f}" fill="none" stroke="{RED}" stroke-width="3.6"/>'
for p,q in [((cx,cy),(Ax,Ay)),((cx,cy),(Px,Py)),((Cx,Cy),(Ax,Ay)),((Cx,Cy),(Px,Py))]:
    b+=L(p[0],p[1],q[0],q[1],INK,2)
b+=L(Ax,Ay,Ax+78*vx,Ay+78*vy,RED,3)+L(Px,Py,Px,Py-78,RED,3)
for x,y in [(cx,cy),(Ax,Ay),(Cx,Cy),(Px,Py)]: b+=f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{INK}"/>'
b+=T(cx+14,cy+26,'O',z=22,a='start')+T(Ax-14,Ay+24,'A',z=22,a='end')+T(Cx-12,Cy-12,'C',z=22,a='end')+T(Px+8,Py-14,'P',z=22,a='start')
b+=T(Px+10,Py-70,'v',RED,20,'start')+T(Ax+78*vx+8,Ay+78*vy-4,'v',RED,20,'start')
(R/'第17章-带电粒子在磁场中运动/assets/磁聚焦菱形.svg').write_text(wrap(740,450,b),encoding='utf8')
print('ok',Px,Py,'CP',sqrt((Cx-Px)**2+(Cy-Py)**2),'OP',sqrt((cx-Px)**2+(cy-Py)**2))
