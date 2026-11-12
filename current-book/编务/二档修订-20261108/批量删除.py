"""二档修订第一步：按审阅方案做整节删除、框架块与读者契约段删除、删图。
只处理比例为 1 的整节；部分压缩另行手改。删下的原文逐条存到“移出段落/”，可随时取回。
"""
import re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOOK = HERE.parents[1]
sys.path.insert(0, str(BOOK / "编务/全书审阅-20261108"))
from 审阅方案 import PLAN, TIER_B, GLOBAL_B  # noqa: E402

SKIP = {"第05章", "第13章", "第16章", "第18章", "第20章", "第23章"}   # 移出或整章重写
KEEP_TEACHING = {"第09章"}   # 完整教学设计（教学目标、板书）保留一处：静电课
CONTRACT = re.compile(r"^(读者想知道|读者会问|读者关心的是|读这一章的老师|第一次用 AI 的老师|读者想)")
OUTDIR = HERE / "移出段落"
OUTDIR.mkdir(exist_ok=True)


def targets():
    for p in sorted((BOOK / "正文").glob("第??章-*")):
        yield p.name[:4], p / "正文.md"
    for key, pat in [("序言", "序言-*"), ("前言", "前言-*"), ("结语", "结语-*")]:
        for p in (BOOK / "正文").glob(pat):
            yield key, p / "正文.md"
    for p in sorted((BOOK / "正文/附录").glob("附录*.md")):
        yield p.name[:3], p


def full_cuts(key):
    plan, pb = PLAN.get(key, {}), TIER_B.get(key, {})
    cuts = [(s, lab) for s, f, lab in plan.get("secs", []) if f >= 1]
    cuts += [(s, lab) for s, f, lab in pb.get("secs", []) if f >= 1]
    for s, f, lab in GLOBAL_B:
        if key in KEEP_TEACHING and s in ("教学目标", "板书"):
            continue
        cuts.append((s, lab))
    imgs = [s for s, why in plan.get("imgs", []) if not why.startswith("保留")] + [s for s, _ in pb.get("imgs", [])]
    return cuts, imgs


report = []
for key, path in targets():
    if key in SKIP:
        continue
    lines = path.read_text(encoding="utf-8").split("\n")
    cuts, imgs = full_cuts(key)
    keep = [True] * len(lines)
    removed = []
    i = 0
    while i < len(lines):
        m = re.match(r"^(#{2,4}) (.*)", lines[i])
        if m:
            lvl, htxt = len(m.group(1)), m.group(2)
            hit = next(((s, lab) for s, lab in cuts if s in htxt), None)
            if hit:
                j = i + 1
                while j < len(lines):
                    m2 = re.match(r"^(#{1,4}) ", lines[j])
                    if m2 and len(m2.group(1)) <= lvl:
                        break
                    j += 1
                for k in range(i, j):
                    keep[k] = False
                removed.append((f"整节：{htxt}（{hit[1]}）", lines[i:j]))
                i = j
                continue
        if lines[i].startswith("> **本章在框架中的位置**"):
            j = i
            while j < len(lines) and lines[j].startswith(">"):
                j += 1
            for k in range(i, j):
                keep[k] = False
            removed.append(("框架块", lines[i:j]))
            i = j
            continue
        if CONTRACT.match(lines[i].strip()) and (i == 0 or not lines[i - 1].strip()):
            keep[i] = False
            removed.append(("读者契约段", [lines[i]]))
        mm = re.match(r"^!\[[^\]]*\]\(([^)]+)\)", lines[i].strip())
        if mm and any(s in Path(mm.group(1)).name for s in imgs):
            keep[i] = False
            removed.append(("删图", [lines[i]]))
        i += 1
    new = [l for l, k in zip(lines, keep) if k]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(new)).rstrip() + "\n"
    if removed:
        out = [f"# {key} 删下的原文（{path.relative_to(BOOK)}）\n"]
        for lab, seg in removed:
            out.append(f"## 【{lab}】\n\n" + "\n".join(seg).strip() + "\n")
        (OUTDIR / f"{key}.md").write_text("\n".join(out), encoding="utf-8")
        path.write_text(text, encoding="utf-8")
    report.append((key, len(removed), sum(1 for l, _ in removed if l == "删图")))
for r in report:
    print(*r)
