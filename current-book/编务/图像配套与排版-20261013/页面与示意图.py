from 执行 import *
import re

def change(p,fn):
    t=p.read_text();v=fn(t)
    if t==v:return
    save(p);q=p.with_name(p.name+'.修改前-20261013')
    if not q.exists():shutil.copy2(p,q)
    p.write_text(v)

def repl(t,pairs):
    for a,b in pairs:t=t.replace(a,b)
    return t
# C6-1 同步生成器，以免重生成恢复旧横幅
for name in ['分析页.html','生成页面.py']:
 p=S/'05-数据与传感器/output/06-视重数据'/name
 change(p,lambda t:repl(t,[('非严力耕老师装置的原始数据，也非本轮真实测量','构造数据，非严力耕老师装置的实测')]))
# C9-1 移除整块原题图，保留物理模型及数值
p=S/'02-力学与电容器/output/第09章/spring-collision.html'
change(p,lambda t:re.sub(r'  <details class="card">\s*<summary>原题图.*?</details>','',t,flags=re.S).replace('恢复题目数据','恢复默认参数'))
# C10-1 页面/独立 SVG/生成器均同步；打印提示放到框外空白内，不改变 310mm 尺度
for name in ['tank-prediction.html','tank-prediction.svg','generate_ch12.py']:
 p=S/'03-水槽预测与测点/output/第12章'/name
 change(p,lambda t:repl(t,[('第 12 章 ·','第 10 章 ·'),('第12章 ·','第10章 ·'),('第14章复用','第12章复用'),('电力线 E=−∇φ</button>','电场线</button>'),('y="307.2" font-size="3.0"','y="309.1" font-size="2.7"')]))
# C11-1
for name in ['photo-annotation.html','generate_ch13.py']:
 p=S/'03-水槽预测与测点/output/第13章'/name
 change(p,lambda t:repl(t,[('第 13 章 ·','第 11 章 ·'),('第13章 ·','第11章 ·'),('✅ 一致','数量一致，仍须逐点核对'),('✅一致','数量一致，仍须逐点核对'),('未凑数：数量与应有数一致才作数','数量一致，仍须逐点核对')]))
# C12-1 只去显示用调试片段，不改拟合数据与方法
for name in ['tank-measured-compare.html','_template.html','generate_ch14.py']:
 p=S/'03-水槽预测与测点/output/第14章'/name
 def f(t):
  t=repl(t,[('第 14 章 ·','第 12 章 ·'),('第14章 ·','第12章 ·'),('复用第 12 章的求解函数','复用第 10 章的求解函数'),('① 用全部 15 点（原记录 nHold=0 的用法）','原记录：15 点全部参与拟合')])
  t=re.sub(r'\s*<div>中心 φ/U（184 网格）.*?</div>','',t)
  t=re.sub(r'<div class="note warn"><b>先把话说清楚：</b>.*?</div>','<div class="note warn">本页按有限水槽模型拟合端电压；照片重建与这里的拟合采用不同参数，结果应结合各自模型比较。</div>',t,flags=re.S)
  return t
 change(p,f)
p=S/'03-水槽预测与测点/output/第14章/points-predictions-residuals.csv'
change(p,lambda t:t.replace('第14章','第12章'))
# C14-1 舍入归零只用于相对累计绝对电荷的机器精度，不吞掉真实微小电荷
p=P/'正文/第16章-活版电路拼图/配套/电容电流积分.html'
def f(t):
 t=t.replace('<th>Q / C</th>','<th>Q（库仑）</th>')
 t=t.replace('function fmtSig(', 'function netDisplay(net, total, sig) {\n  return net !== 0 && Math.abs(net) <= 64 * Number.EPSILON * total ? "0（舍入误差）" : fmtSig(net, sig);\n}\nfunction fmtSig(',1)
 for net,scale in [('whole.tot.net / 1000','(whole.tot.pos + whole.tot.neg) / 1000'),('whole.tot.net/1000','(whole.tot.pos + whole.tot.neg)/1000'),('whole.tot.net','whole.tot.pos + whole.tot.neg'),('netC','thrC'),('c.tot.net/1000','(c.tot.pos + c.tot.neg)/1000'),('c.tot.net','c.tot.pos + c.tot.neg')]:
  for sig in [8,9]:t=t.replace(f'fmtSig({net}, {sig})',f'netDisplay({net}, {scale}, {sig})')
 return t
change(p,f)
# C17-1
change(P/'正文/第20章-审学生的AI作品/配套/输入/自编审核练习.html',lambda t:t.replace('本页由本书编辑环节独立编写','本书自编练习'))
# B8-1/2/3、B16-1：另存且同步正文
for ch,name in [('第08章-可动圆弧轨道','教程模型'),('第08章-可动圆弧轨道','低速关键状态'),('第08章-可动圆弧轨道','高速运动阶段'),('第19章-从一页到一个网站','第一版更新前后')]:
 src=P/'正文'/ch/'assets'/(name+'.svg');t=src.read_text()
 t=repl(t,[('本教程采用的物理模型','本章采用的物理模型'),('原创几何示意；不代表网页运行结果',''),('vᵧ','v<tspan baseline-shift="sub" font-size="70%">y</tspan>'),('x="533" y="749"','x="533" y="773"'),('三幅为独立状态示意，非等时间隔；','三幅按事件排列，时间间隔不等；'),('原创理想模型示意；不是仿真网页的实测截图。',''),('起步资料包 · 第一版','更新前 · 起步包第一版'),('当前线上 · 第一版','更新后 · 线上第一版')])
 dst=src.with_name(name+'-v2.svg');dst.write_text(t)
 edit(src.parent.parent/'正文.md',[(f'assets/{name}.svg',f'assets/{name}-v2.svg')])
print('完成 C6/C9/C10/C11/C12/C14/C17 以及 B8/B16 的源文件修改')
