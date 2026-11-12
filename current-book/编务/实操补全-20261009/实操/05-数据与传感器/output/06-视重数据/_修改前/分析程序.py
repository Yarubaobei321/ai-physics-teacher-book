#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第06章 · 视重（构造数据）练习 — 可复用分析程序
================================================
按 input/06-视重数据/synthetic-definition.md 生成【构造数据，非实测】，
并用二阶巴特沃斯低通对“含 20Hz 人为干扰的原始力”分别做 4Hz / 2Hz 滤波，
各比较「单次前向（实时）」与「前后向零相位」。

构造（严格照定义）：
  m=0.500 kg, g=9.80 m/s², 向上为正
  t_i = i×0.01 s, i=0…300（共 301 点）
  0.50≤t<1.00  → 理想 a=+1.00 m/s²
  2.00≤t<2.50  → 理想 a=-1.00 m/s²
  其余         → 理想 a=0
  F_ideal = m(g+a)
  F_raw   = F_ideal + 0.05·sin(40πt)   （20 Hz 人为正弦干扰，非随机噪声）
  保存 time_s, force_ideal_N, force_raw_N

滤波（无第三方依赖，自实现二阶巴特沃斯低通 biquad）：
  - 算法：RBJ 双二次（biquad）低通，Q = 1/√2（二阶巴特沃斯），双线性变换预畸变。
  - 单次前向（实时）：y[n] = b0x[n]+b1x[n-1]+b2x[n-2] − a1y[n-1] − a2y[n-2]，初值全 0。
  - 前后向零相位：先前向，再把结果反转做同一次滤波，再反转；同样零初值。
  - 端点处理：两端用零初值，故起止处可能存在暂态；未采用 scipy 的奇延拓。
  - 幅频响应：单次前向为 |H(f)|（二阶），前后向为 |H(f)|²（等效四阶），两者不同。

加速度与积分：a = F/m − g；用实际时间做梯形积分，v0 = 0；不强行让末速度归零。

用法：python3 分析程序.py          （输出到脚本同级目录）
"""
import os, math, json, csv

M_KG = 0.500
G = 9.80
DT = 0.01
N = 301
NOISE_AMP = 0.05
NOISE_F = 20.0           # Hz，人为干扰；sin(2π·20·t)=sin(40πt)
LABEL = "构造数据，非实测"

CUTOFFS = [4.0, 2.0]


# ---------------- 构造数据 ----------------
def a_ideal(t):
    if 0.50 <= t < 1.00:
        return 1.00
    if 2.00 <= t < 2.50:
        return -1.00
    return 0.0


def build():
    times, ai, fi, fr = [], [], [], []
    for i in range(N):
        t = i * DT
        a = a_ideal(t)
        fid = M_KG * (G + a)
        fraw = fid + NOISE_AMP * math.sin(2 * math.pi * NOISE_F * t)
        times.append(t); ai.append(a); fi.append(fid); fr.append(fraw)
    return times, ai, fi, fr


# ---------------- 二阶巴特沃斯低通 biquad ----------------
def butter2_lowpass(fc, fs):
    """返回 (b0,b1,b2,a1,a2)。RBJ 低通，Q=1/√2。"""
    w0 = 2 * math.pi * fc / fs
    cw = math.cos(w0); sw = math.sin(w0)
    Q = 1.0 / math.sqrt(2.0)
    alpha = sw / (2 * Q)
    b0 = (1 - cw) / 2
    b1 = 1 - cw
    b2 = (1 - cw) / 2
    a0 = 1 + alpha
    a1 = -2 * cw
    a2 = 1 - alpha
    return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0


def filt_forward(x, c):
    """单次前向（实时）。初值取**稳态初值**：假定 t<0 时输入恒为 x[0]，
    使 y 从 x[0]·DC增益 出发，避免“把 4.9 N 的直流当成 0 起步”的假暂态。"""
    b0, b1, b2, a1, a2 = c
    n = len(x)
    if n == 0:
        return []
    y = [0.0] * n
    x0 = x[0]
    yss = x0 * (b0 + b1 + b2) / (1 + a1 + a2)   # 直流增益处稳态
    x1 = x2 = x0
    y1 = y2 = yss
    for i in range(n):
        xn = x[i]
        yn = b0 * xn + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        y[i] = yn
        x2, x1 = x1, xn
        y2, y1 = y1, yn
    return y


def filt_fwd_bwd(x, c):
    """前后向零相位：前向 → 反转 → 前向 → 反转。
    两次前向都用同一套稳态初值（各自以该次输入的首值为准）。"""
    y = filt_forward(x, c)
    yr = filt_forward(y[::-1], c)
    return yr[::-1]


def mag_response(fc, fs, f):
    """解析幅频响应：二阶巴特沃斯 |H(f)|。"""
    r = f / fc
    return 1.0 / math.sqrt(1.0 + r ** 4)


# ---------------- 积分 ----------------
def trapezoid_velocity(times, acc):
    v = [0.0] * len(times)
    for i in range(1, len(times)):
        v[i] = v[i - 1] + 0.5 * (acc[i - 1] + acc[i]) * (times[i] - times[i - 1])
    return v


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def mask_mean(xs, times, lo, hi):
    sel = [x for x, t in zip(xs, times) if lo <= t < hi]
    return mean(sel)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = here
    times, ai, fi, fr = build()
    fs = 1.0 / DT

    # 结构检查（构造数据本身）
    dt = [round(times[i + 1] - times[i], 9) for i in range(len(times) - 1)]
    dup = sum(1 for d in dt if d == 0)
    back = sum(1 for d in dt if d < 0)
    checks = {"n": len(times), "dt_min": min(dt), "dt_max": max(dt),
              "duplicate_dt": dup, "regress_dt": back,
              "t0": times[0], "t_last": times[-1]}

    # 滤波
    results = {}
    for fc in CUTOFFS:
        c = butter2_lowpass(fc, fs)
        ff = filt_forward(fr, c)
        fb = filt_fwd_bwd(fr, c)
        results[fc] = {"coef": c, "fwd": ff, "fb": fb}

    # 加速度：a = F/m − g（对每种力分别换算）
    acc_ideal = [f / M_KG - G for f in fi]
    acc_raw = [f / M_KG - G for f in fr]
    accs = {"ideal": acc_ideal, "raw": acc_raw}
    for fc in CUTOFFS:
        accs[f"fwd{fc:g}"] = [f / M_KG - G for f in results[fc]["fwd"]]
        accs[f"fb{fc:g}"] = [f / M_KG - G for f in results[fc]["fb"]]

    # 速度：梯形积分
    vels = {k: trapezoid_velocity(times, v) for k, v in accs.items()}

    # 统计区间：静止(3段) / +1平台 / −1平台（分列，避免把 ±1 平台合并后互相抵消）
    static_win = [(0.0, 0.50), (1.00, 2.00), (2.50, 3.001)]
    plus_win = [(0.50, 1.00)]
    minus_win = [(2.00, 2.50)]

    def seg_mean(sig, wins):
        s = []
        for lo, hi in wins:
            s += [x for x, t in zip(sig, times) if lo <= t < hi]
        return mean(s)

    def tri(sig):
        return (seg_mean(sig, static_win), seg_mean(sig, plus_win), seg_mean(sig, minus_win))

    label_map = {"ideal": "理想力/加速度", "raw": "原始力（含20Hz干扰）",
                 "fwd4": "4Hz 单次前向", "fb4": "4Hz 前后向零相位",
                 "fwd2": "2Hz 单次前向", "fb2": "2Hz 前后向零相位"}

    summary = []
    for k in ["ideal", "raw", "fwd4", "fb4", "fwd2", "fb2"]:
        a = accs[k]; v = vels[k]
        sm, pm, mm = tri(a)
        summary.append({
            "key": k, "label": label_map[k],
            "a_static_mean": sm, "a_plus_mean": pm, "a_minus_mean": mm,
            "a_integral": sum(0.5 * (a[i - 1] + a[i]) * (times[i] - times[i - 1]) for i in range(1, len(a))),
            "v_final": v[-1],
        })

    force_stats = []
    fr_sets = [("ideal", "理想力", fi), ("raw", "原始力（含20Hz干扰）", fr)]
    for fc in CUTOFFS:
        fr_sets.append((f"fwd{fc:g}", f"{fc:g}Hz 单次前向", results[fc]["fwd"]))
        fr_sets.append((f"fb{fc:g}", f"{fc:g}Hz 前后向零相位", results[fc]["fb"]))
    for k, lab, sig in fr_sets:
        sm, pm, mm = tri(sig)
        force_stats.append({"key": k, "label": lab, "static_mean": sm,
                            "plus_mean": pm, "minus_mean": mm})

    # 幅频响应对比（20Hz 干扰处）
    resp = []
    for fc in CUTOFFS:
        h1 = mag_response(fc, fs, NOISE_F)
        h2 = h1 * h1
        resp.append({"fc": fc,
                     "fwd_at_20": h1, "fwd_db": 20 * math.log10(h1),
                     "fb_at_20": h2, "fb_db": 20 * math.log10(h2)})

    # ---------------- 输出 ----------------
    # 原始表
    with open(os.path.join(outdir, "原始表.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["# 数据身份", LABEL, "（非严力耕老师实测，非本轮真实测量）"])
        w.writerow(["# 构造参数", f"m={M_KG}kg", f"g={G}m/s^2", f"dt={DT}s",
                    f"噪声={NOISE_AMP}sin(40*pi*t)"])
        w.writerow(["i", "time_s", "a_ideal_m_s2", "force_ideal_N", "force_raw_N"])
        for i in range(N):
            w.writerow([i, f"{times[i]:.3f}", f"{ai[i]:.4f}", f"{fi[i]:.6f}", f"{fr[i]:.6f}"])

    # 处理表
    with open(os.path.join(outdir, "处理表.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["# 数据身份", LABEL, "（非严力耕老师实测，非本轮真实测量）"])
        w.writerow(["# 滤波", "二阶巴特沃斯低通(biquad, Q=1/√2)", "单次前向=实时", "前后向=零相位"])
        w.writerow(["i", "time_s",
                    "force_fwd4_N", "force_fb4_N", "force_fwd2_N", "force_fb2_N",
                    "acc_raw_m_s2", "acc_fwd4_m_s2", "acc_fb4_m_s2", "acc_fwd2_m_s2", "acc_fb2_m_s2",
                    "v_ideal_m_s", "v_raw_m_s", "v_fwd4_m_s", "v_fb4_m_s", "v_fwd2_m_s", "v_fb2_m_s"])
        for i in range(N):
            w.writerow([i, f"{times[i]:.3f}",
                        f'{results[4.0]["fwd"][i]:.6f}', f'{results[4.0]["fb"][i]:.6f}',
                        f'{results[2.0]["fwd"][i]:.6f}', f'{results[2.0]["fb"][i]:.6f}',
                        f"{acc_raw[i]:.6f}", f"{accs['fwd4'][i]:.6f}", f"{accs['fb4'][i]:.6f}",
                        f"{accs['fwd2'][i]:.6f}", f"{accs['fb2'][i]:.6f}",
                        f"{vels['ideal'][i]:.6f}", f"{vels['raw'][i]:.6f}",
                        f"{vels['fwd4'][i]:.6f}", f"{vels['fb4'][i]:.6f}",
                        f"{vels['fwd2'][i]:.6f}", f"{vels['fb2'][i]:.6f}"])

    bundle = {
        "label": LABEL, "m": M_KG, "g": G, "dt": DT, "fs": fs, "noise": NOISE_AMP,
        "noise_f": NOISE_F, "cutoffs": CUTOFFS, "checks": checks,
        "time_s": [round(t, 4) for t in times],
        "a_ideal": [round(x, 6) for x in ai],
        "force_ideal": [round(x, 6) for x in fi],
        "force_raw": [round(x, 6) for x in fr],
        "force_fwd4": [round(x, 6) for x in results[4.0]["fwd"]],
        "force_fb4": [round(x, 6) for x in results[4.0]["fb"]],
        "force_fwd2": [round(x, 6) for x in results[2.0]["fwd"]],
        "force_fb2": [round(x, 6) for x in results[2.0]["fb"]],
        "acc_raw": [round(x, 6) for x in acc_raw],
        "v_ideal": [round(x, 6) for x in vels["ideal"]],
        "v_raw": [round(x, 6) for x in vels["raw"]],
        "v_fwd4": [round(x, 6) for x in vels["fwd4"]],
        "v_fb4": [round(x, 6) for x in vels["fb4"]],
        "v_fwd2": [round(x, 6) for x in vels["fwd2"]],
        "v_fb2": [round(x, 6) for x in vels["fb2"]],
        "coef": {f"{fc:g}": list(butter2_lowpass(fc, fs)) for fc in CUTOFFS},
        "summary": summary, "force_stats": force_stats, "resp": resp,
    }
    with open(os.path.join(outdir, "数据包.json"), "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, ensure_ascii=False, allow_nan=False, separators=(",", ":"))

    # 参数说明
    with open(os.path.join(outdir, "参数说明.md"), "w", encoding="utf-8") as fh:
        fh.write("# 第06章 · 视重（构造数据）— 参数与算法说明\n\n")
        fh.write(f"> 数据身份：**{LABEL}**。不是严力耕老师装置的原始数据，也不是新一次真实测量。\n\n")
        fh.write("## 构造参数\n")
        fh.write(f"- m = {M_KG} kg，g = {G} m/s²，向上为正\n")
        fh.write(f"- t_i = i×{DT} s，i=0…{N-1}（共 {N} 点），fs = {fs:.0f} Hz\n")
        fh.write("- 理想加速度 a：0.50≤t<1.00 → +1.00；2.00≤t<2.50 → −1.00；其余 → 0\n")
        fh.write(f"- F_ideal = m(g+a)；F_raw = F_ideal + {NOISE_AMP}·sin(40πt)（**20 Hz 人为正弦干扰**）\n\n")
        fh.write("## 滤波算法\n")
        fh.write("- 类型：**二阶巴特沃斯低通**（Butterworth, order 2）\n")
        fh.write("- 实现：RBJ 双二次（biquad）低通，Q = 1/√2，双线性变换预畸变（fc 预畸变角 w0 = 2πfc/fs）\n")
        for fc in CUTOFFS:
            b0, b1, b2, a1, a2 = butter2_lowpass(fc, fs)
            fh.write(f"  - fc={fc:g}Hz：b=[{b0:.8f}, {b1:.8f}, {b2:.8f}]，a=[1, {a1:.8f}, {a2:.8f}]\n")
        fh.write("- 单次前向（实时）：y[n]=b0x[n]+b1x[n−1]+b2x[n−2]−a1y[n−1]−a2y[n−2]，"
                 "**稳态初值**（以首个样本 x[0] 的直流稳态出发，避免 4.9 N 直流被当成 0 起步的假暂态）\n")
        fh.write("- 前后向零相位：前向 → 反转 → 同一次前向 → 反转；两次前向各用自己的稳态初值\n")
        fh.write("- 端点处理：两端用稳态初值，故起止处暂态很小；**未**采用 scipy 的奇延拓，"
                 "边缘仍会有轻微差异；前后向为非因果（零相位）\n")
        fh.write("- 幅频响应：单次前向为 |H(f)|（二阶，−12 dB/oct）；前后向为 |H(f)|²（等效四阶，−24 dB/oct）；**两者不同**\n\n")
        fh.write("## 20 Hz 干扰处的幅频响应（解析值）\n")
        fh.write("| fc | 单次前向 \\|H\\| | 前向 dB | 前后向 \\|H\\|² | 前后向 dB |\n|---|---|---|---|---|\n")
        for r in resp:
            fh.write(f"| {r['fc']:g} Hz | {r['fwd_at_20']:.6f} | {r['fwd_db']:.2f} | {r['fb_at_20']:.6f} | {r['fb_db']:.2f} |\n")
        fh.write("\n## 加速度与积分\n")
        fh.write("- a = F/m − g；梯形积分用**实际时间**步长，v0 = 0；**不强行**让末速度归零。\n")

    # 统计与检查
    with open(os.path.join(outdir, "统计与检查.md"), "w", encoding="utf-8") as fh:
        fh.write("# 第06章 · 视重（构造数据）— 实际统计与检查\n\n")
        fh.write(f"> 数据身份：**{LABEL}**。以下数字均由本目录 `分析程序.py` 实际运行得到。\n\n")
        fh.write("## 1. 构造数据时间轴检查\n")
        fh.write(f"- 点数 {checks['n']}；Δt 最小 {checks['dt_min']} s，最大 {checks['dt_max']} s；"
                 f"重复 Δt {checks['duplicate_dt']} 处，倒退 {checks['regress_dt']} 处\n")
        fh.write(f"- t 从 {checks['t0']:.2f} s 到 {checks['t_last']:.2f} s\n\n")
        fh.write("## 2. 力信号区间均值（N）\n")
        fh.write("| 信号 | 静止均值 | +1平台均值 | −1平台均值 |\n|---|---|---|---|\n")
        for s in force_stats:
            fh.write(f"| {s['label']} | {s['static_mean']:.4f} | {s['plus_mean']:.4f} | {s['minus_mean']:.4f} |\n")
        fh.write("\n> 理想力：静止 m·g = %.3f N；a=+1 平台 m(g+1) = %.3f N；a=−1 平台 m(g−1) = %.3f N。\n"
                 % (M_KG * G, M_KG * (G + 1), M_KG * (G - 1)))
        fh.write("> 说明：滤波采用稳态初值，起止暂态很小；平台均值相对理想值的偏差主要来自"
                 "低通对**平台边沿**的平滑（阶跃被展宽），以及 20 Hz 干扰的残余，不是“力的真值偏低”。\n")
        fh.write("\n## 3. 加速度/速度统计（N, m/s 或 m/s²）\n")
        fh.write("| 信号 | a静止均值 | a(+1平台) | a(−1平台) | ∫a dt | 末速度 v(T) |\n|---|---|---|---|---|---|\n")
        for s in summary:
            fh.write(f"| {s['label']} | {s['a_static_mean']:.4f} | {s['a_plus_mean']:.4f} | {s['a_minus_mean']:.4f} | "
                     f"{s['a_integral']:.4f} | {s['v_final']:.4f} |\n")
        fh.write("\n> 理想 a：静止=0，平台=±1.00；∫a dt 理想为 0（+1×0.5 −1×0.5），"
                 "末速度理想为 0。含干扰/滤波后∫a dt 与末速度偏离 0，属真实结果，**未做归零校正**。\n")

    print("OK. 输出：原始表.csv / 处理表.csv / 参数说明.md / 统计与检查.md / 数据包.json")
    for s in force_stats:
        print(f"  force {s['label']}: static={s['static_mean']:.4f} +1={s['plus_mean']:.4f} -1={s['minus_mean']:.4f}")
    for s in summary:
        print(f"  {s['label']}: a_static={s['a_static_mean']:.4f} a+1={s['a_plus_mean']:.4f} "
              f"a-1={s['a_minus_mean']:.4f} int_a={s['a_integral']:.4f} v_final={s['v_final']:.4f}")


if __name__ == "__main__":
    main()
