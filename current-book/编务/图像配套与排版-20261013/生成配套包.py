from 执行 import *
import re,zipfile
Q=P/'配套包';Q.mkdir(exist_ok=True)
base={
 '【书】':str(P),'【实操】':str(S),
 '【圆弧】':'/Users/yaril/个人文档/3 写作/微信文章项目/文章重写/02-物理可视化教学系列/实操/20261001-WorkBuddy续作/教程/配套',
 '【建模】':'/Users/yaril/个人文档/3 写作/微信文章项目/文章重写/01-ESP32与传感器Blender建模/WorkBuddy教程-20261001/试做工作空间'}
manifest=[]
for line in (P/'编务/全书审核修订-20261012/配套包映射.md').read_text().splitlines():
 if not line.startswith('| `配套包/'):continue
 cols=re.split(r'(?<!\\)\|',line);target=re.search(r'`([^`]+)`',cols[1])[1];source=re.search(r'`([^`]+)`',cols[2])[1]
 if '可选' in cols[4]:continue
 if target.endswith('master.blend'):
  manifest.append({'target':target,'status':'待作者确认分发权利，未放入'});continue
 for a,b in base.items():source=source.replace(a,b)
 src=Path(source);dst=P/target
 # 第17章改成此次PNG，文中与附录同步扩展名
 if target.endswith('只点示例B的浏览器截图.jpg'):
  src=src.with_name('示例B未同步-v2.png');dst=dst.with_suffix('.png')
 if target.endswith('再点计算的浏览器截图.jpg'):
  src=src.with_name('按输入重新计算-v2.png');dst=dst.with_suffix('.png')
 if not src.exists():
  manifest.append({'target':str(dst.relative_to(P)),'source':str(src),'status':'待完成'});continue
 dst.parent.mkdir(parents=True,exist_ok=True)
 if src.is_dir():
  dst.mkdir(exist_ok=True)
  for f in src.glob('*.stl'):shutil.copy2(f,dst/f.name)
 else:shutil.copy2(src,dst)
 manifest.append({'target':str(dst.relative_to(P)),'source':str(src),'status':'已复制，待清理核验'})
(R/'配套打包记录.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print('映射条目',len(manifest),'暂缺',sum(x['status']=='待完成' for x in manifest))
