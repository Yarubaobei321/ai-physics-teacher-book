from pathlib import Path
import sys,math,json,shutil
from PIL import Image,ImageDraw
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
R=Path('/Users/yaril/个人文档/3 写作/图书出版/00_这本书的全部进展/编务/图像配套与排版-20261013');sys.path.insert(0,str(R));from 执行 import save
P=R.parents[1]; img=Image.open(R/'照片识别画布-无浮层.png').convert('RGB');d=ImageDraw.Draw(img)
for a,b in [((353,126),(139,155)),((354,236),(171,212)),((430,1102),(260,1158)),((430,1220),(264,1197))]:
 dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy);ux,uy=dx/l,dy/l
 pts=[b,(b[0]-17*ux+8*uy,b[1]-17*uy-8*ux),(b[0]-17*ux-8*uy,b[1]-17*uy+8*ux)]
 d.line([a,b],fill='white',width=10);d.polygon(pts,fill='white');d.line([a,b],fill='#832fb0',width=5);d.polygon([b,(b[0]-14*ux+5*uy,b[1]-14*uy-5*ux),(b[0]-14*ux-5*uy,b[1]-14*uy+5*ux)],fill='#832fb0')
f=P/'正文/第14章-从等势线到电势地形/assets/网页-照片识别-匀强含误识别-v2.png';img.crop((64,48,1250,1240)).save(f)
md=next((P/'正文/第14章-从等势线到电势地形').glob('*.md'));save(md);s=md.read_text().replace('assets/网页-照片识别-匀强含误识别.jpg','assets/网页-照片识别-匀强含误识别-v2.png');md.write_text(s)
p=R/'全书排版稿.docx';shutil.copy2(p,R/'补照片前排版稿.docx')
with ZipFile(p)as z:files={n:z.read(n) for n in z.namelist()}
x=E.fromstring(files['word/document.xml']);rels={e.get('Id'):e.get('Target') for e in E.fromstring(files['word/_rels/document.xml.rels'])};count=0
for e in x.xpath('//*[local-name()="docPr"]'):
 if '平行板照片的自动识别结果' not in e.get('descr',''):continue
 box=e.getparent();b=box.xpath('.//*[local-name()="blip"]')[0];rid=next(v for k,v in b.attrib.items() if k.endswith('}embed'));target='word/'+rels[rid];files[target]=f.read_bytes();w,h=Image.open(f).size;cx=round(145*36000);cy=round(145*h/w*36000)
 for ext in box.xpath('./*[local-name()="extent"]|.//*[local-name()="xfrm"]/*[local-name()="ext"]'):ext.set('cx',str(cx));ext.set('cy',str(cy))
 count+=1
assert count==1
files['word/document.xml']=E.tostring(x,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(p,'w',ZIP_DEFLATED) as z:
 for n,data in files.items():z.writestr(n,data)
(R/'全书排版稿.pdf').rename(R/'补照片前排版稿.pdf')
status=json.loads((R/'逐项状态.json').read_text());status['A12-3']='网页-照片识别-匀强含误识别-v2.png；已导入作者授权的完整记录，按原四角坐标重新识别，复现黄5、红9、蓝5及6个低置信度；导出实际画布并仅加4处箭头，正文已改，原15环及上排两端虚线圈均保留。';(R/'逐项状态.json').write_text(json.dumps(status,ensure_ascii=False,indent=2))
q=P/'编务/全书审核修订-20261012/交给Codex的图像与配套清单.md';save(q);s=q.read_text();import re
s=re.sub(r'(\*\*2026-10-13 执行状态（A12-3）\*\*：)[^\n]*',lambda m:m[1]+status['A12-3'],s);q.write_text(s)
f=P/'配套包/开始阅读.md';f.write_text(f.read_text().replace('第 1、3、13 章','第 1、13 章'))
print('已同步照片、正文与Word；图像119?实际',Image.open(P/'正文/第14章-从等势线到电势地形/assets/网页-照片识别-匀强含误识别-v2.png').size)
