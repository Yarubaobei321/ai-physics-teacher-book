"""Read existing grids only; independently interpolate/fit original points, never rerun solver."""
import csv,json,hashlib
import numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1]
O=R/'实操/03-水槽预测与测点/output'
source=Path('/Users/yaril/Documents/“AI赋能教师”专项培训/精品课/静电场分组实验/实测记录/260930坐标纸 实测/网页重建结果/网页记录（可导入）/0930坐标纸实测-B-匀强.efield.json')
S=json.loads(source.read_text()); cp=O.parent/'input/第14章-平行板15点.csv'
rows=list(csv.DictReader(cp.open(encoding='utf-8-sig')))
x=np.array([float(q['x_mm']) for q in rows]);y=np.array([float(q['y_mm']) for q in rows]);v=np.array([float(q['potential_V']) for q in rows]);ids=np.array([int(q['id']) for q in rows]);mask=np.isin(ids,[1,6,11]);summary_path=O/'第14章/fit-summary.json';summary=json.loads(summary_path.read_text());reported={}
for name, entries in summary['fits'].items():
 reported[name]={'Ey_V_per_m':summary['Ey_V_per_m'][name]}
 for tag,key in [('fitA_fixNeg0','A'),('fitB_freeAB','B')]:
  q=entries[key];reported[name][tag]={'a':q['a'],'b':q['b'],'rms_fit':q['rms_fit'],'rms_check':q['rms_chk'],'maxabs_check':q['max_chk']}
source_ok=len(rows)==len(S['points']) and all(float(q['x_mm'])==p['x'] and float(q['y_mm'])==p['y'] and q['color']==p['ringColor'] and float(q['potential_V'])==S['colorMap'][p['ringColor']]['actual'] for q,p in zip(rows,S['points']))
def at(a,z):
 i=np.searchsorted(a,x,side='right')-1;j=np.searchsorted(a,y,side='right')-1
 tx=(x-a[i])/(a[i+1]-a[i]);ty=(y-a[j])/(a[j+1]-a[j])
 return (1-ty)*((1-tx)*z[j,i]+tx*z[j,i+1])+ty*((1-tx)*z[j+1,i]+tx*z[j+1,i+1])
def metric(pred):
 e=pred-v
 return dict(rms_fit=float(np.sqrt(np.mean(e[~mask]**2))),rms_check=float(np.sqrt(np.mean(e[mask]**2))),maxabs_check=float(np.max(abs(e[mask]))))
out={'report_source':str(summary_path),'report_sha256':hashlib.sha256(summary_path.read_bytes()).hexdigest(),'source':str(source),'csv_source_coordinates_colors_potentials_exact':source_ok,'input_sha256':hashlib.sha256(cp.read_bytes()).hexdigest(),'check_ids':ids[mask].tolist(),'training_ids':ids[~mask].tolist(),'source_original_nHold':S['recon']['versions'][-1]['nHold'],'scope':'Local independent numerical reproduction from saved float32 grids; no new solve or browser check','models':{}}
for name,gp in [('180',O/'第12章/tank-field-0.5mm.npz'),('184',O/'第14章/tank-model-184_field-0.5mm.npz')]:
 z=np.load(gp);a=z['ax'].astype(float);field=z['phi'].astype(float);u=at(a,field);uf=u[~mask];vf=v[~mask];b=float(uf@vf/(uf@uf));aa,c=np.linalg.lstsq(np.column_stack((np.ones(len(uf)),uf)),vf,rcond=None)[0]
 mod={'grid_sha256':hashlib.sha256(gp.read_bytes()).hexdigest(),'grid_range':[float(field.min()),float(field.max())],'center':float(field[len(a)//2,len(a)//2]),'up_down_symmetry_error':float(np.max(abs(field+field[::-1,:]-1))),'fits':{}}
 for tag,lo,hi in [('fitA_fixNeg0',0.,b),('fitB_freeAB',float(aa),float(aa+c))]:
  pred=lo+(hi-lo)*u;metrics=metric(pred);d={'a':lo,'b':hi,**metrics};expected=reported[name][tag];d['max_difference_vs_report']=max(abs(d[k]-expected[k]) for k in ('a','b','rms_fit','rms_check','maxabs_check'));d['matches_saved_report']=d['max_difference_vs_report']<1e-6;mod['fits'][tag]=d
 ey=-b*at(a,np.gradient(field,float(a[1]-a[0]),axis=0))*1000
 mod['Ey_V_per_m']=ey.tolist();mod['Ey_max_difference_vs_report']=float(np.max(abs(ey-np.array(reported[name]['Ey_V_per_m']))));out['models'][name]=mod
out['pass']=source_ok and all(all(m['matches_saved_report'] for m in g['fits'].values()) and g['Ey_max_difference_vs_report']<.001 for g in out['models'].values())
print(json.dumps(out,ensure_ascii=False,indent=2))
