import type { ExperimentReviewData } from './types';

export const fallingBodyReview: ExperimentReviewData = {
  purpose:
    '让重锤自由下落带动纸带，电磁打点计时器以 50 Hz 在纸带上打点。取 0、1、2、…、n 号计数点，以 1 号点作为能量分析起点，比较从 1 号点到 n 号点过程中重力势能减少量 ΔE<sub>p</sub> = mg(x<sub>n</sub> − x<sub>1</sub>) 与动能增加量 ΔE<sub>k</sub> = <span class="formula-frac"><span>1</span><span>2</span></span>m(v<sub>n</sub><sup>2</sup> − v<sub>1</sub><sup>2</sup>) 是否近似相等，从而验证机械能守恒定律。',
  apparatus: [
    '铁架台',
    '电磁打点计时器',
    '220V 交流电源',
    '重锤（约 100 g）',
    '纸带',
  ],
  procedure: [
    { text: '安装铁架台、打点计时器，把重锤连上纸带，纸带穿过限位孔。' },
    { text: '先接通电源，再释放纸带，取一条点迹清晰、起始端打点完整的纸带。' },
    { text: '在纸带上选取清晰、间距适当的位置作为 0 号计数点，依次记 0、1、2、…、n；其中 0 号点只作为位置读数零点。' },
    { text: '测量各点到 0 号点的距离 x<sub>n</sub>；能量分析从 1 号点开始，下落距离 h<sub>n</sub> = x<sub>n</sub> − x<sub>1</sub>。' },
    { text: '用中间点定理 v<sub>n</sub> = (x<sub>n+1</sub> − x<sub>n−1</sub>) ⁄ (2T) 求 n 号点的瞬时速度。' },
    { text: '逐点比较 mg(x<sub>n</sub> − x<sub>1</sub>) 与 <span class="formula-frac"><span>1</span><span>2</span></span>m(v<sub>n</sub><sup>2</sup> − v<sub>1</sub><sup>2</sup>)，按 δ = |1 − ΔE<sub>p</sub> / ΔE<sub>k</sub>| 分析相对误差与变化趋势。' },
  ],
  formulas: [
    {
      label: '能量比较',
      expression:
        'ΔE<sub>p</sub> = mg(x<sub>n</sub> − x<sub>1</sub>)，&nbsp;&nbsp;ΔE<sub>k</sub> = <span class="formula-frac"><span>1</span><span>2</span></span>m(v<sub>n</sub><sup>2</sup> − v<sub>1</sub><sup>2</sup>)',
    },
    {
      label: '相对误差',
      expression: 'δ = |1 − ΔE<sub>p</sub> / ΔE<sub>k</sub>|',
      note: '这里把动能增加量作为比较基准，便于判断势能减少量与动能增加量的相对偏离。',
    },
    {
      label: '下落距离',
      expression: 'h<sub>n</sub> = x<sub>n</sub> − x<sub>1</sub>',
    },
    {
      label: '中间点定理（求瞬时速度）',
      expression:
        'v<sub>n</sub> = (x<sub>n+1</sub> − x<sub>n−1</sub>) ⁄ (2T)',
      note: '匀变速直线运动中，某段时间内的平均速度等于该段时间中点的瞬时速度。',
    },
  ],
  parameters: [
    { symbol: 'm', value: '0.1000 kg', description: '重锤质量' },
    { symbol: 'g', value: '9.7880 m/s²', description: '当地重力加速度' },
    {
      symbol: 'T',
      value: '0.0200 s',
      description: '相邻计数点时间间隔（不抽点时）',
    },
  ],
  notes: [
    '实际教学中常每隔几个打点取 1 个计数点，此时 T 要相应改为 0.04 s 或 0.10 s。',
    '网页上"相邻计数点时间 T"必须按你实际选取的间隔填写，否则速度会差几倍。',
    '操作顺序遵循"先通电再释放纸带"，避免纸带前段缺少打点导致 0、1 号点附近数据不可靠。',
  ],
};
