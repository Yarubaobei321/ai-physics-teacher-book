import type { ExperimentReviewData } from './types';

export const curvedRampReview: ExperimentReviewData = {
  purpose:
    '将金属圆柱体由静止从 A、B 或 C 点释放，沿曲线运动到最低点 D，光电门测得 D 处速度 v。比较从释放点到 D 点过程中的重力势能减少量 ΔE<sub>p</sub> = mgΔh 与动能增加量 ΔE<sub>k</sub> = <span class="formula-frac"><span>1</span><span>2</span></span>mv<sup>2</sup> 是否近似相等。',
  apparatus: [
    'DIS 机械能实验器（带 A、B、C、D 四个标定位置的圆形轨道）',
    '双头光电门（位于 D 点附近）',
    '金属圆柱体',
  ],
  procedure: [
    { text: '把金属圆柱体放在 A 或 B 或 C 点，由静止释放。' },
    { text: '金属圆柱体沿曲线运动到最低点 D，前缘先后通过双头光电门两个探头。' },
    { text: '读取时间差 Δt，由 v = L ⁄ Δt 得到 D 处速度（L = 1 cm 为两探头固定间距）。' },
    { text: '记录 m、Δh，计算 ΔE<sub>p</sub> 与 ΔE<sub>k</sub>，按 δ = |1 − ΔE<sub>p</sub> / ΔE<sub>k</sub>| 比较相对误差。' },
    { text: '在 A、B、C 三点重复，做多组数据并可作 v<sup>2</sup>-Δh 图。' },
  ],
  formulas: [
    {
      label: '能量比较',
      expression:
        'ΔE<sub>p</sub> = m g Δh，&nbsp;&nbsp;ΔE<sub>k</sub> = <span class="formula-frac"><span>1</span><span>2</span></span>m v<sup>2</sup> − 0 = <span class="formula-frac"><span>1</span><span>2</span></span>m v<sup>2</sup>',
    },
    {
      label: '相对误差',
      expression: 'δ = |1 − ΔE<sub>p</sub> / ΔE<sub>k</sub>|',
      note: '页面按这个表达式比较势能减少量和动能增加量。',
    },
    {
      label: '速度的获取（双头光电门）',
      expression: 'v = L ⁄ Δt',
      note: '金属圆柱体直径 d 不参与速度计算，仅作为实验记录项，便于对比不同直径圆柱体的结果。',
    },
  ],
  parameters: [
    { symbol: 'm', value: '100 g', description: '金属圆柱体质量' },
    { symbol: 'g', value: '9.7880 m/s²', description: '重力加速度' },
    { symbol: 'd', value: '1.0000 cm', description: '金属圆柱体直径（仅记录）' },
    { symbol: 'L', value: '1.0 cm', description: '双头光电门两探头距离' },
    {
      symbol: 'Δh<sub>A,B,C</sub>',
      value: '由实验装置给定',
      description: 'A / B / C 三点相对 D 的高度差',
    },
  ],
  notes: [
    '本实验的"质心"概念至关重要——Δh 应当是金属圆柱体质心（圆柱中心）从释放点到 D 点的高度变化。',
    '光电门应该测金属圆柱体质心通过 D 点时的速度，若触发位置对应前缘或后缘，需要在数据解释中说明这一近似。',
    '滚动状态下 ½mv<sup>2</sup> 仅是平动动能，部分动能以转动动能 ½Iω<sup>2</sup> 形式存在，是 ΔE<sub>k</sub> 偏小的主因之一。',
  ],
};
