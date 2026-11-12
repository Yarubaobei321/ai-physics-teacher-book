import numpy as np, json, re, math, hashlib, xml.etree.ElementTree as ET
from pathlib import Path
r=Path(__file__).resolve().parents[1]/'实操/03-水槽预测与测点/output/第12章'
z=np.load(r/'tank-field-0.5mm.npz');a=z['ax'];p=z['phi'];ex=-z['dphidx'];ey=-z['dphidy'];mid=len(a)//2
root=ET.parse(r/'tank-prediction.svg').getroot();ns={'s':'http://www.w3.org/2000/svg'};polys=root.findall('.//s:polygon',ns)
arrows=[]
for q in polys:
 tx,ty,deg=map(float,re.fullmatch(r'translate\(([-.\d]+),([-.\d]+)\) rotate\(([-.\d]+)\)',q.attrib['transform']).groups())
 x=tx-155;y=155-ty;i=int(np.argmin(abs(a-y)));j=int(np.argmin(abs(a-x)))
 e=np.array([ex[i,j],-ey[i,j]]);d=np.array([math.cos(math.radians(deg)),math.sin(math.radians(deg))]);dot=float(e@d/np.linalg.norm(e))
 arrows.append({'transform':q.attrib['transform'],'dot_with_local_E_screen':dot})
for q in root.findall('.//s:path',ns):
 if not ((q.attrib.get('stroke')=='#2f8f83' and q.attrib.get('stroke-width')=='0.5') or q.attrib.get('fill')=='#2f8f83'):continue
 nums=list(map(float,re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?',q.attrib['d'])))
 if len(nums)!=6:continue
 b1,tip,b2=np.array(nums).reshape(3,2);d=tip-(b1+b2)/2;d=d/np.linalg.norm(d)
 tx,ty=tip;x=tx-155;y=155-ty;i=int(np.argmin(abs(a-y)));j=int(np.argmin(abs(a-x)))
 e=np.array([ex[i,j],-ey[i,j]]);dot=float(e@d/np.linalg.norm(e))
 arrows.append({'path':q.attrib['d'],'dot_with_local_E_screen':dot})
res={'sources':{f:hashlib.sha256((r/f).read_bytes()).hexdigest() for f in ['solve_tank.py','generate_ch12.py','tank-field-0.5mm.npz','tank-prediction.svg']},'center':float(p[mid,mid]),'min':float(p.min()),'max':float(p.max()),'upDownReflectionMaxError':float(np.max(abs(p+p[::-1,:]-1))),'leftRightMaxError':float(np.max(abs(p-p[:,::-1]))),'centerEx_per_mm':float(ex[mid,mid]),'centerEy_per_mm':float(ey[mid,mid]),'svgSize':root.attrib,'arrows':arrows,'arrow_direction_pass':bool(arrows) and all(q['dot_with_local_E_screen']>.9 for q in arrows)}
print(json.dumps(res,ensure_ascii=False,indent=2))
