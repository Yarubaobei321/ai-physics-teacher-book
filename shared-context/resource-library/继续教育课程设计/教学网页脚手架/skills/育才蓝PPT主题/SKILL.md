# Skill：育才蓝 PPT 主题

> 用 PptxGenJS 生成"育才蓝"风格、信息密度高、排版干净的课件。
> 方法借鉴 MiniMax 开源 pptx-generator（主题对象契约、页码徽标、5 类版式、QA 清单），配色用《育才设计令牌》。

## 何时用
当我说"按育才蓝主题做/改一份 PPT/课件"时执行。

## 工具链
- `npm install pptxgenjs`（生成）
- `pip install "markitdown[pptx]"` 或 python-pptx（读取/QA）

## 主题契约（见同目录 theme.js）
- 颜色键：`primary`(育才蓝0B63C7)、`secondary`(深蓝)、`ink`(墨蓝正文)、`accent`(信号橙)、`ok`(绿)、`danger`(红)、`light`(浅蓝)、`bg`(浅灰)、`line`、`muted`。
- 画布：LAYOUT_16x9（10" × 5.625"）；中文字体 Microsoft YaHei。
- 颜色用 6 位 hex 不带 `#`；透明度用 `opacity`/`transparency` 属性，**不要**写进 hex（否则文件损坏）。

## 五类版式（每页归一类）
1. 封面 Cover；2. 目录/任务总览 TOC；3. 章节过渡 Divider；4. 内容 Content（文本/混排/数据/对比/流程/图示）；5. 小结/作业 Summary。

## 高信息密度与排版规范
- 标题 24–28pt 加粗育才蓝；正文 12–15pt 墨蓝；关键数字/统计 40–60pt。
- **正文左对齐**，仅标题居中；卡片化分块，块间距统一 0.2–0.3"。
- 每页至少一个非文字元素（卡片/序号圆点/图示/对比块）；同一副牌避免连续重复版式。
- **不要**标题下划线（AI 痕迹）；不要低对比度文字。
- 除封面外每页右下角加页码徽标。

## 助手函数（theme.js）
`base(pres,slide)` 背景+品牌条+页脚；`header(pres,slide,{kicker,title})` 标题区并返回内容起始 y；`card(...)` 卡片；`numDot(...)` 序号圆点；`pageBadge(pres,slide,n)` 页码。

## 工作流
1. 按逐字稿/大纲规划每页类型与内容。
2. 写构建脚本：`const pptx=require('pptxgenjs'); const T=require('./theme.js')`，逐页 `pres.addSlide()` 调助手填充。
3. `node build.js` 生成 .pptx。
4. QA：`python -m markitdown out.pptx` 查漏字/占位/页码；渲染缩略图核对密度与对齐；至少一轮"改-再验"。

## 参考
- MiniMax 开源：https://github.com/MiniMax-AI/skills （skills/pptx-generator）
- 配色：本脚手架《参考/育才设计令牌》
