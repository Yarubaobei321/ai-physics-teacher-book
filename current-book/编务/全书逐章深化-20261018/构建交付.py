"""重建独立候选的审阅入口与证据索引；不触碰现役正文。"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import subprocess,json,re,html,hashlib,os,ast,runpy,difflib
HERE=Path(__file__).resolve().parent;BOOK=HERE.parent.parent
NODE='/Users/yaril/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
PANDOC='/opt/homebrew/bin/pandoc';KATEX=BOOK/'阅读资源/katex/katex.min.js'
manifest=json.loads((HERE/'章节清单.json').read_text());changes=json.loads((HERE/'修改明细.json').read_text())
evidence=runpy.run_path(str(HERE/'逐章证据.py'));CARDS=evidence['CARDS'];SOURCES=evidence['SOURCES']
# 复用前章已经检查过的渲染函数，不执行其文件写入部分。
old_script=BOOK/'编务/第10章深度试做-20261018/构建对比.py'
tree=ast.parse(old_script.read_text())
for node in tree.body:
 if isinstance(node,ast.FunctionDef) and node.name in ['pandoc','visible','counts','render']:
  exec(compile(ast.Module(body=[node],type_ignores=[]),str(old_script),'exec'))
formula_count=0
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def link(p,origin=HERE):return os.path.relpath(Path(p).resolve(),origin)
def mdlink(label,p):return f'[{label}](<{Path(p).resolve()}>)'
def hlink(label,p):return '<a href="'+html.escape(link(p),quote=True)+'">'+html.escape(label)+'</a>'
def text(s):return html.escape(str(s))
CSS='''
:root{--ink:#203944;--muted:#5f7075;--blue:#175d78;--line:#d5e1e4;--bg:#f2f5f5;--old:#8b5b32;--new:#1e6c5a}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.85 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}a{color:var(--blue);text-underline-offset:4px}header{max-width:1400px;margin:auto;padding:45px 35px 25px}h1{font-size:clamp(27px,4vw,43px);line-height:1.35}h2{font-size:26px;line-height:1.5}h3{font-size:20px;line-height:1.5}header p{max-width:1000px}.eyebrow{font-size:12px;letter-spacing:.13em;color:var(--blue)}.layout{display:grid;grid-template-columns:215px minmax(0,1fr);max-width:1600px;margin:auto;gap:25px;padding:10px 25px 70px}aside{position:sticky;top:10px;align-self:start;max-height:96vh;overflow:auto;padding:16px;background:white;border:1px solid var(--line)}aside a{display:block;margin:8px 0;font-size:14px;text-decoration:none}main{min-width:0}section.chapter{background:white;border:1px solid var(--line);padding:28px;margin-bottom:25px;scroll-margin-top:15px}.lead{font-size:19px;color:var(--blue);border-left:4px solid var(--blue);padding-left:17px}.small{font-size:13px;color:var(--muted)}.metrics{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}.metric{background:#edf3f4;padding:10px 17px;font-size:14px}.metric b{font-size:20px;display:block}.tools{display:flex;gap:18px;flex-wrap:wrap;font-size:14px}details{border:1px solid var(--line);margin:18px 0}summary{cursor:pointer;padding:13px 17px;font-weight:600;background:#f4f7f7}.inner{padding:15px 20px}.compare{display:grid;grid-template-columns:1fr 1fr;gap:25px}.column{min-width:0}.tag{font-size:13px;color:var(--muted);border-bottom:2px solid var(--line);padding-bottom:8px}.prose{overflow-wrap:anywhere}.prose h1{font-size:28px}.prose h2{font-size:23px;margin-top:2em}.prose h3{font-size:19px}.prose figure{margin:20px 0}.prose img{max-width:100%;max-height:700px;object-fit:contain;display:block;margin:auto}.prose figcaption{color:var(--muted);font-size:13px}.prose pre,pre.diff{font:14px/1.8 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7f7;padding:15px}.prose blockquote{margin:18px 0;border-left:3px solid #8aabb8;padding:4px 18px;background:#f2f7f8}.table-wrap{overflow:auto;margin:18px 0}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:9px 12px;border:1px solid var(--line);vertical-align:top}th{background:#edf3f5}td p{margin:0}.change{border-top:1px solid var(--line);padding:15px 0}.change:first-child{border-top:0}.change p{margin:7px 0}.old{border-left:3px solid #b28c69!important;background:#faf5ef!important}.new{border-left:3px solid #559c88!important;background:#eff7f3!important}.notice{background:#fff8e9;padding:13px 18px;border-left:3px solid #c6a05e}.katex-display{overflow:auto;padding:6px 0}.katex{font-size:1.04em}button,input,select{font:inherit;padding:7px 12px;border:1px solid var(--line);background:white;color:var(--ink)}.controls{display:flex;gap:12px;flex-wrap:wrap}.reading{max-width:900px;margin:auto;background:white;padding:38px}.reading header{padding:0}.reading section{padding:0}.hidden{display:none!important}@media(max-width:1000px){.layout{display:block;padding:10px 15px 40px}aside{position:static;max-height:none;margin-bottom:20px;display:flex;flex-wrap:wrap;gap:10px}.compare{grid-template-columns:1fr}.chapter{padding:20px!important}.reading{padding:24px}header{padding:30px 22px}}@media print{aside,.controls{display:none}.layout{display:block;padding:0}.compare{display:block}.column{break-before:page}section.chapter{border:0}.prose img{max-height:170mm}body{background:white}}
'''
def doc(title,body,css='../..'):
 return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+text(title)+'</title><link rel="stylesheet" href="'+css+'/阅读资源/katex/katex.min.css"><style>'+CSS+'</style></head><body>'+body+'</body></html>'
stats=[];sections=[];nav=[];source_manifest=[]
for row in manifest:
 n=row['chapter'];d=HERE/f'第{n:02d}章';source=Path(row['source']);snapshot=HERE/row['snapshot']
 assert sha(source)==row['sha256']==sha(snapshot),f'第{n}章原稿或冻结快照变化'
 old=snapshot.read_text();new=(d/'深化稿.md').read_text();a=counts(old);b=counts(new)
 for key in ['visible_nonspace','visible_han','source_bytes']:
  assert b[key]<=a[key],(n,key,a[key],b[key])
 brand=re.search(r'workbuddy|deepseek|deepseek|chatgpt|claude|gemini|\bDSH\b|\bGPT\b|codex|opus',visible(new),re.I)
 assert not brand,(n,brand.group() if brand else '')
 assert not re.search('[\x00-\x08\x0b\x0c\x0e-\x1f]',new),f'第{n}章有控制字符'
 stats.append(dict(chapter=n,title=row['title'],old=a,new=b,sha256=sha(d/'深化稿.md')))
 row['status']='独立深化候选完成；未合入现役正文'
 core,start,shift,boundary,gap=CARDS[n]
 # 原始索引保存当前身份、准确来源和实际核读范围。
 ix=[f'# 第{n:02d}章 原始记录索引','',f'本索引对应：{row["title"]}。只读来源保持原位置；本轮候选位于本目录。', '',
 mdlink('现役原稿（未修改）',source), '',mdlink('原稿快照',snapshot),'',f'原稿 SHA256：`{row["sha256"]}`','',mdlink('深化稿',d/'深化稿.md'),'','## 本轮核对的依据','','|材料|核对范围|支持什么|','|---|---|---|']
 records=[]
 for z in SOURCES.get(n,[]):
  p=Path(z['path']);sig=sha(p);records.append({**z,'sha256':sig})
  ix.append(f'|{mdlink(p.name,p)}|{z["status"]}|{z["role"]}|')
 # 模型计算仅适用于实际有独立算例的章。
 if n in [1,2,4,7,8,11,12,13,14,15,16,17]:
  ix+=['',mdlink('独立复算与计数结果',HERE/'核验/逐章独立复算结果.json'),'',mdlink('独立复算脚本',HERE/'核验/独立复算.py')]
 ix+=['','## 可以与不可以据此判断','',boundary,'','## 仍缺什么','',gap,'','完整来源指纹见 '+mdlink('来源指纹',d/'来源指纹.json')+'。旧目录或材料中的完成声明只作为历史记录，不自动视为本轮现场验证。']
 (d/'原始记录索引.md').write_text('\n'.join(ix)+'\n');(d/'来源指纹.json').write_text(json.dumps(records,ensure_ascii=False,indent=2));source_manifest.extend([dict(chapter=n,**z) for z in records])
 ch=[c for c in changes[str(n)] if c['before']!=c['after'] or n==10]
 card=[f'# 第{n:02d}章 深化说明','','## 核心主张','',core,'','## 学生或读者原来怎样想','',start,'','## 这次改变哪一步判断','',shift,'','## 凭什么这样写','',boundary,'','## 删除与新增对应','','|改了什么|为什么|','|---|---|']
 card += [f'|{c["title"]}|{c["why"]}|' for c in ch]
 card += ['','## 篇幅','',f'可见非空白字符：{a["visible_nonspace"]:,} → {b["visible_nonspace"]:,}；可见汉字：{a["visible_han"]:,} → {b["visible_han"]:,}；Markdown 字节：{a["source_bytes"]:,} → {b["source_bytes"]:,}。','', '新增的物理解释由压缩重复导读、操作说明或旧的过强结论抵扣；实际逐段增删见总对照页。','', '## 作者待裁决与待补证据','',gap,'',mdlink('原始记录索引',d/'原始记录索引.md')]
 (d/'深化说明.md').write_text('\n'.join(card)+'\n')
 # 所有完整原文按其原资源目录渲染；候选已经重定向本地资源。
 oldhtml=render(old,source.parent,f'o{n}-');newhtml=render(new,d,f'n{n}-')
 # 章阅读页的相对链接由总目录再下移一层。
 def down(m):
  attr,url=m.group(1),html.unescape(m.group(2));u=urlsplit(url)
  if u.scheme or url.startswith(('#','//')):return m[0]
  return attr+'="'+html.escape('../'+url,quote=True)+'"'
 reading=re.sub(r'\b(src|href)="([^"]+)"',down,newhtml)
 readhead='<p class="small">独立深化候选 · 未合入现役正文 · <a href="../全书深化对比.html#ch'+str(n)+'">返回本章对照</a></p>'
 (d/'深化稿.html').write_text(doc(row['title'], '<div class="reading">'+readhead+'<article class="prose">'+reading+'</article></div>', '../../..'))
 nav.append(f'<a href="#ch{n}" data-n="{n}">{n:02d}　{text(row["title"].split("　",1)[-1])}</a>')
 metrics=''.join('<div class="metric">'+label+'<b>'+f'{a[key]:,} → {b[key]:,}'+'</b>减少 '+f'{a[key]-b[key]:,}'+'</div>' for key,label in [('visible_nonspace','可见非空白字符'),('visible_han','可见汉字'),('source_bytes','Markdown 字节')])
 summaries=''.join('<div class="change"><b>'+text(c['title'])+'</b><p>'+text(c['why'])+'</p><p class="small">依据：'+hlink('对应原稿' if c['source']=='本章原稿快照' else '来源与核验',snapshot if c['source']=='本章原稿快照' else HERE/c['source'])+' · '+hlink('本章证据范围',d/'原始记录索引.md')+'</p></div>' for c in ch)
 # 逐段对照由实际最终文本生成，覆盖所有改动，包括通用清理。
 # 只去掉资源地址的目录变化，避免把位置搬迁冒充内容深化。
 def normpara(s):return re.sub(r'\]\([^\n]*?\)','](资源位置)',s)
 op=[p for p in old.split('\n\n') if p.strip()];np=[p for p in new.split('\n\n') if p.strip()]
 matcher=difflib.SequenceMatcher(None,[normpara(p) for p in op],[normpara(p) for p in np],autojunk=False)
 diffs=[]
 for tag,i,j,k,l in matcher.get_opcodes():
  if tag=='equal':continue
  bef='\n\n'.join(op[i:j]);aft='\n\n'.join(np[k:l]);label={'replace':'改写','delete':'删除','insert':'新增'}[tag]
  diffs.append('<div class="change"><b>'+label+' · 原段 '+str(i+1)+' / 新段 '+str(k+1)+'</b><div class="compare"><pre class="diff old">'+text(bef or '（无）')+'</pre><pre class="diff new">'+text(aft or '（无）')+'</pre></div></div>')
 ixhtml=render((d/'原始记录索引.md').read_text(),d,f'ix{n}-')
 sections.append(f'<section class="chapter" id="ch{n}" data-n="{n}"><p class="eyebrow">CHAPTER {n:02d} · 独立深化候选</p><h2>{text(row["title"])}</h2><p class="lead">{text(core)}</p><p><b>起点：</b>{text(start)}</p><p><b>推进一步：</b>{text(shift)}</p><p><b>证据到哪里：</b>{text(boundary)}</p><div class="metrics">{metrics}</div><div class="tools">'+hlink('单独阅读深化稿',d/'深化稿.html')+hlink('下载/编辑 Markdown',d/'深化稿.md')+hlink('深化说明',d/'深化说明.md')+hlink('原始记录索引',d/'原始记录索引.md')+hlink('现役原稿',source)+'</div><details open><summary>本章改了什么、为什么</summary><div class="inner">'+summaries+'</div></details><details><summary>逐段增删对照 · '+str(len(diffs))+' 组</summary><div class="inner"><p class="small">左为冻结原稿，右为最终候选。保留原句和公式写法；仅资源相对目录的变化不计为正文修改。</p>'+''.join(diffs)+'</div></details><details class="full"><summary>完整原稿 / 完整深化稿</summary><div class="inner compare"><div class="column"><div class="tag">原稿 · 仅供对照</div><article class="prose">'+oldhtml+'</article></div><div class="column"><div class="tag">深化稿 · 候选</div><article class="prose">'+newhtml+'</article></div></div></details><details><summary>本章原始记录索引与证据范围</summary><div class="inner prose">'+ixhtml+'</div></details><p class="notice"><b>待补或待作者决定：</b>'+text(gap)+'</p></section>')
 print(f'第{n:02d}章：{a["visible_nonspace"]} → {b["visible_nonspace"]}；{len(diffs)}组差异',flush=True)
# 单一主入口，筛选只改变当前显示，不隐藏文件内容。
totals={side:{key:sum(r[side][key] for r in stats) for key in ['visible_nonspace','visible_han','source_bytes']} for side in ['old','new']}
intro='<header><div class="eyebrow">《不会编程的物理老师，能用 AI 做成什么》 · 全书逐章深化</div><h1>每一章，具体深在哪里</h1><p>17 章独立候选：其余 16 章本轮深化，第 10 章复用已交付稿。先看核心主张、修改理由和证据范围，再展开逐段增删或完整两稿。现役正文保持原样。</p><p class="small">范围为第 1—17 章；序言、前言、导论、结语和附录未改。署名与外部方案作者保留；正文统一称 AI，历史工具名仅保留在原稿与来源文件定位中。</p><p class="notice">各章均未增加可见字符、汉字或文件字节。独立计算验证的是列出的物理关系；缺少课堂前后记录的章节，仍不能宣称学生理解已改善。未发布，未做浏览器截图验收。</p><div class="controls"><label>显示章节 <select id="choose"><option value="all">全部 17 章</option>'+''.join(f'<option value="{i}">第 {i} 章</option>' for i in range(1,18))+'</select></label><button id="close">收起完整对照</button>'+hlink('一页审阅说明',HERE/'review.md')+hlink('核验记录',HERE/'核验记录.md')+'</div><p class="small">计数：标题、正文、表格、图注、提示词均计入；链接地址与 Markdown 标记不计，图注只计一次，公式按 TeX 字符计。全章原始文件字节另列。</p></header>'
js='''<script>const select=document.getElementById('choose');function filter(v){document.querySelectorAll('section.chapter').forEach(e=>e.classList.toggle('hidden',v!=='all'&&e.dataset.n!==v));}select.addEventListener('change',()=>filter(select.value));document.querySelectorAll('aside a').forEach(a=>a.addEventListener('click',()=>{select.value='all';filter('all');}));document.getElementById('close').addEventListener('click',()=>document.querySelectorAll('details.full').forEach(e=>e.open=false));</script>'''
(HERE/'全书深化对比.html').write_text(doc('全书逐章深化对比',intro+'<div class="layout"><aside>'+''.join(nav)+'</aside><main>'+''.join(sections)+'</main></div>'+js))
(HERE/'字数与指纹.json').write_text(json.dumps(dict(chapters=stats,totals=totals,formula_count=formula_count),ensure_ascii=False,indent=2))
(HERE/'章节清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(HERE/'核验/来源指纹汇总.json').write_text(json.dumps(source_manifest,ensure_ascii=False,indent=2))
print(json.dumps(dict(totals=totals,formula_count=formula_count),ensure_ascii=False))
