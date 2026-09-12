from pathlib import Path
import html,re,math,json,base64,shutil
ROOT=Path(__file__).resolve().parents[1]
AS=ROOT/'assets';AS.mkdir(exist_ok=True)

def svg_file(name,body,w=1120,h=420):
    txt=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" rx="14" fill="#f2f6f2"/><g font-family="Noto Sans CJK SC,PingFang SC,Microsoft YaHei,sans-serif" fill="#24383e">{body}</g></svg>'''
    (AS/name).write_text(txt,encoding='utf-8');return txt

def text(x,y,t,size=22,fill=None,anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"'+(f' fill="{fill}"' if fill else '')+'>'+html.escape(t)+'</text>'

b=text(42,48,'同一个计数点，可以同时服务于两个速度估计',27)
b+='<line x1="105" y1="180" x2="1010" y2="180" stroke="#597576" stroke-width="3"/>'
for x,label,num in [(120,'A前一点','0.00 cm'),(380,'A / B前一点','1.82 cm'),(665,'B / A后一点','4.00 cm'),(980,'B后一点','6.54 cm')]:
    b+=f'<circle cx="{x}" cy="180" r="10" fill="#196b69"/>'+text(x,140,label,22,anchor='middle')+text(x,223,num,22,anchor='middle')
b+='<path d="M120 263 v18 H665 v-18" fill="none" stroke="#196b69" stroke-width="3"/>'+text(392,315,'A处估速：跨越2T',22,anchor='middle')
b+='<path d="M380 333 v18 H980 v-18" fill="none" stroke="#ad7634" stroke-width="3"/>'+text(680,388,'B处估速：跨越2T',22,anchor='middle')
svg_file('01_shared_points.svg',b)
b=text(40,42,'在四个时刻，逐项核对同一个状态',27)
for j,(phase,xx,v,a) in enumerate([('0',.2,'0','−0.80'),('T/4',0,'−0.40','0'),('T/2',-.2,'0','+0.80'),('3T/4',0,'+0.40','0')]):
    left=35+j*275;center=left+125;cx=center+xx*340
    b+=f'<rect x="{left}" y=" seventy" width="250" height="270" fill="none"/>' if False else ''
    b+=f'<line x1="{left+15}" y1="195" x2="{left+245}" y2="195" stroke="#bac9c4" stroke-width="3"/><line x1="{center}" y1="120" x2="{center}" y2="205" stroke="#9db2aa" stroke-dasharray="5 5"/>'
    b+=f'<circle cx="{cx}" cy="164" r="23" fill="#196b69"/>'+text(center,98,phase,25,anchor='middle')+text(center,242,f'x = {xx:+.2f} m',21,anchor='middle')+text(center,283,f'v = {v} m/s',21,anchor='middle')+text(center,324,f'a = {a} m/s²',21,anchor='middle')
b+=text(560,387,'新编理想示例：m=1 kg，k=4 N/m，A=0.20 m；T=π s，E=0.080 J',20,anchor='middle')
svg_file('02_spring_states.svg',b)
b=''
for j,(title,a,top,val) in enumerate([('初始状态',0,10,'2.4 V'),('只上移下板',2,10,'1.5 V'),('只下移上板',0,8,'3.0 V')]):
    x=36+j*365;y=lambda q:320-24*q
    b+=text(x+158,43,title,26,anchor='middle')
    b+=f'<rect x="{x+33}" y="{y(top)}" width="250" height="{y(a)-y(top)}" fill="#e3eee7"/><line x1="{x+20}" y1="{y(top)}" x2="{x+295}" y2="{y(top)}" stroke="#b47a38" stroke-width="8"/><line x1="{x+20}" y1="{y(a)}" x2="{x+295}" y2="{y(a)}" stroke="#527c8e" stroke-width="8"/>'
    b+=f'<circle cx="{x+157}" cy="{y(4)}" r="9" fill="#a63930"/>'+text(x+170,y(4)-14,'p=4 cm',21)
    b+=text(x+32,y(top)+29,f'b={top} cm · U=6 V',18)+text(x+32,y(a)-17,f'a={a} cm · 0 V',18)
    b+=text(x+158,376,'V(p) = '+val,27,anchor='middle')
b+=text(560,426,'观察点固定；两种移动都减小间距，电势变化却相反。以上为理想模型值。',20,anchor='middle')
svg_file('03_fixed_potential.svg',b,h=460)
b=text(40,43,'充电1秒后切换放电：电压接得上，电流可改向',27)
b+='<path d="M80 80 V325 H1020" fill="none" stroke="#8ea39a" stroke-width="2"/>'
pts=[]
for i in range(241):
    t=i/80;V=5*(1-math.exp(-t)) if t<=1 else 5*(1-math.exp(-1))*math.exp(-(t-1));pts.append(f'{80+t*290:.3f},{325-V*62:.3f}')
b+=f'<polyline points="{" ".join(pts)}" fill="none" stroke="#196b69" stroke-width="4"/>'
b+='<path d="M370 75 V325" stroke="#b57d39" stroke-dasharray="7 6" stroke-width="2"/>'+text(389,99,'切换，VC不跳变',22)
for t,V in [(1,5*(1-math.exp(-1))),(2,5*(math.exp(-1)-math.exp(-2)))]:
    x=80+t*290;y=325-V*62;b+=f'<circle cx="{x}" cy="{y}" r="7" fill="#b57d39"/>'+text(x+12,y-16,f'{V:.3f} V',22)
for t in range(4):b+=text(80+t*290,354,str(t)+' s',19,anchor='middle')
b+=text(28,78,'VC',22)+text(560,395,'新编理想示例：U=5 V，R=10 kΩ，C=100 μF；τ=1 s。不是实测曲线。',20,anchor='middle')
svg_file('04_rc_continuity.svg',b)

# Markdown rendering with installed library, then a standalone standard-library fallback.
def inline(s):
    s=html.escape(s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
    return s

def fallback(md):
    lines=md.splitlines();out=[];i=0
    while i<len(lines):
        line=lines[i]
        if not line.strip():i+=1;continue
        if line.startswith('```'):
            buf=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):buf.append(lines[i]);i+=1
            out.append('<pre><code>'+html.escape('\n'.join(buf))+'</code></pre>');i+=1;continue
        h=re.match(r'^(#{1,6}) (.*)',line)
        if h:out.append(f'<h{len(h[1])}>{inline(h[2])}</h{len(h[1])}>');i+=1;continue
        if line.startswith('>'):
            buf=[]
            while i<len(lines) and lines[i].startswith('>'):buf.append(inline(lines[i][1:].strip()));i+=1
            out.append('<blockquote>'+'<br>'.join(buf)+'</blockquote>');continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                cols=[v.strip() for v in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+',v) for v in cols):rows.append(cols)
                i+=1
            out.append('<table><thead><tr>'+''.join('<th>'+inline(c)+'</th>' for c in rows[0])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+inline(c)+'</td>' for c in row)+'</tr>' for row in rows[1:])+'</tbody></table>');continue
        if line.startswith('- '):
            rows=[]
            while i<len(lines) and lines[i].startswith('- '):rows.append('<li>'+inline(lines[i][2:])+'</li>');i+=1
            out.append('<ul>'+''.join(rows)+'</ul>');continue
        if line.strip()=='---':out.append('<hr>');i+=1;continue
        buf=[line];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#|>|\||```|- )',lines[i]):buf.append(lines[i]);i+=1
        out.append('<p>'+inline('\n'.join(buf))+'</p>')
    return '\n'.join(out)
try:
    import markdown
    render=lambda s:markdown.markdown(s,extensions=['tables','fenced_code'])
except ImportError:
    try:
        import markdown2
        render=lambda s:markdown2.markdown(s,extras=['tables','fenced-code-blocks'])
    except ImportError:render=fallback

files=sorted((ROOT/'chapters').glob('*.md'))
if len(files)!=9:raise RuntimeError(f'正文文件不完整：{len(files)}，应为9。')
texts=[p.read_text(encoding='utf-8') for p in files]
combined='\n\n---\n\n'.join(texts)
source=(ROOT/'editorial/来源与证据边界.md').read_text(encoding='utf-8')
combined+='\n\n---\n\n'+source
(ROOT/'book.md').write_text(combined,encoding='utf-8')
figures={1:('01_shared_points.svg','图1-1　共享计数点示意。位置数值为本版构造的程序核查用例，不是实测数据。'),2:('02_spring_states.svg','图2-1　四个时刻的状态核对。新编理想模型。'),4:('03_fixed_potential.svg','图4-1　固定观察点，分别移动不同电极。新编原理示意，不代表原装置尺寸。'),5:('04_rc_continuity.svg','图5-1　未充满即切换放电，保持电容电压连续。新编理想曲线。')}
chap_titles=[];sections=[]
for i,(p,txt) in enumerate(zip(files,texts)):
    if i==0:txt='# 前言'+txt.split('# 前言',1)[1]
    title=re.search(r'^# (.+)',txt,re.M).group(1);chap_titles.append(title)
    frag=render(txt)
    # Section headings within each chapter, while cover owns the document h1.
    frag=re.sub(r'<(/?)h([1-5])>',lambda m:f'<{m[1]}h{int(m[2])+1}>',frag)
    if i in figures:
        name,caption=figures[i];data=base64.b64encode((AS/name).read_bytes()).decode()
        fig=f'<figure><img alt="{html.escape(caption)}" src="data:image/svg+xml;base64,{data}"><figcaption>{caption}</figcaption></figure>'
        # Place each figure at a relevant section rather than at every opening.
        needles={1:'1.4 用共享计数点',2:'2.3 用四个时刻',4:'4.4 固定同一个点',5:'5.3 一个可以讲深的例子'}
        patt=r'(<h3>'+re.escape(needles[i])+r'.*?</h3>)'
        frag,n=re.subn(patt,r'\1'+fig,frag,count=1)
        if not n:frag=frag.replace('</h2>','</h2>'+fig,1)
    frag=re.sub(r'\[(S\d+|T\d+)\]',lambda m:f'<a class="ref" href="#sources" title="查看来源与证据边界">[{m[1]}]</a>',frag)
    sections.append(f'<section class="chapter" id="ch{i}">{frag}</section>')
chars=sum(len(re.findall(r'[\u4e00-\u9fff]',t)) for t in texts)
css='''*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:72px}body{margin:0;background:#f6f3ec;color:#273b3e;font-family:-apple-system,BlinkMacSystemFont,"Noto Sans CJK SC","PingFang SC","Microsoft YaHei",sans-serif}.top{position:sticky;top:0;z-index:3;background:#f6f3ecf5;border-bottom:1px solid #d5dfd7;padding:14px 5vw;display:flex;justify-content:space-between;gap:12px;font-size:14px}.top a{color:#0b6462;text-decoration:none}a{color:#0d6663}main{max-width:980px;margin:auto;padding:0 40px 70px}.cover{padding:88px 0 68px;border-bottom:2px solid #1f6462;position:relative}.eyebrow{font-size:13px;letter-spacing:.17em;color:#477975}.cover h1{font-size:clamp(37px,7vw,72px);line-height:1.2;letter-spacing:.015em;margin:22px 0}.subtitle{font-size:24px;line-height:1.7;color:#4a6061}.cover .lead{font-family:"Noto Serif CJK SC","Songti SC",serif;font-size:24px;line-height:1.8;margin-top:38px}.meta{font-size:14px;color:#667674;line-height:1.8}.note{background:#e9efea;border-left:4px solid #427773;padding:17px 21px;font-size:15px;line-height:1.8}.toc{padding:38px 0;border-bottom:1px solid #ccd6d0}.toc a{display:block;text-decoration:none;padding:10px 0;border-bottom:1px dotted #c5d2c9;font-size:17px}.chapter{padding-top:62px;font-size:18px;line-height:1.95}.chapter>h2{font-size:33px;line-height:1.5;margin:0 0 33px;padding-top:14px;border-top:3px solid #236c67}.chapter h3{font-size:24px;line-height:1.5;margin:43px 0 18px;color:#205e5c}.chapter h4{font-size:21px;margin-top:30px}.chapter p{margin:0 0 1.05em;overflow-wrap:break-word}.chapter strong{color:#1e5c58}.chapter blockquote{margin:25px 0;padding:22px 26px;background:#eaf0e9;border-left:4px solid #52877d;line-height:1.9}.chapter blockquote p:last-child{margin-bottom:0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eaece6;padding:20px;border-radius:8px;font-size:14px;line-height:1.8}code{font-family:ui-monospace,SFMono-Regular,Consolas,"Noto Sans CJK SC",monospace;overflow-wrap:anywhere;font-size:.9em}table{border-collapse:collapse;font-size:16px;width:100%;margin:24px 0}th,td{padding:11px 13px;border-bottom:1px solid #c8d4cb;text-align:left;vertical-align:top}th{background:#e6eee6}figure{margin:25px 0 32px}figure img{display:block;width:100%;height:auto}figcaption{font-size:13px;line-height:1.7;color:#697772;margin-top:10px}.ref{font-size:12px;text-decoration:none;white-space:nowrap}.appendix{font-size:15px;line-height:1.9;margin-top:70px;border-top:2px solid #416f67;padding-top:25px}.appendix h1{font-size:26px}.appendix h2{font-size:23px;margin-top:30px}.appendix h3{font-size:20px}.appendix code{word-break:break-all}.appendix summary{cursor:pointer;font-size:24px;font-weight:700}.bottom{margin-top:55px;padding-top:20px;border-top:1px solid #cad5ce;font-size:14px;color:#657771}.backtop{position:fixed;right:16px;bottom:18px;padding:10px 14px;background:#1b6260;color:#fff;text-decoration:none;border-radius:6px;font-size:13px}@media(max-width:640px){main{padding:0 20px 55px}.top{padding:12px 20px;font-size:12px}.cover{padding:50px 0 38px}.subtitle{font-size:20px}.cover .lead{font-size:21px}.chapter{font-size:17px;line-height:1.95;padding-top:45px}.chapter>h2{font-size:27px}.chapter h3{font-size:22px}.chapter blockquote{padding:16px}.chapter table{font-size:13px}th,td{padding:8px 5px}figure{margin-left:-9px;margin-right:-9px}.backtop{display:none}}@media print{body{background:#fff;color:#111}main{max-width:none;padding:0}.top,.backtop,.toc,.note.online{display:none}.cover{page-break-after:always;border:0;padding:40mm 0}.chapter{font-size:11pt;line-height:1.85;page-break-before:always;padding-top:0}.chapter>h2{font-size:22pt}.chapter h3{font-size:15pt;break-after:avoid}figure,blockquote,table{break-inside:avoid}.ref{color:#333}.appendix{page-break-before:always;font-size:9pt}details>summary{display:none}details::details-content{display:block}a{color:inherit;text-decoration:none}@page{size:A4;margin:20mm 19mm}}'''
toc=''.join(f'<a href="#ch{i}">{html.escape(t)}</a>' for i,t in enumerate(chap_titles))
book=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="基于真实教学材料重写的七章物理教师AI协作试读本"><title>把物理想法做出来｜七章重写试读本</title><style>{css}</style></head><body id="top"><nav class="top"><a href="#contents">目录</a><span>七章重写试读本 · 2026.09.11</span><a href="#sources">来源说明</a></nav><main><header class="cover"><div class="eyebrow">PHYSICS · MAKING · TEACHING</div><h1>把物理想法<br>做出来</h1><div class="subtitle">AI协作的资源开发、实验与课堂实践</div><p class="lead">让模型、屏幕、装置与解释对得上。</p><p class="meta">基于黄灿斌与合作者的实践材料重新组织<br>七章正文，配套四个新编离线练习 · 供作者审阅</p><p class="note">这是一部完整短稿，不是出版定稿。真实案例、新编示例与待核实部分分别标明；合著署名、图片授权和事实终审仍需作者确认。</p></header><nav class="toc" id="contents"><h2>阅读目录</h2>{toc}<a href="#sources">来源与证据边界</a></nav><p class="note online">本HTML包含全文与示意图，可单文件离线阅读。四个可操作练习请使用配套ZIP：解压后打开index.html。这里的图为新绘原理示意，不是历史截图。</p>{''.join(sections)}<section id="sources" class="appendix"><details><summary>来源与证据边界（展开）</summary>{render(source)}</details></section><div class="bottom">本版正文、前后记约 {chars:,} 个汉字（不含附录，程序统计）。数量仅说明本次交付规模，不代表完成原定大部头。请结合编务中的下一轮修订说明审阅。</div></main><a class="backtop" href="#top">回到顶部</a><script>function openSources(){{if(location.hash==='#sources')document.querySelector('#sources details').open=true;}}window.addEventListener('hashchange',openSources);window.addEventListener('beforeprint',()=>document.querySelector('#sources details').open=true);openSources();</script></body></html>'''
(ROOT/'book.html').write_text(book,encoding='utf-8')
portalcss='''*{box-sizing:border-box}body{margin:0;background:#f4f2e9;color:#253d3e;font:17px/1.8 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}main{max-width:1060px;margin:auto;padding:50px 25px}h1{font-size:clamp(32px,6vw,54px);line-height:1.35}h2{font-size:24px}.tag{color:#637974;font-size:14px}.lead{max-width:830px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.card{display:block;text-decoration:none;color:inherit;background:white;padding:25px;border:1px solid #d9e3d9;border-radius:13px}.card:hover{border-color:#267d76}.card h2{color:#14685f;margin:0 0 12px}.card p{margin:10px 0}.boundary{font-size:14px;color:#6b736b;border-top:1px solid #dbe4db;padding-top:12px}.book{background:#185e5a;color:white;margin:30px 0}.book h2{color:white}.links{padding:24px 0}.links a{color:#12665e;margin-right:20px}.note{border-left:4px solid #a9783a;padding:15px;background:#fff9eb}.small{font-size:14px;color:#62726c}@media(max-width:660px){main{padding:25px 18px}.grid{grid-template-columns:1fr}.card{padding:20px}}'''
cards=[('01_paper_tape.html','01　记录与计算','从六个位置估计速度，比较单位质量能量变化。','输入改动后，旧结果立即失效；可以打印完整记录。','不是自动判断“验证成功”的裁判。'),('02_spring.html','02　运动与能量','在0、T/4、T/2、3T/4四个时刻核对位置、速度和加速度。','改变参数重置初态；能量显示标明固定刻度。','理想解析模型，不是实物弹簧实验。'),('03_potential.html','03　电势与边界','固定观察点，比较不同电极移动的影响。','初始2.4 V；下板上移1.5 V；上板下移3.0 V。','忽略边缘效应，不是有限水槽数值解。'),('04_rc.html','04　电路与过程','未充满即切换放电，观察电压连续与电流改向。','逐次前进τ/4，或播放后随时切换。','理想充放电，不是硬件传感器数据。')]
cardhtml=''.join(f'<a class="card" href="exercises/{n}"><h2>{t}</h2><p>{d}</p><p>{act}</p><div class="boundary">{lim}</div></a>'for n,t,d,act,lim in cards)
portal=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>把物理想法做出来｜阅读与练习入口</title><style>{portalcss}</style></head><body><main><p class="tag">一本书，四个小练习 · 离线示例入口</p><h1>把物理想法做出来</h1><p class="lead">从纸带记录到课堂评价。先打开书稿阅读，也可以直接进入一个练习，用具体输入检查屏幕是否仍在表达同一个物理问题。</p><a class="card book" href="book.html"><h2>打开七章连续阅读版 →</h2><p>前言 · 纸带 · 弹簧 · 网站 · 电势 · 电路 · 课堂 · 学生评价</p></a><div class="grid">{cardhtml}</div><p class="note">以上是本次新编的离线样例，不是对原网站、原硬件或学生作品的原样复现。页面不登录、不上传数据，也不自动保存本次操作记录。</p><div class="links"><a href="book.md">Markdown书稿</a><a href="editorial/revision.html">下一轮材料与修订说明</a><a href="editorial/sources.html">来源与证据边界</a><a href="editorial/validation.html">程序核查说明</a></div><p class="small">解压整个文件夹后使用，保留文件的相对位置。首次使用先看每页的模型边界。2026-09-11。</p></main></body></html>'''
(ROOT/'index.html').write_text(portal,encoding='utf-8')
for mdfile,out,title in [('下一轮修订与材料需求.md','revision.html','下一轮修订与材料需求'),('来源与证据边界.md','sources.html','来源与证据边界')]:
    body=render((ROOT/'editorial'/mdfile).read_text(encoding='utf-8'))
    (ROOT/'editorial'/out).write_text(f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{css}</style></head><body><main><p><a href="../index.html">← 返回目录</a></p><article class="appendix">{body}</article></main></body></html>',encoding='utf-8')
metadata={'date':'2026-09-11','chapter_files':len(files),'main_chapters':7,'main_text_chinese_characters':chars,'main_text_total_characters':sum(len(t) for t in texts),'exercise_count':4,'figure_count':4,'remote_modified':False,'hardware_tested':False,'classroom_validated':False,'format':['Markdown','HTML']}
(ROOT/'editorial/build-metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'README.md').write_text('''# 把物理想法做出来：七章重写试读本

解压后打开 `index.html`。无需安装软件、登录或联网。连续阅读为 `book.html`，可编辑全文为 `book.md`，分章稿在 `chapters/`。

四个新编离线练习在 `exercises/`。示意图在 `assets/`，均为原理示意，不是原装置实测图。来源、下一轮材料建议与核查说明在 `editorial/`。

本版未操作WorkBuddy、未改远端GitHub、未部署原网站、未进行硬件或课堂验证。实际程序检查结果以本包报告为准，不把源码运行等同于教学有效。

## 重建与核查（普通阅读不需要执行）

- `python editorial/build_exercises.py`：重建离线练习。
- `node editorial/test_models.js`：运行解析模型数值与边界检查。
- `python editorial/build_book.py`：重建阅读版及示意图。
- `python editorial/check_browser.py`：安装了Playwright及浏览器的环境可运行界面检查；缺少时报告未执行。

页面不自动保存你刚输入的记录。纸带实验使用打印保存PDF，并自行打开核对末尾。分享给同事时保留整个文件夹的目录结构。
''',encoding='utf-8')
print(json.dumps(metadata,ensure_ascii=False))
