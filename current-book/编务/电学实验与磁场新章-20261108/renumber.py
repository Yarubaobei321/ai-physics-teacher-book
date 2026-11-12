"""2026-11-08 新增第14—16章（电学实验）、第17章（磁场）：原第14—19章改为第18—23章。
只改正文、05-全书目录和配套包里的章号引用及目录名；前面带“原”“当时为”的历史章号不改。"""
import re,glob,os
from pathlib import Path
M={14:18,15:19,16:20,17:21,18:22,19:23}
root=Path('/Users/yaril/个人文档/3 写作/图书出版/00_这本书的全部进展')
pat=re.compile(r'第(\s*)([0-9][0-9\s、，,和与及]*?)(\s*)章')
def fix_span(m,s):
    pre=s[max(0,m.start()-3):m.start()]
    if pre.endswith('原') or pre.endswith('当时为'): return m.group(0)
    def num(t):
        n=int(t.group(0)); k=M.get(n,n)
        return f"{k:0{len(t.group(0))}d}" if t.group(0).startswith('0') else str(k)
    return '第'+m.group(1)+re.sub(r'\d+',num,m.group(2))+m.group(3)+'章'
def fix(s):
    s=s.replace('第 3—16 章','第 3—20 章')
    s=s.replace('第 1、3—16 章','第 1、3—20 章')
    out=[];last=0
    for m in pat.finditer(s):
        out.append(s[last:m.start()]);out.append(fix_span(m,s));last=m.end()
    out.append(s[last:]);return ''.join(out)
files=[Path(f) for f in glob.glob(str(root/'正文/**/*.md'),recursive=True)]+[root/'05-全书目录.md']
files+=[Path(f) for f in glob.glob(str(root/'配套包/**/*'),recursive=True) if f.endswith(('.md','.html','.csv','.txt','.json','.js','.scad'))]
changed=0
for f in files:
    s=f.read_text(encoding='utf-8'); t=fix(s)
    if t!=s: f.write_text(t,encoding='utf-8'); changed+=1; print('改',f.relative_to(root))
print('files changed',changed)
for base in [root/'正文',root/'配套包']:
    for old in sorted(M,reverse=True):
        for d in sorted(base.glob(f'第{old:02d}章*')):
            new=d.with_name(d.name.replace(f'第{old:02d}章',f'第{M[old]:02d}章',1)); os.rename(d,new); print(d.name,'->',new.name)
