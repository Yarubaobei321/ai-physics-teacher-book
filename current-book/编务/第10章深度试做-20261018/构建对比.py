#!/usr/bin/env python3
"""只重建本目录的独立文稿与对照；不写现役正文。"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import subprocess, json, re, html, hashlib, os

HERE = Path(__file__).resolve().parent
BOOK = HERE.parent.parent
SOURCE = BOOK / '正文/第10章-一只水槽测出电势/正文.md'
NODE = '/Users/yaril/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
PANDOC = '/opt/homebrew/bin/pandoc'
KATEX = BOOK / '阅读资源/katex/katex.min.js'
old = (HERE / '原稿快照.md').read_text()
new = (HERE / '第10章-深化稿.md').read_text()
baseline = json.loads((HERE / '核验/基线指纹.json').read_text())

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE) == baseline['sha256'] == sha(HERE / '原稿快照.md'), '现役稿或快照已变化，停止，不覆盖基线'

def pandoc(s, target):
    return subprocess.run([PANDOC, '-f', 'markdown+tex_math_dollars', '-t', target, '--katex'], input=s, text=True, capture_output=True, check=True).stdout

def visible(s):
    """按Pandoc语法树取可见文字，排除链接地址和图片文件名；公式计TeX源。"""
    ast = json.loads(pandoc(s, 'json'))
    out=[]
    def walk(x):
        if isinstance(x, dict):
            typ=x.get('t');c=x.get('c')
            if typ == 'Str': out.append(c)
            elif typ in ('Space','SoftBreak','LineBreak'): out.append(' ')
            elif typ in ('Code','CodeBlock','Math'): out.append(c[-1])
            elif typ == 'Figure': walk(c[1]) # 图注只计一次，不重复计同内容的图片替代文字
            elif typ in ('RawInline','RawBlock'): pass
            else:
                for v in x.values(): walk(v)
        elif isinstance(x,list):
            for item in x: walk(item)
    walk(ast['blocks'])
    return ''.join(out)

def counts(s):
    t=visible(s)
    return {'visible_nonspace':len(re.sub(r'\s','',t)), 'visible_han':len(re.findall(r'[\u4e00-\u9fff]',t)), 'source_bytes':len(s.encode()),'source_characters':len(s)}

co,cn=counts(old),counts(new)
for key in ['visible_nonspace','visible_han','source_bytes']: assert cn[key] <= co[key], key
sections_old=re.split(r'(?m)(?=^## )',old)
sections_new=re.split(r'(?m)(?=^## )',new)
assert len(sections_old)==len(sections_new)==8
section_stats=[{'section':i,'old':counts(a),'new':counts(b)} for i,(a,b) in enumerate(zip(sections_old,sections_new))]

# 替换组指向实际旧/新内容。第一节的小幅增量由第二节压缩抵扣；其余在节内完成。
ledger=[
('章首','撤去“学生能背却难说”等无具体样本的概括与重复导读','改为本章可检验的三个问题；明确第11章分工'),
('第一节','撤去三条泛化困难、教参长转述和“框架位置”重复清单','加入三份学案的前测/记录/后测链与未证明的部分；净增由第二节原课堂流程和展示转述抵扣'),
('第二节','合并器材表与改进表；撤去重复的课堂流程表及多组长引文','保留制作取舍、实际图件与找点/检验切换；腾出第一节学案篇幅'),
('第三节','压缩重复原理口头解释；替换笼统“板外也有电场”与读数直接等于水势','补足有效边界、二维条件、板背/板端区别和探针界面项'),
('第四节','长提示词改为条件清单；压缩程序数字和重复单点算例；撤去单看外形即判错误的说法','简短提示词、有效边界换算、图注警示；保留网格漏钢条和箭头反向两例及真实归属'),
('第五节','撤去粗读表、正极损失归因、单点半径追查和重复动画数值；合并重复检查','透视校正表、离散/RMS/外推限制、同探针差值、零示前提与两处教师判断'),
('第六节','合并七步准备、易错表、目标表、流程表之间的重复；撤去笼统“到第三层”','保留40分钟与五布局追问，改用实际学案不足评价解释，明确新安排未实施'),
('第七节','合并跨实验组织原则和重复操作介绍','保留从平行板起步、预测—测量—判别的迁移方法')]

lines=['# 删减清单与新增抵扣','','以下是全章重写的段组对照，不以未改动句子冒充删除。每个新增主题对应被撤去或压缩的原段组；完整两侧文字在 HTML 逐节对照中保留。第一节若净增，由第二节明确腾出的篇幅抵扣，其余段组均在节内缩减。','',
'计数口径：可见非空白字符含章题、小标题、正文、表格、图注和提示词；排除链接地址、图片文件名和 Markdown 标记；公式按 TeX 字符计数。汉字另按 U+4E00—U+9FFF 统计。字节是原始 Markdown 文件 UTF-8 大小。两稿使用同一算法。','',
'|口径|原稿|深化稿|减少|','|---|---:|---:|---:|']
for key,label in [('visible_nonspace','可见非空白字符'),('visible_han','可见汉字'),('source_bytes','源文件字节')]: lines.append(f'|{label}|{co[key]:,}|{cn[key]:,}|{co[key]-cn[key]:,}|')
lines+=['','|段组|原可见字符|新可见字符|净变化|删去/压缩|新增/保留的价值|','|---|---:|---:|---:|---|---|']
for row,stat in zip(ledger,section_stats):
    a=stat['old']['visible_nonspace'];b=stat['new']['visible_nonspace']
    lines.append(f'|{row[0]}|{a:,}|{b:,}|{b-a:+,}|{row[1]}|{row[2]}|')
lines += ['','正文净减少不代表每句话都应再缩短。保留了器材规格、接线切换、印刷校准、测量条件和课堂追问，压缩主要来自重复介绍和没有证据支撑的概括。',
'','单点原稿中的16/45/74 mm与11/25/56 mm对照不在本章重复；第11章现役文件未改。新稿所有提示词均为本书整理的简短示例。']
(HERE/'删减清单.md').write_text('\n'.join(lines)+'\n')

formula_count=0
def render(s, origin, prefix):
    global formula_count
    result=pandoc(s,'html5')
    # 编译公式而非依赖页面加载后执行，语法错误立即停止。
    matches=list(re.finditer(r'<span class="math (inline|display)">([\s\S]*?)</span>',result))
    if matches:
        items=[[html.unescape(m.group(2)),m.group(1)=='display'] for m in matches]
        js="const k=require(process.argv[1]);const fs=require('fs');process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(x=>k.renderToString(x[0],{displayMode:x[1],throwOnError:true,strict:'ignore',trust:false,output:'htmlAndMathml'}))));"
        r=subprocess.run([NODE,'-e',js,str(KATEX)],input=json.dumps(items),capture_output=True,text=True,check=True)
        rendered=json.loads(r.stdout)
        for m,replacement in reversed(list(zip(matches,rendered))): result=result[:m.start()]+replacement+result[m.end():]
        formula_count+=len(items)
    # 所有标题锚点加局部前缀，全文左右对照不会出现重复id。
    result=re.sub(r'\bid="([^"]+)"',lambda m:'id="'+prefix+m.group(1)+'"',result)
    result=re.sub(r'href="#([^"]+)"',lambda m:'href="#'+prefix+m.group(1)+'"',result)
    def paths(m):
        attr,url=m.group(1),html.unescape(m.group(2));u=urlsplit(url)
        if not url or url.startswith('#') or u.scheme or url.startswith('//'): return m.group(0)
        target=(origin/unquote(u.path)).resolve()
        rel=os.path.relpath(target,HERE)
        if u.fragment:rel+='#'+u.fragment
        return attr+'="'+html.escape(rel,quote=True)+'"'
    result=re.sub(r'\b(src|href)="([^"]+)"',paths,result)
    result=re.sub(r'<table>([\s\S]*?)</table>',r'<div class="table-wrap"><table>\1</table></div>',result)
    return result

CSS='''
:root{--ink:#22323b;--muted:#62737a;--line:#d8e2e5;--blue:#17556d;--paper:#fff;--bg:#f3f5f4;--warm:#f8f2e6}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:85px}body{margin:0;color:var(--ink);background:var(--bg);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.85}a{color:var(--blue);text-underline-offset:4px}header{max-width:1300px;margin:auto;padding:54px 30px 26px}header h1{font-size:clamp(28px,4vw,44px);line-height:1.35;margin:12px 0}header p{max-width:850px;margin:10px 0}.eyebrow{color:var(--blue);font-size:13px;letter-spacing:.15em}.nav{position:sticky;top:0;z-index:3;display:flex;gap:20px;flex-wrap:wrap;padding:13px 30px;background:#fffffff5;border-block:1px solid var(--line)}.nav a{text-decoration:none;font-size:14px}.shell{max-width:1360px;margin:auto;padding:24px 30px 70px}.paper{background:var(--paper);border:1px solid var(--line);padding:30px;margin:0 0 24px}.prose{font-size:17px}.prose p{margin:1em 0}.prose h1{font-size:30px;line-height:1.45}.prose h2{font-size:25px;margin:2.1em 0 .8em;line-height:1.5}.prose h3{font-size:20px;margin:1.8em 0 .7em}.prose img{display:block;max-width:100%;height:auto;max-height:760px;object-fit:contain;margin:22px auto}.prose figure{margin:30px 0}.prose figcaption{font-size:14px;color:var(--muted);line-height:1.75;margin-top:12px}.prose blockquote{border-left:3px solid #6796a7;padding:7px 20px;background:#f2f7f8;margin:24px 0}.prose pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f6;padding:16px;font-size:14px}.prose code{overflow-wrap:anywhere;font-size:.9em}.table-wrap{overflow-x:auto;margin:20px 0}table{width:100%;border-collapse:collapse;font-size:14px;line-height:1.7}th,td{padding:11px 13px;border:1px solid var(--line);vertical-align:top;text-align:left}th{background:#eaf1f3}table p{margin:0!important}td{min-width:95px}.katex-display{overflow-x:auto;overflow-y:hidden;padding:8px 0}.katex{font-size:1.08em}.comparison{display:grid;grid-template-columns:1fr 1fr;gap:25px}.column{min-width:0}.column .prose{font-size:16px}.column .prose h2{font-size:23px}.label{font-size:13px;font-weight:600;letter-spacing:.08em;border-bottom:2px solid var(--line);padding:7px 0}.oldlabel{color:#79644b;border-color:#c6b59e}.newlabel{color:var(--blue);border-color:#5a91a6}.small{color:var(--muted);font-size:14px}.badge{display:inline-block;padding:3px 10px;background:#e4eff2;color:var(--blue);font-size:12px;border-radius:3px}.notice{background:var(--warm);border-left:3px solid #c49f5e;padding:16px 20px}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:22px 0}.metric{background:#fff;padding:20px;border:1px solid var(--line)}.metric b{display:block;font-size:27px;line-height:1.4}.metric span{font-size:13px;color:var(--muted)}details{border:1px solid var(--line);background:white;margin:14px 0}summary{padding:18px 22px;font-weight:600;cursor:pointer}details>.inner{padding:0 24px 26px}button{font:inherit;font-size:14px;border:1px solid var(--line);background:white;padding:8px 14px;cursor:pointer}.change{border-top:1px solid var(--line);padding:25px 0}.change h3{margin:0 0 14px;font-size:21px}.change-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.quote{background:#f4f6f6;padding:14px 17px}.quote p{margin:6px 0}.source{font-size:14px}.reading{max-width:850px;margin:auto}.reading .paper{padding:35px 48px}.reading header{padding-inline:0}.toc{font-size:15px}.toc ol{padding-left:24px}footer{font-size:13px;color:var(--muted);padding-top:20px}.oldnote{color:#825d30;font-size:13px;margin-bottom:12px}@media(max-width:850px){.comparison,.change-grid{grid-template-columns:1fr}.shell{padding:18px 14px 45px}header{padding:32px 20px 20px}.paper{padding:22px}.reading .paper{padding:24px}.metrics{grid-template-columns:1fr}.nav{padding:10px 15px;gap:12px}.prose{font-size:16px}.oldnote{border-bottom:1px dashed #c6b59e;padding-bottom:10px}}@media print{.nav,.controls{display:none}body{background:white}.shell{max-width:none;padding:0}.paper,details{border:0}.comparison,.change-grid{display:block}.column{break-before:page}img{max-height:170mm!important}h2,h3{break-after:avoid}a{color:inherit}.metrics{display:none}}
'''

def doc(title,body):
    return '<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'+html.escape(title)+'</title><link rel="stylesheet" href="../../阅读资源/katex/katex.min.css"><style>'+CSS+'</style></head><body>'+body+'</body></html>'

full_new=render(new,HERE,'read-')
toc=[]
for m in re.finditer(r'<h2 id="([^"]+)">([\s\S]*?)</h2>',full_new):toc.append('<li><a href="#'+m.group(1)+'">'+m.group(2)+'</a></li>')
draft='<div class="reading"><header><div class="eyebrow">第 10 章 · 独立深化候选</div><p><a href="第10章-深化对比.html">查看原稿对照与证据</a> · <a href="第10章-深化稿.md">Markdown 源稿</a></p><p class="small">供作者审读；未合并现役全书。</p></header><div class="paper toc"><ol>'+''.join(toc)+'</ol></div><article class="paper prose">'+full_new+'</article></div>'
(HERE/'第10章-深化稿.html').write_text(doc('第10章｜独立深化稿',draft))

changes=[
('学生困难由概括改为原件所见','教学中常见的困难有三个','三份后测都没有展开理由；A/B 预测图未辨清，不能判为不会画','撤去没有样本支持的普遍判断；把学生已经会的、未交代的和不能判断的分开。', '学生学案摘录与文献检索.md','三份扫描：第1页记录表与分享栏，第2页前后测'),
('平行板从粗读改为透视校正','约 +61、+13、−39 mm；数值还不可靠','+57.9、+9.9、−41.2 mm；列标准差、拟合40.3 V/m与RMS 0.061 V','位置证据更准确，同时明确统计离散与总不确定度不同。','核验/平行板测点透视校正-输出.txt','原照取点的校正与拟合输出'),
('撤去“正极承担主要压降”的定位','比较电极金属与紧贴电极的水之间的读数差，确定哪一侧存在较大的界面压降','同一探针两次读数相减估计水层电压；不能据近负极读零分配两侧压降','探针自身也有界面项；单个仪表读数不能完成原稿宣称的分侧判断。','已核发现-交接.md','第2条；候选第五节三步补测'),
('“板外”改成明确的空间位置','板外也有电场；等势线和电场线都弯曲','钢条背后中部约0.3%，板端延长区域的一个点约97%；B图方向线不表示强弱','保留原印刷图供辨析，避免用相同密度方向线暗示相同场强。','核验/平行板板外场强-输出.txt','板背、端头与板间取样值'),
('底图的U改为水层有效电势差','U 由学生测出自己那节电池的电压后填写','用 V(P)=V₋+(V₊−V₋)u(P) 对应实际读数','消除第四节开头与后文有效边界解释的冲突；前提为探针偏置稳定。','已核发现-交接.md','第2条；候选第三至五节'),
('教师判断保留，单点追查移出','本章列16/45/74 mm实测和11/25/56 mm预测，继续讨论原因','保留“没怎么能看得出来”的课堂判断，原因指向第11章','压缩重复分析；区分承认照片不支持结论，与已经查明原因。','深度卡.md','字幕371—372、383；时间线第25段'),
('AI协作保留实际归属','长提示词及较多程序数值，文中带具体工具名','只说AI；短提示配真实尺寸；网格和箭头错误明确为协作复查发现','保持可跟做，又不制造作者本人发现错误的经历。','核验记录.md','A规格核查、作者访谈与原稿记录'),
('学习结果不再超过学案能证明的程度','两平行板组的两位学生都到了第三层','B组写了平行等距，但未显式写等差条件；三份后测理由都未展开','展示片段与纸面作答不是同一层证据，不能由选择正确推成完整理解。','学生学案摘录与文献检索.md','B组第1页；三份第2页后测第2题')]

change_html=''
for i,(title,a,b,why,ref,loc) in enumerate(changes,1):
    change_html+=f'<section class="change" id="change-{i}"><h3>{i:02d}　{title}</h3><div class="change-grid"><div class="quote"><span class="small">原稿摘句或概括</span><p>{html.escape(a)}</p></div><div class="quote"><span class="small">深化稿的处理</span><p>{html.escape(b)}</p></div></div><p>{why}</p><p class="source">证据：<a href="{ref}">{loc}</a></p></section>'

comp=''
for i,(a,b) in enumerate(zip(sections_old,sections_new)):
    title='章首' if i==0 else ledger[i][0]+' · '+b.splitlines()[0].lstrip('# ')
    stat=section_stats[i];diff=stat['new']['visible_nonspace']-stat['old']['visible_nonspace']
    comp+=f'<details class="section-compare" id="section-{i}"><summary>{html.escape(title)} <span class="small">｜可见字符 {diff:+,}</span></summary><div class="inner"><p class="small">{ledger[i][1]} → {ledger[i][2]}</p><div class="comparison"><div class="column"><div class="label oldlabel">原稿 · 本轮开始时快照</div><div class="oldnote">保留原有说法用于比较，不代表本候选继续采用。</div><div class="prose">{render(a,SOURCE.parent,f"old{i}-")}</div></div><div class="column"><div class="label newlabel">深化稿 · 独立候选</div><div class="prose">{render(b,HERE,f"new{i}-")}</div></div></div></div></details>'

docs=''
for name,label in [('深度卡.md','深度卡'),('学生学案摘录与文献检索.md','学生原件与本地文献'),('核验记录.md','核验记录：含未通过项'),('证据缺口.md','证据缺口与作者裁决')]:
    docs+=f'<details><summary>{label}</summary><div class="inner prose"><p class="small"><a href="{name}">打开源文件</a></p>{render((HERE/name).read_text(),HERE,"doc-"+str(len(docs))+"-")}</div></details>'
percent=(1-cn['visible_nonspace']/co['visible_nonspace'])*100
body=f'''<header id="top"><div class="eyebrow">不会编程的物理老师，能用 AI 做成什么</div><h1>第 10 章：更深，篇幅更少</h1><p>以三份学生学案、平行板测点和独立计算，重新区分“看见了什么”“怎样判断”与“证据还不足以说明什么”。</p><p><span class="badge">独立候选 · 未合并</span>　<a href="第10章-深化稿.html">先读完整新稿 →</a></p></header>
<nav class="nav"><a href="#changes">关键变化</a><a href="#comparison">逐节全文对照</a><a href="#counts">字数与删减</a><a href="#evidence">证据与缺口</a><a href="review.md">一页说明</a></nav>
<main class="shell"><div class="metrics"><div class="metric"><span>可见非空白字符</span><b>{co['visible_nonspace']:,} → {cn['visible_nonspace']:,}</b></div><div class="metric"><span>正文缩短</span><b>{percent:.1f}%</b></div><div class="metric"><span>覆盖范围</span><b>7 节 · 6 页学案</b></div></div>
<div class="notice">没有把物理核验写成学习效果。三份后测都写了“不能”，但没有展开理由；本地未找到可直接支持原稿三个困难的迷思实证研究。上述缺口在候选和审读记录中保留。</div>
<section class="paper" id="changes"><h2>先看这八处实质变化</h2>{change_html}</section>
<section id="comparison"><h2>逐节全文对照</h2><p class="small">两侧均为全文，不是仅展示有利片段。逐节展开阅读；原稿保留本轮开始时的版本，原有图件未重绘。</p><div class="controls"><button id="expand" type="button">展开全部七节与章首</button> <button id="collapse" type="button">收起全文对照</button></div>{comp}</section>
<section class="paper prose" id="counts">{render((HERE/'删减清单.md').read_text(),HERE,'counts-')}</section>
<section id="evidence"><h2>证据、核验与需要作者判断的地方</h2>{docs}</section>
<footer>现役正文未改。仅完成文件、资源、锚点与公式等基本结构检查；按要求未作浏览器截图验收。<a href="核验/文件核验结果.json">检查明细</a> · <a href="第10章-深化稿.html">独立文稿</a> · <a href="原稿快照.md">原稿快照</a></footer></main>
<script>document.getElementById('expand').addEventListener('click',()=>document.querySelectorAll('.section-compare').forEach(x=>x.open=true));document.getElementById('collapse').addEventListener('click',()=>document.querySelectorAll('.section-compare').forEach(x=>x.open=false));function reveal(){{let x=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(x){{let p=x;while(p){{if(p.tagName==='DETAILS')p.open=true;p=p.parentElement;}}}}}}window.addEventListener('hashchange',reveal);reveal();</script>'''
(HERE/'第10章-深化对比.html').write_text(doc('第10章｜深化对比与证据',body))

class Check(HTMLParser):
    def __init__(self):super().__init__();self.refs=[];self.ids=[];self.stack=[];self.errors=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if 'id' in d:self.ids.append(d['id'])
        for k in ('src','href'):
            if k in d:self.refs.append(d[k])
        if tag in ('article','section','details','figure','table','nav','main'):self.stack.append(tag)
    def handle_endtag(self,tag):
        if tag in ('article','section','details','figure','table','nav','main'):
            if not self.stack or self.stack.pop()!=tag:self.errors.append('标签配对:'+tag)

errors=[];checked=0
for f in [HERE/'第10章-深化稿.html',HERE/'第10章-深化对比.html']:
    parser=Check();parser.feed(f.read_text())
    if len(parser.ids)!=len(set(parser.ids)):errors.append(f.name+':重复id')
    errors+=parser.errors
    if parser.stack:errors.append(f.name+':未闭合标签')
    for url in parser.refs:
        u=urlsplit(html.unescape(url))
        if u.scheme or url.startswith('//'):continue
        target=(f.parent/unquote(u.path)).resolve() if u.path else f
        # 检查结果文件将在本次验证结束时生成。
        if target==HERE/'核验/文件核验结果.json':continue
        checked+=1
        if not target.exists():errors.append(f.name+':路径失效:'+url)
        if not u.path and u.fragment and unquote(u.fragment) not in parser.ids:errors.append(f.name+':锚点失效:'+url)

plain=visible(new)
for term in ['WorkBuddy','Codex','Claude','DeepSeek','Deepseek','GPT-']:
    if term in plain:errors.append('新稿出现工具/模型名:'+term)
assert sha(SOURCE)==baseline['sha256']
report={'status':'通过' if not errors else '未通过','scope':'文件、链接、锚点、公式与字数；无浏览器截图或实物/课堂验证','original_sha256':sha(SOURCE),'snapshot_sha256':sha(HERE/'原稿快照.md'),'candidate_sha256':sha(HERE/'第10章-深化稿.md'),'old':co,'new':cn,'section_counts':section_stats,'formula_render_operations':formula_count,'local_links_checked':checked,'errors':errors}
(HERE/'核验/文件核验结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
if errors:raise SystemExit(1)
