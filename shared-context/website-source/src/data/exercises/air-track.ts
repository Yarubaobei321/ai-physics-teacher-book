import type { Exercise } from './types';

export const airTrackExercises: Exercise[] = [
  {
    kind: 'single',
    number: 1,
    difficulty: '基础',
    category: '选择题',
    stem: `<p>本实验中<strong>必须</strong>调节气垫导轨水平的最主要原因是（　　）</p>`,
    choices: [
      { id: 'A', label: '让滑块在气垫上稳定漂浮，避免滑块磕碰导轨' },
      { id: 'B', label: '避免滑块所受重力沿导轨方向的分量做功，使能量分析能够只考虑重锤重力做功' },
      { id: 'C', label: '美观，便于观察现象' },
      { id: 'D', label: '让滑轮位于重锤正上方，避免绳与导轨之间产生摩擦' },
    ],
    answer: 'B',
    explanation: `
      <p><strong>答案：B。</strong>不水平时滑块所受重力沿导轨方向的分量也做功，能量方程多出一项 M g sinθ · s，
      若忽略不计就会引入与"机械能不守恒"等价的系统误差。</p>
      <p>A 描述的是气垫的作用而非"调水平"；C 不构成科学依据；D 是滑轮安装而非导轨水平问题。</p>
    `,
  },
  {
    kind: 'multi',
    number: 2,
    difficulty: '基础',
    category: '多选题',
    stem: `<p>关于"为什么动能要写成 ½(M+m)(v<sub>2</sub>² − v<sub>1</sub>²)"，下列说法<strong>正确</strong>的是（　　　）</p>`,
    choices: [
      { id: 'A', label: '滑块和重锤必须一起算，因为绳子不可伸长，二者瞬时速率相同' },
      { id: 'B', label: '重锤做的是自由落体，不应放进系统动能' },
      { id: 'C', label: '之所以是 v₂² − v₁²，是因为本实验取"滑块通过前光电门到通过后光电门"这一过程，前光电门处系统已经有初速度 v₁' },
      { id: 'D', label: '绳上张力做了正功，必须显式加进能量方程才能守恒' },
    ],
    answer: ['A', 'C'],
    explanation: `
      <p><strong>答案：A、C。</strong></p>
      <ul class="list-disc pl-5 space-y-1">
        <li>A：绳不可伸长 → 重锤下落速度等于滑块水平速度，所以系统动能项里它们用同一个 v。</li>
        <li>C：双光电门测两次速度，描述的是"滑块从前门到后门"的能量变化过程，所以应当用 v₂² − v₁²。</li>
        <li>B 错：重锤也是系统的一部分，必须计入动能。</li>
        <li>D 错：取系统为研究对象，绳张力是内力，对滑块做正功、对重锤做负功，<strong>总和为 0</strong>，不能再额外加进能量方程。</li>
      </ul>
    `,
  },
  {
    kind: 'single',
    number: 3,
    difficulty: '中等',
    category: '选择题',
    stem: `<p>关于"如何判断气垫导轨已经水平"，下列方法中<strong>最可靠</strong>的是（　　）</p>`,
    choices: [
      { id: 'A', label: '把水平仪放在导轨上观察气泡居中' },
      { id: 'B', label: '关闭气源后，把滑块放在导轨中央，看滑块是否静止' },
      { id: 'C', label: '打开气源，将滑块放在不同位置释放，看在两个相反方向上漂移加速度是否对称（即从两端释放都能基本静止或漂移很慢）' },
      { id: 'D', label: '看导轨与桌面之间是否水平' },
    ],
    answer: 'C',
    explanation: `
      <p><strong>答案：C。</strong>气垫导轨调平的本质判据是"气垫开启后无重力分量加速度"。</p>
      <ul class="list-disc pl-5 space-y-1">
        <li>A 仅是粗调；</li>
        <li>B 关闭气源后导轨与滑块间的摩擦反而会让"看似静止"误判；</li>
        <li>C 是规范操作：观察从两端反方向释放后是否漂移近似对称（或都极慢漂移）；</li>
        <li>D 不能等同于导轨水平。</li>
      </ul>
    `,
  },
  {
    kind: 'multi',
    number: 4,
    difficulty: '中等',
    category: '多选题',
    stem: `<p>在该实验中，下列因素<strong>会</strong>导致系统能量损失的有（　　　）</p>`,
    choices: [
      { id: 'A', label: '气垫导轨的滑动摩擦' },
      { id: 'B', label: '重锤与绳之间的摩擦' },
      { id: 'C', label: '绳与定滑轮之间的摩擦' },
      { id: 'D', label: '滑轮转动的转动动能（滑轮有质量）' },
      { id: 'E', label: '空气对滑块、重锤的阻力' },
      { id: 'F', label: '遮光条做穿过光电门的"切割"动作' },
    ],
    answer: ['A', 'B', 'C', 'D', 'E'],
    explanation: `
      <p><strong>答案：A、B、C、D、E。</strong></p>
      <ul class="list-disc pl-5 space-y-1">
        <li>A：气垫显著减小但<strong>不能完全消除</strong>底部摩擦，残余仍有；</li>
        <li>B / C：绳与滑轮间相对运动，绳-滑轮、轴承摩擦不可避免；</li>
        <li>D：滑轮自身有转动惯量 I，绳张力会使 I·dω/dt 占用一部分能量，使下方重锤加速度小于自由落体；</li>
        <li>E：空气阻力虽小，但对低速重锤 + 高速滑块仍有微弱影响；</li>
        <li>F 不是误差源：遮光条切割光电门是测量手段，不直接消耗系统机械能。</li>
      </ul>
    `,
  },
  {
    kind: 'fill',
    number: 5,
    difficulty: '基础',
    category: '填空题',
    stem: `
      <p>已知滑块质量 M = 200 g，重锤质量 m = 50 g，重锤下落高度 h = 50 cm，取 g = 9.8 m/s²。</p>
      <ol class="list-decimal pl-5 space-y-1">
        <li>重力势能减少量 ΔE<sub>p</sub> = {{a}} J（保留 3 位有效数字）。</li>
        <li>若假设无任何能量损失，从静止开始到重锤刚要落地时滑块速度 v 的理论值为 {{b}} m/s。</li>
      </ol>
    `,
    blanks: [
      { id: 'a', answer: '0.245', alternates: ['0.245J', '0.245 J'] },
      { id: 'b', answer: '1.40', alternates: ['1.4', '1.400'] },
    ],
    explanation: `
      <p><strong>(1)</strong> ΔE<sub>p</sub> = m g h = 0.050 × 9.8 × 0.50 = <strong>0.245 J</strong>。</p>
      <p><strong>(2)</strong> ΔE<sub>p</sub> = ½(M+m) v²，所以
      v = √(2 m g h / (M + m)) = √(2 × 0.050 × 9.8 × 0.50 / 0.250) = √1.96 = <strong>1.40 m/s</strong>。</p>
    `,
  },
  {
    kind: 'open',
    number: 6,
    difficulty: '基础',
    category: '计算与数据处理',
    stem: `
      <p>某次实验数据如下（取 g = 9.8 m/s²）：</p>
      <div class="overflow-x-auto"><table class="min-w-[640px] text-left text-sm">
        <thead><tr class="border-b border-slate-300">
          <th class="px-3 py-2">序号</th><th class="px-3 py-2">m / g</th><th class="px-3 py-2">M / g</th>
          <th class="px-3 py-2">h / cm</th><th class="px-3 py-2">v<sub>1</sub> / (m·s⁻¹)</th><th class="px-3 py-2">v<sub>2</sub> / (m·s⁻¹)</th>
        </tr></thead>
        <tbody>
          <tr><td class="px-3 py-2">1</td><td class="px-3 py-2">50</td><td class="px-3 py-2">200</td>
          <td class="px-3 py-2">50.0</td><td class="px-3 py-2">0.20</td><td class="px-3 py-2">1.38</td></tr>
        </tbody>
      </table></div>
      <ol class="list-decimal pl-5 space-y-1">
        <li>计算重力势能减少量 ΔE<sub>p</sub>。</li>
        <li>计算系统动能增加量 ΔE<sub>k</sub> = ½(M+m)(v<sub>2</sub>² − v<sub>1</sub>²)。</li>
        <li>计算相对误差 δ = |1 − ΔE<sub>p</sub> / ΔE<sub>k</sub>| × 100%，并判断该误差是否在合理范围（一般 ≤5% 视为良好验证）。</li>
      </ol>
    `,
    explanation: `
      <p><strong>(1)</strong> ΔE<sub>p</sub> = m g h = 0.050 × 9.8 × 0.500 = <strong>0.245 J</strong>。</p>
      <p><strong>(2)</strong> ΔE<sub>k</sub> = ½ × (0.200 + 0.050) × (1.38² − 0.20²)
      = 0.5 × 0.250 × (1.9044 − 0.0400) = 0.125 × 1.8644 ≈ <strong>0.233 J</strong>。</p>
      <p><strong>(3)</strong> δ = |1 − 0.245 / 0.233| × 100% ≈ <strong>5.2%</strong>。</p>
      <p>约 5%，<strong>在教学验收的合理范围内</strong>（≤5%），说明气垫导轨方案能较好验证机械能守恒定律。</p>
    `,
  },
  {
    kind: 'open',
    number: 7,
    difficulty: '中等',
    category: '操作分析',
    stem: `
      <p>请说明：</p>
      <ul class="list-disc pl-5 space-y-1">
        <li>为什么 v<sub>1</sub> 不是 0，而是 0.20 m/s？</li>
        <li>如果整个实验从滑块<strong>静止释放</strong>开始，是否就可以让 v<sub>1</sub> = 0，把动能项简化为 ½(M+m)v<sub>2</sub>²？</li>
        <li>若只在末端测一次速度，并把释放点速度近似取 0，与本网页"前、后光电门分别测 v<sub>1</sub>、v<sub>2</sub>"的处理相比，各自适合什么场景？</li>
      </ul>
    `,
    explanation: `
      <ul class="list-disc pl-5 space-y-1">
        <li><strong>v<sub>1</sub> ≠ 0：</strong>前光电门并不一定放在滑块的释放位置，通常在释放点下游 5～10 cm 处。
        这样才能避开"释放时手抖"等扰动，同时方便读取一对完整的 v<sub>1</sub>、v<sub>2</sub>。</li>
        <li><strong>关于简化：</strong>若严格从静止释放并把光电门放在起点，v<sub>1</sub> = 0 时确实可以简化为
        ΔE<sub>k</sub> = ½(M+m) v<sub>2</sub>²。但起点附近滑块加速度大、姿态不稳，遮光条切割时刻可能不对应"真正起点"，反而引入更大误差。</li>
      </ul>
      <div class="overflow-x-auto"><table class="min-w-[600px] text-left text-sm">
        <thead><tr class="border-b border-slate-300">
          <th class="px-3 py-2">方案</th><th class="px-3 py-2">优点</th><th class="px-3 py-2">缺点</th>
        </tr></thead>
        <tbody>
          <tr><td class="px-3 py-2">末端单测点，释放点速度近似为 0</td><td class="px-3 py-2">公式简单、所需仪器少，适合入门演示</td><td class="px-3 py-2">起点速度难以真正为 0；释放扰动会直接进入结果；只能比较一段总变化</td></tr>
          <tr><td class="px-3 py-2">前、后光电门分别测 v<sub>1</sub>、v<sub>2</sub></td><td class="px-3 py-2">避开起点扰动；前后两次速度独立测量；可分析"导轨段"内能量变化</td><td class="px-3 py-2">需要两套光电门和数据采集；需保证两只光电门测速口径一致</td></tr>
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
      <p>实验中通常发现 ΔE<sub>p</sub> &gt; ΔE<sub>k</sub>，且偏差约 3 ～ 8%。
      请逐项判断下列误差源对该偏差的贡献是<strong>正向</strong>（使 ΔE<sub>p</sub> &gt; ΔE<sub>k</sub> 加剧）、
      <strong>负向</strong>（缓解）还是<strong>双向</strong>（随机）。</p>
      <ol class="list-[upper-alpha] pl-6 space-y-1">
        <li>滑轮转动惯量带走部分动能</li>
        <li>绳子有质量</li>
        <li>气垫导轨没有完全调水平，且倾向"重锤端低"</li>
        <li>空气阻力</li>
        <li>双光电门间距 L 测量偏大</li>
        <li>遮光条切割时滑块姿态轻微偏摆</li>
      </ol>
    `,
    explanation: `
      <div class="overflow-x-auto"><table class="min-w-[640px] text-left text-sm">
        <thead><tr class="border-b border-slate-300">
          <th class="px-3 py-2">选项</th><th class="px-3 py-2">偏向</th><th class="px-3 py-2">解释</th>
        </tr></thead>
        <tbody>
          <tr><td class="px-3 py-2">A</td><td class="px-3 py-2">正向</td><td class="px-3 py-2">滑轮转动需要能量 ½ I ω²，从系统平动动能中"扣除"</td></tr>
          <tr><td class="px-3 py-2">B</td><td class="px-3 py-2">正向</td><td class="px-3 py-2">绳子动能也消耗能量；若绳质量小可忽略</td></tr>
          <tr><td class="px-3 py-2">C</td><td class="px-3 py-2">负向</td><td class="px-3 py-2">重锤端低 → 滑块沿轨道方向上重力分量做正功，让 ΔE<sub>k</sub> 偏大、误差减小，但掩盖了真实能量损失</td></tr>
          <tr><td class="px-3 py-2">D</td><td class="px-3 py-2">正向</td><td class="px-3 py-2">阻力做负功</td></tr>
          <tr><td class="px-3 py-2">E</td><td class="px-3 py-2">双向</td><td class="px-3 py-2">L 偏大 → 测得 v 偏大 → 动能偏大 → 误差减小（但是错的"减小"）；偏小则反向</td></tr>
          <tr><td class="px-3 py-2">F</td><td class="px-3 py-2">双向（随机）</td><td class="px-3 py-2">切割不规则使 Δt 抖动，可正可负</td></tr>
        </tbody>
      </table></div>
    `,
  },
  {
    kind: 'open',
    number: 9,
    difficulty: '拓展',
    category: '数字化测量',
    stem: `
      <p>本实验需要 ESP32 双光电门通过蓝牙将测量数据传给网页（页面上的"蓝牙输入"）。</p>
      <ol class="list-decimal pl-5 space-y-1">
        <li>这种"实时上传 + 网页表格"的方式相比传统人工读数有什么误差控制上的优势？</li>
        <li>若蓝牙数据偶尔丢包导致某次实验只收到了 v<sub>2</sub> 没收到 v<sub>1</sub>，应当如何处理？是否可以用"上一次实验的 v<sub>1</sub>"代替？为什么？</li>
      </ol>
    `,
    explanation: `
      <p><strong>(1)</strong> ESP32 + 蓝牙的优势：</p>
      <ul class="list-disc pl-5 space-y-1">
        <li>时间戳由 MCU 给出，分辨率 µs 级，<strong>远高于人眼读秒表</strong>；</li>
        <li>数据自动入表，避免抄表错位；</li>
        <li>可累积多次实验数据，做统计分析；</li>
        <li>网页可即时绘图反馈，便于发现明显错点立即重做。</li>
      </ul>
      <p><strong>(2)</strong> <strong>不能</strong>用上次实验的 v<sub>1</sub> 代替。
      因为 v<sub>1</sub> 与每次释放的具体位置、扰动有关，每次值都不同；用旧值会引入不可控的系统误差。
      正确处理：<strong>重做这一次实验</strong>，或在网页"导出 CSV"前过滤掉数据不完整的行。</p>
    `,
  },
];
