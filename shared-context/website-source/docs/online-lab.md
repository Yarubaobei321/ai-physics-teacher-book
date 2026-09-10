# 在线实验室

主题：**机械能守恒定律**。三套互补的方案。

| 方案 | URL | 主体组件 | 习题数据 | 实验回顾数据 |
|---|---|---|---|---|
| 落体法 | `/online-lab/falling-body/` | `FallingBodyEnergyLab.astro` | `src/data/exercises/falling-body.ts` (10 题) | `src/data/lab-reviews/falling-body.ts` |
| 曲面下滑 | `/online-lab/curved-ramp/` | `CurvedRampEnergyLab.astro` | `src/data/exercises/curved-ramp.ts` (9 题) | `src/data/lab-reviews/curved-ramp.ts` |
| 气垫导轨 | `/online-lab/air-track/` | `AirTrackEnergyLab.astro` | `src/data/exercises/air-track.ts` (9 题) | `src/data/lab-reviews/air-track.ts` |

## 页面渲染顺序

```
<BaseLayout>
  <XxxEnergyLab />        ← 实验主体（实验目的 / 器材 / 步骤 / 数据表 / 能量图）
                           └ 末尾追加 <ExperimentReview />
  <ExerciseSection />      ← 配套习题
</BaseLayout>
```

页面顶部含「跳到配套习题 ↓」按钮，锚点 `#exercises-<slug>`，由 `scroll-mt-24` 抵消 sticky header。

## 习题数据结构

类型在 `src/data/exercises/types.ts`：

```ts
type ExerciseDifficulty = '基础' | '中等' | '挑战' | '拓展';
interface ExerciseBase {
  number: number;
  difficulty: ExerciseDifficulty;
  category: string;          // '选择题' / '多选题' / '填空题' / '计算与数据处理' / '误差分析与改进'
  stem: string;              // HTML
  explanation: string;       // HTML
}
type Exercise =
  | (SingleChoice {kind:'single'; choices; answer})
  | (MultiChoice  {kind:'multi';  choices; answer:string[]})
  | (Fill         {kind:'fill';   blanks:[{id, answer, alternates?}]})
  | (Open         {kind:'open'});
```

`stem` 与 `explanation` 都直接渲染为 HTML，可包含 `<sub>` / `<sup>` / `<table>` / `<strong>` 等。`fill` 题的 `stem` 用 `{{blankId}}` 占位，运行时被 `<input class="exercise-blank">` 替换。

## 习题交互行为（`ExerciseSection.astro`）

- **单选 / 多选**：点选立刻有视觉反馈；提交后给每个选项打 `correct/wrong/missed`，整体 `correct/partial/wrong`；可"查看详解" / "重做"。
- **填空**：归一化（去空白、统一中英文逗号、忽略大小写）后比对，可填入参考答案。
- **简答 / 计算**：直接「查看参考解答」。
- 所有题目支持折叠展开 `<div class="exercise-explanation">`，默认 hidden。

## 实验回顾（`ExperimentReview.astro`）

数据结构在 `src/data/lab-reviews/types.ts`：

```ts
interface ExperimentReviewData {
  eyebrow?: string;          // 默认 'LAB REVIEW · 实验回顾'
  title?: string;            // 默认 '实验回顾'
  purpose: string;           // HTML
  apparatus?: string[];      // 标签气泡
  procedure?: ReviewListItem[];  // 步骤
  formulas?: ReviewFormulaItem[]; // label + expression + note
  parameters?: ReviewParameterItem[];  // symbol + value + description
  notes?: string[];          // 误差与注意事项
}
```

布局采用 12 列响应式网格：apparatus(5) + parameters(7) → formulas(满宽) → procedure(7) + notes(5)。任意字段缺省自动折叠空块。

## 更新记录（维护）

- **2026-04-27**：网页版 DIS 光电门数据表将单头类时间列统一为「遮光时间」、双头类为「双门时间差」；三种机械能守恒在线实验的数据区将「一键清零」改为「一键数据清除」、去掉主数据表中的「结论提示」列及侧栏「实验结论提示」；落体法方案器材与步骤改为电火花计时器 + 220V 交流、说明 0 号点含义，数据表扩展为 10 个计数点；曲面下滑方案相对 D 的高度改为 **cm** 输入（计算仍用 m）。
- **2026-04-27（晚）**：两单头/两双头「四光电门」模式下图表区并排展示 **速度** 与 **挡光时间/双门时间差** 两幅柱状图，表格列与图轴一致；两单头时间列、图轴称为「挡光时间」以对接实验用语。
- **2026-04-27（夜）**：DIS 四光电门两图改为**上下**排列；三种机械能实验**隐藏 AI 模拟**按钮；气垫导轨方案三增加表头**滑块质量**录入（默认 160 g、同步表格各次），钩码质量行默认 20→150 g 六档。

## 教学使用建议

- 课前：让学生在网页里跑数据采集，体验数据流；
- 课中：用「实验回顾」对核心公式 / 参数做对照讲解；
- 课后：从习题区按"基础 → 中等 → 挑战"顺序作业；
- 教师：`docs/exercises/` 下的 Markdown 与网页同源，可直接打印。
