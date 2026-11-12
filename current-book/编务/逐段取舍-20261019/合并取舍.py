"""按取舍页提交的 JSON 合并出唯一现役正文。

用法：python3 合并取舍.py 提交.json [--out 目录]
不带 --out 时先备份现役正文再写回；带 --out 时只把合并结果写到该目录，用于试算。
未选的地方一律保留原稿。
"""
from pathlib import Path
from urllib.parse import unquote
import json, hashlib, re, os, sys, shutil, datetime

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / '取舍数据.json').read_text())


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def relink(block, frm, to):
    """深化稿段落里的本地相对路径，改为相对现役正文目录。"""
    def fix(m):
        url = m.group(2) or m.group(3)
        if re.match(r'^[a-z]+:|^#|^/', url): return m.group(0)
        rel = os.path.relpath((frm / unquote(url)).resolve(), to)
        return m.group(1) + (f'<{rel}>' if m.group(2) is not None or ' ' in rel else rel) + ')'
    return re.sub(r'(\]\()(?:<([^>\n]+)>|([^)\s]+))\)', fix, block)


def merge(chapter, choices):
    src = Path(chapter['source']); deep = Path(chapter['deep'])
    ob, nb, out, tally = chapter['old_blocks'], chapter['new_blocks'], [], {}
    new = lambda j: relink(nb[j], deep.parent, src.parent)
    for r in chapter['rows']:
        default = 'none' if r['kind'] == 'add' else 'old'
        v = 'old' if r['kind'] == 'same' else choices.get(r['id'], default)
        if r['kind'] != 'same': tally[v] = tally.get(v, 0) + 1
        if v in ('old', 'both'): out += [ob[i] for i in r['old']]
        if v in ('new', 'both'): out += [new(j) for j in r['new']]
    return '\n\n'.join(out) + '\n', tally


def main():
    sub = json.loads(Path(sys.argv[1]).read_text())
    assert sub['build'] == DATA['build'], '提交文件与当前取舍页版本不一致'
    outdir = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else None
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    log = [f'# 逐段取舍合并记录 {stamp}', '', f'提交文件：`{sys.argv[1]}`', '', '|章|用原稿|用深化稿|两段都要|都不要|合并前 SHA256|合并后 SHA256|', '|---|---:|---:|---:|---:|---|---|']
    for ch in DATA['chapters']:
        src = Path(ch['source'])
        assert sha(src) == ch['source_sha256'], f'第{ch["chapter"]}章现役正文在取舍期间被改过，停止合并'
        text, t = merge(ch, sub['choices'])
        if outdir:
            outdir.mkdir(parents=True, exist_ok=True); (outdir / f'第{ch["chapter"]:02d}章.md').write_text(text); continue
        before = sha(src)
        if text != src.read_text():
            bk = HERE / f'合并前备份-{stamp}' / src.parent.name; bk.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, bk / src.name); src.write_text(text)
        log.append(f'|{ch["chapter"]}|{t.get("old",0)}|{t.get("new",0)}|{t.get("both",0)}|{t.get("none",0)}|`{before[:12]}`|`{sha(src)[:12]}`|')
    if not outdir:
        (HERE / f'合并记录-{stamp}.md').write_text('\n'.join(log) + '\n'); print('\n'.join(log))


if __name__ == '__main__':
    main()
