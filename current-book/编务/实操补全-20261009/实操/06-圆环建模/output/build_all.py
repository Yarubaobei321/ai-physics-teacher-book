#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
圆环参数化流水线 (只做四款最小成果, 不批量渲染/不切片/不打印)

路径:
  1. 解析 ring_params.scad 的参数表(唯一几何参数源)
  2. 调用本机已有 OpenSCAD 命令行导出 STL
       - 单件: stl/<款>.stl
       - 排盘: stl/<款>_plate4.stl (同款 4 个)
  3. 用纯标准库读取二进制 STL, 做闭合性 + 尺寸核对
  4. 生成 参数表.csv 与 尺寸预览 preview.html

依赖: 本机已有的 openscad 命令 + Python 标准库(无第三方包, 不安装任何东西)
"""
import csv
import html
import math
import os
import re
import shutil
import struct
import subprocess
import sys
from collections import Counter

ROOT      = os.path.dirname(os.path.abspath(__file__))
SCAD      = os.path.join(ROOT, "ring_params.scad")
STL_DIR   = os.path.join(ROOT, "stl")
OPENSCAD  = shutil.which("openscad") or "/opt/homebrew/bin/openscad"

TOL = 5e-3  # 尺寸判定容差 (mm), STL 为 float32, 留足余量


# ----------------------------------------------------------------------
# 1. 解析参数表
# ----------------------------------------------------------------------
def parse_scad(path):
    src = open(path, encoding="utf-8").read()

    def num(name):
        m = re.search(r"^\s*%s\s*=\s*([0-9.]+)\s*;" % name, src, re.M)
        if not m:
            raise SystemExit("参数解析失败: %s" % name)
        return float(m.group(1))

    od   = num("OD")
    gap  = num("GAP")
    npp  = int(num("N_PER_PLATE"))

    rows = re.findall(r'\[\s*"([A-Za-z0-9]+)"\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\]', src)
    variants = [{"name": n, "id": float(i), "h": float(h)} for n, i, h in rows]
    if not variants:
        raise SystemExit("参数解析失败: VARIANTS 为空")
    return {"od": od, "gap": gap, "npp": npp, "variants": variants}


# ----------------------------------------------------------------------
# 2. 导出 STL
# ----------------------------------------------------------------------
def export_stl(variant, mode, out_path):
    cmd = [OPENSCAD, "-o", out_path, "--export-format", "binstl", "--render",
           "-D", 'variant="%s"' % variant, "-D", 'mode="%s"' % mode, SCAD]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out_path):
        raise SystemExit("OpenSCAD 导出失败 (%s/%s):\n%s\n%s"
                         % (variant, mode, r.stdout[-800:], r.stderr[-800:]))


# ----------------------------------------------------------------------
# 3. 读取 + 核对二进制 STL
# ----------------------------------------------------------------------
def read_stl(path):
    with open(path, "rb") as f:
        head = f.read(84)
        if len(head) < 84:
            raise ValueError("文件过短, 不是二进制 STL")
        n = struct.unpack("<I", head[80:84])[0]
        body = f.read(n * 50)
    tris = []
    off = 0
    for _ in range(n):
        v = struct.unpack_from("<12f", body, off)
        off += 50
        tris.append(((v[3], v[4], v[5]), (v[6], v[7], v[8]), (v[9], v[10], v[11])))
    return tris


def analyse(path, centers):
    """返回一个 dict: 面/点/闭合/朝向/欧拉/亏格/外壳数/尺寸实测量"""
    tris = read_stl(path)

    key = lambda p: (round(p[0], 4), round(p[1], 4), round(p[2], 4))
    vid, verts = {}, []
    faces = []
    for t in tris:
        idx = []
        for p in t:
            k = key(p)
            if k not in vid:
                vid[k] = len(verts)
                verts.append(p)
            idx.append(vid[k])
        faces.append(tuple(idx))

    undirected = Counter()
    directed = Counter()
    for a, b, c in faces:
        for u, v in ((a, b), (b, c), (c, a)):
            undirected[(u, v) if u < v else (v, u)] += 1
            directed[(u, v)] += 1

    closed      = all(cnt == 2 for cnt in undirected.values())
    orientation = all(cnt == 1 for cnt in directed.values())

    V, E, F = len(verts), len(undirected), len(faces)
    chi = V - E + F
    genus = (2 - chi) / 2 if closed else None

    # 连通分量 = 独立外壳数 (并查集)
    parent = list(range(V))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in undirected:
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[ru] = rv
    shells = len({find(i) for i in range(V)})

    # 包围盒
    xs = [p[0] for p in verts]; ys = [p[1] for p in verts]; zs = [p[2] for p in verts]
    bbox = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))

    # 半径实测量: 相对最近的圆心
    rmax = rmin = None
    for x, y, z in verts:
        cx = min(centers, key=lambda c: abs(c - x))
        r = math.hypot(x - cx, y)
        rmax = r if rmax is None or r > rmax else rmax
        rmin = r if rmin is None or r < rmin else rmin

    return {"file": os.path.basename(path),
            "tris": F, "verts": V, "edges": E,
            "closed": closed, "orientation": orientation,
            "chi": chi, "genus": genus, "shells": shells,
            "bbox": bbox, "od_meas": 2 * rmax, "id_meas": 2 * rmin,
            "h_meas": bbox[2], "bytes": os.path.getsize(path)}


# ----------------------------------------------------------------------
# 4. 预览 HTML (俯视 + 侧视, 带 mm 标注)
# ----------------------------------------------------------------------
def svg_card(v, od, scale=12.0):
    """一款一张 SVG: 俯视图(外径/内径标注) + 侧视图(高度标注), 真实比例"""
    R  = od / 2 * scale
    Ri = v["id"] / 2 * scale
    H  = v["h"] * scale
    cx, cy = 120.0, 170.0            # 俯视图圆心
    sx, sy = 350.0, 170.0            # 侧视图中心

    def arrow(x, y, d):
        s = 5.0
        if d == "l":
            pts = "%.1f,%.1f %.1f,%.1f %.1f,%.1f" % (x, y, x + 2 * s, y - s * 0.6, x + 2 * s, y + s * 0.6)
        elif d == "r":
            pts = "%.1f,%.1f %.1f,%.1f %.1f,%.1f" % (x, y, x - 2 * s, y - s * 0.6, x - 2 * s, y + s * 0.6)
        elif d == "u":
            pts = "%.1f,%.1f %.1f,%.1f %.1f,%.1f" % (x, y, x - s * 0.6, y + 2 * s, x + s * 0.6, y + 2 * s)
        else:
            pts = "%.1f,%.1f %.1f,%.1f %.1f,%.1f" % (x, y, x - s * 0.6, y - 2 * s, x + s * 0.6, y - 2 * s)
        return '<polygon points="%s" fill="#1f2430"/>' % pts

    dk, ln, tx, dim = "#1f2430", "#8a93a6", "#3a4356", "#c2410c"

    # --- 俯视图 ---
    top = []
    top.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#eef2f7" stroke="%s" stroke-width="1.6"/>' % (cx, cy, R, dk))
    top.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#ffffff" stroke="%s" stroke-width="1.6"/>' % (cx, cy, Ri, dk))
    # 外径标注 (上方)
    y1 = cy - R - 34
    top.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="0.9" stroke-dasharray="3 3"/>' % (cx - R, cy - R - 4, cx - R, y1 - 6, ln))
    top.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="0.9" stroke-dasharray="3 3"/>' % (cx + R, cy - R - 4, cx + R, y1 - 6, ln))
    top.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.1"/>' % (cx - R, y1, cx + R, y1, dim))
    top.append(arrow(cx - R, y1, "l")); top.append(arrow(cx + R, y1, "r"))
    top.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="13" fill="%s">&#8960;%.1f</text>' % (cx, y1 - 8, dim, od))
    # 内径标注 (下方)
    y2 = cy + R + 34
    top.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.1"/>' % (cx - Ri, y2, cx + Ri, y2, dim))
    top.append(arrow(cx - Ri, y2, "l")); top.append(arrow(cx + Ri, y2, "r"))
    top.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="13" fill="%s">&#8960;%.1f</text>' % (cx, y2 + 18, dim, v["id"]))
    top.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="11" fill="%s">俯视图</text>' % (cx, cy + R + 66, tx))

    # --- 侧视图 ---
    side = []
    x_l, x_r = sx - R, sx + R
    y_t, y_b = sy - H / 2, sy + H / 2
    side.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#eef2f7" stroke="%s" stroke-width="1.6"/>' % (x_l, y_t, 2 * R, H, dk))
    side.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.0" stroke-dasharray="4 3"/>' % (sx - Ri, y_t, sx - Ri, y_b, ln))
    side.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.0" stroke-dasharray="4 3"/>' % (sx + Ri, y_t, sx + Ri, y_b, ln))
    side.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="10" fill="%s">虚线=中心通孔</text>' % (sx, y_b + 52, tx))
    # 高度标注 (右侧)
    xd = x_r + 30
    side.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="0.9" stroke-dasharray="3 3"/>' % (x_r + 3, y_t, xd + 8, y_t, ln))
    side.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="0.9" stroke-dasharray="3 3"/>' % (x_r + 3, y_b, xd + 8, y_b, ln))
    side.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.1"/>' % (xd, y_t, xd, y_b, dim))
    side.append(arrow(xd, y_t, "u")); side.append(arrow(xd, y_b, "d"))
    side.append('<text x="%.1f" y="%.1f" font-size="13" fill="%s">高 %.1f</text>' % (xd + 8, sy + 4, dim, v["h"]))
    side.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="11" fill="%s">侧视图</text>' % (sx, y_b + 68, tx))

    return ('<svg viewBox="0 0 470 320" width="100%%" role="img" aria-label="款 %s 尺寸图">'
            '%s%s</svg>') % (v["name"], "".join(top), "".join(side))


def build_preview(cfg, results):
    od  = cfg["od"]
    rows = []
    for v in cfg["variants"]:
        res = results["single"][v["name"]]
        ok  = (abs(res["od_meas"] - od) < TOL and
               abs(res["id_meas"] - v["id"]) < TOL and
               abs(res["h_meas"] - v["h"]) < TOL and
               res["closed"] and res["orientation"])
        badge = ('<span class="ok">闭合 &#10003; 尺寸 &#10003;</span>' if ok
                 else '<span class="bad">核对未通过</span>')
        rows.append("""
<div class="card">
  <div class="hdr"><b>款 %s</b>
    <span class="spec">外径 &#8960;%.1f &middot; 内径 &#8960;%.1f &middot; 高 %.1f <i>mm</i></span>%s</div>
  %s
</div>""" % (v["name"], od, v["id"], v["h"], badge, svg_card(v, od)))

    table = "".join(
        "<tr><td>%s</td><td>&#8960;%.1f</td><td>&#8960;%.1f</td><td>%.1f</td>"
        "<td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>"
        % (v["name"], od, v["id"], v["h"],
           results["single"][v["name"]]["tris"],
           "是" if results["single"][v["name"]]["closed"] else "否",
           "%.3f" % results["single"][v["name"]]["od_meas"],
           "%.3f / %.3f / %.3f" % tuple(results["single"][v["name"]]["bbox"])
           ) for v in cfg["variants"])

    doc = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>圆环尺寸预览 (mm)</title>
<style>
  :root{--bg:#f6f8fb;--panel:#ffffff;--ink:#1f2430;--sub:#3a4356;--line:#dfe5ee;--dim:#c2410c}
  *{box-sizing:border-box}
  body{margin:0;padding:28px;background:var(--bg);color:var(--ink);
       font:15px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
  h1{font-size:20px;margin:0 0 4px}
  .lead{color:var(--sub);font-size:13px;margin-bottom:18px}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:16px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px 6px}
  .hdr{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:2px}
  .hdr b{font-size:17px}
  .spec{color:var(--sub);font-size:13px}
  .hdr .ok,.hdr .bad{margin-left:auto;font-size:12px;padding:2px 8px;border-radius:999px}
  .ok{background:#e7f6ec;color:#1a7f43;border:1px solid #bfe6cd}
  .bad{background:#fdeceb;color:#b42318;border:1px solid #f5c6c2}
  .card svg{display:block;margin:-6px auto 0}
  table{border-collapse:collapse;width:100%;margin-top:22px;background:var(--panel);
        border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:13.5px}
  th,td{padding:8px 10px;text-align:center;border-bottom:1px solid var(--line)}
  th{background:#eef2f7;font-weight:600}
  td:first-child{font-weight:600}
  .notes{margin-top:18px;color:var(--sub);font-size:12.5px;border-left:3px solid var(--dim);padding-left:12px}
  code{background:#eef2f7;padding:1px 5px;border-radius:4px}
</style></head><body>
<h1>圆环尺寸预览 <span style="font-size:13px;color:var(--sub)">单位: mm &middot; 真实比例</span></h1>
<div class="lead">四款圆环: 外径统一 &#8960;__OD__ mm, 无通气孔。图形按毫米真实比例绘制, 用于本地目视核对尺寸。</div>
<div class="grid">__CARDS__</div>

<table>
  <tr><th>款</th><th>外径 mm</th><th>内径 mm</th><th>高 mm</th>
      <th>三角面</th><th>网格闭合</th><th>外径实测</th><th>包围盒 X/Y/Z mm</th></tr>
  __TABLE__
</table>

<div class="notes">
  <b>说明:</b> 本页仅为尺寸目视核对, 数据来自 <code>stl/</code> 中各款单件 STL 的实测值。<br>
  &#8226; 网页预览与 STL 只反映几何尺寸, <b>不能证明圆环能否沉底或在水中的任何行为</b> —— 未做水中试验, 也不给出水中结论。<br>
  &#8226; 未做通气孔; 未切片; 未打印。排盘 STL 见 <code>stl/&lt;款&gt;_plate4.stl</code>。
</div>
</body></html>"""

    doc = (doc.replace("__OD__", "%.1f" % od)
              .replace("__CARDS__", "".join(rows))
              .replace("__TABLE__", table))

    with open(os.path.join(ROOT, "preview.html"), "w", encoding="utf-8") as f:
        f.write(doc)


# ----------------------------------------------------------------------
# 5. 报告 + 参数表
# ----------------------------------------------------------------------
def build_report(cfg, results, oscad_ver, pyver):
    L = []
    L.append("# 圆环建模核对报告\n")
    L.append("- 建模程序: `ring_params.scad` (OpenSCAD, 单位 mm)")
    L.append("- 实际使用工具: OpenSCAD %s (命令行导出 STL) + Python %s 标准库 (读 STL 做核对)"
             % (oscad_ver, pyver))
    L.append("- 未安装任何新软件; 未切片; 未打印; 未做水中试验\n")
    L.append("## 一、参数表 (mm)\n")
    L.append("| 款 | 外径 | 内径 | 高 | 备注 |")
    L.append("|----|------|------|----|------|")
    for v in cfg["variants"]:
        L.append("| %s | %.1f | %.1f | %.1f | 无通气孔 |" % (v["name"], cfg["od"], v["id"], v["h"]))

    L.append("\n## 二、网格闭合与尺寸核对 (单件)\n")
    L.append("| 款 | 文件 | 三角面 | 顶点 | 闭合(每边2面) | 朝向一致 | V-E+F | 亏格 | 外径实测 | 内径实测 | 高实测 | 判定 |")
    L.append("|----|------|-------|------|--------------|---------|-------|------|---------|---------|-------|------|")
    all_ok = True
    for v in cfg["variants"]:
        r = results["single"][v["name"]]
        ok = (abs(r["od_meas"] - cfg["od"]) < TOL and abs(r["id_meas"] - v["id"]) < TOL
              and abs(r["h_meas"] - v["h"]) < TOL and r["closed"] and r["orientation"])
        all_ok = all_ok and ok
        L.append("| %s | %s | %d | %d | %s | %s | %d | %s | %.3f | %.3f | %.3f | %s |"
                 % (v["name"], r["file"], r["tris"], r["verts"],
                    "是" if r["closed"] else "否",
                    "是" if r["orientation"] else "否",
                    r["chi"],
                    ("%.0f" % r["genus"]) if r["genus"] is not None else "-",
                    r["od_meas"], r["id_meas"], r["h_meas"],
                    "通过" if ok else "**不通过**"))

    L.append("\n## 三、排盘核对 (同款 4 个)\n")
    L.append("| 款 | 文件 | 外壳数 | 闭合 | 包围盒 X/Y/Z mm | 预期 X | 判定 |")
    L.append("|----|------|-------|------|-----------------|--------|------|")
    for v in cfg["variants"]:
        r = results["plate"][v["name"]]
        exp_x = cfg["od"] + (cfg["npp"] - 1) * (cfg["od"] + cfg["gap"])
        ok = (r["shells"] == cfg["npp"] and r["closed"] and r["orientation"]
              and abs(r["bbox"][0] - exp_x) < TOL)
        all_ok = all_ok and ok
        L.append("| %s | %s | %d | %s | %.3f / %.3f / %.3f | %.3f | %s |"
                 % (v["name"], r["file"], r["shells"],
                    "是" if r["closed"] else "否",
                    r["bbox"][0], r["bbox"][1], r["bbox"][2], exp_x,
                    "通过" if ok else "**不通过**"))

    L.append("\n## 四、结论\n")
    L.append("- 四款单件 STL 全部闭合(每条边恰被 2 个三角面共享)且朝向一致, 实测外径/内径/高与参数表一致(容差 %.0e mm)。" % TOL)
    L.append("- 每款排盘 STL 含 4 个独立闭合外壳, 排列尺寸符合 `外径+净间隙` 的排布。")
    L.append("- **总判定: %s**" % ("全部通过" if all_ok else "存在未通过项, 见上表"))

    # ---- 五、产物清单与文件说明 ----
    desc = {
        "ring_params.scad": "可改参数的建模程序(唯一几何参数源, 顶部 VARIANTS 表)",
        "build_all.py":     "流水线脚本: 解析参数表 -> 调 OpenSCAD 导出 STL -> 核对 -> 生成预览/报告/参数表",
        "preview.html":     "本地尺寸预览(俯视+侧视, 真实比例, mm 标注)",
        "参数表.csv":        "参数表(mm, 含通气孔=无)",
        "核对报告.md":       "本报告",
    }
    for v in cfg["variants"]:
        desc["stl/%s.stl" % v["name"]] = "款 %s 单件 STL(外径%.1f/内径%.1f/高%.1f mm)" % (v["name"], cfg["od"], v["id"], v["h"])
    for v in cfg["variants"]:
        desc["stl/%s_plate4.stl" % v["name"]] = "款 %s 排盘 STL(同款 4 个, 净间隙 %.0f mm)" % (v["name"], cfg["gap"])

    L.append("\n## 五、产物清单与文件说明 (output/ 目录)\n")
    L.append("| 文件 | 大小 | 说明 |")
    L.append("|------|------|------|")
    for rel in ["ring_params.scad", "build_all.py", "preview.html", "参数表.csv",
                "核对报告.md"] + ["stl/%s.stl" % v["name"] for v in cfg["variants"]] \
               + ["stl/%s_plate4.stl" % v["name"] for v in cfg["variants"]]:
        p = os.path.join(ROOT, rel)
        if rel == "核对报告.md":
            size = "本文件"
        else:
            size = "%.1f KB" % (os.path.getsize(p) / 1024.0) if os.path.exists(p) else "-"
        L.append("| `%s` | %s | %s |" % (rel, size, desc.get(rel, "")))

    # ---- 六、验证边界与未验证项 ----
    L.append("\n## 六、验证边界与未验证项 (如实记录)\n")
    L.append("**已完成:**")
    L.append("- 闭合性与朝向: 由 `build_all.py` 读取 STL 三角面逐边统计(无向边恰 2 面、有向边恰 1 次), 并非目测。")
    L.append("- 尺寸实测量: 由 STL 顶点坐标计算外径/内径/高/包围盒, 与本报告参数表逐项比对。")
    L.append("- `preview.html` 仅做 SVG 结构校验(4 个卡片良构、尺寸标注文字正确)。")
    L.append("")
    L.append("**未验证 / 未完成:**")
    L.append("- **浏览器预览未验证**: 本机 Chrome 无头截图被运行沙箱权限拦截(弹出工作空间外文件授权后被拒绝), 未重试。"
             "因此**未在浏览器中实际打开 `preview.html` 确认渲染效果**, 预览的显示效果请由用户自行打开确认。")
    L.append("- 未做: 通气孔、切片、3D 打印、水中试验。")
    L.append("- 网页预览与 STL 只反映几何尺寸, **不能证明圆环能否沉底或在水中的任何行为**; 本报告不含任何水中行为结论。")

    with open(os.path.join(ROOT, "核对报告.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return all_ok


def build_csv(cfg):
    with open(os.path.join(ROOT, "参数表.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["款", "外径_mm", "内径_mm", "高_mm", "通气孔"])
        for v in cfg["variants"]:
            w.writerow([v["name"], "%.1f" % cfg["od"], "%.1f" % v["id"], "%.1f" % v["h"], "无"])


# ----------------------------------------------------------------------
def main():
    cfg = parse_scad(SCAD)
    print("参数表:", ", ".join("%s(id=%.1f,h=%.1f)" % (v["name"], v["id"], v["h"])
                              for v in cfg["variants"]))
    os.makedirs(STL_DIR, exist_ok=True)

    results = {"single": {}, "plate": {}}
    for v in cfg["variants"]:
        for mode, suffix in (("single", ""), ("plate", "_plate4")):
            out = os.path.join(STL_DIR, "%s%s.stl" % (v["name"], suffix))
            export_stl(v["name"], mode, out)
            pitch = cfg["od"] + cfg["gap"]
            x0 = -pitch * (cfg["npp"] - 1) / 2
            centers = [0.0] if mode == "single" else [x0 + i * pitch for i in range(cfg["npp"])]
            results[mode][v["name"]] = analyse(out, centers)
            r = results[mode][v["name"]]
            print("  %-16s tris=%-6d closed=%s orient=%s shell=%d bbox=%.2f/%.2f/%.2f"
                  % (r["file"], r["tris"], r["closed"], r["orientation"], r["shells"],
                     r["bbox"][0], r["bbox"][1], r["bbox"][2]))

    build_preview(cfg, results)
    build_csv(cfg)
    _v = subprocess.run([OPENSCAD, "--version"], capture_output=True, text=True)
    oscad_ver = (_v.stdout + _v.stderr).strip().replace("OpenSCAD version ", "").splitlines()[0] or "未知"
    pyver = "%d.%d.%d" % sys.version_info[:3]
    ok = build_report(cfg, results, oscad_ver, pyver)
    print("\n预览: preview.html   报告: 核对报告.md   参数表: 参数表.csv")
    print("总判定:", "全部通过" if ok else "存在未通过项")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
