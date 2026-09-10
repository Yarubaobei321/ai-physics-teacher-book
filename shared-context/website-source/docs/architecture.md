# 站点架构

## 路由

| 路径 | 入口文件 | 用途 |
|---|---|---|
| `/` | `src/pages/index.astro` | 门户首页（保留原版校园照片首屏与内容布局） |
| `/resources/` | `src/pages/resources.astro` | 38 项资源搜索、用途筛选与本机收藏 |
| `/project-learning/` | `src/pages/project-learning/index.astro` | 项目式学习入口（三类项目） |
| `/project-learning/new-grade-one/` | `src/pages/project-learning/new-grade-one.astro` | 新高一：五方案测 g + 数据工作台 |
| `/project-learning/new-grade-two/` | `src/pages/project-learning/new-grade-two.astro` | 新高二：力学综合探究 + 图像法工作台 |
| `/project-learning/dis-sensor/` | `src/pages/project-learning/dis-sensor.astro` | DIS 传感器实验介绍（ESP32 + 超声波） |
| `/project-learning/ultrasonic-lab/` | `src/pages/project-learning/ultrasonic-lab.astro` | 超声波小车网页实验室（Web Serial 烧录 + 实时作图） |
| `/maker/` | `src/pages/maker/index.astro` | 科创天地（课程模块 + 剪影轮播 + 项目入口） |
| `/maker/smart-car/` | `src/pages/maker/smart-car/index.astro` | 智能小车作品说明（原理长文档） |
| `/maker/mars-rover/` | `src/pages/maker/mars-rover/index.astro` | 尘光一号火星车作品说明（原理长文档） |
| `/projects/smart-car/` | `src/pages/projects/smart-car/index.astro` | 智能小车教学控制台（React island） |
| `/projects/mars-rover/` | `src/pages/projects/mars-rover/index.astro` | 火星车网页地面站（React island · Web Bluetooth） |
| `/programming/` | `src/pages/programming.astro` | 在线编程（Web Serial → ESP32） |
| `/dis/` | `src/pages/dis.astro` | 网页版 DIS（Web Bluetooth → ESP32） |
| `/online-lab/` | `src/pages/online-lab/index.astro` | 在线实验室入口（在线编程 / DIS / 案例实验） |
| `/online-lab/mechanical-energy/` | `src/pages/online-lab/mechanical-energy.astro` | 验证机械能守恒三方案入口 |
| `/online-lab/falling-body/` | `src/pages/online-lab/falling-body.astro` | 落体法验证机械能守恒 |
| `/online-lab/curved-ramp/` | `src/pages/online-lab/curved-ramp.astro` | 曲面下滑法验证机械能守恒 |
| `/online-lab/air-track/` | `src/pages/online-lab/air-track.astro` | 气垫导轨验证系统机械能守恒 |
| `/simulations/` | `src/pages/simulations/index.astro` | 模拟实验室入口：教师作品区（高考真题 + 动量）+ 学生 AI 素养评价 |
| `/simulations/gaokao/` | `src/pages/simulations/gaokao/index.astro` | 《智启格物》20 个本地高考真题模拟目录 |
| `/simulations/gaokao/2026-film-impact/` | `public/simulations/gaokao/2026-film-impact/index.html` | 2026 薄膜冲击独立交互模型与 10 项自检 |
| `/simulations/gaokao/<slug>/` | `public/simulations/gaokao/<slug>/index.html` | 其余 19 个共享底座模型；入口由生成器维护 |
| `/simulations/teacher/` | `src/pages/simulations/teacher.astro` | 教师作品 · 动量章节 6 个演示模型 |
| `/simulations/student-ai-lab/` | `src/pages/simulations/student-ai-lab/index.astro` | 学生 AI 素养评价（现场规则、双轨量规、匿名统计与 77 代号目录） |
| `/simulations/student-ai-lab/<alias>/` | `src/pages/simulations/student-ai-lab/[alias].astro` | 单代号证据链（对话、首版/提交版、v4 评分、最优提示词、DeepSeek 优化对照） |
| `/simulations/student-ai-audit/` | `astro.config.mjs` redirects | 旧复核页硬替换：重定向到学生 AI 素养评价 |
| `/simulations/momentum/*.html` | `public/simulations/momentum/` | 动量章节独立演示页 |
| `/photogate-comparison/` | `src/pages/photogate-comparison.astro` | 单头/双头光电门对比（由 `/dis/` 页面内链进入） |

> 学生作品库 `public/simulations/student-works/` 已于 2026-06-23「站点去机构化」提交中下线；复核结论见 `docs/student-ai-work-adversarial-review.md`。

## 关键共享组件

- `BaseLayout.astro` — 全站 `<head>` 元数据（OG / Twitter / canonical / theme-color / apple-touch-icon），并装载 `Header` / `Footer`。`title` / `description` / `ogImage` / `ogType` / `canonical` 可逐页覆盖。
- `Header.astro` — sticky 头；桌面显示五栏目与资源搜索入口，窄屏用原生 details 展开导航，支持 Escape 与点击外部关闭。DIS、在线编程、光电门对比归入在线实验室，控制台归入科创天地。
- `BrowserSupportNotice.astro` — Web Bluetooth / Web Serial 不支持时显示的琥珀色横幅；同时检测是否 secure context。在 `/dis/`、`/programming/` 顶部接入。
- `Hero.astro` — 按用户反馈恢复原版大幅校园照片首屏、原文案与标志放大功能。`PhotogateComparison.astro` 继续负责教程页。
- `ResourceCatalog.astro` + `src/data/resources.ts` — 独立 `/resources/` 页的跨栏目资源索引，样式为 `src/styles/resources.css`；动量与高考模型复用已有台账，搜索/分类覆盖全部 38 项，默认展示 8 项，可继续展开。本机收藏键为 `yucai:resource-favorites:v1`。
- `LabDraftNotice.astro` + `src/lib/lab-draft.ts` — 三套机械能实验的原始字段自动保存、恢复与删除。按实验分键，版本化校验，存储失败明确提示；多标签冲突时暂停自动覆盖。仅恢复参数和表格，不恢复设备连接、采集日志或预先存储的计算结果。
- `LabSectionNav.astro` — 三套机械能实验快捷导航，定位填写区、图像、回顾与习题。
- 三个 `*EnergyLab.astro`（FallingBody / AirTrack / CurvedRamp）— 每个机械能方案的主体（实验目的 / 器材 / 步骤 / 数据表 / 能量图），文件末尾追加 `<ExperimentReview>`，紧接其后由页面再渲染 `<ExerciseSection>`。
- `ExperimentReview.astro` — 通用「实验回顾」展示组件，由 `src/data/lab-reviews/*.ts` 驱动。
- `ExerciseSection.astro` — 通用「配套习题」交互组件（单选 / 多选 / 填空 / 简答），由 `src/data/exercises/*.ts` 驱动；section 自身有 `id="exercises-<slug>"` 锚点 + `scroll-mt-24`，避免被 sticky header 挡住。

## 数据约定

### 习题（`src/data/exercises/*.ts`）

类型定义在 `types.ts`：`SingleChoiceExercise` / `MultiChoiceExercise` / `FillExercise` / `OpenExercise`，共享 `number` / `difficulty` / `category` / `stem` / `explanation`（`stem` 与 `explanation` 都是 HTML 字符串，可包含 `<sub>` / `<sup>` / `<table>`）。

三套数据：

- `falling-body.ts` — 10 题
- `curved-ramp.ts` — 9 题
- `air-track.ts` — 9 题

页面 `*.astro` 中通过 `<ExerciseSection exercises={...} slug="..." title="..." />` 嵌入。

### 实验回顾（`src/data/lab-reviews/*.ts`）

`types.ts` 定义 `ExperimentReviewData`：`purpose` / `apparatus` / `procedure` / `formulas` / `parameters` / `notes`。
公式与上下标使用 `<sub>` / `<sup>` 与 unicode（v₁、v₂、Δh、E_k、E_p 等）。
被三个 `*EnergyLab.astro` 末尾的 `<ExperimentReview reviews={...} />` 消费。

### 站点元数据（`src/data/site.ts`）

导航、四工具说明、首页文案。修改导航不需要碰组件。

### 高考真题模拟（`src/data/gaokao-simulations.ts`）

保存《智启格物》使用的 20 道题的内部 ID、年份、专题、书中章节、交互重点与本地路由。当前 20 个模型均已在本地实现：薄膜冲击使用独立运行时和 10 项自检，其余 19 个模型共用 `gaokao-models.js`、`gaokao-model-page.js`、三个专题场景模块和 77 项物理回归测试。

19 个共享入口由 `scripts/generate-gaokao-model-pages.mjs` 生成。页面使用 `?view=book` 进入统一图书模式；测试、参数范围、当前计算结果和模型警告构成截图门禁。详细边界见 `docs/gaokao-simulations.md`。

截至 2026-08-02，这套页面只完成了本地构建与预览核验，尚未部署，尚未经过作者审核。架构文档中的“已实现”只描述本地文件状态，不代表线上可见或内容定稿。

### 学生 AI 素养评价（`src/data/student-ai-lab.json`）

`student-ai-lab.json` 是脱敏导出生成的内部页面数据，不手工维护，也不作为下载文件提供。每个代号只引用六类公开资源：关键对话、完整可见对话、DeepSeek 第一版、学生提交最终版、评审重构的最优提示词和 DeepSeek 优化对照。

详情页固定按“对话 → 首版/提交版 → v4 评分 → 最优提示词 → 优化对照”排列。学生 HTML 只在不含 `allow-same-origin` 的 iframe 沙箱中运行；公开资源不能包含姓名、班级、分享链接、本地路径、内部作品 ID 或原始评分 JSON。完整口径见 `docs/student-ai-literacy-evaluation.md`。

## 头跳转锚点

每个在线实验页面顶部含「跳到配套习题 ↓」按钮，`href="#exercises-<slug>"`。全局 `html { scroll-behavior: smooth }` 已开启（`src/styles/global.css`）；锚点在 `ExerciseSection` 上配 `scroll-mt-24` 抵消 sticky header。

## 资源约定

- 大于 50 KB 的图片必须有 `.webp` 和原格式两份，模板用 `<picture>` + `<source type="image/webp">`，并显式声明 `width` / `height` / `loading` / `decoding`。
- 上方折叠内可见的关键图（首屏 hero、教程页 hero）加 `fetchpriority="high"`；其它图懒加载。
- 站点 favicon 使用 `/logo-web.png`（337KB），不要回退到 `/logo.png`（1.5MB）。
- OG 默认图 `/campus.jpeg`（1000×562），可由各页面 `ogImage` prop 覆盖。

## 测试

- `npm test` 先运行学生 AI 素养评价数据门禁，再运行 `scripts/verify-site.mjs`（结构性检查：logo 引用、导航项、学生页面顺序、20 个高考模型入口、19 模型 77 项共享回归、薄膜冲击 10 项自检、场景语义与极端参数边界等）。
- `npm run generate:gaokao-pages -- --all --check` 核对 19 个共享模型入口与当前规格、专用场景清单一致。
- `npm run validate:student-ai-lab` 校验 77 条证据链、六类资源、v4 分数求和、特殊状态和公开隐私门禁；可选环境变量 `STUDENT_AI_LAB_NAME_LIST` 或 `STUDENT_AI_LAB_ALIAS_MAP` 做本地真名/班级零命中检查。
- 首页与草稿交互回归为 `scripts/browser-site-usability-checks.js`，通过 Playwright MCP `browser_run_code_unsafe(filename)` 执行；入口 page 需指向本机生产预览，脚本创建隔离浏览器上下文。2026-09-05 反馈调整后的 52 项检查包括真实链接、过滤、收藏、手机导航、草稿刷新恢复、CSV 一致性、损坏/禁用存储与多标签冲突。
