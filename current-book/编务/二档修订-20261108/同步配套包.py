from pathlib import Path
import shutil,re,base64,json,hashlib,zipfile,html
from urllib.parse import unquote,urlsplit
from bs4 import BeautifulSoup
import markdown
p=Path('/Users/yaril/个人文档/3 写作/图书出版/00_这本书的全部进展');c=p/'配套包';w=p/'编务/二档修订-20261108';b=w/'配套更新前';b.mkdir(exist_ok=True)
for n in ['开始阅读.md','开始阅读.html']:
 if not (b/n).exists():shutil.copy2(c/n,b/n)
if (p/'随书配套包.zip').exists() and not (b/'随书配套包.zip').exists():shutil.copy2(p/'随书配套包.zip',b/'随书配套包.zip')
style='''body{max-width:1020px;margin:auto;padding:32px 25px;background:#fffefa;color:#263e42;font:17px/1.85 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}h1{font-size:31px}h2{margin-top:38px;color:#155f63}a{color:#166c77}img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #d3dedb;padding:9px;vertical-align:top}th{background:#eaf3ef}code{overflow-wrap:anywhere}li{margin:5px 0}@media(max-width:700px){table{display:block;overflow-x:auto}}'''
def page(title,body):return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>'+style+'</style></head><body>'+body+'</body></html>'
def render(s):return markdown.markdown(s,extensions=['tables','fenced_code'])
# 序言文字与图片直接取现役源稿，离线HTML同时嵌入图像。
src=p/'正文/序言-不会编程的物理老师能用AI做成什么';s=(src/'正文.md').read_text();assets=c/'序言配图';assets.mkdir(exist_ok=True)
for target in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',s):
 f=src/target;shutil.copy2(f,assets/f.name);s=s.replace(']('+target+')','](序言配图/'+f.name+')')
(c/'序言.md').write_text(s);body=render(s)
for f in assets.iterdir():
 mime='image/png' if f.suffix=='.png' else 'image/jpeg';body=body.replace('序言配图/'+f.name,'data:'+mime+';base64,'+base64.b64encode(f.read_bytes()).decode())
(c/'序言.html').write_text(page('序言｜不会编程的物理老师，能用AI做成什么',body))
shutil.copy2(p/'编务/电容器习题课-视频补充-20261015/电势变化-电表放大.html',c/'第10章/电势变化-电表放大.html')
# 包内索引沿用现役附录D，并增加本次附入的材料。
s=(w/'配套文件索引-源.md').read_text();s=s.replace('本地阅读版：[打开随书配套包](../../随书配套包.zip)。','你正在浏览的这个文件夹就是随书配套包。');s+='\n\n## 本包阅读入口\n\n- [序言](序言.html)\n- [全书提示词（按章）](全书提示词（按章）.md)\n- [极板移动前后的电势变化](第10章/电势变化-电表放大.html)：四个测量节点，原电表局部放大、变化数值与物理解释。\n- [按16章浏览配套材料](开始阅读.html)。\n'
(c/'配套文件索引.md').write_text(s)
body=render(s)
for node in BeautifulSoup(body,'html.parser').find_all('code'):
 t=node.get_text();f=c/t.removeprefix('配套包/')
 if t.startswith('配套包/') and f.exists():body=body.replace(str(node),'<a href="'+html.escape(t.removeprefix('配套包/'),quote=True)+'">'+str(node)+'</a>')
(c/'配套文件索引.html').write_text(page('配套文件和网页索引｜16章',body))
intro='''# 随书配套材料

本包对应 2026 年 11 月修订后的 16 章正文。先解压整个文件夹，再打开本页。各章材料按现行章号排列。

- [阅读序言（含配图）](序言.html)
- [查看用途、数据性质与打开方法](配套文件索引.html)
- [全书提示词（按章）](全书提示词（按章）.md)
- [极板移动前后的电势变化：电表放大版](第10章/电势变化-电表放大.html)

单文件网页可用 Chrome 或 Edge 打开。第7章课堂示例保留整个文件夹的目录关系。连接蓝牙或USB时须使用实际设备与相应浏览器权限。

实测、历史记录、构造数据与模型计算在各页或说明中标明。第10章自动候选点仍需逐点核对；第14章圆环练习模型尚未完成实体打印与入水验证。

'''
for i in range(1,17):
 chapter=next((p/'正文').glob(f'第{i:02d}章-*'));title=(chapter/'正文.md').read_text().splitlines()[0].lstrip('# ').strip();intro+='\n## '+title+'\n\n'
 for f in sorted((c/f'第{i:02d}章').rglob('*')):
  if f.is_file() and not f.name.startswith('.'):
   rel=f.relative_to(c).as_posix();label=f.relative_to(c/f'第{i:02d}章').as_posix();intro+=f'- [{label}]({rel})\n'
 if not (c/f'第{i:02d}章').exists():intro+='本章没有配套文件。\n'
intro+='\n## 打开方式与阅读顺序\n\n第2、3章用于起步与审核；想先看模型和实验，可从第7、8、9章进入。按教材进度选择案例时，结合《开始之前》的对照表。\n'
(c/'开始阅读.md').write_text(intro);(c/'开始阅读.html').write_text(page('随书配套材料｜16章',render(intro)))
# 检查所有本地HTML资源。仅检查包内链接，不访问外部网站。
missing=[];outside=[];checked=0
for f in c.rglob('*.html'):
 d=BeautifulSoup(f.read_text(),'html.parser')
 for n in d.find_all(True):
  for key in ['href','src']:
   url=n.get(key,'');u=urlsplit(url)
   if not url or url.startswith('#') or url.startswith('/') or u.scheme in ['http','https','data','mailto','javascript','blob']:continue  # 以 / 开头的是网站导航链接，部署后才有效
   if u.scheme=='file':outside.append([str(f.relative_to(c)),url]);continue
   target=(f.parent/unquote(u.path)).resolve();checked+=1
   if not target.exists():missing.append([str(f.relative_to(c)),url])
assert not missing,missing
files=sorted(f for f in c.rglob('*') if f.is_file() and not any(x.startswith('.') for x in f.relative_to(c).parts))
new=w/'随书配套包.zip'
with zipfile.ZipFile(new,'w',zipfile.ZIP_DEFLATED) as z:
 for f in files:z.write(f,Path('配套包')/f.relative_to(c))
with zipfile.ZipFile(new) as z:
 assert z.testzip() is None
 for f in files:assert hashlib.sha256(z.read('配套包/'+f.relative_to(c).as_posix())).digest()==hashlib.sha256(f.read_bytes()).digest()
shutil.copy2(new,p/'随书配套包.zip')
result={'文件数':len(files),'章节':16,'序言源稿sha256':hashlib.sha256((src/'正文.md').read_bytes()).hexdigest(),'本地HTML链接检查数':checked,'失效链接':missing,'依赖本机绝对路径':outside,'ZIPsha256':hashlib.sha256(new.read_bytes()).hexdigest(),'ZIP字节数':new.stat().st_size}
(w/'配套包同步核对.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
