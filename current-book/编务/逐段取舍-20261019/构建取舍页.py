"""把原稿与深化稿逐段对齐，生成可勾选的本地取舍页；只读两稿，不改现役正文。"""
from pathlib import Path
from urllib.parse import urlsplit, unquote
import subprocess, json, re, html, hashlib, os, difflib

HERE = Path(__file__).resolve().parent
BOOK = HERE.parent.parent
SRC = BOOK / '编务/全书逐章深化-20261018'
PANDOC = '/opt/homebrew/bin/pandoc'
manifest = json.loads((SRC / '章节清单.json').read_text())
changes = json.loads((SRC / '修改明细.json').read_text())


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def esc(s): return html.escape(str(s))


def blocks(md):
    """按空行切段；代码块与 <details> 整体算一段。"""
    out, cur, fence, depth = [], [], False, 0
    for line in md.split('\n'):
        s = line.strip()
        if s.startswith('```'): fence = not fence
        if not fence:
            depth += len(re.findall(r'<details\b', s)) - len(re.findall(r'</details>', s))
        if not s and not fence and depth <= 0:
            if cur: out.append('\n'.join(cur).strip('\n')); cur = []
            continue
        cur.append(line)
    if cur: out.append('\n'.join(cur).strip('\n'))
    return [b for b in out if b.strip()]


def norm(s): return re.sub(r'\]\([^\n]*?\)', '](资源)', s).strip()


def pair(olds, news):
    """在一组改动内按相似度保序配对，返回 (旧序号|None, 新序号|None) 行。"""
    n, m = len(olds), len(news)
    sim = [[0.0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            sm = difflib.SequenceMatcher(None, norm(olds[i]), norm(news[j]), autojunk=False)
            sim[i][j] = sm.ratio() if sm.quick_ratio() >= 0.3 else 0.0
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            v = max(best[i + 1][j], best[i][j + 1])
            if sim[i][j] >= 0.3: v = max(v, sim[i][j] + best[i + 1][j + 1])
            best[i][j] = v
    rows, i, j = [], 0, 0
    while i < n or j < m:
        if i < n and j < m and sim[i][j] >= 0.3 and abs(best[i][j] - (sim[i][j] + best[i + 1][j + 1])) < 1e-9:
            rows.append((i, j)); i += 1; j += 1
        elif i < n and (j == m or best[i][j] == best[i + 1][j]):
            rows.append((i, None)); i += 1
        else:
            rows.append((None, j)); j += 1
    return rows


def render_all(mds, origin):
    """整章一次交给 Pandoc，用注释标记切回逐段 HTML；图片路径改为相对本页。"""
    joined = '\n\n'.join(f'<!--BLK{k}-->\n\n{b}' for k, b in enumerate(mds)) + '\n\n<!--BLK-END-->'
    out = subprocess.run([PANDOC, '-f', 'markdown+tex_math_dollars', '-t', 'html5', '--katex'],
                         input=joined, text=True, capture_output=True, check=True).stdout
    parts = re.split(r'<!--BLK(?:\d+|-END)-->', out)[1:-1]
    assert len(parts) == len(mds), (origin, len(parts), len(mds))

    def fix(m):
        attr, url = m.group(1), html.unescape(m.group(2)); u = urlsplit(url)
        if not url or url.startswith('#') or u.scheme or url.startswith('//'): return m.group(0)
        rel = os.path.relpath((origin / unquote(u.path)).resolve(), HERE)
        return attr + '="' + html.escape(rel, quote=True) + '"'
    res = []
    for p in parts:
        p = re.sub(r'\b(src|href)="([^"]+)"', fix, p)
        p = re.sub(r'\bid="[^"]*"', '', p)
        p = re.sub(r'<table>([\s\S]*?)</table>', r'<div class="table-wrap"><table>\1</table></div>', p)
        res.append(p.strip())
    return res


def reasons_for(n, old, new):
    """把修改明细里的理由挂到对应段落上，供取舍参考。"""
    hit = []
    for c in changes.get(str(n), []):
        for side, txt in (('before', old), ('after', new)):
            frag = [x.strip() for x in c[side].split('\n') if len(x.strip()) >= 12]
            if txt and any(f[:40] in txt for f in frag[:6]):
                hit.append(c['title'] + '：' + c['why']); break
    return list(dict.fromkeys(hit))


data, sections, nav = [], [], []
total_choices = 0
for row in manifest:
    n = row['chapter']; d = SRC / f'第{n:02d}章'; source = Path(row['source'])
    assert sha(source) == row['sha256'], f'第{n}章现役正文已变化，需先重新对齐'
    old_md = source.read_text(); new_md = (d / '深化稿.md').read_text()
    ob, nb = blocks(old_md), blocks(new_md)
    oh, nh = render_all(ob, source.parent), render_all(nb, d)
    sm = difflib.SequenceMatcher(None, [norm(b) for b in ob], [norm(b) for b in nb], autojunk=False)
    rows = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1): rows.append(('same', [i1 + k], [j1 + k]))
        else:
            for a, b in pair(ob[i1:i2], nb[j1:j2]):
                ai = [] if a is None else [i1 + a]; bj = [] if b is None else [j1 + b]
                rows.append(('pair' if ai and bj else 'del' if ai else 'add', ai, bj))
    # 整章重写时逐段拼接会不连贯，改按二级标题整节取舍。
    section_mode = sum(1 for r in rows if r[0] == 'same') < len(ob) / 2
    if section_mode:
        def groups(bs):
            g = [[]]
            for k, b in enumerate(bs):
                if b.startswith('## ') and g[-1]: g.append([])
                g[-1].append(k)
            return g
        og, ng = groups(ob), groups(nb)
        assert len(og) == len(ng), (n, len(og), len(ng))
        rows = [('pair', a, b) for a, b in zip(og, ng)]
    chap_rows, html_rows, same_run, k = [], [], [], 0

    def flush():
        if not same_run: return
        first = re.sub(r'<[^>]+>', '', oh[same_run[0]])[:60]
        html_rows.append(f'<details class="same"><summary>未改动 {len(same_run)} 段 · <span>{esc(first)}…</span></summary>'
                         + ''.join(f'<div class="prose">{oh[i]}</div>' for i in same_run) + '</details>')
        same_run.clear()
    for kind, i, j in rows:
        rid = f'{n}-{k}'; k += 1
        chap_rows.append(dict(id=rid, kind=kind, old=i, new=j))
        if kind == 'same':
            same_run.append(i[0]); continue
        flush(); total_choices += 1
        opts = {'pair': [('old', '用原稿'), ('new', '用深化稿'), ('both', '两段都要'), ('none', '都不要')],
                'del': [('old', '保留原段'), ('none', '删去')],
                'add': [('new', '加入新段'), ('none', '不加')]}[kind]
        label = {'pair': '改写', 'del': '深化稿删去', 'add': '深化稿新增'}[kind]
        why = [] if section_mode else reasons_for(n, '\n\n'.join(ob[x] for x in i), '\n\n'.join(nb[x] for x in j))
        btns = ''.join(f'<button type="button" data-v="{v}">{t}</button>' for v, t in opts)
        if section_mode: label = '整节'
        left = f'<div class="cell old prose">{"".join(oh[x] for x in i)}</div>' if i else '<div class="cell empty">原稿没有这一段</div>'
        right = f'<div class="cell new prose">{"".join(nh[x] for x in j)}</div>' if j else '<div class="cell empty">深化稿删去了这一段</div>'
        whyhtml = ('<p class="why">修改理由：' + '；'.join(esc(w) for w in why) + '</p>') if why else ''
        html_rows.append(f'<div class="row" data-id="{rid}" data-kind="{kind}"><div class="bar"><span class="kind">{label}</span>'
                         f'<span class="opts">{btns}</span></div>{whyhtml}<div class="pairgrid">{left}{right}</div></div>')
    flush()
    data.append(dict(chapter=n, title=row['title'], mode='section' if section_mode else 'paragraph', source=str(source), source_sha256=row['sha256'],
                     deep=str(d / '深化稿.md'), deep_sha256=sha(d / '深化稿.md'),
                     old_blocks=ob, new_blocks=nb, rows=chap_rows))
    short = row['title'].split('　', 1)[-1]
    nchg = sum(1 for r in chap_rows if r['kind'] != 'same')
    nav.append(f'<a href="#ch{n}" data-n="{n}"><b>{n:02d}</b> {esc(short)}<span class="cnt" data-n="{n}">0/{nchg}</span></a>')
    sections.append(f'<section class="chapter" id="ch{n}" data-n="{n}"><h2>{esc(row["title"])}</h2>'
                    f'<p class="small">{nchg} 处可选 · 左：现役原稿　右：深化稿'
                    + ('<br><b>本章深化稿是整章重写，逐段拼接会前后不接，这里按大节整节取舍。</b>' if section_mode else '') + '</p>'
                    f'<div class="bulk"><button type="button" data-bulk="old">本章全部用原稿</button>'
                    f'<button type="button" data-bulk="new">本章全部用深化稿</button>'
                    f'<button type="button" data-bulk="clear">清空本章选择</button></div>'
                    + ''.join(html_rows) + '</section>')
    print(f'第{n:02d}章：原 {len(ob)} 段，新 {len(nb)} 段，可选 {nchg} 处', flush=True)

stamp = hashlib.sha256(json.dumps([[r['id'], r['kind'], r['old'], r['new']] for c in data for r in c['rows']]).encode()).hexdigest()[:12]
(HERE / '取舍数据.json').write_text(json.dumps(dict(build=stamp, chapters=data), ensure_ascii=False, indent=1))

katex = os.path.relpath(BOOK / '阅读资源/katex', HERE)
CSS = '''
:root{--ink:#203944;--muted:#5f7075;--blue:#175d78;--line:#d5e1e4;--bg:#f2f5f5;--card:#fff;--oldbg:#faf5ef;--oldbd:#b28c69;--newbg:#eff7f3;--newbd:#559c88;--pick:#175d78;--off:.38}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.8 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
header{max-width:1500px;margin:auto;padding:32px 28px 10px}h1{font-size:30px;margin:0 0 8px}header p{max-width:960px;margin:6px 0}
.layout{display:grid;grid-template-columns:230px minmax(0,1fr);gap:22px;max-width:1700px;margin:auto;padding:10px 22px 120px}
aside{position:sticky;top:10px;align-self:start;max-height:94vh;overflow:auto;background:var(--card);border:1px solid var(--line);padding:12px}
aside a{display:flex;gap:6px;align-items:baseline;margin:5px 0;font-size:13.5px;color:var(--ink);text-decoration:none;line-height:1.5}aside a b{color:var(--blue)}
.cnt{margin-left:auto;font-size:12px;color:var(--muted);white-space:nowrap}.cnt.done{color:#1e6c5a;font-weight:600}
section.chapter{background:var(--card);border:1px solid var(--line);padding:22px 24px;margin-bottom:22px;scroll-margin-top:10px}
h2{font-size:23px;margin:0 0 4px}.small{font-size:13px;color:var(--muted);margin:0 0 10px}
.bulk{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}
button{font:inherit;font-size:14px;padding:5px 12px;border:1px solid var(--line);background:#fff;color:var(--ink);cursor:pointer;border-radius:3px}
button:hover{border-color:var(--blue)}button.on{background:var(--pick);color:#fff;border-color:var(--pick)}
details.same{margin:8px 0;border:1px dashed var(--line);font-size:14px}details.same summary{cursor:pointer;padding:6px 12px;color:var(--muted)}details.same summary span{color:#9aa8ab}
details.same .prose{padding:0 14px;color:#4b5d63}
.row{border:1px solid var(--line);margin:14px 0;scroll-margin-top:12px}.row.undecided{box-shadow:inset 4px 0 0 #d9a441}
.bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:7px 12px;background:#f4f7f7;border-bottom:1px solid var(--line)}
.kind{font-size:13px;font-weight:600;color:var(--blue);min-width:72px}.opts{display:flex;gap:6px;flex-wrap:wrap}
.why{margin:0;padding:6px 12px;font-size:13px;color:var(--muted);background:#fbfcfc;border-bottom:1px solid var(--line)}
.pairgrid{display:grid;grid-template-columns:1fr 1fr}.cell{padding:4px 16px;min-width:0;transition:opacity .15s}
.cell.old{background:var(--oldbg);border-left:3px solid var(--oldbd)}.cell.new{background:var(--newbg);border-left:3px solid var(--newbd)}
.cell.empty{color:#9aa8ab;font-size:13px;padding:14px 16px;background:#fafbfb}
.row[data-v] .cell.old,.row[data-v] .cell.new{opacity:var(--off)}
.row[data-v=old] .cell.old,.row[data-v=new] .cell.new,.row[data-v=both] .cell.old,.row[data-v=both] .cell.new{opacity:1;box-shadow:inset 0 0 0 2px var(--pick)}
.prose{overflow-wrap:anywhere}.prose img{max-width:100%;max-height:420px;object-fit:contain;display:block;margin:8px auto}.prose figure{margin:10px 0}.prose figcaption{font-size:13px;color:var(--muted)}
.prose pre{white-space:pre-wrap;background:rgba(0,0,0,.035);padding:10px;font:14px/1.7 -apple-system,"PingFang SC",sans-serif}.prose blockquote{margin:8px 0;border-left:3px solid #8aabb8;padding:2px 14px}
.prose h1{font-size:24px}.prose h2{font-size:21px}.prose h3{font-size:18px}
.table-wrap{overflow:auto}table{border-collapse:collapse;font-size:14px;width:100%}th,td{border:1px solid var(--line);padding:5px 8px;vertical-align:top}
.katex-display{overflow:auto}
footer.dock{position:fixed;left:0;right:0;bottom:0;background:rgba(255,255,255,.97);border-top:1px solid var(--line);padding:10px 22px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;z-index:5}
footer.dock .prog{font-size:14px}footer.dock .prog b{color:var(--blue)}footer.dock .sp{flex:1}
#submit{background:var(--blue);color:#fff;border-color:var(--blue);font-weight:600;padding:7px 18px}
#msg{font-size:13px;color:#1e6c5a}
.hidden{display:none!important}
@media(max-width:900px){.layout{display:block;padding:10px 16px 140px}aside{position:static;max-height:none;margin-bottom:14px}.pairgrid{grid-template-columns:1fr}header{padding:22px 16px 6px}}
'''
intro = (f'<header><h1>逐段取舍：原稿与深化稿</h1>'
         f'<p>左边是现役原稿，右边是深化稿，只列出有差别的段落；没改动的段落折叠在灰色虚线框里。每处点一个按钮：用原稿、用深化稿、两段都要（原稿在前）或都不要。</p>'
         f'<p>没选的地方合并时一律<b>保留原稿</b>。选择会自动存在这个浏览器里，关掉再开还在。全部看完或看完一部分都可以点右下角“提交”，会下载一份取舍文件，告诉我即可，我据此合并出唯一的最新版，写回现役正文。</p>'
         f'<p class="small">构建标识 {stamp} · 页面只读两稿，不改任何正文</p></header>')
body = (intro + '<div class="layout"><aside>' + ''.join(nav) + '</aside><main>' + ''.join(sections) + '</main></div>'
        '<footer class="dock"><span class="prog">已选 <b id="done">0</b> / ' + str(total_choices) + ' 处</span>'
        '<button type="button" id="next">跳到下一处未选</button><label class="small"><input type="checkbox" id="hideDone"> 隐藏已选</label>'
        '<span class="sp"></span><span id="msg"></span><button type="button" id="submit">提交取舍</button></footer>')
JS = '''
const BUILD="__BUILD__",KEY="逐段取舍-"+BUILD;let S={};try{S=JSON.parse(localStorage.getItem(KEY)||"{}")}catch(e){}
function save(){try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}}
const rows=[...document.querySelectorAll('.row')];
function paint(r){const v=S[r.dataset.id];if(v)r.dataset.v=v;else delete r.dataset.v;r.classList.toggle('undecided',!v);
 r.querySelectorAll('.opts button').forEach(b=>b.classList.toggle('on',b.dataset.v===v));r.classList.toggle('hidden',!!v&&hideDone.checked)}
function counts(){let all=0;document.querySelectorAll('section.chapter').forEach(sec=>{const rs=[...sec.querySelectorAll('.row')];const d=rs.filter(r=>S[r.dataset.id]).length;all+=d;
 const c=document.querySelector('.cnt[data-n="'+sec.dataset.n+'"]');c.textContent=d+'/'+rs.length;c.classList.toggle('done',d===rs.length)});document.getElementById('done').textContent=all}
const hideDone=document.getElementById('hideDone');
rows.forEach(r=>{r.querySelectorAll('.opts button').forEach(b=>b.addEventListener('click',()=>{const id=r.dataset.id;S[id]=S[id]===b.dataset.v?undefined:b.dataset.v;if(!S[id])delete S[id];save();paint(r);counts()}));paint(r)});
document.querySelectorAll('[data-bulk]').forEach(b=>b.addEventListener('click',()=>{const sec=b.closest('section');sec.querySelectorAll('.row').forEach(r=>{const k=r.dataset.kind,m=b.dataset.bulk;
 if(m==='clear')delete S[r.dataset.id];else if(m==='old')S[r.dataset.id]=k==='add'?'none':'old';else S[r.dataset.id]=k==='del'?'none':'new';paint(r)});save();counts()}));
hideDone.addEventListener('change',()=>rows.forEach(paint));
document.getElementById('next').addEventListener('click',()=>{const r=rows.find(r=>!S[r.dataset.id]);if(r)r.scrollIntoView({behavior:'smooth',block:'start'});else msg('全部选完了')});
function msg(t){const m=document.getElementById('msg');m.textContent=t;setTimeout(()=>m.textContent='',6000)}
document.getElementById('submit').addEventListener('click',()=>{const out={build:BUILD,submitted:new Date().toISOString(),choices:S};const txt=JSON.stringify(out,null,1);
 const a=document.createElement('a');const t=new Date();const p=n=>String(n).padStart(2,'0');a.download='逐段取舍-提交-'+t.getFullYear()+p(t.getMonth()+1)+p(t.getDate())+'-'+p(t.getHours())+p(t.getMinutes())+'.json';
 a.href=URL.createObjectURL(new Blob([txt],{type:'application/json'}));document.body.appendChild(a);a.click();a.remove();
 try{navigator.clipboard.writeText(txt)}catch(e){};msg('已下载取舍文件（也复制到了剪贴板）。告诉我一声即可合并。')});
counts();
document.querySelectorAll('.math').forEach(el=>{try{katex.render(el.textContent,el,{displayMode:el.classList.contains('display'),throwOnError:false,strict:'ignore'})}catch(e){}});
'''.replace('__BUILD__', stamp)
page = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>逐段取舍</title><link rel="stylesheet" href="{katex}/katex.min.css"><style>{CSS}</style></head><body>{body}'
        f'<script src="{katex}/katex.min.js"></script><script>{JS}</script></body></html>')
(HERE / '逐段取舍.html').write_text(page)
print('可选总数', total_choices, '构建标识', stamp)
