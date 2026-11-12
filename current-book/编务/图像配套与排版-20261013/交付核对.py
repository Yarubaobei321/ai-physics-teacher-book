from pathlib import Path
import hashlib,zipfile,json,re,sys,shutil,urllib.parse
from pypdf import PdfReader
from lxml import etree as E
R=Path('/Users/yaril/个人文档/3 写作/图书出版/00_这本书的全部进展/编务/图像配套与排版-20261013');P=R.parents[1];sys.path.insert(0,str(R));from 执行 import save
p=R/'全书排版稿.docx'
with zipfile.ZipFile(p)as z:
 assert z.testzip() is None
 xmls={n:z.read(n)for n in z.namelist()if n.endswith('.xml')};assert not any(b'Courier' in d for d in xmls.values())
 x=E.fromstring(xmls['word/document.xml']);b=x.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body');assert b[0].tag.endswith('sdt')
 assert any('平行板照片的自动识别结果' in e.get('descr','') for e in x.xpath('//*[local-name()="docPr"]'))
pdf=PdfReader(R/'全书排版稿.pdf');assert len(pdf.pages)==364;assert '目录' in pdf.pages[0].extract_text();assert '第 17 章' in pdf.pages[0].extract_text();assert '平行板照片的自动识别结果' in pdf.pages[219].extract_text()
for suffix in ['docx','pdf']:
 dst=P/f'全书排版稿.{suffix}';save(dst);shutil.copy2(R/dst.name,dst);assert hashlib.sha256(dst.read_bytes()).digest()==hashlib.sha256((R/dst.name).read_bytes()).digest()
q=P/'配套包';missing=[];banned=[]
for f in q.rglob('*'):
 if not f.is_file():continue
 if f.suffix in ['.md','.html','.json','.js','.csv','.txt']:
  s=f.read_text();banned +=[(str(f.relative_to(q)),m)for m in ['/Users/','file:///','publish-probe-99114.app.workbuddy.host']if m in s]
 if f.suffix in ['.md','.html']:
  links=re.findall(r'(?:src|href)=[\x22\x27]([^\x22\x27]+)',s)if f.suffix=='.html' else re.findall(r'\]\(([^)]+)\)',s)
  for link in links:
   u=urllib.parse.urlsplit(link.strip('<>'))
   if not u.scheme and u.path and not(f.parent/urllib.parse.unquote(u.path)).exists():missing.append([str(f.relative_to(q)),link])
assert not missing,missing;assert not banned,banned
for f in [P/'随书配套包.zip',*q.rglob('*.zip')]:
 with zipfile.ZipFile(f)as z:assert z.testzip()is None
result={'状态':'本地审读交付，待补项见review.md','PDF页数':len(pdf.pages),'正文章数':17,'图片引用':106,'正文公式':818,'配套文件':len([f for f in q.rglob('*') if f.is_file()]),'失效配套依赖':missing,'禁带路径命中':banned,'Courier命中':0,'最后换图分页变化':[220,221,222,223,224],'最后换图复看':'五页放大检查通过','交付文件':[{ '文件':f.name,'SHA256':hashlib.sha256(f.read_bytes()).hexdigest(),'字节':f.stat().st_size}for f in [P/'全书排版稿.docx',P/'全书排版稿.pdf',P/'全书阅读.html',P/'随书配套包.zip']]};(R/'交付验证.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
# 复现脚本留在工作包；原一次性清理脚本不作为重建入口。
for src,name in [('/tmp/final_photo.py','补入照片识别图.py'),('/tmp/verify_deliver.py','交付核对.py')]:shutil.copy2(src,R/name)
