"""平行板实测照片：由原照取点记录做透视校正，换算成毫米坐标并检验界面压降解释。
输入：精品课/静电场分组实验/实测记录/260930坐标纸 实测/PPT标注副本/取点与裁剪记录.json（原照人工取点）
标定：在 2000×2000 校正图上读坐标纸刻度。原点 (1022,1028) px；x 方向 6.42 px/mm，y 方向 6.20 px/mm（读刻度 ±100 mm 得到，读数误差约 ±1 mm）。
"""
import json, numpy as np
SRC='/Users/yaril/Documents/“AI赋能教师”专项培训/精品课/静电场分组实验/实测记录/260930坐标纸 实测/PPT标注副本/取点与裁剪记录.json'
N=2000; X0,Y0,SX,SY=1022,1028,6.42,6.20
def H(src,dst):
    A=[];b=[]
    for (x,y),(u,v) in zip(src,dst):
        A+= [[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]; b+=[u,v]
    return np.append(np.linalg.solve(np.array(A,float),b),1).reshape(3,3)
rec=json.load(open(SRC,encoding='utf-8'))[0]
M=H(rec['corners'],[(0,0),(N-1,0),(N-1,N-1),(0,N-1)])
def mm(p):
    q=M@np.array([p[0],p[1],1.]); q=q[:2]/q[2]
    return (q[0]-X0)/SX,(Y0-q[1])/SY
print('原照',rec['file'],rec['sha256'][:12])
ys=[];phis=[]
for v,g in zip(rec['v'],rec['groups']):
    pts=np.array([mm(p) for p in g]); y=pts[:,1]
    print(f'{v} V: x=',np.round(pts[:,0]).astype(int),' y=',np.round(y,1),f' 平均 {y.mean():.1f} 标准差 {y.std(ddof=1):.1f} 极差 {np.ptp(y):.1f}')
    ys+=list(y); phis+=[v]*len(y)
ys=np.array(ys); phis=np.array(phis,float)
k,c=np.polyfit(ys,phis,1); res=phis-(k*ys+c)
n=len(ys); s=np.sqrt((res**2).sum()/(n-2)); sk=s/np.sqrt(((ys-ys.mean())**2).sum())
print(f'线性拟合 φ = {k*1000:.1f} mV/mm · y + {c:.2f} V；斜率标准误 {sk*1000:.1f} mV/mm；残差均方根 {s*1000:.0f} mV')
print(f'场强 E ≈ {k*1000:.1f} V/m')
for name,yp in [('正极板 y=+93',93),('负极板 y=-90',-90)]:
    phi=k*yp+c
    # 外推不确定度
    se=s*np.sqrt(1/n+(yp-ys.mean())**2/((ys-ys.mean())**2).sum())
    print(f'外推到{name}: φ ≈ {phi:.2f} ± {se:.2f} V（仅统计误差；极板位置 ±2 mm 另加 ±{abs(k)*2:.2f} V）')
for U in (9.3,9.7):
    print(f'若端电压 {U} V：理想均匀分压时 6/4/2 V 线应在 y =',[round(-90+(v/U)*183,1) for v in (6,4,2)])
