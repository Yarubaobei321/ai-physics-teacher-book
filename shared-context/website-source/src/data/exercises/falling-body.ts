import type { Exercise } from './types';

export const fallingBodyExercises: Exercise[] = [
  {
    kind: 'single',
    number: 1,
    difficulty: '基础',
    category: '选择题',
    stem: `<p>关于本实验中"<strong>先接通电源后释放纸带</strong>"这一操作，下列说法<strong>正确</strong>的是（　　）</p>`,
    choices: [
      { id: 'A', label: '这只是习惯做法，先释放纸带再通电也能得到正确数据' },
      { id: 'B', label: '先释放纸带再通电，会使纸带前段缺少打点甚至漏掉 0、1 号点附近数据，导致起始位置和初速度不可靠' },
      { id: 'C', label: '先通电是为了让线圈充磁，与打点节奏无关' },
      { id: 'D', label: '顺序由电源类型决定，电火花计时器无所谓' },
    ],
    answer: 'B',
    explanation: `
      <p><strong>答案：B。</strong>先释放再通电，纸带最开始几格内可能无打点或打点不清晰，导致 0、1 号点附近数据丢失或不准。</p>
      <ul class="list-disc pl-5 space-y-1">
        <li>A 错：顺序直接关系到数据可靠性；</li>
        <li>C 错：先通电主要是为了让计时器进入稳定打点状态；</li>
        <li>D 错：电磁、电火花计时器都应遵循"先通电再释放"。</li>
      </ul>
    `,
  },
  {
    kind: 'single',
    number: 2,
    difficulty: '基础',
    category: '选择题',
    stem: `<p>选取纸带上用于能量分析的 1 号计数点时，下列做法<strong>最合适</strong>的是（　　）</p>`,
    choices: [
      { id: 'A', label: '取纸带最开始那一点' },
      { id: 'B', label: '取打点最密集的那一点' },
      { id: 'C', label: '取一个清晰、便于测量、且前后相邻点都清楚的位置' },
      { id: 'D', label: '取一个相邻间距最小的点，这样误差最小' },
    ],
    answer: 'C',
    explanation: `
      <p><strong>答案：C。</strong>1 号点作为能量分析起点，不必是纸带最开始那一点，关键是清晰、间距适当、且前后相邻点都可读
      ——这样才能用中间点公式 v<sub>n</sub> = (x<sub>n+1</sub> − x<sub>n−1</sub>) / (2T) 算出 1 号点的初速度。</p>
      <ul class="list-disc pl-5 space-y-1">
        <li>A 错：开始点常常打点重叠；</li>
        <li>B 错：最密的点意味着速度最小、间距分辨率不足；</li>
        <li>D 错：间距越小相对读数误差越大。</li>
      </ul>
    `,
  },
  {
    kind: 'multi',
    number: 3,
    difficulty: '中等',
    category: '多选题',
    stem: `<p>关于公式 v<sub>n</sub> = (x<sub>n+1</sub> − x<sub>n−1</sub>) / (2T)，下列分析<strong>正确</strong>的是（　　　）</p>`,
    choices: [
      { id: 'A', label: '它依据的是匀变速直线运动中"中间时刻的瞬时速度等于这段时间的平均速度"' },
      { id: 'B', label: '它仅适用于打点计时器实验，不适用于光电门' },
      { id: 'C', label: '它能减小因单点测量带来的偶然误差' },
      { id: 'D', label: '即使物体不做匀变速运动，该公式仍然给出 n 号点的瞬时速度' },
    ],
    answer: ['A', 'C'],
    explanation: `
      <p><strong>答案：A、C。</strong></p>
      <ul class="list-disc pl-5 space-y-1">
        <li>A：这是匀变速直线运动的"中间时刻定理"。</li>
        <li>B 错：双头光电门也使用"距离 / 时间差"的等价思想，本质是平均速度近似瞬时速度。</li>
        <li>C：用 n−1 与 n+1 两点参与计算可减小单点位置误差的影响。</li>
        <li>D 错：该公式仅在匀变速运动下才精确成立；非匀变速时只是近似的"中间时刻平均速度"。</li>
      </ul>
    `,
  },
  {
    kind: 'single',
    number: 4,
    difficulty: '中等',
    category: '选择题',
    stem: `<p>在该实验中，多次测量结果总是 mgh &gt; ½ mv² 而很少出现相反情况，<strong>最主要</strong>的原因是（　　）</p>`,
    choices: [
      { id: 'A', label: '重力加速度 g 的取值偏大' },
      { id: 'B', label: '重锤未做自由落体运动，存在阻力做负功（空气阻力、纸带与限位孔摩擦、电磁阻尼）' },
      { id: 'C', label: '计时器打点频率不稳定' },
      { id: 'D', label: '学生测量距离时偏小' },
    ],
    answer: 'B',
    explanation: `
      <p><strong>答案：B。</strong>自由落体模型忽略阻力，但实验中纸带与限位孔的摩擦、空气阻力、电磁阻尼都做负功，
      使重锤实际加速度 a &lt; g，因此实测 ½ mv² &lt; mgh 是<strong>系统性</strong>偏差。</p>
      <p>A、D 是数值偏差（且 g 是固定查表值，并非偏大）；C 实际上 50 Hz 频率非常稳定。</p>
    `,
  },
  {
    kind: 'fill',
    number: 5,
    difficulty: '基础',
    category: '填空题',
    stem: `
      <p>我国市电频率为 50 Hz，因此电磁打点计时器每 0.02 s 打一个点。
      若某同学在纸带上每隔 4 个打点取 1 个计数点（即两个相邻计数点之间共有 5 个间隔），
      则相邻计数点时间间隔 <strong>T =</strong> {{a}} s。
      在网页"在线实验室"工具中，应当把"相邻计数点时间 T"输入框改为 {{b}} s。</p>
    `,
    blanks: [
      { id: 'a', answer: '0.10', alternates: ['0.1', '0.100', '0.1000', '1/10'] },
      { id: 'b', answer: '0.1000', alternates: ['0.1', '0.10', '0.100'] },
    ],
    explanation: `
      <p><strong>答案：T = 0.10 s；网页输入 0.1000。</strong></p>
      <p>相邻两计数点中间夹了 5 个间隔（4 个打点 + 1 个计数点连接），所以
      T = 5 × 0.02 s = 0.10 s。网页中保留 4 位小数填 0.1000 即可。</p>
    `,
  },
  {
    kind: 'open',
    number: 6,
    difficulty: '基础',
    category: '计算与数据处理',
    stem: `
      <p>某小组得到一条纸带，每隔 1 个打点取 1 个计数点（即 T = 0.04 s）。
      依次测量 0 ～ 6 号计数点到 0 号点的距离如下，其中能量分析以 1 号点为起点：</p>
      <div class="overflow-x-auto"><table class="min-w-[460px] text-left text-sm">
        <thead><tr class="border-b border-slate-300">
          <th class="px-3 py-2">n</th>
          <th class="px-3 py-2">0</th><th class="px-3 py-2">1</th><th class="px-3 py-2">2</th>
          <th class="px-3 py-2">3</th><th class="px-3 py-2">4</th><th class="px-3 py-2">5</th><th class="px-3 py-2">6</th>
        </tr></thead>
        <tbody><tr>
          <td class="px-3 py-2 font-bold">x<sub>n</sub> / cm</td>
          <td class="px-3 py-2">0.00</td><td class="px-3 py-2">0.76</td><td class="px-3 py-2">3.04</td>
          <td class="px-3 py-2">6.84</td><td class="px-3 py-2">12.16</td><td class="px-3 py-2">19.00</td><td class="px-3 py-2">27.36</td>
        </tr></tbody>
      </table></div>
      <p>取 m = 0.100 kg，g = 9.788 m/s²。</p>
      <ol class="list-decimal pl-5 space-y-1">
        <li>计算 3 号计数点的瞬时速度 v<sub>3</sub>（保留 3 位有效数字）。</li>
        <li>计算从 1 号点到 3 号点过程中：① 重力势能减少量 ΔE<sub>p</sub>；② 动能增加量 ΔE<sub>k</sub>。</li>
        <li>计算相对误差 δ = |1 − ΔE<sub>p</sub> / ΔE<sub>k</sub>| × 100%。</li>
        <li>用相同方法分别求 v<sub>1</sub> ～ v<sub>5</sub>，并讨论相对误差随 n 增大的变化趋势及原因。</li>
      </ol>
    `,
    explanation: `
      <p>数据先化为 m：x<sub>2</sub> = 0.0304 m，x<sub>3</sub> = 0.0684 m，x<sub>4</sub> = 0.1216 m。</p>
      <p><strong>(1) 中间点定理：</strong><br>
        v<sub>3</sub> = (x<sub>4</sub> − x<sub>2</sub>) / (2T) = (0.1216 − 0.0304) / 0.08 ≈ <strong>1.14 m/s</strong></p>
      <p><strong>(2)</strong> 从 1 号点到 3 号点的下落距离 h<sub>3</sub> = x<sub>3</sub> − x<sub>1</sub> = 0.0608 m。<br>
        势能减少 ΔE<sub>p</sub> = mgh<sub>3</sub> = 0.100 × 9.788 × 0.0608 ≈ <strong>0.0595 J</strong>。<br>
        1 号点初速度 v<sub>1</sub> = 0.380 m/s，动能增加 ΔE<sub>k</sub> = ½ × 0.100 × (1.14² − 0.380²) ≈ <strong>0.0578 J</strong>。</p>
      <p><strong>(3)</strong> δ = |1 − 0.0595 / 0.0578| × 100% ≈ <strong>2.9%</strong>。</p>
      <p><strong>(4)</strong> 同理算各点（保留 3 位）：</p>
      <div class="overflow-x-auto"><table class="min-w-[520px] text-left text-sm">
        <thead><tr class="border-b border-slate-300">
          <th class="px-3 py-2">n</th><th class="px-3 py-2">v<sub>n</sub> / (m·s⁻¹)</th>
          <th class="px-3 py-2">ΔE<sub>p</sub> / J</th><th class="px-3 py-2">ΔE<sub>k</sub> / J</th>
          <th class="px-3 py-2">相对误差</th>
        </tr></thead>
        <tbody>
          <tr><td class="px-3 py-2">1</td><td class="px-3 py-2">0.380</td><td class="px-3 py-2">0</td><td class="px-3 py-2">0</td><td class="px-3 py-2">--</td></tr>
          <tr><td class="px-3 py-2">2</td><td class="px-3 py-2">0.760</td><td class="px-3 py-2">0.0223</td><td class="px-3 py-2">0.0217</td><td class="px-3 py-2">≈2.9%</td></tr>
          <tr><td class="px-3 py-2">3</td><td class="px-3 py-2">1.140</td><td class="px-3 py-2">0.0595</td><td class="px-3 py-2">0.0578</td><td class="px-3 py-2">≈2.9%</td></tr>
          <tr><td class="px-3 py-2">4</td><td class="px-3 py-2">1.520</td><td class="px-3 py-2">0.112</td><td class="px-3 py-2">0.108</td><td class="px-3 py-2">≈2.9%</td></tr>
          <tr><td class="px-3 py-2">5</td><td class="px-3 py-2">1.900</td><td class="px-3 py-2">0.179</td><td class="px-3 py-2">0.173</td><td class="px-3 py-2">≈2.9%</td></tr>
        </tbody>
      </table></div>
      <p>各点相对误差大致稳定，说明系统性能量损失（阻力做负功）的比例近似恒定，
      也佐证"自由落体加速度被打折扣"的图像（实测 a ≈ 9.5 m/s² 而非 9.788 m/s²）。</p>
    `,
  },
  {
    kind: 'open',
    number: 7,
    difficulty: '中等',
    category: '计算与数据处理',
    stem: `
      <p>同一根纸带，把 v<sub>n</sub>² − v<sub>1</sub>² 作为纵坐标、h<sub>n</sub> 作为横坐标作图，
      理论上应得到一条过原点的直线。</p>
      <ol class="list-decimal pl-5 space-y-1">
        <li>写出直线方程，并指出斜率的物理意义。</li>
        <li>实验中实际测得直线斜率约为 19.2 m/s² 而不是 2g ≈ 19.6 m/s²，主要原因是什么？</li>
        <li>这种作图法相比逐点比较 mgh 与 ½ mv² 的方法，有什么优点？</li>
      </ol>
    `,
    explanation: `
      <p><strong>(1)</strong> 由 v<sub>n</sub>² − v<sub>1</sub>² = 2ah，理想下 a = g，故 (v<sub>n</sub>² − v<sub>1</sub>²) − h<sub>n</sub> 图为过原点直线，
      <strong>方程 v<sub>n</sub>² − v<sub>1</sub>² = 2g h，斜率 k = 2g</strong>。</p>
      <p><strong>(2)</strong> 实测斜率 19.2 &lt; 2g = 19.6，因为存在阻力使<strong>有效加速度</strong> a 略小于 g，
      该有效加速度 a = k / 2 ≈ 9.6 m/s²。</p>
      <p><strong>(3)</strong> 优点：</p>
      <ul class="list-disc pl-5 space-y-1">
        <li>用所有数据点共同确定斜率，受偶然误差影响小；</li>
        <li>直接给出"实际重力加速度修正值" a，可以量化阻力的影响；</li>
        <li>直线是否过原点也是数据可靠性的检验判据。</li>
      </ul>
    `,
  },
  {
    kind: 'open',
    number: 8,
    difficulty: '中等',
    category: '误差分析与改进',
    stem: `
      <p>列出本实验<strong>特有</strong>的误差来源（至少 3 条），并简要说明哪种误差对动能与势能比较的影响是
      <strong>系统性偏向 mgh &gt; ½ mv²</strong>，哪种是随机性的。</p>
    `,
    explanation: `
      <div class="overflow-x-auto"><table class="min-w-[520px] text-left text-sm">
        <thead><tr class="border-b border-slate-300">
          <th class="px-3 py-2">类型</th>
          <th class="px-3 py-2">误差来源</th>
          <th class="px-3 py-2">偏向</th>
        </tr></thead>
        <tbody>
          <tr><td class="px-3 py-2">系统性</td><td class="px-3 py-2">空气阻力、纸带与限位孔摩擦、电磁阻尼，使有效 a &lt; g</td><td class="px-3 py-2">始终 mgh &gt; ½ mv²</td></tr>
          <tr><td class="px-3 py-2">系统性</td><td class="px-3 py-2">用 g = 9.788 默认值，但本地实际 g 可能偏大或偏小</td><td class="px-3 py-2">单向偏移</td></tr>
          <tr><td class="px-3 py-2">随机性</td><td class="px-3 py-2">纸带读数误差（毫米尺最小分度 1 mm，估读 ±0.5 mm）</td><td class="px-3 py-2">双向</td></tr>
          <tr><td class="px-3 py-2">随机性</td><td class="px-3 py-2">打点本身略有抖动</td><td class="px-3 py-2">双向</td></tr>
          <tr><td class="px-3 py-2">随机性</td><td class="px-3 py-2">选取 1 号点或读取 x<sub>1</sub> 不一致</td><td class="px-3 py-2">双向</td></tr>
        </tbody>
      </table></div>
      <p><strong>要点：</strong>"mgh &gt; ½ mv² 几乎是必然的"——这反映了系统性误差，
      是机械能"略微不守恒"的能量去向问题，而不是定律本身有误。</p>
    `,
  },
  {
    kind: 'open',
    number: 9,
    difficulty: '中等',
    category: '误差分析与改进',
    stem: `
      <p>下列哪些做法可以<strong>减小</strong>实验误差？请逐条判断并说明物理原因。</p>
      <ol class="list-[upper-alpha] pl-6 space-y-1">
        <li>选用更重的重锤</li>
        <li>在重锤前端加锥形头以减小空气阻力</li>
        <li>让纸带尽量竖直、限位孔与纸带不要刮擦</li>
        <li>把打点计时器改为电火花计时器</li>
        <li>把"相邻计数点时间 T"由 0.02 s 改为 0.10 s</li>
      </ol>
    `,
    explanation: `
      <ul class="list-disc pl-5 space-y-1">
        <li><strong>A 可减小：</strong>重锤越重，重力相对阻力的占比越大，有效加速度更接近 g。</li>
        <li><strong>B 可减小：</strong>锥形头降低空气阻力。</li>
        <li><strong>C 可减小：</strong>避免纸带刮擦，减小摩擦阻力。</li>
        <li><strong>D 可减小：</strong>电火花计时器纸带摩擦更小，且可直接使用 220V 交流电源。</li>
        <li><strong>E 不一定减小，反而要谨慎：</strong>这只是把多个打点合并为一个计数点，间距变大相对读数误差变小，
        但<strong>前提是 T 必须改为 0.10 s</strong>，否则速度算出来会差 5 倍——这正是网页工具上常见的输入错误。</li>
      </ul>
    `,
  },
  {
    kind: 'open',
    number: 10,
    difficulty: '拓展',
    category: '误差分析与改进',
    stem: `
      <p>本实验是"<strong>验证性</strong>实验"。
      为什么不直接代入默认的 g = 9.788 m/s² 计算 ½ mv²，
      而要先从纸带读出 v，再做能量比较？请从"自由落体模型"与"实际下落"的差别出发，
      说明这种处理方法的科学意义。</p>
    `,
    explanation: `
      <p>实验目的是<strong>验证</strong>机械能守恒，前提是不能预设结论里的物理量。
      若直接用 g = 9.788 计算 ½ mv²（其实是用 h 反推 v），就退化为"用守恒律算守恒律"，逻辑循环。</p>
      <p>正确方法：从纸带读出<strong>独立测量量</strong> x<sub>n</sub>，由运动学（中间点定理）得到 v<sub>n</sub>，
      再用 g、m 算 mgh 与 ½ mv² 进行<strong>独立比较</strong>。这样 v<sub>n</sub> 就和 h<sub>n</sub> 在原始数据上分离开，
      二者的接近才能作为守恒律成立的证据，也才能体现"自由落体模型 vs 实际下落"的差距——
      这是物理实验"独立测量、独立验证"的基本要求。</p>
    `,
  },
];
