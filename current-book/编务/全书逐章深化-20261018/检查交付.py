from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
from collections import Counter
import hashlib,json,re
R=Path(__file__).resolve().parent
class Page(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.links=[];self.title=False;self.lang=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  for key in ['href','src']:
   if key in a:self.links.append((key,a[key]))
  if tag=='title':self.title=True
  if tag=='html':self.lang=a.get('lang')=='zh-CN'
files=[R/'全书深化对比.html']+sorted(R.glob('第*/深化稿.html'))
missing=[];duplicates=[];brokenanchors=[];external=set();local=0
for p in files:
 parser=Page();parser.feed(p.read_text());assert parser.title and parser.lang,p
 duplicates += [(str(p.relative_to(R)),i,c) for i,c in Counter(parser.ids).items() if c>1]
 for attr,u in parser.links:
  v=urlsplit(u)
  if v.scheme or u.startswith('//'):external.add(u);continue
  if not v.path:
   if v.fragment and unquote(v.fragment) not in parser.ids:brokenanchors.append((str(p.relative_to(R)),u))
   continue
  dest=(p.parent/unquote(v.path)).resolve();local+=1
  if not dest.exists():missing.append((str(p.relative_to(R)),attr,u,str(dest)))
  elif v.fragment and dest.suffix=='.html':
   q=Page();q.feed(dest.read_text())
   if unquote(v.fragment) not in q.ids:brokenanchors.append((str(p.relative_to(R)),u))
manifest=json.loads((R/'章节清单.json').read_text());checks=[]
for r in manifest:
 n=r['chapter'];d=R/f'第{n:02d}章'
 sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
 checks.append(dict(chapter=n,source_unchanged=sha(r['source'])==r['sha256'],snapshot_matches=sha(R/r['snapshot'])==r['sha256'],deliverables=all((d/f).exists() for f in ['深化稿.md','深化稿.html','原稿快照.md','原始记录索引.md','来源指纹.json','深化说明.md'])))
report=dict(html_files=len(files),local_references_checked=local,missing=missing,duplicate_ids=duplicates,broken_anchors=brokenanchors,external_urls_not_fetched=sorted(external),chapter_checks=checks,browser_screenshot=False,online_publish=False)
(R/'核验/文件链接结构检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ['external_urls_not_fetched','chapter_checks']},ensure_ascii=False,indent=2))
assert not missing and not duplicates and not brokenanchors
assert all(all(v for k,v in x.items() if k!='chapter') for x in checks)
print('17章原稿指纹不变；18份HTML结构及本地链接检查通过。')
