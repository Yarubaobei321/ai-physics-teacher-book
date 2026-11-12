#!/usr/bin/env python3
"""现役十七章的整书排版。正文不在导出过程中改写；公式保留为 Word 原生公式。"""
from pathlib import Path
import copy, hashlib, importlib.util, json, re, subprocess, zipfile, os, html
from urllib.parse import unquote, urlsplit
from collections import Counter
from PIL import Image, ImageOps
from docx import Document
from docx.shared import Mm, Pt, Twips, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

HERE=Path(__file__).resolve().parent
P=HERE.parents[1]
D=Path('/Users/yaril/.cache/codex-runtimes/codex-primary-runtime/dependencies')
spec=importlib.util.spec_from_file_location('reader',P/'编务/新增两章与重新编号-20261018/构建阅读版.py')
reader=importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)
ASSETS=HERE/'排版资源'; ASSETS.mkdir(exist_ok=True)
OUT=HERE/'全书排版稿.docx'
MANIFEST=[]

def element(parent,tag,**attrs):
    el=parent.find(qn(tag))
    if el is None: el=OxmlElement(tag); parent.append(el)
    for key,value in attrs.items(): el.set(qn('w:'+key),str(value))
    return el

def font(style,size=10.5,east='Songti SC',bold=False):
    style.font.name='Times New Roman'; style.font.size=Pt(size)
    style.font.bold=bold; style.font.color.rgb=RGBColor(0,0,0)
    rf=style.element.get_or_add_rPr().get_or_add_rFonts()
    for key in ['ascii','hAnsi','cs']: rf.set(qn('w:'+key),'Times New Roman')
    rf.set(qn('w:eastAsia'),east)
    for key in ['asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme','csTheme']: rf.attrib.pop(qn('w:'+key),None)

def reference():
    doc=Document(); sec=doc.sections[0]
    sec.page_width=Mm(185); sec.page_height=Mm(260)
    sec.top_margin=Mm(18); sec.bottom_margin=Mm(18); sec.left_margin=Mm(22); sec.right_margin=Mm(18)
    sec.header_distance=Mm(8); sec.footer_distance=Mm(9)
    normal=doc.styles['Normal']; font(normal)
    pf=normal.paragraph_format; pf.line_spacing=1.35; pf.space_after=Pt(4); pf.widow_control=True
    for name in ['Body Text','First Paragraph','Compact','Block Text','Source Code','Verbatim Char','Caption','Image Caption','Table Caption']:
        if name not in doc.styles:
            from docx.enum.style import WD_STYLE_TYPE
            doc.styles.add_style(name,WD_STYLE_TYPE.CHARACTER if name=='Verbatim Char' else WD_STYLE_TYPE.PARAGRAPH)
        st=doc.styles[name];font(st,9.5 if name in ['Source Code','Verbatim Char','Caption','Image Caption','Table Caption'] else 10.5)
        if name!='Verbatim Char':
            st.paragraph_format.line_spacing=1.3; st.paragraph_format.space_after=Pt(4)
    doc.styles['Source Code'].paragraph_format.left_indent=Mm(4)
    doc.styles['Source Code'].paragraph_format.right_indent=Mm(4)
    doc.styles['Source Code'].paragraph_format.keep_together=False
    for name in ['Caption','Image Caption','Table Caption']:
        doc.styles[name].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for i,size in [(1,19),(2,14),(3,12),(4,11)]:
        st=doc.styles[f'Heading {i}'];font(st,size,'Heiti SC',True)
        st.paragraph_format.keep_with_next=True; st.paragraph_format.keep_together=True
        st.paragraph_format.space_before=Pt(18 if i==1 else 12);st.paragraph_format.space_after=Pt(8)
        if i==1: st.paragraph_format.page_break_before=True
    for name in ['Title','Subtitle','TOC Heading','Header','Footer']:
        if name in doc.styles:font(doc.styles[name],18 if name in ['Title','TOC Heading'] else 9,'Heiti SC' if name in ['Title','TOC Heading'] else 'Songti SC')
    footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=footer.add_run();field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');r._r.addnext(field)
    element(doc.settings.element,'w:updateFields',val='true')
    doc.save(HERE/'参考样式.docx')

def parse_text(source):
    # Word 无折叠控件，保留标题与全部内容。
    source=re.sub(r'<summary>(.*?)</summary>',lambda m:'\n\n**'+re.sub('<[^>]+>','',m[1]).strip()+'**\n\n',source,flags=re.S)
    source=re.sub(r'</?details[^>]*>','',source)
    return source

def plain_for_count(node):
    if isinstance(node,list):return ''.join(plain_for_count(x) for x in node)
    if not isinstance(node,dict):return ''
    t=node.get('t');c=node.get('c')
    if t=='Str': return c
    if t in ['Space','SoftBreak','LineBreak']:return ' '
    if t in ['Code','CodeBlock']:return c[1]+'\n'
    if t=='Math':return ''
    if t in ['RawBlock','RawInline']:return ''
    if t=='Image':return ''
    if t=='Link':return plain_for_count(c[1])
    if t=='Header':return plain_for_count(c[2])+'\n'
    return plain_for_count(c)+ ('\n' if t in ['Para','Plain'] else '')

def image_versions(path):
    key=hashlib.sha256(str(path).encode()).hexdigest()[:14]
    if path.suffix.lower()=='.svg':
        target=ASSETS/(key+'.png')
        js="const sharp=require(process.argv[1]);sharp(process.argv[2],{density:220}).flatten({background:'#ffffff'}).png().toFile(process.argv[3]);"
        subprocess.run([str(D/'node/bin/node'),'-e',js,str(D/'node/node_modules/sharp'),str(path),str(target)],check=True)
        return [target]
    im=ImageOps.exif_transpose(Image.open(path));w,h=im.size
    if h/w<=2.05:return [path]
    # 长界面截图按阅读顺序分段排入书页，保留小段重叠，原图不变。
    segment=int(w*1.34);overlap=int(w*.055);start=0;files=[]
    while start<h:
        end=min(h,start+segment);target=ASSETS/f'{key}-{len(files)+1}.png'
        im.crop((0,start,w,end)).save(target);files.append(target)
        if end==h:break
        start=end-overlap
    MANIFEST.append({'原图':str(path),'分段':len(files),'尺寸':[w,h],'重叠像素':overlap})
    return files

def image_node(node,path):
    n=copy.deepcopy(node);w,h=reader.intrinsic_image_size(path)
    max_height=192
    if path.name=='超失重仪-整机.jpg':max_height=130
    fixed_plane=hashlib.sha256(str(P/'正文/第04章-超声波测速/实操图/第05章-固定平面.jpg').encode()).hexdigest()[:14]
    if path.name==fixed_plane+'-1.png':max_height=169
    bad_input=hashlib.sha256(str(P/'正文/第06章-验证机械能守恒/实操图/第07章-异常输入-修订后.jpg').encode()).hexdigest()[:14]
    if path.name==bad_input+'-1.png':max_height=169
    width=min(145,max_height*w/h)
    # 低分辨率原照和题图不强行铺满版心，避免放大后模糊。
    if path.suffix.lower() != '.svg' and w < 800 and h/w <= 2.05:
        width=min(width,w*25.4/150)
    n['c'][0][2]=[['width',f'{width:.2f}mm']]
    n['c'][2][0]=str(path)
    return n

def prepare_blocks(blocks,src):
    result=[]
    for bi,block in enumerate(blocks):
        if block['t']=='RawBlock':continue
        images=[n for n in reader.walk(block) if n['t']=='Image']
        if block['t'] in ['Para','Plain'] and len(block['c'])==1 and images:
            node=images[0];path=(src.parent/unquote(urlsplit(node['c'][2][0]).path)).resolve()
            versions=image_versions(path)
            for i,version in enumerate(versions):
                result.append({'t':'Para','c':[image_node(node,version)]})
                if len(versions)>1:
                    result.append({'t':'Para','c':[{'t':'Str','c':f'（截图分段 {i+1}/{len(versions)}）'}]})
            next_block=blocks[bi+1] if bi+1<len(blocks) else None
            existing_caption=next_block and next_block['t']=='Para' and len(next_block['c'])==1 and next_block['c'][0]['t']=='Emph'
            if not existing_caption and node['c'][1]:
                result.append({'t':'Div','c':[['',[],[['custom-style','Image Caption']]],[{'t':'Para','c':copy.deepcopy(node['c'][1])}]]})
            continue
        for n in reader.walk(block):
            if n['t']=='Image':
                path=(src.parent/unquote(urlsplit(n['c'][2][0]).path)).resolve();n.update(image_node(n,image_versions(path)[0]))
            elif n['t']=='Link':
                url=n['c'][2][0]
                if not urlsplit(url).scheme and not url.startswith('#'):
                    n['c'][2][0]=(src.parent/unquote(urlsplit(url).path)).resolve().as_uri()
        result.append(block)
    return result

def build_ast():
    files,_=reader.get_files(P,None);blocks=[];counts=[];meta={};version=None
    for key,src in files:
        text=parse_text(src.read_text())
        ast=json.loads(subprocess.check_output(['/opt/homebrew/bin/pandoc','-f',reader.READER,'-t','json'],input=text,text=True))
        local_ids={n['c'][1][0]:key+'--'+n['c'][1][0] for n in reader.walk(ast['blocks']) if n['t']=='Header'}
        for n in reader.walk(ast['blocks']):
            if n['t']=='Header':n['c'][1][0]=local_ids[n['c'][1][0]]
            if n['t']=='Link' and n['c'][2][0].startswith('#'):
                old=n['c'][2][0][1:]
                if old in local_ids:n['c'][2][0]='#'+local_ids[old]
        version=ast['pandoc-api-version'];prepared=prepare_blocks(ast['blocks'],src);visible=plain_for_count(prepared)
        zh=len(re.findall(r'[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002FA1F]',visible))
        en=len(re.findall(r'[A-Za-z]+(?:[’\x27-][A-Za-z]+)*|\d+(?:\.\d+)?',visible))
        title=next(reader.inline_text(x['c'][2]) for x in ast['blocks'] if x['t']=='Header')
        counts.append({'部分':title,'文件':str(src.relative_to(P)),'中文汉字':zh,'英文及数字词':en,'合计字词':zh+en,'可见字符不含空白':len(re.sub(r'\s','',visible)),'sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
        blocks+=prepared
    ast={'pandoc-api-version':version,'meta':{'lang':{'t':'MetaString','c':'zh-CN'},'toc-title':{'t':'MetaString','c':'目录'}},'blocks':blocks}
    (HERE/'整书内容.json').write_text(json.dumps(ast,ensure_ascii=False))
    total={k:sum(c[k] for c in counts) for k in ['中文汉字','英文及数字词','合计字词','可见字符不含空白']}
    (HERE/'字数统计.json').write_text(json.dumps({'口径':'现役序言、前言、导论、十七章、附录A—E，含表格、图注、提示词及参考文献；中文每字一项、英文连续单词及数值每项计一词；不含公式节点、图片内文字、网址目标和Markdown标记。非空白字符另计，包含标点。','合计':total,'分章':counts,'长截图分段':MANIFEST},ensure_ascii=False,indent=2))
    return total

def polish():
    doc=Document(OUT)
    mathpr=doc.settings.element.find(qn('m:mathPr'))
    if mathpr is None:mathpr=OxmlElement('m:mathPr');doc.settings.element.append(mathpr)
    mathfont=OxmlElement('m:mathFont');mathfont.set(qn('m:val'),'STIX Two Math');mathpr.append(mathfont)
    # 使用统一字体，包括未使用样式，清除默认模板字体。
    for st in doc.styles:
        if st.type in [1,2]:
            rf=st.element.get_or_add_rPr().get_or_add_rFonts()
            for key in ['ascii','hAnsi','cs']:
                if 'Courier' in (rf.get(qn('w:'+key)) or ''):rf.set(qn('w:'+key),'Times New Roman')
            if not rf.get(qn('w:eastAsia')):rf.set(qn('w:eastAsia'),'Songti SC')
    for p in doc.paragraphs:
        # WPS会拆开某些行内复合单位；在此数值前换行，保留完整原生公式。
        if '如果加速度大小是' in p.text:
            maths=p._p.xpath('./m:oMath')
            if maths:
                br_run=OxmlElement('w:r');br_run.append(OxmlElement('w:br'))
                maths[0].addprevious(br_run)
        if p.style.name=='Heading 1' and p.text.startswith(('第 2 章','第 7 章')):
            for r in p.runs:
                if '：' in r.text:
                    before,after=r.text.split('：',1);r.text=before+'：';r.add_break();r.add_text(after);break
        visible_runs=[r for r in p.runs if r.text.strip()]
        if 0<len(p.text.strip())<85 and visible_runs and all(r.bold for r in visible_runs):
            p.paragraph_format.keep_with_next=True
            p.paragraph_format.keep_together=True
        if re.match(r'^\[\d+\] ',p.text):
            p.paragraph_format.left_indent=Mm(7)
            p.paragraph_format.first_line_indent=Mm(-7)
            p.paragraph_format.keep_together=True
        if p._p.xpath('.//w:drawing'):
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.keep_with_next=True
            p.paragraph_format.space_before=Pt(6);p.paragraph_format.space_after=Pt(4)
        if p.text.startswith('图 ') or p.text.startswith('图　') or p.text.startswith('（截图分段'):
            p.style=doc.styles['Caption'];p.paragraph_format.keep_together=True
        if p.style.name=='Source Code':
            p.paragraph_format.keep_together=False;p.paragraph_format.keep_with_next=False
            element(p._p.get_or_add_pPr(),'w:wordWrap',val='1')
        if p.text.strip() in {'。','，','；'} and p._p.getprevious() is not None and p._p.getprevious().xpath('.//m:oMath'):
            prev=p._p.getprevious()
            for child in list(p._p):
                if child.tag!=qn('w:pPr'):prev.append(child)
            p._p.getparent().remove(p._p)
    # 序号仅给真实文献标记以上标，代码和URL内容不受影响。
    for p in doc.paragraphs:
        if p.style.name=='Source Code' or re.match(r'^\[\d+\]',p.text):continue
        for r in list(p.runs):
            if re.search(r'\[\d+(?:[—–,，-]\d+)*\]',r.text):
                original=r.text;parent=r._r.getparent();idx=parent.index(r._r)
                for part in re.split(r'(\[\d+(?:[—–,，-]\d+)*\])',original):
                    if not part:continue
                    nr=copy.deepcopy(r._r)
                    for ch in list(nr):
                        if ch.tag!=qn('w:rPr'):nr.remove(ch)
                    tx=OxmlElement('w:t');tx.text=part;tx.set(qn('xml:space'),'preserve');nr.append(tx)
                    if re.fullmatch(r'\[\d+(?:[—–,，-]\d+)*\]',part):element(nr.get_or_add_rPr(),'w:vertAlign',val='superscript')
                    parent.insert(idx,nr);idx+=1
                parent.remove(r._r)
    for table in doc.tables:
        n=len(table.columns);width=8220
        weights=[1]*n
        if n==8:weights=[2.05]+[1]*7
        elif n==2:weights=[1,2.6]
        elif n>=3:
            values=[]
            for i in range(n):
                lens=[len(row.cells[i].text) for row in table.rows]
                values.append(min(2.7,max(.7,(sum(lens)/max(1,len(lens)))**.42)))
            weights=values
        widths=[round(width*w/sum(weights)) for w in weights];widths[-1]=width-sum(widths[:-1])
        table.autofit=False;table.alignment=WD_TABLE_ALIGNMENT.CENTER
        pr=table._tbl.tblPr;element(pr,'w:tblW',type='dxa',w=width);element(pr,'w:tblLayout',type='fixed')
        grid=table._tbl.tblGrid
        for ch in list(grid):grid.remove(ch)
        for w in widths:element(grid,'w:gridCol',w=w) if False else None
        for w in widths:
            e=OxmlElement('w:gridCol');e.set(qn('w:w'),str(w));grid.append(e)
        borders=element(pr,'w:tblBorders')
        for side in ['top','left','bottom','right','insideH','insideV']:element(borders,'w:'+side,val='single',sz='4',color='D9D9D9')
        for ri,row in enumerate(table.rows):
            tr=row._tr.get_or_add_trPr();element(tr,'w:cantSplit')
            if ri==0:element(tr,'w:tblHeader',val='1')
            for ci,cell in enumerate(row.cells):
                cell.width=Twips(widths[ci]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                cp=cell._tc.get_or_add_tcPr();element(cp,'w:tcW',type='dxa',w=widths[ci])
                mar=element(cp,'w:tcMar')
                for side,val in [('top',70),('bottom',70),('left',90),('right',90)]:element(mar,'w:'+side,type='dxa',w=val)
                if ri==0:element(cp,'w:shd',fill='E9EFF2',val='clear')
                for para in cell.paragraphs:
                    pf=para.paragraph_format;pf.space_before=Pt(0);pf.space_after=Pt(0);pf.line_spacing=1.2
                    pf.keep_with_next=ri==0;pf.keep_together=False
                    para.alignment=WD_ALIGN_PARAGRAPH.CENTER if ri==0 or len(cell.text)<12 else WD_ALIGN_PARAGRAPH.LEFT
                    for r in para.runs:r.font.size=Pt(9.5);r.font.bold=ri==0
                    for r in para._p.xpath('.//m:r'):
                        rp=element(r,'w:rPr');element(rp,'w:sz',val=19)
                        r.remove(rp);r.insert(1 if len(r) and r[0].tag==qn('m:rPr') else 0,rp)
    for deg in doc.element.xpath('.//m:rad'):
        d=deg.find(qn('m:deg'))
        if d is not None and not ''.join(d.itertext()).strip():
            rp=deg.find(qn('m:radPr'))
            if rp is None:rp=OxmlElement('m:radPr');deg.insert(0,rp)
            e=OxmlElement('m:degHide');e.set(qn('m:val'),'1');rp.append(e)
    for node in doc.element.xpath('.//w:t'):
        if node.text=='Table of Contents':node.text='目录'
    # 提供实际可见、可点击的目录与页码域，避免打开软件后出现空白目录。
    toc=doc.element.body.find(qn('w:sdt')).find(qn('w:sdtContent'))
    for child in list(toc)[1:]:toc.remove(child)
    cache=json.loads((HERE/'目录页码.json').read_text()) if (HERE/'目录页码.json').exists() else {}
    headings=[p for p in doc.paragraphs if p.style.name=='Heading 1']
    for i,h in enumerate(headings):
        mark='book_chapter_'+str(i+1)
        bs=OxmlElement('w:bookmarkStart');bs.set(qn('w:id'),str(10000+i));bs.set(qn('w:name'),mark);h._p.insert(1,bs)
        be=OxmlElement('w:bookmarkEnd');be.set(qn('w:id'),str(10000+i));h._p.append(be)
        tp=OxmlElement('w:p');pp=element(tp,'w:pPr');element(pp,'w:spacing',after='100',line='300',lineRule='auto')
        tabs=element(pp,'w:tabs');element(tabs,'w:tab',val='right',leader='dot',pos='8220')
        link=OxmlElement('w:hyperlink');link.set(qn('w:anchor'),mark)
        heading_text=h.text.replace('\n','')
        r=OxmlElement('w:r');tx=OxmlElement('w:t');tx.text=heading_text;r.append(tx);link.append(r);tp.append(link)
        r=OxmlElement('w:r');r.append(OxmlElement('w:tab'));tp.append(r)
        field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGEREF '+mark+' \\h')
        r=OxmlElement('w:r');tx=OxmlElement('w:t');tx.text=str(cache.get(heading_text,' '));r.append(tx);field.append(r);tp.append(field);toc.append(tp)
    doc.save(OUT)
    # 字体表和主题也会继承等宽字体，最后逐项清除。
    tmp=OUT.with_suffix('.tmp.docx')
    with zipfile.ZipFile(OUT) as zin,zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data=zin.read(item.filename)
            if item.filename.endswith('.xml'):
                data=data.replace(b'Courier New',b'Times New Roman').replace(b'Courier',b'Times New Roman')
                for obsolete in ['MS ゴシック','ＭＳ ゴシック','ＭＳ 明朝','MS 明朝','MS Gothic','MS Mincho']:
                    data=data.replace(obsolete.encode(),'Songti SC'.encode())
                if item.filename=='word/settings.xml':data=data.replace(b'Cambria Math',b'STIX Two Math')
            zout.writestr(item,data)
    tmp.replace(OUT)

if __name__=='__main__':
    reference();counts=build_ast()
    subprocess.run(['/opt/homebrew/bin/pandoc',str(HERE/'整书内容.json'),'-f','json','-t','docx','--reference-doc',str(HERE/'参考样式.docx'),'--toc','--toc-depth','1','--output',str(OUT)],check=True)
    polish();print(json.dumps({'输出':str(OUT),'字数':counts,'长图分段':len(MANIFEST)},ensure_ascii=False))
