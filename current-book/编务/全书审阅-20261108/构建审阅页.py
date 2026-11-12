"""生成《全书审阅-20261108.html》：全书正文与图片＋删改标注＋版面字数测算＋表达与配图建议。
只读正文，不改任何源稿。运行：/opt/anaconda3/bin/python 构建审阅页.py
"""
from __future__ import annotations
import html, math, re, sys, json
from pathlib import Path
from urllib.parse import quote
import markdown
from PIL import Image

HERE = Path(__file__).resolve().parent
BOOK = HERE.parents[1]
SRC = BOOK / "正文"
OUT = BOOK / "全书审阅-20261108.html"
sys.path.insert(0, str(HERE))
from 审阅方案 import PLAN, GLOBAL_NOTES, NEW_TOC, MOVED, ADD_UNITS, GLOBAL_B, TIER_B, TIER_C  # noqa: E402
from 表达样本 import DETECT, EMPTY, SAMPLES, GOOD, READER  # noqa: E402

# ---------- 版心假设 ----------
CPL, LPP = 38, 37            # 16 开、五号字：每行 38 字、每页 37 行
PAGE = CPL * LPP             # 1406 字/页
TEXT_W_MM, LINE_MM = 140, 5.6
TARGET = 300_000


def files():
    order = []
    for pat, key in [("序言-*", "序言"), ("前言-*", "前言")]:
        order += [(key, p / "正文.md") for p in sorted(SRC.glob(pat))]
    for p in sorted(SRC.glob("第??章-*")):
        order.append((p.name[:4], p / "正文.md"))
    order += [("结语", p / "正文.md") for p in sorted(SRC.glob("结语-*"))]
    for p in sorted((SRC / "附录").glob("附录*.md")):
        order.append((p.name[:3], p))
    order.append(("参考文献", SRC / "参考文献.md"))
    return order


# ---------- 计数 ----------
def plain(s):
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"<[^>]+>", "", s)
    return s.replace("**", "").replace("`", "")


def width_units(s):
    """排版宽度：汉字与全角标点 1，西文字符 0.5；行内公式按去掉命令后的字符折算。"""
    s = plain(s)
    s = re.sub(r"\$\$.*?\$\$", "", s, flags=re.S)
    s = re.sub(r"\$([^$]+)\$", lambda m: "x" * len(re.sub(r"\\[a-zA-Z]+|[{}^_\\ ]", "", m.group(1))), s)
    cjk = len(re.findall(r"[　-〿一-鿿＀-￯“”‘’—…·]", s))
    asc = len(re.findall(r"[\x21-\x7e]", s))
    return cjk + 0.5 * asc + 0.25 * s.count(" ")


def word_count(s):
    """与项目以往口径一致：汉字＋中文标点＋西文词，不含公式和图片。"""
    s = re.sub(r"\$\$.*?\$\$", "", s, flags=re.S)
    s = re.sub(r"\$[^$\n]+\$", "", s)
    s = plain(s)
    return (len(re.findall(r"[一-鿿]", s)) + len(re.findall(r"[，。、；：？！“”‘’（）《》—…·]", s))
            + len(re.findall(r"[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*", s)))


# ---------- 解析 ----------
LIST_RE = r"^\s*([-*]|\d+\.) "


def parse(text):
    lines, i, blocks = text.split("\n"), 0, []
    while i < len(lines):
        l = lines[i]
        st = l.strip()
        if not st:
            i += 1; continue
        if st.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            blocks.append(["code", "\n".join(lines[i:j + 1])]); i = j + 1; continue
        if st.startswith("$$"):
            if st != "$$" and st.endswith("$$") and len(st) > 4:
                blocks.append(["math", l]); i += 1; continue
            j = i + 1
            while j < len(lines) and not lines[j].strip().endswith("$$"):
                j += 1
            blocks.append(["math", "\n".join(lines[i:j + 1])]); i = j + 1; continue
        m = re.match(r"^(#{1,4}) (.*)", l)
        if m:
            blocks.append(["h%d" % len(m.group(1)), l]); i += 1; continue
        if st.startswith("!["):
            blocks.append(["img", st]); i += 1; continue
        if st.startswith("<summary"):
            blocks.append(["para", "**" + re.sub(r"<[^>]+>", "", st) + "**"]); i += 1; continue
        if st.startswith("<details") or st.startswith("</details"):
            i += 1; continue
        if l.startswith("|"):
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            blocks.append(["table", "\n".join(lines[i:j])]); i = j; continue
        if l.startswith(">"):
            j = i
            while j < len(lines) and lines[j].startswith(">"):
                j += 1
            blocks.append(["quote", "\n".join(lines[i:j])]); i = j; continue
        if re.match(LIST_RE, l):
            j = i
            while j < len(lines) and lines[j].strip() and (re.match(LIST_RE, lines[j]) or lines[j].startswith("  ")):
                j += 1
            blocks.append(["list", "\n".join(lines[i:j])]); i = j; continue
        j = i
        while j < len(lines) and lines[j].strip() and not re.match(r"^(#|```|\||>|!\[|\$\$|<details|</details|<summary)", lines[j].strip()) \
                and not re.match(LIST_RE, lines[j]):
            j += 1
        if j == i:
            j = i + 1
        blocks.append(["para", "\n".join(lines[i:j])]); i = j
    return blocks


def image_size(path: Path):
    if path.suffix.lower() == ".svg":
        t = path.read_text(encoding="utf-8", errors="ignore")[:2000]
        m = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', t)
        if m:
            return float(m.group(1)), float(m.group(2))
        w = re.search(r'width="([\d.]+)', t); h = re.search(r'height="([\d.]+)', t)
        return (float(w.group(1)), float(h.group(1))) if w and h else (800, 500)
    with Image.open(path) as im:
        return im.size


def img_lines(path: Path, caption: str):
    w, h = image_size(path)
    ratio = h / w
    width = 120 if ratio <= 0.9 else 85            # 横图按 12 cm、竖图按 8.5 cm 宽排
    height = min(width * ratio, 150)
    cap = math.ceil(width_units(caption) / (CPL * 1.15)) * 0.85
    return height / LINE_MM + cap + 1.2


def block_lines(kind, src, base: Path):
    if kind == "h1":
        return 8
    if kind == "h2":
        return 3
    if kind == "h3":
        return 2.0
    if kind == "h4":
        return 1.8
    if kind == "para":
        return math.ceil(width_units(src) / CPL) + 0.1
    if kind == "quote":
        return sum(math.ceil(width_units(x.lstrip("> ")) / (CPL - 3)) for x in src.split("\n") if x.strip("> ")) + 0.5
    if kind == "list":
        items = re.split(r"\n(?=\s*(?:[-*]|\d+\.) )", src)
        return sum(math.ceil(width_units(x) / (CPL - 2)) + 0.15 for x in items) + 0.3
    if kind == "code":
        body = src.split("\n")[1:-1]
        return sum(max(1, math.ceil(width_units(x) / (CPL * 1.1))) for x in body) + 1.2
    if kind == "math":
        return 2.6 + src.count("\\\\") * 1.2
    if kind == "table":
        rows = [r for r in src.split("\n") if not re.match(r"^\|\s*:?-", r)]
        ncol = max(1, rows[0].count("|") - 1)
        colw = CPL * 1.15 / ncol
        tot = 1.2
        for r in rows:
            cells = [c for c in r.strip().strip("|").split("|")]
            tot += max(1, max(math.ceil(width_units(c) / colw) for c in cells)) * 0.95 + 0.3
        return tot
    return 1


# ---------- 渲染 ----------
def md(src):
    toks = []

    def keep(m):
        toks.append(m.group(0)); return f"@@M{len(toks)-1}@@"
    s = re.sub(r"\$\$.*?\$\$", keep, src, flags=re.S)
    s = re.sub(r"(?<!\\)\$[^$\n]+?\$", keep, s)
    h = markdown.markdown(s, extensions=["tables", "fenced_code"])
    for i, t in enumerate(toks):
        h = h.replace(f"@@M{i}@@", html.escape(t))
    return h


def rel(p: Path):
    return quote(str(p.relative_to(BOOK)))


def figure(path: Path, caption: str, cls="", badge=""):
    b = f'<span class="badge {cls}">{html.escape(badge)}</span>' if badge else ""
    return (f'<figure class="fig {cls}">{b}<img loading="lazy" src="{rel(path)}" alt="{html.escape(caption)}">'
            f'<figcaption>{md(caption)[3:-4] if caption else ""}</figcaption></figure>')


def frame_like(kind, src):
    return kind == "quote" and "本章在框架中的位置" in src


def contract_like(kind, src):
    return kind == "para" and re.match(r"^(读者想知道|读者会问|读者关心的是|读这一章的老师|第一次用 AI 的老师|读者想)", src.strip())


def process(key, path: Path):
    plan = PLAN.get(key, {})
    text = path.read_text(encoding="utf-8")
    blocks = parse(text)
    secs = plan.get("secs", [])
    imgs = plan.get("imgs", [])
    news = plan.get("new", [])
    used_secs, used_imgs = set(), set()
    out_ch = plan.get("out", False)
    pb = TIER_B.get(key, {})
    secsB = pb.get("secs", []) + GLOBAL_B
    imgsB = pb.get("imgs", [])
    activeB = []
    usedB = set()
    active = []
    items = []      # dict(kind, html, lines, frac, label, units, img_cut)
    title = ""
    for kind, src in blocks:
        frac, label = 0.0, ""
        if kind.startswith("h"):
            lvl = int(kind[1]); htxt = src.lstrip("#").strip()
            if lvl == 1:
                title = htxt
            active = [a for a in active if a[0] < lvl]
            for k, (sub, f, lab) in enumerate(secs):
                if sub in htxt:
                    active.append((lvl, f, lab, sub)); used_secs.add(k); break
            activeB = [a for a in activeB if a[0] < lvl]
            for k, (sub, f, lab) in enumerate(secsB):
                if sub in htxt:
                    activeB.append((lvl, f, lab, sub)); usedB.add(k); break
        if active:
            frac, label = active[-1][1], (active[-1][2] or ("整节删或移配套" if active[-1][1] >= 1 else f"压缩约 {int(active[-1][1]*100)}%"))
        if frame_like(kind, src):
            frac, label = 1.0, "框架块：建议删去"
        elif contract_like(kind, src) and frac < 0.7:
            frac, label = 0.7, "读者契约段：建议删去或压成一句"
        if out_ch:
            frac, label = 1.0, ""
        fracB, labelB = frac, ""
        if activeB and activeB[-1][1] > frac:
            fracB, labelB = activeB[-1][1], activeB[-1][2]
        it = dict(kind=kind, frac=frac, label=label, fracB=fracB, labelB=labelB, units=word_count(src) if kind not in ("img",) else 0)
        if kind == "img":
            m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", src)
            cap, s = m.group(1), m.group(2)
            ip = (path.parent / s).resolve()
            it["path"], it["cap"] = ip, cap
            it["lines"] = img_lines(ip, cap) if ip.exists() else 10
            cut = None
            for k, (sub, why) in enumerate(imgs):
                if sub in ip.name:
                    cut = why; used_imgs.add(k); break
            it["img_cut"] = cut is not None and not cut.startswith("保留")
            it["img_why"] = cut or ""
            it["img_cutB"] = it["img_cut"]
            for sub, why in imgsB:
                if sub in ip.name and not it["img_cut"]:
                    it["img_cutB"] = True; it["img_why"] = why
            it["exists"] = ip.exists()
            if out_ch:
                it["img_cut"] = it["img_cutB"] = True
        else:
            it["lines"] = block_lines(kind, src, path.parent)
            it["src"] = src
        items.append(it)
        if kind.startswith("h") and not out_ch:
            htxt = src.lstrip("#").strip()
            for (after, fpath, fcap) in news:
                if after in htxt:
                    fp = BOOK / fpath
                    items.append(dict(kind="newfig", path=fp, cap=fcap, lines=img_lines(fp, fcap), frac=0, label="", fracB=0, labelB="", units=0))
    miss_s = [secs[k][0] for k in range(len(secs)) if k not in used_secs]
    miss_i = [imgs[k][0] for k in range(len(imgs)) if k not in used_imgs]
    miss_s += ["二档:" + x[0] for k, x in enumerate(pb.get("secs", [])) if k not in usedB]
    return dict(key=key, path=path, title=title or path.stem, items=items, plan=plan, miss=(miss_s, miss_i), raw=text)


def stats(ch):
    plan = ch["plan"]
    out_ch = plan.get("out", False)
    b_lines = sum(i["lines"] for i in ch["items"] if i["kind"] != "newfig")
    words_b = sum(i["units"] for i in ch["items"])
    imgs_b = sum(1 for i in ch["items"] if i["kind"] == "img")
    br = 0.5

    def after(tier):
        res = plan.get("residual", 0.06)
        if tier == "B":
            res = max(res, TIER_B.get(ch["key"], {}).get("residual", res))
        fk, ck = ("frac", "img_cut") if tier == "A" else ("fracB", "img_cutB")
        lines = words = 0.0; imgs = newf = 0
        if out_ch:
            return 0, 0, 0, 0
        for i in ch["items"]:
            if i["kind"] == "img":
                if not i[ck]:
                    lines += i["lines"]; imgs += 1
            elif i["kind"] == "newfig":
                lines += i["lines"]; newf += 1; imgs += 1
            else:
                keep = 1 - i[fk]
                lines += i["lines"] * keep * (1 - res)
                words += i["units"] * keep * (1 - res)
        add = ADD_UNITS.get(ch["key"], 0)
        lines += add / CPL * 1.15; words += add
        return lines / LPP + br, words, imgs, newf
    pa, wa, ia, nf = after("A")
    pB, wB, iB, _ = after("B")
    pages_b = b_lines / LPP + br
    return dict(pages_b=pages_b, pages_a=pa, pages_B=pB, lay_b=pages_b * PAGE, lay_a=pa * PAGE, lay_B=pB * PAGE,
                words_b=words_b, words_a=wa, words_B=wB, imgs_b=imgs_b, imgs_a=ia, imgs_B=iB, newf=nf)


# ---------- HTML 片段 ----------
def e(s):
    return html.escape(str(s))


VERDICT_CLS = {"保留": "v-keep", "精简": "v-trim", "合并": "v-merge", "移出正文": "v-out"}


def chapter_html(ch, st, idx):
    plan = ch["plan"]
    v = plan.get("verdict", "保留")
    anchor = f"ch-{idx}"
    parts = [f'<section class="chapter" id="{anchor}">']
    parts.append(f'<div class="ch-card {VERDICT_CLS.get(v,"")}"><div class="ch-head"><span class="verdict">{e(v)}</span>'
                 f'<h2>{e(ch["title"])}</h2></div>')
    if plan.get("why"):
        parts.append(f'<p class="why">{e(plan["why"])}</p>')
    parts.append('<div class="nums">'
                 f'<span>正文 {st["words_b"]:,.0f} 字 → <b>{st["words_a"]:,.0f}</b></span>'
                 f'<span>图 {st["imgs_b"]} → <b>{st["imgs_a"]}</b>{"（含新图 %d）" % st["newf"] if st["newf"] else ""}</span>'
                 f'<span>版面约 {st["pages_b"]:.1f} 页 → 一档 <b>{st["pages_a"]:.1f}</b> 页 → 二档 <b>{st["pages_B"]:.1f}</b> 页</span></div>')
    miss_s, miss_i = ch["miss"]
    if miss_s or miss_i:
        parts.append(f'<p class="warn">方案中未匹配：{e("、".join(miss_s + miss_i))}</p>')
    parts.append("</div>")
    body = []
    if plan.get("out"):
        body.append('<details class="outbox"><summary>本章建议移出正文：点开阅读原文</summary>')
    cur_label, buf = None, []

    def flush():
        nonlocal buf, cur_label
        if not buf:
            return
        if cur_label and not plan.get("out"):
            tier, lab_, fr = cur_label
            cls = ("cut" if fr >= 1 else "trim") + (" tierb" if tier == "B" else "")
            body.append(f'<div class="mark {cls}"><span class="mlabel">{e(lab_)}</span>{"".join(buf)}</div>')
        else:
            body.append("".join(buf))
        buf = []
    for it in ch["items"]:
        k = it["kind"]
        lab = ("A", it["label"], it["frac"]) if it.get("frac", 0) > 0 else (("B", it["labelB"], it["fracB"]) if it.get("fracB", 0) > 0 else None)
        if k == "newfig":
            flush(); cur_label = None
            body.append(figure(it["path"], it["cap"], "new", "新增图")); continue
        if lab != cur_label:
            flush(); cur_label = lab
        if k == "img":
            if not it["exists"]:
                buf.append(f'<p class="warn">图片缺失：{e(it["path"].name)}</p>'); continue
            if it["img_cut"] and not plan.get("out"):
                buf.append(figure(it["path"], it["cap"], "imgcut", "建议删图：" + it["img_why"]))
            elif it.get("img_cutB") and not plan.get("out"):
                buf.append(figure(it["path"], it["cap"], "imgcut tierb", it["img_why"]))
            else:
                note = it["img_why"] if it["img_why"] else ""
                buf.append(figure(it["path"], it["cap"], "", note))
        elif k == "h1":
            continue
        elif k.startswith("h"):
            lvl = int(k[1]) + 1
            htxt = it["src"].lstrip("#").strip()
            buf.append(f"<h{lvl}>{md(htxt)[3:-4]}</h{lvl}>")
        else:
            buf.append(md(it["src"]))
    flush()
    if plan.get("out"):
        body.append("</details>")
    parts.append('<div class="ch-body">' + "".join(body) + "</div></section>")
    return "\n".join(parts)


def bars(chs, sts):
    rows = [(c, s) for c, s in zip(chs, sts)]
    mx = max(s["lay_b"] for _, s in rows)
    W, rowh, L = 760, 22, 150
    h = rowh * len(rows) + 40
    out = [f'<svg class="bars" viewBox="0 0 {W} {h}" role="img" aria-label="各章版面字数，删改前后对比">']
    out.append(f'<text x="{L}" y="14" class="axis">版面字数（万）：灰条＝现稿，蓝条＝一档删改后，紫色竖线＝再加二档（估算）</text>')
    for k, (c, s) in enumerate(rows):
        y = 28 + k * rowh
        wb = (W - L - 60) * s["lay_b"] / mx; wa = (W - L - 60) * s["lay_a"] / mx; wB = (W - L - 60) * s["lay_B"] / mx
        name = c["title"].split("　")[0] if c["title"].startswith("第") else c["title"][:8]
        tip = f'{c["title"]}：现稿 {s["lay_b"]/1e4:.2f} 万 → 一档 {s["lay_a"]/1e4:.2f} 万 → 二档 {s["lay_B"]/1e4:.2f} 万'
        out.append(f'<g><title>{e(tip)}</title><text x="{L-8}" y="{y+12}" text-anchor="end" class="lab">{e(name)}</text>'
                   f'<rect x="{L}" y="{y+2}" width="{wb:.1f}" height="14" rx="3" class="b0"/>'
                   f'<rect x="{L}" y="{y+5}" width="{wa:.1f}" height="8" rx="3" class="b1"/>'
                   f'<rect x="{L+max(wB-2,0):.1f}" y="{y}" width="3" height="18" rx="1" class="b2"/>'
                   f'<text x="{L+wb+6:.1f}" y="{y+13}" class="val">{s["lay_b"]/1e4:.1f} → {s["lay_a"]/1e4:.1f} → {s["lay_B"]/1e4:.1f}</text></g>')
    out.append("</svg>")
    return "".join(out)


PROMPTS = [
    dict(name="P1 篇章页小插图（11 篇，统一风格）", where="各篇的篇章页。篇章页本来就占一页，加图不增加页数。",
         prompt="纸张拼贴风格的扁平插画，米白底，深蓝、橙、青绿三色纸片叠层，有轻微纸张纹理和柔和投影，与本书封面的拼贴风格一致。主体：{主体}。构图居中，四周大量留白，竖版 3:4，适合放在书的篇章页上半部分。画面里不要出现任何文字、数字、字母、公式和刻度；不要人脸特写；器材造型简洁，不追求真实细节。",
         note="{主体} 依次替换：①一台笔记本电脑旁放着一条打点纸带；②滑台在立柱上运动的电梯模型；③从斜面滑下的小车与一扇光电门；④一段圆弧轨道和一个小滑块；⑤浅水槽里的三色小圆环；⑥吸在黑板上的白色电路方块；⑦矩形磁场区域里的一段圆弧轨迹；⑧边缘贴着小磁铁的光盘与线圈；⑨一片光盘反射出的彩虹光带；⑩3D 打印机和一盘小零件；⑪翻开的书与一张折线图。图注统一写“AI 生成的篇章插图”。"),
    dict(name="P2 第 11 章（建议新编号）拼图模块结构分解图", where="替换“建模-Solidworks”界面截图和“侧面磁吸触点”照片，说明一块模块里有什么。",
         prompt="技术插图风格的分解视图（exploded view），白底，细黑描边加浅灰填色。一块方形的白色 3D 打印电路模块，从上到下依次分开：最上层是印着电容器符号的方形贴纸；一只直立的电解电容器；白色方形外壳，四个侧面各有一个圆形孔位；四个侧面的小圆形磁铁和铜色触点；外壳内部两根细导线把电容器两脚分别连到左右两侧的触点。各部件之间用细虚线上下对齐。等轴测视角，横版 3:2。不要出现文字标注和数字（标注由作者后期加）；只用黑、灰、白和少量铜色、蓝色。",
         note="图注必须写“结构示意（AI 生成），不是实物照片”；生成后由严力耕老师核对触点与导线位置，不对就改提示词，不用这张图冒充实物。"),
    dict(name="P3 第 14 章（建议新编号）转盘装置示意", where="放在“波形的样子说明线圈离光盘不近”一节，配合新图 F3 说明线圈距离。",
         prompt="简洁的教学示意插图，白底，等轴测视角：一张竖直放置的光盘，边缘一小段贴着一排方形小磁铁，光盘中心连着一个小型减速电机；光盘正前方隔开一段距离放着一个红色线圈，线圈轴线水平，正对磁铁经过的位置；线圈两根引线接到一个小盒子上。用一个弯曲箭头表示光盘的转动方向，用一条两端带箭头的虚线标出线圈与光盘之间的距离。扁平线稿，少量蓝、橙配色。不要文字和数字。",
         note="图注写“结构示意（AI 生成）”，距离数字由作者在图注里补（模拟中约 15 cm 时波形与实测相像）。"),
]


CSS = """
:root{--bg:#fbfaf7;--paper:#ffffff;--ink:#1f1f1d;--ink2:#52514e;--muted:#8a8984;--line:#e4e3df;--accent:#2a78d6;--warn:#b5432f;
--keep:#1baf7a;--trim:#d48a00;--merge:#4a3aa7;--out:#b5432f;--cutbg:#fbecea;--trimbg:#fff6e0;--newbg:#eaf2fc}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#171716;--paper:#1f1f1d;--ink:#f1f0ea;--ink2:#c3c2b7;--muted:#8f8e88;--line:#3a3a37;--cutbg:#3a2522;--trimbg:#3a3220;--newbg:#1d2b3d}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.85 "Songti SC","Noto Serif CJK SC","Source Han Serif SC",serif}
.wrap{display:grid;grid-template-columns:260px minmax(0,1fr);max-width:1240px;margin:0 auto}
nav.toc{position:sticky;top:0;height:100vh;overflow:auto;padding:18px 14px;border-right:1px solid var(--line);font:13px/1.6 "PingFang SC",sans-serif}
nav.toc a{color:var(--ink2);text-decoration:none;display:block;padding:2px 6px;border-radius:4px}nav.toc a:hover{background:var(--line)}
nav.toc .grp{margin:12px 0 4px;color:var(--muted);font-weight:600}
nav.toc .tag{font-size:11px;padding:0 5px;border-radius:3px;margin-left:4px;color:#fff}
main{padding:28px 40px 120px;min-width:0}
h1{font:600 30px/1.3 "PingFang SC",sans-serif;margin:0 0 6px}
.sub{color:var(--ink2);font:14px/1.6 "PingFang SC",sans-serif;margin-bottom:24px}
section.part{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:22px 28px;margin:22px 0}
section.part>h2{font:600 22px/1.4 "PingFang SC",sans-serif;margin:0 0 12px}
section.part h3{font:600 17px/1.5 "PingFang SC",sans-serif;margin:20px 0 8px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:12px 0}
.tile{border:1px solid var(--line);border-radius:10px;padding:12px 14px;font-family:"PingFang SC",sans-serif}
.tile .k{font-size:12.5px;color:var(--ink2)}.tile .v{font-size:26px;font-weight:600}.tile .d{font-size:12px;color:var(--muted)}
table{border-collapse:collapse;width:100%;font:13.5px/1.6 "PingFang SC",sans-serif;margin:10px 0;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:5px 8px;vertical-align:top;text-align:left}th{background:var(--bg)}
.bars{width:100%;height:auto;font-family:"PingFang SC",sans-serif}.bars .lab{font-size:11.5px;fill:var(--ink2)}.bars .val{font-size:11px;fill:var(--ink2)}
.bars .axis{font-size:12px;fill:var(--ink2)}.bars .b0{fill:#c9c8c2}.bars .b1{fill:var(--accent)}.bars .b2{fill:#4a3aa7}
.sample{border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:12px 0}
.sample .lab{font:600 13px "PingFang SC",sans-serif;color:var(--ink2);margin-top:6px}
.orig{background:var(--cutbg);padding:6px 10px;border-radius:6px}.final{background:var(--newbg);padding:6px 10px;border-radius:6px}
.chapter{background:var(--paper);border:1px solid var(--line);border-radius:12px;margin:26px 0;overflow:hidden}
.ch-card{padding:18px 26px;border-bottom:1px solid var(--line);border-left:6px solid var(--muted);font-family:"PingFang SC",sans-serif}
.ch-card.v-keep{border-left-color:var(--keep)}.ch-card.v-trim{border-left-color:var(--trim)}.ch-card.v-merge{border-left-color:var(--merge)}.ch-card.v-out{border-left-color:var(--out)}
.ch-head{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}.ch-head h2{font-size:21px;margin:0}
.verdict{font-size:12.5px;padding:2px 8px;border-radius:4px;color:#fff;background:var(--muted)}
.v-keep .verdict{background:var(--keep)}.v-trim .verdict{background:var(--trim)}.v-merge .verdict{background:var(--merge)}.v-out .verdict{background:var(--out)}
.why{margin:8px 0;font-size:14.5px;line-height:1.75}.nums{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--ink2)}
.ch-body{padding:8px 34px 24px}.ch-body h3{font:600 19px/1.5 "PingFang SC",sans-serif;margin:26px 0 8px}.ch-body h4,.ch-body h5{font:600 16px/1.5 "PingFang SC",sans-serif;margin:18px 0 6px}
.ch-body blockquote{border-left:3px solid var(--line);margin:10px 0;padding:2px 14px;color:var(--ink2)}
.ch-body pre{background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:10px 12px;white-space:pre-wrap;font:13.5px/1.7 "PingFang SC",monospace}
.mark{position:relative;border-radius:8px;padding:8px 12px 4px;margin:10px -12px}
.mark.cut{background:var(--cutbg)}.mark.cut>*:not(.mlabel){opacity:.62}.mark.trim{background:var(--trimbg)}
.mlabel{display:inline-block;font:600 12px/1.5 "PingFang SC",sans-serif;color:#fff;background:var(--out);border-radius:4px;padding:1px 8px;margin-bottom:4px}
.mark.trim .mlabel{background:var(--trim)}.mark.tierb{background:#efedfb;outline:1px dashed #4a3aa7}.mark.tierb .mlabel{background:#4a3aa7}.mark.tierb>*:not(.mlabel){opacity:.85}
.badge.imgcut.tierb{background:#4a3aa7}figure.imgcut.tierb img{outline-color:#4a3aa7;opacity:.7}
figure.fig{margin:16px auto;max-width:640px;text-align:center;position:relative}
figure.fig img{max-width:100%;max-height:520px;border:1px solid var(--line);border-radius:6px;background:#fff}
figcaption{font:13px/1.6 "PingFang SC",sans-serif;color:var(--ink2);text-align:left;margin-top:6px}
figure.imgcut img{opacity:.45;filter:grayscale(.6);outline:3px solid var(--out);outline-offset:2px}
figure.new{background:var(--newbg);padding:10px;border-radius:10px}figure.new img{outline:3px solid var(--accent);outline-offset:2px}
.badge{display:inline-block;font:600 12px/1.5 "PingFang SC",sans-serif;padding:1px 8px;border-radius:4px;margin-bottom:6px;background:var(--line);color:var(--ink2)}
.badge.imgcut{background:var(--out);color:#fff}.badge.new{background:var(--accent);color:#fff}
.outbox summary{cursor:pointer;font:600 14px "PingFang SC",sans-serif;color:var(--out);margin:12px 0}
.warn{color:var(--warn);font:13px "PingFang SC",sans-serif}.legend span{display:inline-block;margin-right:14px;font:13px "PingFang SC",sans-serif}
.sw{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-1px;margin-right:4px}
.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.prompt{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px 12px;font:13.5px/1.7 "PingFang SC",sans-serif;white-space:pre-wrap}
ul.tight li{margin:3px 0}
@media (max-width:900px){.wrap{display:block}nav.toc{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line);max-height:40vh}
main{padding:16px}.ch-body{padding:6px 16px 18px}section.part{padding:16px}.mark{margin:10px -6px}}
"""


def build():
    chs, sts = [], []
    for key, p in files():
        ch = process(key, p)
        chs.append(ch); sts.append(stats(ch))
    tot_b = sum(s["lay_b"] for s in sts); tot_a = sum(s["lay_a"] for s in sts); tot_B = sum(s["lay_B"] for s in sts)
    pg_b = sum(s["pages_b"] for s in sts); pg_a = sum(s["pages_a"] for s in sts); pg_B = sum(s["pages_B"] for s in sts)
    w_b = sum(s["words_b"] for s in sts); w_a = sum(s["words_a"] for s in sts); w_B = sum(s["words_B"] for s in sts)
    i_b = sum(s["imgs_b"] for s in sts); i_a = sum(s["imgs_a"] for s in sts); i_B = sum(s["imgs_B"] for s in sts)
    misses = [(c["key"], c["miss"]) for c in chs if c["miss"][0] or c["miss"][1]]
    frame_units = sum(i["units"] for c in chs for i in c["items"] if i.get("label", "").startswith(("框架块", "读者契约")))
    bykey = {c["key"]: s for c, s in zip(chs, sts)}
    crow, csum = [], 0.0
    for name, why, v in TIER_C:
        pg = bykey[v]["pages_B"] if isinstance(v, str) else v
        if "备选" not in name:
            csum += pg
        crow.append(f"<tr><td>{e(name)}</td><td>{e(why)}</td><td>约 {pg:.1f} 页</td></tr>")
    pg_C = pg_B - csum
    need = TARGET / PAGE
    pk = {"img": 0.0, "table": 0.0, "text": 0.0}
    for c in chs:
        for it in c["items"]:
            if it["kind"] != "newfig":
                pk[it["kind"] if it["kind"] in ("img", "table") else "text"] += it["lines"] / LPP

    toc = ['<nav class="toc"><div class="grp">审阅结论</div>'
           '<a href="#summary">一、结论与版面测算</a><a href="#structure">二、结构：删、并、移</a><a href="#table">三、逐章一览</a>'
           '<a href="#expr">四、表达与可读性</a><a href="#figs">五、配图</a><a href="#notes">六、说明</a><div class="grp">正文（带标注）</div>']
    tagcol = {"保留": "var(--keep)", "精简": "var(--trim)", "合并": "var(--merge)", "移出正文": "var(--out)"}
    for k, c in enumerate(chs):
        v = c["plan"].get("verdict", "保留")
        toc.append(f'<a href="#ch-{k}">{e(c["title"][:22])}<span class="tag" style="background:{tagcol.get(v)}">{e(v[:2])}</span></a>')
    toc.append("</nav>")

    P = []
    P.append(f"""<section class="part" id="summary"><h2>一、结论与版面测算</h2>
<ul class="tight">
<li><b>超得比想象的多，去掉一些图表不够。</b>按 16 开、五号字（每行 {CPL} 字 × 每页 {LPP} 行 = {PAGE} 字/页）逐段、逐图、逐表排算，现稿约 <b>{pg_b:.0f} 页、{tot_b/1e4:.0f} 万版面字</b>，是目标的两倍。正文 {w_b/1e4:.1f} 万字连同小标题、提示词框、列表约占 {pk['text']:.0f} 页；177 张图约 {pk['img']:.0f} 页，160 张表约 {pk['table']:.0f} 页。以前“原稿约 25 万即可”的估计，没有把图、表和段落末行的空白算进去。30 万版面字约 {need:.0f} 页，正文大约只能留 14 万字左右、图 80—90 张。</li>
<li><b>一档（建议都做，读者几乎不损失）</b>：删 23 个框架块和约 20 段读者契约段（共约 {frame_units/1e4:.1f} 万字），删约 90 张截图和重复图（其中 14 张随移出的章节），第 5、13、20 章移出正文，第 14、15 章合并，开发日志和教研论文腔的段落移走。结果约 <b>{pg_a:.0f} 页、{tot_a/1e4:.1f} 万</b>，正文 {w_a/1e4:.1f} 万字，图 {i_a} 张（含新画的 7 张）。</li>
<li><b>二档（会损失一些好东西，需要你取舍）</b>：全书统一删章末“同样的方法还能用在哪里”“课上最值得问的三个问题”和重复的教学目标、板书、解释层次表；高考题整体移到配套讲义；第 23 章再压。结果约 <b>{pg_B:.0f} 页、{tot_B/1e4:.1f} 万</b>。网页正文里用紫色虚线框标出。</li>
<li><b>还差约 {pg_B-need:.0f} 页，要再挑几项（第三档，见第二部分的表）</b>：按表里不带“备选”的几项全做，约 {pg_C:.0f} 页、{pg_C*PAGE/1e4:.1f} 万。出版社的实际版式（图排得小一点、表格用小五号）也会让数字下降，拿到版心参数后把脚本里的 CPL、LPP 改掉重算即可。</li>
<li><b>主线</b>：一线物理老师用 AI 把资源做出来，再用物理把它查清楚、用到课上。离主线最远的是：传感器制作说明（第 5 章，没有标定数据）、没有完整上过课的闭合电路一章（第 13 章）、网站发布操作（第 20 章）、电学误差的教辅式全集（第 15 章后半）、Blender 修订记录（第 19 章）。</li>
<li><b>表达</b>：AI 高频词已经很少，句子也干净。真正的 AI 痕迹是<b>模板</b>：每章同样的框架块、同样的“读者想知道”、同样以“人教版……教师用书写明”开头，还有第 7 章第五节、第 23 章的论文腔和过密的限定句。写得最好的地方都有作者在场：原话、错例、对自己的反省。</li>
<li><b>正文没有改动。</b>本页只是建议；你定下来以后再改源稿，按惯例先存副本。</li>
</ul>
<div class="tiles">
<div class="tile"><div class="k">现稿（估算）</div><div class="v">{tot_b/1e4:.1f} 万</div><div class="d">约 {pg_b:.0f} 页 · 正文 {w_b/1e4:.1f} 万字 · 图 {i_b}</div></div>
<div class="tile"><div class="k">一档删改后</div><div class="v">{tot_a/1e4:.1f} 万</div><div class="d">约 {pg_a:.0f} 页 · 正文 {w_a/1e4:.1f} 万字 · 图 {i_a}</div></div>
<div class="tile"><div class="k">再加二档</div><div class="v">{tot_B/1e4:.1f} 万</div><div class="d">约 {pg_B:.0f} 页 · 正文 {w_B/1e4:.1f} 万字 · 图 {i_B}</div></div>
<div class="tile"><div class="k">再挑第三档</div><div class="v">{pg_C*PAGE/1e4:.1f} 万</div><div class="d">约 {pg_C:.0f} 页；目标 30 万 ≈ {need:.0f} 页</div></div>
</div>
<p class="sub">测算方法：段落按每行 {CPL} 字折行（段末空行照算，段间不加空）；横图按 12 cm 宽、竖图按 8.5 cm 宽，用实际宽高比算高度（单图最高 15 cm），加图注；表格按列宽逐格折行；每章另起页按平均半页计。现有 PDF 共 569 页，版式更松，不能直接换算。各档还假设正文另有 3%—12% 的语言压缩（见各章卡片），这部分是估计；表格与图的数字是按现稿逐个算的。</p>
</section>""")

    toc_rows = []
    for part, items in NEW_TOC:
        toc_rows.append(f'<tr><th colspan="3">{e(part)}</th></tr>')
        for n, o, t in items:
            toc_rows.append(f"<tr><td>第 {e(n)} 章</td><td>原第 {e(o)} 章</td><td>{e(t)}</td></tr>")
    moved_rows = "".join(f"<tr><td>原第 {e(a)} 章</td><td>{e(b)}</td><td>{e(c)}</td><td>{e(d)}</td></tr>" for a, b, c, d in MOVED)
    P.append(f"""<section class="part" id="structure"><h2>二、结构：删、并、移</h2>
<p>站在读者的位置看，这本书的主线是：<b>不会编程的物理老师，从一句话开始让 AI 做出教学资源，再用物理把它查清楚、用到课上。</b>每章都应当回答“做了什么、AI 错在哪里、物理怎样抓住它、课上怎么用”。按这条线，建议目录如下（序言、开始之前、结语和附录不变）：</p>
<table><thead><tr><th>建议章号</th><th>来源</th><th>标题</th></tr></thead><tbody>{"".join(toc_rows)}</tbody></table>
<h3>建议移出正文（先放到别处，不删）</h3>
<table><thead><tr><th>章</th><th>标题</th><th>建议存放位置</th><th>正文里怎样接住</th></tr></thead><tbody>{moved_rows}</tbody></table>
<p class="sub">本轮没有移动任何文件。表中位置只是建议；你确认后再移，移之前按惯例存“修改前”副本。第 4、7、17、23 章主笔王硕、第 6、12、18 章主笔严力耕，删改主笔章节前需要合著者同意；第 14+15 章合并都是黄灿斌的章，不涉及主笔拆分。</p>
<h3>第三档：二档之后还差约 {pg_B-need:.0f} 页，从下面挑</h3>
<table><thead><tr><th>选项</th><th>怎样做</th><th>约省</th></tr></thead><tbody>{"".join(crow)}</tbody></table>
<h3>全书都要处理的两类模板</h3><ul class="tight"><li>{e(GLOBAL_NOTES["frame"])}</li><li>{e(GLOBAL_NOTES["contract"])}</li></ul>
</section>""")

    rows = []
    for k, (c, s) in enumerate(zip(chs, sts)):
        v = c["plan"].get("verdict", "保留")
        rows.append(f'<tr><td><a href="#ch-{k}">{e(c["title"][:26])}</a></td><td><span class="verdict" style="background:{tagcol.get(v)}">{e(v)}</span></td>'
                    f'<td>{s["words_b"]:,.0f} → {s["words_a"]:,.0f} → {s["words_B"]:,.0f}</td><td>{s["imgs_b"]} → {s["imgs_a"]} → {s["imgs_B"]}</td>'
                    f'<td>{s["lay_b"]/1e4:.2f} → {s["lay_a"]/1e4:.2f} → {s["lay_B"]/1e4:.2f}</td></tr>')
    rows.append(f'<tr><th>合计</th><th></th><th>{w_b:,.0f} → {w_a:,.0f} → {w_B:,.0f}</th><th>{i_b} → {i_a} → {i_B}</th><th>{tot_b/1e4:.1f} → {tot_a/1e4:.1f} → {tot_B/1e4:.1f}</th></tr>')
    P.append(f"""<section class="part" id="table"><h2>三、逐章一览</h2>
<div class="legend"><span><i class="sw" style="background:var(--keep)"></i>保留（小删）</span><span><i class="sw" style="background:var(--trim)"></i>精简</span><span><i class="sw" style="background:var(--merge)"></i>合并</span><span><i class="sw" style="background:var(--out)"></i>移出正文</span></div>
{bars(chs, sts)}
<table><thead><tr><th>篇目</th><th>建议</th><th>正文字数（现稿→一档→二档）</th><th>图</th><th>版面字数（万）</th></tr></thead><tbody>{"".join(rows)}</tbody></table>
</section>""")

    det = "".join(f"<h3>{e(cat)}</h3><ul class='tight'>" + "".join(f"<li>{e(x)}</li>" for x in xs) + "</ul>" for cat, xs in DETECT)
    emp = "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td></tr>" for a, b in EMPTY)
    sam = "".join(f"""<div class="sample"><b>{e(s['ch'])}</b>
<div class="lab">原文</div><div class="orig">{e(s['orig'])}</div>
<div class="lab">问题</div><div>{e(s['issue'])}</div>
<div class="lab">第一版</div><div>{e(s['v1'])}</div>
<div class="lab">反查：还像 AI 吗</div><div>{e(s['check'])}</div>
<div class="lab">建议定稿</div><div class="final">{e(s['final'])}</div></div>""" for s in SAMPLES)
    good = "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td></tr>" for a, b, c in GOOD)
    rd = "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td></tr>" for a, b in READER)
    P.append(f"""<section class="part" id="expr"><h2>四、表达与可读性</h2>
<p>按项目里新存的 <code>zh-ai-trace-editor</code> 技能处理：先做检测报告，再标出正确但没有信息量的句子，最后给出改写示例（每例都删去 20% 以上，并反查一次）。整体判断：<b>这本书没有明显的“AI 词汇味”，不要逐句硬改；该动的是模板和论文腔。</b></p>
<h3>1. 检测报告（不改，先列）</h3>{det}
<h3>2. 正确但没有信息量的句子（可直接删）</h3><table><tbody>{emp}</tbody></table>
<h3>3. 改写示例</h3>{sam}
<h3>4. 写得好、建议原样保留的地方（声音样本）</h3><p class="sub">以后改稿时拿这些段落校准句长和口吻：短句、长句、口语混用，有人、有错、有数字。</p>
<table><thead><tr><th>位置</th><th>段落</th><th>好在哪里</th></tr></thead><tbody>{good}</tbody></table>
<h3>5. 读者视角的可读性问题</h3><table><tbody>{rd}</tbody></table>
<h3>6. WorkBuddy 与 DeepSeek Harness 操作：哪些可以不要</h3>
<ul class="tight">
<li><b>留</b>：第 1 章装好 WorkBuddy、认三个区、建 input/output、第一句话、找到真正的文件——这是零门槛起步，不能删。第 2 章“新开任务只交原始材料”的复查做法。各章“先让 AI 列条件、我确认再做”的提问方式。</li>
<li><b>删或移附录 C</b>：权限确认、文件卡片、应用管理入口、缓存与版本号、烧录卡点表、蓝牙服务编号、网页发布与恢复的逐步操作（第 1、3、4、8、9、14、20 章）。</li>
<li><b>DeepSeek Harness（第 19 章器件建模）</b>：正文现在写作“另一个能调用本机软件的 AI 编程工具”，读者不知道是什么、能不能装。建议只留三条可迁移的方法（先做环境检查；按部件写反馈：数脚数、量尺寸；重新打开工程核对），把 16 分钟、修订 1/2/3、渲染引擎改名、亮线反射这些过程记录移配套包；并在《开始之前》说明这一处用的是哪个工具、读者用 WorkBuddy 同样可以做，只是要多改几轮。</li>
<li><b>“由 AI 按作者授权代为操作”“没有在 WorkBuddy 里完整重跑”</b>：集中到《开始之前》一处，正文不再逐章交代。</li>
</ul>
</section>""")

    newfigs = [("F1-区间取舍-遮光片宽度.svg", "第 3 章“遮光片该选多宽”", "把表格变成两条交叉的线；第 4、6 章同一取舍回指它。"),
               ("F2-电梯下降三段.svg", "第 6 章第三节", "速度、加速度、视重三行对齐，一眼看出“看加速度，不看速度方向”。"),
               ("F3-采样混叠-147转.svg", "第 17 章“峰值为什么一会儿高、一会儿低”", "把文字推理画出来：采样点每圈后移，约 5 s 轮回。"),
               ("F4-核查路线.svg", "第 2 章开头，替换 AI 概念图", "每个追查节点都挂着书里一个真实错例。"),
               ("F5-全书地图.svg", "《开始之前》，替换 AI 概念图", "载体 × 章节，实心表示有完整真实课例；读者据此选读。"),
               ("F6-水槽移板四格合一.jpg", "第 11 章水槽移板演示", "四张截图合一，读数局部放大保留，省一页多。"),
               ("F7-力传感器信号链.svg", "第 6 章第二节（第 5 章移出后）", "一张图交代压力传感器从力到读数的六步。")]
    gal = "".join(f'<div>{figure(HERE/"新图"/f, "**"+w+"**："+why, "new", "新增图")}</div>' for f, w, why in newfigs)
    pr = "".join(f"""<div class="sample"><b>{e(p['name'])}</b><div class="lab">用在哪里</div><div>{e(p['where'])}</div>
<div class="lab">提示词（可直接交给 gpt-image）</div><div class="prompt">{e(p['prompt'])}</div><div class="lab">说明</div><div>{e(p['note'])}</div></div>""" for p in PROMPTS)
    P.append(f"""<section class="part" id="figs"><h2>五、配图</h2>
<h3>1. 删图原则</h3>
<ul class="tight">
<li><b>界面截图只在“界面就是要讲的对象”时留</b>，而且裁到局部。16 开版心约 14 cm 宽，整屏截图里的字印出来只有 1—2 mm。全书约六七十张截图，建议删去大半。</li>
<li><b>同一内容只留一张</b>：序言与第 8、9、10、11 章重复的 4 张、第 2 章与第 11 章重复的红线试稿、第 8 章三张几乎一样的弹簧截图。</li>
<li><b>AI 概念图换成信息图</b>：两张 GPT 概念图（四类载体、教师核查 AI）只有气氛，没有信息，换成新图 F4、F5。封面保留。</li>
<li><b>真实照片优先留</b>：装置、实测、学生手写笔记、课堂现场，这些是证据，AI 画不出来。</li>
</ul>
<p>按各章卡片里的标注，图从 {i_b} 张减到 {i_a} 张（含新增 7 张）。每张建议删的图在正文里都灰显并标了理由。</p>
<h3>2. 我画好的新图（数据全部取自书稿，未新增测量）</h3>
<div class="gallery">{gal}</div>
<p class="sub">源文件与重画脚本在 <code>编务/全书审阅-20261108/新图/</code> 与 <code>画新图.py</code>。颜色按色盲安全的参考调色板，线型另有实线／虚线区分，黑白印刷也能分清。</p>
<h3>3. 适合文生图的三处（提示词给你，我没有调用）</h3>
<p class="sub">这三张需要立体感或统一插画风格，SVG 画不好。按工作区规则，AI 图必须在图注里写明“AI 生成／结构示意”，不能冒充装置照片；P2 生成后要请严力耕老师核对结构。</p>
{pr}
</section>""")

    miss_html = "".join(f"<li>{e(k)}：{e('、'.join(a+b))}</li>" for k, (a, b) in misses) or "<li>无</li>"
    P.append(f"""<section class="part" id="notes"><h2>六、说明</h2>
<ul class="tight">
<li>本页只读取 <code>正文/</code> 下的现役源稿，<b>没有修改任何正文、图片、配套包或 Word/PDF</b>。</li>
<li>正文里的标注：<span class="mlabel" style="background:var(--out)">红</span> 一档，整节建议删或移到配套／附录（文字灰显）；<span class="mlabel" style="background:var(--trim)">黄</span> 一档，建议压缩，比例写在标签上；<span class="mlabel" style="background:#4a3aa7">紫</span> 二档，要压到 30 万才删；红框灰显的图为一档删图，紫框为二档删图；蓝框为新增图。</li>
<li>重新生成：<code>/opt/anaconda3/bin/python 编务/全书审阅-20261108/构建审阅页.py</code>；删改方案在同目录 <code>审阅方案.py</code>，改了方案重跑即可得到新的测算。</li>
<li>方案中未匹配到的小标题或图片（应为空）：<ul>{miss_html}</ul></li>
<li>新增技能：<code>.agents/skills/zh-ai-trace-editor/SKILL.md</code>（Claude Code 通过 <code>.claude/skills/</code> 链接读取），本轮表达审读按它的流程做。</li>
</ul></section>""")

    body = "\n".join(P) + "\n".join(chapter_html(c, s, k) for k, (c, s) in enumerate(zip(chs, sts)))
    doc = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>全书审阅与删改建议</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
 onload="renderMathInElement(document.body,{{delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}}],throwOnError:false}})"></script>
<style>{CSS}</style></head><body><div class="wrap">{"".join(toc)}<main>
<h1>全书审阅与删改建议</h1><div class="sub">2026-11-08 · 对象：现役 23 章稿（序言、开始之前、23 章、结语、附录 A—E、参考文献）· 目标：版面字数 30 万 · 本页含全书正文与图片，建议删改处已在正文中标出</div>
{body}</main></div></body></html>"""
    OUT.write_text(doc, encoding="utf-8")
    summary = dict(pages_before=round(pg_b, 1), pages_after=round(pg_a, 1), pages_B=round(pg_B, 1), pages_C=round(pg_C, 1), layout_before=round(tot_b), layout_after=round(tot_a), layout_B=round(tot_B),
                   words_before=round(w_b), words_after=round(w_a), imgs_before=i_b, imgs_after=i_a, frame_units=round(frame_units), misses=misses,
                   per_chapter=[(c["key"], round(s["lay_b"]), round(s["lay_a"]), round(s["lay_B"]), s["imgs_b"], s["imgs_a"], s["imgs_B"]) for c, s in zip(chs, sts)])
    (HERE / "测算结果.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_chapter"}, ensure_ascii=False))


if __name__ == "__main__":
    build()
