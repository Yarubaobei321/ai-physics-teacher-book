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
  - 初值：**与首点恒定输入相符的稳态初值**（y[-1]=y[-2]=x[0]·DC增益，x[-1]=x[-2]=x[0]）。
    含 4.9 N 静重的力若用全零初值，会人为制造近 −g 的启动暂态，本程序**不使用**零初值。
  - 单次前向（实时）：因果。
  - 前后向零相位：前向 → 反转 → 同一次前向 → 反转；两次各用自身稳态初值；非因果。
  - 端点：两端稳态初值，暂态很小；未采用 scipy 奇延拓。

幅频响应：按**实际离散传递函数** H(z)=(b0+b1 z⁻¹+b2 z⁻²)/(1+a1 z⁻¹+a2 z⁻²) 取 z=e^{jω} 计算，
  单次前向 = |H(e^{jω})|，前后向零相位 = |H(e^{jω})|²（等效阶数翻倍）。**不是**模拟域公式。

加速度与积分：a = F/m − g；用实际时间做梯形积分，v0 = 0；不强行让末速度归零。

用法：python3 分析程序.py          （输出到脚本同级目录）
"""
import os, math, cmath, json, csv

M_KG = 0.500
G = 9.80
DT = 0.01
N = 301
NOISE_AMP = 0.05
NOISE_F = 20.0           # Hz，人为干扰；sin(2π·20·t)=sin(40πt)
LABEL = "构造数据，非实测"

CUTOFFS = [4.0, 2.0]

# 运动状态区间（按理想 a 的定义划分；名称按“运动状态”而非“受力是否变化”）
WINDOWS = [
    ("起始静止", 0.00, 0.50),
    ("正加速",   0.50, 1.00),
    ("匀速",     1.00, 2.00),
    ("负加速",   2.00, 2.50),
    ("结束静止", 2.50, 3.001),
]
WINDOW_NAMES = [w[0] for w in WINDOWS]


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
    """返回 (b0,b1,b2,a1,a2)。RBJ 低通，Q=1/√2（二阶巴特沃斯）。"""
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


def dc_gain(c):
    b0, b1, b2, a1, a2 = c
    return (b0 + b1 + b2) / (1 + a1 + a2)


def filt_forward(x, c):
    """单次前向（实时）。**稳态初值**：假定 t<0 时输入恒为 x[0]，
    y[-1]=y[-2]=x[0]·DC增益、x[-1]=x[-2]=x[0]，避免“把 4.9 N 直流当成 0 起步”的假暂态。"""
    b0, b1, b2, a1, a2 = c
    n = len(x)
    if n == 0:
        return []
    y = [0.0] * n
    x0 = x[0]
    yss = x0 * dc_gain(c)
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
    """前后向零相位：前向 → 反转 → 前向 → 反转。两次前向各用自身稳态初值。"""
    y = filt_forward(x, c)
    yr = filt_forward(y[::-1], c)
    return yr[::-1]


def mag_response_digital(c, fs, f):
    """按实际离散传递函数计算 |H(e^{jω})|，ω = 2πf/fs。"""
    b0, b1, b2, a1, a2 = c
    w = 2 * math.pi * f / fs
    z1 = cmath.exp(-1j * w)
    z2 = cmath.exp(-2j * w)
    num = b0 + b1 * z1 + b2 * z2
    den = 1.0 + a1 * z1 + a2 * z2
    return abs(num) / abs(den)


# ---------------- 积分 ----------------
def trapezoid_velocity(times, acc):
    v = [0.0] * len(times)
    for i in range(1, len(times)):
        v[i] = v[i - 1] + 0.5 * (acc[i - 1] + acc[i]) * (times[i] - times[i - 1])
    return v


def mean(xs):
    return sum(xs) / len(xs) if xs else None


# ---------------- 恒定力回归自检（①）----------------
def constant_force_check(coef_list):
    """恒定 4.9 N × 301 点过同一套滤波器：应始终保持 4.9 N，a=0，v=0。"""
    x = [M_KG * G] * N
    out = []
    for fc, c in coef_list:
        fwd = filt_forward(x, c)
        fb = filt_fwd_bwd(x, c)
        af = [v / M_KG - G for v in fwd]
        vf = trapezoid_velocity([i * DT for i in range(N)], af)
        ag = [v / M_KG - G for v in fb]
        vg = trapezoid_velocity([i * DT for i in range(N)], ag)
        out.append({
            "fc": fc,
            "fwd_max_dev": max(abs(v - x[0]) for v in fwd),
            "fb_max_dev": max(abs(v - x[0]) for v in fb),
            "fwd_v_final": vf[-1],
            "fb_v_final": vg[-1],
        })
    return out


# ---------------- 主流程 ----------------
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = here
    times, ai, fi, fr = build()
    fs = 1.0 / DT
    coefs = [(fc, butter2_lowpass(fc, fs)) for fc in CUTOFFS]

    # 结构检查（构造数据本身）
    dt = [round(times[i + 1] - times[i], 9) for i in range(len(times) - 1)]
    dup = sum(1 for d in dt if d == 0)
    back = sum(1 for d in dt if d < 0)
    checks = {"n": len(times), "dt_min": min(dt), "dt_max": max(dt),
              "duplicate_dt": dup, "regress_dt": back,
              "t0": times[0], "t_last": times[-1]}

    # 滤波
    results = {}
    for fc, c in coefs:
        results[fc] = {"coef": c, "fwd": filt_forward(fr, c), "fb": filt_fwd_bwd(fr, c)}

    # 加速度 a = F/m − g
    acc_ideal = [f / M_KG - G for f in fi]
    acc_raw = [f / M_KG - G for f in fr]
    accs = {"ideal": acc_ideal, "raw": acc_raw}
    for fc in CUTOFFS:
        accs[f"fwd{fc:g}"] = [f / M_KG - G for f in results[fc]["fwd"]]
        accs[f"fb{fc:g}"] = [f / M_KG - G for f in results[fc]["fb"]]

    # 速度：梯形积分
    vels = {k: trapezoid_velocity(times, v) for k, v in accs.items()}

    def win_mean(sig, lo, hi):
        sel = [x for x, t in zip(sig, times) if lo <= t < hi]
        return mean(sel)

    label_map = {"ideal": "理想力/加速度", "raw": "原始力（含20Hz干扰）",
                 "fwd4": "4Hz 单次前向", "fb4": "4Hz 前后向零相位",
                 "fwd2": "2Hz 单次前向", "fb2": "2Hz 前后向零相位"}
    KEYS = ["ideal", "raw", "fwd4", "fb4", "fwd2", "fb2"]

    # 力：各运动区间均值
    force_stats = []
    fr_sets = [("ideal", "理想力", fi), ("raw", "原始力（含20Hz干扰）", fr)]
    for fc in CUTOFFS:
        fr_sets.append((f"fwd{fc:g}", f"{fc:g}Hz 单次前向", results[fc]["fwd"]))
        fr_sets.append((f"fb{fc:g}", f"{fc:g}Hz 前后向零相位", results[fc]["fb"]))
    for k, lab, sig in fr_sets:
        force_stats.append({"key": k, "label": lab,
                            "wins": [win_mean(sig, lo, hi) for _, lo, hi in WINDOWS]})

    # 加速度/速度：各运动区间均值 + 总积分 + 末速度
    summary = []
    for k in KEYS:
        a = accs[k]; v = vels[k]
        summary.append({
            "key": k, "label": label_map[k],
            "a_wins": [win_mean(a, lo, hi) for _, lo, hi in WINDOWS],
            "v_wins": [win_mean(v, lo, hi) for _, lo, hi in WINDOWS],
            "a_integral": sum(0.5 * (a[i - 1] + a[i]) * (times[i] - times[i - 1]) for i in range(1, len(a))),
            "v_final": v[-1],
        })

    # 20 Hz 处幅频响应（离散传递函数）
    resp = []
    for fc, c in coefs:
        h1 = mag_response_digital(c, fs, NOISE_F)
        h2 = h1 * h1
        resp.append({"fc": fc, "fwd_at_20": h1, "fwd_db": 20 * math.log10(h1),
                     "fb_at_20": h2, "fb_db": 20 * math.log10(h2)})

    # 恒定力回归自检
    constchk = constant_force_check(coefs)

    # ---------------- 输出 ----------------
    with open(os.path.join(outdir, "原始表.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["# 数据身份", LABEL, "（非严力耕老师实测，非本轮真实测量）"])
        w.writerow(["# 构造参数", f"m={M_KG}kg", f"g={G}m/s^2", f"dt={DT}s",
                    f"噪声={NOISE_AMP}sin(40*pi*t)"])
        w.writerow(["i", "time_s", "a_ideal_m_s2", "force_ideal_N", "force_raw_N"])
        for i in range(N):
            w.writerow([i, f"{times[i]:.3f}", f"{ai[i]:.4f}", f"{fi[i]:.6f}", f"{fr[i]:.6f}"])

    with open(os.path.join(outdir, "处理表.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["# 数据身份", LABEL, "（非严力耕老师实测，非本轮真实测量）"])
        w.writerow(["# 滤波", "二阶巴特沃斯低通(biquad, Q=1/√2, 稳态初值)",
                    "单次前向=实时", "前后向=零相位"])
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
        "window_names": WINDOW_NAMES, "windows": [[n, lo, hi] for n, lo, hi in WINDOWS],
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
        "summary": summary, "force_stats": force_stats, "resp": resp, "const_check": constchk,
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
        fh.write("## 滤波算法与初始化\n")
        fh.write("- 类型：**二阶巴特沃斯低通**（Butterworth, order 2）\n")
        fh.write("- 实现：RBJ 双二次（biquad）低通，Q = 1/√2，双线性变换预畸变（w0 = 2πfc/fs）\n")
        for fc, c in coefs:
            b0, b1, b2, a1, a2 = c
            fh.write(f"  - fc={fc:g}Hz：b=[{b0:.10f}, {b1:.10f}, {b2:.10f}]，a=[1, {a1:.10f}, {a2:.10f}]"
                     f"（DC 增益 {dc_gain(c):.12f}）\n")
        fh.write("- 单次前向（实时，因果）：y[n]=b0x[n]+b1x[n−1]+b2x[n−2]−a1y[n−1]−a2y[n−2]；\n")
        fh.write("  **稳态初值**：x[-1]=x[-2]=x[0]，y[-1]=y[-2]=x[0]·DC增益。\n")
        fh.write("  含 4.9 N 静重的力若用**全零初值**，会人为制造近 −g 的启动暂态（伪影），本程序不使用。\n")
        fh.write("- 前后向零相位：前向 → 反转 → 同一次前向 → 反转；两次各用自身稳态初值；非因果、不能实时。\n")
        fh.write("- 端点处理：两端稳态初值，暂态很小；**未**采用 scipy 的奇延拓。\n")
        fh.write("- 恒定力自检：对恒定 4.9 N×301 点跑同一套滤波器，结果见 `统计与检查.md`。\n\n")
        fh.write("## 幅频响应（按实际离散传递函数 H(e^{jω}) 计算）\n")
        fh.write("`H(z)=(b0+b1 z⁻¹+b2 z⁻²)/(1+a1 z⁻¹+a2 z⁻²)`，单次前向 = `|H(e^{jω})|`，"
                 "前后向 = `|H(e^{jω})|²`（等效阶数翻倍）。**不是**模拟域公式 `1/√(1+(f/fc)⁴)`。\n\n")
        fh.write("| fc | 单次前向 \\|H\\| | 前向 dB | 前后向 \\|H\\|² | 前后向 dB |\n|---|---|---|---|---|\n")
        for r in resp:
            fh.write(f"| {r['fc']:g} Hz | {r['fwd_at_20']:.10f} | {r['fwd_db']:.2f} | {r['fb_at_20']:.10f} | {r['fb_db']:.2f} |\n")
        fh.write("\n## 加速度与积分\n")
        fh.write("- a = F/m − g；梯形积分用**实际时间**步长，v0 = 0；**不强行**让末速度归零。\n")

    # 统计与检查
    with open(os.path.join(outdir, "统计与检查.md"), "w", encoding="utf-8") as fh:
        fh.write("# 第06章 · 视重（构造数据）— 实际统计与检查\n\n")
        fh.write(f"> 数据身份：**{LABEL}**。以下数字均由本目录 `分析程序.py` 实际运行得到。\n\n")
        fh.write("## 0. 区间定义（按运动状态）\n")
        fh.write("| 区间 | 时间范围 (s) | 理想 a (m/s²) |\n|---|---|---|\n")
        for name, lo, hi in WINDOWS:
            fh.write(f"| {name} | [{lo:.2f}, {hi if hi<=3 else 3:.2f}] | {a_ideal(lo + (hi-lo)/2):+.2f} |\n")
        fh.write("\n> 1.00–2.00 s 理想 a = 0，物体**匀速上升**（速度不为零），"
                 "属于“受力平衡”而非“静止”，故此处命名为“匀速”而不是“静止”。\n\n")

        fh.write("## 1. 构造数据时间轴检查\n")
        fh.write(f"- 点数 {checks['n']}；Δt 最小 {checks['dt_min']} s，最大 {checks['dt_max']} s；"
                 f"重复 Δt {checks['duplicate_dt']} 处，倒退 {checks['regress_dt']} 处\n")
        fh.write(f"- t 从 {checks['t0']:.2f} s 到 {checks['t_last']:.2f} s\n\n")

        fh.write("## 2. 恒定力回归自检（①：应始终保持 4.9 N）\n")
        fh.write("对**恒定 4.9 N × 301 点**跑同一套滤波器：\n\n")
        fh.write("| fc | 单次前向最大偏离 (N) | 前后向最大偏离 (N) | 单次前向末速度 (m/s) | 前后向末速度 (m/s) |\n|---|---|---|---|---|\n")
        for c in constchk:
            fh.write(f"| {c['fc']:g} Hz | {c['fwd_max_dev']:.3e} | {c['fb_max_dev']:.3e} | "
                     f"{c['fwd_v_final']:.3e} | {c['fb_v_final']:.3e} |\n")
        fh.write("\n> 全零初值会产生近 −g 的启动暂态（例如 4Hz 前向末速约 −0.50 m/s、前后向约 −0.61 m/s），"
                 "那是初始化伪影；本程序用稳态初值后，恒定力保持 4.9 N、末速度≈0。\n\n")

        fh.write("## 3. 力在各运动区间的均值（N）\n")
        fh.write("| 信号 | " + " | ".join(WINDOW_NAMES) + " |\n")
        fh.write("|---|" + "---|" * len(WINDOW_NAMES) + "\n")
        for s in force_stats:
            fh.write(f"| {s['label']} | " + " | ".join(f"{v:.4f}" for v in s["wins"]) + " |\n")
        fh.write("\n> 理想力：起始/结束静止与匀速 = m·g = %.3f N；正加速平台 = m(g+1) = %.3f N；"
                 "负加速平台 = m(g−1) = %.3f N。\n" % (M_KG * G, M_KG * (G + 1), M_KG * (G - 1)))
        fh.write("> 正、负加速平台**分列**，不合并平均（合并会互相抵消）。\n\n")

        fh.write("## 4. 加速度 / 速度在各运动区间的均值\n")
        fh.write("| 信号 | " + " | ".join("a " + n for n in WINDOW_NAMES) + " | ∫a dt | 末速度 v(T) |\n")
        fh.write("|---|" + "---|" * (len(WINDOW_NAMES) + 2) + "\n")
        for s in summary:
            fh.write(f"| {s['label']} | " + " | ".join(f"{v:.4f}" for v in s["a_wins"]) +
                     f" | {s['a_integral']:.4f} | {s['v_final']:.4f} |\n")
        fh.write("\n| 信号 | " + " | ".join("v " + n for n in WINDOW_NAMES) + " |\n")
        fh.write("|---|" + "---|" * len(WINDOW_NAMES) + "\n")
        for s in summary:
            fh.write(f"| {s['label']} | " + " | ".join(f"{v:.4f}" for v in s["v_wins"]) + " |\n")
        fh.write("\n> 理想：起始静止 v=0；正加速结束后 v=+0.50 m/s；匀速段 v=+0.50 m/s（常量）；"
                 "负加速后 v≈0；结束静止 v≈0。∫a dt 理想为 0。\n")
        fh.write("> 含干扰/滤波后与理想值的偏离属真实结果，**未做归零校正**。\n")

    print("OK. 输出：原始表.csv / 处理表.csv / 参数说明.md / 统计与检查.md / 数据包.json")
    print("恒定 4.9N 自检：", [(c["fc"], f'fwd_dev={c["fwd_max_dev"]:.2e}', f'fb_dev={c["fb_max_dev"]:.2e}') for c in constchk])
    for r in resp:
        print(f"  20Hz fc={r['fc']:g}: |H|={r['fwd_at_20']:.10f} |H|^2={r['fb_at_20']:.10f}")
    for s in summary:
        print(f"  {s['label']}: a_wins={[round(x,4) for x in s['a_wins']]} int_a={s['a_integral']:.4f} v_final={s['v_final']:.4f}")
    for s in force_stats:
        print(f"  force {s['label']}: wins={[round(x,4) for x in s['wins']]}")


if __name__ == "__main__":
    main()
