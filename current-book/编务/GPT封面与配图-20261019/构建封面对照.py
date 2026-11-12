from pathlib import Path
import json, html

R = Path(__file__).resolve().parent
items = json.loads((R/'生成文件映射.json').read_text())[:10]
cards = []
for item in items:
    href = '封面候选/' + Path(item['local']).name
    cards.append(f'<article><a href="{html.escape(href)}" target="_blank"><img loading="lazy" src="{html.escape(href)}" alt="{item["n"]:02d} {item["name"]}"></a><h2>{item["n"]:02d} · {html.escape(item["name"])}</h2><a href="{html.escape(href)}" download>下载原图</a></article>')
page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>把物理做出来 · 封面候选</title><style>
body{margin:0;background:#f5f2eb;color:#183a3a;font:16px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1400px;margin:auto;padding:36px 24px}h1{font-size:32px;margin:0}p{color:#59615e}a{color:#1a6563}header{margin-bottom:28px}.current{display:grid;grid-template-columns:minmax(240px,460px) 1fr;gap:34px;align-items:center;background:white;padding:24px;margin-bottom:48px;border:1px solid #ddd8ce}.current img{width:100%;height:auto}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}article{padding:14px;background:white;border:1px solid #ddd8ce}article img{width:100%;height:auto;display:block}h2{font-size:20px;margin:14px 0 4px}article p{margin:0 0 12px}@media(max-width:950px){.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:600px){.grid,.current{grid-template-columns:1fr}}</style>
<main><header><h1>《把物理做出来》封面</h1><p>GPT 图像模型生成 · 纸张拼贴风格 · 点击图片查看原图</p></header>
<section class="current"><a href="../../封面/把物理做出来-封面.png" target="_blank"><img src="../../封面/把物理做出来-封面.png" alt="当前修订封面"></a><div><h2>当前修订 · 综合实验封面</h2><p>移除装饰红线，放大四位作者署名，加入深圳市育才一中。</p><p>水槽放回黄、红、蓝三色小环；右侧换为电容器、刀开关和侧面磁吸触点；线圈核为四个接线柱。</p><p><a href="../../封面/把物理做出来-封面.png" download>下载当前封面</a>　<a href="../../全书阅读.html">打开全书阅读版</a></p><p>封面依据原照绘制，尺寸、颜色与布局有艺术化处理，不作为接线图或实测证据。</p></div></section><h2>十款构图对照</h2><p>第09款是当前修订的基础；下列保留该轮候选原貌。</p><section class="grid">'''
page += ''.join(cards) + '</section><p><a href="review.md">图件来源与本轮说明</a> · <a href="生成提示词与来源.json">提示词与参照材料</a></p></main></html>'
(R/'封面对照.html').write_text(page)
