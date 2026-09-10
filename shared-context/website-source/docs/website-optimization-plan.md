# 数智育才网站优化计划

> 2026-06-11 编制。重点：各模拟实验页面的显示效果与教学效果优化。
> 优先级说明：P0 = 影响课堂使用的硬伤，立即做；P1 = 显著提升体验/教学效果；P2 = 锦上添花；P3 = 工程保障。
> 工作量按「小 = 半天内 / 中 = 1–2 天 / 大 = 3 天以上」估算。

## 现状总览

| 板块 | 路径 | 现状 |
|---|---|---|
| 模拟实验室（动量章 6 模型） | `public/simulations/momentum/*.html` | 独立单文件 HTML，Canvas + 参数面板，每页约 2000+ 行 |
| 学生作品库（25 份） | `public/simulations/student-works/` + `src/data/student-works.ts` | 独立 HTML，AI 协作完成，已有评分与版本记录 |
| 在线实验室（机械能 3 实验） | `src/pages/online-lab/` | Astro 组件，数据表 + Canvas + 配套习题（ExerciseSection） |
| 网页版 DIS | `src/pages/dis.astro`（DisPanel，1337 行） | Web Bluetooth + Canvas 实时曲线 |
| 在线编程 | `src/pages/programming.astro` | Web Serial + 模板 |
| 火星车地面站 | `src/pages/projects/mars-rover/` | 2026-06 已合并 React 版三视图地面站 |

---

## A. 模拟实验室 6 个动量模型页（重点）

涉及文件：`public/simulations/momentum/` 下 `spring-ball-block-model.html`、`ball-ring-model.html`、`suspended-ring-pendulum-model.html`、`ball-semicircular-groove-model.html`、`ball-curved-cart-model.html`、`slider-curved-track-model.html`。

### A1. 显示效果

#### A1-1 Canvas 高分屏模糊（P0，小×6）
**已核实**：6 个页面全部没有 `devicePixelRatio` 处理。在视网膜屏、4K 教室投影上，动画和文字发虚，是最直观的显示质量问题。

统一修法（每页的 canvas 初始化处）：

```js
function setupCanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  canvas.getContext('2d').setTransform(dpr, 0, 0, dpr, 0, 0);
}
```

注意：页面里所有以 `canvas.width/height` 为坐标系的绘制代码要改为以 CSS 尺寸（`rect.width/height`）为基准；`resize` 监听里同步重建。逐页改造，改完一页在投影/外接 4K 屏上抽查一页。

#### A1-2 公式渲染库三态并存（P0，小）
**已核实**：3 页用 MathJax CDN（`cdn.jsdelivr.net/npm/mathjax@3`）、1 页用 KaTeX CDN、2 页无公式库。教室断网或 CDN 被墙时，半数页面公式直接裂开；两套库视觉风格也不一致。

方案：统一为 **本地自托管 KaTeX**（比 MathJax 小一个量级、渲染快）：
1. 把 `katex.min.css`、`katex.min.js`、`auto-render.min.js`、字体目录放入 `public/vendor/katex/`；
2. 6 页统一替换 `<script src>` 指向本地路径；
3. 用 MathJax 的 3 页需把 `\( \)` 定界符配置迁到 KaTeX auto-render 的 `delimiters` 选项，逐页核对公式渲染结果（KaTeX 不支持的宏需就地改写）。

#### A1-3 移动端 / 窄屏适配（P1，中）
**已核实**：每页仅 3–8 个 `@media`。学生平板/手机上控制面板挤压画布。统一规范：
- ≤768px 时参数面板折叠为可展开抽屉，画布占满宽度；
- 滑块触控目标 ≥44px；
- 按钮组允许横向滚动而非换行挤压。

#### A1-4 统一外壳与导航（P1，中）
现状：独立 HTML 无站点导航，风格各异，从模拟页无法回站。

两案对比：
- **方案甲（推荐）**：保留独立 HTML（优点：与 25 份学生作品同构、教师可拷走单文件离线用），抽一份共享 `public/simulations/sim-shell.css` + 每页顶部统一加一条返回栏（站点 logo + 「← 返回模拟实验室」+ 模型标题），配色对齐育才蓝。
- 方案乙：`simulations.astro` 做统一详情页模板，iframe 包裹各 HTML。缺点：iframe 内滚动/全屏/移动端体验差，公式与画布尺寸联动复杂，不推荐。

### A2. 教学效果

#### A2-1 慢放 / 单步 / 逐帧（P0，中）
碰撞、绳绷直、弹簧最大压缩这些「瞬间」是动量教学的核心，而实时速度下学生根本看不清。统一给 6 页加：
- 速度档：0.1× / 0.25× / 0.5× / 1×（实现上即给物理步长乘系数，注意保持定步长积分稳定性）；
- 「单步」按钮：暂停态下每按一次推进一个固定物理时间步；
- 键盘空格 = 暂停/继续，方向键 = 单步（教师拿翻页笔也能控制）。

#### A2-2 物理量可视化分层（P0，大）
让「守恒」看得见，是模拟实验对真实实验的核心增值。每个模型按适用性增加可独立开关的图层：
- **速度 / 动量矢量箭头**：跟随物体绘制，长度按比例；
- **动量条形图**：m₁v₁、m₂v₂ 与总动量三根条，实时更新——总动量条「纹丝不动」就是动量守恒最直观的呈现；
- **能量堆叠条**：动能/势能/弹性势能/已损耗，总高恒定（或损耗增长），完全弹性与非弹性碰撞一眼可辨；
- 图层开关默认关闭矢量、开启条形图，避免画面过载。

#### A2-3 参数预设 + 「先预测再播放」引导（P1，中）
每个模型内置 2–3 组教学预设（如弹簧模型：等质量对碰 / 大碰小 / 小碰大），每组预设配一个引导问题（「碰后两球速度方向如何？先选择再播放验证」）。问题以折叠卡片放在参数面板顶部，与 `src/data/exercises/` 已有习题体系风格一致；预测-验证是被验证最有效的模拟实验教学法。

#### A2-4 v-t 图与动画时间轴联动（P2，中）
现有 v-t 图与动画各画各的。加联动游标：动画进行时 v-t 图上画当前时刻竖线；暂停后拖动 v-t 图游标可回溯动画到对应时刻（需要保留状态历史环形缓冲）。数据可导出 CSV，与在线实验室体验对齐。

#### A2-5 教师演示模式（P2，小）
一键切换：字号放大 1.25×、线宽加粗、隐藏次要面板、高对比配色——适配教室投影低对比环境。一个 `body.classroom` 类 + 一段覆盖 CSS 即可。

### A 板块实施顺序建议

1. A1-1 DPR（6 页机械修改，立竿见影）→ 2. A1-2 KaTeX 本地化 → 3. A2-1 慢放单步 → 4. A2-2 可视化分层（先做弹簧模型打样，验证后推广到其余 5 页）→ 5. A1-4 统一外壳 → 6. A2-3 预设引导 → 7. 其余 P2。

---

## B. 在线实验室 3 页（落体 / 曲面 / 气垫导轨）

- **B1（P2，中）**：三个组件（829 / 1447 / 1536 行）各自实现 Canvas 绘图与数据表逻辑。抽共享工具到 `src/lib/`（如 `chart.ts`：坐标轴/网格/折线/导出；`datatable.ts`：行增删/校验/CSV），降维护成本——本次火星车合并已建立 `src/lib/` 目录，正好沿用。
- **B2（P2，小）**：补「误差与不确定度」引导：在能量对比表后加讨论卡片（「ΔE 为何总略小于 0？列出三个可能原因」），把『误差』从尴尬变成教学素材。
- **B3（P1，小）**：实验页 Canvas 同样无 DPR 处理的，一并按 A1-1 修。

## C. 网页版 DIS 与在线编程

- **C1（P1，小）**：`DisPanel.astro` 的实时曲线 Canvas 补 DPR（同 A1-1）。
- **C2（P1，中）**：曲线加缩放与游标读数（捏合/滚轮缩放时间轴，悬停显示 t、v 数值）——光电门时间差读数靠肉眼对曲线很不精确。
- **C3（P2，小）**：补全演示数据模式（参考火星车 `demoTelemetry` 的做法：无硬件时生成合理波形），教师备课与学生课前预习不依赖实物。

## D. 学生作品库（25 份）

- **D1（P2，中）**：`simulations.astro` 列表加筛选（按物理主题/班级/评分区间）与缩略图（构建时用 Playwright 批量截图存 `public/simulations/thumbs/`）。
- **D2（P2，小）**：作品页顶部统一加返回栏（与 A1-4 共用 sim-shell 方案）；「AI 协作过程」做成折叠时间线展示版本演进，本身就是「如何与 AI 协作做物理模拟」的教学素材。
- **D3（P1，小）**：学生作品同样普遍缺 DPR 与本地公式库——新作品入库前用 E1 校验脚本把关，存量作品视使用频率逐步修。

## E. 工程化保障

- **E1（P3，小）**：扩展 `scripts/verify-site.mjs`：扫描 `public/simulations/**/*.html`，检查 ① 是否引用外部 CDN（应为本地 vendor）② 是否含 `<title>` ③ 是否含返回栏标记 ④ 是否调用 DPR 初始化。作为 `npm test` 的一部分。
- **E2（说明，无需动作）**：本次合并引入的 React 仅在 `/projects/mars-rover/` 一个页面 hydrate（islands 架构），其余页面零 JS 增量，无性能回归。
- **E3（P3，小）**：为 `public/vendor/` 写一份 README 记录各库版本与升级方式。

## 总优先级一览

| 优先级 | 项目 | 工作量 |
|---|---|---|
| P0 | A1-1 六模型页 Canvas DPR | 小×6 |
| P0 | A1-2 公式库统一本地 KaTeX | 小 |
| P0 | A2-1 慢放/单步/逐帧 | 中 |
| P0 | A2-2 动量/能量可视化分层 | 大（先打样一页） |
| P1 | A1-3 移动端适配、A1-4 统一外壳、A2-3 预设引导、B3/C1 DPR、C2 曲线游标、D3 入库校验 | 小–中 |
| P2 | A2-4 时间轴联动、A2-5 演示模式、B1 共享绘图库、B2 误差引导、C3 演示数据、D1/D2 作品库 | 小–中 |
| P3 | E1 校验脚本、E3 vendor 文档 | 小 |
