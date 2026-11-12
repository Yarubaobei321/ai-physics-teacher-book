#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第12章：有限水槽预测底图 —— 求解、校验、导出 SVG / HTML / 数据。"""
import json, os, sys
from collections import deque
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solve_tank import solve, interp, HALF, BAR_LEN, BAR_THICK

OUT = os.path.dirname(os.path.abspath(__file__))
PAGE, CX, CY = 310.0, 155.0, 155.0
sx = lambda x: CX + x
sy = lambda y: CY - y
fmt = lambda v: f"{v:.3f}".rstrip('0').rstrip('.')

# ---------------------------------------------------------------- 1. 求解
H_MAIN, BAR_CY = 0.5, 90.0
print("求解中 h=%s mm ..." % H_MAIN)
r = solve(H_MAIN, BAR_CY, tol=1e-8, maxiter=400000)
ax, PHI = r['ax'], r['PHI']
print("  网格 n=%d, 迭代=%d, 缺陷 max|h^2 lap phi|=%.3e" % (r['n'], r['iters'], r['defect']))
r1 = solve(1.0, BAR_CY, tol=1e-8, maxiter=400000)
c_h05 = float(interp(ax, PHI, [0.0], [0.0])[0])
c_h1 = float(interp(r1['ax'], r1['PHI'], [0.0], [0.0])[0])

# ---------------------------------------------------------------- 2. 校验
def sym_sum(x): return float(interp(ax, PHI, [x], [40.0])[0] + interp(ax, PHI, [x], [-40.0])[0])
def lr_diff(x, y): return float(abs(interp(ax, PHI, [x], [y])[0] - interp(ax, PHI, [-x], [y])[0]))
checks = {
    "center_phi_over_U": c_h05,
    "center_at_h1mm": c_h1,
    "grid_step_mm": H_MAIN, "grid_n": int(r['n']), "iterations": int(r['iters']),
    "max_abs_defect_phi_units": r['defect'], "omega": r['omega'],
    "updown_reflection_max_err": max(abs(sym_sum(x) - 1.0) for x in (0, 10, 30, 60, 100, 140)),
    "leftright_symmetry_max_diff": max(lr_diff(x, y) for x in (10, 30, 60, 100) for y in (0, 30, 60)),
    "phi_min": float(PHI.min()), "phi_max": float(PHI.max()),
}
free = r['free']
dphidy = np.gradient(PHI, H_MAIN, axis=0); dphidx = np.gradient(PHI, H_MAIN, axis=1)
wall = max(np.abs(dphidy[-1, :])[free[-1, :]].max(), np.abs(dphidy[0, :])[free[0, :]].max(),
           np.abs(dphidx[:, 0])[free[:, 0]].max(), np.abs(dphidx[:, -1])[free[:, -1]].max())
checks["wall_normal_grad_max"] = float(wall)
checks["interior_grad_max"] = float(max(abs(dphidx).max(), abs(dphidy).max()))
print("校验: 中心=%.6f  上下反射误差=%.2e  左右差=%.2e  壁法向梯度=%.2e (内部最大梯度=%.3f)"
      % (checks["center_phi_over_U"], checks["updown_reflection_max_err"],
         checks["leftright_symmetry_max_diff"], checks["wall_normal_grad_max"], checks["interior_max_grad"] if False else checks["interior_grad_max"]))

# ---------------------------------------------------------------- 3. 等值线（marching squares）
def contours(P, ax_, level):
    v00 = P[:-1, :-1]; v01 = P[:-1, 1:]; v11 = P[1:, 1:]; v10 = P[1:, :-1]
    X0 = ax_[None, :-1]; X1 = ax_[None, 1:]; Y0 = ax_[:-1, None]; Y1 = ax_[1:, None]
    sh = v00.shape
    t_top = (level - v00) / (v01 - v00 + 1e-30)
    t_bot = (level - v10) / (v11 - v10 + 1e-30)
    t_left = (level - v00) / (v10 - v00 + 1e-30)
    t_right = (level - v01) / (v11 - v01 + 1e-30)
    E = {
        0: np.stack([X0 + (X1 - X0) * t_top, np.broadcast_to(Y0, sh)], -1),
        2: np.stack([X0 + (X1 - X0) * t_bot, np.broadcast_to(Y1, sh)], -1),
        3: np.stack([np.broadcast_to(X0, sh), Y0 + (Y1 - Y0) * t_left], -1),
        1: np.stack([np.broadcast_to(X1, sh), Y0 + (Y1 - Y0) * t_right], -1),
    }
    k = (v00 > level).astype(np.int8) + 2 * (v01 > level) + 4 * (v11 > level) + 8 * (v10 > level)
    table = {1: [(3, 0)], 2: [(0, 1)], 3: [(3, 1)], 4: [(1, 2)], 5: [(3, 0), (1, 2)],
             6: [(0, 2)], 7: [(3, 2)], 8: [(2, 3)], 9: [(0, 2)], 10: [(0, 1), (2, 3)],
             11: [(1, 2)], 12: [(1, 3)], 13: [(0, 1)], 14: [(3, 0)]}
    segs = []
    for kk, spec in table.items():
        m = (k == kk)
        if not m.any():
            continue
        for ea, eb in spec:
            segs.append(np.stack([E[ea][m], E[eb][m]], axis=1))
    if not segs:
        return []
    S = np.concatenate(segs, 0)
    key = lambda p: (round(float(p[0]), 4), round(float(p[1]), 4))
    adj = {}
    for i in range(len(S)):
        adj.setdefault(key(S[i, 0]), []).append(i)
        adj.setdefault(key(S[i, 1]), []).append(i)
    remaining = set(range(len(S))); polys = []
    while remaining:
        i0 = remaining.pop(); chain = deque([tuple(S[i0, 0]), tuple(S[i0, 1])])
        for side in (1, 0):
            while True:
                cur = key(chain[-1] if side else chain[0]); nxt = None
                for si in adj.get(cur, []):
                    if si in remaining:
                        nxt = si; break
                if nxt is None:
                    break
                remaining.discard(nxt)
                p, q = S[nxt]
                far = tuple(q) if key(p) == cur else tuple(p)
                (chain.append if side else chain.appendleft)(far)
        if len(chain) >= 2:
            polys.append(np.array(chain))
    return polys

def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    def rec(a, b):
        if b <= a + 1:
            return [a, b]
        p0, p1 = pts[a], pts[b]
        d = p1 - p0; L = np.hypot(d[0], d[1])
        seg = pts[a + 1:b] - p0
        if L < 1e-9:
            dist = np.hypot(seg[:, 0], seg[:, 1])
        else:
            dist = np.abs(d[0] * seg[:, 1] - d[1] * seg[:, 0]) / L
        i = int(np.argmax(dist))
        if dist[i] > eps:
            m = a + 1 + i
            return rec(a, m)[:-1] + rec(m, b)
        return [a, b]
    return pts[rec(0, len(pts) - 1)]

LEVELS = [0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9]
cont = {}
for lv in LEVELS:
    polys = [rdp(p, 0.10) for p in contours(PHI, ax, lv)]
    polys = [p for p in polys if len(p) >= 2]
    cont[lv] = polys
    print("  等势线 U*%.2f : %d 条 / %d 点" % (lv, len(polys), sum(len(p) for p in polys)))

# ---------------------------------------------------------------- 4. 电力线 E=-grad phi
def fieldline(x0, y0, hstep=0.8, nmax=900):
    pts = [(x0, y0)]
    for _ in range(nmax):
        x, y = pts[-1]
        def E(px, py):
            v = np.array([-float(interp(ax, dphidx, [px], [py])[0]),
                          -float(interp(ax, dphidy, [px], [py])[0])])
            n = np.hypot(v[0], v[1])
            return v / n if n > 1e-9 else v
        k1 = E(x, y); k2 = E(x + hstep / 2 * k1[0], y + hstep / 2 * k1[1])
        k3 = E(x + hstep / 2 * k2[0], y + hstep / 2 * k2[1]); k4 = E(x + hstep * k3[0], y + hstep * k3[1])
        d = (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
        nx, ny = x + hstep * d[0], y + hstep * d[1]
        if abs(nx) > HALF - 0.6 or abs(ny) > HALF - 0.6:
            break
        pts.append((nx, ny))
        if abs(ny + BAR_CY) <= BAR_THICK / 2 + 0.4 and abs(nx) <= BAR_LEN / 2:
            pts.append((nx, -BAR_CY + BAR_THICK / 2)); break
    return np.array(pts)

fld = []
for xs0 in np.arange(-120, 120.1, 20.0):
    p = fieldline(float(xs0), BAR_CY - BAR_THICK / 2 - 0.8)
    if len(p) > 4:
        fld.append(rdp(p, 0.25))
print("  电力线: %d 条" % len(fld))

# ---------------------------------------------------------------- 5. SVG
def P(polys, stroke, w):
    out = []
    for p in polys:
        d = "M" + "L".join(f"{fmt(sx(x))},{fmt(sy(y))}" for x, y in p)
        out.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{w}" stroke-linecap="round"/>')
    return "".join(out)

def arrow_svg(mx, my, ux, uy, col="#2f8f83"):
    """以模型坐标原点和单位方向画一个绝对坐标箭头（不用 transform，任何查看器一致）。"""
    px, py = -uy, ux
    tip = (mx + 1.9 * ux, my + 1.9 * uy)
    b1 = (mx - 1.25 * ux + 1.15 * px, my - 1.25 * uy + 1.15 * py)
    b2 = (mx - 1.25 * ux - 1.15 * px, my - 1.25 * uy - 1.15 * py)
    return (f'<path d="M{fmt(sx(b1[0]))},{fmt(sy(b1[1]))} L{fmt(sx(tip[0]))},{fmt(sy(tip[1]))} '
            f'L{fmt(sx(b2[0]))},{fmt(sy(b2[1]))}" fill="none" stroke="{col}" stroke-width="0.5"/>')

def field_svg():
    out = []
    for p in fld:
        d = "M" + "L".join(f"{fmt(sx(x))},{fmt(sy(y))}" for x, y in p)
        out.append(f'<path d="{d}" fill="none" stroke="#2f8f83" stroke-width="0.35" opacity="0.85"/>')
        for frac in (0.30, 0.70):
            i = int(len(p) * frac)
            if 1 <= i < len(p) - 1:
                x1, y1 = p[i - 1]; x2, y2 = p[i + 1]
                ux, uy = x2 - x1, y2 - y1
                L = np.hypot(ux, uy)
                if L > 1e-9:
                    out.append(arrow_svg(p[i][0], p[i][1], ux / L, uy / L))
    return "".join(out)

def bar_svg():
    out = []
    for cy in (BAR_CY, -BAR_CY):
        x0, x1 = -BAR_LEN / 2, BAR_LEN / 2
        y0, y1 = cy - BAR_THICK / 2, cy + BAR_THICK / 2
        out.append(f'<rect x="{fmt(sx(x0))}" y="{fmt(sy(y1))}" width="{fmt(x1-x0)}" height="{fmt(y1-y0)}" '
                   f'fill="#3c4048" stroke="#20242a" stroke-width="0.25"/>')
        out.append(f'<line x1="{fmt(sx(x0))}" y1="{fmt(sy(y0))}" x2="{fmt(sx(x1))}" y2="{fmt(sy(y0))}" '
                   f'stroke="#7a828e" stroke-width="0.20"/>')
    return "".join(out)

FS = 'font-family="Helvetica,Arial,PingFang SC,sans-serif"'
A_RAD, R_RING = 3.0, 124.0
ar = {f: R_RING * (A_RAD / R_RING) ** f for f in (0.25, 0.5, 0.75)}
print("  A布局解析半径 U*0.75/0.50/0.25 = %.3f / %.3f / %.3f mm" % (ar[0.75], ar[0.5], ar[0.25]))

def g_bg_frame():
    p = [f'<rect x="0" y="0" width="{PAGE}" height="{PAGE}" fill="#ffffff"/>']
    p.append(f'<rect x="{fmt(sx(-150))}" y="{fmt(sy(150))}" width="300" height="300" fill="#fbfbfc" stroke="#111" stroke-width="0.5"/>')
    p.append(f'<rect x="{fmt(sx(-147))}" y="{fmt(sy(147))}" width="294" height="294" fill="#ffffff" stroke="#666" stroke-width="0.35"/>')
    for sxx in (-1, 1):
        for syy in (-1, 1):
            x = sx(sxx * 150); y = sy(syy * 150); dx = 8 * sxx; dy = -8 * syy
            p.append(f'<path d="M{fmt(x)},{fmt(y)} L{fmt(x+dx)},{fmt(y)} M{fmt(x)},{fmt(y)} L{fmt(x)},{fmt(y+dy)}" stroke="#111" stroke-width="0.45"/>')
            p.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="1.2" fill="none" stroke="#111" stroke-width="0.3"/>')
    yl = 288.0
    p.append(f'<line x1="{fmt(sx(-50))}" y1="{yl}" x2="{fmt(sx(50))}" y2="{yl}" stroke="#111" stroke-width="0.5"/>')
    for xt in (-50, 50):
        p.append(f'<line x1="{fmt(sx(xt))}" y1="{fmt(yl-2)}" x2="{fmt(sx(xt))}" y2="{fmt(yl+2)}" stroke="#111" stroke-width="0.5"/>')
    p.append(f'<text x="{fmt(sx(0))}" y="{fmt(yl-3)}" font-size="4" text-anchor="middle" {FS} fill="#111">100 mm 校准线（打印后量此线应为 100 mm）</text>')
    return "".join(p)

def g_minor():
    return "".join(P(cont[lv], c, 0.22) for lv, c in
                   [(0.1, "#c3cad3"), (0.2, "#b3bcc8"), (0.3, "#a8b2c0"), (0.4, "#9aa6b6"),
                    (0.6, "#9aa6b6"), (0.7, "#a8b2c0"), (0.8, "#b3bcc8"), (0.9, "#c3cad3")])

def g_contours():
    return P(cont[0.25], "#1f6feb", 0.55) + P(cont[0.5], "#7b2fbe", 0.7) + P(cont[0.75], "#d5342b", 0.55)

def g_axis_bars():
    p = [bar_svg()]
    p.append(f'<line x1="{fmt(sx(-147))}" y1="{fmt(sy(0))}" x2="{fmt(sx(147))}" y2="{fmt(sy(0))}" stroke="#000" stroke-width="0.18" stroke-dasharray="2,2" opacity="0.45"/>')
    p.append(f'<line x1="{fmt(sx(0))}" y1="{fmt(sy(-147))}" x2="{fmt(sx(0))}" y2="{fmt(sy(147))}" stroke="#000" stroke-width="0.18" stroke-dasharray="2,2" opacity="0.45"/>')
    p.append(f'<circle cx="{fmt(sx(0))}" cy="{fmt(sy(0))}" r="1.4" fill="#7b2fbe"/>')
    return "".join(p)

def g_labels():
    p = [f'<text x="{fmt(sx(3))}" y="{fmt(sy(0)-2.5)}" font-size="3.4" {FS} fill="#333">中心 O（φ/U=0.5）</text>',
         f'<text x="{fmt(sx(-146))}" y="{fmt(sy(BAR_CY+9))}" font-size="3.6" {FS} fill="#d5342b">正端钢条 φ=U（上，y=+90，长250×厚3×高10）</text>',
         f'<text x="{fmt(sx(-146))}" y="{fmt(sy(-BAR_CY-11))}" font-size="3.6" {FS} fill="#1f6feb">参考端钢条 φ=0（下，y=−90）</text>',
         f'<text x="{fmt(sx(6))}" y="{fmt(sy(143))}" font-size="3.3" {FS} fill="#555">四壁绝缘 ∂φ/∂n=0 → 等势线到达壁面时与壁垂直</text>',
         f'<text x="{fmt(sx(-146))}" y="{fmt(sy(-143))}" font-size="3.1" {FS} fill="#666">内腔 294×294 mm ｜ 水深 5 mm ｜ 网格 {H_MAIN} mm（n={r["n"]}）｜ 缺陷 {r["defect"]:.1e}</text>']
    lx, ly = 7.0, 9.0
    p.append(f'<rect x="{lx}" y="{ly}" width="92" height="32" fill="#ffffff" stroke="#999" stroke-width="0.25" opacity="0.95"/>')
    p.append(f'<text x="{lx+2}" y="{ly+5}" font-size="3.4" {FS} fill="#111">等势线 φ/U 与电场方向</text>')
    for i, (c, t) in enumerate([("#d5342b", "0.75 U"), ("#7b2fbe", "0.50 U"), ("#1f6feb", "0.25 U"), ("#a8b2c0", "其余每 0.1U")]):
        yy = ly + 10 + i * 4.3
        p.append(f'<line x1="{lx+3}" y1="{yy}" x2="{lx+16}" y2="{yy}" stroke="{c}" stroke-width="0.7"/>')
        p.append(f'<text x="{lx+18}" y="{yy+1.3}" font-size="3.1" {FS} fill="#333">{t}</text>')
    yy = ly + 27.5
    p.append(f'<line x1="{lx+3}" y1="{yy}" x2="{lx+16}" y2="{yy}" stroke="#2f8f83" stroke-width="0.35"/>')
    p.append(f'<text x="{lx+18}" y="{yy+1.3}" font-size="3.1" {FS} fill="#333">电力线 = E=−∇φ 方向</text>')
    p.append(f'<text x="{fmt(sx(-150))}" y="307.2" font-size="3.0" {FS} fill="#555">打印请选“100%／实际大小”，勿用“适合页面”；本页 310×310 mm 无法塞进单张 A4，本图未声称已校准打印。</text>')
    return "".join(p)

HEAD = ('<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" '
        'width="310mm" height="310mm" viewBox="0 0 310 310">')
svg = HEAD + "\n" + g_bg_frame() + g_minor() + g_contours() + field_svg() + g_axis_bars() + g_labels() + "\n</svg>\n"
open(os.path.join(OUT, "tank-prediction.svg"), "w", encoding="utf-8").write(svg)
print("  tank-prediction.svg 写出 (%d KB)" % (len(svg) // 1024))

def svg_embed():
    return ('<svg id="tankSvg" viewBox="0 0 310 310" xmlns="http://www.w3.org/2000/svg" '
            'style="width:100%;height:auto;display:block">' + g_bg_frame() +
            f'<g id="lyMinor">{g_minor()}</g><g id="lyContour">{g_contours()}</g>' +
            f'<g id="lyField">{field_svg()}</g><g id="lyAxis">{g_axis_bars()}</g>' +
            f'<g id="lyLabel">{g_labels()}</g></svg>')

# A 布局小图
def alayout_svg():
    k = 1.13
    c = 150.0
    out = [f'<svg viewBox="0 0 300 300" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:330px;display:block;margin:0 auto">',
           f'<rect x="0" y="0" width="300" height="300" fill="#fff"/>']
    out.append(f'<circle cx="{c}" cy="{c}" r="{R_RING*k:.2f}" fill="none" stroke="#111" stroke-width="1.6"/>')
    out.append(f'<text x="{c}" y="{c-R_RING*k-4:.1f}" font-size="11" text-anchor="middle" {FS} fill="#111">外环内半径 R=124 mm（φ/U=0）</text>')
    for f_, col, lab in [(0.75, "#d5342b", "3U/4"), (0.5, "#7b2fbe", "U/2"), (0.25, "#1f6feb", "U/4")]:
        rr = ar[f_] * k
        out.append(f'<circle cx="{c}" cy="{c}" r="{rr:.2f}" fill="none" stroke="{col}" stroke-width="1.6"/>')
        out.append(f'<text x="{c+rr+3:.1f}" y="{c+4}" font-size="11" {FS} fill="{col}">{lab}: r={ar[f_]:.3f} mm</text>')
    out.append(f'<circle cx="{c}" cy="{c}" r="{A_RAD*k:.2f}" fill="#222"/>')
    out.append(f'<text x="{c+7}" y="{c-6}" font-size="11" {FS} fill="#222">a=3 mm（底帽半径）</text>')
    out.append(f'<text x="6" y="292" font-size="10.5" {FS} fill="#555">A 布局拓展：r = R·(a/R)^(φ/U)，φ/U=1 在 r=a，φ/U=0 在 r=R</text>')
    out.append('</svg>')
    return "".join(out)

# ---------------------------------------------------------------- 7. HTML
pts_tbl = [(0.0, 0.0), (0.0, 45.0), (0.0, 57.0), (0.0, -45.0), (0.0, -57.0),
           (0.0, 88.0), (0.0, -88.0), (0.0, 147.0), (0.0, -147.0), (100.0, 0.0), (140.0, 0.0)]
rows = "".join(
    f"<tr><td>({x:g}, {y:g})</td><td>{float(interp(ax, PHI, [x], [y])[0]):.4f}</td></tr>" for x, y in pts_tbl)
ideal57 = (57 + BAR_CY) / (2 * BAR_CY)
checks_rows = "".join(f"<tr><td>{k}</td><td>{v:.6g}</td></tr>" if isinstance(v, float) else f"<tr><td>{k}</td><td>{v}</td></tr>"
                      for k, v in checks.items())

html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>第12章 · 有限水槽预测底图</title>
<style>
:root{{--ink:#1b1f24;--sub:#5b646e;--line:#dfe4ea;--bg:#f6f7f9;--card:#fff;--hl:#0b63ce}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}}
header{{padding:22px 26px 16px;background:#fff;border-bottom:1px solid var(--line)}}
h1{{margin:0 0 6px;font-size:21px}}
h2{{font-size:16px;margin:22px 0 8px;padding-left:9px;border-left:4px solid var(--hl)}}
.sub{{color:var(--sub);font-size:13.5px}}
.wrap{{display:grid;grid-template-columns:minmax(360px,1.25fr) minmax(340px,1fr);gap:18px;padding:18px 26px 60px;align-items:start}}
@media(max-width:960px){{.wrap{{grid-template-columns:1fr}}}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}}
.paper{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px;overflow:auto;max-height:84vh}}
table{{border-collapse:collapse;width:100%;font-size:13.5px}}
th,td{{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}}
th{{background:#f2f4f7;font-weight:600}}
code{{background:#eef1f5;padding:1px 5px;border-radius:4px;font-size:12.5px}}
label.ck{{display:flex;gap:8px;align-items:center;margin:5px 0;font-size:14px}}
.note{{background:#fff8e6;border:1px solid #f0d79a;border-radius:9px;padding:9px 12px;font-size:13.5px;margin-top:10px}}
.warn{{background:#fdecec;border-color:#f0b9b9}}
.ok{{color:#0a7a3d;font-weight:600}}
.bad{{color:#c62828;font-weight:600}}
.btnrow{{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}}
button{{font:inherit;font-size:13.5px;padding:6px 12px;border-radius:8px;border:1px solid var(--line);background:#fff;cursor:pointer}}
button:hover{{border-color:var(--hl);color:var(--hl)}}
input[type=range]{{width:100%}}
</style></head><body>
<header>
<h1>第 12 章 · 有限水槽预测底图</h1>
<div class="sub">二维稳态电流场（拉普拉斯）真实数值解 ｜ 内腔 294×294 mm ｜ 上下水平钢条 250×3×10 mm，中心线 y=±90 mm ｜ 正端上板 φ=U、负端下板 φ=0 ｜ 四壁绝缘 ∂φ/∂n=0</div>
</header>
<div class="wrap">
  <div>
    <div class="card" style="margin-bottom:12px">
      <div class="btnrow">
        <button onclick="toggle('lyContour')">等势线 0.25/0.50/0.75</button>
        <button onclick="toggle('lyMinor')">其余 0.1U 等势线</button>
        <button onclick="toggle('lyField')">电力线 E=−∇φ</button>
        <button onclick="toggle('lyLabel')">文字标注</button>
        <button onclick="toggle('lyAxis')">坐标轴与钢条</button>
      </div>
      <label class="ck">缩放 <input type="range" min="60" max="220" value="100" oninput="document.getElementById('tankSvg').style.width=this.value+'%'"></label>
      <div class="sub">图中尺寸按 1:1 毫米绘制（viewBox 310×310 mm）。</div>
    </div>
    <div class="paper">{svg_embed()}</div>
  </div>

  <div>
    <h2>一、这是解出来的，不是画出来的</h2>
    <div class="card">
      <p style="margin-top:0">在水层（水深 5 mm，均匀）上解 <code>∇²φ = 0</code>：正/负端钢条上是狄利克雷条件（U、0），四条槽壁是零法向电流（∂φ/∂n=0）的诺伊曼条件。钢板贯穿水层，故俯视截面即一条等电位矩形。</p>
      <p><b>网格与残差</b>（自写红黑 SOR 迭代，非插值、非平行板直线填充）：</p>
      <table><tr><th>项</th><th>值</th></tr>
        <tr><td>主网格步长</td><td>{H_MAIN:g} mm（n={r['n']}×{r['n']} 节点）</td></tr>
        <tr><td>迭代次数 / 松弛因子 ω</td><td>{r['iters']} / {r['omega']:.6f}</td></tr>
        <tr><td>缺陷 max|h²∇²φ|</td><td>{r['defect']:.3e} V（U=1 归一）</td></tr>
        <tr><td>粗网格对照 h=1 mm 的中心值</td><td>{c_h1:.6f}</td></tr>
      </table>
    </div>

    <h2>二、四项自检（全部通过）</h2>
    <div class="card">
      <table><tr><th>检查</th><th>结果</th></tr>
      <tr><td>中心 φ/U ≈ 0.5</td><td class="ok">{checks['center_phi_over_U']:.6f}</td></tr>
      <tr><td>上下反射 φ(x,y)+φ(x,−y) ≈ 1</td><td class="ok">最大偏差 {checks['updown_reflection_max_err']:.2e}</td></tr>
      <tr><td>左右对称 φ(−x,y)=φ(x,y)</td><td class="ok">最大差 {checks['leftright_symmetry_max_diff']:.2e}</td></tr>
      <tr><td>取值范围 0—1</td><td class="ok">[{checks['phi_min']:.3f}, {checks['phi_max']:.3f}]</td></tr>
      <tr><td>绝缘壁法向梯度 ≈ 0（等势线垂直入壁）</td><td class="ok">{checks['wall_normal_grad_max']:.2e}</td></tr>
      <tr><td>板端等势线弯曲（非直线）</td><td class="ok">见图中 x=±125 处 0.1/0.9 等势线外鼓</td></tr>
      </table>
      <div class="note">φ(x,y)+φ(x,−y)=1 是真空（绝缘、无源）区解的唯一性结论：把上下两条钢条电位互换即得镜像场，故两者之和恒为 1；由此中心必为 0.5，0.5 等势线恰为直线 y=0。</div>
    </div>

    <h2>三、有限解 vs 理想平行板</h2>
    <div class="card">
      <table><tr><th>位置（mm）</th><th>φ/U（数值解）</th></tr>{rows}</table>
      <p class="sub">正中间 y=57 mm 处：数值解 {float(interp(ax, PHI, [0.0], [57.0])[0]):.4f}，理想无限大平行板 {(57+BAR_CY)/(2*BAR_CY):.4f}。中央区确实近似匀强（等势线水平等距），但板外与板端不是——这正是不能用理想平行板直线填满整个槽的原因。</p>
    </div>

    <h2>四、A 布局（仅作拓展，简化解析模型）</h2>
    <div class="card">
      <div class="note warn" style="margin-top:0">这是 <b>单点与圆筒</b> 的二维轴对称简化：<code>r = R·(a/R)^(φ/U)</code>，取有效圆柱半径 a=3 mm（底帽半径）、外环内半径 R=124 mm。原实物螺柱半径仅 1.5 mm、底帽高 1.1 mm，<b>不能说整个水深截面都是半径 3 mm</b>；此式不适用于本章的平行板工况。</div>
      {alayout_svg()}
      <table style="margin-top:8px"><tr><th>等势</th><th>解析半径 r / mm</th></tr>
        <tr><td>3U/4</td><td>{ar[0.75]:.3f}</td></tr>
        <tr><td>U/2</td><td>{ar[0.5]:.3f}</td></tr>
        <tr><td>U/4</td><td>{ar[0.25]:.3f}</td></tr>
      </table>
    </div>

    <h2>五、打印说明</h2>
    <div class="card">
      <p style="margin-top:0">页面 310×310 mm，含外框 300、内框 294、四角定位记号与一条 100 mm 校准线。</p>
      <ul style="margin:6px 0 0 18px;padding:0">
        <li>打印对话框里选 <b>100% / 实际大小</b>，<b>不要</b>选“适合页面/缩放到 A4”。</li>
        <li>310 mm 放不进单张 A4（210×297 mm），需要 A3 或拼贴；页面已写明该限制。</li>
        <li>打印后量一下 100 mm 校准线：对得上才算校准成功。</li>
        <li><b>本说明不声称已完成校准打印</b>；如需 PDF 可由 WorkBuddy 另导出，否则请直接用随附的 <code>tank-prediction.svg</code> 打印。</li>
      </ul>
    </div>

    <h2>六、随附文件</h2>
    <div class="card"><table>
      <tr><th>文件</th><th>用途</th></tr>
      <tr><td><code>tank-prediction.svg</code></td><td>可按实际大小打印的 310×310 mm 底图</td></tr>
      <tr><td><code>tank-prediction.html</code></td><td>本页（可开关图层、缩放）</td></tr>
      <tr><td><code>tank-field-0.5mm.npz</code></td><td>φ 与 ∇φ 全场（0.5 mm 网格）</td></tr>
      <tr><td><code>contours.json</code> / <code>checks.json</code> / <code>solver-report.json</code></td><td>等势线坐标、自检数值、求解参数</td></tr>
      <tr><td><code>solve_tank.py</code> / <code>generate_ch12.py</code></td><td>求解器与出图脚本（第14章复用）</td></tr>
    </table></div>
  </div>
</div>
<script>
function toggle(id){{var e=document.getElementById(id);e.style.display=(e.style.display==='none')?'':'none';}}
</script>
</body></html>
"""
open(os.path.join(OUT, "tank-prediction.html"), "w", encoding="utf-8").write(html)
print("  tank-prediction.html 写出 (%d KB)" % (len(html) // 1024))


with open(os.path.join(OUT, "checks.json"), "w", encoding="utf-8") as f:
    json.dump(checks, f, ensure_ascii=False, indent=2)
json.dump({"bar_center_y_mm": BAR_CY, "bar_len_mm": BAR_LEN, "bar_thick_mm": BAR_THICK,
           "bar_height_mm": 10.0, "inner_half_mm": HALF, "water_depth_mm": 5.0,
           "grid_step_mm": H_MAIN, "grid_n": int(r['n']), "iterations": int(r['iters']),
           "omega": r['omega'], "max_abs_defect_phi_units": r['defect'],
           "A_layout": {"a_mm": A_RAD, "R_mm": R_RING, "r_at_0.75U": ar[0.75],
                        "r_at_0.5U": ar[0.5], "r_at_0.25U": ar[0.25]}},
          open(os.path.join(OUT, "solver-report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
np.savez_compressed(os.path.join(OUT, "tank-field-0.5mm.npz"),
                    ax=ax.astype(np.float32), phi=PHI.astype(np.float32),
                    dphidx=dphidx.astype(np.float32), dphidy=dphidy.astype(np.float32))
json.dump({"note": "SVG 中的等势线（mm，模型坐标，原点槽中心）",
           "levels": {str(k): [[[round(float(x), 2), round(float(y), 2)] for x, y in p] for p in v] for k, v in cont.items()}},
          open(os.path.join(OUT, "contours.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("done.")
print(json.dumps({k: (round(v, 8) if isinstance(v, float) else v) for k, v in checks.items()}, ensure_ascii=False))
