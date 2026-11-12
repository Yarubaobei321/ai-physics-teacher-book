#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第05章 · 超声波历史记录复算程序（可复用）
=========================================
读取 input/05-超声波/ 下的两份原始 CSV，按固定声速 343 m/s 复算距离，
用连续 5 个有效点对（距离 m，板端时间 s）做最小二乘直线拟合得到速度。

- 只分析 kind=U 行（kind=D 为温湿度行，本程序只统计、不参与距离/速度计算）。
- 有效 = status=='ok'。
- 距离复算：distance_mm = pulse_us * 343 / 2000；distance_m = distance_mm/1000。
- 时间使用板端触发时间：t_s = t_us / 1e6（运动时间）；两门时间差与 pulse 时间不混用。
- 拟合窗口：连续 5 个有效点；遇无效点 / 序号缺号 / 时间倒退则重置窗口，前 4 点为空白。
- 速度标注在窗口时间的平均值处。
- 样本标准差一律用 N-1。

输出（默认写到脚本同级目录）：
  - 处理结果-固定平面.csv
  - 处理结果-往返.csv
  - 统计报告.md
  - 数据包.json （供 index.html 离线绘图使用）

用法： python3 分析程序.py [input目录]
"""
import os, sys, csv, json, math

CONST_C = 343.0          # m/s，固定声速，用于复算历史记录
FILES = {
    "fixed":  "20260918-161137-fixed-plane30cm-100ms.csv",
    "motion": "20260918-161547-motion-away-stop-toward.csv",
}
LABEL = "2026-09-18历史记录复算"


def read_rows(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames
        rows = list(reader)
    return fields, rows


def to_num(s):
    s = (s or "").strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def inspect(name, fields, rows):
    """原始结构 / 连续性 / 时间检查，返回报告字典。"""
    rep = {"file": name, "fields": fields, "n_rows": len(rows)}
    kinds = {}
    status = {}
    for r in rows:
        kinds[r.get("kind", "")] = kinds.get(r.get("kind", ""), 0) + 1
        status[r.get("status", "")] = status.get(r.get("status", ""), 0) + 1
    rep["kinds"] = kinds
    rep["status"] = status

    u = [r for r in rows if r.get("kind") == "U"]
    d = [r for r in rows if r.get("kind") == "D"]
    rep["n_U"] = len(u)
    rep["n_D"] = len(d)

    seq_u = [int(r["seq"]) for r in u]
    rep["seq_first_last"] = (seq_u[0], seq_u[-1]) if seq_u else None
    gaps = [(seq_u[i - 1], seq_u[i]) for i in range(1, len(seq_u)) if seq_u[i] != seq_u[i - 1] + 1]
    rep["seq_gaps"] = gaps

    t = [int(r["t_us"]) for r in u]
    back = [(i, t[i - 1], t[i]) for i in range(1, len(t)) if t[i] <= t[i - 1]]
    rep["time_regress"] = back
    dts = [t[i + 1] - t[i] for i in range(len(t) - 1)]
    rep["dt_us_min"] = min(dts) if dts else None
    rep["dt_us_max"] = max(dts) if dts else None
    rep["dt_us_mean"] = (sum(dts) / len(dts)) if dts else None

    # 与历史 distance_mm_343 比对，验证 343 复算一致
    mism = 0
    for r in u:
        p = to_num(r["pulse_us"]); dh = to_num(r["distance_mm_343"])
        if p is None or dh is None:
            continue
        if abs(p * CONST_C / 2000.0 - dh) > 0.001:
            mism += 1
    rep["distance_recompute_mismatch"] = mism

    # D 行温湿度范围（仅统计，不改写历史距离）
    temps = [to_num(r["temp_c"]) for r in d if to_num(r["temp_c"]) is not None]
    if temps:
        rep["temp_c_min"] = min(temps)
        rep["temp_c_max"] = max(temps)
    return rep


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def stdev_n1(xs):
    n = len(xs)
    if n < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def linfit(xs, ys):
    """最小二乘直线 y = a + b x，返回 (a, b, r2)。"""
    n = len(xs)
    mx = mean(xs); my = mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = my - b * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else None
    return a, b, r2


def process(path):
    """按规则计算距离与 5 点窗口速度。返回逐点记录列表与窗口速度列表。"""
    _, rows = read_rows(path)
    u = [r for r in rows if r.get("kind") == "U"]

    recs = []          # 每个 U 点一条
    window = []        # 当前连续有效窗口（至多 5）
    for r in u:
        seq = int(r["seq"])
        t_us = to_num(r["t_us"])
        pulse = to_num(r["pulse_us"])
        ok = (r.get("status") == "ok") and (t_us is not None) and (pulse is not None)

        rec = {"seq": seq, "t_us": t_us, "pulse_us": pulse}
        rec["distance_mm"] = pulse * CONST_C / 2000.0 if ok else None
        rec["distance_m"] = rec["distance_mm"] / 1000.0 if ok else None
        rec["t_s"] = t_us / 1e6 if t_us is not None else None
        rec["valid"] = bool(ok)

        if not ok:
            window = []                     # 无效点 -> 重置
        else:
            if window:
                prev = window[-1]
                if seq != prev["seq"] + 1:  # 缺号 -> 重置
                    window = []
                elif rec["t_us"] <= prev["t_us"]:   # 时间倒退 -> 重置
                    window = []
            window.append(rec)
            if len(window) > 5:
                window.pop(0)

        if len(window) == 5:
            xs = [p["t_s"] for p in window]
            ys = [p["distance_m"] for p in window]
            a, b, r2 = linfit(xs, ys)
            rec["vel_m_s"] = b
            rec["vel_mm_s"] = b * 1000.0
            rec["center_t_s"] = mean(xs)
            rec["fit_r2"] = r2
        else:
            rec["vel_m_s"] = None
            rec["vel_mm_s"] = None
            rec["center_t_s"] = None
            rec["fit_r2"] = None

        recs.append(rec)

    vels = [r["vel_mm_s"] for r in recs if r["vel_mm_s"] is not None]
    dists = [r["distance_mm"] for r in recs if r["distance_mm"] is not None]
    return recs, dists, vels


def sign_label(v_mm_s, thr):
    if v_mm_s is None:
        return "空"
    if v_mm_s > thr:
        return "远离"
    if v_mm_s < -thr:
        return "靠近"
    return "停住"


def segments(recs, thr):
    """按速度符号（相对首点时间）划分 远离/停住/靠近 连续段。"""
    segs = []
    t0 = next((r["t_s"] for r in recs if r["t_s"] is not None), None)
    cur = None
    for r in recs:
        if r["vel_mm_s"] is None:
            continue
        lab = sign_label(r["vel_mm_s"], thr)
        t_rel = r["center_t_s"] - t0
        if cur is None or cur["label"] != lab:
            if cur is not None:
                segs.append(cur)
            cur = {"label": lab, "t_start_rel": t_rel, "t_end_rel": t_rel,
                   "v_list": [r["vel_mm_s"]], "n": 1}
        else:
            cur["t_end_rel"] = t_rel
            cur["v_list"].append(r["vel_mm_s"])
            cur["n"] += 1
    if cur is not None:
        segs.append(cur)
    for s in segs:
        s["v_mean"] = mean(s["v_list"])
        s.pop("v_list")
    return segs


def write_csv(path, recs, label, thr):
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["# 数据身份", label])
        w.writerow(["# 声速 (m/s)", CONST_C])
        w.writerow(["# 距离复算式", "pulse_us * 343 / 2000"])
        w.writerow(["# 速度法", "连续5点 距离(m)~板端时间(s) 最小二乘斜率, 标在窗口时间均值处"])
        w.writerow(["# 符号阈值 (mm/s)", f"{thr:.6f}",
                    "|v|<=阈值判停住, 否则按正负判 远离/靠近"])
        w.writerow(["逐点局部序号", "设备seq", "t_us", "t_s", "pulse_us",
                    "distance_mm_原表", "distance_mm_复算", "有效",
                    "vel_mm_s", "vel_m_s", "窗口中心t_s", "拟合R2", "符号"])
        for i, r in enumerate(recs, 1):
            w.writerow([i, r["seq"], r["t_us"], f'{r["t_s"]:.6f}' if r["t_s"] is not None else "",
                        r["pulse_us"],
                        f'{r["distance_mm"]:.3f}' if r["distance_mm"] is not None else "",
                        f'{r["distance_mm"]:.3f}' if r["distance_mm"] is not None else "",
                        1 if r["valid"] else 0,
                        f'{r["vel_mm_s"]:.4f}' if r["vel_mm_s"] is not None else "",
                        f'{r["vel_m_s"]:.7f}' if r["vel_m_s"] is not None else "",
                        f'{r["center_t_s"]:.6f}' if r["center_t_s"] is not None else "",
                        f'{r["fit_r2"]:.6f}' if r["fit_r2"] is not None else "",
                        sign_label(r["vel_mm_s"], thr)])


def bin_sign_summary(recs, thr, bin_s=5.0):
    """按 bin_s 秒分箱，统计箱内各符号占比（相对首点时间）。"""
    t0 = next((r["t_s"] for r in recs if r["t_s"] is not None), None)
    bins = {}
    for r in recs:
        if r["vel_mm_s"] is None:
            continue
        t_rel = r["center_t_s"] - t0
        b = int(t_rel // bin_s)
        d = bins.setdefault(b, {"away": 0, "stop": 0, "toward": 0, "n": 0, "vs": []})
        lab = sign_label(r["vel_mm_s"], thr)
        if lab == "远离":
            d["away"] += 1
        elif lab == "靠近":
            d["toward"] += 1
        else:
            d["stop"] += 1
        d["n"] += 1
        d["vs"].append(r["vel_mm_s"])
    out = []
    for b in sorted(bins):
        d = bins[b]
        out.append({"t_start": b * bin_s, "t_end": (b + 1) * bin_s,
                    "away": d["away"], "stop": d["stop"], "toward": d["toward"],
                    "n": d["n"], "v_mean": mean(d["vs"])})
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    indir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "..", "input", "05-超声波")
    indir = os.path.abspath(indir)
    outdir = here

    out = {"label": LABEL, "c": CONST_C, "files": {}}
    reports = {}
    recs_all = {}

    for key, fn in FILES.items():
        path = os.path.join(indir, fn)
        fields, rows = read_rows(path)
        reports[key] = inspect(fn, fields, rows)
        recs, dists, vels = process(path)
        recs_all[key] = recs
        out["files"][key] = {
            "file": fn,
            "seq": [r["seq"] for r in recs],
            "t_s": [r["t_s"] for r in recs],
            "distance_mm": [r["distance_mm"] for r in recs],
            "vel_mm_s": [r["vel_mm_s"] for r in recs],
            "center_t_s": [r["center_t_s"] for r in recs],
            "valid": [1 if r["valid"] else 0 for r in recs],
            "stats": {
                "dist_mean_mm": mean(dists),
                "dist_std_mm": stdev_n1(dists),
                "vel_mean_mm_s": mean(vels),
                "vel_std_mm_s": stdev_n1(vels),
                "n_valid": len(dists),
                "n_vel": len(vels),
            },
        }

    # “停住”阈值：取静止记录 5 点速度样本标准差的 3 倍（严格按其定义，不额外加下限）
    thr = 3.0 * (out["files"]["fixed"]["stats"]["vel_std_mm_s"] or 0.0)
    out["stop_threshold_mm_s"] = thr

    # 写出处理结果 CSV（含符号列）
    write_csv(os.path.join(outdir, "处理结果-固定平面.csv"), recs_all["fixed"], LABEL, thr)
    write_csv(os.path.join(outdir, "处理结果-往返.csv"), recs_all["motion"], LABEL, thr)

    # 远离/停住/靠近：逐点符号段 + 5 秒分箱概览
    out["files"]["fixed"]["segments"] = segments(recs_all["fixed"], thr)
    out["files"]["motion"]["segments"] = segments(recs_all["motion"], thr)
    out["files"]["motion"]["phase_bins"] = bin_sign_summary(recs_all["motion"], thr, 5.0)
    out["files"]["fixed"]["phase_bins"] = bin_sign_summary(recs_all["fixed"], thr, 5.0)

    with open(os.path.join(outdir, "数据包.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, allow_nan=False, separators=(",", ":"))

    # 统计报告
    lines = []
    lines.append("# 第05章 · 超声波历史记录复算 — 统计报告\n")
    lines.append(f"> 数据身份：**{LABEL}**（非本轮新测量）。声速固定 343 m/s，未按当前气温改写历史数据。\n")
    lines.append("## 1. 原始结构与连续性检查\n")
    for key, label in (("fixed", "固定平面 30cm"), ("motion", "往返 远离-停住-靠近")):
        rep = reports[key]
        lines.append(f"### {label}：`{rep['file']}`\n")
        lines.append(f"- 总行数 {rep['n_rows']}；kind 统计 {rep['kinds']}；status 统计 {rep['status']}")
        lines.append(f"- kind=U 行数 {rep['n_U']}，kind=D（温湿度）行数 {rep['n_D']}")
        lines.append(f"- U 序号范围 {rep['seq_first_last'][0]}…{rep['seq_first_last'][1]}；缺号 {len(rep['seq_gaps'])} 处"
                     + (f"：{rep['seq_gaps'][:5]}" if rep["seq_gaps"] else ""))
        lines.append(f"- 板端时间倒退 {len(rep['time_regress'])} 处")
        lines.append(f"- 相邻 t_us 间隔：最小 {rep['dt_us_min']} us，最大 {rep['dt_us_max']} us，"
                     f"平均 {rep['dt_us_mean']:.1f} us")
        lines.append(f"- 用 343 m/s 复算距离与原表 `distance_mm_343` 不一致的点数：{rep['distance_recompute_mismatch']}")
        if "temp_c_min" in rep:
            lines.append(f"- D 行温度范围 {rep['temp_c_min']}~{rep['temp_c_max']} ℃（仅统计，不用于改写历史距离）")
        lines.append("")
    lines.append("## 2. 静态统计（样本标准差用 N-1）\n")
    for key, label in (("fixed", "固定平面 30cm"), ("motion", "往返")):
        s = out["files"][key]["stats"]
        lines.append(f"### {label}\n")
        lines.append(f"- 有效距离点数 {s['n_valid']}：距离均值 {s['dist_mean_mm']:.3f} mm，样本标准差 {s['dist_std_mm']:.4f} mm")
        lines.append(f"- 5 点窗口速度数 {s['n_vel']}：速度均值 {s['vel_mean_mm_s']:.4f} mm/s "
                     f"({s['vel_mean_mm_s']/1000:.6f} m/s)，样本标准差 {s['vel_std_mm_s']:.4f} mm/s")
        lines.append("")
    lines.append(f"## 3. 往返记录 远离/停住/靠近（符号按相对首点时间；停住阈值 = 静止速度样本标准差×3 = {thr:.4f} mm/s）\n")
    lines.append(f"- 逐点符号共切出 {len(out['files']['motion']['segments'])} 个连续同号段（噪声使停住附近频繁翻转）。")
    lines.append("- 下表按 5 秒分箱给出每箱内 远离/停住/靠近 的窗口计数，便于看整体节律：\n")
    lines.append("| 时间箱(s, 相对首点) | 远离 | 停住 | 靠近 | 箱内速度均值(mm/s) |")
    lines.append("|---|---|---|---|---|")
    for b in out["files"]["motion"]["phase_bins"]:
        lines.append(f"| {b['t_start']:.0f}–{b['t_end']:.0f} | {b['away']} | {b['stop']} | {b['toward']} | {b['v_mean']:.3f} |")
    lines.append("")
    lines.append("> 说明：每段/每窗速度都是“5 点窗口最小二乘斜率”，只代表该窗口内的局部变化率，"
                 "**不能**当作任意运动全程的“位移/总时间”平均速度。停住附近速度接近阈值，"
                 "噪声会造成符号频繁翻转，这是原始记录的真实特性。\n")
    lines.append("## 4. 固定平面记录（重复性）\n")
    sf = out["files"]["fixed"]["stats"]
    lines.append(f"- 距离均值 {sf['dist_mean_mm']:.3f} mm，样本标准差 {sf['dist_std_mm']:.4f} mm。")
    lines.append("> 该静止记录只用于检验重复性与计算实现，不能据此声称动态准确度；"
                 "约 30cm 的点距并非精密距离标准，不代表真值精确为 300 mm。\n")

    with open(os.path.join(outdir, "统计报告.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    print("OK. 输出：处理结果-固定平面.csv / 处理结果-往返.csv / 统计报告.md / 数据包.json")
    print(f"stop_threshold_mm_s = {thr:.4f}")
    for key in ("fixed", "motion"):
        s = out["files"][key]["stats"]
        print(key, "dist_mean_mm=%.3f" % s["dist_mean_mm"], "dist_std_mm=%.4f" % s["dist_std_mm"],
              "vel_mean_mm_s=%.4f" % s["vel_mean_mm_s"], "vel_std_mm_s=%.4f" % s["vel_std_mm_s"],
              "n_vel=", s["n_vel"])


if __name__ == "__main__":
    main()
