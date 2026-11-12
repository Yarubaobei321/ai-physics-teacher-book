"""二档修订后的审阅页：改后的全书正文与图片、本轮改动、版面字数对比。只读源稿。
运行：/opt/anaconda3/bin/python 构建当前稿审阅页.py
"""
import importlib.util, json, html
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOOK = HERE.parents[1]
spec = importlib.util.spec_from_file_location("b", BOOK / "编务/全书审阅-20261108/构建审阅页.py")
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
b.PLAN, b.TIER_B, b.GLOBAL_B = {}, {}, []
e = html.escape

BEFORE = json.loads((BOOK / "编务/全书审阅-20261108/测算结果.json").read_text(encoding="utf-8"))

CHANGES = {
    "序言": "四张图都与正文重复，留一张；“从哪里读起”改成新章号。",
    "前言": "重写：七个问题去掉章号路标；四类载体配新画的全书地图；新增“用什么工具，谁动的手”，代操作身份只在这里说一次；教材对照表按 16 章更新。",
    "第01章": "原第 23 章理论篇移到书前作第 1 章，按“学生怎样从看见走到学会”重新组织并扩写：概念转变、多重表征与多媒体学习、认知负荷、模型建构与科学论证、实物与模拟的分工，每组理论都讲清它说了什么、落在哪一章、什么时候会失效；再讨论 AI 改变了什么、一节课怎样设计、本书证据的层次。",
    "第02章": "原第 1 章。删框架块、读者契约段、排错一节、两张截图；代操作说明移到《开始之前》。",
    "第03章": "原第 2 章。十种方法的例子改用第 2 章和本章自己的，跨章例子精简；AI 概念图换成新画的核查路线图；复查报告的推导压缩。",
    "第04章": "原第 3、4 章合并。光电门讲测的是时间、速度标在哪一刻、遮光片多宽（配新图）；超声波讲噪声与窗口。蓝牙字节、断线、相同包、字段名、烧录排错表移走。",
    "第05章": "原第 6 章。补一段压力传感器的来历和标定（配信号链图），代替移出的原第 5 章；新增电梯下降三段对齐图；课例的量表、作业、例题和板书压缩或删去。",
    "第06章": "原第 7 章。开头改写；删框架对照表、教学目标、记录单（移配套包）、行动研究、板书、结论层次表和末段总结。",
    "第07章": "原第 8 章。弹簧派生页一步移入配套包，正文留一段和一张图；18 张图删到 9 张；带进课堂压缩。",
    "第08章": "原第 9 章。网站、后台、诊断三节合成一节（约 2 页）；删 7 张网站截图；保留完整教学目标、流程和板书。",
    "第09章": "原第 10 章。删装置演变照片和重复的预测底图；网格漏钢条等开发细节压缩；教学目标和解释层次表删去。",
    "第10章": "原第 11 章。高考题只留水槽移板演示，四张截图合成一张；油滴例题和两道真题移配套讲义；电势游戏压缩，留一张图。",
    "第11章": "原第 12 章。分析页的导入开发细节压缩；删建模截图等 3 张图。",
    "第12章": "原第 14、15 章合并：做减法的故事、视频审错、限流分压的推导与选型、内外接和电动势两处误差。欧姆表、半偏法、电桥等移到配套讲义。",
    "第13章": "原第 17 章。删器材分图和预习单模板，新增采样混叠示意图；课前、作业、误差分析压缩。",
    "第14章": "原第 19 章。去掉 DeepSeek Harness 建模过程及其图片，只留 WorkBuddy 的标注和色环试样；电学器材网页压缩；24 张图删到 8 张。",
    "第15章": "原第 21 章。智学网操作路径压缩。",
    "第16章": "原第 22 章。删两张方框示意图和一张成对截图。",
    "结语": "按新章号重写，删去移出章节的例子。",
    "附录A": "不再按章重印提示词（移到配套包），保留四件事、三句话、反馈格式、补一句表；各章协作方法表按 16 章重排。",
    "附录B": "方法速查表与第 3 章对齐；删去移出章节的条目和题旁模型、发布两组。",
    "附录C": "压到约 3 页，并入原第 20 章的发布要点和检查表。",
    "附录D": "压到 1 页，只列各章需要准备的器材；完整文件索引移到配套包。",
    "附录E": "静电约定和审图清单压缩。",
    "参考文献": "未改。",
}


def main():
    b.PLAN = {k: dict(verdict="本轮已改", why=v, residual=0) for k, v in CHANGES.items()}
    chs = [b.process(k, p) for k, p in b.files()]
    sts = [b.stats(c) for c in chs]
    pg = sum(s["pages_b"] for s in sts); lay = sum(s["lay_b"] for s in sts)
    w = sum(s["words_b"] for s in sts); im = sum(s["imgs_b"] for s in sts)
    need = b.TARGET / b.PAGE
    rows = "".join(f'<tr><td><a href="#ch-{i}">{e(c["title"][:28])}</a></td><td>{e(CHANGES.get(c["key"], ""))}</td>'
                   f'<td>{s["words_b"]:,.0f}</td><td>{s["imgs_b"]}</td><td>{s["pages_b"]:.1f}</td></tr>' for i, (c, s) in enumerate(zip(chs, sts)))
    toc = '<nav class="toc"><div class="grp">本轮</div><a href="#summary">一、结果</a><a href="#changes">二、各篇改了什么</a><a href="#gap">三、离 30 万还差多少</a><a href="#notes">四、说明</a><div class="grp">正文</div>' + \
          "".join(f'<a href="#ch-{i}">{e(c["title"][:22])}</a>' for i, c in enumerate(chs)) + "</nav>"
    summary = f"""<section class="part" id="summary"><h2>一、结果</h2>
<div class="tiles">
<div class="tile"><div class="k">修订前（23 章）</div><div class="v">{BEFORE['layout_before']/1e4:.1f} 万</div><div class="d">约 {BEFORE['pages_before']:.0f} 页 · 正文 {BEFORE['words_before']/1e4:.1f} 万字 · 图 {BEFORE['imgs_before']}</div></div>
<div class="tile"><div class="k">现在（16 章）</div><div class="v">{lay/1e4:.1f} 万</div><div class="d">约 {pg:.0f} 页 · 正文 {w/1e4:.1f} 万字 · 图 {im}</div></div>
<div class="tile"><div class="k">目标</div><div class="v">30 万</div><div class="d">约 {need:.0f} 页，还差约 {pg-need:.0f} 页</div></div>
</div>
<ul class="tight">
<li>按你定的范围做完：一档、二档全部整节删改，加上第三档选中的七项；原第 5、13、16、18、20 章移出正文（原稿和配套材料都保留在编务目录）；原第 3、4 章合成《传感器测速》，原第 14、15 章合成《电学实验》；理论章放到书前作第 1 章并扩写；第 14 章去掉 DeepSeek Harness，只留 WorkBuddy。</li>
<li>全书删去 23 个框架块和各章“读者想知道”段，约 100 张图（截图、重复图和随移出章节去掉的图）；新画的 7 张图已放进正文（全书地图、核查路线、遮光片取舍、电梯三段、信号链、水槽移板四格合一、采样混叠）。</li>
<li>章号、交叉引用、配套包文件夹、配套索引和 ZIP 都已按 16 章同步；全书阅读版已重建（82 图、722 个公式，失效链接、锚点和公式错误均为 0）。</li>
<li>版面测算用的还是上一轮的模型（16 开、每行 38 字×37 行），只是估计；出版社给出版心后可以重算。</li>
</ul></section>"""
    changes = f"""<section class="part" id="changes"><h2>二、各篇改了什么</h2>
<table><thead><tr><th>篇目</th><th>本轮改动</th><th>正文字数</th><th>图</th><th>版面页数</th></tr></thead><tbody>{rows}</tbody></table></section>"""
    gap = f"""<section class="part" id="gap"><h2>三、离 30 万还差多少</h2>
<p>现在约 {lay/1e4:.1f} 万版面字，比 30 万多约 {(lay-b.TARGET)/1e4:.1f} 万，相当于 {pg-need:.0f} 页左右。差距主要来自两处：审阅时假设的 3%—12% 逐句语言压缩这次没有做；一档、二档里“压缩三到六成”的小节，这次只手改了篇幅较大的几十处，小节没有逐个压。可选的办法：</p>
<table><thead><tr><th>办法</th><th>约省</th><th>代价</th></tr></thead><tbody>
<tr><td>全书逐句压缩 6%（按 zh-ai-trace-editor 的流程，只删空转句和重复的限定句）</td><td>约 12 页</td><td>不损失内容，但要逐章读一遍，主笔章节需合著者过目</td></tr>
<tr><td>第 14 章只留色环和卡尺两例（电学器材观察台、磁吸演示台移配套）</td><td>约 6 页</td><td>第三档里你没选这一项</td></tr>
<tr><td>附录 E 移到配套包，正文留一页审图清单</td><td>约 4 页</td><td>画面原则是本书独有的内容，纸书里会少一块</td></tr>
<tr><td>出版社排版时图片用小一号（横图 10 cm 宽）</td><td>约 8 页</td><td>不改稿；截图类的图会更难看清</td></tr>
</tbody></table></section>"""
    notes = """<section class="part" id="notes"><h2>四、说明</h2><ul class="tight">
<li>修改前的全部源稿、目录、配套索引和阅读版在 <code>编务/二档修订-20261108/修改前/</code>（附指纹）；每章删下的原文逐条存在 <code>移出段落/</code>；移出的章节在 <code>移出正文/</code>，移出的配套材料在 <code>移出配套/</code>。</li>
<li>Word 和 PDF 已按 16 章重建（PDF 315 页，用的是原有排版脚本的版式），Word 无 Courier 字体；按既定方式未做 WPS 版面检查。修改前的 23 章 Word/PDF 在 <code>排版更新前/</code>。</li>
<li>按既定的审阅方式，本页只检查了文件、链接和结构，没有做浏览器截图验收。</li>
</ul></section>"""
    import re
    body = "".join(b.chapter_html(c, s, i) for i, (c, s) in enumerate(zip(chs, sts)))
    body = re.sub(r'<div class="nums">.*?</div>', "", body)
    doc = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>二档修订后全书</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
 onload="renderMathInElement(document.body,{{delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}}],throwOnError:false}})"></script>
<style>{b.CSS}</style></head><body><div class="wrap">{toc}<main>
<h1>二档修订后的全书</h1><div class="sub">2026-11-08 · 16 章 · 本页含改后的全书正文与图片</div>
{summary}{changes}{gap}{notes}{body}</main></div></body></html>"""
    (BOOK / "全书审阅-20261108.html").write_text(doc, encoding="utf-8")
    res = dict(pages=round(pg, 1), layout=round(lay), words=round(w), imgs=im)
    (HERE / "测算结果-修订后.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(res)


if __name__ == "__main__":
    main()
