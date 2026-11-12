"""手改辅助：按小标题替换一节的正文，或替换一段原文。"""
import re
from pathlib import Path

BOOK = Path(__file__).resolve().parents[2]
SRC = BOOK / "正文"


def chapter(key):
    if key.startswith("附录"):
        return next((SRC / "附录").glob(key + "*.md"))
    if key in ("序言", "前言", "结语"):
        return next(SRC.glob(key + "-*")) / "正文.md"
    return next(SRC.glob(key + "-*")) / "正文.md"


def body(key, heading, new, whole=False):
    """替换小标题下的正文。whole=False 时到下一个任意级小标题为止；True 时连同下级小节一起替换。"""
    p = chapter(key)
    lines = p.read_text(encoding="utf-8").split("\n")
    idx = [i for i, l in enumerate(lines) if re.match(r"^#{2,4} ", l) and heading in l]
    assert len(idx) == 1, (key, heading, idx)
    i = idx[0]
    lvl = len(re.match(r"^(#+)", lines[i]).group(1))
    j = i + 1
    while j < len(lines):
        m = re.match(r"^(#{1,4}) ", lines[j])
        if m and (not whole or len(m.group(1)) <= lvl):
            break
        j += 1
    out = lines[: i + 1] + [""] + new.strip("\n").split("\n") + [""] + lines[j:]
    p.write_text(re.sub(r"\n{3,}", "\n\n", "\n".join(out)), encoding="utf-8")


def heading(key, old, new):
    p = chapter(key)
    t = p.read_text(encoding="utf-8")
    assert t.count(old) == 1, (key, old, t.count(old))
    p.write_text(t.replace(old, new), encoding="utf-8")


def sub(key, old, new, count=1):
    p = chapter(key)
    t = p.read_text(encoding="utf-8")
    n = t.count(old)
    assert n == count, (key, old[:40], n)
    t = t.replace(old, new)
    p.write_text(re.sub(r"\n{3,}", "\n\n", t), encoding="utf-8")


def show(key, heading, whole=False):
    p = chapter(key)
    lines = p.read_text(encoding="utf-8").split("\n")
    i = next(i for i, l in enumerate(lines) if re.match(r"^#{2,4} ", l) and heading in l)
    lvl = len(re.match(r"^(#+)", lines[i]).group(1))
    j = i + 1
    while j < len(lines):
        m = re.match(r"^(#{1,4}) ", lines[j])
        if m and (not whole or len(m.group(1)) <= lvl):
            break
        j += 1
    return "\n".join(lines[i:j])
