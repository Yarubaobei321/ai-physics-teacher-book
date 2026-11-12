# 2026-11-08 新增第15章《自制光谱仪》，全书18章；由上一轮构建脚本复制，只改章数。
#!/usr/bin/env python3
"""把现役序言、前言、导论、十七章、结语与附录 A—E 合成连续阅读页；不改写 Markdown。

2026-10-18 新增两章：插入第5章《自制力传感器》、第13章《闭合电路的欧姆定律》，原第5—11章改为第6—12章，原第12—15章改为第14—17章，全书17章。

2026-10-18 电磁感应新章：插入第12章《法拉第电磁感应定律》，原第12—14章改为第13—15章，全书15章。

2026-10-15 结构压缩与序言：原第1、2章合为第1章，原第3章改为第2章，原第8、9章合为第7章，全书14章；新增序言，排在前言之前。

2026-10-15 静电课新章：插入第10章《静电的防止与利用》，原第10—15章改为第11—16章，第01—16章全部参与生成。

2026-10-14 静电两章与章号整理：原第10—13章合为第10、11章，后续各章依次改号；正文目录名与书中章号一致，第01—15章全部参与生成。

2026-10-12 全书审核修订：原第15章（源目录第17章）并入第16章（源目录第18章），源目录第17章不再参与生成；新增结语。

python3 构建阅读版.py --check  # 只在内存中转换并核对，不生成阅读页
python3 构建阅读版.py          # 现役合并后执行，输出根目录全书阅读.html

依赖已有 Pandoc、Node 和本地 KaTeX。公式在构建时预渲染，成品不依赖 CDN。
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

PROJECT = Path(__file__).resolve().parents[2]
RECORD = Path(__file__).resolve().parent / "阅读版构建核对.json"
READER = "markdown+tex_math_dollars+tex_math_single_backslash-raw_tex-smart-implicit_figures"

CSS = r"""
:root{--paper:#fff;--canvas:#f7f7f4;--ink:#252a2e;--muted:#67717a;--line:#dce2e4;--accent:#235e78;--soft:#eff5f7;--sidebar:276px}
*{box-sizing:border-box}html{scroll-behavior:auto;scroll-padding-top:28px}body{margin:0;background:var(--canvas);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration-thickness:1px;text-underline-offset:3px}a:hover{text-decoration-thickness:2px}a:focus-visible,summary:focus-visible,button:focus-visible{outline:3px solid #a1c3d3;outline-offset:4px}.skip{position:fixed;top:-70px;left:16px;z-index:10;background:#fff;padding:12px}.skip:focus{top:12px}
.sidebar{position:fixed;inset:0 auto 0 0;width:var(--sidebar);background:#fff;border-right:1px solid var(--line);overflow:auto;padding:28px 18px 32px;z-index:3}.nav-head{padding:0 10px 18px;border-bottom:1px solid var(--line);margin-bottom:14px}.nav-head a{font-size:18px;font-weight:650;text-decoration:none;color:var(--ink)}.nav-head p{margin:6px 0 0;color:var(--muted);font-size:12px}.toc{list-style:none;padding:0;margin:0}.toc>li{margin:3px 0}.toc a{display:block;padding:8px 10px;font-size:13px;line-height:1.6;text-decoration:none;border-radius:5px;overflow-wrap:anywhere}.toc a:hover,.toc a[aria-current="location"]{background:var(--soft);color:#164960}.toc .appendix-start{border-top:1px solid var(--line);padding-top:12px;margin-top:14px}
.mobile-bar{display:none}.reading{margin-left:var(--sidebar);padding:0 38px 90px}.book-head,.chapter{width:min(100%,840px);margin:0 auto}.book-head{padding:64px 0 44px;border-bottom:1px solid var(--line)}.book-head h1{font-size:36px;font-weight:650;line-height:1.4;margin:0 0 12px}.book-head p{color:var(--muted);font-size:15px;margin:0}.chapter{padding-top:66px;font-size:18px;line-height:1.85;overflow-wrap:break-word}.chapter+.chapter{margin-top:58px;border-top:1px solid var(--line)}.chapter>h2:first-child{font-size:31px;line-height:1.5;margin:0 0 34px;color:#203942}.chapter h3{font-size:25px;line-height:1.5;margin:42px 0 19px;color:#203942}.chapter h4{font-size:21px;line-height:1.55;margin:31px 0 15px}.chapter h5,.chapter h6{font-size:19px;line-height:1.55;margin:25px 0 13px}.chapter h2,.chapter h3,.chapter h4{scroll-margin-top:25px}.chapter p{margin:0 0 1.05em}.chapter strong{font-weight:650}.chapter ul,.chapter ol{padding-left:1.6em;margin:1em 0 1.25em}.chapter li{padding-left:.15em;margin:.32em 0}.chapter li p{margin-bottom:.55em}.chapter hr{border:0;border-top:1px solid var(--line);margin:34px 0}
.chapter img{display:block;max-width:100%;height:auto;margin:25px auto 16px;background:#fff}.chapter figure{margin:26px 0}.chapter figcaption{font-size:14px;color:var(--muted);line-height:1.7}.chapter blockquote{margin:25px 0;padding:17px 22px;background:var(--soft);border-left:3px solid #87a9b9}.chapter blockquote p:last-child{margin-bottom:0}.chapter pre{margin:24px 0;padding:20px 22px;white-space:pre-wrap;overflow-wrap:anywhere;overflow:auto;border:1px solid #e0e5e7;border-radius:6px;background:#f1f4f5;font-size:14px;line-height:1.8}.chapter code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"PingFang SC",monospace;font-size:.9em}.chapter p code,.chapter li code,.chapter td code{background:#edf1f2;padding:.1em .25em;border-radius:3px;overflow-wrap:anywhere}.chapter pre code{font-size:inherit}
.table-scroll{overflow-x:auto;margin:25px 0 29px;max-width:100%}.chapter table{border-collapse:collapse;width:100%;min-width:520px;font-size:15px;line-height:1.7;background:#fff}.chapter th,.chapter td{padding:10px 12px;border:1px solid var(--line);text-align:left;vertical-align:top}.chapter th{background:#edf3f5;font-weight:650}.chapter td p:last-child,.chapter th p:last-child{margin-bottom:0}.chapter col{width:auto!important}.chapter details{margin:24px 0;padding:15px 20px;border:1px solid var(--line);border-radius:6px;background:#fcfdfd}.chapter summary{cursor:pointer;color:var(--accent);font-weight:600;line-height:1.65}.chapter summary p{display:inline;margin:0}.chapter details[open]>summary{margin-bottom:18px}.chapter details>p:last-child{margin-bottom:0}.chapter .katex{font-size:1.05em}.chapter .katex-display{padding:9px 2px;margin:22px 0;overflow-x:auto;overflow-y:hidden;max-width:100%}.chapter .katex-display>.katex{white-space:nowrap}.chapter .footnotes{font-size:14px}.top-link{display:block;width:max-content;margin:28px 0 0 auto;font-size:13px;text-decoration:none;color:var(--muted)}
.book-head .reading-links{display:flex;flex-wrap:wrap;gap:10px 22px;margin-top:17px}.source-link{display:block;font-size:13px;line-height:1.6;margin:0 0 13px;color:var(--muted);text-decoration:none}.chapter>.source-link+h2{font-size:31px;line-height:1.5;margin:0 0 34px;color:#203942}
@media(max-width:1000px){:root{--sidebar:235px}.reading{padding-left:28px;padding-right:28px}.sidebar{padding-left:12px;padding-right:12px}.chapter{font-size:17px}.chapter>h2:first-child,.chapter>.source-link+h2{font-size:28px}}
@media(max-width:760px){html{scroll-padding-top:70px}.sidebar{width:285px;transform:translateX(-100%);transition:transform .18s ease}.sidebar.open{transform:translateX(0);box-shadow:12px 0 30px #0002}.mobile-bar{position:sticky;top:0;display:flex;align-items:center;gap:15px;padding:11px 18px;background:#fffffff5;border-bottom:1px solid var(--line);z-index:4}.mobile-bar button{background:#fff;border:1px solid #c4d0d5;padding:6px 11px;border-radius:5px;color:var(--accent);font:inherit}.mobile-bar span{font-size:14px}.reading{margin-left:0;padding:0 22px 65px}.book-head{padding:38px 0 30px}.book-head h1{font-size:29px}.chapter{padding-top:42px;font-size:17px;line-height:1.85}.chapter+.chapter{margin-top:38px}.chapter>h2:first-child,.chapter>.source-link+h2{font-size:26px}.chapter h3{font-size:22px}.chapter h4{font-size:19px}.chapter pre{padding:15px;font-size:13px}.chapter blockquote{padding:15px 17px}.chapter details{padding:13px 15px}.chapter table{font-size:14px}.chapter h2,.chapter h3,.chapter h4{scroll-margin-top:75px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.sidebar{transition:none}}
@media print{body{background:white}.sidebar,.mobile-bar,.skip,.top-link,.source-link{display:none}.reading{margin:0;padding:0}.book-head,.chapter{width:100%}.book-head{padding:0 0 15mm}.chapter{font-size:11pt;line-height:1.8;padding:0;break-before:page}.chapter+.chapter{margin:0;border:0}.chapter>h2:first-child,.chapter>.source-link+h2{font-size:21pt}.chapter h3{font-size:16pt}.chapter h4{font-size:13pt}.chapter h2,.chapter h3,.chapter h4{break-after:avoid}.chapter img{max-height:220mm;object-fit:contain}.chapter pre{font-size:9pt;white-space:pre-wrap}.chapter table{min-width:0;font-size:9pt}.chapter .table-scroll{overflow:visible}.chapter .katex-display{overflow:visible}.chapter details{border:0;padding:0}.chapter details::details-content{display:block}a{color:inherit}@page{size:A4;margin:20mm}}
"""

SCRIPT = r"""
const menu=document.querySelector('.sidebar');
const button=document.querySelector('#menu-button');
button.addEventListener('click',()=>{const open=menu.classList.toggle('open');button.setAttribute('aria-expanded',String(open));});
document.querySelectorAll('.toc a').forEach(a=>a.addEventListener('click',()=>{menu.classList.remove('open');button.setAttribute('aria-expanded','false');}));
document.addEventListener('keydown',e=>{if(e.key==='Escape'){menu.classList.remove('open');button.setAttribute('aria-expanded','false');}});
const links=new Map([...document.querySelectorAll('.toc a')].map(a=>[a.hash.slice(1),a]));
function mark(id){links.forEach((a,k)=>{if(k===id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');});}
if('IntersectionObserver' in window){const seen=new Map();const observer=new IntersectionObserver(entries=>{entries.forEach(e=>seen.set(e.target.id,e));const visible=[...seen.values()].filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top);if(visible.length)mark(visible[0].target.id);},{rootMargin:'-10% 0px -65% 0px',threshold:0});document.querySelectorAll('.chapter').forEach(s=>observer.observe(s));}
function reveal(){const id=decodeURIComponent(location.hash.slice(1));const target=document.getElementById(id);if(target){let node=target.parentElement;while(node){if(node.tagName==='DETAILS')node.open=true;node=node.parentElement;}}}
window.addEventListener('hashchange',reveal);reveal();
let closed=[];window.addEventListener('beforeprint',()=>{closed=[...document.querySelectorAll('details:not([open])')];closed.forEach(e=>e.open=true);});window.addEventListener('afterprint',()=>closed.forEach(e=>e.open=false));
"""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def inline_text(inlines) -> str:
    pieces = []
    for n in walk(inlines):
        if n["t"] == "Str":
            pieces.append(n["c"])
        elif n["t"] in {"Space", "SoftBreak", "LineBreak"}:
            pieces.append(" ")
        elif n["t"] in {"Code", "Math"}:
            pieces.append(n["c"][1])
    return "".join(pieces)


def get_files(project: Path, appendix_override: Path | None):
    files = []
    for prefix, folder in [("foreword", "序言-不会编程的物理老师能用AI做成什么"), ("preface", "前言-这本书怎么用"), ("introduction", "导论-让物理看得见")]:
        path = project / "正文" / folder / "正文.md"
        if not path.is_file():
            raise RuntimeError(f"现役序言/前言/导论缺失：{path}")
        files.append((prefix, path))
    for number in range(1, 19):
        matches = sorted((project / "正文").glob(f"第{number:02d}章-*/正文.md"))
        if len(matches) != 1:
            raise RuntimeError(f"第{number:02d}章现役正文应有且只有1份，实际{len(matches)}份。")
        files.append((f"ch{number:02d}", matches[0]))
    conclusion = sorted((project / "正文").glob("结语-*/正文.md"))
    if len(conclusion) > 1:
        raise RuntimeError(f"结语应至多1份，实际{len(conclusion)}份。")
    files.extend(("conclusion", c) for c in conclusion)
    appendix = appendix_override or project / "正文/附录"
    for letter in "ABCDE":
        matches = sorted(appendix.glob(f"附录{letter}-*.md"))
        if len(matches) != 1:
            raise RuntimeError(f"附录{letter}应有且只有1份，实际{len(matches)}份；目录：{appendix}")
        files.append((f"appendix-{letter.lower()}", matches[0]))
    files.append(("references", project / "正文/参考文献.md"))
    return files, appendix


def locate_katex(project: Path, override: Path | None) -> Path:
    candidates = [override] if override else []
    candidates += [project / "阅读资源/katex/katex.min.js", Path("/Users/yaril/个人文档/数智育才网站/node_modules/katex/dist/katex.min.js")]
    for p in candidates:
        if p and p.is_file() and (p.parent / "katex.min.css").is_file() and (p.parent / "fonts").is_dir():
            return p
    raise RuntimeError("未找到完整本地KaTeX资源，请通过 --katex-js 指定已有 dist/katex.min.js；不自动联网安装。")


def render_formulas(node: str, katex: Path, items: list[tuple[str, bool]]):
    js = r"""const fs=require('fs');const katex=require(process.argv[1]);
const items=JSON.parse(fs.readFileSync(0,'utf8'));const errors=[];
const results=items.map((x,i)=>{try{return katex.renderToString(x[0],{displayMode:x[1],throwOnError:true,strict:'ignore',trust:false,output:'htmlAndMathml'});}catch(e){errors.push({index:i,tex:x[0],error:e.message});return null;}});
process.stdout.write(JSON.stringify({version:katex.version,results,errors}));"""
    result = json.loads(run([node, "-e", js, str(katex)], json.dumps(items, ensure_ascii=False)))
    if result["errors"]:
        raise RuntimeError("公式无法排版（未生成阅读版）：\n" + json.dumps(result["errors"], ensure_ascii=False, indent=2))
    return result


def intrinsic_image_size(path: Path) -> tuple[int, int]:
    """只读图片元数据；SVG 使用 viewBox，JPEG 按 EXIF 显示方向处理。"""
    if path.suffix.lower() == ".svg":
        root = ET.parse(path).getroot()
        viewbox = root.get("viewBox", "").replace(",", " ").split()
        if len(viewbox) == 4:
            width, height = (float(x) for x in viewbox[2:])
        else:
            def numeric(value):
                match = re.fullmatch(r"([\d.]+)(?:px)?", value or "")
                if not match:
                    raise RuntimeError(f"SVG 缺少可确定比例的 viewBox/像素宽高：{path}")
                return float(match[1])
            width, height = numeric(root.get("width")), numeric(root.get("height"))
        if width <= 0 or height <= 0:
            raise RuntimeError(f"图片尺寸不是正数：{path}")
        # 当前书稿 viewBox 均为整数；通用小数 viewBox 保留其准确比例。
        from fractions import Fraction
        ratio = Fraction(str(width)) / Fraction(str(height))
        if width.is_integer() and height.is_integer():
            return int(width), int(height)
        return ratio.numerator, ratio.denominator
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("读取图片尺寸需要已有 Pillow；本脚本不自动安装。") from exc
    with Image.open(path) as image:
        width, height = image.size
        if image.getexif().get(274, 1) in {5, 6, 7, 8}:
            width, height = height, width
    if width <= 0 or height <= 0:
        raise RuntimeError(f"图片尺寸不是正数：{path}")
    return width, height


def reserve_image_space(fragment: str, base: Path, dimensions: dict) -> str:
    """先预留所有本地图的显示比例，防止懒加载后把目录目标推离屏幕。"""
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
            if path not in dimensions:
                dimensions[path] = intrinsic_image_size(path)
            width, height = dimensions[path]
            attrs.update({"width": str(width), "height": str(height)})
            style = re.sub(r"(?:^|;)\s*aspect-ratio\s*:[^;]*;?", ";", attrs.get("style", ""))
            attrs["style"] = style.rstrip("; ") + ("; " if style.strip("; ") else "") + f"aspect-ratio: {width} / {height};"
        return "<img " + " ".join(key if value is None else f'{key}="{html.escape(value, quote=True)}"' for key, value in attrs.items()) + ">"

    return re.sub(r"<img\b[^>]*>", replace, fragment)


class StructureCheck(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.anchors = []
        self.images = []
        self.image_attributes = []
        self.resources = []
        self.math = 0
        self.chapters = 0
        self.details = 0
        self.scripts = 0
        self.code_blocks = []
        self.in_pre = False
        self.pre_text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a" and a.get("href", "").startswith("#"):
            self.anchors.append(unquote(a["href"][1:]))
        if tag == "img":
            self.images.append(a.get("src", ""))
            self.image_attributes.append(a)
        attribute = {"a": "href", "img": "src", "link": "href", "script": "src", "source": "src", "video": "src", "audio": "src"}.get(tag)
        if attribute and a.get(attribute) and not a[attribute].startswith("#"):
            self.resources.append(a[attribute])
        if "katex" in a.get("class", "").split():
            self.math += 1
        if tag == "section" and "chapter" in a.get("class", "").split():
            self.chapters += 1
        if tag == "details":
            self.details += 1
        if tag == "script":
            self.scripts += 1
        if tag == "pre":
            self.in_pre = True
            self.pre_text = []

    def handle_data(self, data):
        if self.in_pre:
            self.pre_text.append(data)

    def handle_endtag(self, tag):
        if tag == "pre" and self.in_pre:
            self.code_blocks.append("".join(self.pre_text).rstrip("\n"))
            self.in_pre = False


def copy_katex(source: Path, project: Path):
    target = project / "阅读资源/katex"
    if source.parent.resolve() == target.resolve():
        return
    target.mkdir(parents=True, exist_ok=True)
    for name in ["katex.min.js", "katex.min.css"]:
        shutil.copy2(source.parent / name, target / name)
    shutil.copytree(source.parent / "fonts", target / "fonts", dirs_exist_ok=True)
    license_file = source.parent.parent / "LICENSE"
    if license_file.exists():
        shutil.copy2(license_file, target / "LICENSE")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="只在内存中预检，不写HTML、资源或核对报告")
    parser.add_argument("--project", type=Path, default=PROJECT)
    parser.add_argument("--appendix-dir", type=Path)
    parser.add_argument("--katex-js", type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    output = project / "全书阅读.html"
    pandoc, node = shutil.which("pandoc"), shutil.which("node")
    if not pandoc or not node:
        raise RuntimeError("需要已有的 Pandoc 与 Node；本脚本不自动安装依赖。")
    katex = locate_katex(project, args.katex_js)
    files, appendix = get_files(project, args.appendix_dir)
    fingerprints = {str(p): sha(p) for _, p in files}
    documents = []
    formulas = []
    formula_keys = {}
    formula_occurrences = 0
    alt_formula_occurrences = 0
    source_code_blocks = []
    for prefix, path in files:
        ast = json.loads(run([pandoc, "--from", READER, "--to", "json", str(path)]))
        headings = [n for n in walk(ast) if n["t"] == "Header"]
        if not headings or headings[0]["c"][0] != 1:
            raise RuntimeError(f"缺少章首一级标题：{path}")
        title = inline_text(headings[0]["c"][2])
        ids = {n["c"][1][0]: prefix + "--" + n["c"][1][0] for n in headings if n["c"][1][0]}
        documents.append({"prefix": prefix, "path": path, "ast": ast, "title": title, "ids": ids})
        for n in walk(ast):
            if n["t"] == "CodeBlock":
                source_code_blocks.append(n["c"][1].rstrip("\n"))
            if n["t"] == "Image":
                alt_formula_occurrences += sum(x["t"] == "Math" for x in walk(n["c"][1]))
            if n["t"] == "Math":
                formula_occurrences += 1
                key = (n["c"][1], n["c"][0]["t"] == "DisplayMath")
                if key not in formula_keys:
                    formula_keys[key] = len(formulas)
                    formulas.append(key)
    math_result = render_formulas(node, katex, formulas)
    doc_map = {d["path"].resolve(): d for d in documents}
    link_count = 0
    missing = []
    body = []
    toc = []
    image_dimensions = {}

    def rewrite_url(raw, source, image=False):
        nonlocal link_count
        parts = urlsplit(raw)
        if parts.scheme and parts.scheme != "file" or raw.startswith("//"):
            return raw
        if not parts.path:
            anchor = unquote(parts.fragment)
            return "#" + source["ids"].get(anchor, source["prefix"] + "--" + anchor) if anchor else raw
        local = Path(unquote(parts.path))
        if not local.is_absolute():
            local = source["path"].parent / local
        local = Path(os.path.abspath(local))
        link_count += 1
        if not local.exists():
            missing.append({"source": str(source["path"]), "target": str(local), "image": image})
        destination = doc_map.get(local.resolve())
        if destination and not image:
            anchor = unquote(parts.fragment)
            return "#" + (destination["ids"].get(anchor, destination["prefix"] + "--" + anchor) if anchor else destination["prefix"])
        relative = Path(os.path.relpath(local, output.parent)).as_posix()
        return relative + ("?" + parts.query if parts.query else "") + ("#" + parts.fragment if parts.fragment else "")

    for d in documents:
        for n in walk(d["ast"]):
            if n["t"] == "Header":
                level, attr, _ = n["c"]
                n["c"][0] = min(6, level + 1)
                attr[0] = d["ids"].get(attr[0], d["prefix"] + "--" + attr[0])
            elif n["t"] in {"Image", "Link"}:
                n["c"][2][0] = rewrite_url(n["c"][2][0], d, n["t"] == "Image")
                if n["t"] == "Image":
                    # HTML alt 属性不能容纳公式节点，保留原公式文字以便辅助阅读。
                    for alt in walk(n["c"][1]):
                        if alt["t"] == "Math":
                            text = alt["c"][1]
                            alt.clear()
                            alt.update({"t": "Str", "c": text})
            elif n["t"] == "Math":
                key = (n["c"][1], n["c"][0]["t"] == "DisplayMath")
                n.clear()
                n.update({"t": "RawInline", "c": ["html", math_result["results"][formula_keys[key]]]})
            elif n["t"] in {"RawBlock", "RawInline"} and n["c"][0] == "html":
                raw = n["c"][1]
                # 正文中的原生图片或链接同样按各章所在目录解析。
                raw = re.sub(r'\b(src|href)=("|\')(.*?)\2', lambda m: m[1] + '=' + m[2] + html.escape(rewrite_url(html.unescape(m[3]), d, m[1] == 'src'), quote=True) + m[2], raw)
                n["c"][1] = raw
        fragment = run([pandoc, "--from", "json", "--to", "html5", "--wrap=none", "--no-highlight"], json.dumps(d["ast"], ensure_ascii=False))
        # 每章脚注采用独立前缀，防止合并后 fn1/fnref1 重名。
        fragment = re.sub(r'(id="|href="#)(fn(?:ref)?\d+)', lambda m: m[1] + d["prefix"] + "--" + m[2], fragment)
        fragment = re.sub(r'<table(\s[^>]*)?>', r'<div class="table-scroll"><table\1>', fragment).replace('</table>', '</table></div>')
        fragment = reserve_image_space(fragment, output.parent, image_dimensions)
        source_link = html.escape(Path(os.path.relpath(d["path"], output.parent)).as_posix(), quote=True)
        body.append(f'<section class="chapter" id="{d["prefix"]}"><a class="source-link" href="{source_link}">本篇 Markdown 原稿</a>{fragment}<a class="top-link" href="#top">回到全书目录</a></section>')
        separator = ' class="appendix-start"' if d["prefix"] == "appendix-a" else ""
        toc.append(f'<li{separator}><a href="#{d["prefix"]}">{html.escape(d["title"])}</a></li>')
    if missing:
        raise RuntimeError("存在本地链接缺失（未生成阅读版）：\n" + json.dumps(missing, ensure_ascii=False, indent=2))
    page = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>全书阅读</title><link rel="stylesheet" href="阅读资源/katex/katex.min.css"><style>{CSS}</style></head>
<body id="top"><a class="skip" href="#main">跳到正文</a><nav class="sidebar" id="book-navigation" aria-label="全书目录"><div class="nav-head"><a href="#top">全书阅读</a><p>序言 · 前言 · 导论 · 十七章 · 结语 · 附录 A—E · 参考文献</p></div><ol class="toc">{''.join(toc)}</ol></nav><div class="mobile-bar"><button id="menu-button" type="button" aria-controls="book-navigation" aria-expanded="false">目录</button><span>全书阅读</span></div><main id="main" class="reading"><header class="book-head"><img src="封面/把物理做出来-封面.png" alt="把物理做出来：AI与实验的协同教学。深圳市育才一中。丁龙、黄灿斌、王硕、严力耕。AI生成封面插图。" style="display:block;width:min(100%,580px);height:auto;margin:0 auto 36px"><h1>把物理做出来：AI与实验的协同教学</h1><p>序言、前言、导论、十七章正文、结语、附录 A—E 与参考文献</p><p class="reading-links"><a href="05-全书目录.md">现役 Markdown 目录</a><a href="06-全书审核结论与修改意见.md">全书审核意见</a><a href="编务/GPT封面与配图-20261019/review.md">本轮修订说明</a></p></header>{''.join(body)}</main><script>{SCRIPT}</script></body></html>'''
    page = reserve_image_space(page, output.parent, image_dimensions)
    checked = StructureCheck()
    checked.feed(page)
    duplicates = sorted(x for x in set(checked.ids) if checked.ids.count(x) > 1)
    broken = sorted(set(checked.anchors) - set(checked.ids))
    visible_formula_occurrences = formula_occurrences - alt_formula_occurrences
    if duplicates or broken or checked.chapters != len(files) or checked.math != visible_formula_occurrences:
        raise RuntimeError(f"HTML结构核对失败：重复ID={duplicates}；失效锚点={broken}；篇目={checked.chapters}；公式={checked.math}/{visible_formula_occurrences}")
    if checked.code_blocks != source_code_blocks:
        raise RuntimeError("围栏提示词/代码块与源文不一致，未生成阅读版。")
    for attrs in checked.image_attributes:
        parts = urlsplit(attrs.get("src", ""))
        if parts.scheme or attrs.get("src", "").startswith("//"):
            continue
        path = (output.parent / unquote(parts.path)).resolve()
        expected = image_dimensions[path]
        if (attrs.get("width"), attrs.get("height")) != tuple(str(v) for v in expected):
            raise RuntimeError(f"图片预留宽高与实际尺寸不一致：{path}")
    run([node, "--check"], SCRIPT)
    local_resource_paths = set()
    for raw in checked.resources:
        parts = urlsplit(raw)
        if parts.scheme or raw.startswith("//"):
            continue
        target = (output.parent / unquote(parts.path)).resolve()
        local_resource_paths.add(str(target))
        if target == (project / "阅读资源/katex/katex.min.css").resolve() and args.check:
            continue  # 已核对源资源，正式构建时复制到此位置。
        if target == (project / "阅读资源/katex/katex.min.css").resolve() and not target.exists():
            continue
        if not target.exists():
            raise RuntimeError(f"HTML本地资源缺失：{raw}")
    css_source = katex.parent / "katex.min.css"
    css_font_paths = set()
    for raw in re.findall(r'url\(([^)]+)\)', css_source.read_text(encoding="utf-8")):
        raw = raw.strip('"\' ')
        if urlsplit(raw).scheme or raw.startswith("//"):
            continue
        font = css_source.parent / unquote(urlsplit(raw).path)
        if not font.is_file():
            raise RuntimeError(f"KaTeX字体资源缺失：{font}")
        css_font_paths.add(raw)
    unique_images = set()
    unique_image_contents = set()
    for raw in checked.images:
        parts = urlsplit(raw)
        if parts.scheme or raw.startswith("//"):
            unique_images.add(raw)
            continue
        image = (output.parent / unquote(parts.path)).resolve()
        if not image.exists():
            raise RuntimeError(f"HTML图片路径缺失：{raw}")
        unique_images.add(str(image))
        unique_image_contents.add(sha(image))
    changed = [p for p, digest in fingerprints.items() if sha(Path(p)) != digest]
    if changed:
        raise RuntimeError("构建期间源稿发生变化，重新读取后再运行：" + ", ".join(changed))
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "check_only" if args.check else "built",
        "output": str(output), "appendix_directory": str(appendix),
        "foreword_preface_and_introduction": 3, "chapters": 18, "conclusion": sum(1 for prefix, _ in files if prefix == "conclusion"), "appendices": sum(1 for prefix, _ in files if prefix.startswith("appendix-")), "references": 1,
        "images": len(checked.images), "unique_image_files": len(unique_images),
        "unique_local_image_contents": len(unique_image_contents), "local_links": link_count,
        "local_images_with_intrinsic_dimensions": len(image_dimensions), "local_images_missing_dimensions": 0,
        "chapter_navigation_scroll": "instant",
        "unique_html_local_resources": len(local_resource_paths), "katex_font_resources": len(css_font_paths),
        "formulas": visible_formula_occurrences, "unique_formulas": len(formulas),
        "recognized_math_total": formula_occurrences, "formulas_in_image_alt_text": alt_formula_occurrences,
        "formula_render_errors": 0, "missing_local_links": 0,
        "missing_local_resources": 0,
        "broken_anchors": 0, "duplicate_ids": 0,
        "verbatim_code_blocks": len(source_code_blocks), "verbatim_code_block_mismatches": 0,
        "katex_version": math_result["version"],
        "katex_source": str(katex),
        "source_files": [{"path": p, "sha256": digest} for p, digest in fingerprints.items()],
        "scope": "全文合并、图片和配套路径、锚点、KaTeX公式静态渲染；未做浏览器截图、视觉或实体打印验收。",
    }
    if not args.check:
        copy_katex(katex, project)
        temp = output.with_suffix(".html.tmp")
        temp.write_text(page, encoding="utf-8")
        temp.replace(output)
        result["output_sha256"] = sha(output)
        RECORD.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {k: v for k, v in result.items() if k != "source_files"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
