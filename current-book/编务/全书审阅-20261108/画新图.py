"""全书审阅（2026-11-08）新增配图。数据全部取自书稿正文，不新增测量。
运行：/opt/anaconda3/bin/python 画新图.py
"""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "新图"
OUT.mkdir(exist_ok=True)
BOOK = Path(__file__).resolve().parents[2]

FONT = "'PingFang SC','Songti SC','Noto Sans CJK SC',sans-serif"
INK, INK2, MUTED, GRID = "#1f1f1d", "#52514e", "#8a8984", "#e4e3df"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"   # 参考调色板前三位


def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'font-family="{FONT}" role="img" aria-label="{title}">'
            f'<title>{title}</title><rect width="{w}" height="{h}" fill="#ffffff"/>{body}</svg>')


def text(x, y, s, size=14, fill=INK, anchor="start", weight="normal"):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>'


def line(x1, y1, x2, y2, stroke=GRID, w=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{w}"{d}/>'


def poly(pts, stroke, w=2, dash=None, fill="none"):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<polyline points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"{d}/>'


def dot(x, y, fill, r=4.5):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="#fff" stroke-width="2"/>'


# ---------- F1 区间取舍：第 3 章遮光片宽度表 ----------
def fig_tradeoff():
    W, H = 760, 440
    L, R, T, B = 80, 600, 50, 340
    d = [4.0, 2.0, 1.0, 0.5]
    bias = [3.9, 2.0, 1.0, 0.5]
    unc = [0.5, 1.0, 2.1, 4.1]
    lx = lambda v: L + (math.log2(4.0) - math.log2(v)) / (math.log2(4.0) - math.log2(0.5)) * (R - L)
    ly = lambda p: B - p / 4.5 * (B - T)
    b = []
    for p in [0, 1, 2, 3, 4]:
        b += [line(L, ly(p), R, ly(p)), text(L - 10, ly(p) + 5, f"{p}%", 13, MUTED, "end")]
    for v in d:
        b += [line(lx(v), B, lx(v), B + 5, MUTED), text(lx(v), B + 22, f"{v:g} cm", 13, INK2, "middle")]
    b.append(line(L, B, R, B, MUTED))
    b.append(text((L + R) / 2, B + 46, "遮光片宽度 d（越往右越窄，区间越短）", 14, INK2, "middle"))
    b.append(text(L, T - 22, "两种误差随遮光片宽度变化（第 3 章构造算例：v₀ = 0.50 m/s，a = 0.50 m/s²）", 14, INK, weight="bold"))
    b.append(poly([(lx(v), ly(p)) for v, p in zip(d, bias)], S1))
    b.append(poly([(lx(v), ly(p)) for v, p in zip(d, unc)], S2, dash="7 5"))
    b += [dot(lx(v), ly(p), S1) for v, p in zip(d, bias)]
    b += [dot(lx(v), ly(p), S2) for v, p in zip(d, unc)]
    # 交叉带
    b.append(f'<rect x="{lx(2.0):.1f}" y="{T}" width="{lx(1.0)-lx(2.0):.1f}" height="{B-T}" fill="#2a78d6" opacity="0.07"/>')
    b.append(text((lx(2.0) + lx(1.0)) / 2, T + 18, "两者相当：1—2 cm", 13, INK2, "middle"))
    b.append(text(R + 12, ly(0.5) + 4, "平均速度偏离", 13, INK))
    b.append(text(R + 12, ly(0.5) + 21, "前缘速度（实线）", 13, INK2))
    b.append(text(R + 12, ly(4.1) + 4, "宽度与计时的", 13, INK))
    b.append(text(R + 12, ly(4.1) + 21, "相对不确定度（虚线）", 13, INK2))
    b.append(text(L, H - 10, "同一个取舍还出现在：超声波测速的五点拟合窗口、第 5 章电梯曲线的滤波截止频率——区间越短越接近“瞬时”，噪声也越大。", 13, INK2))
    (OUT / "F1-区间取舍-遮光片宽度.svg").write_text(svg(W, H, "".join(b), "遮光片宽度与两种误差"), encoding="utf-8")


# ---------- F2 电梯下降：运动阶段—加速度—视重 ----------
def fig_elevator():
    W, H = 800, 540
    L, R = 150, 700
    t1, t2, t3 = 0.33, 1.83, 2.16
    tx = lambda t: L + (t + 0.3) / (t3 + 0.6) * (R - L)
    rows = [("速度 v / (m·s⁻¹)", 70, 190, (-0.8, 0.2)),
            ("加速度 a / (m·s⁻²)", 225, 335, (-2.6, 2.6)),
            ("视重 F / N", 370, 480, (0.30, 0.60))]
    b = [text(L, 30, "一次“电梯下降”：三段运动，三种视重（第 5 章实测估读值，取竖直向上为正）", 14, INK, weight="bold")]
    for x0, x1, lab, col in [(0, t1, "向下加速 · 失重", "#2a78d6"), (t1, t2, "匀速下降 · 视重 = mg", "#8a8984"),
                             (t2, t3, "向下减速 · 超重", "#eb6834")]:
        b.append(f'<rect x="{tx(x0):.1f}" y="45" width="{tx(x1)-tx(x0):.1f}" height="445" fill="{col}" opacity="0.06"/>')
        b.append(text((tx(x0) + tx(x1)) / 2, 58, lab, 12, INK2, "middle"))
    series = {
        0: [(-0.3, 0), (0, 0), (t1, -0.66), (t2, -0.66), (t3, 0), (t3 + 0.3, 0)],
        1: [(-0.3, 0), (0, 0), (0, -2), (t1, -2), (t1, 0), (t2, 0), (t2, 2), (t3, 2), (t3, 0), (t3 + 0.3, 0)],
        2: [(-0.3, .447), (0, .447), (0, .36), (t1, .36), (t1, .447), (t2, .447), (t2, .54), (t3, .54), (t3, .447), (t3 + .3, .447)],
    }
    refs = {0: [(0, "0")], 1: [(0, "0"), (-2, "−2"), (2, "+2")], 2: [(0.447, "0.447 = mg"), (0.36, "0.36"), (0.54, "0.54")]}
    for i, (lab, top, bot, (lo, hi)) in enumerate(rows):
        yy = lambda v: bot - (v - lo) / (hi - lo) * (bot - top)
        b.append(text(L - 12, (top + bot) / 2, lab, 12, INK2, "end"))
        for v, s in refs[i]:
            b += [line(L, yy(v), R, yy(v), GRID, 1, "3 3"), text(R + 4, yy(v) + 4, s, 11, MUTED)]
        b.append(poly([(tx(t), yy(v)) for t, v in series[i]], [S1, INK, S2][i], 2.4))
    for t, s in [(0, "0"), (t1, "0.33 s"), (t2, "1.83 s"), (t3, "2.16 s")]:
        b += [line(tx(t), 480, tx(t), 486, MUTED), text(tx(t), 502, s, 11, INK2, "middle")]
    b.append(text(L, 532, "速度一直向下；视重却经历小于、等于、大于 mg 三段。判断超重失重看加速度方向，不看速度方向。", 12, INK2))
    (OUT / "F2-电梯下降三段.svg").write_text(svg(W, H + 10, "".join(b), "电梯下降的速度、加速度与视重"), encoding="utf-8")


# ---------- F3 采样混叠：147 r/min，每秒 10 点 ----------
def fig_alias():
    W, H = 780, 360
    L, R, T, B = 60, 740, 60, 290
    T_rev = 60 / 147
    c = 1.5
    eps = lambda t: math.sin(2 * math.pi * t / T_rev) * math.exp(c * (math.cos(2 * math.pi * t / T_rev) - 1))
    peak = max(eps(i / 2000) for i in range(2000))
    tmax = 6.0
    X = lambda t: L + t / tmax * (R - L)
    Y = lambda v: (T + B) / 2 - v / peak * (B - T) / 2 * 0.95
    b = [text(L, 28, "每秒只采 10 个点时，峰值为什么一会儿高一会儿低（第 13 章，147 r/min）", 14, INK, weight="bold"),
         text(L, 47, "浅色：按模型连续变化的电动势（形状示意，振幅归一）；深色折线：每 0.1 s 采一点再连线", 12, INK2)]
    b += [line(L, Y(0), R, Y(0), MUTED)]
    for s in range(7):
        b += [line(X(s), B, X(s), B + 5, MUTED), text(X(s), B + 20, f"{s} s", 11, INK2, "middle")]
    cont = [(X(i / 400 * tmax), Y(eps(i / 400 * tmax))) for i in range(401)]
    cont = [(X(i * tmax / 3000), Y(eps(i * tmax / 3000))) for i in range(3001)]
    b.append(poly(cont, "#b9cff0", 1.2))
    samp = [(X(k * 0.1), Y(eps(k * 0.1))) for k in range(61)]
    b.append(poly(samp, S1, 2))
    b += [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{S1}"/>' for x, y in samp]
    # 包络标注
    b.append(text(R, T - 4, "采样点每圈后移 0.008 s，约 5 s 轮回一次", 12, INK2, "end"))
    b.append(line(X(0.25), T + 12, X(5.35), T + 12, MUTED, 1, "4 3"))
    b.append(text(L, H - 22, "一圈 0.408 s 只分到 4 个点：读到的“峰值”是采样点中的最大值，是真峰值的下限。", 12, INK2))
    b.append(text(L, H - 6, "检验办法：把采样率调到每秒 100 点重测一组，起伏若消失，就是采样造成的。", 12, INK2))
    (OUT / "F3-采样混叠-147转.svg").write_text(svg(W, H + 8, "".join(b), "采样混叠示意"), encoding="utf-8")


# ---------- F4 核查路线（替换第 2 章 AI 概念图） ----------
def fig_check():
    W, H = 760, 388
    def box(x, y, w, h, title, sub, col=INK):
        return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#fff" stroke="{col}" stroke-width="1.6"/>'
                + text(x + w / 2, y + 24, title, 14, INK, "middle", "bold")
                + "".join(text(x + w / 2, y + 44 + 17 * i, s, 11.5, INK2, "middle") for i, s in enumerate(sub)))
    def arrow(x1, y1, x2, y2):
        return (line(x1, y1, x2, y2, INK2, 1.6) +
                f'<path d="M{x2},{y2} l-8,-4 v8 z" fill="{INK2}" transform="rotate({math.degrees(math.atan2(y2-y1,x2-x1)):.1f} {x2} {y2})"/>')
    b = [text(20, 28, "拿到 AI 交来的资源：先有预期，再看证据，对不上时追查", 15, INK, weight="bold")]
    b.append(box(20, 50, 200, 100, "① 先写下预期", ["用高中物理算一个关键状态", "例：圆弧轨道最高点 1 m/s、0.6 m"]))
    b.append(box(280, 50, 200, 100, "② 实际运行取证", ["在浏览器里操作、打印、量", "不抄 AI 的“检查通过”"]))
    b.append(box(540, 50, 200, 100, "③ 并排比较", ["原始条件 · 独立预期", "实际结果 · 怎样查的"]))
    b += [arrow(220, 100, 278, 100), arrow(480, 100, 538, 100)]
    b.append(box(540, 200, 200, 90, "一致", ["留下可复核的记录", "（第 3 章检查表）"], S3))
    b.append(box(220, 200, 280, 140, "不一致：先查最早的一环", ["输入进没进计算？（第 16 章 P22）", "算法用了哪些数据？（第 2 章 1.500/1.467）",
                                                         "报告和画面是同一份数据吗？（第 7 章）", "结果在物理上可能吗？（第 10 章 10.21 V > 9.3 V）",
                                                         "测量本身可信吗？（第 9 章 端电压）"], S2))
    b += [arrow(640, 150, 640, 198), arrow(600, 150, 470, 198)]
    b.append(box(20, 230, 160, 110, "一次只改一件事", ["改前存旧版", "用同样参数复查", "也看没打算改的地方"]))
    b.append(arrow(220, 285, 182, 285))
    b.append(line(100, 230, 100, 160, INK2, 1.6, "5 4"))
    b.append(text(108, 196, "回到 ①", 11.5, INK2))
    b.append(text(20, 380, "两个 AI 意见一致也可能一起错（第 3 章：都把拟合与逐差叫作“两个独立估计”）；裁决在教师。", 12, INK2))
    (OUT / "F4-核查路线.svg").write_text(svg(W, H + 6, "".join(b), "物理审核的路线"), encoding="utf-8")


# ---------- F5 全书地图（替换《开始之前》AI 概念图） ----------
def fig_map():
    chapters = [("1", "教学主张"), ("2", "纸带记录页"), ("3", "物理审核"), ("4", "传感器测速"), ("5", "超重失重"), ("6", "机械能"),
                ("7", "动量模型"), ("8", "静电"), ("9", "水槽测电势"), ("10", "电势地形"), ("11", "电路拼图"), ("12", "电学实验"),
                ("13", "电磁感应"), ("14", "三维模型"), ("15", "学情诊断"), ("16", "学生作品")]
    carriers = ["自制教具与实物实验", "数据与数字化实验", "模拟与交互网页", "学生作品与作答"]
    m = {0: [], 1: [0, 1], 2: [], 3: [0, 1], 4: [0, 1], 5: [1], 6: [2], 7: [0, 2], 8: [0], 9: [2], 10: [0, 1], 11: [2],
         12: [0, 1, 2], 13: [0, 2], 14: [3], 15: [3]}
    real = {4, 5, 7, 8, 12}   # 有完整真实课例
    W, H = 720, 380
    L, T, cw, rh = 170, 150, 33, 40
    b = [text(20, 28, "全书地图：每章用到哪类载体", 15, INK, weight="bold"),
         text(20, 48, "实心 = 有真实上过的完整课例；空心 = 有资源和课堂用法、无完整课例；第 1、3 章贯穿各类载体", 12, INK2)]
    for j, (n, name) in enumerate(chapters):
        x = L + j * cw + cw / 2
        b.append(text(x, T + 4 * rh + 8, n, 12, INK, "middle", "bold"))
        b.append(f'<text x="{x-4:.1f}" y="{T-6}" font-size="11" fill="{INK2}" text-anchor="start" transform="rotate(-55 {x-4:.1f} {T-6})">{name}</text>')
    for i, cname in enumerate(carriers):
        y = T + i * rh + rh / 2
        b.append(line(L, y, L + len(chapters) * cw, y, GRID))
        b.append(text(L - 10, y + 5, cname, 12.5, INK, "end"))
        for j in range(len(chapters)):
            if i in m[j]:
                x = L + j * cw + cw / 2
                col = [S1, S2, S3, "#4a3aa7"][i]
                b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{col if j in real else "#fff"}" stroke="{col}" stroke-width="2"/>')
    y0 = T + 4 * rh + 22
    for k, (a, z, lab) in enumerate([(0, 0, "主张"), (1, 2, "起步"), (3, 4, "运动与相互作用"), (5, 5, "机械能"), (6, 6, "动量"), (7, 9, "静电场"),
                                     (10, 11, "电路"), (12, 12, "电磁感应"), (13, 15, "资源与评价")]):
        x1, x2 = L + a * cw + 3, L + (z + 1) * cw - 3
        b.append(f'<rect x="{x1:.1f}" y="{y0}" width="{x2-x1:.1f}" height="6" rx="3" fill="{["#c9c8c2","#a9a8a2"][k%2]}"/>')
        b.append(text((x1 + x2) / 2, y0 + 22 + (k % 2) * 14, lab, 11, INK2, "middle"))
    (OUT / "F5-全书地图.svg").write_text(svg(W, H, "".join(b), "全书地图"), encoding="utf-8")


# ---------- F6 第 11 章水槽移板四格合一 ----------
def fig_composite():
    src = BOOK / "正文/第10章-从等势线到电势地形/assets"
    names = ["水槽演示-1-移板前-3.60V.jpg", "水槽演示-2-负极板移近-2.48V.jpg", "水槽演示-3-负极板再移近-1.19V.jpg", "水槽演示-4-正极板移近-6.51V.jpg"]
    labels = ["① 移板前 3.60 V", "② 负极板移近一档 2.48 V", "③ 负极板再移近 1.19 V", "④ 改移正极板 6.51 V"]
    ims = [Image.open(src / n).convert("RGB") for n in names]
    w = 1200
    ims = [im.resize((w, int(im.height * w / im.width))) for im in ims]
    h = ims[0].height
    pad, lab = 16, 56
    sheet = Image.new("RGB", (2 * w + 3 * pad, 2 * (h + lab) + 3 * pad), "white")
    try:
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 40)
    except OSError:
        font = ImageFont.load_default()
    d = ImageDraw.Draw(sheet)
    for i, (im, s) in enumerate(zip(ims, labels)):
        x = pad + (i % 2) * (w + pad)
        y = pad + (i // 2) * (h + lab + pad)
        d.text((x, y + 4), s, fill=(30, 30, 30), font=font)
        sheet.paste(im, (x, y + lab))
    sheet.save(OUT / "F6-水槽移板四格合一.jpg", quality=88)


# ---------- F7 力传感器信号链（第 5 章移出后，放进超重失重一章） ----------
def fig_chain():
    W, H = 760, 170
    steps = [("力 F", "托盘受压"), ("形变", "金属梁微弯"), ("电阻变化", "应变片一增一减"), ("几毫伏", "电桥输出"), ("原始计数 N", "HX711 放大、转换"), ("F = k(N − N₀)", "零点 + 比例")]
    b = [text(20, 26, "自制压力传感器的信号链：哪一步出错，屏幕都照样有读数", 14, INK, weight="bold")]
    bw, gap, y = 106, 18, 50
    for i, (a, s) in enumerate(steps):
        x = 20 + i * (bw + gap)
        col = S2 if i == 5 else S1
        b.append(f'<rect x="{x}" y="{y}" width="{bw}" height="66" rx="8" fill="#fff" stroke="{col}" stroke-width="1.6"/>')
        b.append(text(x + bw / 2, y + 28, a, 13.5, INK, "middle", "bold"))
        b.append(text(x + bw / 2, y + 50, s, 11, INK2, "middle"))
        if i < 5:
            b.append(line(x + bw + 2, y + 33, x + bw + gap - 3, y + 33, INK2, 1.6))
    b.append(text(20, 145, "标定只定两个数：空载取 N₀，放已知砝码求 k；再用没参与标定的砝码检验，读数报告到哪一位由波动决定。", 12, INK2))
    (OUT / "F7-力传感器信号链.svg").write_text(svg(W, H, "".join(b), "力传感器信号链"), encoding="utf-8")


if __name__ == "__main__":
    for f in [fig_tradeoff, fig_elevator, fig_alias, fig_check, fig_map, fig_composite, fig_chain]:
        f()
    print(sorted(p.name for p in OUT.iterdir()))
