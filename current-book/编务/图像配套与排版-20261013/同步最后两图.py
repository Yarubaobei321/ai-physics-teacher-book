from pathlib import Path
from lxml import etree as E
from zipfile import ZipFile,ZIP_DEFLATED
from PIL import Image
import shutil,json
R=Path(__file__).resolve().parent;P=R.parents[1];p=R/'全书排版稿.docx';shutil.copy2(p,R/'第一轮排版校样.docx')
images={'五个速度':P/'正文/第02章-打点计时器纸带/本轮配图/纸带计算结果-v2.png','184 mm 几何':P/'正文/第14章-从等势线到电势地形/实操图/WorkBuddy-电势地形与实测点-v2.png'}
with ZipFile(p)as z:files={n:z.read(n) for n in z.namelist()}
x=E.fromstring(files['word/document.xml']);r=E.fromstring(files['word/_rels/document.xml.rels']);rel={e.get('Id'):e.get('Target') for e in r};changes=[]
for e in x.xpath('//*[local-name()="docPr"]'):
 for key,img in images.items():
  if key not in e.get('descr',''):continue
  box=e.getparent();blip=box.xpath('.//*[local-name()="blip"]')[0];rid=next(v for k,v in blip.attrib.items() if k.endswith('}embed'));target='word/'+rel[rid];files[target]=img.read_bytes();w,h=Image.open(img).size;ww=min(145,192*w/h);cx=round(ww*36000);cy=round(ww*h/w*36000)
  for ex in box.xpath('./*[local-name()="extent"]|.//*[local-name()="xfrm"]/*[local-name()="ext"]'):ex.set('cx',str(cx));ex.set('cy',str(cy))
  changes.append({'image':str(img),'media':target,'size_mm':[ww,ww*h/w]})
assert len(changes)==2
files['word/document.xml']=E.tostring(x,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(p.with_suffix('.new.docx'),'w',ZIP_DEFLATED)as z:
 for n,d in files.items():
  if n.endswith('.xml'):d=d.replace(b'Courier New',b'Times New Roman').replace(b'Courier',b'Times New Roman')
  z.writestr(n,d)
p.with_suffix('.new.docx').replace(p);(R/'最后两图同步.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2))
if (R/'全书排版稿.pdf').exists():(R/'全书排版稿.pdf').rename(R/'第一轮排版校样.pdf')
print(changes)
