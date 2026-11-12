"""平行板有限水槽：板外（钢条背后到槽壁）与板端附近的场强，和板间中部比较。网格 0.5 mm，二维（钢条贯穿水层，二维即严格）。"""
import numpy as np, importlib.util as iu
s=iu.spec_from_file_location('m','独立二维复算.py'); 
import sys; sys.argv=['x','none']; m=iu.module_from_spec(s); s.loader.exec_module(m)
x,u=m.solve('plates',0.5)
gy,gx=np.gradient(u,0.5)   # 每毫米
E=np.hypot(gx,gy)
from scipy.interpolate import RegularGridInterpolator as R
f=R((x,x),E.T)
E0=float(f((0,0)))
print(f'板间中部 (0,0)：|∇u| = {E0*1000:.3f} /m（以正端=1）；相当 U/d，d≈{1/E0:.0f} mm')
for p,name in [((0,100),'板间、靠近板端一侧 y=100'),((0,135),'板端以外、两板之间 y=135'),((-89,135),'正极钢条端头外 3 mm'),((-120,0),'正极钢条背后中部'),((-120,120),'正极钢条背后靠端头'),((-140,140),'背后角落')]:
    print(f'{name} {p}: {float(f(p))/E0*100:.1f}% 板间场强')
