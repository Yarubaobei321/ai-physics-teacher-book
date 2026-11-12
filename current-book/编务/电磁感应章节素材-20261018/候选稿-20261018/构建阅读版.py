#!/usr/bin/env python3
"""生成本目录独立候选阅读页及两幅解释图；不调用全书构建。"""
from pathlib import Path
import subprocess,json,re,html,hashlib,xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
P=Path(__file__).resolve().parent
BOOK=P.parents[2]
INK='#203747';BLUE='#285b79';MUTED='#526674'
def text(x,y,s,size=25,fill=INK,weight='400'):
 return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}">{html.escape(s)}</text>'
def box(x,y,w,h,title,detail):
 return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="#f3f7f9" stroke="#c9d6df"/>'+text(x+22,y+36,title,27,INK,'600')+text(x+22,y+72,detail,21,MUTED)
def arrow(x1,y1,x2,y2):
 return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{BLUE}" stroke-width="3" fill="none" marker-end="url(#arrow)"/>'
def svg(content,w,h,title):
 return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img"><title>{html.escape(title)}</title><defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="{BLUE}"/></marker></defs><rect width="100%" height="100%" fill="white"/><g font-family="PingFang SC,Microsoft YaHei,sans-serif">{content}</g></svg>'
rows=[('怎样改变匝数？','同时保持位置与运动条件','选择线圈接线柱','核对接入绕组与实际匝数'),('怎样改变磁通量的条件？','区分操作量与理论量','改变小磁铁组合','数量、排布和距离都需要说明'),('怎样控制并知道运动快慢？','调节与测量分别安排','调速装置＋转速仪','用实际转速读数记录条件'),('怎样保存快速变化的电压？','使信号可以回看和比较','微电压传感器＋电脑','保留波形，并说明取值方法')]
c=text(36,46,'定量探究的要求',30,INK,'600')+text(600,46,'对应的实验安排',30,INK,'600')
for i,(a,b,d,e) in enumerate(rows):
 y=76+i*125;c+=box(30,y,465,100,a,b)+arrow(510,y+50,565,y+50)+box(585,y,570,100,d,e)
(P/'图件/图01-教学问题与实验安排.svg').write_text(svg(c,1190,600,'教学问题与实验安排'))
c=text(30,42,'控制运动、测量转速、记录电压',30,INK,'600')
c+=box(30,80,300,100,'调速装置','改变电机运行状态')+box(430,80,330,100,'电机带动磁铁','沿固定路径转动')+box(850,80,310,100,'固定线圈','磁通量随相对位置改变')
c+=arrow(330,130,430,130)+arrow(760,130,850,130)
c+=box(430,265,330,100,'转速仪','测量实际转速')+box(850,265,310,100,'微电压传感器＋电脑','记录电压随时间的变化')
c+=arrow(595,180,595,265)+arrow(1005,180,1005,265)
c+=box(430,455,730,100,'对应同一次实验条件','同时保存：匝数、磁铁组合、位置、转速、波形与取值规则')
c+=arrow(595,365,595,455)+arrow(1005,365,1005,455)
c+=text(34,300,'控制量：旋钮设置',21,MUTED)+text(34,340,'测量量：转速、端电压',21,MUTED)+text(34,380,'解释量：磁通量变化率',21,MUTED)
c+=text(30,608,'功能关系示意；箭头不表示电气接线。',20,MUTED)
(P/'图件/图07-控制与测量关系.svg').write_text(svg(c,1190,640,'运动控制与两条测量路径'))

def walk(v):
 if isinstance(v,dict):
  yield v
  for k in list(v):yield from walk(v[k])
 elif isinstance(v,list):
  for x in v:yield from walk(x)
def run(args,data=None):return subprocess.check_output(args,input=data,text=True)
math_count=0
def convert(name):
 global math_count
 src=(P/name).read_text()
 ast=json.loads(run(['pandoc','-f','markdown+raw_html+tex_math_dollars-implicit_figures','-t','json'],src))
 nodes=[n for n in walk(ast) if n.get('t')=='Math']
 vals=[[n['c'][1],n['c'][0]['t']=='DisplayMath'] for n in nodes]
 js="const fs=require('fs'),k=require(process.argv[1]);let a=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(a.map(x=>k.renderToString(x[0],{displayMode:x[1],throwOnError:true,strict:'ignore',output:'htmlAndMathml'}))));"
 if nodes:
  rendered=json.loads(run(['node','-e',js,str(BOOK/'阅读资源/katex/katex.min.js')],json.dumps(vals)))
  for n,s in zip(nodes,rendered):n.clear();n.update(t='RawInline',c=['html',s])
  math_count+=len(nodes)
 out=run(['pandoc','-f','json','-t','html5','--wrap=none'],json.dumps(ast))
 out=re.sub(r'<table>',r'<div class="table-wrap"><table>',out).replace('</table>','</table></div>')
 out=re.sub(r'<img ([^>]*?)src="([^"]+)"([^>]*)>',lambda m:f'<a class="image-link" href="{m[2]}" target="_blank" rel="noopener"><img {m[1]}src="{m[2]}"{m[3]}></a>',out)
 return out
body=convert('正文.md');pending=convert('待开展实践.md')
headings=re.findall(r'<h2 id="([^"]+)">(.*?)</h2>',body)
nav=''.join(f'<a href="#{i}">{t}</a>' for i,t in headings)
css='''
:root{--ink:#263744;--blue:#285b79;--muted:#61727d;--line:#dbe3e7;--paper:#fff;--canvas:#f1f4f5}*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--canvas);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}a{color:var(--blue);text-underline-offset:3px}a:focus-visible{outline:2px solid var(--blue);outline-offset:4px}nav{position:fixed;top:0;bottom:0;left:0;width:250px;background:white;border-right:1px solid var(--line);padding:32px 22px;overflow:auto}nav strong{display:block;font-size:16px;margin:0 0 7px}nav small{display:block;color:var(--muted);line-height:1.7;margin-bottom:26px}nav a{display:block;text-decoration:none;padding:10px 0;font-size:14px;line-height:1.6}nav .aux{border-top:1px solid var(--line);margin-top:20px;padding-top:12px}main{margin-left:250px;padding:35px 34px 90px}.banner{max-width:950px;margin:0 auto 20px;display:flex;gap:18px;align-items:center;flex-wrap:wrap;font-size:13px;color:var(--muted)}.banner span{margin-right:auto}article,.pending{max-width:950px;margin:auto;background:white;padding:52px 62px;font-size:18px;line-height:1.95;overflow-wrap:break-word}h1{font-size:33px;line-height:1.5;margin:0 0 40px;font-weight:650;letter-spacing:.02em}h2{font-size:27px;line-height:1.6;margin:54px 0 24px;padding-top:12px;border-top:1px solid var(--line);scroll-margin-top:20px}h3{font-size:21px;line-height:1.6;margin:32px 0 16px}p{margin:0 0 1.05em}figure{margin:30px 0 36px;padding:18px 0 22px;border-bottom:1px solid var(--line)}img{display:block;max-width:100%;height:auto;margin:auto}figcaption{font-size:14px;line-height:1.85;color:var(--muted);margin-top:15px}figcaption strong{color:var(--ink)}.image-link{display:block;cursor:zoom-in;text-decoration:none}.image-pair{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:center}.image-pair img{max-height:480px;width:100%;object-fit:contain}.panel-label{font-size:14px;text-align:center;margin:10px 0 0;color:var(--muted)}.portrait{max-width:420px;max-height:540px;object-fit:contain}.worksheet{max-width:600px}.wave-stack>div+div{margin-top:22px}.rotate-frame{position:relative;aspect-ratio:4/3;width:100%;overflow:hidden}.rotate-frame .image-link{position:absolute;inset:0}.rotate-frame img{position:absolute;left:50%;top:50%;width:75%;max-width:none;max-height:none;transform:translate(-50%,-50%) rotate(-90deg)}.table-wrap{overflow:auto;margin:26px 0}table{width:100%;border-collapse:collapse;font-size:15px;line-height:1.75}th,td{border:1px solid var(--line);padding:11px 12px;vertical-align:top}th{background:#f0f5f7;font-weight:600;text-align:left}blockquote{margin:22px 0;background:#f1f6f8;padding:20px 24px;border-left:3px solid #6d93a8}blockquote p:last-child{margin:0}.katex{font-size:1.06em}.katex-display{overflow-x:auto;overflow-y:hidden;padding:10px 0}.pending{margin-top:32px;border-top:5px solid #c69e58}.pending h1{font-size:28px}.pending h2{font-size:23px}.status{color:#785c2b;font-size:14px;font-weight:600;margin-bottom:20px}.foot{max-width:950px;margin:20px auto;color:var(--muted);font-size:13px;line-height:1.8}ul,ol{padding-left:1.5em}
@media(max-width:1100px){nav{width:210px;padding:25px 16px}main{margin-left:210px;padding:25px 20px 60px}article,.pending{padding:36px;font-size:17px}h1{font-size:29px}}
@media(max-width:760px){nav{position:static;width:auto;border-bottom:1px solid var(--line);padding:20px}nav small{margin-bottom:10px}nav a{display:inline-block;margin-right:16px;font-size:13px;padding:4px 0}nav .aux{margin-top:10px}main{margin:0;padding:18px 12px 45px}article,.pending{padding:27px 20px}h1{font-size:27px}h2{font-size:23px}h3{font-size:20px}.image-pair{gap:14px}.image-pair img{max-height:350px}table{font-size:13px;min-width:560px}}
@media print{nav,.banner,.foot{display:none}main{margin:0;padding:0}body{background:white}article,.pending{padding:0;max-width:none;font-size:11pt;line-height:1.8}h1{font-size:22pt}h2{font-size:17pt;break-after:avoid}h3{font-size:13pt;break-after:avoid}figure{break-inside:avoid}figure img{max-height:150mm;object-fit:contain}figcaption{font-size:9pt}.pending{break-before:page;padding-top:10mm}table{font-size:9pt}.table-wrap{overflow:visible}a{color:inherit;text-decoration:none}@page{size:A4;margin:19mm}}
'''
page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>电磁感应章节｜独立候选稿</title><link rel="stylesheet" href="../../../阅读资源/katex/katex.min.css"><style>{css}</style></head><body><nav aria-label="章节导航"><strong>法拉第电磁感应实验</strong><small>前五节正文 · 独立候选<br>2026-10-18</small>{nav}<div class="aux"><a href="#pending">待开展的 AI 实践</a><a href="review.md">作者审读说明与图源</a><a href="../电磁感应章节详细写作提纲.md">写作提纲</a></div></nav><main><div class="banner"><span>独立候选稿 · 未合并入书</span><a href="正文.md">正文源稿</a><a href="待开展实践.md">待开展实践</a><a href="review.md">审读说明</a></div><article>{body}</article><section class="pending" id="pending"><p class="status">单独保留的实践设计 · 尚未开展</p>{pending}</section><p class="foot">图片可点击查看原尺寸。真实照片与波形直接来自王硕老师的材料；图 1、图 7 为依据材料整理的解释图。正文与待开展实践分别保存，可独立修订。</p></main></body></html>'''
(P/'阅读.html').write_text(page)
class Check(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.ids=[];self.fig=[];self.images=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if tag=='figure':self.fig.append(a.get('id'))
  if tag=='img':self.images.append(a.get('src'))
  for k in ['href','src']:
   if a.get(k):self.links.append(a[k])
c=Check();c.feed(page)
missing=[]
for s in c.links:
 u=urlsplit(s)
 if u.scheme:continue
 if u.path and not (P/unquote(u.path)).exists():missing.append(s)
 if not u.path and u.fragment and unquote(u.fragment) not in c.ids:missing.append(s)
for f in (P/'图件').glob('*.svg'):ET.parse(f)
old=json.loads((P/'现役稿只读指纹.json').read_text())
changed=[p for p,h in old.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
result={'figures':len(c.fig),'image_placements':len(c.images),'math_expressions':math_count,'missing':missing,'duplicate_ids':len(c.ids)-len(set(c.ids)),'unchanged_current_book_files':len(old)-len(changed),'changed_current_book_files':changed,'scope':'静态结构、引用路径、公式编译、现役稿指纹；未作浏览器截图或移动端视觉验收'}
(P/'构建核对.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
