from 执行 import *
# 提升真实画布像素密度；逻辑坐标、曲线数据、页面尺寸均保持原值。
for chapter in ['05-超声波','06-视重数据']:
 for name in (['index.html','生成页面.py'] if chapter.startswith('05') else ['分析页.html','生成页面.py']):
  p=S/'05-数据与传感器/output'/chapter/name;t=p.read_text();old=t
  if chapter.startswith('05'):
   for cid,ctx,W,H in [('cDist','dctx','Wd','Hd'),('cVel','vctx','Wv','Hv')]:
    a=f'var {ctx}=$("{cid}").getContext("2d");\n  var {W}=$("{cid}").width, {H}=$("{cid}").height;'
    b=f'var {W}=1000, {H}=300, density=Math.max(1,window.devicePixelRatio||1);\n  $("{cid}").width={W}*density; $("{cid}").height={H}*density;\n  var {ctx}=$("{cid}").getContext("2d"); {ctx}.setTransform(density,0,0,density,0,0);'
    assert a in t,(p,cid);t=t.replace(a,b)
  else:
   a='var c=$(canvasId), ctx=c.getContext("2d");\n  var W=c.width, H=c.height, pad={l:66,r:20,t:20,b:36};'
   b='var c=$(canvasId), density=Math.max(1,window.devicePixelRatio||1);\n  var W=1000, H=330, pad={l:66,r:20,t:20,b:36};\n  c.width=W*density; c.height=H*density;\n  var ctx=c.getContext("2d"); ctx.setTransform(density,0,0,density,0,0);'
   assert a in t,p;t=t.replace(a,b)
  if t!=old:
   save(p);q=p.with_name(p.name+'.修改前-20261013')
   if not q.exists():shutil.copy2(p,q)
   p.write_text(t)
for ch,src,pack in [('ch05',S/'05-数据与传感器/output/05-超声波/index.html',P/'配套包/第05章/超声波历史记录分析页.html'),('ch06',S/'05-数据与传感器/output/06-视重数据/分析页.html',P/'配套包/第06章/视重构造数据分析页.html')]:
 shutil.copy2(src,R/'网页预览'/ch/'index.html')
 t=src.read_text().replace('非本轮新测量','历史记录复算');pack.write_text(t)
p=P/'正文/第16章-活版电路拼图/配套/电容电流积分.html';t=p.read_text()
t=t.replace('ctx.translate((gapL+gapR)/2, y0 + 14); ctx.rotate(-Math.PI/2);','ctx.translate((gapL+gapR)/2, y0 + 14); ctx.rotate(-Math.PI/2); ctx.textAlign = "right";')
# 下面紧随的一行可能重设对齐，连同修正
s=t.index("ctx.fillText('开关切换")
print(t[s-220:s+90])
for expr,scale in [('Math.abs(whole.tot.net) / 1000','(whole.tot.pos + whole.tot.neg) / 1000'),('Math.abs(c.tot.net)/1000','(c.tot.pos + c.tot.neg)/1000')]:
 t=t.replace(f'fmtSig({expr}, 9)',f'netDisplay({expr}, {scale}, 9)')
p.write_text(t);shutil.copy2(p,R/'网页预览/ch14/index.html');shutil.copy2(p,P/'配套包/第14章/电流积分页.html')
