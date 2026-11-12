#!/usr/bin/env python3
"""第 14—17 章正文用到的算例，独立于网页重新计算一遍。"""
from math import pi, sin, cos, sqrt, radians
def par(a,b): return a*b/(a+b)
print('--ch14 磁吸台')
Rv,Ra=3000,0.10; R=10; E=3; r=1
for name,Rs in [('65%',50*.65),('A端',0)]:
    Rp=par(R,Rv); I=E/(r+Ra+Rs+Rp); print(name,'I',round(I,5),'U',round(I*Rp,5))
print('3V挡直接跨电池 U',round(E*3000/(3000+1),4),' 15V挡电流uA',round(E/(15000+1)*1e6,1))
print('电表 1.5V: 3V档偏转',1.5/3,' 15V档偏转',1.5/15)
print('游标',[(N,N-1,round(1/N,3)) for N in (10,20,50)],'测微器每格',0.5/50)
print('--ch15')
U=3
print('限流空载范围 100/20:',round(U*100/120,3),U)
def lim(k,t): return U/(1+k*t)
def div(k,t): return U*t/(1+k*t*(1-t))
for Rh,Rx in [(50,500),(50,50),(50,10),(200,5)]:
    k=Rh/Rx; print('限流',Rh,Rx,'k',k,'最小',round(lim(k,1),3),'t=0.1',round(lim(k,.1),3),'前10%%行程占变化%.0f%%'%(100*(3-lim(k,.1))/(3-lim(k,1))))
for k in (0.2,1,2,10):
    print('分压中点 k',k,round(div(k,.5),3))
print('手算核对 3V,200,100 中点:',round(U*par(100,100)/(par(100,100)+100),3))
print('公式核对 随机点:',all(abs(div(k,t)-U*par(t*k,1)/(par(t*k,1)+(1-t)*k))<1e-12 for k in (.1,.2,1,2,3,5,10) for t in (.1,.3,.5,.7,.9)))
print('教参 5Ω/10Ω 限流最低',3*10/15)
for Rh,RL in [(200,5),(50,5),(50,50),(50,100),(50,500)]:
    Itot=U/Rh; print('分压 空载总电流 A',Rh,RL,round(Itot,3),'滑到输出端总电流',round(U/par(Rh,RL),3),'负载满压电流',round(U/RL,3))
print('--ch16')
print('内接 200/10:',210,' 外接 200,2000:',round(par(200,2000),1))
print('内接 87.4:',87.5,' 外接',round(par(87.4,1000),1))
print('判据 sqrt(RA RV) RA=1,RV=3000',round(sqrt(3000),1),' 精确 Rx^2=RA(Rx+RV):',round((1+sqrt(1+4*3000))/2,1))
print('金属丝 R',round(1e-6*.18/(pi*(0.3e-3)**2/4),3))
print('视频第05次 1.5/0.16',1.5/.16)
I=[.10,.14,.19,.26,.34,.46];V=[1.30,1.25,1.20,1.12,1.02,.85]
n=len(I);sx=sum(I);sy=sum(V);sxx=sum(i*i for i in I);sxy=sum(i*v for i,v in zip(I,V))
m=(n*sxy-sx*sy)/(n*sxx-sx*sx);b=(sy-m*sx)/n;print('E-r 拟合 b',round(b,3),'m',round(m,3))
print('等效电源 E=1.5 r=1 RV=3000: E测',round(1.5*3000/3001,5),'r测',round(par(3000,1),5))
print('等效 RV=8 夸张: E测',round(1.5*8/9,3),'r测',round(par(8,1),3))
print('欧姆表 R内',1.5/.01,'接150:',1.5/(150+150)*1000,'mA')
for e in (1.5,1.3):
    Ro=e/.01;Ix=e/(Ro+150);print('E',e,'R内',round(Ro,1),'I mA',round(Ix*1000,3),'表盘读',round(1.5/Ix-150,1))
Im=6e-3;RA=100
for E in (6,12):
    R1=E/Im-RA
    a,b_=1,2000
    for _ in range(80):
        m_=(a+b_)/2;It=E/(R1+par(m_,RA));Ia=It*m_/(m_+RA)
        if Ia>Im/2:b_=m_
        else:a=m_
    print('半偏A E',E,'R1',R1,'R2',round(a,2))
RV=3000;Um=3;E=6
def solveX(R0):
    a,b_=0,1
    for _ in range(60):
        x=(a+b_)/2;p=par(max(x,1e-9)*R0,RV);u=E*p/(p+(1-x)*R0)
        if u>Um:b_=x
        else:a=x
    return (a+b_)/2
for R0 in (20,2000):
    x=solveX(R0);lo,hi=0,20000
    for _ in range(80):
        Rb=(lo+hi)/2;tot=RV+Rb;p=par(x*R0,tot);u=E*p/(p+(1-x)*R0);uv=u*RV/tot
        if uv>1.5:lo=Rb
        else:hi=Rb
    print('半偏V R0',R0,'R2',round(lo,1))
print('--ch17')
qm=1e8
def rad(v,B): return v/(qm*B)*100
print('2km/s,2mT r cm',rad(2e3,2e-3),' T/2 us',pi/(qm*2e-3)*1e6)
rc=2/(1+cos(radians(30)));vc=qm*1e-3*rc/100;print('30° rc',round(rc,4),'vc km/s',round(vc/1e3,4),'右',round(rc*(1+sin(radians(30))),3),'上',round(rc*(1-cos(radians(30))),3))
rc=2/(1+cos(radians(60)));print('60° rc',round(rc,4),'vc',round(qm*1e-3*rc/100/1e3,4),'x',round(rc*(1+sin(radians(60))),3))
print('2.5km/s 1mT r',rad(2.5e3,1e-3))
v=4e3;B=2e-3;th=radians(60);T=2*pi/(qm*B);print('螺旋 T us',T*1e6,'/pi',T*1e6/pi,'螺距 cm',v*cos(th)*T*100,' r',v*sin(th)/(qm*B)*100)
print('圆形 磁聚焦 r=R')
print('--补充')
print('分流 0.6A',round(0.001*30/0.599,4),'分压 3V',3/0.001-30)
for name,U0,Rx,RV,RA in [('A',3,8,3000,2),('B',3,2000,3000,1)]:
    p=par(Rx,RV);I0=U0/(p+RA);U_0=I0*p;I1=U0/(Rx+RA);U1=U0
    print('试触',name,'外接',round(U_0,3),round(I0*1000,2),'内接',U1,round(I1*1000,2),'dU%',round(abs(U_0-U1)/U_0*100,2),'dI%',round(abs(I0-I1)/I0*100,2))
E,r=1.5,1.2;print('安阻 斜率',round(1/E,3),'截距',round(r/E,3),'伏阻 斜率',round(r/E,3),'截距',round(1/E,3))
print('滑线 平衡 L1',100*20/32)
from math import atan,degrees
for rr in (3,1,9): print('圆形场径向 r',rr,'偏转角',round(2*degrees(atan(3/rr)),1))
print('测微器 2.458=',2.0+45.8*.01,' 2.958=',2.5+45.8*.01)
