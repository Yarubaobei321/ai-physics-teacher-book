/*
 * 转盘式法拉第实验的物理模型（王硕老师装置的简化）。
 * 光盘在 x-y 平面内绕原点转动；一排小磁铁贴在半径 R 处，磁化方向沿 +z（N 面朝向线圈）。
 * 线圈轴线沿 z，穿过磁铁轨道的最高点 (0, R)，近端面离光盘 D，绕组在 [D, D+depth] 内分层。
 * 每个磁铁按磁偶极子处理，单匝磁通量用矢势沿线圈的环路积分求得：Phi = ∮A·dl。
 * 感应电动势 ε = −N dΦ/dt = −N ω dΦ/dθ。
 */
(function (root) {
  "use strict";
  const MU0 = 4e-7 * Math.PI;
  const GEOMETRY = {
    discRadius: 0.06,      // 光盘半径 / m
    orbitRadius: 0.05,     // 磁铁中心到转轴 / m
    coilRadius: 0.02,      // 线圈平均半径 / m（估计值）
    coilDepth: 0.03,       // 绕组沿轴向的厚度 / m（估计值）
    magnetMoment: 0.48,    // 单个磁铁的磁矩 / (A·m²)（按 10 mm×10 mm×5 mm、N35 估计）
    magnetPitch: 0.011     // 并排磁铁中心沿圆周的间距 / m
  };
  const GRID = 720;        // 一圈取 720 个角度点

  // 磁偶极子（位于 (px,py,0)，磁矩沿 z）穿过圆环（圆心 (cx,cy,cz)，法向 z）的磁通量
  function loopFlux(px, py, m, a, cx, cy, cz, K) {
    const k0 = MU0 / (4 * Math.PI) * m;
    let s = 0;
    for (let i = 0; i < K; i++) {
      const t1 = 2 * Math.PI * i / K, t2 = 2 * Math.PI * (i + 1) / K, tm = (t1 + t2) / 2;
      const x = cx + a * Math.cos(tm), y = cy + a * Math.sin(tm);
      const dlx = a * (Math.cos(t2) - Math.cos(t1)), dly = a * (Math.sin(t2) - Math.sin(t1));
      const rx = x - px, ry = y - py, rz = cz;
      const r3 = Math.pow(rx * rx + ry * ry + rz * rz, 1.5);
      s += (-k0 * ry / r3) * dlx + (k0 * rx / r3) * dly;
    }
    return s;
  }

  /*
   * 计算单匝磁通量 Φ1(θ) 与 dΦ1/dθ 的表。θ 是磁铁组中心的转角，θ=0 时正对线圈，顺时针为正。
   * magnets: 磁铁个数；distance: 线圈近端面到光盘的距离 / m；
   * arrangement: "stack" 叠成一组（磁矩相加，位置相同），"row" 沿光盘边缘并排。
   */
  function buildTable(magnets, distance, arrangement) {
    const g = GEOMETRY, layers = 5, K = 48;
    const phi = new Float64Array(GRID), dphi = new Float64Array(GRID);
    for (let k = 0; k < GRID; k++) {
      const th = 2 * Math.PI * k / GRID;
      let total = 0;
      const groups = arrangement === "row" ? magnets : 1;
      const moment = arrangement === "row" ? g.magnetMoment : g.magnetMoment * magnets;
      for (let j = 0; j < groups; j++) {
        const ang = th + (j - (groups - 1) / 2) * (g.magnetPitch / g.orbitRadius);
        const px = g.orbitRadius * Math.sin(ang), py = g.orbitRadius * Math.cos(ang);
        for (let L = 0; L < layers; L++) {
          const cz = distance + g.coilDepth * (L + 0.5) / layers;
          total += loopFlux(px, py, moment, g.coilRadius, 0, g.orbitRadius, cz, K) / layers;
        }
      }
      phi[k] = total;
    }
    const h = 2 * Math.PI / GRID;
    for (let k = 0; k < GRID; k++) {
      dphi[k] = (phi[(k + 1) % GRID] - phi[(k - 1 + GRID) % GRID]) / (2 * h);
    }
    let max = -Infinity, min = Infinity;
    for (let k = 0; k < GRID; k++) { max = Math.max(max, phi[k]); min = Math.min(min, phi[k]); }
    return { phi, dphi, phiMax: max, phiMin: min };
  }

  function interp(arr, theta) {
    let u = (theta / (2 * Math.PI)) * GRID;
    u = ((u % GRID) + GRID) % GRID;
    const i = Math.floor(u), f = u - i;
    return arr[i] * (1 - f) + arr[(i + 1) % GRID] * f;
  }

  /*
   * 一组实验条件。时间 t=0 时磁铁在离线圈最远处（θ=π）。
   * 返回的电压单位为 V，磁通量单位为 Wb。
   */
  function createExperiment(opts) {
    const table = buildTable(opts.magnets, opts.distance, opts.arrangement || "stack");
    const omega = 2 * Math.PI * opts.rpm / 60;
    const theta0 = opts.theta0 === undefined ? Math.PI : opts.theta0;
    const exp = {
      turns: opts.turns, magnets: opts.magnets, rpm: opts.rpm, distance: opts.distance, arrangement: opts.arrangement || "stack",
      omega, period: 60 / opts.rpm, table, theta0,
      theta(t) { return theta0 + omega * t; },
      flux1(t) { return interp(table.phi, theta0 + omega * t); },          // 单匝 / Wb
      emf(t) { return -opts.turns * omega * interp(table.dphi, theta0 + omega * t); }, // V
      // 一个半周的面积 = N(Φmax − Φmin)，与转速无关 / (V·s)
      lobeArea() { return opts.turns * (table.phiMax - table.phiMin); },
      peakEmf() {
        let m = 0;
        for (let k = 0; k < GRID; k++) m = Math.max(m, -opts.turns * omega * table.dphi[k]);
        return m;
      }
    };
    return exp;
  }

  /* 传感器采样：从 offset 开始每 1/rate 秒取一个瞬时值，可按分辨率取整（V）。 */
  function sampleAt(exp, k, rate, offset, resolution) {
    const t = offset + k / rate;
    let v = exp.emf(t);
    if (resolution > 0) v = Math.round(v / resolution) * resolution;
    return { t, v };
  }

  root.FaradayModel = { GEOMETRY, GRID, buildTable, createExperiment, sampleAt };
})(typeof window !== "undefined" ? window : globalThis);
if (typeof module !== "undefined") module.exports = globalThis.FaradayModel || window.FaradayModel;
