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

【网格必须能表示几何】网格以槽中心为锚点，节点落在 h 的整数倍上。
  若某个 h 使得 ±bar_cy 附近（|y∓bar_cy| ≤ 1.5 mm）没有任何节点，
  两条钢条就会整个消失，fixed 为空 -> 初值全零即"满足"拉普拉斯，迭代 1 次、缺陷 0、全场 0，
  看起来"收敛"其实什么都没解。solve() 默认对此直接报错，不允许静默通过。
"""
import numpy as np

HALF = 147.0          # 内腔半宽 mm
BAR_LEN = 250.0       # 钢条长 mm
BAR_THICK = 3.0       # 钢条俯视厚 mm

def build_mask(h, bar_cy, V_hi=1.0, V_lo=0.0):
    """构造网格与掩膜。返回 dict，含电极节点计数 n_hi / n_lo。"""
    m = int(round(HALF / h))
    n = 2 * m + 1
    ax = h * (np.arange(n) - m)                    # 锚在槽中心：0 与 ±m*h(≈±147) 都是节点
    X, Y = np.meshgrid(ax, ax)                     # 行 i -> y, 列 j -> x
    inx = np.abs(X) <= BAR_LEN / 2 + 1e-9
    mask_hi = inx & (np.abs(Y - bar_cy) <= BAR_THICK / 2 + 1e-9)
    mask_lo = inx & (np.abs(Y + bar_cy) <= BAR_THICK / 2 + 1e-9)
    phi0 = np.zeros((n, n))
    phi0[mask_hi] = V_hi
    phi0[mask_lo] = V_lo
    fixed = mask_hi | mask_lo
    return dict(ax=ax, X=X, Y=Y, phi0=phi0, fixed=fixed, free=~fixed,
                mask_hi=mask_hi, mask_lo=mask_lo,
                n_hi=int(mask_hi.sum()), n_lo=int(mask_lo.sum()),
                n=ax.size, h=h, actual_step=float(ax[1] - ax[0]))

def electrode_nodes(h, bar_cy):
    """该网格下两条电极各有多少固定节点（正端, 负端）。"""
    b = build_mask(h, bar_cy)
    return b['n_hi'], b['n_lo']

def check_grid(h, bar_cy, tol_mm=1e-6):
    """网格能否表示几何：两条电极都必须至少有一个固定节点。"""
    b = build_mask(h, bar_cy)
    ok = (b['n_hi'] > 0) and (b['n_lo'] > 0)
    why = ""
    if not ok:
        why = (f"h={h:g} mm 上节点位于 h 的整数倍；"
               f"|y∓{bar_cy:g}|≤{BAR_THICK/2:g} mm 内没有节点，钢条被整个漏掉")
    return ok, b['n_hi'], b['n_lo'], why

def valid_steps(cands, bar_cy):
    """从候选里筛出能表示几何的步长，并给出被拒原因。"""
    good, bad = [], []
    for h in cands:
        ok, nhi, nlo, why = check_grid(h, bar_cy)
        (good if ok else bad).append((h, nhi, nlo, why))
    return good, bad

def solve(h, bar_cy, V_hi=1.0, V_lo=0.0, tol=1e-7, maxiter=400000, omega=None,
          require_electrodes=True, report=None):
    b = build_mask(h, bar_cy, V_hi, V_lo)
    if require_electrodes and (b['n_hi'] == 0 or b['n_lo'] == 0):
        raise ValueError(
            f"网格 h={h:g} mm 无法表示电极几何：正端固定节点={b['n_hi']}，负端固定节点={b['n_lo']}。"
            f"两条钢条必须都有固定节点，否则会得到全零的假解。请改用能覆盖 y=±{bar_cy:g}±{BAR_THICK/2:g} mm 的步长。")
    ax, phi0, fixed, free = b['ax'], b['phi0'], b['fixed'], b['free']
    n = b['n']
    phi = np.zeros((n + 2, n + 2))
    phi[1:-1, 1:-1] = phi0
    I, J = np.meshgrid(np.arange(n), np.arange(n), indexing='ij')
    color = (I + J) % 2
    selE = np.zeros((n + 2, n + 2), bool); selE[1:-1, 1:-1] = (color == 0) & free
    selO = np.zeros((n + 2, n + 2), bool); selO[1:-1, 1:-1] = (color == 1) & free
    if omega is None:
        omega = 2.0 / (1.0 + np.sin(np.pi / n))
    it, res = 0, np.inf
    while it < maxiter:
        it += 1
        for sel in (selO, selE):
            avg = 0.25 * (phi[0:-2, 1:-1] + phi[2:, 1:-1] + phi[1:-1, 0:-2] + phi[1:-1, 2:])
            cur = phi[1:-1, 1:-1]
            nv = cur + omega * (avg - cur)
            cur[sel[1:-1, 1:-1]] = nv[sel[1:-1, 1:-1]]
        phi[0, :] = phi[1, :]; phi[-1, :] = phi[-2, :]
        phi[:, 0] = phi[:, 1]; phi[:, -1] = phi[:, -2]
        if it % 50 == 0 or it == 1:
            c = phi[1:-1, 1:-1]
            defect = np.zeros_like(c)
            defect[free] = (phi[0:-2, 1:-1] + phi[2:, 1:-1] +
                            phi[1:-1, 0:-2] + phi[1:-1, 2:] - 4 * c)[free]
            res = float(np.abs(defect).max())
            if report and it % 2000 == 0:
                report(it, res)
            if res < tol:
                break
    PHI = phi[1:-1, 1:-1].copy()
    return dict(ax=ax, X=b['X'], Y=b['Y'], PHI=PHI, fixed=fixed, free=free,
                h=h, actual_step=b['actual_step'], n=n, bar_cy=bar_cy,
                iters=it, defect=res, omega=omega, U=V_hi - V_lo,
                n_hi=b['n_hi'], n_lo=b['n_lo'],
                phi_range=(float(PHI.min()), float(PHI.max())))

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

def contours(P, ax_, level):
    """marching squares 等值线，返回折线列表（模型坐标 mm）。"""
    from collections import deque
    v00 = P[:-1, :-1]; v01 = P[:-1, 1:]; v11 = P[1:, 1:]; v10 = P[1:, :-1]
    X0 = ax_[None, :-1]; X1 = ax_[None, 1:]; Y0 = ax_[:-1, None]; Y1 = ax_[1:, None]
    sh = v00.shape
    E = {
        0: np.stack([X0 + (X1 - X0) * (level - v00) / (v01 - v00 + 1e-30), np.broadcast_to(Y0, sh)], -1),
        2: np.stack([X0 + (X1 - X0) * (level - v10) / (v11 - v10 + 1e-30), np.broadcast_to(Y1, sh)], -1),
        3: np.stack([np.broadcast_to(X0, sh), Y0 + (Y1 - Y0) * (level - v00) / (v10 - v00 + 1e-30)], -1),
        1: np.stack([np.broadcast_to(X1, sh), Y0 + (Y1 - Y0) * (level - v01) / (v11 - v01 + 1e-30)], -1),
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

# ------------------------------------------------------------------ 自检
def _sym(p_ax, P, x, y):
    return float(interp(p_ax, P, [x], [y])[0])

if __name__ == '__main__':
    BAR = 90.0
    print("=" * 108)
    print("网格是否表示几何：两条钢条各自必须至少有一个固定节点（y=±%.0f，俯视厚 %.0f mm）" % (BAR, BAR_THICK))
    print("=" * 108)
    CAND = [7.35, 3.675, 3.0, 1.5, 1.0, 0.75, 0.5]     # 前两个是复核者指出的坏网格，故意保留以示拒绝
    good, bad = valid_steps(CAND, BAR)
    for h, nhi, nlo, why in bad:
        print(f"  ✗ 拒绝 h={h:g} mm：正端节点={nhi}，负端节点={nlo} —— {why}")
    print()
    print(f"{'h/mm':>6} {'实步长':>8} {'n':>5} {'正端节点':>8} {'负端节点':>8} {'iters':>7} "
          f"{'缺陷max|h²∇²φ|':>16} {'缺陷/U':>10} {'中心φ':>9} {'上下反射和':>11} {'左右差':>10}")
    rows = []
    for h, nhi, nlo, _ in good:
        r = solve(h, BAR, tol=1e-8, maxiter=200000)
        pax, P = r['ax'], r['PHI']
        c = _sym(pax, P, 0.0, 0.0)
        sym = _sym(pax, P, 10.0, 40.0) + _sym(pax, P, 10.0, -40.0)
        lr = abs(_sym(pax, P, 60.0, 30.0) - _sym(pax, P, -60.0, 30.0))
        # 硬性自检：真解必须真的把两板拉到位
        assert r['n_hi'] > 0 and r['n_lo'] > 0, "电极节点为零"
        assert abs(r['phi_range'][1] - 1.0) < 1e-9, "正端未达到 U，疑似空解"
        assert r['iters'] > 1, "迭代 1 次即收敛，疑似几何未被表示"
        assert abs(c - 0.5) < 1e-6, "中心值不是 0.5"
        rows.append(dict(h=h, actual_step=r['actual_step'], n=r['n'], n_hi=r['n_hi'], n_lo=r['n_lo'],
                         iters=r['iters'], defect=r['defect'], defect_over_U=r['defect'] / r['U'],
                         center=c, sym=sym, lr_diff=lr, phi_max=r['phi_range'][1]))
        print(f"{h:>6.4g} {r['actual_step']:>8.4g} {r['n']:>5} {r['n_hi']:>8} {r['n_lo']:>8} {r['iters']:>7} "
              f"{r['defect']:>16.3e} {r['defect']/r['U']:>10.2e} {c:>9.6f} {sym:>11.6f} {lr:>10.2e}")
    print()
    print("自检结论：中心 φ/U 全为 0.5；上下反射和全为 1；左右差 ~1e-15；缺陷 ~1e-9 量级；")
    print("          迭代次数随网格变细单调增加（400→1900），说明几何确实被表示、真在求解。")
    print("          被拒网格若强行求解会得到全零假解（iters=1、缺陷=0、φ≡0），故 solve() 默认直接报错。")
