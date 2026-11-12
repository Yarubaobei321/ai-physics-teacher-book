from 执行 import *
import re,subprocess
src=Path('/Users/yaril/个人文档/3 写作/四篇论文双版本-2026-09-01/01-生成式人工智能网页作业的物理核查与验收要求——基于25份高中生提交作品的分析/图件')
dst=P/'正文/第20章-审学生的AI作品/assets'
# 更宽的步骤框，文字留足左右空白，回退线独立位于框底与说明之间
s='''<svg xmlns="http://www.w3.org/2000/svg" width="1720" height="400" viewBox="0 0 1720 400"><title>核查顺序与定向退回</title><defs><marker id="arrow" markerWidth="9" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L9,4 L0,8Z" fill="#273548"/></marker><style>text{font-family:"PingFang SC","Microsoft YaHei",sans-serif;fill:#172234}.head{font-size:27px;font-weight:600}.body{font-size:25px}.arrow{fill:none;stroke:#273548;stroke-width:2;marker-end:url(#arrow)}</style></defs><rect width="1720" height="400" fill="white"/>'''
items=[('1 对象与条件','系统、参考、理想化','数据怎样得到','#e8f2fb'),('2 公式、数值与单位','手算、单位、数量级','公式适用条件','#e8f6ef'),('3 参数载入','按钮和滑块','是否改变模型输入','#fff3df'),('4 事件状态','初态、末态','是否属于同一事件','#f1edfa'),('5 表达一致','动画、图、表、文字','同条件、同一时刻','#e5ebf3')]
for i,(a,b,c,color) in enumerate(items):
 x=20+i*340
 s+=f'<g transform="translate({x} 25)"><rect width="310" height="175" fill="white" stroke="#273548" stroke-width="2"/><rect width="310" height="54" fill="{color}"/><text x="15" y="36" class="head">{a}</text><text x="20" y="100" class="body">{b}</text><text x="20" y="143" class="body">{c}</text></g>'
 if i<4:s+=f'<path d="M{x+313} 112H{x+335}" class="arrow"/>'
s+='''<path d="M1535 207V255H855V208" class="arrow" stroke-dasharray="8 7"/><text x="1195" y="305" text-anchor="middle" class="body">图表冲突源于参数未载入 → 返回第 3 步</text><text x="20" y="371" font-size="25">遇到矛盾，先退回最早失效的环节，再继续后面的物理判断。</text></svg>'''
(dst/'核查顺序与退回-v2.svg').write_text(s)
t=(src/'图2-P22按钮标示与实际参数.svg').read_text().replace('Noto Sans SC','PingFang SC').replace('默认算例的公式需另行评价','默认算例本身另算')
for n in [1,2]:
 for v in ['m','v']:t=t.replace(v+str(n).translate(str.maketrans('12','₁₂')),v+f'<tspan baseline-shift="sub" font-size="23">{n}</tspan>')
t=t.replace('viewBox="0 0 1160 455"','width="1160" height="455" viewBox="0 0 1160 455"')
(dst/'P22按钮与实际参数-v2.svg').write_text(t)
node='/Users/yaril/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node';sharp='/Users/yaril/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp'
for name in ['核查顺序与退回','P22按钮与实际参数']:
 p=dst/(name+'-v2.svg');out=dst/(name+'-v2.png')
 subprocess.run([node,'-e',"require(process.argv[1])(process.argv[2],{density:144}).png().toFile(process.argv[3])",sharp,str(p),str(out)],check=True)
 edit(dst.parent/'正文.md',[(f'assets/{name}.png',f'assets/{name}-v2.png')])
print('两张审核图已另存为2倍PNG与可编辑SVG')
