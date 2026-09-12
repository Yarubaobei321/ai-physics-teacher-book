"""可重复执行的离线浏览器检查；不把未安装环境写成通过。"""
from pathlib import Path
import json,shutil,traceback,datetime
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'editorial/browser-test-report.json'
PREVIEW=ROOT/'editorial/preview';PREVIEW.mkdir(exist_ok=True)
checks=[];errors=[];requests=[]
def check(name,fn):
    try:
        result=fn()
        if not result:raise AssertionError('条件不成立')
        checks.append({'name':name,'passed':True})
    except Exception as e:checks.append({'name':name,'passed':False,'error':str(e)})
def write(status,reason=''):
    result={'status':status,'reason':reason,'executed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'total':len(checks),'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'checks':checks,'page_errors':errors,'limitations':['仅自动化浏览器与选定输入检查','未进行真实硬件测试','未进行学生课堂验证','打印媒体检查不等于逐页实打印验收']}
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['status','reason','total','passed','failed']},ensure_ascii=False))
try:
    from playwright.sync_api import sync_playwright
except ImportError as e:
    write('not_run','当前环境未安装Python Playwright：'+str(e));raise SystemExit(0)
try:
    with sync_playwright() as p:
        browser=None;launch_errors=[]
        candidates=[None,shutil.which('chromium'),shutil.which('chromium-browser'),shutil.which('google-chrome'),'/opt/google/chrome/chrome']
        for executable in dict.fromkeys(candidates):
            if executable is not None and not Path(executable).exists():continue
            try:
                opts={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage']}
                if executable:opts['executable_path']=executable
                browser=p.chromium.launch(**opts);break
            except Exception as e:launch_errors.append(str(e)[:250])
        if browser is None:
            write('not_run','无法启动已安装浏览器。'+' | '.join(launch_errors));raise SystemExit(0)
        context=browser.new_context(viewport={'width':1280,'height':900},device_scale_factor=1)
        page=context.new_page();page.on('pageerror',lambda err:errors.append(str(err)));page.on('request',lambda r:requests.append(r.url))
        def goto(file):page.goto((ROOT/file).as_uri(),wait_until='load');page.wait_for_timeout(100)
        goto('exercises/01_paper_tape.html')
        check('纸带初始不显示结果',lambda:page.locator('#result').is_hidden())
        page.locator('#sample').click();page.locator('#calc').click()
        check('纸带共享点示例计算正确',lambda:abs(page.evaluate('window.exerciseState().D')-.01744)<1e-9)
        check('纸带结果区可见',lambda:page.locator('#result').is_visible())
        page.locator('#group').fill('核查示例组（非实测）')
        check('改记录名称不撤下结果',lambda:page.locator('#result').is_visible())
        page.locator('#g').fill('9.81')
        check('改变g立即撤下旧结果',lambda:page.locator('#result').is_hidden())
        page.locator('#calc').click();page.locator('#a1').fill('');page.locator('#calc').click()
        check('空白输入拒绝计算且无旧结果',lambda:page.locator('#result').is_hidden() and '填写' in page.locator('#status').inner_text())
        page.locator('#sample').click();page.locator('#calc').click()
        note='这是本次构造的程序检查记录，不是实验结果。\n'+'长结论应当自然换行，而不是截断在输入框内。'*18+'\n打印末尾核查标记：END-0926'
        page.locator('#notes').fill(note);page.emulate_media(media='print')
        check('打印结论包含末尾标记',lambda:'END-0926' in page.locator('#printedNotes').inner_text())
        check('打印使用可展开普通文字而非文本框',lambda:page.locator('#printedNotes').is_visible() and page.locator('#notes').is_hidden())
        check('打印结论容器不裁切内容',lambda:page.locator('#printedNotes').evaluate('(e)=>e.scrollHeight<=e.clientHeight+2'))
        page.emulate_media(media='screen');page.screenshot(path=str(PREVIEW/'01_paper_tape_desktop.png'),full_page=True)
        goto('exercises/02_spring.html');page.locator('[data-phase="0.25"]').click()
        check('弹簧T/4显示负速度−0.4',lambda:abs(page.evaluate('window.exerciseState().v')+.4)<1e-9)
        page.locator('[data-phase="0.75"]').click()
        check('弹簧3T/4显示正速度+0.4',lambda:abs(page.evaluate('window.exerciseState().v')-.4)<1e-9)
        page.locator('#m').fill('2')
        check('改变弹簧质量重置为t=0',lambda:float(page.locator('#time').input_value())==0)
        check('改变参数后状态为右端静止释放',lambda:abs(page.evaluate('window.exerciseState().v'))<1e-9)
        page.locator('#m').fill('0')
        check('弹簧无效参数有明确提示',lambda:'大于零' in page.locator('#status').inner_text())
        page.locator('#m').fill('1');page.locator('[data-phase="0.25"]').click();page.screenshot(path=str(PREVIEW/'02_spring_desktop.png'),full_page=True)
        goto('exercises/03_potential.html')
        check('平行板初值2.4V',lambda:abs(page.evaluate('window.exerciseState().V')-2.4)<1e-9)
        page.locator('[data-case="lower"]').click()
        check('下板上移后1.5V',lambda:abs(page.evaluate('window.exerciseState().V')-1.5)<1e-9)
        check('下板上移保持观察点4cm',lambda:float(page.locator('#p').input_value())==4)
        page.locator('[data-case="upper"]').click()
        check('上板下移后3V',lambda:abs(page.evaluate('window.exerciseState().V')-3)<1e-9)
        check('上板下移保持观察点4cm',lambda:float(page.locator('#p').input_value())==4)
        page.locator('#p').fill('20')
        check('点超出板间时清除有效结果',lambda:'无有效结果' in page.locator('#metrics').inner_text())
        page.locator('[data-case="initial"]').click();page.screenshot(path=str(PREVIEW/'03_potential_desktop.png'),full_page=True)
        goto('exercises/04_rc.html')
        for _ in range(4):page.locator('#step').click()
        before=page.evaluate('window.exerciseState().V')
        check('RC充电1τ电压正确',lambda:abs(before-3.1606027941427883)<1e-9)
        page.locator('#switch').click()
        check('RC开关切换电容电压不跳变',lambda:abs(page.evaluate('window.exerciseState().V')-before)<1e-12)
        check('RC放电电流改为负值',lambda:page.evaluate('window.exerciseState().i')<0)
        for _ in range(4):page.locator('#step').click()
        check('RC继续放电1τ电压正确',lambda:abs(page.evaluate('window.exerciseState().V')-1.1627207896741481)<1e-9)
        page.screenshot(path=str(PREVIEW/'04_rc_desktop.png'),full_page=True)
        page.locator('#R').fill('20')
        check('RC改变元件参数才复位电压',lambda:page.evaluate('window.exerciseState().V')==0)
        for name in ['01_paper_tape','02_spring','03_potential','04_rc']:
            page.set_viewport_size({'width':390,'height':844});goto('exercises/'+name+'.html')
            check(name+'手机宽度无整页横向溢出',lambda:page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'))
            page.screenshot(path=str(PREVIEW/(name+'_mobile.png')),full_page=True)
        page.set_viewport_size({'width':1280,'height':900});goto('book.html')
        check('阅读版含前后记及七章',lambda:page.locator('section.chapter').count()==9)
        check('阅读版含四幅新绘示意图',lambda:page.locator('figure img').count()==4)
        check('阅读版示意图全部加载',lambda:page.locator('figure img').evaluate_all('(els)=>els.every(e=>e.complete&&e.naturalWidth>0)'))
        page.screenshot(path=str(PREVIEW/'book_cover.png'),full_page=False)
        page.locator('#ch4').scroll_into_view_if_needed();page.screenshot(path=str(PREVIEW/'book_chapter4.png'),full_page=False)
        page.set_viewport_size({'width':390,'height':844});page.evaluate('window.scrollTo(0,0)')
        check('连续阅读版手机宽度无整页横向溢出',lambda:page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'))
        page.screenshot(path=str(PREVIEW/'book_mobile.png'),full_page=False)
        check('检查过程没有页面脚本异常',lambda:not errors)
        check('检查过程没有外部HTTP请求',lambda:not any(u.startswith(('http://','https://')) for u in requests))
        browser.close();write('completed')
except SystemExit:raise
except Exception as e:
    write('interrupted',str(e)+'\n'+traceback.format_exc()[-1500:])
