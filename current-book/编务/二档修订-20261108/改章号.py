"""把仍用旧章号的源稿改成新章号。链接目标里的路径不动；配套包路径单独映射。
指向已移出章节的引用改成【原第N章】，留待手改。用法：python 改章号.py 文件...
"""
import re, sys
from pathlib import Path

MAP = {1: 2, 2: 3, 3: 4, 4: 4, 6: 5, 7: 6, 8: 7, 9: 8, 10: 9, 11: 10, 12: 11, 14: 12, 15: 12,
       17: 13, 19: 14, 21: 15, 22: 16, 23: 1}
GONE = {5, 13, 16, 18, 20}


def expand(spec):
    nums = []
    for part in re.split(r"\s*、\s*", spec):
        m = re.match(r"(\d+)\s*[—–-]\s*(\d+)$", part.strip())
        if m:
            nums += list(range(int(m.group(1)), int(m.group(2)) + 1))
        else:
            nums.append(int(part))
    return nums


def fmt(nums):
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(f"{nums[i]}—{nums[j]}" if j - i >= 2 else "、".join(str(n) for n in nums[i:j + 1]))
        i = j + 1
    return "、".join(out)


def convert(text):
    keep = []

    def hold(m):
        keep.append(m.group(0)); return f"\x00{len(keep)-1}\x00"
    text = re.sub(r"\]\([^)]*\)", hold, text)          # 链接目标原样保留

    def pkg(m):
        n = int(m.group(1))
        if n in GONE:
            return f"配套包/【原第{n:02d}章】"
        return f"配套包/第{MAP[n]:02d}章"
    text = re.sub(r"配套包/第(\d\d)章", pkg, text)
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
    text = re.sub(r"(?<![/\w])第 ?(\d+(?:\s*[、—–-]\s*\d+)*) ?章", ch, text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], text)
    return text, flags


if __name__ == "__main__":
    for f in sys.argv[1:]:
        p = Path(f)
        t, flags = convert(p.read_text(encoding="utf-8"))
        p.write_text(t, encoding="utf-8")
        print(p.parent.name if p.name == "正文.md" else p.name, len(flags), flags[:6])
