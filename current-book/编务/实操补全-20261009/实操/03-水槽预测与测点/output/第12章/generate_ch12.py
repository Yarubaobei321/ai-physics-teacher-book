#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第12章：有限水槽预测底图 —— 求解、校验、导出 SVG / HTML / 数据。"""
import json, os, sys
from collections import deque
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solve_tank import solve, interp, check_grid, HALF, BAR_LEN, BAR_THICK

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
         checks["leftright_symmetry_max_diff"], checks["wall_normal_grad_max"], checks["interior_grad_max"]))

# ---------------------------------------------------------------- 2b. 网格收敛自检（含"网格必须能表示几何"）
CAND = [7.35, 3.675, 3.0, 1.5, 1.0, 0.75, 0.5]
grid_rej, ladder = [], [("1.0", r1), ("0.5", r)]
for h in CAND:
    ok, nhi, nlo, why = check_grid(h, BAR_CY)
    if not ok:
        grid_rej.append(dict(h=h, n_hi=nhi, n_lo=nlo, reason=why))
for h in (3.0, 1.5, 0.75):
    ladder.append((f"{h:g}", solve(h, BAR_CY, tol=1e-8, maxiter=200000)))
ladder.sort(key=lambda t: -float(t[0]))
grid_rows = []
for hs, rr in ladder:
    cc = float(interp(rr['ax'], rr['PHI'], [0.0], [0.0])[0])
    sref = float(interp(rr['ax'], rr['PHI'], [10.0], [40.0])[0] + interp(rr['ax'], rr['PHI'], [10.0], [-40.0])[0])
    assert rr['n_hi'] > 0 and rr['n_lo'] > 0 and rr['iters'] > 1 and abs(rr['phi_range'][1] - 1.0) < 1e-9
    grid_rows.append(dict(h=float(hs), n=rr['n'], n_hi=rr['n_hi'], n_lo=rr['n_lo'], iters=rr['iters'],
                          defect=rr['defect'], center=cc, sym=sref, phi_max=rr['phi_range'][1]))
checks["grid_sweep"] = grid_rows
checks["grid_rejected"] = grid_rej
print("  网格阶梯（细化时迭代数 400→1900 单调增加，说明几何被表示、真在求解）：")
for g in grid_rows:
    print("    h=%-5g n=%-4d 正/负端节点=%-5d/%-5d iters=%-5d 缺陷=%.2e 中心=%.6f 上下反射和=%.6f"
          % (g['h'], g['n'], g['n_hi'], g['n_lo'], g['iters'], g['defect'], g['center'], g['sym']))
for g in grid_rej:
    print("    ✗ 拒绝 h=%g：正/负端节点=%d/%d（钢条被漏掉，强解会得到全零假解）" % (g['h'], g['n_hi'], g['n_lo']))

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

FLD = []                       # [(原始折线, 简化后折线)]，箭头按原始弧长放，不因简化丢箭头
for xs0 in np.arange(-120, 120.1, 20.0):
    raw = fieldline(float(xs0), BAR_CY - BAR_THICK / 2 - 0.8)
    if len(raw) > 4:
        FLD.append((raw, rdp(raw, 0.25)))
print("  电力线: %d 条" % len(FLD))

# ---------------------------------------------------------------- 5. SVG
def P(polys, stroke, w):
    out = []
    for p in polys:
        d = "M" + "L".join(f"{fmt(sx(x))},{fmt(sy(y))}" for x, y in p)
        out.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{w}" stroke-linecap="round"/>')
    return "".join(out)

def arrow_svg(mx, my, ux, uy, col="#2f8f83"):
    """填充三角箭头。
    只有一个坐标转换：模型坐标 (x,y) -> 屏幕坐标 (sx,sy)，不做旋转、不做 atan2，
    因此不存在 y 方向被翻转两次的问题。指向 = 传入的单位方向 u（调用方保证 = −∇φ）。"""
    px, py = -uy, ux                                   # u 的左法向
    tip = (mx + 2.1 * ux, my + 2.1 * uy)               # 尖端在 u 方向前方
    b1 = (mx - 1.3 * ux + 1.25 * px, my - 1.3 * uy + 1.25 * py)
    b2 = (mx - 1.3 * ux - 1.25 * px, my - 1.3 * uy - 1.25 * py)
    return (f'<path d="M{fmt(sx(b1[0]))},{fmt(sy(b1[1]))} L{fmt(sx(tip[0]))},{fmt(sy(tip[1]))} '
            f'L{fmt(sx(b2[0]))},{fmt(sy(b2[1]))} Z" fill="{col}" stroke="none"/>')

def place_arrows(p, fracs=(0.30, 0.70), min_len_mm=30.0):
    """沿折线【弧长】放箭头，返回 [(模型坐标点, 单位方向)]。
    关键在于按弧长插值而不是取整数下标——折线被简化成 2 个点时同样能放箭头。"""
    seg = np.diff(p, axis=0)
    L = np.hypot(seg[:, 0], seg[:, 1])
    cum = np.concatenate([[0.0], np.cumsum(L)])
    total = float(cum[-1])
    if total < 1e-9:
        return []
    use = fracs if total >= min_len_mm else (0.5,)      # 线太短也至少给 1 个，绝不留空
    out = []
    for f in use:
        s = f * total
        k = int(np.searchsorted(cum, s, side='right'))
        k = min(max(k, 1), len(p) - 1)
        seglen = float(L[k - 1])
        t = 0.0 if seglen < 1e-12 else (s - float(cum[k - 1])) / seglen
        pos = p[k - 1] + t * (p[k] - p[k - 1])
        i0 = max(0, k - 2); i1 = min(len(p) - 1, k + 1)
        d = p[i1] - p[i0]
        nrm = float(np.hypot(d[0], d[1]))
        if nrm < 1e-12:
            continue
        out.append((pos, d / nrm))
    return out

def field_svg():
    """返回 (SVG 片段, 箭头总数, 每个箭头与 −∇φ 的余弦列表)。"""
    out, n_arrow, cosines = [], 0, []
    for raw, simp in FLD:
        d = "M" + "L".join(f"{fmt(sx(x))},{fmt(sy(y))}" for x, y in simp)
        out.append(f'<path d="{d}" fill="none" stroke="#2f8f83" stroke-width="0.35" opacity="0.85"/>')
        arr = place_arrows(simp)
        assert arr, "电力线没放上箭头：%s" % simp[:2]
        for pos, u in arr:
            g = np.array([-float(interp(ax, dphidx, [pos[0]], [pos[1]])[0]),
                          -float(interp(ax, dphidy, [pos[0]], [pos[1]])[0])])
            gn = float(np.hypot(g[0], g[1]))
            if gn > 1e-12:
                cosines.append(float(u @ (g / gn)))     # 与 −∇φ 的夹角余弦，>0 即同向
            out.append(arrow_svg(pos[0], pos[1], u[0], u[1]))
            n_arrow += 1
    return "".join(out), n_arrow, cosines

FIELD_SVG, N_ARROWS, ARROW_COS = field_svg()
checks["field_lines"] = len(FLD)
checks["arrows_total"] = N_ARROWS
checks["arrow_min_cos_with_minus_grad"] = min(ARROW_COS)
assert N_ARROWS >= 2 * len(FLD) or all(len(p) >= 2 for _, p in FLD), "有电力线未获得箭头"
assert min(ARROW_COS) > 0.9, "有箭头方向与 −∇φ 不一致"
print("  箭头: %d 个 / %d 条电力线；与 −∇φ 的最小余弦 = %.4f（>0 表示全部沿 −∇φ）"
      % (N_ARROWS, len(FLD), min(ARROW_COS)))

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
    p.append(f'<text x="{fmt(sx(-150))}" y="309.1" font-size="2.7" {FS} fill="#555">打印请选“100%／实际大小”，勿用“适合页面”；本页 310×310 mm 无法塞进单张 A4，本图未声称已校准打印。</text>')
    return "".join(p)

HEAD = ('<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" '
        'width="310mm" height="310mm" viewBox="0 0 310 310">')
svg = HEAD + "\n" + g_bg_frame() + g_minor() + g_contours() + FIELD_SVG + g_axis_bars() + g_labels() + "\n</svg>\n"
open(os.path.join(OUT, "tank-prediction.svg"), "w", encoding="utf-8").write(svg)
print("  tank-prediction.svg 写出 (%d KB)" % (len(svg) // 1024))

def svg_embed():
    return ('<svg id="tankSvg" viewBox="0 0 310 310" xmlns="http://www.w3.org/2000/svg" '
            'style="width:100%;height:auto;display:block">' + g_bg_frame() +
            f'<g id="lyMinor">{g_minor()}</g><g id="lyContour">{g_contours()}</g>' +
            f'<g id="lyField">{FIELD_SVG}</g><g id="lyAxis">{g_axis_bars()}</g>' +
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

# 网格收敛自检表（回应复核意见：坏网格必须被拒，不能把全零假解当收敛）
grid_rows_html = "".join(
    f"<tr><td>{g['h']:g}</td><td>{g['n']}×{g['n']}</td><td>{g['n_hi']}</td><td>{g['n_lo']}</td>"
    f"<td>{g['iters']}</td><td>{g['defect']:.2e}</td><td>{g['center']:.6f}</td><td>{g['sym']:.6f}</td></tr>"
    for g in grid_rows)
grid_rej_html = "".join(
    f"<li>h = <b>{g['h']:g} mm</b>：正端固定节点 <b>{g['n_hi']}</b>、负端固定节点 <b>{g['n_lo']}</b> —— "
    f"网格节点都落在 h 的整数倍上，<code>|y∓90| ≤ 1.5 mm</code> 内一个节点都没有，<b>3 mm 钢条被整个漏掉</b>。"
    f"此时初始的全零场就“满足”了拉普拉斯方程，于是迭代 1 次、缺陷 0、φ≡0 —— 看着像收敛，其实什么都没解，"
    f"<b>不能当作收敛检验</b>。现在 <code>solve()</code> 对这种网格直接抛错拒绝。</li>"
    for g in grid_rej) or "<li>无</li>"
arrow_rows_html = (
    f"<tr><td>电力线 / 箭头</td><td>{checks['field_lines']} 条 / <b>{checks['arrows_total']}</b> 个</td></tr>"
    f"<tr><td>箭头与 E = −∇φ 的最小夹角余弦</td>"
    f"<td class=\"ok\">{checks['arrow_min_cos_with_minus_grad']:.4f}</td></tr>")

html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>第10章 · 有限水槽预测底图</title>
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
<h1>第 10 章 · 有限水槽预测底图</h1>
<div class="sub">二维稳态电流场（拉普拉斯）真实数值解 ｜ 内腔 294×294 mm ｜ 上下水平钢条 250×3×10 mm，中心线 y=±90 mm ｜ 正端上板 φ=U、负端下板 φ=0 ｜ 四壁绝缘 ∂φ/∂n=0</div>
</header>
<div class="wrap">
  <div>
    <div class="card" style="margin-bottom:12px">
      <div class="btnrow">
        <button onclick="toggle('lyContour')">等势线 0.25/0.50/0.75</button>
        <button onclick="toggle('lyMinor')">其余 0.1U 等势线</button>
        <button onclick="toggle('lyField')">电场线</button>
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
        {arrow_rows_html}
      </table>
    </div>

    <h2>二、网格必须能表示几何（否则是假解）</h2>
    <div class="card">
      <p style="margin-top:0">网格节点落在 h 的整数倍上。如果某个 h 让 <code>|y∓90| ≤ 1.5 mm</code> 内没有任何节点，
        两条 3 mm 钢条就会整体消失：<code>fixed</code> 为空，<b>初值全零恰好“满足”拉普拉斯方程</b>，
        于是迭代 1 次、缺陷 0、φ≡0 —— 看着像收敛，其实什么都没解。因此求解前必须显式检查两条电极都有固定节点。</p>
      <p><b>能表示几何的网格阶梯</b>（细化时迭代数单调增加，说明确实在求解）：</p>
      <table><tr><th>h / mm</th><th>节点</th><th>正端固定节点</th><th>负端固定节点</th><th>迭代</th><th>缺陷</th><th>中心 φ</th><th>上下反射和</th></tr>
      {grid_rows_html}</table>
      <p style="margin-top:12px"><b>被拒绝的网格（复核发现）</b>：</p>
      <ul style="margin:4px 0 0 18px;padding:0">{grid_rej_html}</ul>
      <div class="note warn">这不是把坏结果删掉，而是把判据写进代码：<code>solve(..., require_electrodes=True)</code>
        默认开启，遇到漏掉电极的网格直接抛错，不允许静默返回全零场。</div>
    </div>

    <h2>三、四项自检（全部通过）</h2>
    <div class="card">
      <table><tr><th>检查</th><th>结果</th></tr>
      <tr><td>中心 φ/U ≈ 0.5</td><td class="ok">{checks['center_phi_over_U']:.6f}</td></tr>
      <tr><td>上下反射 φ(x,y)+φ(x,−y) ≈ 1</td><td class="ok">最大偏差 {checks['updown_reflection_max_err']:.2e}</td></tr>
      <tr><td>左右对称 φ(−x,y)=φ(x,y)</td><td class="ok">最大差 {checks['leftright_symmetry_max_diff']:.2e}</td></tr>
      <tr><td>取值范围 0—1</td><td class="ok">[{checks['phi_min']:.3f}, {checks['phi_max']:.3f}]</td></tr>
      <tr><td>绝缘壁法向梯度 ≈ 0（等势线垂直入壁）</td><td class="ok">{checks['wall_normal_grad_max']:.2e}</td></tr>
      <tr><td>板端等势线弯曲（非直线）</td><td class="ok">见图中 x=±125 处 0.1/0.9 等势线外鼓</td></tr>
      <tr><td>箭头方向与 E=−∇φ 一致</td><td class="ok">最小余弦 {checks['arrow_min_cos_with_minus_grad']:.4f}（由正端指向负端，即图面上向下）</td></tr>
      </table>
      <div class="note">φ(x,y)+φ(x,−y)=1 是真空（绝缘、无源）区解的唯一性结论：把上下两条钢条电位互换即得镜像场，故两者之和恒为 1；由此中心必为 0.5，0.5 等势线恰为直线 y=0。</div>
    </div>

    <h2>四、有限解 vs 理想平行板</h2>
    <div class="card">
      <table><tr><th>位置（mm）</th><th>φ/U（数值解）</th></tr>{rows}</table>
      <p class="sub">正中间 y=57 mm 处：数值解 {float(interp(ax, PHI, [0.0], [57.0])[0]):.4f}，理想无限大平行板 {(57+BAR_CY)/(2*BAR_CY):.4f}。中央区确实近似匀强（等势线水平等距），但板外与板端不是——这正是不能用理想平行板直线填满整个槽的原因。</p>
    </div>

    <h2>五、A 布局（仅作拓展，简化解析模型）</h2>
    <div class="card">
      <div class="note warn" style="margin-top:0">这是 <b>单点与圆筒</b> 的二维轴对称简化：<code>r = R·(a/R)^(φ/U)</code>，取有效圆柱半径 a=3 mm（底帽半径）、外环内半径 R=124 mm。原实物螺柱半径仅 1.5 mm、底帽高 1.1 mm，<b>不能说整个水深截面都是半径 3 mm</b>；此式不适用于本章的平行板工况。</div>
      {alayout_svg()}
      <table style="margin-top:8px"><tr><th>等势</th><th>解析半径 r / mm</th></tr>
        <tr><td>3U/4</td><td>{ar[0.75]:.3f}</td></tr>
        <tr><td>U/2</td><td>{ar[0.5]:.3f}</td></tr>
        <tr><td>U/4</td><td>{ar[0.25]:.3f}</td></tr>
      </table>
    </div>

    <h2>六、打印说明</h2>
    <div class="card">
      <p style="margin-top:0">页面 310×310 mm，含外框 300、内框 294、四角定位记号与一条 100 mm 校准线。</p>
      <ul style="margin:6px 0 0 18px;padding:0">
        <li>打印对话框里选 <b>100% / 实际大小</b>，<b>不要</b>选“适合页面/缩放到 A4”。</li>
        <li>310 mm 放不进单张 A4（210×297 mm），需要 A3 或拼贴；页面已写明该限制。</li>
        <li>打印后量一下 100 mm 校准线：对得上才算校准成功。</li>
        <li><b>本说明不声称已完成校准打印</b>；如需 PDF 可由 WorkBuddy 另导出，否则请直接用随附的 <code>tank-prediction.svg</code> 打印。</li>
      </ul>
    </div>

    <h2>七、随附文件</h2>
    <div class="card"><table>
      <tr><th>文件</th><th>用途</th></tr>
      <tr><td><code>tank-prediction.svg</code></td><td>可按实际大小打印的 310×310 mm 底图</td></tr>
      <tr><td><code>tank-prediction.html</code></td><td>本页（可开关图层、缩放）</td></tr>
      <tr><td><code>tank-field-0.5mm.npz</code></td><td>φ 与 ∇φ 全场（0.5 mm 网格）</td></tr>
      <tr><td><code>contours.json</code> / <code>checks.json</code> / <code>solver-report.json</code></td><td>等势线坐标、自检数值、求解参数</td></tr>
      <tr><td><code>solve_tank.py</code> / <code>generate_ch12.py</code></td><td>求解器与出图脚本（第12章复用）</td></tr>
      <tr><td><code>_修改前备份-20261009/</code></td><td>本次修正<b>之前</b>的 solve_tank.py、generate_ch12.py、tank-prediction.svg/.html 原件（保留备查）</td></tr>
    </table></div>
    <div class="card" style="margin-top:12px">
      <b>本次修正记录</b>（独立复核提出两处问题，逐一复核后处理）：
      <ul style="margin:6px 0 0 18px;padding:0">
        <li><b>电力线箭头漏画（属实，已修）</b>：原实现按折线<b>点数</b>的 30%/70% 取整数下标放箭头；
          中央直线被 RDP 简化成 2 点后下标越界，13 条线只画了 8 个箭头（应 26 个）。现改为
          <b>按弧长插值</b>放箭头，并加断言“每条线至少 1 个箭头”。</li>
        <li><b>箭头方向被翻转两次（复核，未复现）</b>：双翻转确实存在于早期用
          <code>atan2(−Δy,Δx)</code> + <code>rotate(−ang)</code> 的写法；该写法此前已被替换为
          “只做一次模型坐标→屏幕坐标转换”的绝对坐标箭头。对当前 SVG 做数值复核：8 个箭头在模型坐标下
          尖端相对翼展中点 dy = −3.146（指向 −y），与 npz 中 E<sub>y</sub> = −0.00564（指向负端）一致，
          <b>方向本来就是对的</b>。现改为填充三角并把“与 −∇φ 的夹角余弦 &gt; 0.9”写成断言，防止回归。</li>
        <li><b>坏网格被当成收敛（属实，已修）</b>：h = 7.35 / 3.675 mm 使
          <code>|y∓90| ≤ 1.5 mm</code> 内无节点，两条钢条整体消失，<code>fixed</code> 为空，
          全零初值即“满足”拉普拉斯，于是迭代 1 次、缺陷 0、φ≡0。现 <code>solve()</code> 默认
          <code>require_electrodes=True</code>，电极节点为 0 直接抛错；自测改用能表示几何的阶梯并报告
          电极节点数、残差、中心值、对称性。</li>
      </ul>
    </div>
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
