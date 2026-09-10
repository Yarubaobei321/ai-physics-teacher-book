import type { ExperimentReviewData } from './types';

export const airTrackReview: ExperimentReviewData = {
  purpose:
    '重锤下落 h，滑块在水平气垫导轨上同步加速。取"滑块 + 重锤"为系统，绳上张力是系统内力，比较重锤重力势能减少量 ΔE<sub>p</sub> = mgh 与系统动能增加量 ΔE<sub>k</sub> = <span class="formula-frac"><span>1</span><span>2</span></span>(M+m)(v<sub>2</sub><sup>2</sup> − v<sub>1</sub><sup>2</sup>) 是否近似相等。',
  apparatus: [
    '水平气垫导轨',
    '两双头光电门（前 / 后各一）',
    '带遮光条的滑块（质量 M）',
    '重锤（质量 m，通过细绳和滑轮与滑块连接）',
  ],
  procedure: [
    { text: '将气垫导轨调节水平：先开启气源，从两端反方向释放滑块观察漂移是否对称；再推动滑块，比较它通过前、后两只光电门的速度是否基本相同。' },
    { text: '安装两只双头光电门（前 / 后），固定其间距 L。' },
    { text: '由静止释放重锤，滑块依次通过前、后光电门，得到两次速度 v<sub>1</sub>、v<sub>2</sub>。' },
    { text: '记录重锤下落高度 h、滑块质量 M、重锤质量 m。' },
    { text: '比较 ΔE<sub>p</sub> 与 ΔE<sub>k</sub>，按 δ = |1 − ΔE<sub>p</sub> / ΔE<sub>k</sub>| 计算相对误差，重复多次取平均。' },
  ],
  formulas: [
    {
      label: '能量比较（系统视角）',
      expression:
        'ΔE<sub>p</sub> = mgh，&nbsp;&nbsp;ΔE<sub>k</sub> = <span class="formula-frac"><span>1</span><span>2</span></span>(M + m)(v<sub>2</sub><sup>2</sup> − v<sub>1</sub><sup>2</sup>)',
      note: '绳不可伸长，重锤与滑块速率相同；张力是内力，作用-反作用做功之和为 0。',
    },
    {
      label: '相对误差',
      expression: 'δ = |1 − ΔE<sub>p</sub> / ΔE<sub>k</sub>|',
      note: '页面按这个表达式比较重锤势能减少量和系统动能增加量。',
    },
    {
      label: '速度的获取（双头光电门）',
      expression:
        'v = L ⁄ Δt（两探头间距 ÷ 时间差）&nbsp;&nbsp;或&nbsp;&nbsp;v = b ⁄ Δt（遮光条宽度 ÷ 时间差）',
      note: '页面上的双头光电门用的是前者（"两探头距离 ÷ 时间差"）。',
    },
  ],
  parameters: [
    { symbol: 'g', value: '9.7880 m/s²', description: '重力加速度' },
    { symbol: 'M', value: '160 g', description: '滑块质量（含遮光条）' },
    { symbol: 'm', value: '50 ～ 100 g', description: '重锤质量' },
    { symbol: 'h', value: '50 ～ 80 cm', description: '重锤下落高度' },
  ],
  notes: [
    '页面中质量列单位为 g、高度单位为 cm，自动换算为 SI 单位参与计算。',
    '前光电门通常布置在释放点下游 5 ～ 10 cm 处，避开释放扰动；此时 v<sub>1</sub> ≠ 0。',
    '从两端反方向释放滑块观察漂移是否对称属于粗调；精细调平需要推动滑块，让它以基本相同的速度通过前、后两只光电门。',
  ],
};
