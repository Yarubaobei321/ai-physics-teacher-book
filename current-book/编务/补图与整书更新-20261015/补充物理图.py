"""为本轮补充的物理关系图保留可重建源文件；图中数据均为明确标注的理论示意。"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle, Circle

P = Path(__file__).resolve().parents[2]
font_manager.fontManager.addfont('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
plt.rcParams.update({'font.family':'Arial Unicode MS', 'font.size':12,
                     'axes.unicode_minus':False, 'svg.fonttype':'none',
                     'axes.spines.top':False,'axes.spines.right':False})
BLUE='#24628b'; RED='#bd493a'; TEAL='#218278'; GRAY='#576777'

def save(fig, chapter, name):
    dest=next((P/'正文').glob(f'第{chapter:02d}章-*'))/'assets'
    dest.mkdir(exist_ok=True)
    fig.savefig(dest/(name+'.png'),dpi=240,bbox_inches='tight',facecolor='white')
    fig.savefig(dest/(name+'.svg'),bbox_inches='tight',facecolor='white')
    plt.close(fig)

# 计数点包含五个打点周期，不能把四个中间点当成四个周期。
fig,ax=plt.subplots(figsize=(10,3.4));ax.set(xlim=(-.5,10.5),ylim=(-1.5,1.5));ax.axis('off')
ax.add_patch(Rectangle((-.3,-.28),10.6,.56,facecolor='#f3f5f6',edgecolor='#ced7dd'))
for x in range(11):
    ax.plot(x,0,'o',color=BLUE if x%5==0 else GRAY,ms=9 if x%5==0 else 4)
    if x%5==0:ax.text(x,.5,['O','A','B'][x//5],ha='center',fontsize=15,color=BLUE)
for j in range(5):
    ax.annotate('',(j+1,-.65),(j,-.65),arrowprops=dict(arrowstyle='<->',color=GRAY,lw=1.3))
    ax.text(j+.5,-.94,'0.02 s',ha='center',fontsize=11)
ax.annotate('',(5,1.02),(0,1.02),arrowprops=dict(arrowstyle='<->',color=BLUE,lw=1.6))
ax.text(2.5,1.12,'4 个中间计时点，5 个打点周期',ha='center',fontsize=14,color=BLUE)
ax.text(7.6,.92,'打点频率  f = 50 Hz',ha='center')
ax.text(7.6,-.75,'计数间隔  T = 5/f = 0.10 s',ha='center',color=BLUE,fontsize=14)
ax.text(5,-1.4,'图示只说明计时关系；点距未按真实运动绘制。',ha='center',color=GRAY,fontsize=11)
save(fig,2,'计数点与打点周期')

# 两种电压测量：电源连接不变，只改变电压表的公共端位置。
fig,axes=plt.subplots(1,2,figsize=(11,5.2))
for i,ax in enumerate(axes):
    ax.set(xlim=(0,10),ylim=(0,10));ax.axis('off')
    ax.add_patch(Rectangle((1,1.7),8,5.2,facecolor='#eef7fa',edgecolor=BLUE,lw=1.4))
    ax.plot([1.5,8.5],[6.2,6.2],color=RED,lw=6)
    ax.plot([1.5,8.5],[2.4,2.4],color=BLUE,lw=6)
    ax.text(8.8,6.2,'+',ha='center',va='center',color=RED,fontsize=18)
    ax.text(8.8,2.4,'−',ha='center',va='center',color=BLUE,fontsize=18)
    ax.text(5,1.1,'电池持续接在两电极之间',ha='center',color=GRAY,fontsize=11)
    ax.add_patch(Rectangle((3.15,7.5),3.7,1.25,facecolor='white',edgecolor=GRAY,lw=1.5))
    ax.text(5,8.2,'电压表',ha='center',va='center',fontsize=15)
    ax.text(3.65,7.7,'COM',ha='center',fontsize=9)
    ax.text(6.35,7.7,'V',ha='center',fontsize=10,color=RED)
    ax.plot([6.35,9.5,9.5,6.5],[7.5,7.1,4.6,4.6],color=RED,lw=1.8)
    ax.plot(6.5,4.6,'o',color=RED,ms=7)
    ax.text(6.5,4.1,'P' if i==0 else 'A',ha='center',color=RED,fontsize=13)
    if i==0:
        ax.plot([3.65,.5,.5,2],[7.5,7.1,2.4,2.4],color='#30343b',lw=1.8)
        ax.text(3.6,3.0,'参考电极：0 V',ha='center',color=BLUE,fontsize=12)
        ax.set_title('① 测某点电势',loc='left',fontsize=16,pad=12)
        ax.text(5,.05,r'读数 $=\varphi_P-0=\varphi_P$',ha='center',fontsize=15)
    else:
        ax.plot([3.65,.5,.5,3.5],[7.5,7.1,4.6,4.6],color='#30343b',lw=1.8)
        ax.plot(3.5,4.6,'o',color='#30343b',ms=7)
        ax.text(3.5,4.1,'B',ha='center',fontsize=13)
        for x in [3.5,6.5]:ax.add_patch(Circle((x,4.6),.27,fill=False,edgecolor='#c19124',lw=3))
        ax.set_title('② 检验两点是否等势',loc='left',fontsize=16,pad=12)
        ax.text(5,.05,r'读数 $=\varphi_A-\varphi_B\approx0$',ha='center',fontsize=15)
fig.subplots_adjust(wspace=.16)
save(fig,11,'测电势与验等势接线')

# 同一等量同种正点电荷模型，两条路径使用相同的电势单位和零点。
fig,axes=plt.subplots(1,3,figsize=(12.2,4))
ax=axes[0];ax.set_aspect('equal');ax.set(xlim=(-1.55,1.55),ylim=(-1.3,1.3));ax.axis('off')
ax.annotate('',(1.45,0),(-1.45,0),arrowprops=dict(arrowstyle='->',color=BLUE,lw=1.7))
ax.annotate('',(0,1.2),(0,-1.2),arrowprops=dict(arrowstyle='->',color=TEAL,lw=1.7))
for x in [-1,1]:
    ax.add_patch(Circle((x,0),.14,color=RED));ax.text(x,0,'+',ha='center',va='center',color='white',fontsize=17)
ax.plot(0,0,'ko',ms=4);ax.text(.1,-.22,'O');ax.text(1.3,-.24,'x',color=BLUE);ax.text(.12,1.08,'y',color=TEAL)
ax.text(0,-.65,'两电荷位于 x = ±a',ha='center',fontsize=11)
ax.set_title('同一个中点 O，两条剖面',fontsize=13)
x=np.linspace(-.8,.8,400);y=np.linspace(-1.5,1.5,400)
for ax,xx,phi,label,col in [(axes[1],x,1/(1+x)+1/(1-x),'连线方向  x/a',BLUE),
                             (axes[2],y,2/np.sqrt(1+y*y),'中垂线方向  y/a',TEAL)]:
    ax.plot(xx,phi,color=col,lw=2.5);ax.plot(0,2,'o',color=RED,ms=6)
    ax.axhline(2,color=GRAY,lw=.8,ls=':');ax.set_ylim(0,6);ax.set_xlabel(label)
    ax.set_ylabel(r'$\varphi/(kq/a)$');ax.grid(alpha=.15)
axes[1].set_title('O 是这段连线上的最低点',fontsize=13)
axes[2].set_title('O 是中垂线上的最高点',fontsize=13)
fig.text(.52,-.035,'理想点电荷，q > 0，以无穷远为电势零点；两条曲线在 O 处斜率都为零，电势均为 2kq/a。',ha='center',fontsize=11,color=GRAY)
fig.tight_layout(w_pad=2)
save(fig,12,'等量同种两条剖面')

# 三块平行板：d1:d2=1:2 仅为画图选取，不冒充原题给定比例。
fig,axes=plt.subplots(1,2,figsize=(10.5,4))
for sign,ax in zip([1,-1],axes):
    ax.plot([0,1,3],np.array([0,1,0])*sign,color=BLUE,lw=2.3)
    for pos,lab in [(0,'A'),(1,'B'),(3,'C')]:
        ax.axvline(pos,color=GRAY,lw=.8,ls=':');ax.text(pos,-1.21,lab,ha='center',fontsize=13)
    ax.axhline(0,color=GRAY,lw=.8)
    ax.plot([.5,2],[sign*.5,sign*.5],'o',color=RED,ms=6)
    ax.plot([.5,2],[sign*.5,sign*.5],'--',color=RED,lw=1)
    for pos,lab in [(.5,'a'),(2,'b')]:ax.text(pos,sign*.5+.1,lab,ha='center',color=RED,fontsize=13)
    ax.set(xlim=(-.2,3.2),ylim=(-1.3,1.3),xlabel='垂直极板的方向 x',ylabel='相对电势（示意）')
    ax.set_xticks([]);ax.set_yticks([-1,0,1]);ax.set_title('B 板带正电' if sign==1 else 'B 板带负电',fontsize=15)
fig.text(.5,-.035,'两间隙的中点电势相同；窄间隙的斜率绝对值更大。图示取 d₂ = 2d₁，原题只要求 d₁ < d₂。',ha='center',fontsize=11,color=GRAY)
fig.tight_layout(w_pad=3)
save(fig,12,'三块金属板电势剖面')

# 单束光与双束光记录的是不同事件，不能混用所需长度。
fig,axes=plt.subplots(2,1,figsize=(10,5.7))
for ax in axes:
    ax.set(xlim=(0,10),ylim=(0,3));ax.axis('off')
axes[0].text(.1,2.65,'① 单束光：同一光束，先被前沿挡住，再由后沿放开',fontsize=14)
axes[0].add_patch(Rectangle((1,1),2.6,.9,facecolor='#dae8f1',edgecolor=BLUE,lw=1.5))
axes[0].plot([3.6,3.6],[.55,2.25],color=RED,ls='--',lw=2)
axes[0].annotate('',(1,.6),(3.6,.6),arrowprops=dict(arrowstyle='<->',color=BLUE))
axes[0].text(2.3,.13,'遮光片宽度 d',ha='center',color=BLUE)
axes[0].annotate('运动方向',(5,1.45),(3.85,1.45),arrowprops=dict(arrowstyle='->',color=GRAY),ha='left')
axes[0].text(6.25,1.9,'t₁：前沿到达光束\nt₂：后沿离开光束',fontsize=12,va='top')
axes[0].text(6.25,.6,r'$\bar v=d/(t_2-t_1)$',fontsize=17,color=BLUE)
axes[1].text(.1,2.65,'② 双束光：同一前沿，依次挡住两束光',fontsize=14)
axes[1].add_patch(Rectangle((.5,1),1.3,.9,facecolor='#dae8f1',edgecolor=BLUE,lw=1.5))
for x,label in [(1.8,'光束 1'),(4.8,'光束 2')]:
    axes[1].plot([x,x],[.65,2.25],color=RED,ls='--',lw=2);axes[1].text(x,2.2,label,ha='center',fontsize=11)
axes[1].add_patch(Rectangle((3.5,1),1.3,.9,facecolor='none',edgecolor=BLUE,ls=':',lw=1.5))
axes[1].annotate('',(4.8,.6),(1.8,.6),arrowprops=dict(arrowstyle='<->',color=BLUE))
axes[1].text(3.3,.13,'两束光间距 L',ha='center',color=BLUE)
axes[1].text(6.25,1.9,'t₁：前沿挡住光束 1\nt₂：前沿挡住光束 2',fontsize=12,va='top')
axes[1].text(6.25,.6,r'$\bar v=L/(t_2-t_1)$',fontsize=17,color=BLUE)
fig.subplots_adjust(hspace=.22)
save(fig,4,'单束与双束光计时')

print('已生成 5 组物理关系图（PNG 与 SVG）')
