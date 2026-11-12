"""独立复算：用二维有限差分（稀疏直接解）重算有限水槽中的电势，与印刷底图所用的三维解对照。
与原程序不同：原程序是三维、逐层迭代；这里是二维、一次性解线性方程组，代码另写，不调用原程序。
槽内 ±147 mm，槽壁绝缘（法向导数为零），电极节点固定电势（正端 1，负端 0）。
"""
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl, sys
PRINT='/Users/yaril/Documents/“AI赋能教师”专项培训/精品课/静电场分组实验/实验底图印刷包/计算数据/'
def solve(case,h=0.5,rpost=3.0):
    x=np.arange(-147,147+1e-9,h); n=len(x); X,Y=np.meshgrid(x,x,indexing='xy')
    fix=np.full(X.shape,np.nan)
    def post(cx,cy,v): fix[(X-cx)**2+(Y-cy)**2<=rpost**2+1e-9]=v
    def bar(cx,v): fix[(np.abs(X-cx)<=1.5+1e-9)&(np.abs(Y)<=125)]=v
    def ring(v): fix[np.hypot(X,Y)>=124]=v
    if case=='dipole': post(-60,0,1); post(60,0,0)
    if case=='plates': bar(-90,1); bar(90,0)
    if case=='point-ring': post(0,0,1); ring(0)
    idx=np.arange(n*n).reshape(n,n); rows=[];cols=[];vals=[]; b=np.zeros(n*n)
    for i in range(n):
        for j in range(n):
            k=idx[i,j]
            if not np.isnan(fix[i,j]): rows.append(k);cols.append(k);vals.append(1);b[k]=fix[i,j];continue
            rows.append(k);cols.append(k);vals.append(-4)
            for di,dj in((1,0),(-1,0),(0,1),(0,-1)):
                ii,jj=i+di,j+dj
                if ii<0 or ii>=n: ii=i-di   # 绝缘壁：镜像
                if jj<0 or jj>=n: jj=j-dj
                rows.append(k);cols.append(idx[ii,jj]);vals.append(1)
    A=sp.csr_matrix((vals,(rows,cols)),shape=(n*n,n*n))
    u=spl.spsolve(A.tocsc(),b).reshape(n,n)
    return x,u
def at(x,u,px,py):
    from scipy.interpolate import RegularGridInterpolator as R
    return R((x,x),u.T)((px,py))
case=sys.argv[1]
for h in (1.0,0.5):
    x,u=solve(case,h)
    print(f'== {case} 网格 {h} mm')
    if case=='dipole':
        print(' 中点 u=',round(float(at(x,u,0,0)),4))
        # 右槽壁 x=147 上 u=1/3 的位置
        wall=at(x,u,np.full(589,147.0),np.linspace(-147,147,589))
        ys=np.linspace(-147,147,589); s=np.where(np.diff(np.sign(wall-1/3)))[0]
        print(' 右槽壁 u 范围',round(wall.min(),3),'—',round(wall.max(),3),' u=1/3 与右壁交点 y≈',[round(float(ys[k]),1) for k in s])
        top=at(x,u,np.linspace(-147,147,589),np.full(589,147.0)); print(' 上槽壁 u 范围',round(top.min(),3),'—',round(top.max(),3))
    if case=='plates':
        for yy in (0,100,130):
            print(f' y={yy}: 剖面 x=-60,-30,0,30,60 的 u =',np.round(at(x,u,np.array([-60,-30,0,30,60.]),np.full(5,float(yy))),4))
    if case=='point-ring':
        for r in (7.61,19.3,48.9): print(f' r={r}: u={float(at(x,u,r,0)):.3f}（对数式 a=3 mm 应为 {np.log(124/r)/np.log(124/3):.3f}）')
try:
    d=np.load(PRINT+f'{case}-print.npz'); px=d['x']; pu=d['u']
    print('== 与印刷底图三维解对照（同一点，正端=1）')
    pts=[(0,0),(30,0),(-30,40),(100,100),(140,0),(0,140)]
    for p in pts:
        mine=float(at(x,u,*p)); theirs=float(at(px,pu,*p))
        print(f' {p}: 本复算 {mine:.4f}  底图 {theirs:.4f}  差 {mine-theirs:+.4f}')
except Exception as e: print('对照失败',e)
