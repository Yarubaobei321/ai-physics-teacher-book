"""检查交付结构、生成核查说明并打包；不将未运行检查计入通过数。"""
from pathlib import Path
from html.parser import HTMLParser
import json,html,subprocess,shutil,hashlib,zipfile,re
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
required=['book.html','book.md','index.html','exercises/01_paper_tape.html','exercises/02_spring.html','exercises/03_potential.html','exercises/04_rc.html','editorial/来源与证据边界.md','editorial/下一轮修订与材料需求.md']
for rel in required:
    p=ROOT/rel
    if not p.is_file() or p.stat().st_size==0:raise RuntimeError('缺少必交文件：'+rel)

def load(name):
    p=ROOT/'editorial'/name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'status':'not_run','reason':'未找到执行报告','total':0,'passed':0,'failed':0}
model=load('model-test-report.json');browser=load('browser-test-report.json')
structure=[]
def rec(name,ok,detail=''):structure.append({'name':name,'passed':bool(ok),'detail':detail})
rec('前言、七章、后记均存在',len(list((ROOT/'chapters').glob('*.md')))==9)
rec('四个独立练习页均存在',len(list((ROOT/'exercises').glob('*.html')))==4)
rec('阅读版包含四幅内嵌示意图',(ROOT/'book.html').read_text().count('data:image/svg+xml;base64,')==4)
class Inspect(HTMLParser):
    def __init__(self):super().__init__();self.refs=[];self.scripts=[];self._in=False;self._buf=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag in ['a','img','script','link']:
            for key in ['href','src']:
                if key in d:self.refs.append(d[key])
        if tag=='script' and 'src' not in d:self._in=True;self._buf=[]
    def handle_data(self,data):
        if self._in:self._buf.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self._in:self.scripts.append(''.join(self._buf));self._in=False
# Create temporary validation target before checking relative navigation.
validation=ROOT/'editorial/validation.html'
validation.write_text('<!doctype html><meta charset="utf-8"><title>核查说明</title>',encoding='utf-8')
node=shutil.which('node');missing=[];syntax=[]
for p in sorted(ROOT.rglob('*.html')):
    parser=Inspect();parser.feed(p.read_text(encoding='utf-8'))
    for ref in parser.refs:
        if ref.startswith(('#','data:','http:','https:','mailto:')):continue
        path=ref.split('#')[0].split('?')[0]
        if path and not (p.parent/path).exists():missing.append(str(p.relative_to(ROOT))+': '+ref)
    if node:
        for i,script in enumerate(parser.scripts):
            proc=subprocess.run([node,'--check'],input=script,text=True,capture_output=True,timeout=20)
            syntax.append({'file':str(p.relative_to(ROOT)),'script':i,'passed':proc.returncode==0,'error':proc.stderr[:600] if proc.returncode else ''})
rec('HTML本地引用路径均存在',not missing,'; '.join(missing))
rec('所有内嵌JavaScript语法检查',bool(node) and all(x['passed'] for x in syntax),'未安装Node，未执行' if not node else f'{len(syntax)} 段脚本')
rec('交付包不包含字体文件',not any(p.suffix.lower() in ['.ttf','.otf','.woff','.woff2'] for p in ROOT.rglob('*')))
structure_report={'total':len(structure),'passed':sum(x['passed'] for x in structure),'failed':sum(not x['passed'] for x in structure),'checks':structure,'script_checks':syntax}
(ROOT/'editorial/structure-test-report.json').write_text(json.dumps(structure_report,ensure_ascii=False,indent=2),encoding='utf-8')

model_status=f"实际报告：{model.get('passed',0)}/{model.get('total',0)}项通过，{model.get('failed',0)}项失败。" if model.get('total') else '未执行或未取得有效报告。'
if browser.get('status')=='completed':browser_status=f"已执行选定场景：{browser.get('passed',0)}/{browser.get('total',0)}项通过，{browser.get('failed',0)}项失败。"
else:browser_status='未完整执行：'+browser.get('reason','未说明原因')
lines=['# 本次程序与文件核查','', '## 解析模型与边界',model_status,'脚本：`test_models.js`；完整逐项报告：`model-test-report.json`。','', '## 浏览器选定场景',browser_status,'脚本：`check_browser.py`；完整逐项报告：`browser-test-report.json`。','', '## 文件结构与脚本语法',f"{structure_report['passed']}/{structure_report['total']}项通过；完整报告：`structure-test-report.json`。",'', '## 这些检查没有证明什么','这些检查不等于真实实验核验、全部浏览器兼容性保证、课堂有效性评价或出版质量终审。打印媒体检查核对的是DOM与CSS表现，不声称已经逐页实打印验收。浏览器截图若已生成，位于`preview/`，均为本次新编资源的画面，不是历史截图。','', '## 与正文的对应','纸带检查共享计数点、单位换算、输入失效和长结论打印；弹簧检查关键相位、参数重置和能量；平行板检查固定点及边界输入；RC检查分步演化、切换连续性和电流符号。各报告保留实际结果，未运行项目不计为通过。']
for kind,d in [('模型',model),('浏览器',browser),('文件结构',structure_report)]:
    items=d.get('results',d.get('checks',[]));fails=[v for v in items if not v.get('passed')]
    if fails:lines+=['',f'## 尚未通过：{kind}']+[f"- {x['name']}：{x.get('error',x.get('detail',''))}" for x in fails]
md='\n\n'.join(lines)
(ROOT/'editorial/程序核查说明.md').write_text(md,encoding='utf-8')
css='body{max-width:920px;margin:35px auto;padding:0 22px;background:#f6f4ed;color:#263e3f;font:17px/1.9 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}h1{font-size:32px}h2{font-size:23px;margin-top:35px}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#176d65}.card{padding:20px;background:white;border:1px solid #dce4db;margin:16px 0}'
body=f'<h1>本次程序与文件核查</h1><div class="card"><h2>解析模型与边界</h2><p>{html.escape(model_status)}</p></div><div class="card"><h2>浏览器选定场景</h2><p>{html.escape(browser_status)}</p></div><div class="card"><h2>文件结构与脚本语法</h2><p>{structure_report["passed"]}/{structure_report["total"]}项通过。</p></div><h2>范围</h2><p>本报告仅说明实际执行的代码和文件检查。不等于真实硬件验证、课堂教学效果、全部浏览器保证或出版终审。打印媒体检查不等于逐页实打印验收。</p><p>逐项记录在model-test-report.json、browser-test-report.json、structure-test-report.json。若有未通过项目，请以这些实际记录为准。</p><h2>详细说明</h2><pre>{html.escape(md)}</pre>'
validation.write_text(f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>程序与文件核查</title><style>{css}</style></head><body><a href="../index.html">← 返回目录</a>{body}</body></html>',encoding='utf-8')
# Manifest intentionally excludes itself.
manifest=[]
for p in sorted(ROOT.rglob('*')):
    if p.is_file() and p.name!='manifest-sha256.json' and '__pycache__' not in p.parts:
        manifest.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(ROOT/'editorial/manifest-sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
exports={ROOT/'book.html':BASE/'physics_book_v2_reading.html',ROOT/'book.md':BASE/'physics_book_v2_manuscript.md',ROOT/'editorial/下一轮修订与材料需求.md':BASE/'physics_book_v2_materials.md',validation:BASE/'physics_book_v2_validation.html'}
for src,dst in exports.items():shutil.copy2(src,dst)
zip_path=BASE/'physics_book_v2_bundle.zip'
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:z.write(p,arcname='physics_book_v2/'+str(p.relative_to(ROOT)))
with zipfile.ZipFile(zip_path) as z:
    if z.testzip() is not None:raise RuntimeError('ZIP完整性校验失败')
summary={'exports':[{'path':str(p),'bytes':p.stat().st_size}for p in [*exports.values(),zip_path]],'model':{'total':model.get('total',0),'passed':model.get('passed',0),'failed':model.get('failed',0)},'browser':{k:browser.get(k)for k in ['status','total','passed','failed']},'structure':{k:structure_report[k]for k in ['total','passed','failed']}}
(BASE/'physics_book_v2_delivery.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
