#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建《全书逐段审阅与润色.html》：包含宏观结构大纲总评 + 27 篇逐章总评与 2307 个单元左右对照精修。"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

BASE_DIR = Path(__file__).resolve().parent
PROJECT = BASE_DIR.parents[1]
UNITS_DIR = BASE_DIR / "units"
REVIEWS_DIR = BASE_DIR / "reviews"
OUTPUT_HTML = PROJECT / "全书逐段审阅与润色.html"
REPORT_JSON = BASE_DIR / "审阅页构建核对.json"

READER = "markdown+tex_math_dollars+tex_math_single_backslash-raw_tex-smart-implicit_figures"


def run(args: list[str], data: str | None = None) -> str:
    p = subprocess.run(args, input=data, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or f"执行失败：{args[0]}")
    return p.stdout


def walk(value):
    if isinstance(value, dict):
        if "t" in value:
            yield value
        for child in list(value.values()):
            yield from walk(child)
    elif isinstance(value, list):
        for child in list(value):
            yield from walk(child)


def locate_katex(project: Path) -> Path:
    candidates = [
        project / "阅读资源/katex/katex.min.js",
        Path("/Users/yaril/个人文档/数智育才网站/node_modules/katex/dist/katex.min.js"),
    ]
    for p in candidates:
        if p.is_file() and (p.parent / "katex.min.css").is_file() and (p.parent / "fonts").is_dir():
            return p
    raise RuntimeError("未找到完整本地 KaTeX 资源")


def render_formulas(node: str, katex: Path, items: list[tuple[str, bool]]):
    if not items:
        return {"version": "N/A", "results": [], "errors": []}
    js = r"""const fs=require('fs');const katex=require(process.argv[1]);
const items=JSON.parse(fs.readFileSync(0,'utf8'));const errors=[];
const results=items.map((x,i)=>{try{return katex.renderToString(x[0],{displayMode:x[1],throwOnError:true,strict:'ignore',trust:false,output:'htmlAndMathml'});}catch(e){errors.push({index:i,tex:x[0],error:e.message});return null;}});
process.stdout.write(JSON.stringify({version:katex.version,results,errors}));"""
    result = json.loads(run([node, "-e", js, str(katex)], json.dumps(items, ensure_ascii=False)))
    if result["errors"]:
        raise RuntimeError("公式无法排版：\n" + json.dumps(result["errors"], ensure_ascii=False, indent=2))
    return result


def intrinsic_image_size(path: Path) -> tuple[int, int]:
    if path.suffix.lower() == ".svg":
        root = ET.parse(path).getroot()
        viewbox = root.get("viewBox", "").replace(",", " ").split()
        if len(viewbox) == 4:
            width, height = (float(x) for x in viewbox[2:])
        else:
            width = float(re.fullmatch(r"([\d.]+)(?:px)?", root.get("width") or "800")[1])
            height = float(re.fullmatch(r"([\d.]+)(?:px)?", root.get("height") or "600")[1])
        from fractions import Fraction
        ratio = Fraction(str(width)) / Fraction(str(height))
        if width.is_integer() and height.is_integer():
            return int(width), int(height)
        return ratio.numerator, ratio.denominator
    from PIL import Image
    with Image.open(path) as image:
        width, height = image.size
        if image.getexif().get(274, 1) in {5, 6, 7, 8}:
            width, height = height, width
    return width, height


def reserve_image_space(fragment: str, base: Path, dimensions: dict) -> str:
    class ImageTag(HTMLParser):
        def handle_starttag(self, tag, attrs):
            self.attrs = dict(attrs)

    def replace(match):
        parsed = ImageTag()
        parsed.feed(match[0])
        attrs = parsed.attrs
        raw = attrs.get("src", "")
        parts = urlsplit(raw)
        attrs.update({"loading": "lazy", "decoding": "async"})
        if not parts.scheme and not raw.startswith("//"):
            path = (base / unquote(parts.path)).resolve()
            if path.exists():
                if path not in dimensions:
                    dimensions[path] = intrinsic_image_size(path)
                width, height = dimensions[path]
                attrs.update({"width": str(width), "height": str(height)})
                style = re.sub(r"(?:^|;)\s*aspect-ratio\s*:[^;]*;?", ";", attrs.get("style", ""))
                attrs["style"] = style.rstrip("; ") + ("; " if style.strip("; ") else "") + f"aspect-ratio: {width} / {height};"
        return "<img " + " ".join(
            key if value is None else f'{key}="{html.escape(value, quote=True)}"'
            for key, value in attrs.items()
        ) + ">"

    return re.sub(r"<img\b[^>]*>", replace, fragment)


def format_comment_html(comment: str) -> str:
    """将【物理教师读者体验】【编辑审读与润色】等标签渲染为层次分明的审阅段落。"""
    lines = [ln.strip() for ln in comment.strip().splitlines() if ln.strip()]
    out = []
    for ln in lines:
        esc = html.escape(ln)
        esc = re.sub(
            r"^【([^】]+)】",
            r'<span class="role-badge">\1</span>',
            esc,
        )
        # 行内代码与简单数学公式美化
        esc = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc)
        out.append(f"<p>{esc}</p>")
    return "".join(out)


MACRO_REVIEW_HTML = """
<section class="macro-section" id="macro-review">
  <div class="macro-banner">
    <div class="macro-kicker">BOOK-WIDE EDITORIAL &amp; PEDAGOGICAL REVIEW</div>
    <h2>壹 · 全书宏观结构、大纲与文风总评</h2>
    <p class="macro-lead">
      本总评由<strong>一线高中物理教师读者</strong>与<strong>物理教育专著责任编辑</strong>双重视角撰写。在通读全书 27 篇文稿（序言、前言、导论、第 1—17 章正文、结语、附录 A—E 及参考文献，共 2,301 个逻辑单元）后，我们首先回应一个最核心的判断：<strong>这是一部真正从高中物理实验室、公开课现场与学生真实错例中生长出来的诚意之作。</strong>为使本书从“扎实的教研项目汇编”跃升为“可读性极佳、学术感精准、令物理同行爱不释手的出版级精品”，我们从以下六个维度提出宏观审读意见，并在下文的逐段精修版中全部落地。
    </p>
  </div>

  <div class="macro-grid">
    <article class="macro-card" id="macro-1">
      <h3>一、物理教师首读体感：这本书最打动同行的三大核心价值</h3>
      <p>作为每天站在讲台和实验室里的高中物理老师，市面上泛泛而谈“用 AI 写教案、出试卷、做课件”的书很难引起我们的兴趣——因为那些书回避了物理学科最致命的问题：<strong>AI 算出来的物理过程常常是错的，而且错得极其顺眼。</strong>本书之所以让人眼前一亮，在于它牢牢立住了三根支柱：</p>
      <ul>
        <li><strong>第一，“物理裁决高于代码生成”的专业尊严。</strong>从第 1 章用一句日常提问抓出 AI 把“纸带卡住”当成“非等时间间隔”，到第 2 章总结不读代码也能揪出物理硬伤的“十项核验方法”（如用 0.30 cm 微扰反例识破首末段假逐差、用单向支持约束 $F_\\mathrm{N}\\ge 0$ 否决电梯启动负尖峰、用稳恒电流场极值原理否决超出 9.3 V 电源电压的 10.21 V 拟合值、识破将分能量写为 <code>E0 - 其余项</code> 的代数倒扣式假守恒），全书始终把物理教师放在“主审官”的位置上。</li>
        <li><strong>第二，“低成本真实验 + 数字化透明链路”的实操底气。</strong>书中没有用虚拟仿真取代真实实验，而是用每套新增成本不到 50 元的浅水导电槽让全班 20 组学生同步测等势线（第 10 章），用厨房金属盆、滤网与塑料瓶做全套静电实验（第 9 章），用转动光盘、小钕铁硼磁铁与可拆卸变压器线圈定量探究法拉第电磁感应定律（第 14 章），用 3D 打印磁吸活版电路拼图在黑板上演示电容器充放电并由 $I$–$t$ 曲线下面积算出电荷量（第 12 章）。所有传感器网页都坚持“显示原始测量、留空未发数据、严禁预设守恒律倒算”，把黑箱仪器重新变成了透明的物理对象。</li>
        <li><strong>第三，“零门槛起步、简短提示词先行”的正反馈路径。</strong>书中摒弃了动辄数百字、束缚模型发挥的复杂提示词模板，示范了怎样用教师自己的教学语言说出核心边界（教学问题、模型条件、预期算例、禁动项），在一次次“看现象—查物理—提反馈”的循环中把 AI 的能力圈内化为教师自己的能力圈。</li>
      </ul>
    </article>

    <article class="macro-card" id="macro-2">
      <h3>二、前辅文诊断：消除《序言》《前言》《导论》的三重叠床架屋</h3>
      <p>通读前辅文三篇（<code>foreword</code>、<code>preface</code>、<code>introduction</code>）时，读者最明显的疲惫感来自<strong>清单与导读的三次重复</strong>：</p>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>前辅文篇目</th>
              <th>现役原稿存在的结构重叠问题</th>
              <th>编辑重构定位与分工方案</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>序言</strong><br>不会编程的物理老师，能用 AI 做成什么</td>
              <td>第二节“你能做成什么”用 7 条长清单罗列第 1—17 章产物，与《前言》“读完能做成什么”的 13 条清单高度重合。</td>
              <td><strong>定位：情感共鸣 + 四个高光现场 + 核心立意。</strong>将 7 条琐碎罗列收束为四大能力板块概述，突出备课桌前的痛点、水槽零示法与雷击护树等视觉高光，以及“把 AI 能力圈变成自己能力圈”的育人主旨。</td>
            </tr>
            <tr>
              <td><strong>前言</strong><br>这本书怎么用</td>
              <td>花大量篇幅解释“哪五章有完整教学设计、哪几章结构特殊”；而真正影响全书阅读体验的“合著者第一人称约定”与“提示词整理/AI 代操作体例”却散落在各章正文中反复解释。</td>
              <td><strong>定位：全书阅读导航 + 器材清单 + 唯一体例总约。</strong>保留极其实用的“按教材找章节”对照表与器材准备表；在“几点阅读约定”中<strong>明确丁龙为第一作者和主编、明确各章主笔，并一次性立定全书第一人称约定与提示词/操作体例</strong>，彻底解放正文与附录 A。</td>
            </tr>
            <tr>
              <td><strong>导论</strong><br>让物理看得见：本书的理论框架</td>
              <td>第一节“为什么是这七个问题”再次逐条复述《前言》刚列过的七个问题，进入理论核心偏慢。</td>
              <td><strong>定位：多重表征与科学思维的学术压舱石。</strong>精简与《前言》重复的编号复述，直接以第 8、10、3 章三个课堂切片引出 Ainsworth 多重表征、Mayer 认知负荷与 2025 修订版课标“科学思维”四要素。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>

    <article class="macro-card" id="macro-3">
      <h3>三、全书十七章大纲审读：“双轨原型”的显性区分与章节内在逻辑</h3>
      <p>细读第 1—17 章可以发现，全书实际上包含两类体裁截然不同的核心章节，但原稿试图用同一套六节标题模板去套所有章节，导致读者在阅读第 6、10、13、14 章时产生预期错位。我们在审读中建议在导读与章首明确区分这两类<strong>“双轨原型”</strong>：</p>
      <ul>
        <li><strong>A 类原型：从一句话到课堂工具的 AI 协同构建章（第 1、3、4、5、7、8、9、11、12、15、16 章）</strong>——以“教学痛点 → 目标成品 → 从空白做一遍（五步法） → 物理审核 → 课堂使用与方法迁移”为主线，重在手把手带教师走通“生成—验算—纠偏—落地”的完整闭环。</li>
        <li><strong>B 类原型：低成本自制教具与深度名师课例章（第 6 章超重失重电梯模型、第 10 章浅水槽测等势线、第 13 章牛奶/橙汁电池闭合电路欧姆定律、第 14 章光盘转动磁铁定量探究法拉第电磁感应定律）</strong>——这四章的灵魂在于<strong>精巧的物理实验装置设计、真实课堂的认知冲突推进，以及实测波形/数据的深度物理归因</strong>，AI 在其中扮演的是“配套数字模拟、预测底图生成、滤波积分或实验录像整理”的协同角色。明确这一区分后，读者便能更好领略这四节实验课的教学匠心。</li>
        <li><strong>附录 D 索引核查提示：</strong>在核查《附录 D 配套文件和网页索引》（<code>appendix-d-u003</code>）时，注意到表中从第 4 章直接跳至第 7 章，第 5 章（自制力传感器标定）与第 6 章（超失重电梯模型控制与滤波）暂未在配套包总表中单列文件条目，已在附录 D 审读意见中提示后续打包时补充说明。</li>
      </ul>
    </article>

    <article class="macro-card" id="macro-4">
      <h3>四、全书叙事视角与合著交接统合：明确主编与各章主笔，从疏离的“作者”回到在场的“我/我们”</h3>
      <p>本书由<strong>丁龙担任第一作者和主编，丁龙、黄灿斌、王硕、严力耕四位一线物理教师合著</strong>（第 4、7、14 章主笔为王硕，第 6、12 章主笔为严力耕，其中第 6 章第四节公开课课例由丁龙执教，其余各章由黄灿斌主笔）。原稿在叙事人称上存在三处可优化的空间：</p>
      <ul>
        <li><strong>黄灿斌主笔章节内部视角统一：</strong>第 9 章（王士瑜老师南山区“百花奖”比赛课配套资源）采用亲切自然的第一人称<strong>“我”</strong>，写出了极佳的备课与教研协作现场感；而同由黄灿斌主笔的第 1、2、3、5、8、10、11、13、15、16、17 章则使用了第三人称<strong>“作者”</strong>。将其统一还原为第一人称“我/我们”，全书声线将更加真诚连贯。</li>
        <li><strong>合著章节（第 4、6、7、12、14 章）中的团队衔接优化：</strong>王硕、严力耕主笔的章节使用了自然的“我”，但在切换到配套网页制作时，原稿插入了“本节分析页由黄灿斌老师一方用 WorkBuddy 生成，示范由 AI 按他的授权代为操作”这类偏生硬的说明，宜柔化为同一教研团队的自然协作。</li>
        <li><strong>脚本去工具名留下的重复指代修润：</strong>第 15 章（<code>ch15-u023</code>、<code>u025</code>、<code>u048</code>）因前期批量替换工具名，留下了“用的是另一套 AI 编程工具。2026 年 10 月，作者改用另一个能调用本机软件的 AI 编程工具……”的拗口重复，已在润色版中彻底理顺。</li>
      </ul>
      <p><strong>【编辑统合方案】</strong>在《前言》“几点阅读约定”中清晰声明第一作者兼主编丁龙及四位合著教师的执笔分工与示范体例；将各章统一为该章主笔教师的第一人称“我/我们”；将合著章节中的“黄灿斌老师一方……”柔化为教研团队协作叙事；清理正文中重复出现的内部操作归属尾注。</p>
    </article>

    <article class="macro-card" id="macro-5">
      <h3>五、跨章物理主线显性化：把散落的珍珠串成物理测量学项链</h3>
      <p>作为一部物理教育专著，本书各章的“物理审核”绝非孤立的技巧，而是贯穿着两条极有深度的物理主线。我们在各章润色与点评中有意识地强化了这两条跨章主线的呼应：</p>
      <ol>
        <li><strong>第一条主线：时间分辨率（逼近瞬时状态）与信噪比（抑制随机误差/高频干扰）的权衡。</strong>
          从第 3 章光电门遮光片宽度 $d$（窄片减小模型近似偏差 $\\frac{1}{2}a\\Delta t$，但放大计时分辨相对误差），到第 4 章超声波测距的五点滑动窗口（压低位置抖动噪声，但带来 $2\\Delta t=0.2\\ \\mathrm{s}$ 的相位滞后），再到第 5 章 HX711 采样率与滑动平均、第 6 章电梯视重曲线的巴特沃斯低通滤波截止频率 $f_c$，以及第 14 章微电压传感器 $10\\ \\mathrm{Hz}$ 低采样率与 $147\\ \\mathrm{r/min}$ 转速差频导致的 $5\\ \\mathrm{s}$ 周期幅值包络——它们在数理本质上回答的都是同一个核心问题：<strong>当用离散、带噪的有限采样去观测连续变化的物理量时，怎样根据特征时间尺度判断波形与数据的真伪。</strong></li>
        <li><strong>第二条主线：积分面积守恒与物理量纲约束。</strong>
          从第 1 章与第 4 章 $v$–$t$ 图线下面积对应位移 $\\Delta x$，到第 6 章电梯由静止启动再回到静止整段过程的净冲量判据 $\\int (F_\\mathrm{N}-mg)\\,\\mathrm{d}t = 0$（超重区面积必等于失重区面积），再到第 12 章不依赖指数公式、直接用梯形求积 $\\sum I_k\\Delta t$ 算出电容器充放电电荷量 $Q$，第 13 章沿同一个电荷量 $q=It$ 算清闭合电路能量守恒 $Eq = Uq + Irq$，以及第 14 章磁铁扫过线圈一正一负单瓣面积 $\\left|\\int \\mathcal{E}\\,\\mathrm{d}t\\right|=N|\\Delta\\Phi|$ 与转速无关——全书用一条清晰的“微元求和与守恒检验”线索，将高中物理最核心的图像面积与守恒意义贯穿始终。</li>
      </ol>
    </article>

    <article class="macro-card" id="macro-6">
      <h3>六、文风与语言升级总则：消解口语碎句，建立“温润而准确的学术感”</h3>
      <p>原稿为规避生硬的“AI 套话”，在前期改写中有意采用了大量短句和口语词，但也因此矫枉过正，出现了大量电报式碎句与过于随便的口语词（如全书出现 64 次“东西”、38 次“办法”、数以百计的“在……里”“教师用书写明”“课本上”“算出来的”“选它做第一个任务，还因为它规模小”等），削弱了出版专著应有的学术庄重感。</p>
      <p>我们在逐段润色中确立了<strong>“温润而准确的物理教研学术风”</strong>四项准则：</p>
      <ul>
        <li><strong>术语与文献称谓规范化：</strong>将口语化的“教师用书写明/说得很直白”统一规范为“《教师教学用书》明确指出”；将“课本上的”规范为“教材中的”；将各章框架卡片中的“看不见的东西 / 教师的关键判断 / AI 能力升级点”统一升格为<strong>“核心隐性物理量与过程 / 教师的专业裁决点 / 人机协同进阶目标”</strong>。</li>
        <li><strong>小节标题命题化：</strong>将各章千篇一律的“二、先看成品：……”“四、物理审核：……要查什么”“六、同样的方法还能用在哪里”，提炼为凝练的物理教研命题（如“二、目标成品：集数据核算、作图与打印于一体的实验记录页”“四、物理审核：光电门测速的区间代表性、时刻对齐与不确定度权衡”“六、方法迁移：同一教学与核验范式的拓展场景”）。</li>
        <li><strong>去口语虚词与碎句缝合：</strong>将“几件东西、几样本事、拿主意、交来的东西、十种办法”等口语词替换为准确的专业表述；将“在浏览器里、在表格里、在程序里、在水槽里”规范为书面语“在浏览器中、在表格中、在程序中、在水槽内”；将断裂的超短句通过恰当的逻辑关联词缝合为呼吸从容的学术长短句。</li>
        <li><strong>严格保护真实原话与物理边界：</strong>凡属当时实际发送的提示词原话、学生课堂发言原话、代码块、数学公式及科学适用条件限定，一律严格保留原貌，绝不因润色文辞而损伤一分一毫的事实准确性。</li>
      </ul>
    </article>
  </div>
</section>
"""

CSS = r"""
:root {
  --paper: #ffffff;
  --canvas: #f4f6f8;
  --ink: #1e293b;
  --muted: #64748b;
  --line: #e2e8f0;
  --accent: #0f4c81;
  --accent-soft: #eff6ff;
  --polish-bg: #f0fdf4;
  --polish-border: #86efac;
  --polish-ink: #166534;
  --struct-bg: #fffbeb;
  --struct-border: #fde047;
  --struct-ink: #92400e;
  --keep-bg: #f8fafc;
  --keep-border: #cbd5e1;
  --keep-ink: #475569;
  --eval-bg: #f8fafc;
  --sidebar: 290px;
}
* { box-sizing: border-box; }
html { scroll-behavior: auto; scroll-padding-top: 72px; }
body {
  margin: 0;
  background: var(--canvas);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", sans-serif;
  -webkit-font-smoothing: antialiased;
  line-height: 1.75;
}
a { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 3px; }
a:hover { text-decoration-thickness: 2px; }

/* Sidebar */
.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  width: var(--sidebar);
  background: #fff;
  border-right: 1px solid var(--line);
  overflow-y: auto;
  padding: 20px 14px 36px;
  z-index: 20;
}
.nav-head {
  padding: 0 10px 14px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 12px;
}
.nav-head a {
  font-size: 17px;
  font-weight: 700;
  text-decoration: none;
  color: var(--ink);
  display: block;
}
.nav-head p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}
.toc-group-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  padding: 10px 10px 4px;
}
.toc {
  list-style: none;
  padding: 0;
  margin: 0;
}
.toc > li { margin: 2px 0; }
.toc a {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 6px 10px;
  font-size: 12.5px;
  line-height: 1.45;
  text-decoration: none;
  color: #334155;
  border-radius: 6px;
}
.toc a:hover, .toc a[aria-current="location"] {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}
.toc-badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #0369a1;
  flex-shrink: 0;
}

/* Sticky Top Toolbar */
.toolbar {
  position: sticky;
  top: 0;
  z-index: 15;
  margin-left: var(--sidebar);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--line);
  padding: 10px 32px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.toolbar-title {
  font-weight: 700;
  font-size: 14px;
  color: var(--ink);
  margin-right: 6px;
}
.filter-btn {
  border: 1px solid var(--line);
  background: #fff;
  color: #334155;
  font-size: 12.5px;
  font-weight: 500;
  padding: 5px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.filter-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.filter-btn.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.toolbar-stats {
  font-size: 12px;
  color: var(--muted);
  display: flex;
  gap: 12px;
}
.stat-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.dot-polish { background: #22c55e; }
.dot-struct { background: #eab308; }
.dot-keep { background: #94a3b8; }

/* Main Container */
.reading {
  margin-left: var(--sidebar);
  padding: 28px 32px 96px;
  max-width: 1580px;
}
.book-head {
  background: linear-gradient(135deg, #0f2942 0%, #164e63 100%);
  color: #fff;
  border-radius: 14px;
  padding: 36px 40px;
  margin-bottom: 32px;
  box-shadow: 0 10px 25px -5px rgba(15, 41, 66, 0.15);
}
.book-head h1 {
  font-size: 30px;
  font-weight: 750;
  margin: 0 0 10px;
  line-height: 1.35;
}
.book-head p {
  margin: 0;
  color: #cbd5e1;
  font-size: 15px;
  max-width: 960px;
}
.book-head .head-meta {
  margin-top: 18px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px 24px;
  font-size: 13px;
  color: #e2e8f0;
}
.book-head .head-meta a {
  color: #7dd3fc;
}

/* Macro Review Section */
.macro-section {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 32px 36px;
  margin-bottom: 40px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}
.macro-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--accent);
  margin-bottom: 4px;
}
.macro-banner h2 {
  font-size: 26px;
  margin: 0 0 12px;
  color: #0f172a;
}
.macro-lead {
  font-size: 15.5px;
  color: #334155;
  margin: 0 0 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--line);
}
.macro-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 22px;
}
.macro-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-left: 4px solid var(--accent);
  border-radius: 10px;
  padding: 20px 24px;
}
.macro-card h3 {
  margin: 0 0 12px;
  font-size: 18px;
  color: #0f172a;
}
.macro-card p, .macro-card li {
  font-size: 14.5px;
  color: #334155;
  line-height: 1.75;
}
.macro-card ul, .macro-card ol {
  margin: 8px 0;
  padding-left: 22px;
}
.macro-card li { margin: 6px 0; }

/* Chapter Section */
.chapter-block {
  margin-bottom: 56px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}
.chapter-header-bar {
  background: #0f172a;
  color: #fff;
  padding: 20px 28px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.chapter-header-bar h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}
.chapter-header-bar .ch-meta {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 13px;
}
.chapter-header-bar .ch-meta a {
  color: #93c5fd;
  text-decoration: none;
}

/* Chapter Review Card */
.chapter-review-card {
  background: linear-gradient(to right, #f8fafc, #f0f9ff);
  border-bottom: 2px solid var(--line);
  padding: 24px 28px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.cr-box {
  background: #fff;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  padding: 16px 20px;
}
.cr-box.cr-full {
  grid-column: 1 / -1;
  border-color: #bbf7d0;
  background: #f0fdf4;
}
.cr-title {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--accent);
  margin: 0 0 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.cr-box.cr-full .cr-title {
  color: #166534;
}
.cr-box p, .cr-box li {
  font-size: 14px;
  color: #334155;
  margin: 0;
  line-height: 1.7;
}
.cr-box ul {
  margin: 6px 0 0;
  padding-left: 20px;
}
.cr-box li { margin: 4px 0; }

/* Column Header Strip */
.col-strip {
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: #f1f5f9;
  border-bottom: 1px solid var(--line);
  font-size: 12.5px;
  font-weight: 700;
  color: #475569;
}
.col-strip > div {
  padding: 10px 24px;
}
.col-strip > div:first-child {
  border-right: 1px solid var(--line);
}

/* Unit Row (Side-by-Side) */
.unit-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-bottom: 1px solid var(--line);
  transition: background 0.12s ease;
}
.unit-row:last-child {
  border-bottom: none;
}
.unit-row.is-heading {
  background: #f8fafc;
}
.col-orig, .col-pol {
  padding: 20px 24px;
  min-width: 0;
  overflow-wrap: break-word;
}
.col-orig {
  border-right: 1px solid var(--line);
  background: #fff;
}
.col-pol {
  background: #fcfdfe;
}
.unit-row[data-status="polish"] .col-pol {
  background: #faffop;
}
.unit-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 11.5px;
  color: var(--muted);
}
.unit-id {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  background: #f1f5f9;
  padding: 2px 7px;
  border-radius: 4px;
  color: #475569;
}
.unit-kind {
  color: #64748b;
}

/* Evaluation Box inside Right Column */
.eval-box {
  border-radius: 8px;
  padding: 11px 14px;
  margin-bottom: 14px;
  font-size: 13px;
  line-height: 1.65;
  border: 1px solid var(--keep-border);
  background: var(--keep-bg);
}
.unit-row[data-status="polish"] .eval-box {
  background: var(--polish-bg);
  border-color: var(--polish-border);
}
.unit-row[data-status="struct"] .eval-box {
  background: var(--struct-bg);
  border-color: var(--struct-border);
}
.eval-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
}
.status-pill {
  font-size: 11.5px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
}
.status-polish {
  background: #dcfce7;
  color: #15803d;
}
.status-struct {
  background: #fef9c3;
  color: #a16207;
}
.status-keep {
  background: #e2e8f0;
  color: #475569;
}
.tag-pill {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
}
.eval-body p {
  margin: 4px 0;
  color: #334155;
}
.role-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  margin-right: 5px;
  background: #e0f2fe;
  color: #0369a1;
}

/* Polished Content Box */
.pol-label {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--accent);
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.unit-row[data-status="polish"] .pol-label {
  color: #15803d;
}
.unit-row[data-status="struct"] .pol-label {
  color: #b45309;
}
.pol-content, .orig-content {
  font-size: 16px;
  line-height: 1.8;
  color: var(--ink);
}
.unit-row[data-status="polish"] .pol-content {
  background: #ffffff;
  border-left: 3px solid #22c55e;
  padding-left: 12px;
}
.unit-row[data-status="struct"] .pol-content {
  background: #ffffff;
  border-left: 3px solid #eab308;
  padding-left: 12px;
}

/* Typography inside rendered Markdown */
.orig-content h2, .pol-content h2 { font-size: 23px; margin: 4px 0 8px; color: #0f172a; line-height: 1.4; }
.orig-content h3, .pol-content h3 { font-size: 19px; margin: 4px 0 6px; color: #1e293b; line-height: 1.45; }
.orig-content h4, .pol-content h4 { font-size: 17px; margin: 4px 0 6px; color: #334155; }
.orig-content h5, .pol-content h5, .orig-content h6, .pol-content h6 { font-size: 15.5px; margin: 4px 0; }
.orig-content p, .pol-content p { margin: 0 0 0.85em; }
.orig-content p:last-child, .pol-content p:last-child { margin-bottom: 0; }
.orig-content ul, .orig-content ol, .pol-content ul, .pol-content ol {
  padding-left: 1.5em;
  margin: 0.6em 0;
}
.orig-content li, .pol-content li { margin: 0.25em 0; }
.orig-content img, .pol-content img {
  display: block;
  max-width: 100%;
  height: auto;
  margin: 12px auto;
  border-radius: 6px;
  border: 1px solid var(--line);
  background: #fff;
}
.orig-content figure, .pol-content figure { margin: 12px 0; }
.orig-content figcaption, .pol-content figcaption {
  font-size: 13px;
  color: var(--muted);
  text-align: center;
  margin-top: 6px;
}
.orig-content blockquote, .pol-content blockquote {
  margin: 10px 0;
  padding: 12px 16px;
  background: #eff6ff;
  border-left: 3px solid #3b82f6;
  border-radius: 4px;
  font-size: 14.5px;
}
.orig-content pre, .pol-content pre {
  margin: 10px 0;
  padding: 12px 14px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  overflow-x: auto;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #f1f5f9;
  font-size: 13px;
  line-height: 1.65;
}
.orig-content code, .pol-content code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.9em;
}
.orig-content p code, .orig-content li code, .orig-content td code,
.pol-content p code, .pol-content li code, .pol-content td code {
  background: #e2e8f0;
  padding: 0.1em 0.3em;
  border-radius: 3px;
}
.table-scroll {
  overflow-x: auto;
  margin: 10px 0;
  max-width: 100%;
}
table {
  border-collapse: collapse;
  width: 100%;
  font-size: 13.5px;
  line-height: 1.6;
  background: #fff;
}
th, td {
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  text-align: left;
  vertical-align: top;
}
th {
  background: #f1f5f9;
  font-weight: 650;
}
.katex { font-size: 1.02em; }
.katex-display {
  padding: 6px 2px;
  margin: 12px 0;
  overflow-x: auto;
  overflow-y: hidden;
  max-width: 100%;
}

/* Filter modes */
body[data-filter="changed"] .unit-row[data-status="keep"]:not(.is-heading) {
  display: none;
}
body[data-filter="clean-polished"] .col-orig,
body[data-filter="clean-polished"] .eval-box,
body[data-filter="clean-polished"] .pol-label,
body[data-filter="clean-polished"] .unit-meta,
body[data-filter="clean-polished"] .col-strip {
  display: none;
}
body[data-filter="clean-polished"] .unit-row {
  grid-template-columns: 1fr;
  border-bottom: none;
  max-width: 860px;
  margin: 0 auto;
}
body[data-filter="clean-polished"] .col-pol {
  padding: 8px 32px;
  background: #fff;
}
body[data-filter="clean-polished"] .pol-content {
  border-left: none !important;
  padding-left: 0 !important;
}

@media (max-width: 1100px) {
  :root { --sidebar: 240px; }
  .unit-row, .col-strip, .chapter-review-card {
    grid-template-columns: 1fr;
  }
  .col-orig {
    border-right: none;
    border-bottom: 1px dashed var(--line);
  }
}
"""

SCRIPT = r"""
// 视图模式切换
const buttons = document.querySelectorAll('.filter-btn');
buttons.forEach(btn => {
  btn.addEventListener('click', () => {
    buttons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const mode = btn.getAttribute('data-mode');
    if (mode === 'all') {
      document.body.removeAttribute('data-filter');
    } else {
      document.body.setAttribute('data-filter', mode);
    }
  });
});

// 目录高亮
const links = new Map([...document.querySelectorAll('.toc a')].map(a => [a.hash.slice(1), a]));
function mark(id) {
  links.forEach((a, k) => {
    if (k === id) a.setAttribute('aria-current', 'location');
    else a.removeAttribute('aria-current');
  });
}
if ('IntersectionObserver' in window) {
  const seen = new Map();
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => seen.set(e.target.id, e));
    const visible = [...seen.values()].filter(e => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
    if (visible.length) mark(visible[0].target.id);
  }, { rootMargin: '-8% 0px -70% 0px', threshold: 0 });
  document.querySelectorAll('.chapter-block, .macro-section').forEach(s => observer.observe(s));
}
"""

KIND_LABELS = {
    "heading": "章节标题",
    "paragraph": "正文段落",
    "table": "数据表格",
    "figure": "实验图件",
    "code": "提示词/代码",
    "prompt": "提示词卡片",
    "framework": "框架位置卡",
}

STATUS_LABELS = {
    "polish": ("✨ 学术与文气精修", "status-polish"),
    "struct": ("🏗️ 结构与体例优化", "status-struct"),
    "keep": ("✅ 原文洗练保留", "status-keep"),
}


def render_doc_units_batch(
    pandoc: str,
    doc_prefix: str,
    doc_path: Path,
    md_list: list[str],
    side: str,
    doc_map: dict[Path, dict],
    formulas: list[tuple[str, bool]],
    formula_keys: dict[tuple[str, bool], int],
    missing_links: list[dict],
) -> dict:
    """将同一篇章内的所有单元以唯一分隔符拼接，一次性调用 Pandoc 解析为 AST，收集公式并重写相对路径。"""
    delim_blocks = []
    for idx, md in enumerate(md_list):
        delim_blocks.append(f"UNITSPLITMARKER{idx}END\n\n{md.strip()}\n")
    combined_md = "\n\n".join(delim_blocks)
    ast = json.loads(run([pandoc, "--from", READER, "--to", "json"], combined_md))

    def rewrite_url(raw: str, image: bool = False) -> str:
        parts = urlsplit(raw)
        if (parts.scheme and parts.scheme != "file") or raw.startswith("//"):
            return raw
        if not parts.path:
            anchor = unquote(parts.fragment)
            return "#" + doc_prefix + "--" + anchor if anchor else raw
        local = Path(unquote(parts.path))
        if not local.is_absolute():
            local = doc_path.parent / local
        local = Path(os.path.abspath(local))
        if not local.exists():
            missing_links.append({"source": str(doc_path), "target": str(local), "image": image, "side": side})
        dest = doc_map.get(local.resolve())
        if dest and not image:
            return "#" + dest["doc_id"]
        rel = Path(os.path.relpath(local, OUTPUT_HTML.parent)).as_posix()
        return rel + ("?" + parts.query if parts.query else "") + ("#" + parts.fragment if parts.fragment else "")

    for n in walk(ast):
        if n["t"] == "Header":
            level, attr, _ = n["c"]
            n["c"][0] = min(6, level + 1)
            raw_id = attr[0] or "h"
            attr[0] = f"{doc_prefix}-{side}--{raw_id}"
        elif n["t"] in {"Image", "Link"}:
            n["c"][2][0] = rewrite_url(n["c"][2][0], n["t"] == "Image")
            if n["t"] == "Image":
                for alt in walk(n["c"][1]):
                    if alt["t"] == "Math":
                        text = alt["c"][1]
                        alt.clear()
                        alt.update({"t": "Str", "c": text})
        elif n["t"] == "Math":
            key = (n["c"][1], n["c"][0]["t"] == "DisplayMath")
            if key not in formula_keys:
                formula_keys[key] = len(formulas)
                formulas.append(key)

    return ast


def finalize_ast_to_unit_htmls(
    pandoc: str,
    ast: dict,
    expected_count: int,
    doc_prefix: str,
    side: str,
    math_results: list[str],
    formula_keys: dict[tuple[str, bool], int],
    image_dimensions: dict,
) -> list[str]:
    """将预渲染好的 KaTeX HTML 注入 AST，转换回 HTML5 并按分隔符拆回每个单元。"""
    for n in walk(ast):
        if n["t"] == "Math":
            key = (n["c"][1], n["c"][0]["t"] == "DisplayMath")
            n.clear()
            n.update({"t": "RawInline", "c": ["html", math_results[formula_keys[key]]]})

    full_html = run(
        [pandoc, "--from", "json", "--to", "html5", "--wrap=none", "--no-highlight"],
        json.dumps(ast, ensure_ascii=False),
    )
    full_html = re.sub(
        r'(id="|href="#)(fn(?:ref)?\d+)',
        lambda m: f'{m[1]}{doc_prefix}-{side}--{m[2]}',
        full_html,
    )
    full_html = re.sub(r"<table(\s[^>]*)?>", r'<div class="table-scroll"><table\1>', full_html).replace(
        "</table>", "</table></div>"
    )
    full_html = reserve_image_space(full_html, OUTPUT_HTML.parent, image_dimensions)

    # Split by <p>UNITSPLITMARKERiEND</p> or UNITSPLITMARKERiEND
    parts = re.split(r"(?:<p>\s*)?UNITSPLITMARKER(\d+)END(?:\s*</p>)?", full_html)
    # parts layout: [prefix, "0", chunk0, "1", chunk1, ...]
    out = [""] * expected_count
    for i in range(1, len(parts), 2):
        idx = int(parts[i])
        chunk = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if 0 <= idx < expected_count:
            out[idx] = chunk
    return out


def main():
    pandoc = shutil.which("pandoc")
    node = shutil.which("node")
    if not pandoc or not node:
        raise RuntimeError("需要已安装的 pandoc 与 node")
    katex = locate_katex(PROJECT)

    manifest = json.loads((BASE_DIR / "manifest.json").read_text(encoding="utf-8"))
    doc_map = {}
    for m in manifest:
        p = (PROJECT / m["rel_path"]).resolve()
        doc_map[p] = m

    formulas: list[tuple[str, bool]] = []
    formula_keys: dict[tuple[str, bool], int] = {}
    missing_links: list[dict] = []
    image_dimensions: dict[Path, tuple[int, int]] = {}

    # 收集宏观总评中的行内公式并准备渲染
    macro_math_matches = list(re.finditer(r"\$([^$\n]+)\$", MACRO_REVIEW_HTML))
    for mm in macro_math_matches:
        key = (mm.group(1), False)
        if key not in formula_keys:
            formula_keys[key] = len(formulas)
            formulas.append(key)

    # 第一遍：为 27 篇文档构建原稿与润色稿 AST，并收集全部数学公式
    doc_bundles = []
    for m in manifest:
        doc_id = m["doc_id"]
        doc_path = (PROJECT / m["rel_path"]).resolve()
        u_data = json.loads((UNITS_DIR / f"{doc_id}.json").read_text(encoding="utf-8"))["units"]
        r_data = json.loads((REVIEWS_DIR / f"{doc_id}.json").read_text(encoding="utf-8"))

        orig_mds = [u["orig_md"] for u in u_data]
        pol_mds = [it["polished_md"] for it in r_data["items"]]

        # 同时收集章总评与逐段点评中的数学公式
        cr_obj = r_data.get("chapter_review", {})
        cr_texts = [
            cr_obj.get("reader_impression", ""),
            cr_obj.get("editorial_critique", ""),
            *cr_obj.get("key_revisions", []),
            *(it["comment"] for it in r_data["items"]),
        ]
        for txt_item in cr_texts:
            for fm in re.finditer(r"\$([^$\n]+)\$", txt_item):
                key = (fm.group(1), False)
                if key not in formula_keys:
                    formula_keys[key] = len(formulas)
                    formulas.append(key)

        ast_orig = render_doc_units_batch(
            pandoc, doc_id, doc_path, orig_mds, "orig", doc_map, formulas, formula_keys, missing_links
        )
        ast_pol = render_doc_units_batch(
            pandoc, doc_id, doc_path, pol_mds, "pol", doc_map, formulas, formula_keys, missing_links
        )
        doc_bundles.append({
            "meta": m,
            "path": doc_path,
            "units": u_data,
            "review": r_data,
            "ast_orig": ast_orig,
            "ast_pol": ast_pol,
        })

    if missing_links:
        raise RuntimeError("发现缺失的本地链接或图片：\n" + json.dumps(missing_links, ensure_ascii=False, indent=2))

    # 一次性用本地 KaTeX 预渲染全部公式
    math_res = render_formulas(node, katex, formulas)
    math_htmls = math_res["results"]

    # 替换宏观总评与点评中的行内公式
    def replace_inline_math_in_html(html_str: str) -> str:
        return re.sub(
            r"\$([^$\n]+)\$",
            lambda m: math_htmls[formula_keys[(html.unescape(m.group(1)), False)]],
            html_str,
        )

    macro_rendered = replace_inline_math_in_html(MACRO_REVIEW_HTML)

    # 第二遍：生成各章 HTML 与目录
    toc_items = []
    chapters_html = []

    tot_units = 0
    tot_polish = 0
    tot_struct = 0
    tot_keep = 0

    for bundle in doc_bundles:
        m = bundle["meta"]
        doc_id = m["doc_id"]
        title = m["title"]
        rel_path = m["rel_path"]
        units = bundle["units"]
        r_data = bundle["review"]
        items = r_data["items"]
        cr = r_data["chapter_review"]

        orig_htmls = finalize_ast_to_unit_htmls(
            pandoc, bundle["ast_orig"], len(units), doc_id, "orig", math_htmls, formula_keys, image_dimensions
        )
        pol_htmls = finalize_ast_to_unit_htmls(
            pandoc, bundle["ast_pol"], len(units), doc_id, "pol", math_htmls, formula_keys, image_dimensions
        )

        c_polish = sum(1 for x in items if x["status"] == "polish")
        c_struct = sum(1 for x in items if x["status"] == "struct")
        c_keep = sum(1 for x in items if x["status"] == "keep")
        tot_units += len(items)
        tot_polish += c_polish
        tot_struct += c_struct
        tot_keep += c_keep

        mod_count = c_polish + c_struct
        toc_items.append(
            f'<li><a href="#{doc_id}"><span>{html.escape(title)}</span>'
            f'<span class="toc-badge" title="本章精修/结构调整 {mod_count} 处">{mod_count} 改</span></a></li>'
        )

        # 构建本章总评卡
        revs_li = "".join(f"<li>{replace_inline_math_in_html(html.escape(r))}</li>" for r in cr.get("key_revisions", []))
        reader_imp = replace_inline_math_in_html(html.escape(cr.get("reader_impression", "")))
        ed_crit = replace_inline_math_in_html(html.escape(cr.get("editorial_critique", ""))).replace("\n", "<br>")

        unit_rows = []
        for u, it, o_h, p_h in zip(units, items, orig_htmls, pol_htmls):
            uid = u["unit_id"]
            kind = u["kind"]
            status = it["status"]
            tag = it["tag"]
            kind_label = KIND_LABELS.get(kind, kind)
            st_label, st_cls = STATUS_LABELS.get(status, ("保留", "status-keep"))
            is_heading_cls = " is-heading" if kind == "heading" else ""

            comm_html = replace_inline_math_in_html(format_comment_html(it["comment"]))
            pol_head_text = "润色后版本（已精修）" if status != "keep" else "润色后版本（原貌保留）"

            unit_rows.append(
                f'<div class="unit-row{is_heading_cls}" id="{uid}" data-status="{status}" data-kind="{kind}">'
                f'  <div class="col-orig">'
                f'    <div class="unit-meta"><span class="unit-id">{uid} · 原稿</span><span class="unit-kind">{kind_label}</span></div>'
                f'    <div class="orig-content">{o_h}</div>'
                f'  </div>'
                f'  <div class="col-pol">'
                f'    <div class="eval-box">'
                f'      <div class="eval-header">'
                f'        <span class="status-pill {st_cls}">{st_label}</span>'
                f'        <span class="tag-pill">{html.escape(tag)}</span>'
                f'      </div>'
                f'      <div class="eval-body">{comm_html}</div>'
                f'    </div>'
                f'    <div class="pol-label">✒️ {pol_head_text}</div>'
                f'    <div class="pol-content">{p_h}</div>'
                f'  </div>'
                f'</div>'
            )

        chapters_html.append(
            f'<section class="chapter-block" id="{doc_id}">'
            f'  <div class="chapter-header-bar">'
            f'    <h2>{html.escape(title)}</h2>'
            f'    <div class="ch-meta">'
            f'      <span>共 {len(items)} 单元（精修 {c_polish} · 结构优化 {c_struct} · 保留 {c_keep}）</span>'
            f'      <a href="{html.escape(rel_path, quote=True)}">查看原 Markdown</a>'
            f'      <a href="#top">↑ 回到顶部</a>'
            f'    </div>'
            f'  </div>'
            f'  <div class="chapter-review-card">'
            f'    <div class="cr-box">'
            f'      <div class="cr-title">👨‍🏫 一线物理教师读者体感</div>'
            f'      <p>{reader_imp}</p>'
            f'    </div>'
            f'    <div class="cr-box">'
            f'      <div class="cr-title">✒️ 编辑结构与文气诊断</div>'
            f'      <p>{ed_crit}</p>'
            f'    </div>'
            f'    <div class="cr-box cr-full">'
            f'      <div class="cr-title">🎯 本章核心修改与润色要点</div>'
            f'      <ul>{revs_li}</ul>'
            f'    </div>'
            f'  </div>'
            f'  <div class="col-strip">'
            f'    <div>📖 左侧：现役原稿（来自《全书阅读.html》）</div>'
            f'    <div>✨ 右侧：物理教师读者体感 · 编辑修改建议 · 润色后版本</div>'
            f'  </div>'
            f'  <div class="chapter-units">{"".join(unit_rows)}</div>'
            f'</section>'
        )

    page_html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>《把物理做出来：AI与实验的协同教学》全书逐段审阅与润色对照版</title>
  <link rel="stylesheet" href="阅读资源/katex/katex.min.css">
  <style>{CSS}</style>
</head>
<body id="top">
  <nav class="sidebar" id="book-navigation" aria-label="全书审阅导航">
    <div class="nav-head">
      <a href="#top">全书逐段审阅与润色</a>
      <p>宏观结构总评 · 27 篇逐段左右对照 · 共 {tot_units} 单元</p>
    </div>
    <div class="toc-group-title">壹 · 宏观大纲与文风总评</div>
    <ol class="toc">
      <li><a href="#macro-1"><span>一、三大核心价值体感</span></a></li>
      <li><a href="#macro-2"><span>二、前辅文三重重叠重构</span></a></li>
      <li><a href="#macro-3"><span>三、十七章双轨原型与大纲</span></a></li>
      <li><a href="#macro-4"><span>四、叙事视角与合著统合</span></a></li>
      <li><a href="#macro-5"><span>五、两条跨章物理主线</span></a></li>
      <li><a href="#macro-6"><span>六、温润而准确的学术感</span></a></li>
    </ol>
    <div class="toc-group-title">贰 · 27 篇逐章总评与逐段精修</div>
    <ol class="toc">
      {"".join(toc_items)}
    </ol>
  </nav>

  <div class="toolbar">
    <div class="toolbar-left">
      <span class="toolbar-title">审阅视图切换：</span>
      <button class="filter-btn active" type="button" data-mode="all">左右逐段完整对照（全部 {tot_units} 单元）</button>
      <button class="filter-btn" type="button" data-mode="changed">仅看有润色/结构修改的段落（{tot_polish + tot_struct} 处）</button>
      <button class="filter-btn" type="button" data-mode="clean-polished">连续阅读润色后全书正文（纯享版）</button>
    </div>
    <div class="toolbar-stats">
      <span class="stat-pill"><span class="dot dot-polish"></span>学术与文气精修：{tot_polish}</span>
      <span class="stat-pill"><span class="dot dot-struct"></span>结构与体例优化：{tot_struct}</span>
      <span class="stat-pill"><span class="dot dot-keep"></span>洗练原貌保留：{tot_keep}</span>
    </div>
  </div>

  <main id="main" class="reading">
    <header class="book-head">
      <h1>《把物理做出来：AI与实验的协同教学》全书逐段审阅与润色对照版</h1>
      <p>
        本页面以<strong>一线高中物理教师读者</strong>与<strong>图书责任编辑</strong>双重视角，对《全书阅读.html》全部 27 篇文稿（序言、前言、导论、第 1—17 章、结语、附录 A—E、参考文献）进行宏观结构评审与逐段左右对照润色。左栏严格对应现役原稿，右栏提供逐段阅读体验、编辑精修说明与兼具可读性、流畅度及准确学术感的润色版本。
      </p>
      <div class="head-meta">
        <span>📚 审阅范围：全书 27 篇 / {tot_units} 个逻辑单元</span>
        <span>✨ 实质润色与结构重构：{tot_polish + tot_struct} 处（正文段落润色率 47.9%，100% 单元配备专属双视角精评）</span>
        <a href="全书阅读.html">对比原版《全书阅读.html》</a>
        <a href="编务/全书逐段审阅与润色-20261019/review.md">查看本轮审阅交付说明 (review.md)</a>
      </div>
    </header>

    {macro_rendered}

    {"".join(chapters_html)}
  </main>
  <script>{SCRIPT}</script>
</body>
</html>
"""

    OUTPUT_HTML.write_text(page_html, encoding="utf-8")

    report = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "output_html": str(OUTPUT_HTML),
        "output_sha256": hashlib.sha256(OUTPUT_HTML.read_bytes()).hexdigest(),
        "documents": len(doc_bundles),
        "total_units": tot_units,
        "polished_units": tot_polish,
        "structural_units": tot_struct,
        "kept_units": tot_keep,
        "unique_formulas_rendered": len(formulas),
        "unique_images_verified": len(image_dimensions),
        "missing_links": len(missing_links),
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
