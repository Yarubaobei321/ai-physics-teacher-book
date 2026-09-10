import type { Exercise } from './types';

export const curvedRampExercises: Exercise[] = [
  {
    kind: 'single',
    number: 1,
    difficulty: '基础',
    category: '选择题',
    stem: `<p>关于本实验中"为何选用 A、B、C 三个不同高度释放金属圆柱体并多次测量"，<strong>最主要</strong>的目的是（　　）</p>`,
    choices: [
      { id: 'A', label: '让实验耗时更长，看起来更专业' },
      { id: 'B', label: '在不同初始势能下分别验证 ΔE<sub>p</sub> ≈ ΔE<sub>k</sub>，多组数据相互佐证' },
      { id: 'C', label: '为了求得不同位置上的重力加速度' },
      { id: 'D', label: '为了减小双头光电门的间距测量误差' },
    ],
    answer: 'B',
    explanation: `
      <p><strong>答案：B。</strong>多个不同 Δh 各对应一组 ΔE<sub>p</sub> 与 ΔE<sub>k</sub>，可以画 v² − Δh 图，
      从斜率反推 g，也可以逐组比较以减少偶然误差，体现"在不同条件下守恒律都成立"。</p>
    `,
  },
  {
    kind: 'single',
    number: 2,
    difficulty: '中等',
    category: '选择题',
    stem: `<p>本实验中最容易被忽视的误差源是（　　）</p>`,
    choices: [
      { id: 'A', label: '空气阻力' },
      { id: 'B', label: '释放时手指给金属圆柱体了非零初速度' },
      { id: 'C', label: '金属圆柱体在摆线轨道上滚动时的转动动能（部分平动动能转化为转动动能）' },
      { id: 'D', label: '重力加速度本地值与 9.788 m/s² 略有偏差' },
    ],
    answer: 'C',
    explanation: `
      <p><strong>答案：C。</strong>A 在沿曲线运动时速度不大，几乎可忽略；B 通过专业释放装置可控制；
      D 对相对误差影响极小（&lt; 0.1%）。</p>
      <p>滚动状态下动能 = ½ mv² + ½ I ω²，平动动能 ½ mv² 永远比总动能小：
      实心圆柱 ½ I ω² = ½ · ½ mr² · (v/r)² = ¼ mv²，约占总动能的 1/3。
      这是为什么实测 ΔE<sub>k</sub> 偏小的最主要原因。</p>
    `,
  },
  {
    kind: 'multi',
    number: 3,
    difficulty: '中等',
    category: '多选题',
    stem: `<p>关于"Δh 是哪两点的高度差"，下列说法<strong>正确</strong>的是（　　　）</p>`,
    choices: [
      { id: 'A', label: 'Δh 是释放点处金属圆柱体质心到 D 点处金属圆柱体质心的竖直距离' },
      { id: 'B', label: '因为 D 是最低点，可直接读取实验器铭刻的"高度差"——只要装置出厂时已扣除质心修正' },
      { id: 'C', label: '把 Δh 当作"释放点轨道表面到 D 点表面的距离"会引入约 d/2 的系统误差' },
      { id: 'D', label: '不同直径圆柱在同一释放点应当有相同 Δh，因为 Δh 仅由轨道决定' },
    ],
    answer: ['A', 'C', 'D'],
    explanation: `
      <p><strong>答案：A、C、D。</strong></p>
      <ul class="list-disc pl-5 space-y-1">
        <li>A：质心是动能、势能计算的"代表点"，Δh 必须用质心高度差。</li>
        <li>B 错：不能依赖装置铭文是否扣除质心修正，应自行用直径作必要修正。</li>
        <li>C：若忽略 d/2 的系统差，Δh 会偏大约 d/2 = 0.5 cm，对 ΔE<sub>p</sub> 引入约 0.005 / 0.20 = 2.5% 的误差。</li>
        <li>D：Δh 仅由轨道几何决定（释放点与 D 点的轨道表面高度差再加修正），与圆柱本身无关。</li>
      </ul>
    `,
  },
  {
    kind: 'fill',
    number: 4,
    difficulty: '中等',
    category: '填空题',
    stem: `
      <p>金属圆柱体质量 m = 50 g，从 B 点释放，B 点比 D 点高 Δh = 20.0 cm，取 g = 9.80 m/s²。</p>
      <ol class="list-decimal pl-5 space-y-1">
        <li>重力势能减少量 ΔE<sub>p</sub> = {{a}} J。</li>
        <li>若<strong>完全不考虑滚动和摩擦</strong>，到 D 点的理论速度 v<sub>理</sub> = {{b}} m/s（保留 3 位有效数字）。</li>
      </ol>
    `,
    blanks: [
      { id: 'a', answer: '0.0980', alternates: ['0.098', '9.8e-2'] },
      { id: 'b', answer: '1.98', alternates: ['1.980', '1.97', '1.99'] },
    ],
    explanation: `
      <p><strong>(1)</strong> ΔE<sub>p</sub> = m g Δh = 0.050 × 9.80 × 0.20 = <strong>0.0980 J</strong>。</p>
      <p><strong>(2)</strong> v<sub>理</sub> = √(2 g Δh) = √(2 × 9.80 × 0.20) = √3.92 ≈ <strong>1.98 m/s</strong>。</p>
    `,
  },
  {
    kind: 'open',
    number: 5,
    difficulty: '基础',
    category: '计算与数据处理',
    stem: `
      <p>实测一次：m = 0.050 kg，从 B 点静止释放，Δh = 20.0 cm，
      双头光电门测得 v = 1.92 m/s。</p>
      <ol class="list-decimal pl-5 space-y-1">
        <li>计算 ΔE<sub>p</sub> 与 ΔE<sub>k</sub>。</li>
        <li>计算相对误差 δ = |1 − ΔE<sub>p</sub> / ΔE<sub>k</sub>| × 100%。</li>
        <li>与上一题（理论值 v<sub>理</sub>）对比，实测速度比理论值小，差异主要源于哪些因素？</li>
      </ol>
    `,
    explanation: `
      <p><strong>(1)</strong> ΔE<sub>p</sub> = 0.050 × 9.80 × 0.200 = <strong>0.0980 J</strong>；
      ΔE<sub>k</sub> = ½ × 0.050 × 1.92² = 0.025 × 3.6864 ≈ <strong>0.0922 J</strong>。</p>
      <p><strong>(2)</strong> δ = |1 − 0.0980 / 0.0922| × 100% ≈ <strong>6.3%</strong>。</p>
      <p><strong>(3)</strong> 实测 v &lt; v<sub>理</sub> = 1.98 m/s，差异源于：</p>
      <ul class="list-disc pl-5 space-y-1">
        <li>滚动状态下部分平动动能 → 转动动能（最主要）；</li>
        <li>摆线轨道与圆柱接触处的滑动摩擦做负功；</li>
        <li>释放瞬间金属圆柱体摆动 / 滑动，姿态非纯滚动；</li>
        <li>空气阻力（次要）。</li>
      </ul>
    `,
  },
  {
    kind: 'open',
    number: 6,
    difficulty: '中等',
    category: '计算与数据处理',
    stem: `
      <p>同一金属圆柱体，分别从 A、B、C 三点释放（Δh<sub>A</sub> &gt; Δh<sub>B</sub> &gt; Δh<sub>C</sub>），得到下表数据：</p>
      <div class="overflow-x-auto"><table class="min-w-[560px] text-left text-sm">
        <thead><tr class="border-b border-slate-300">
          <th class="px-3 py-2">释放点</th><th class="px-3 py-2">Δh / cm</th><th class="px-3 py-2">v / (m·s⁻¹)</th>
          <th class="px-3 py-2">ΔE<sub>p</sub> / J</th><th class="px-3 py-2">ΔE<sub>k</sub> / J</th><th class="px-3 py-2">相对误差</th>
        </tr></thead>
        <tbody>
          <tr><td class="px-3 py-2">A</td><td class="px-3 py-2">30.0</td><td class="px-3 py-2">2.34</td><td class="px-3 py-2">?</td><td class="px-3 py-2">?</td><td class="px-3 py-2">?</td></tr>
          <tr><td class="px-3 py-2">B</td><td class="px-3 py-2">20.0</td><td class="px-3 py-2">1.92</td><td class="px-3 py-2">?</td><td class="px-3 py-2">?</td><td class="px-3 py-2">?</td></tr>
          <tr><td class="px-3 py-2">C</td><td class="px-3 py-2">10.0</td><td class="px-3 py-2">1.36</td><td class="px-3 py-2">?</td><td class="px-3 py-2">?</td><td class="px-3 py-2">?</td></tr>
        </tbody>
      </table></div>
      <p>取 m = 0.050 kg，g = 9.8 m/s²。</p>
      <ol class="list-decimal pl-5 space-y-1">
        <li>补全表格。</li>
        <li>比较三次实验的相对误差，是否随 Δh 增大而单调变化？分析其物理原因（提示：滚动动能与摩擦做功对总能量的相对占比）。</li>
        <li>若以 v² 为纵坐标、Δh 为横坐标作图，理论上斜率应为 2g ≈ 19.6，实验所得斜率约为多少？这对实验目的（验证机械能守恒）意味着什么？</li>
      </ol>
    `,
    explanation: `
      <p><strong>(1) 计算结果（取 m = 0.050 kg，g = 9.8 m/s²）：</strong></p>
      <div class="overflow-x-auto"><table class="min-w-[560px] text-left text-sm">
        <thead><tr class="border-b border-slate-300">
          <th class="px-3 py-2">释放点</th><th class="px-3 py-2">Δh / cm</th><th class="px-3 py-2">v / (m·s⁻¹)</th>
          <th class="px-3 py-2">ΔE<sub>p</sub> / J</th><th class="px-3 py-2">ΔE<sub>k</sub> / J</th><th class="px-3 py-2">相对误差</th>
        </tr></thead>
        <tbody>
          <tr><td class="px-3 py-2">A</td><td class="px-3 py-2">30.0</td><td class="px-3 py-2">2.34</td><td class="px-3 py-2">0.1470</td><td class="px-3 py-2">0.1369</td><td class="px-3 py-2">7.4%</td></tr>
          <tr><td class="px-3 py-2">B</td><td class="px-3 py-2">20.0</td><td class="px-3 py-2">1.92</td><td class="px-3 py-2">0.0980</td><td class="px-3 py-2">0.0922</td><td class="px-3 py-2">6.3%</td></tr>
          <tr><td class="px-3 py-2">C</td><td class="px-3 py-2">10.0</td><td class="px-3 py-2">1.36</td><td class="px-3 py-2">0.0490</td><td class="px-3 py-2">0.0462</td><td class="px-3 py-2">6.1%</td></tr>
        </tbody>
      </table></div>
      <p><strong>(2)</strong> 相对误差随 Δh 增大略微增大。原因：</p>
      <ul class="list-disc pl-5 space-y-1">
        <li>滚动动能始终占总动能 ~1/3，与 Δh 关系不大，是恒定相对值；</li>
        <li>摩擦阻力做负功与路径长度成正比，A 点路径最长，摩擦消耗能量绝对量更多；</li>
        <li>但 A 点 ΔE<sub>p</sub> 也最大，相对值仍主要由"滚动动能占比"决定，所以差距不大。</li>
      </ul>
      <p><strong>(3)</strong> v² − Δh 数据点：(0.10, 1.85)、(0.20, 3.69)、(0.30, 5.48)，
      斜率 k ≈ (5.48 − 1.85) / 0.20 ≈ <strong>18.2</strong>。</p>
      <p>理论 2g = 19.6，差 ≈ 7.1%；这一<strong>斜率亏损</strong>正是滚动动能与摩擦带走能量的体现：
      v² = 2g' Δh，其中 g' = k / 2 ≈ 9.1 m/s²。</p>
    `,
  },
  {
    kind: 'open',
    number: 7,
    difficulty: '中等',
    category: '误差分析与改进',
    stem: `
      <p>列出本实验<strong>特有</strong>的误差来源（至少 4 条），并按是否会引起 ΔE<sub>p</sub> &gt; ΔE<sub>k</sub> 的<strong>系统性偏差</strong>分类。</p>
    `,
    explanation: `
      <div class="overflow-x-auto"><table class="min-w-[640px] text-left text-sm">
        <thead><tr class="border-b border-slate-300">
          <th class="px-3 py-2">系统性偏差源（使 ΔE<sub>p</sub> &gt; ΔE<sub>k</sub>）</th>
          <th class="px-3 py-2">双向 / 随机误差源</th>
        </tr></thead>
        <tbody>
          <tr><td class="px-3 py-2">滚动动能占总动能 ~30%，被 ½ mv² 公式忽略</td><td class="px-3 py-2">双头光电门 Δt 测量抖动</td></tr>
          <tr><td class="px-3 py-2">摆线轨道与圆柱间滑动摩擦做负功</td><td class="px-3 py-2">释放瞬间手部初速度</td></tr>
          <tr><td class="px-3 py-2">空气阻力做负功</td><td class="px-3 py-2">圆柱在轨道上摆动姿态不正</td></tr>
          <tr><td class="px-3 py-2">Δh 没有用<strong>质心</strong>修正，按表面读数会偏大</td><td class="px-3 py-2">多次实验时 L 标定偶然变化</td></tr>
        </tbody>
      </table></div>
    `,
  },
  {
    kind: 'open',
    number: 8,
    difficulty: '中等',
    category: '误差分析与改进',
    stem: `
      <p>下列改进措施，哪些可以<strong>降低</strong>实验相对误差？请逐条判断并说明物理原因。</p>
      <ol class="list-[upper-alpha] pl-6 space-y-1">
        <li>把金属圆柱体表面打磨光滑、轨道擦干净，减小摩擦</li>
        <li>把金属圆柱体换成"小滑块"（不是圆柱，无法滚动）</li>
        <li>把双头光电门间距 L 由 1 cm 增大到 2 cm</li>
        <li>增大金属圆柱体质量</li>
        <li>在 D 点上方再加一个光电门，独立测一次速度做交叉验证</li>
      </ol>
    `,
    explanation: `
      <ul class="list-disc pl-5 space-y-1">
        <li><strong>A 可</strong>：直接减小摩擦，效果最明显；</li>
        <li><strong>B 不一定</strong>：滑块虽无转动动能，但与轨道间摩擦更大、姿态更不稳，实测往往误差更大；</li>
        <li><strong>C 可（双刃剑）</strong>：L 增大让 Δt 增大、相对读数误差减小；但此时 D 点附近的速度不再是"瞬时速度"而是 L 段平均速度。需在 1 ～ 2 cm 之间取折中；</li>
        <li><strong>D 基本无效</strong>：ΔE<sub>p</sub> 与 ΔE<sub>k</sub> 都正比 m，相对误差与质量无关；不过较重圆柱对空气阻力更不敏感，在大 Δh 时有微小好处；</li>
        <li><strong>E 可</strong>：双独立速度比较可发现单点测量异常，但需要硬件支持。</li>
      </ul>
    `,
  },
];
