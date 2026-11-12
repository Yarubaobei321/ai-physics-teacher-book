"""补漏：第一遍的正则把前面紧挨汉字的“第 N 章”跳过了（Python 的 \\w 含汉字）。
这些位置仍是旧章号；本脚本只改它们，第一遍已改的位置（前面是空格、标点或行首）不动。"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from 改章号 import MAP, GONE, expand, fmt

def convert(text):
    keep = []
    text = re.sub(r"\]\([^)]*\)", lambda m: (keep.append(m.group(0)), f"\x00{len(keep)-1}\x00")[1], text)
    flags = []
    def ch(m):
        nums = expand(m.group(1))
        gone = [n for n in nums if n in GONE]
        new = [MAP[n] for n in nums if n in MAP]
        if gone:
            flags.append((m.group(0), gone))
        if not new:
            return f"【原{m.group(0)}】"
        s = f"第 {fmt(new)} 章"
        if gone:
            s += "【含已移出章：" + "、".join(map(str, gone)) + "】"
        return s
    text = re.sub(r"(?<=[^\W\d_])第 ?(\d+(?:\s*[、—–-]\s*\d+)*) ?章", ch, text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], text)
    return text, flags

for f in sys.argv[1:]:
    p = Path(f); t, flags = convert(p.read_text(encoding="utf-8")); p.write_text(t, encoding="utf-8")
    print(p.parent.name if p.name == "正文.md" else p.name, flags)
