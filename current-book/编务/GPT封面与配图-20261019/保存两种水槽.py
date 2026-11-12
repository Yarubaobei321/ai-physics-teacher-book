from pathlib import Path
import shutil
R = Path(__file__).resolve().parent
P = R.parents[1]
S = Path('/Users/yaril/.codex/generated_images/01a156f1-2b6b-77b0-8d05-363b254b55e8')
for src, name in [('exec-54268b09-7bc0-4747-a82a-fe6d1d34f04c.png','圆筒版-黄3红5蓝7.png'),('exec-2080e711-077c-4c31-b2c4-d39aebd6a712.png','平行板版-每色5个.png'),('exec-8eef8b00-8e9b-4e44-8bde-62cea9043f6f.png','六环版-磁吸归入模块.png')]:
    shutil.copy2(S/src, R/'封面候选'/name)
page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>两种水槽封面对照</title><style>body{background:#f4f1e9;color:#173c3c;font:17px/1.7 -apple-system,"PingFang SC",sans-serif;margin:30px}main{max-width:1400px;margin:auto}.grid{display:grid;grid-template-columns:1fr 1fr;gap:25px}article{background:white;padding:20px}img{width:100%;height:auto}a{color:#1c6763}h2{font-size:22px}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style><main><h1>两种水槽封面</h1><p>两版均已删除独立磁吸条，触点嵌在各拼图自身侧面。当前为比较稿，尚未替换全书封面。</p><div class="grid"><article><h2>A · 圆筒电极</h2><p>黄色3个、红色5个、蓝色7个，按同心层次对称排布。</p><a href="封面候选/圆筒版-黄3红5蓝7.png"><img src="封面候选/圆筒版-黄3红5蓝7.png" alt="圆筒版"></a></article><article><h2>B · 平行板电极</h2><p>三种颜色各5个，排为三列，与电极平行；对应板间中部近似匀强区域。</p><a href="封面候选/平行板版-每色5个.png"><img src="封面候选/平行板版-每色5个.png" alt="平行板版"></a></article></div></main></html>'''
(R/'两种水槽封面对照.html').write_text(page)
with (R/'review.md').open('a') as f:
    f.write('\n## 环数与模块磁吸修订\n\n删除独立磁吸条，触点嵌入两块拼图自身侧面。新增两种比较稿：圆筒版黄3红5蓝7；平行板版每色5个。逐个查看可见环数均符合要求，圆筒版第三个黄环已从螺柱顶部移回槽底。排列为插画概括，不是原测点坐标。等待作者选定，尚未替换全书HTML与Word/PDF。[两版比较](两种水槽封面对照.html)。\n')
with (P/'PROJECT_SUMMARY.md').open('a') as f:
    f.write('\n\n## 封面两种水槽比较稿\n\n按作者纠正，候选将磁吸触点归入每块拼图自身侧面，删除独立磁吸条。圆筒版黄3红5蓝7，平行板版每色5个。[并排比较](编务/GPT封面与配图-20261019/两种水槽封面对照.html)。等待选定，全书HTML/Word/PDF尚未采用这两张新候选。\n')
