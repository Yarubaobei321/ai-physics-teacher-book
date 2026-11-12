"""本轮小规模独立复算：不调用配套网页算法，不新增实物测量。"""
from pathlib import Path
import csv,json,math,statistics,itertools,hashlib

OUT=Path(__file__).resolve().parent
BOOK=OUT.parents[2]
checks={}
def slope(t,x):
    mt=statistics.mean(t);mx=statistics.mean(x)
    return sum((a-mt)*(b-mx) for a,b in zip(t,x))/sum((a-mt)**2 for a in t)

x=[0,.0375,.09,.1605,.243,.3405,.453];T=.1
s=[b-a for a,b in zip(x,x[1:])]
v=[(x[k+1]-x[k-1])/(2*T) for k in range(1,6)]
checks['01-02']={'身份':'按章中构造位置独立复算，非实测','首末段法':(s[-1]-s[0])/(5*T*T),'分组逐差':(x[6]-2*x[3]+x[0])/(9*T*T),'拟合':slope([T*k for k in range(1,6)],v),'时间错为0.08s的倍率':(0.1/0.08)**2,'说明':'两种算法共享标尺比例和计时误差，不能称独立测量'}
assert abs(checks['01-02']['拟合']-1.485)<1e-12

table=[]
for d in [.04,.02,.01,.005]:
    dt=(math.sqrt(.5**2+2*.5*d)-.5)/.5
    table.append({'d_m':d,'dt_s':dt,'v_average':d/dt,'v_at_time_mid':.5+.5*dt/2,'relative_u':math.hypot(.0002/d,.0001/dt)})
checks['03']={'身份':'恒加速度构造情境','宽度比较':table,'结论':'时间中点速度与区间平均相等；若目标是前缘到光束的时刻，另有区间偏差。分辨率不能直接当标准不确定度。'}

records={}
for name in ['20260918-161137-fixed-plane30cm-100ms.csv','20260918-161547-motion-away-stop-toward.csv']:
    f=BOOK/'配套包/第04章'/name
    rows=list(csv.DictReader(f.open()));u=[r for r in rows if r['kind']=='U' and r['status']=='ok']
    ts=[float(r['t_us'])/1e6 for r in u];xs=[343*float(r['pulse_us'])/2000 for r in u]
    vel=[slope(ts[i:i+5],xs[i:i+5]) for i in range(len(xs)-4)]
    records[name]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'有效点':len(u),'总时长_s':ts[-1]-ts[0],'距离均值_mm':statistics.mean(xs),'距离样本标准差_mm':statistics.stdev(xs),'五点速度数':len(vel),'五点速度均值_mm_s':statistics.mean(vel),'五点速度样本标准差_mm_s':statistics.stdev(vel),'缺号数':sum(int(b['seq'])!=int(a['seq'])+1 for a,b in zip(u,u[1:]))}
checks['04']={'身份':'历史CSV重新读取与计算；未新采集','records':records,'五点窗口中心滞后_s':.2,'滑动五点窗口跨度_s':.4,'注意':'重叠窗口共享4个位置，不能当作442个独立速度样本估算均值误差。'}
assert records['20260918-161137-fixed-plane30cm-100ms.csv']['有效点']==446

checks['05']={'身份':'代数及输出节奏检查，无标定实测','采样10Hz块平均5点输出Hz':2,'采样10Hz滑动平均5点稳态输出Hz':10,'共同点':'二者均跨越0.4s采样区间；更新快不等于动态响应快','不确定度':'检验残差、重复性、标准件与分辨率应分别列出；最大值不是通用合成规则'}
m=.05;mt=.02;a=-8;g=9.8
checks['06']={'身份':'去皮效应的理想化反例，非现有装置参数','物体质量kg':m,'随动托盘等效质量kg':mt,'a':a,'实际物体支持力N':m*(g+a),'载荷加托盘总支持力N':(m+mt)*(g+a),'减去静态托盘重量后的示数N':m*g+(m+mt)*a,'说明':'后者可负而物体支持力仍正；原装置是否存在此项需测，不能从截图确认噪声机理'}
assert checks['06']['实际物体支持力N']>0 and checks['06']['减去静态托盘重量后的示数N']<0

xx=[0,.002,.0079,.0176,.0315,.0488,.0707];v1=(xx[2]-xx[0])/.04
def eps3(xx):
    vn=(xx[4]-xx[2])/.04
    return ((vn*vn-v1*v1)/2-9.8*(xx[3]-xx[1]))/(9.8*(xx[3]-xx[1]))
cases=[]
for signs in itertools.product([-1,1],repeat=7):
    z=[q+d*.00005 for q,d in zip(xx,signs)];vv1=(z[2]-z[0])/.04;vv3=(z[4]-z[2])/.04
    cases.append(((vv3*vv3-vv1*vv1)/2-9.8*(z[3]-z[1]))/(9.8*(z[3]-z[1])))
checks['07']={'身份':'原演示位置独立复算；端点扰动仅作构造检验','第3点相对差异':eps3(xx),'所有位置各偏半个最末小数单位的范围':[min(cases),max(cases)],'气垫末行相对差异':(.5*.223*(1.493**2-.855**2)-.05*9.8*.3)/(.05*9.8*.3),'说明':'扰动范围说明舍入敏感性，不是实测不确定度或免查理由'}

checks['08']={'身份':'水平动量和能量解析检查','高速离轨':{'vx':1.5,'V':1.5,'vy':math.sqrt(7),'K_total':8,'U':10},'飞行最高点':{'vx':1.5,'V':1.5,'vy':0,'K_total':4.5,'U':13.5},'结论':'两时刻水平共速，但只有最高点竖直动能为零；水平共速不足以单独判断势能最大'}
checks['09']={'身份':'边界条件与证据层级检查，无高压实操','结论':'封闭空腔无内部电荷的静电平衡结论，不能无条件推广为开口容器/金属网内处处E=0；铝箔不张开仅说明现象低于该装置灵敏度'}
r1,r2,r3=16,45,74
checks['11']={'身份':'按原稿粗读半径作条件性诊断','相邻比值':[r2/r1,r3/r2],'等差对数模型要求的中圈_mm':math.sqrt(r1*r3),'记录中圈_mm':r2,'偏差_mm':r2-math.sqrt(r1*r3),'说明':'零点和端电压的线性变换不能改变等差电势所要求的半径等比关系；这不鉴别水深、电导率、探针或照片误差的原因'}
C=470e-6;U=5;tau=4.7
q=C*U*(1-math.exp(-5));qd=q*(1-math.exp(-5))
checks['12']={'身份':'RC解析构造，非真实拼图数据','独立从充分充电起放电5tau_C':q,'先充5tau紧接着放5tau_C':qd,'两者不同原因':'真实连续过程第二段的初始电荷低于CU；两个独立构造过程不能当作同一次完整循环','偏置0.01mA积分23.5s_C':.01e-3*23.5}
checks['13']={'身份':'等效电源/电表模型代数检查','公式':'U_v/E = R_v/(R_v+r)','电表负载低于1percent所需Rv_over_r':99,'示例E1_5_r1_R4':{'I':.3,'U':1.2,'q10s':3,'源能量J':4.5,'外能量J':3.6,'内热J':.9}}
rpm=[60,83,99,118,138,147];e=[.68,.97,1.29,1.52,1.7,1.78]
k=slope(rpm,e);inter=statistics.mean(e)-k*statistics.mean(rpm)
checks['14']={'身份':'按历史表的数值复算，单位仍须作者确认','转速组拟合斜率':k,'截距':inter,'147rpm采样相位缓变周期_s':1/abs(10-4*147/60),'圈采样点数':10*60/147,'说明':'5s仅为10Hz采样与4倍转频的拍频候选；不能排除慢机械变化。没有磁矩与几何标定，波形形状/振幅不能唯一反推距离。'}
V=math.pi/4*(6**2-2.4**2)*1.6
checks['15']={'身份':'按设计尺寸的理想估算，非试样实测','体积mm3':V,'重力mN':1.24*V*1e-6*9.8*1000,'完全浸没有效重量mN':(.24)*V*1e-6*9.8*1000,'毛细力上界mN':.072*math.pi*.0084*1000,'局部水层厚度比':(5-1.6)/5,'说明':'局部厚度比不等于电势误差比例；润湿、气泡与槽底密合条件需实测。'}
checks['16']={'身份':'构造运动用于图区间配对；不访问线上','x=t2的五点窗口':[0,.1,.2,.3,.4],'中心速度':.4,'应配中心距离':.04,'错配最新距离':.16,'结论':'速度、位置应按同一时刻配对；第二版图表正常不自动验证第一版更新'}
base=Path('/Users/yaril/个人文档/3 写作/人机协同科研 sol/40-论文项目/02-论文重建/00-研究素材/02-学生主样本')
us=as_=0
for p in sorted(base.glob('P*/过程对话.json')):
    j=json.loads(p.read_text());us+=j['summary'].get('confirmedUserMessageCount',0);as_+=j['summary'].get('assistantMessageCount',0)
checks['17']={'身份':'当前25份脱敏会话JSON的摘要字段计数','确认学生消息':us,'AI消息':as_,'说明':'现稿158条没有说明角色口径；候选正文撤去该总数，不把158改为157后继续沿用旧编码比例。P17的mr语句位于有绳连接情境，须保留。'}
(OUT/'逐章独立复算结果.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(checks,ensure_ascii=False,indent=2))
