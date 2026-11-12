from pathlib import Path
import json,shutil,hashlib,zipfile,subprocess,os
from PIL import Image
P=Path('/Users/yaril/个人文档/3 写作/图书出版/00_这本书的全部进展')
R=P/'编务/GPT封面与配图-20261019'
O=R/'四器材留白-20261020';O.mkdir(exist_ok=True)
B=O/'修改前';B.mkdir(exist_ok=True)
cover=P/'封面/把物理做出来-封面.png'
for f in [cover,P/'全书排版稿.docx',P/'全书排版稿.pdf']:
    shutil.copy2(f,B/f.name)
images=json.loads((R/'四器材修订记录.json').read_text())['images']
for row in images:shutil.copy2(row['path'],O/(row['key']+'.png'))
new=O/'four_spacious_final.png'
new_w,new_h=Image.open(new).size
old_sha=hashlib.sha256(cover.read_bytes()).hexdigest()
out=O/'全书排版稿.docx';replaced=[]
with zipfile.ZipFile(P/'全书排版稿.docx') as zi,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as zo:
    for info in zi.infolist():
        data=zi.read(info.filename)
        if info.filename.startswith('word/media/') and hashlib.sha256(data).hexdigest()==old_sha:
            data=new.read_bytes();replaced.append(info.filename)
        if info.filename=='word/document.xml':
            from lxml import etree
            root=etree.fromstring(data)
            ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
            first=root.xpath('/w:document/w:body/w:p[1]',namespaces=ns)[0]
            for node in first.xpath('.//wp:extent|.//a:xfrm/a:ext',namespaces=ns):
                node.set('cy',str(round(int(node.get('cx'))*new_h/new_w)))
            data=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
        zo.writestr(info,data)
assert len(replaced)==1,replaced
with zipfile.ZipFile(out) as z:assert z.testzip() is None
shutil.copy2(new,cover)
(O/'检查.json').write_text(json.dumps({'只替换Word内嵌封面':replaced,'尺寸':Image.open(new).size,'源图':str(new)},ensure_ascii=False,indent=2))
env=dict(os.environ,TMPDIR='/private/tmp',OMP_NUM_THREADS='1',FONTCONFIG_FILE=str((R/'本机字体配置.xml').resolve()),XDG_CACHE_HOME='/private/tmp/book-font-cache-20261015')
subprocess.run(['/Users/yaril/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice','-env:UserInstallation=file:///private/tmp/book-four-cover-20261020','--headless','--convert-to','pdf','--outdir',str(O.resolve()),str(out.resolve())],env=env,check=True,timeout=600)
from pypdf import PdfReader
pdf=PdfReader(O/'全书排版稿.pdf');assert len(pdf.pages)>400 and len(list(pdf.pages[0].images))>0
for ext in ['docx','pdf']:shutil.copy2(O/('全书排版稿.'+ext),P/('全书排版稿.'+ext))
with (R/'review.md').open('a') as f:f.write('\n## 2026-10-20 四器材与留白\n\n按作者选择采用异种双电极带连线水槽，三色环各5个。超失重左上、水槽右上、光盘线圈左下、电路拼图右下；缩小上方两套器材，增大文字和器材之间的留白。磁吸触点嵌在每块拼图侧面。封面PNG、HTML引用、Word内嵌封面与PDF已同步；Word仅替换同尺寸封面图片，正文与排版参数未改。PDF共'+str(len(pdf.pages))+'页，文件完整性通过，按要求不检查排版。旧文件保存在四器材留白-20261020/修改前。\n')
with (P/'PROJECT_SUMMARY.md').open('a') as f:f.write('\n\n## 2026-10-20 四器材封面\n\n作者选用异种双电极带等势连线水槽；四器材按超失重左上、水槽右上、法拉第左下、活版电路右下排列，缩小架子与水槽并增加留白。封面与HTML/Word/PDF已同步，PDF'+str(len(pdf.pages))+'页。仅更新封面，正文未改；未检查排版。恢复和来源见编务/GPT封面与配图-20261019/四器材留白-20261020。\n')
print('PDF pages:',len(pdf.pages),'replaced:',replaced)
