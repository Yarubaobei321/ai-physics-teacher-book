# 01-上 guizang 生产提示

请使用 `/Users/yaril/.codex/skills/guizang-ppt-skill/SKILL.md` 生成一份中文 HTML 横向课件。

## 基本信息

- 输出文件：`/Users/yaril/个人文档/深圳继续教育课程设计/新课件制作工作流/decks/01-上-问题聚焦.html`
- 标题：`问题聚焦：AI时代，教师从资源使用者到校本资源开发者`
- 用途：继续教育课程录屏，约 20 分钟。
- 受众：中小学教师，多数零编程基础。
- 风格：风格 B · 瑞士国际主义。
- Accent：IKB 蓝。
- 版式规则：正文页必须使用已登记的 S01-S22 或明确允许的封面/结尾版式；每页写 `data-layout`。

## 页面计划

读取并遵守：

`/Users/yaril/个人文档/深圳继续教育课程设计/新课件制作工作流/01-上-slide-plan.json`

## 素材

已规划但未必已生成：

- `assets/images/01-上-01-cover.png`
- `assets/infographics/01-上-02-course-path.png`
- `assets/infographics/01-上-04-home-school-gap.png`
- `assets/infographics/01-上-07-demand-validation.png`

如果素材文件不存在，先使用模板内的几何占位块，不要引用不存在文件导致破图。占位块要保留同样的 16:9 槽位，并在源码注释里标出应替换的素材路径。

## 录屏要求

- 页面字数少，能投屏读清楚。
- 每页都要能支撑 1.5–2.5 分钟讲述，不要只有一句装饰性标题。
- 不要把逐字稿塞进 PPT。
- 不要使用 emoji。
- 不要生成 sponsor 信息。
- 底部导航和页码不得遮挡内容。

## 质检

生成后运行：

```bash
node /Users/yaril/.codex/skills/guizang-ppt-skill/scripts/validate-swiss-deck.mjs /Users/yaril/个人文档/深圳继续教育课程设计/新课件制作工作流/decks/01-上-问题聚焦.html
```

然后用浏览器打开检查 16:9 录屏画面。
