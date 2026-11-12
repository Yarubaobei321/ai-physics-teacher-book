#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第14章：同一有限模型叠加实测 15 点。复用第12章 solve_tank 求解函数与显示约定。
输出：tank-measured-compare.html、有限模型网格 CSV、每点预测与残差 CSV、拟合汇总 JSON。"""
import csv, json, os, sys
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "第12章")))
from solve_tank import solve, interp, contours, HALF, BAR_LEN, BAR_THICK

HERE = os.path.dirname(os.path.abspath(__file__))
CSVP = os.path.abspath(os.path.join(HERE, "..", "..", "input", "第14章-平行板15点.csv"))
rows = list(csv.DictReader(open(CSVP, encoding='utf-8-sig')))
P = [(float(r['x_mm']), float(r['y_mm']), float(r['potential_V']), r['color'], int(r['id'])) for r in rows]
CN = {'yellow': '黄', 'red': '红', 'blue': '蓝'}
HEX = {'yellow': '#e8b400', 'red': '#e23b2e', 'blue': '#1f6feb'}
V_TERM = 9.3
V_OLD, RMS_OLD = 7.884235450652902, 0.02041598659114245

# ------------------------------------------------ 1. 两套几何各自重新求解
GEOS = {"180": 90.0, "184": 92.0}
SOL = {}
for name, cy in GEOS.items():
    r = solve(0.5, cy, tol=1e-8, maxiter=400000)
    r['u_pts'] = interp(r['ax'], r['PHI'], [q[0] for q in P], [q[1] for q in P])
    r['dphidy'] = np.gradient(r['PHI'], 0.5, axis=0)
    SOL[name] = r
    print(f"  几何 {name} mm（钢条 y=±{cy:g}）: n={r['n']} iters={r['iters']} 缺陷={r['defect']:.2e} "
          f"中心phi={float(interp(r['ax'], r['PHI'], [0.0], [0.0])[0]):.6f}")

# ------------------------------------------------ 2. 两种拟合
def fitA(u, V):
    return 0.0, float((u * V).sum() / (u * u).sum())
def fitB(u, V):
    A = np.c_[np.ones_like(u), u]
    a, c = np.linalg.lstsq(A, V, rcond=None)[0]
    return float(a), float(a + c)

CHECK_IDS = {1, 6, 11}
i_fit = [i for i, q in enumerate(P) if q[4] not in CHECK_IDS]
i_chk = [i for i, q in enumerate(P) if q[4] in CHECK_IDS]
VALL = np.array([q[2] for q in P])
fit = {}
for name in GEOS:
    u = SOL[name]['u_pts']; e = {}
    for tag, fn in (("A", fitA), ("B", fitB)):
        a, b = fn(u[i_fit], VALL[i_fit])
        pr = a + (b - a) * u
        e[tag] = dict(a=a, b=b, pred=pr.tolist(),
                      rms_fit=float(np.sqrt(((pr[i_fit] - VALL[i_fit]) ** 2).mean())),
                      rms_chk=float(np.sqrt(((pr[i_chk] - VALL[i_chk]) ** 2).mean())),
                      max_chk=float(np.abs(pr[i_chk] - VALL[i_chk]).max()),
                      res_fit=(pr[i_fit] - VALL[i_fit]).tolist(),
                      res_chk=(pr[i_chk] - VALL[i_chk]).tolist())
        a2, b2 = fn(u, VALL)
        e[tag + "_all"] = dict(a=a2, b=b2, rms=float(np.sqrt(((a2 + (b2 - a2) * u - VALL) ** 2).mean())))
    fit[name] = e
    dy_mm = interp(SOL[name]['ax'], SOL[name]['dphidy'], [q[0] for q in P], [q[1] for q in P])
    fit[name]['Ey'] = (-e["A"]["b"] * dy_mm * 1000.0).tolist()

BA184, BB184, AB184 = fit["184"]["A"]["b"], fit["184"]["B"]["b"], fit["184"]["B"]["a"]
BA180 = fit["180"]["A"]["b"]
loss = V_TERM - BA184
plate_eff = BA184 - BA180
print("\n[真实拟合数值]")
for name in ("184", "180"):
    e = fit[name]
    print(f"  {name} mm ①固定负端0: b={e['A']['b']:.4f} V | 拟合RMS={e['A']['rms_fit']*1000:.1f} mV "
          f"检查点RMS={e['A']['rms_chk']*1000:.1f} mV 最大|残差|={e['A']['max_chk']*1000:.1f} mV")
    print(f"  {name} mm ②自由a,b : a={e['B']['a']:+.4f} V b={e['B']['b']:.4f} V | 拟合RMS={e['B']['rms_fit']*1000:.1f} mV "
          f"检查点RMS={e['B']['rms_chk']*1000:.1f} mV")
    print(f"  {name} mm 全15点    : ①b={e['A_all']['b']:.4f} V RMS={e['A_all']['rms']*1000:.1f} mV ; "
          f"②a={e['B_all']['a']:+.4f} b={e['B_all']['b']:.4f} RMS={e['B_all']['rms']*1000:.1f} mV")
print(f"  板位 180→184 对 b 的影响: {plate_eff:+.4f} V ({abs(plate_eff)/BA180*100:.2f}%)")
print(f"  记录端电压 9.3 V 与拟合 b 的缺口: {loss:.3f} V ({loss/V_TERM*100:.1f}%)，量级比 {loss/abs(plate_eff):.0f} 倍")

# ------------------------------------------------ 3. 网格数据 CSV（1 mm）
for name, cy in GEOS.items():
    r = SOL[name]; ax = r['ax']; P0 = r['PHI']; bb = fit[name]["A"]["b"]
    xs = ax[::2]; sub = P0[::2, ::2]
    with open(os.path.join(HERE, f"tank-model-grid-{name}_1mm.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"# 有限水槽求解结果：钢条中心线 y=+/-{cy:g} mm（中心距 {name} mm），网格 1.0 mm，四壁绝缘"])
        w.writerow(["x_mm", "y_mm", "u_norm", f"phi_V(正端={bb:.4f},负端0)"])
        for iy, y in enumerate(xs):
            for ix, x in enumerate(xs):
                w.writerow([f"{x:.1f}", f"{y:.1f}", f"{sub[iy,ix]:.6f}", f"{sub[iy,ix]*bb:.6f}"])
    print(f"  tank-model-grid-{name}_1mm.csv  ({len(xs)}×{len(xs)} 点)")

# ------------------------------------------------ 4. 每点预测与残差 CSV
with open(os.path.join(HERE, "points-predictions-residuals.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow([f"# 第14章 每点预测值与残差（残差=预测-实测）。正端①固定负端0拟合 b(184)={BA184:.4f}V, b(180)={BA180:.4f}V"])
    w.writerow(["id", "color", "role", "x_mm", "y_mm", "V_measured", "u_180", "u_184",
                "ideal_parallel", "predA_184", "resA_184", "predB_184", "resB_184",
                "predA_180", "resA_180", "predB_180", "resB_180", "Ey_V_per_m_184"])
    for i, q in enumerate(P):
        w.writerow([q[4], CN[q[3]], "检查点" if i in i_chk else "拟合点", q[0], q[1], q[2],
                    f"{SOL['180']['u_pts'][i]:.6f}", f"{SOL['184']['u_pts'][i]:.6f}", f"{(q[1]+90)/180:.6f}",
                    f"{fit['184']['A']['pred'][i]:.4f}", f"{fit['184']['A']['pred'][i]-q[2]:+.4f}",
                    f"{fit['184']['B']['pred'][i]:.4f}", f"{fit['184']['B']['pred'][i]-q[2]:+.4f}",
                    f"{fit['180']['A']['pred'][i]:.4f}", f"{fit['180']['A']['pred'][i]-q[2]:+.4f}",
                    f"{fit['180']['B']['pred'][i]:.4f}", f"{fit['180']['B']['pred'][i]-q[2]:+.4f}",
                    f"{fit['184']['Ey'][i]:.2f}"])
print("  points-predictions-residuals.csv")

json.dump(dict(terminal_recorded_V=V_TERM, grid_mm=0.5, bar_center_y=GEOS,
               u_points={g: SOL[g]['u_pts'].tolist() for g in GEOS},
               fits={g: {k: {kk: vv for kk, vv in v.items() if kk not in ("pred", "res_fit", "res_chk")}
                         for k, v in fit[g].items() if k != "Ey"} for g in fit},
               Ey_V_per_m={g: fit[g]['Ey'] for g in fit},
               old_software=dict(b=V_OLD, rms=RMS_OLD, note="含颜色偏移与曲面重建，不作新拟合标准"),
               derived=dict(b_184=BA184, a_184=AB184, b_free_184=BB184, b_180=BA180,
                            plate_effect_V=plate_eff, loss_V=loss, loss_pct=loss/V_TERM*100)),
          open(os.path.join(HERE, "fit-summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ------------------------------------------------ 5. 地形网格（3D）
K = 61
axq = np.linspace(-HALF, HALF, K)
Zq = np.vstack([interp(SOL["184"]['ax'], SOL["184"]['PHI'], [axq[i]] * K, axq) for i in range(K)]) * BA184
terrain = dict(n=K, lo=float(-HALF), hi=float(HALF), zmax=float(Zq.max()),
               phi=[[round(float(v), 3) for v in row] for row in Zq])

# ------------------------------------------------ 6. SVG 片段
def cpath(polys, col, w):
    o = []
    for p in polys:
        d = "M" + "L".join(f"{27+x+147:.2f},{27+147-y:.2f}" for x, y in p)
        o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}"/>')
    return "".join(o)
contour_svg = "".join(cpath(contours(SOL['184']['PHI'], SOL['184']['ax'], u),
                            f"hsl({215-205*u:.0f},72%,48%)", 0.6 if abs(u-0.5) < 1e-9 else 0.42)
                     for u in [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9])

def prof_svg():
    W_, Hh, x0, x1, y0, y1 = 700.0, 330.0, 46.0, 660.0, 292.0, 22.0
    ymax = 8.0
    T = lambda ym, v: (x0 + (ym + HALF) / (2 * HALF) * (x1 - x0), y0 + v / ymax * (y1 - y0))
    o = [f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="#cfd6de"/>',
         f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="#cfd6de"/>']
    for v in range(0, 9):
        py = T(0, v)[1]
        o.append(f'<line x1="{x0}" y1="{py:.1f}" x2="{x1}" y2="{py:.1f}" stroke="#eef1f5"/>')
        o.append(f'<text x="{x0-6}" y="{py+4:.1f}" font-size="12" text-anchor="end" fill="#5b646e">{v}</text>')
    for ym in range(-140, 141, 20):
        px = T(ym, 0)[0]
        o.append(f'<line x1="{px:.1f}" y1="{y0}" x2="{px:.1f}" y2="{y0+4}" stroke="#cfd6de"/>')
        o.append(f'<text x="{px:.1f}" y="{y0+18}" font-size="11" text-anchor="middle" fill="#5b646e">{ym}</text>')
    o.append(f'<text x="{(x0+x1)/2}" y="{y0+36}" font-size="12" text-anchor="middle" fill="#5b646e">y / mm（过中心 x=0 的剖面）</text>')
    o.append(f'<text x="14" y="{(y0+y1)/2}" font-size="12" fill="#5b646e" transform="rotate(-90 14 {(y0+y1)/2})">电势 / V</text>')
    yl = np.linspace(-HALF, HALF, 295)
    for name, dash, col in (("180", 'stroke-dasharray="7,5"', "#8a94a3"), ("184", "", "#0b63ce")):
        v = interp(SOL[name]['ax'], SOL[name]['PHI'], [0.0] * 295, yl) * fit[name]["A"]["b"]
        d = "M" + "L".join(f"{T(a,b)[0]:.1f},{T(a,b)[1]:.1f}" for a, b in zip(yl, v))
        o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.4" {dash}/>')
    for yy in (92, -92, 90, -90):
        px = T(yy, 0)[0]
        o.append(f'<line x1="{px:.1f}" y1="{y1}" x2="{px:.1f}" y2="{y0}" stroke="#b0b8c2" '
                 f'stroke-width="1" stroke-dasharray="3,3" opacity="0.75"/>')
    for q in P:
        px, py = T(q[1], q[2])
        o.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5.5" fill="{HEX[q[3]]}" stroke="#fff" stroke-width="1.5"/>')
        o.append(f'<text x="{px+8:.1f}" y="{py-7:.1f}" font-size="11" fill="#333">{q[4]}</text>')
    return "".join(o)
profile_svg = prof_svg()

def pts2d():
    o = []
    for q in P:
        px, py = 27 + q[0] + 147, 27 + 147 - q[1]
        o.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.8" fill="{HEX[q[3]]}" stroke="#fff" stroke-width="1.5"/>')
        o.append(f'<text x="{px+7:.1f}" y="{py-6:.1f}" font-size="11" fill="#333">{q[4]}</text>')
    return "".join(o)

def ptsjson():
    return json.dumps([dict(id=q[4], color=q[3], x=q[0], y=q[1], V=q[2],
                            u=round(float(SOL['184']['u_pts'][i]), 5),
                            predA=round(float(fit['184']['A']['pred'][i]), 4),
                            predB=round(float(fit['184']['B']['pred'][i]), 4),
                            role="check" if i in i_chk else "fit",
                            Ey=round(float(fit['184']['Ey'][i]), 2)) for i, q in enumerate(P)], ensure_ascii=False)

def fit_table():
    o = []
    for name in ("184", "180"):
        e = fit[name]
        o.append(f"<tr><th colspan=3>中心距 {name} mm（钢条 y=±{GEOS[name]:g}）</th></tr>")
        for tag, lab in (("A", "① 固定负端 0，只拟合正端 b"), ("B", "② 允许 a、b 同时拟合 φ=a+(b−a)u")):
            d = e[tag]
            o.append(f"<tr><td>{lab}</td><td>a = {d['a']:+.4f} V<br>b = {d['b']:.4f} V</td>"
                     f"<td>拟合点 RMS {d['rms_fit']*1000:.1f} mV<br>检查点 RMS {d['rms_chk']*1000:.1f} mV<br>"
                     f"检查点最大 |残差| {d['max_chk']*1000:.1f} mV</td></tr>")
        d = e["A_all"]
        o.append(f"<tr><td>原记录：15 点全部参与拟合</td><td>b = {d['b']:.4f} V</td>"
                 f"<td>15 点 RMS {d['rms']*1000:.1f} mV</td></tr>")
    return "".join(o)

def pred_table():
    o = []
    for i, q in enumerate(P):
        chk = i in i_chk
        o.append(f"<tr class=\"{'chk' if chk else ''}\"><td>{q[4]}</td>"
                 f"<td><span class='dot' style='background:{HEX[q[3]]}'></span>{CN[q[3]]}</td>"
                 f"<td>{'检查点' if chk else '拟合点'}</td><td>{q[0]:.1f}</td><td>{q[1]:.1f}</td><td><b>{q[2]:.0f}</b></td>"
                 f"<td>{SOL['184']['u_pts'][i]:.4f}</td>"
                 f"<td>{fit['184']['A']['pred'][i]:.3f}</td><td>{(fit['184']['A']['pred'][i]-q[2])*1000:+.1f}</td>"
                 f"<td>{fit['184']['B']['pred'][i]:.3f}</td><td>{(fit['184']['B']['pred'][i]-q[2])*1000:+.1f}</td>"
                 f"<td>{fit['184']['Ey'][i]:.1f}</td></tr>")
    return "".join(o)

def warn_html():
    o = []
    if AB184 < 0:
        o.append(f"<li><b>参数越界提示（轻度触发）：</b>两参数拟合（②）的负端截距 "
                 f"a = {AB184:+.4f} V &lt; 0。量级只有 {abs(AB184)*1000:.1f} mV，落在 2/4/6 V 取值与照片定位的分辩之内，"
                 f"但按判据仍应标注「参数越界／模型或记录待查」，<b>不能</b>把它当成新的实测电势。</li>")
    if BB184 > V_TERM:
        o.append(f"<li><b>参数越界提示：</b>正端拟合 b = {BB184:.4f} V &gt; 记录端电压 {V_TERM} V。</li>")
    if not o:
        o.append(f"<li>两参数拟合未越界：a = {AB184:+.4f} V ≈ 0，b = {BB184:.4f} V &lt; {V_TERM} V。</li>")
    return "".join(o)

# ------------------------------------------------ 7. HTML
TPL = open(os.path.join(HERE, "_template.html"), encoding="utf-8").read()
rep = {
    "@@BA184@@": f"{BA184:.4f}", "@@BA180@@": f"{BA180:.4f}",
    "@@LOSS@@": f"{loss:.2f}", "@@LOSSPCT@@": f"{loss/V_TERM*100:.1f}",
    "@@PLATE@@": f"{plate_eff:+.3f}", "@@PLATEPCT@@": f"{abs(plate_eff)/BA180*100:.2f}",
    "@@VOLD@@": f"{V_OLD:.4f}", "@@RMSOLD@@": f"{RMS_OLD:.5f}",
    "@@RATIO@@": f"{loss/max(abs(plate_eff),1e-9):.0f}",
    "@@CONTOURS@@": contour_svg, "@@PROFILE@@": profile_svg, "@@PTS2D@@": pts2d(),
    "@@FITTABLE@@": fit_table(), "@@PREDTABLE@@": pred_table(), "@@WARN@@": warn_html(),
    "@@TERRAIN@@": json.dumps(terrain, ensure_ascii=False), "@@PTSJSON@@": ptsjson(),
    "@@IT184@@": str(SOL['184']['iters']), "@@DEF184@@": f"{SOL['184']['defect']:.1e}",
    "@@R180A@@": f"{fit['180']['A']['rms_fit']*1000:.1f}", "@@R184A@@": f"{fit['184']['A']['rms_fit']*1000:.1f}",
    "@@C180A@@": f"{fit['180']['A']['rms_chk']*1000:.1f}", "@@C184A@@": f"{fit['184']['A']['rms_chk']*1000:.1f}",
    "@@EY180@@": f"{float(np.median(fit['180']['Ey'])):.2f}",
    "@@EY184@@": f"{float(np.median(fit['184']['Ey'])):.2f}",
    "@@BAR1Y@@": f"{27+147-93.5:.1f}", "@@BAR2Y@@": f"{27+147+90.5:.1f}",
    "@@CLOSECHK@@": f"{abs(AB184)*1000:.1f}",
}
html = TPL
for k in sorted(rep, key=len, reverse=True):
    html = html.replace(k, rep[k])
missing = sorted(set(__import__('re').findall(r'@@[A-Za-z0-9_]+@@', html)))
assert not missing, missing
open(os.path.join(HERE, "tank-measured-compare.html"), "w", encoding="utf-8").write(html)
print("  tank-measured-compare.html 写出 (%d KB)" % (len(html)//1024))
print("\n完成。")
