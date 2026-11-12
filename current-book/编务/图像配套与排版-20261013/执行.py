from pathlib import Path
import shutil,hashlib,json
P=Path('/Users/yaril/个人文档/3 写作/图书出版/00_这本书的全部进展')
R=P/'编务/图像配套与排版-20261013'
S=P/'编务/实操补全-20261009/实操'
B=R/'修改前'; B.mkdir(exist_ok=True)
def save(p):
    p=Path(p); rel=p.relative_to(P) if p.is_relative_to(P) else Path('外部原件')/str(p).lstrip('/')
    q=B/rel
    if not q.exists():
        q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
        with (R/'修改前指纹.jsonl').open('a') as f:f.write(json.dumps({'path':str(p),'backup':str(q),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()},ensure_ascii=False)+'\n')
def edit(p,changes):
    p=Path(p);t=p.read_text();old=t
    for a,b in changes:
        if a not in t: raise ValueError(f'未找到 {p}: {a}')
        t=t.replace(a,b)
    if t!=old: save(p);p.write_text(t)
if __name__=='__main__':
    for p in [*P.glob('正文/**/*.md'),P/'PROJECT_SUMMARY.md',P/'全书排版稿.docx',P/'全书排版稿.pdf',P/'全书阅读.html']:
        save(p)
    edit(P/'正文/第07章-验证机械能守恒/正文.md',[
      ('学生做完实验，把数据录入网页，再用平板连接投影仪展示。','学生做完实验，把数据手动录入网页，再用平板连接投影仪展示。'),
      ('DIS 机械能实验器（网页装置图上，金属圆柱体固定在摆杆末端，从不同高度摆下）','DIS 机械能实验器（摆锤固定在摆杆末端，从不同高度摆下）'),
      ('照这张图，圆柱体是随摆杆一起摆动，不是在曲面上滚动，解释和装置对不上。课上用哪种装置，解释就要按哪种装置写；用的是这种摆式装置，就不能搬用沿曲面滚动的说法。','公开课使用的正是这种摆锤装置：圆柱体随摆杆一起摆动，并不在曲面上滚动。网页的解释和实际装置对不上，应按摆锤装置分析能量变化。')])
    p=P/'正文/第04章-光电门测速/正文.md'
    t=p.read_text()
    print('\n'.join(x for x in t.splitlines() if '公开课' in x))
    p=P/'正文/第01章-准备好工作区/正文.md'
    print('\n'.join(x for x in p.read_text().splitlines() if '官方网站' in x))
