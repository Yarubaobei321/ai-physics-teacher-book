# 继续教育课程课件重制工作流

## 目标

把现有课程设计、旧 PPT 和逐字稿，重制为适合录屏讲授的 HTML 横向课件。课程按 4 个课时组织，每个课时拆成上下两个约 20 分钟小节，共 8 套课件。

## 输入材料

- 课程设计：`/Users/yaril/个人文档/深圳继续教育课程设计/课程详细教学设计（4课时版）.md`
- 旧课件与逐字稿：`/Users/yaril/个人文档/深圳继续教育课程设计/课件和逐字稿`
- 源材料摘要：`source/源材料摘要.md`

## 使用的 Skill 分工

1. `humanize-ppt`
   - 负责先做“能讲”的结构：受众状态、叙事弧、页面计划、素材清单。
   - 本轮已调用，输出在 `humanize-run/`。
   - 自动输出质量不足，因此保留调用记录，实际生产采用 `课程重制总方案.md` 中的人工校正版 AST。

2. `guizang-ppt-skill`
   - 负责最终 HTML 横向课件生成。
   - 本课程默认使用风格 B：瑞士国际主义。
   - 主题建议：IKB 蓝，适合 AI、工程化、流程与教育科技内容。

3. `baoyu-image-gen`
   - 负责生成封面、场景图、概念图。
   - 已配置为项目级 `codex-cli` 后端：`.baoyu-skills/baoyu-image-gen/EXTEND.md`。

4. `baoyu-infographic`
   - 负责生成课程流程、闭环模型、三问选题法等信息图。
   - 已配置为中文、16:9、Codex 后端：`.baoyu-skills/baoyu-infographic/EXTEND.md`。

5. `baoyu-article-illustrator`
   - 负责读取逐字稿或小节讲稿，判断哪些位置需要插图、场景图或概念图。
   - 输出配图 outline 和 prompt，之后再交给 `baoyu-image-gen` / Codex 图片后端生成。
   - 已配置为中文、Codex 后端、串行生成：`.baoyu-skills/baoyu-article-illustrator/EXTEND.md`。

6. `baoyu-diagram`
   - 负责确定性 SVG 图：流程图、架构图、决策树、闭环图、发布路径图。
   - 适合科学结构、技术链路、部署架构；不把这些内容交给图片模型自由发挥。

## 串行生产流程

每个小节都按以下顺序处理，不并行：

1. 读取对应逐字稿和旧 PPT 页面。
2. 用 `baoyu-article-illustrator` 思路分析逐字稿，列出“必须配图 / 可用 SVG / 不需要图”的页面。
3. 写该小节的 `deck_brief.md`、`slide_plan.json` 和 `speaker_intent.md`。
4. 对确定性流程/架构图，优先用 `baoyu-diagram` 生成 SVG。
5. 对封面、场景图、概念图，写 `baoyu-image-gen` prompt。
6. 对高密度流程、闭环、三问法，写 `baoyu-infographic` prompt。
7. 生成必要图片到 `assets/`。
8. 用 `guizang-ppt-skill` 瑞士风模板生成 HTML 课件到 `decks/`。
9. 本地打开检查，重点看大标题、底部导航安全区、图片比例、录屏可读性。
10. 通过后再进入下一个小节。

## 输出目录约定

```text
新课件制作工作流/
├── README.md
├── 课程重制总方案.md
├── source/
│   └── 源材料摘要.md
├── humanize-run/
│   └── humanize-ppt 自动输出
├── prompts/
│   ├── images/
│   └── infographics/
├── assets/
│   ├── images/
│   └── infographics/
└── decks/
    ├── 01-上-问题聚焦.html
    ├── 01-下-案例导览.html
    ├── 02-上-环境与提示词.html
    ├── 02-下-工程化协作.html
    ├── 03-上-设计到PRD.html
    ├── 03-下-开发与验收.html
    ├── 04-上-发布与合规.html
    └── 04-下-反馈闭环与迁移.html
```

## 风险与回滚

- 风险：图片生成会消耗 Codex/GPT Image 2 额度；批量生成容易受网络影响。
- 控制：所有图片 prompts 先保存，确认后逐张生成。
- 回滚：本目录所有产物都在项目内，可用 git 管理；建议开始批量生成前新建 branch 或提交当前版本。
