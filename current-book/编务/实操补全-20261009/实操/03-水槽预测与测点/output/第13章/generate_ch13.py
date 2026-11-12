#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第13章：在真实照片上分层标点。
输入仅为原照（复制为 original.jpg，不改一像素）。
自动检测三种颜色环的中心，输出 points.json 与 photo-annotation.html。
不确定的点留空/标注，供人工核对；不为了凑 5/5/8 编造位置。
"""
import json, os, sys
from collections import deque
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = "/Users/yaril/个人文档/3 写作/图书出版/00_这本书的全部进展/正文/第13章-二十组同时测量/assets/单点实测-未标注原照.jpg"
DST = os.path.join(HERE, "original.jpg")
EXPECT = {"yellow": 5, "red": 5, "blue": 8}
VOLT = {"yellow": 6, "red": 4, "blue": 2}

# ---------------------------------------------------------------- 0. 原图原样复制
if os.path.abspath(SRC) != os.path.abspath(DST):
    with open(SRC, 'rb') as f, open(DST, 'wb') as g:
        g.write(f.read())
print("原图复制 ->", DST, os.path.getsize(DST), "bytes")

# ---------------------------------------------------------------- 1. 颜色团块检测
im = Image.open(DST).convert('RGB')
A = np.asarray(im).astype(np.float32) / 255.0
IMG_W, IMG_H = im.size
R, G, B = A[..., 0], A[..., 1], A[..., 2]
mx = A.max(2); mn = A.min(2); V = mx
S = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
C = mx - mn
hue = np.zeros_like(mx); m = (C > 1e-6)
rr = (mx == R) & m; gg = (mx == G) & m & ~rr; bb = (mx == B) & m & ~rr & ~gg
hue[rr] = (60 * ((G - B) / np.maximum(C, 1e-6)) % 360)[rr]
hue[gg] = (60 * ((B - R) / np.maximum(C, 1e-6)) + 120)[gg]
hue[bb] = (60 * ((R - G) / np.maximum(C, 1e-6)) + 240)[bb]

def blobs(mask, minarea=100, maxarea=1200):
    out = []; seen = np.zeros(mask.shape, bool)
    for (y0, x0) in np.argwhere(mask):
        if seen[y0, x0]:
            continue
        q = deque([(y0, x0)]); seen[y0, x0] = True; pts = []
        while q:
            y, x = q.popleft(); pts.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < IMG_H and 0 <= nx < IMG_W and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; q.append((ny, nx))
        pts = np.array(pts)
        if minarea <= len(pts) <= maxarea:
            cy, cx = pts[:, 0].mean(), pts[:, 1].mean()
            h = float(pts[:, 0].max() - pts[:, 0].min()) + 1
            w = float(pts[:, 1].max() - pts[:, 1].min()) + 1
            out.append(dict(cx=float(cx), cy=float(cy), area=int(len(pts)),
                            w=w, h=h, fill=float(len(pts) / (w * h))))
    return out

masks = {"yellow": (hue > 45) & (hue < 70) & (S > 0.35) & (V > 0.45),
         "red": ((hue < 12) | (hue > 348)) & (S > 0.45) & (V > 0.35),
         "blue": (hue > 190) & (hue < 260) & (S > 0.30) & (V > 0.30)}

# 坐标纸区域（排除桌面/地板/导线），并排除已知的红色鳄鱼夹导线
TANK_BOX = (120, 830, 820, 1500)     # x0,y0,x1,y1
def in_tank(cx, cy):
    return TANK_BOX[0] < cx < TANK_BOX[2] and TANK_BOX[1] < cy < TANK_BOX[3]

detected, rejected = {}, []
for name, mask in masks.items():
    keep, drop = [], []
    for b in blobs(mask):
        (keep if in_tank(b['cx'], b['cy']) else drop).append(b)
    keep.sort(key=lambda b: (b['cy'], b['cx']))
    detected[name] = keep
    rejected += [dict(color=name, **d) for d in drop]
    print(f"  {name}: 检出 {len(keep)} 个（期望 {EXPECT[name]}）；剔除 {len(drop)} 个区域外团块")

# ---------------------------------------------------------------- 2. 共同中心与半径（二维网格搜索 + 精化）
allpts = [(b['cx'], b['cy'], c) for c, bs in detected.items() for b in bs]
def radii_at(cx, cy):
    out, sse = {}, 0.0
    for c in detected:
        r = np.array([np.hypot(x - cx, y - cy) for x, y, cc in allpts if cc == c])
        R = float(r.mean())
        out[c] = (R, r)
        sse += float(((r - R) ** 2).sum())
    return sse, out
best = None
for cx in np.arange(500.0, 590.0, 1.0):
    for cy in np.arange(1060.0, 1145.0, 1.0):
        s, _ = radii_at(cx, cy)
        if best is None or s < best[0]:
            best = (s, cx, cy)
for step in (0.5, 0.2, 0.05, 0.02):
    s, cx, cy = best; improved = True
    while improved:
        improved = False
        for ddx in (-step, 0, step):
            for ddy in (-step, 0, step):
                ss, _ = radii_at(cx + ddx, cy + ddy)
                if ss < s - 1e-12:
                    s, cx, cy, best = ss, cx + ddx, cy + ddy, (ss, cx + ddx, cy + ddy); improved = True
SSE, RR_ = radii_at(cx, cy)
CX, CY = float(cx), float(cy)
RMAP = {c: RR_[c][0] for c in detected}
rms = {c: float(np.sqrt(np.mean((RR_[c][1] - RMAP[c]) ** 2))) for c in detected}
PAPER_ORIGIN = (550.0, 1100.0)   # 人工从坐标纸主轴线读出的标注原点 O(0,0)
print("  拟合电势中心 (%.2f, %.2f)  半径 黄=%.2f 红=%.2f 蓝=%.2f px  总SSE=%.1f"
      % (CX, CY, RMAP['yellow'], RMAP['red'], RMAP['blue'], SSE))
print("  各色共圆 RMS / px:", {k: round(v, 2) for k, v in rms.items()})
print("  与坐标纸标注原点 (%.0f,%.0f) 相差 %.1f px" % (PAPER_ORIGIN[0], PAPER_ORIGIN[1],
      float(np.hypot(CX - PAPER_ORIGIN[0], CY - PAPER_ORIGIN[1]))))
print("  半径排序 6V=%.1f < 4V=%.1f < 2V=%.1f px → 内高外低，自洽"
      % (RMAP['yellow'], RMAP['red'], RMAP['blue']))

# ---------------------------------------------------------------- 3. 组装点位
points = []
for color in ("yellow", "red", "blue"):
    for i, b in enumerate(detected[color], 1):
        x, y = b['cx'], b['cy']
        rad = float(np.hypot(x - CX, y - CY))
        ang = float(np.degrees(np.arctan2(-(y - CY), x - CX)) % 360)
        dev = round(rad - RMAP[color], 1)
        flags = []
        if b['fill'] < 0.55:
            flags.append("环轮廓不完整（fill=%.2f），中心由残月形轮廓估计" % b['fill'])
        if min(b['w'], b['h']) < 16:
            flags.append("轮廓被裁切（%.0f×%.0f px），中心可能偏移" % (b['w'], b['h']))
        if not (150 <= b['area'] <= 700):
            flags.append("色块面积 %.0f px 偏离常见区间 150—700" % b['area'])
        review = abs(dev) > 0.10 * RMAP[color]
        points.append(dict(id=f"{color[0].upper()}{i}", color=color, voltage=VOLT[color],
                           x=round(x, 1), y=round(y, 1), radius_px=round(rad, 1),
                           circle_dev_px=dev, angle_deg=round(ang, 1), area=b['area'],
                           w=round(b['w'], 1), h=round(b['h'], 1), fill=round(b['fill'], 2),
                           auto=True, uncertain=flags, review=bool(review),
                           note="；".join(flags) if flags else ("—" if not review else "共圆偏离 %.1f px，建议人工核对" % dev)))
cnt = {c: sum(1 for q in points if q['color'] == c) for c in EXPECT}
print("  数量核对:", cnt, "期望:", EXPECT)

# 辅助线（同色按角度顺序），缺测弧段用虚线；标记为草稿、待人工核对
def arcs_for(color):
    ps = sorted([q for q in points if q['color'] == color], key=lambda q: q['angle_deg'])
    res = []
    if len(ps) < 2:
        return res
    gaps = [(ps[(i + 1) % len(ps)]['angle_deg'] - ps[i]['angle_deg']) % 360 for i in range(len(ps))]
    med = float(np.median(gaps))
    thr = max(50.0, 1.6 * med)          # 只有明显大于常规间隔的角度缺口才判为“缺测弧段”
    for i in range(len(ps)):
        a, b_ = ps[i], ps[(i + 1) % len(ps)]
        gap = gaps[i]
        res.append(dict(from_id=a['id'], to_id=b_['id'], gap_deg=round(gap, 1),
                        dashed=bool(gap > thr)))
    return res
aux = {c: arcs_for(c) for c in EXPECT}
for c, a in aux.items():
    gaps = [x['gap_deg'] for x in a]
    print(f"  {c} 角度间隔: {gaps}")

# ---------------------------------------------------------------- 4. 输出 points.json
data = dict(
    source_image="original.jpg", image_size=[IMG_W, IMG_H],
    center_px=dict(x=round(CX, 2), y=round(CY, 2),
                   method="三种颜色环共圆、共享圆心的二维网格搜索最小二乘"),
    paper_origin_px=dict(x=PAPER_ORIGIN[0], y=PAPER_ORIGIN[1],
                         method="人工读坐标纸主轴线交点", note="与拟合中心相差约 %.1f px" % float(np.hypot(CX - PAPER_ORIGIN[0], CY - PAPER_ORIGIN[1]))),
    fit_sse=round(SSE, 2),
    estimated_ring_radius_px=dict(yellow=round(RMAP['yellow'], 2), red=round(RMAP['red'], 2), blue=round(RMAP['blue'], 2)),
    fit_rms_px={k: round(v, 2) for k, v in rms.items()},
    radius_order_check="6V 内环 %.1f px < 4V 中环 %.1f px < 2V 外环 %.1f px，电势越低半径越大，自洽" % (RMAP['yellow'], RMAP['red'], RMAP['blue']),
    colors=dict(yellow=dict(voltage=6, expect=5), red=dict(voltage=4, expect=5), blue=dict(voltage=2, expect=8)),
    detection=dict(color_space="HSV 阈值 + 8 邻域连通域", min_area=100, max_area=1200,
                   tank_box=list(TANK_BOX)),
    rejected_blobs=rejected,
    points=points, auxiliary_arcs_draft=aux,
    status="第一轮自动识别完成；不确定点已在 uncertain 字段列出，等人工核对。",
    not_claimed=["未确认是否存在被鳄鱼夹/导线完全遮挡的环",
                 "颜色—电压对应取自任务，未从照片独立验证",
                 "‘分支’划分待人工核对",
                 "辅助连线为草稿，启用前须人工核对点身份",
                 "像素坐标未做透视矫正"])
json.dump(data, open(os.path.join(HERE, "points.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
n_unc = sum(1 for q in points if q['uncertain']); n_rev = sum(1 for q in points if q['review'])
print("points.json 写出；总点数 = %d，不确定 = %d，共圆偏离待核对 = %d" % (len(points), n_unc, n_rev))
for q in points:
    if q['uncertain'] or q['review']:
        print("   ⚠ %s %s %s" % (q['id'], (q['x'], q['y']), q['note']))

# ---------------------------------------------------------------- 5. HTML
num = {c: 0 for c in EXPECT}
rows_html = []
for q in points:
    num[q['color']] += 1
    need = bool(q['uncertain']) or bool(q['review'])
    st = ('<span style="color:#c62828">待核对</span>' if need else '<span style="color:#0a7a3d">自动识别通过</span>')
    rows_html.append(
        f"<tr data-id='{q['id']}' class=\"{'unc' if need else ''}\">"
        f"<td>{q['id']}</td><td><span class='dot' style='background:{q['color']}'></span>{dict(yellow='黄',red='红',blue='蓝')[q['color']]}</td>"
        f"<td>{q['voltage']} V</td>"
        f"<td><input type='number' step='0.1' value='{q['x']}' data-k='x'></td>"
        f"<td><input type='number' step='0.1' value='{q['y']}' data-k='y'></td>"
        f"<td>{q['radius_px']}</td><td>{q['circle_dev_px']:+.1f}</td><td>{q['angle_deg']}</td><td>{st}</td>"
        f"<td class='nt'>{q['note']}</td></tr>")
rows_html = "".join(rows_html)

unc = [q for q in points if q['uncertain'] or q['review']]
unc_html = "".join(
    f"<li><b>{q['id']}</b>（{q['color']} {q['voltage']}V，像素 {q['x']}, {q['y']}）：{q['note']}</li>"
    for q in unc) or "<li>无——18 个环的第一轮自动识别均未触发不确定条件（<b>仍需人工过目</b>）。</li>"
rej_html = "".join(f"<li>{d['color']} 团块 像素({d['cx']:.0f}, {d['cy']:.0f})、面积 {d['area']} → 判定为画面外/导线，已剔除</li>" for d in rejected) or "<li>无</li>"
cnt_html = "".join(f"<tr><td>{k}</td><td>{cnt[k]}</td><td>{EXPECT[k]}</td><td>{'数量一致，仍须逐点核对' if cnt[k]==EXPECT[k] else '⚠️ 不一致'}</td></tr>" for k in EXPECT)
aux_json = json.dumps(aux, ensure_ascii=False)
n_dash = sum(1 for c in aux for a in aux[c] if a['dashed'])

html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>第11章 · 真实照片分层标点</title>
<style>
:root{{--ink:#1b1f24;--sub:#5b646e;--line:#dfe4ea;--bg:#f6f7f9;--card:#fff;--hl:#0b63ce}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}}
header{{padding:20px 26px 14px;background:#fff;border-bottom:1px solid var(--line)}}
h1{{margin:0 0 6px;font-size:21px}} h2{{font-size:16px;margin:20px 0 8px;padding-left:9px;border-left:4px solid var(--hl)}}
.sub{{color:var(--sub);font-size:13.5px}}
.wrap{{display:grid;grid-template-columns:minmax(340px,1fr) minmax(420px,1.25fr);gap:18px;padding:16px 26px 60px;align-items:start}}
@media(max-width:980px){{.wrap{{grid-template-columns:1fr}}}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-bottom:12px}}
.stagewrap{{position:relative;background:#fff;border:1px solid var(--line);border-radius:12px;padding:8px;overflow:auto;max-height:82vh}}
.stage{{position:relative;margin:0 auto}}
.stage img{{display:block;width:100%;height:auto}}
.stage svg{{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}}
.mk{{cursor:pointer}}
.mk.tweak{{cursor:grab}}
.side{{display:flex;gap:10px;align-items:flex-start}}
.btnrow{{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0}}
button{{font:inherit;font-size:13.5px;padding:6px 11px;border-radius:8px;border:1px solid var(--line);background:#fff;cursor:pointer}}
button:hover{{border-color:var(--hl);color:var(--hl)}}
button.on{{background:#e8f0fd;border-color:var(--hl);color:var(--hl)}}
label.ck{{display:flex;gap:7px;align-items:center;font-size:14px;margin:4px 0}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border-bottom:1px solid var(--line);padding:5px 7px;text-align:left;vertical-align:middle}}
th{{background:#f2f4f7;font-weight:600;position:sticky;top:0}}
tr.unc td{{background:#fffaf0}}
td.nt{{color:#c62828;font-size:12px}}
input[type=number]{{width:78px;font:inherit;font-size:12.5px;padding:2px 4px;border:1px solid var(--line);border-radius:5px}}
.dot{{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:5px;vertical-align:-1px}}
.note{{background:#fff8e6;border:1px solid #f0d79a;border-radius:9px;padding:9px 12px;font-size:13.5px}}
.warn{{background:#fdecec;border-color:#f0b9b9}}
.ok{{background:#eaf7ee;border-color:#b6e0c2}}
.tblwrap{{max-height:340px;overflow:auto;border:1px solid var(--line);border-radius:9px}}
.pair{{display:none;gap:10px}} .pair.show{{display:flex}}
.pair>div{{flex:1;min-width:0}}
</style></head><body>
<header>
<h1>第 11 章 · 在真实照片上分层标点</h1>
<div class="sub">底层为原照 <code>original.jpg</code>（原样复制、未重绘、未涂改、未裁剪）；标记为独立 SVG 叠层。黄环 6 V 共 5、红环 4 V 共 5、蓝环 2 V 共 8。</div>
</header>
<div class="wrap">
  <div>
    <div class="card">
      <div class="btnrow">
        <button id="bNum" class="on" onclick="tg('bNum','numg')">显示/隐藏编号</button>
        <button id="bCenter" onclick="tg('bCenter','centerLayer')">环中心十字</button>
        <button id="bMark" class="on" onclick="tg('bMark','markLayer')">显示/隐藏标记</button>
        <button id="bAux" onclick="tg('bAux','auxLayer')">辅助连线（草稿·待核对）</button>
      </div>
      <div class="btnrow">
        <button id="bPhotoOnly" onclick="onlyPhoto()">只看原图（关掉全部叠层）</button>
        <button id="bOverlayOnly" onclick="onlyOverlay()">只看叠层（关掉原图）</button>
        <button id="bPair" onclick="togglePair()">并排：原图 ｜ 标注</button>
        <button id="bEdit" onclick="toggleEdit()">调整点位</button>
      </div>
      <div class="btnrow">
        <label class="ck"><input type="checkbox" id="cbGrid" onchange="document.getElementById('gridLayer').style.display=this.checked?'':'none'"> 叠一层像素网格（便于人工核对坐标）</label>
      </div>
      <div class="sub">缩放：<input type="range" min="60" max="200" value="100" style="width:180px" oninput="setZoom(this.value)"></div>
      <div class="sub" id="hint">点“调整点位”后：点选标记可直接拖动，或用方向键 ±1 px 微调。</div>
    </div>
    <div class="side">
      <div id="plainPane" style="display:none;flex:1;min-width:0">
        <div class="sub" style="text-align:center">原照（无叠层、未标注）</div>
        <div class="stagewrap"><img src="original.jpg" alt="单点实测-未标注原照" style="width:100%;display:block"></div>
      </div>
      <div style="flex:1;min-width:0">
        <div class="sub" style="text-align:center" id="annTitle">标注（原图 ＋ 独立 SVG 叠层）</div>
        <div class="stagewrap" id="stagewrap"><div class="stage" id="stage">
          <img id="baseImg" src="original.jpg" alt="单点实测-未标注原照">
          <svg id="ov" viewBox="0 0 {IMG_W} {IMG_H}" preserveAspectRatio="none">
            <g id="gridLayer" style="display:none"></g>
            <g id="centerLayer"></g>
            <g id="auxLayer" style="display:none"></g>
            <g id="markLayer"></g>
            <g id="numg"></g>
          </svg>
        </div></div>
      </div>
    </div>
  </div>

  <div>
    <h2>一、第一轮：自动识别 + 编号</h2>
    <div class="card">
      <p style="margin-top:0">用 HSV 阈值 + 连通域自动找出三种彩色环的中心（不重画、不合成）。识别出的数量：</p>
      <table><tr><th>颜色</th><th>识别数</th><th>应有数</th><th>核对</th></tr>{cnt_html}</table>
      <p class="sub">数量一致，仍须逐点核对；下面列出被剔除的团块与触发不确定条件的点。</p>
      <p><b>被剔除的团块（非环）</b></p><ul style="margin:4px 0 0 18px;padding:0">{rej_html}</ul>
      <p style="margin-top:10px"><b>不确定点（留待人工核对）</b></p><ul style="margin:4px 0 0 18px;padding:0">{unc_html}</ul>
    </div>

    <h2>二、各色共圆校验</h2>
    <div class="card">
      <p style="margin-top:0">把三种颜色的环分别作共圆拟合（共享同一圆心、各色一个半径，圆心用二维网格搜索最小二乘）：</p>
      <table><tr><th>颜色</th><th>半径 / px</th><th>共圆 RMS / px</th><th>半径 / 拟合中心的相对偏差</th></tr>
        <tr><td>黄 6V</td><td>{RMAP['yellow']:.2f}</td><td>{rms['yellow']:.2f}</td><td>{(rms['yellow']/RMAP['yellow']*100):.1f}%</td></tr>
        <tr><td>红 4V</td><td>{RMAP['red']:.2f}</td><td>{rms['red']:.2f}</td><td>{(rms['red']/RMAP['red']*100):.1f}%</td></tr>
        <tr><td>蓝 2V</td><td>{RMAP['blue']:.2f}</td><td>{rms['blue']:.2f}</td><td>{(rms['blue']/RMAP['blue']*100):.1f}%</td></tr></table>
      <div class="note ok">
        <b>两个独立佐证：</b><br>
        ① 拟合出的电势中心在 <code>({CX:.2f}, {CY:.2f})</code> px，人工从坐标纸主轴线读出的标注原点在 <code>({PAPER_ORIGIN[0]:.0f}, {PAPER_ORIGIN[1]:.0f})</code> px，两者相差约 {float(np.hypot(CX-PAPER_ORIGIN[0], CY-PAPER_ORIGIN[1])):.1f} px（约等于环半径的一半，属读图与贴点误差量级）。<br>
        ② 半径随电势下降而增大：6V 内环 {RMAP['yellow']:.1f} px &lt; 4V 中环 {RMAP['red']:.1f} px &lt; 2V 外环 {RMAP['blue']:.1f} px，与「内高外低」的场一致。<br>
        红、黄的共圆 RMS 只有几 px；蓝的偏大，与其轮廓被裁切、环更大有关。
      </div>
    </div>

    <h2>三、像素坐标表（可编辑）</h2>
    <div class="card">
      <div class="tblwrap"><table id="ptTable">
        <tr><th>编号</th><th>颜色</th><th>电势</th><th>x / px</th><th>y / px</th><th>半径</th><th>共圆偏差</th><th>角度°</th><th>状态</th><th>说明</th></tr>
        {rows_html}
      </table></div>
      <div class="btnrow" style="margin-top:8px">
        <button onclick="nudge(-1,0)">← 选中点 −1px</button><button onclick="nudge(1,0)">→</button>
        <button onclick="nudge(0,-1)">↑</button><button onclick="nudge(0,1)">↓</button>
        <button onclick="addPoint('yellow')">＋黄点</button><button onclick="addPoint('red')">＋红点</button>
        <button onclick="addPoint('blue')">＋蓝点</button>
        <button onclick="delPoint()">删除选中</button>
        <button onclick="resetPoints()">还原自动识别结果</button>
      </div>
      <div class="btnrow">
        <button onclick="exportJSON()">导出 points.json</button>
        <button onclick="exportPNG()">导出标注 PNG（原图叠加副本）</button>
      </div>
    </div>

    <h2>四、辅助连线（人工核对后才用）</h2>
    <div class="card">
      <div class="note warn" style="margin-top:0">
        <b>先别当结论用。</b>同色、同分支的点按空间顺序连成的弧线只是“辅助连线，<b>非新增实测</b>”；缺测弧段用虚线表示这里是<b>没测</b>，<b>不是</b>已经测出等势。连线本身不证明缺测处等势。左边按钮默认是关的，请人工核对完点位身份（哪些点属于同一分支）再打开。
      </div>
      <table><tr><th>颜色</th><th>相邻点角度间隔 / °（明显大于常规间隔的才判为缺测弧段→虚线）</th></tr>
        {"".join(f"<tr><td>{k}</td><td>{', '.join(str(x['gap_deg']) for x in v)}</td></tr>" for k, v in aux.items())}
      </table>
      <div class="note"><b>本次结果：</b>三种颜色的点都基本均匀铺满各自的圆（角度间隔彼此接近），<b>按几何判据没有识别出明显的缺测弧段，因此虚线数为 {n_dash}</b>。有没有“缺测”，最终要按实验方案里<b>原本该测哪些角度</b>来定，不能只靠几何。判据（阈值）可在本页脚本里改。</div>
      <p class="sub" style="margin-bottom:0">红线不会接到黄环或蓝环；不同颜色之间不连线。</p>
    </div>

    <h2>五、还没做 / 不能声称的</h2>
    <div class="card"><ul style="margin:0 0 0 18px;padding:0">
      <li>所有点仍是自动候选，尚待人工逐点核对。“自动识别通过”只表示未触发程序的不确定条件；“待核对”提示优先检查的点。</li>
      <li>不能排除被鳄鱼夹或导线<b>完全遮住</b>的环（遮挡处无颜色证据）。</li>
      <li>颜色↔电压（黄6/红4/蓝2 V）沿用任务给定，未从照片独立验证。</li>
      <li>照片为透视拍摄，像素坐标未做透视矫正；环本身有直径，中心存在约 ±2 px 估计误差。</li>
      <li>未导出 PNG 作为“实测图”——如需，用上面的按钮生成，它只是原图叠加标注的副本。</li>
    </ul></div>
  </div>
</div>
<script>
const IMG_W={IMG_W}, IMG_H={IMG_H};
let PTS={json.dumps(points, ensure_ascii=False)};
const AUTO={json.dumps(points, ensure_ascii=False)};
const CENTER=[{CX},{CY}];
const RAD={json.dumps({k: round(v,1) for k,v in RMAP.items()}, ensure_ascii=False)};
const AUX={aux_json};
const COL={{yellow:'#e8b400', red:'#e23b2e', blue:'#1f6feb'}};
let sel=null, editMode=false;

function render(){{
  const mg=document.getElementById('markLayer'), ng=document.getElementById('numg'), cg=document.getElementById('centerLayer');
  mg.innerHTML=''; ng.innerHTML=''; cg.innerHTML='';
  // 中心与共圆参考
  cg.innerHTML += `<circle cx="${{CENTER[0]}}" cy="${{CENTER[1]}}" r="9" fill="none" stroke="#111" stroke-width="2"/>`
               +  `<path d="M${{CENTER[0]-16}},${{CENTER[1]}} L${{CENTER[0]+16}},${{CENTER[1]}} M${{CENTER[0]}},${{CENTER[1]-16}} L${{CENTER[0]}},${{CENTER[1]+16}}" stroke="#111" stroke-width="2" fill="none"/>`
               +  `<text x="${{CENTER[0]+14}}" y="${{CENTER[1]-14}}" font-size="26" fill="#111">O(O,0) 中心</text>`;
  // 辅助弧线
  const ag=document.getElementById('auxLayer'); ag.innerHTML='';
  for(const c in AUX){{
    for(const a of AUX[c]){{
      const p1=PTS.find(p=>p.id===a.from_id), p2=PTS.find(p=>p.id===a.to_id);
      if(!p1||!p2) continue;
      const a1=Math.atan2(-(p1.y-CENTER[1]),p1.x-CENTER[0]), a2=Math.atan2(-(p2.y-CENTER[1]),p2.x-CENTER[0]);
      let d=a2-a1; if(d<0) d+=2*Math.PI;
      const R=RAD[c]; let pts=[];
      for(let k=0;k<=48;k++){{const t=a1+d*k/48; pts.push((CENTER[0]+R*Math.cos(t)).toFixed(1)+','+(CENTER[1]-R*Math.sin(t)).toFixed(1));}}
      ag.innerHTML += `<polyline points="${{pts.join(' ')}}" fill="none" stroke="${{COL[c]}}" stroke-width="3" `
                    + `stroke-dasharray="${{a.dashed?'14,10':''}}" opacity="0.75"/>`;
    }}
  }}
  // 标记
  for(const p of PTS){{
    const c=COL[p.color];
    const unc=p.uncertain&&p.uncertain.length;
    mg.innerHTML += `<g class="mk${{editMode?' tweak':''}}" data-id="${{p.id}}" style="pointer-events:all">`
      + `<circle cx="${{p.x}}" cy="${{p.y}}" r="17" fill="none" stroke="${{c}}" stroke-width="4"/>`
      + `<circle cx="${{p.x}}" cy="${{p.y}}" r="2.5" fill="${{c}}"/>`
      + `<path d="M${{p.x-23}},${{p.y}} L${{p.x-8}},${{p.y}} M${{p.x+8}},${{p.y}} L${{p.x+23}},${{p.y}} M${{p.x}},${{p.y-23}} L${{p.x}},${{p.y-8}} M${{p.x}},${{p.y+8}} L${{p.x}},${{p.y+23}}" stroke="${{c}}" stroke-width="2.5" fill="none"/>`
      + (unc?`<circle cx="${{p.x}}" cy="${{p.y}}" r="25" fill="none" stroke="#c62828" stroke-width="2" stroke-dasharray="5,4"/>`:'')
      + `</g>`;
    const ux0=p.x-CENTER[0], uy0=p.y-CENTER[1], LL=Math.hypot(ux0,uy0)||1;
    const lx=p.x+36*ux0/LL, ly=p.y+36*uy0/LL;
    ng.innerHTML += `<g><rect x="${{lx-26}}" y="${{ly-16}}" width="52" height="27" rx="6" fill="#ffffffee" stroke="${{c}}" stroke-width="2"/>`
      + `<text x="${{lx}}" y="${{ly+5}}" font-size="21" text-anchor="middle" fill="#111" font-weight="700">${{p.id}}</text></g>`;
  }}
  // 网格
  const gg=document.getElementById('gridLayer');
  if(gg&&!gg.dataset.done){{ let s='';
    for(let x=0;x<IMG_W;x+=50) s+=`<line x1="${{x}}" y1="0" x2="${{x}}" y2="${{IMG_H}}" stroke="#0b63ce" stroke-width="1" opacity="0.35"/>`;
    for(let y=0;y<IMG_H;y+=50) s+=`<line x1="0" y1="${{y}}" x2="${{IMG_W}}" y2="${{y}}" stroke="#0b63ce" stroke-width="1" opacity="0.35"/>`;
    for(let x=0;x<IMG_W;x+=200)for(let y=0;y<IMG_H;y+=200) s+=`<text x="${{x+4}}" y="${{y+22}}" font-size="20" fill="#0b63ce">${{x}},${{y}}</text>`;
    gg.innerHTML=s; gg.dataset.done=1; }}
  syncTable();
}}
function tg(btn,id){{const e=document.getElementById(id);const on=e.style.display!=='none';e.style.display=on?'none':'';document.getElementById(btn).classList.toggle('on',!on);}}
function onlyPhoto(){{const s=document.getElementById('ov');const hide=s.style.display!=='none';s.style.display=hide?'none':'';document.getElementById('bPhotoOnly').classList.toggle('on',hide);}}
function onlyOverlay(){{const i=document.getElementById('baseImg');const hide=i.style.visibility!=='hidden';i.style.visibility=hide?'hidden':'visible';document.getElementById('bOverlayOnly').classList.toggle('on',hide);}}
function setZoom(v){{document.getElementById('stage').style.width=v+'%';}}
function togglePair(){{const p=document.getElementById('plainPane');const on=p.style.display==='none';p.style.display=on?'block':'none';document.getElementById('bPair').classList.toggle('on',on);}}
function toggleEdit(){{editMode=!editMode;document.getElementById('bEdit').classList.toggle('on',editMode);
  document.getElementById('hint').textContent=editMode?'拖动模式已开：点选标记后直接拖动，或用方向键 ±1 px 微调。':'点“调整点位”后：点选标记可直接拖动，或用方向键 ±1 px 微调。';render();}}
function syncTable(){{
  document.querySelectorAll('#ptTable tr[data-id]').forEach(tr=>{{
    const p=PTS.find(q=>q.id===tr.dataset.id); if(!p) return;
    tr.querySelector("input[data-k=x]").value=p.x.toFixed(1);
    tr.querySelector("input[data-k=y]").value=p.y.toFixed(1);
  }});
}}
function select(id){{sel=id;document.querySelectorAll('#ptTable tr[data-id]').forEach(tr=>tr.style.outline=(tr.dataset.id===id?'2px solid #0b63ce':''));}}
function nudge(dx,dy){{const p=PTS.find(q=>q.id===sel);if(!p)return alert('先在下面表格或图上选一个点');p.x=Math.round((p.x+dx)*10)/10;p.y=Math.round((p.y+dy)*10)/10;render();}}
function addPoint(color){{const i=PTS.filter(q=>q.color===color).length+1;
  PTS.push({{id:color[0].toUpperCase()+i+(PTS.some(q=>q.id===color[0].toUpperCase()+i)?'x':''),color:color,
    voltage:{{yellow:6,red:4,blue:2}}[color],x:Math.round(CENTER[0]),y:Math.round(CENTER[1]),radius_px:0,angle_deg:0,
    area:0,w:0,h:0,fill:0,auto:false,uncertain:['人工新增，待核对'],note:'人工新增，待核对'}});render();}}
function delPoint(){{if(!sel) return alert('先选一个点');PTS=PTS.filter(q=>q.id!==sel);sel=null;render();}}
function resetPoints(){{PTS=JSON.parse(JSON.stringify(AUTO));sel=null;render();}}
function exportJSON(){{const d=Object.assign({{}},{{source_image:'original.jpg',image_size:[IMG_W,IMG_H],
  center_px:{{x:CENTER[0],y:CENTER[1]}},points:PTS,edited:true}});
  dl(new Blob([JSON.stringify(d,null,2)],{{type:'application/json'}}),'points.edited.json');}}
function exportPNG(){{const img=document.getElementById('baseImg');const cv=document.createElement('canvas');
  cv.width=IMG_W;cv.height=IMG_H;const ctx=cv.getContext('2d');ctx.drawImage(img,0,0,IMG_W,IMG_H);
  for(const p of PTS){{const c=COL[p.color];ctx.strokeStyle=c;ctx.lineWidth=4;ctx.beginPath();ctx.arc(p.x,p.y,17,0,7);ctx.stroke();
    ctx.fillStyle='#000';ctx.font='bold 24px sans-serif';ctx.fillText(p.id,p.x+20,p.y-20);}}
  cv.toBlob(b=>dl(b,'original-annotated.png'));}}
function dl(blob,name){{const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();URL.revokeObjectURL(a.href);}}
// 拖动
let drag=null;
document.getElementById('ov').addEventListener('pointerdown',e=>{{
  const g=e.target.closest('.mk'); if(!g) return; select(g.dataset.id);
  if(editMode){{drag=g.dataset.id; const svg=document.getElementById('ov'); svg.setPointerCapture(e.pointerId);}}
}});
document.getElementById('ov').addEventListener('pointermove',e=>{{
  if(!drag) return; const svg=document.getElementById('ov'); const r=svg.getBoundingClientRect();
  const p=PTS.find(q=>q.id===drag); if(!p) return;
  p.x=Math.round((e.clientX-r.left)/r.width*IMG_W*10)/10; p.y=Math.round((e.clientY-r.top)/r.height*IMG_H*10)/10; render();
}});
document.getElementById('ov').addEventListener('pointerup',()=>{{drag=null;}});
document.querySelectorAll('#ptTable input').forEach(inp=>{{
  inp.addEventListener('change',()=>{{const id=inp.closest('tr').dataset.id;const p=PTS.find(q=>q.id===id);
    const k=inp.dataset.k;p[k]=parseFloat(inp.value)||0;render();}});
}});
document.querySelectorAll('#ptTable tr[data-id]').forEach(tr=>tr.addEventListener('click',()=>select(tr.dataset.id)));
document.addEventListener('keydown',e=>{{if(!sel)return;const m={{ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}}[e.key];
  if(m){{e.preventDefault();nudge(m[0],m[1]);}}}});
document.getElementById('baseImg').addEventListener('load',()=>{{document.getElementById('stage').style.width='100%';render();}});
render();
</script>
</body></html>
"""
open(os.path.join(HERE, "photo-annotation.html"), "w", encoding="utf-8").write(html)
print("photo-annotation.html 写出 (%d KB)" % (len(html) // 1024))
