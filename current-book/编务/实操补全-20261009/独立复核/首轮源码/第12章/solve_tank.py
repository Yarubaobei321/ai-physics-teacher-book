#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
有限水槽二维拉普拉斯求解器（自写红黑 SOR，仅用 numpy）。
物理：水深 5 mm 的薄导电水层 -> 俯视二维稳态电流场，满足 ∇²φ = 0。
  · 内腔正方形 294x294 mm，原点在槽中心，x,y ∈ [-147, 147]
  · 上下两条水平钢条：长 250 mm（x ∈ [-125,125]）、俯视厚 3 mm、高 10 mm（>水深，贯穿水层）
    设计中心线 y = ±bar_cy（第12章 bar_cy=90；第14章照片估计 bar_cy=92 -> 中心距184）
  · 正端上板 φ=U、负端下板 φ=0
  · 四壁绝缘：∂φ/∂n = 0（镜像鬼点实现）
单位：长度 mm，电势 V（求解时用 U=1 归一，线性叠加）。
"""
import numpy as np

HALF = 147.0          # 内腔半宽 mm
BAR_LEN = 250.0       # 钢条长 mm
BAR_THICK = 3.0       # 钢条俯视厚 mm

def build_mask(h, bar_cy, V_hi=1.0, V_lo=0.0):
    """返回 (X, Y, phi0, fixed, free)。网格节点 x,y ∈ [-HALF, HALF]。
    网格以槽中心为锚点，保证 x=0 与 y=0 落在节点上（利于对称性校验）。"""
    m = int(round(HALF / h))
    n = 2 * m + 1
    ax = h * (np.arange(n) - m)                    # 保证 0 与 ±m*h(≈±147) 落在节点上
    X, Y = np.meshgrid(ax, ax)                     # 行 i -> y, 列 j -> x
    fixed = np.zeros((n, n), bool)
    phi0 = np.zeros((n, n))
    inx = np.abs(X) <= BAR_LEN / 2 + 1e-9
    up = inx & (np.abs(Y - bar_cy) <= BAR_THICK / 2 + 1e-9)
    dn = inx & (np.abs(Y + bar_cy) <= BAR_THICK / 2 + 1e-9)
    phi0[up] = V_hi; fixed |= up
    phi0[dn] = V_lo; fixed |= dn
    free = ~fixed
    return ax, X, Y, phi0, fixed, free

def solve(h, bar_cy, V_hi=1.0, V_lo=0.0, tol=1e-7, maxiter=400000, omega=None, report=None):
    ax, X, Y, phi0, fixed, free = build_mask(h, bar_cy, V_hi, V_lo)
    n = ax.size
    # 带鬼点的数组，鬼点用于实现绝缘壁零法向电流
    phi = np.zeros((n + 2, n + 2))
    phi[1:-1, 1:-1] = phi0
    freeP = np.zeros((n + 2, n + 2), bool); freeP[1:-1, 1:-1] = free
    I, J = np.meshgrid(np.arange(n), np.arange(n), indexing='ij')
    color = (I + J) % 2
    selE = np.zeros((n + 2, n + 2), bool); selE[1:-1, 1:-1] = (color == 0) & free
    selO = np.zeros((n + 2, n + 2), bool); selO[1:-1, 1:-1] = (color == 1) & free
    if omega is None:
        omega = 2.0 / (1.0 + np.sin(np.pi / n))     # 最优松弛因子
    it = 0
    res = np.inf
    while it < maxiter:
        it += 1
        for sel in (selO, selE):                    # 先奇后偶
            up = phi[0:-2, 1:-1]; dn = phi[2:, 1:-1]
            lf = phi[1:-1, 0:-2]; rt = phi[1:-1, 2:]
            avg = 0.25 * (up + dn + lf + rt)
            cur = phi[1:-1, 1:-1]
            nv = cur + omega * (avg - cur)
            cur[sel[1:-1, 1:-1]] = nv[sel[1:-1, 1:-1]]
        # 绝缘壁：鬼点 = 相邻内点
        phi[0, :] = phi[1, :]; phi[-1, :] = phi[-2, :]
        phi[:, 0] = phi[:, 1]; phi[:, -1] = phi[:, -2]
        if it % 50 == 0 or it == 1:
            c = phi[1:-1, 1:-1]
            up = phi[0:-2, 1:-1]; dn = phi[2:, 1:-1]
            lf = phi[1:-1, 0:-2]; rt = phi[1:-1, 2:]
            defect = np.zeros_like(c)
            defect[free] = (up + dn + lf + rt - 4 * c)[free]
            res = float(np.abs(defect).max())       # 未除以 h² 的“缺陷”，量纲为 phi
            if report and it % 2000 == 0:
                report(it, res)
            if res < tol:
                break
    PHI = phi[1:-1, 1:-1].copy()
    # 归一化残差（等效于把缺陷除以 h² 后与 U 比较的粗糙量度）
    return dict(ax=ax, X=X, Y=Y, PHI=PHI, fixed=fixed, free=free,
                h=h, n=n, bar_cy=bar_cy, iters=it, defect=res,
                omega=omega, U=V_hi - V_lo)

def interp(ax, PHI, xs, ys):
    """对求解结果做双线性插值。"""
    a0 = ax[0]; h = ax[1] - ax[0]; n = ax.size
    out = []
    for x, y in zip(xs, ys):
        fx = (x - a0) / h; fy = (y - a0) / h
        j = min(max(int(np.floor(fx)), 0), n - 2); i = min(max(int(np.floor(fy)), 0), n - 2)
        tx = fx - j; ty = fy - i
        v = ((1 - ty) * ((1 - tx) * PHI[i, j] + tx * PHI[i, j + 1]) +
             ty * ((1 - tx) * PHI[i + 1, j] + tx * PHI[i + 1, j + 1]))
        out.append(float(v))
    return np.array(out)

if __name__ == '__main__':
    # 小规模验证：网格从粗到细，检查中心值与收敛
    print(f"{'h/mm':>6} {'n':>5} {'iters':>8} {'|h^2 lap phi|':>14} {'phi(0,0)':>10} {'phi(x,y)+phi(x,-y)':>18} {'左右差':>10}")
    for h in (3.0, 1.5, 1.0, 0.75, 0.5):
        r = solve(h, 90.0, tol=1e-8, maxiter=200000)
        ax = r['ax']; P = r['PHI']
        c = interp(ax, P, [0.0], [0.0])[0]
        symy = interp(ax, P, [10.0], [40.0])[0] + interp(ax, P, [10.0], [-40.0])[0]
        lr = abs(interp(ax, P, [60.0], [30.0])[0] - interp(ax, P, [-60.0], [30.0])[0])
        print(f"{h:>6.4g} {r['n']:>5} {r['iters']:>8} {r['defect']:>14.3e} {c:>10.6f} {symy:>18.6f} {lr:>10.2e}")
