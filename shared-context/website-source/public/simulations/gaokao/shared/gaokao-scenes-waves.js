const COLORS = Object.freeze({
  ink: '#102033',
  muted: '#566a7f',
  line: '#c8d7e4',
  blue: '#0b63c7',
  blueDark: '#064b98',
  blueSoft: '#dbeafe',
  amber: '#c46d08',
  amberBright: '#f0a11b',
  amberSoft: '#fff0cf',
  green: '#14734b',
  greenSoft: '#e7f6ee',
  paper: 'rgba(255,255,255,.88)',
  water: 'rgba(192,224,247,.58)'
});

const FONT_STACK = '"Avenir Next", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif';
const SCENES = new Set(['ropeWave', 'travelingWave', 'springOscillator', 'forcedDoppler', 'echoSounder']);
const TAU = Math.PI * 2;

const clamp = (value, minimum = 0, maximum = 1) => Math.min(maximum, Math.max(minimum, value));
const lerp = (start, end, amount) => start + (end - start) * amount;
const finite = (value, fallback = 0) => Number.isFinite(Number(value)) ? Number(value) : fallback;
const positive = (value, fallback = 1) => Math.max(1e-9, finite(value, fallback));
const phaseTime = (baseTime, period, phase) => baseTime + phase * period;
const echoTargetDistanceAtPhase = (distance, targetSpeed, echoTime, phase) => distance - targetSpeed * echoTime * phase;

function formatNumber(value, digits = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  if (Math.abs(number) >= 100000 || (Math.abs(number) > 0 && Math.abs(number) < .001)) {
    return number.toExponential(Math.min(2, digits));
  }
  return number.toFixed(digits);
}

function roundedPath(context, x, y, width, height, radius = 10) {
  const r = Math.min(Math.max(radius, 0), Math.abs(width) / 2, Math.abs(height) / 2);
  context.beginPath();
  context.moveTo(x + r, y);
  context.lineTo(x + width - r, y);
  context.quadraticCurveTo(x + width, y, x + width, y + r);
  context.lineTo(x + width, y + height - r);
  context.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  context.lineTo(x + r, y + height);
  context.quadraticCurveTo(x, y + height, x, y + height - r);
  context.lineTo(x, y + r);
  context.quadraticCurveTo(x, y, x + r, y);
  context.closePath();
}

function box(context, x, y, width, height, options = {}) {
  if (width <= 0 || height <= 0) return;
  context.save();
  roundedPath(context, x, y, width, height, options.radius ?? 11);
  if (options.fill !== false) {
    context.fillStyle = options.fill || COLORS.paper;
    context.fill();
  }
  if (options.stroke !== false) {
    context.strokeStyle = options.stroke || COLORS.line;
    context.lineWidth = options.lineWidth || 1;
    context.stroke();
  }
  context.restore();
}

function line(context, points, color = COLORS.blue, width = 2, dash = []) {
  if (!Array.isArray(points) || points.length < 2) return;
  context.save();
  context.strokeStyle = color;
  context.lineWidth = width;
  context.lineCap = 'round';
  context.lineJoin = 'round';
  context.setLineDash(dash);
  context.beginPath();
  context.moveTo(points[0][0], points[0][1]);
  for (let index = 1; index < points.length; index += 1) context.lineTo(points[index][0], points[index][1]);
  context.stroke();
  context.restore();
}

function fittedText(context, value, x, y, options = {}) {
  const original = String(value ?? '');
  const weight = options.weight || 700;
  let size = options.size || 12;
  const minimum = options.minimumSize || 7;
  const maximumWidth = Math.max(0, options.maximumWidth ?? Number.POSITIVE_INFINITY);
  context.save();
  context.textAlign = options.align || 'left';
  context.textBaseline = options.baseline || 'alphabetic';
  context.fillStyle = options.color || COLORS.ink;
  context.font = `${weight} ${size}px ${FONT_STACK}`;
  while (size > minimum && context.measureText(original).width > maximumWidth) {
    size -= 1;
    context.font = `${weight} ${size}px ${FONT_STACK}`;
  }
  let output = original;
  if (Number.isFinite(maximumWidth) && context.measureText(output).width > maximumWidth) {
    const characters = Array.from(original);
    while (characters.length > 1 && context.measureText(`${characters.join('')}…`).width > maximumWidth) characters.pop();
    output = `${characters.join('')}…`;
  }
  context.fillText(output, x, y);
  context.restore();
}

function pill(context, label, x, y, width, options = {}) {
  const height = options.height || 23;
  box(context, x, y, width, height, {
    radius: height / 2,
    fill: options.fill || COLORS.blueSoft,
    stroke: options.stroke || 'rgba(11,99,199,.18)'
  });
  fittedText(context, label, x + width / 2, y + height / 2 + .5, {
    size: options.size || 9,
    minimumSize: 7,
    weight: 900,
    color: options.color || COLORS.blueDark,
    align: 'center',
    baseline: 'middle',
    maximumWidth: Math.max(0, width - 10)
  });
}

function arrow(context, x1, y1, x2, y2, color = COLORS.amber, label = '', options = {}) {
  const angle = Math.atan2(y2 - y1, x2 - x1);
  const head = options.head || 7;
  context.save();
  context.strokeStyle = color;
  context.fillStyle = color;
  context.lineWidth = options.width || 2.4;
  context.lineCap = 'round';
  context.beginPath();
  context.moveTo(x1, y1);
  context.lineTo(x2, y2);
  context.stroke();
  context.beginPath();
  context.moveTo(x2, y2);
  context.lineTo(x2 - head * Math.cos(angle - Math.PI / 6), y2 - head * Math.sin(angle - Math.PI / 6));
  context.lineTo(x2 - head * Math.cos(angle + Math.PI / 6), y2 - head * Math.sin(angle + Math.PI / 6));
  context.closePath();
  context.fill();
  if (label) {
    const horizontal = Math.abs(x2 - x1) >= Math.abs(y2 - y1);
    fittedText(context, label, (x1 + x2) / 2 + (horizontal ? 0 : 9), (y1 + y2) / 2 + (horizontal ? -7 : 3), {
      size: 9,
      weight: 900,
      color,
      align: horizontal ? 'center' : 'left',
      maximumWidth: horizontal ? Math.abs(x2 - x1) + 32 : 74
    });
  }
  context.restore();
}

function doubleArrow(context, x1, y1, x2, y2, color = COLORS.muted, label = '') {
  arrow(context, x1, y1, x2, y2, color, label, { head: 6, width: 1.8 });
  arrow(context, x2, y2, x1, y1, color, '', { head: 6, width: 1.8 });
}

function sceneHeader(context, width, spec, title, phase) {
  const margin = clamp(width * .035, 10, 24);
  const stages = Array.isArray(spec?.phases) && spec.phases.length ? spec.phases : ['观察物理过程'];
  const stageIndex = Math.min(stages.length - 1, Math.floor(clamp(phase) * stages.length));
  const stage = stages[stageIndex];
  if (width < 470) {
    fittedText(context, title, margin, 20, { size: 14, minimumSize: 10, weight: 950, maximumWidth: width - margin * 2 });
    pill(context, stage, margin, 30, width - margin * 2, { height: 22, size: 9 });
    return 62;
  }
  fittedText(context, title, margin, 29, { size: 16, minimumSize: 11, weight: 950, maximumWidth: width * .57 });
  const chipWidth = clamp(width * .27, 132, 190);
  pill(context, stage, width - margin - chipWidth, 14, chipWidth, { height: 25, size: 9 });
  return 52;
}

function statusStrip(context, width, height, items) {
  const margin = clamp(width * .035, 10, 24);
  const gap = width < 430 ? 4 : 7;
  const y = height - 37;
  const available = width - margin * 2 - gap * (items.length - 1);
  const itemWidth = available / items.length;
  items.forEach((item, index) => {
    pill(context, item.label, margin + index * (itemWidth + gap), y, itemWidth, {
      height: 24,
      size: width < 430 ? 8 : 9,
      fill: item.fill || COLORS.paper,
      stroke: item.stroke || COLORS.line,
      color: item.color || COLORS.ink
    });
  });
}

function drawAxisLabel(context, label, x, y, options = {}) {
  fittedText(context, label, x, y, {
    size: options.size || 8,
    weight: 850,
    color: options.color || COLORS.muted,
    align: options.align || 'left',
    maximumWidth: options.maximumWidth || 92
  });
}

function drawWavePath(context, x, y, width, height, physicalSpan, displacement, color = COLORS.blue, lineWidth = 3) {
  const points = [];
  const samples = Math.max(90, Math.round(width / 2));
  for (let index = 0; index <= samples; index += 1) {
    const ratio = index / samples;
    const physicalX = physicalSpan * ratio;
    points.push([x + width * ratio, y + height / 2 - displacement(physicalX) * height / 2]);
  }
  line(context, points, color, lineWidth);
}

function drawRopeWave(context, width, height, spec, result, input, phase) {
  const top = sceneHeader(context, width, spec, '波形向前传，绳上质点只做往复运动', phase);
  const margin = clamp(width * .035, 10, 24);
  const bottom = height - 46;
  const panelX = margin;
  const panelY = top + 6;
  const panelW = width - margin * 2;
  const panelH = Math.max(90, bottom - panelY - 2);
  box(context, panelX, panelY, panelW, panelH, { radius: 13, fill: 'rgba(255,255,255,.73)', stroke: COLORS.line });

  const amplitude = positive(input.amplitude, .15);
  const wavelength = positive(result.wavelength, positive(input.waveSpeed, 2) / positive(input.frequency, 1.5));
  const period = positive(result.period, 1 / positive(input.frequency, 1.5));
  const speed = positive(input.waveSpeed, 2);
  const markerX = Math.max(0, finite(input.markerX));
  const physicalSpan = Math.max(3 * wavelength, markerX + .7 * wavelength);
  const currentTime = phaseTime(0, period, phase);
  const plotX = panelX + 20;
  const plotW = Math.max(60, panelW - 40);
  const plotY = panelY + 39;
  const plotH = Math.max(48, panelH - 67);
  const equilibriumY = plotY + plotH / 2;
  const amplitudeScale = .78;
  const displacement = (x) => amplitudeScale * Math.cos(TAU * (x / wavelength - currentTime / period));

  line(context, [[plotX, equilibriumY], [plotX + plotW, equilibriumY]], '#8fa5b8', 1.2, [6, 5]);
  drawAxisLabel(context, 'y=0 平衡位置', plotX, equilibriumY - 6, { maximumWidth: 96 });
  arrow(context, plotX + plotW * .66, panelY + 22, plotX + plotW * .88, panelY + 22, COLORS.blueDark, '波形 +x');
  drawWavePath(context, plotX, plotY, plotW, plotH, physicalSpan, displacement, COLORS.blue, 3.2);

  const movingCrestBase = speed * currentTime;
  const crestIndex = Math.round((physicalSpan * .55 - movingCrestBase) / wavelength);
  const crestPhysicalX = clamp(movingCrestBase + crestIndex * wavelength, 0, physicalSpan);
  const crestCanvasX = plotX + plotW * crestPhysicalX / physicalSpan;
  const crestCanvasY = equilibriumY - amplitudeScale * plotH / 2;
  context.fillStyle = COLORS.amberBright;
  context.beginPath();
  context.arc(crestCanvasX, crestCanvasY, 5, 0, TAU);
  context.fill();
  line(context, [[crestCanvasX, crestCanvasY + 7], [crestCanvasX, equilibriumY]], 'rgba(196,109,8,.42)', 1.2, [4, 4]);
  fittedText(context, '波峰', crestCanvasX, Math.max(panelY + 15, crestCanvasY - 10), { size: 9, weight: 950, color: COLORS.amber, align: 'center', maximumWidth: 44 });

  const markerCanvasX = plotX + plotW * markerX / physicalSpan;
  const markerValue = amplitude * Math.cos(TAU * (markerX / wavelength - currentTime / period));
  const markerCanvasY = equilibriumY - markerValue / amplitude * amplitudeScale * plotH / 2;
  line(context, [[markerCanvasX, plotY + 3], [markerCanvasX, plotY + plotH - 3]], 'rgba(196,109,8,.46)', 1.4, [5, 4]);
  context.fillStyle = '#fff';
  context.strokeStyle = COLORS.amber;
  context.lineWidth = 2;
  context.beginPath();
  context.arc(markerCanvasX, equilibriumY, 4, 0, TAU);
  context.fill();
  context.stroke();
  context.fillStyle = COLORS.amber;
  context.beginPath();
  context.arc(markerCanvasX, markerCanvasY, 7, 0, TAU);
  context.fill();
  doubleArrow(context, markerCanvasX + 15, equilibriumY, markerCanvasX + 15, markerCanvasY, COLORS.amber, 'yₘ');
  fittedText(context, `固定质点 xₘ=${formatNumber(markerX, 2)} m`, clamp(markerCanvasX, plotX + 68, plotX + plotW - 68), plotY + plotH + 16, {
    size: 9,
    weight: 900,
    color: COLORS.amber,
    align: 'center',
    maximumWidth: 136
  });

  pill(context, '蓝线：波形水平传播', panelX + 10, panelY + 8, Math.min(142, panelW * .45), { height: 20, size: 8 });
  if (panelW > 330) pill(context, '琥珀点：质点竖直振动', panelX + panelW - Math.min(157, panelW * .47) - 10, panelY + 8, Math.min(157, panelW * .47), { height: 20, size: 8, fill: COLORS.amberSoft, color: COLORS.amber, stroke: '#ead09c' });

  statusStrip(context, width, height, [
    { label: `λ ${formatNumber(wavelength, 2)} m` },
    { label: `T ${formatNumber(period, 2)} s` },
    { label: `yₘ ${formatNumber(markerValue, 2)} m`, color: COLORS.amber }
  ]);
}

function drawTravelingWave(context, width, height, spec, result, input, phase) {
  const top = sceneHeader(context, width, spec, '行波向前平移，固定探针记录自己的历史', phase);
  const margin = clamp(width * .035, 10, 24);
  const bottom = height - 46;
  const gap = 7;
  const availableH = Math.max(160, bottom - top - 5);
  const upperH = availableH * (width < 470 ? .55 : .57);
  const lowerH = availableH - upperH - gap;
  const upper = { x: margin, y: top + 4, w: width - margin * 2, h: upperH };
  const lower = { x: margin, y: top + 4 + upperH + gap, w: width - margin * 2, h: lowerH };
  box(context, upper.x, upper.y, upper.w, upper.h, { radius: 12, fill: 'rgba(255,255,255,.76)', stroke: COLORS.line });
  box(context, lower.x, lower.y, lower.w, lower.h, { radius: 12, fill: 'rgba(255,255,255,.76)', stroke: COLORS.line });

  const amplitude = positive(input.amplitude, .1);
  const speed = positive(input.waveSpeed, 1);
  const wavelength = positive(input.wavelength, 2);
  const period = positive(result.period, wavelength / speed);
  const probeX = Math.max(0, finite(input.probeX, 1.5));
  const baseTime = Math.max(0, finite(input.probeTime, 1));
  const currentTime = phaseTime(baseTime, period, phase);
  const physicalSpan = Math.max(2 * wavelength, probeX + .45 * wavelength);

  fittedText(context, '空间快照 y—x', upper.x + 10, upper.y + 18, { size: 10, weight: 950, maximumWidth: 106 });
  arrow(context, upper.x + upper.w - 95, upper.y + 14, upper.x + upper.w - 22, upper.y + 14, COLORS.blueDark, '+x 传播');
  const ux = upper.x + 16;
  const uy = upper.y + 27;
  const uw = upper.w - 32;
  const uh = Math.max(42, upper.h - 39);
  const ueq = uy + uh / 2;
  line(context, [[ux, ueq], [ux + uw, ueq]], '#91a8bb', 1, [6, 5]);
  const spatial = (x) => .79 * Math.sin(TAU * (x - speed * currentTime) / wavelength);
  drawWavePath(context, ux, uy, uw, uh, physicalSpan, spatial, COLORS.blue, 3);
  const probeCanvasX = ux + uw * probeX / physicalSpan;
  const probeValue = amplitude * Math.sin(TAU * (probeX - speed * currentTime) / wavelength);
  const probeCanvasY = ueq - probeValue / amplitude * .79 * uh / 2;
  line(context, [[probeCanvasX, uy], [probeCanvasX, uy + uh]], COLORS.amber, 1.4, [5, 4]);
  context.fillStyle = COLORS.amber;
  context.beginPath();
  context.arc(probeCanvasX, probeCanvasY, 6, 0, TAU);
  context.fill();
  fittedText(context, '固定探针', clamp(probeCanvasX, ux + 38, ux + uw - 38), uy + 11, { size: 8, weight: 950, color: COLORS.amber, align: 'center', maximumWidth: 76 });

  fittedText(context, '探针历史 y—t', lower.x + 10, lower.y + 17, { size: 9, weight: 950, maximumWidth: 100 });
  const lx = lower.x + 18;
  const ly = lower.y + 24;
  const lw = lower.w - 36;
  const lh = Math.max(28, lower.h - 34);
  const leq = ly + lh / 2;
  line(context, [[lx, leq], [lx + lw, leq]], '#91a8bb', 1, [6, 5]);
  const history = [];
  for (let index = 0; index <= 100; index += 1) {
    const u = index / 100;
    const t = baseTime + u * period;
    const y = amplitude * Math.sin(TAU * (probeX - speed * t) / wavelength);
    history.push([lx + lw * u, leq - y / amplitude * lh * .39]);
  }
  line(context, history, COLORS.blueDark, 2.2);
  const cursorX = lx + lw * phase;
  const cursorY = leq - probeValue / amplitude * lh * .39;
  line(context, [[cursorX, ly], [cursorX, ly + lh]], 'rgba(196,109,8,.45)', 1.2, [4, 4]);
  context.fillStyle = COLORS.amber;
  context.beginPath();
  context.arc(cursorX, cursorY, 5, 0, TAU);
  context.fill();
  drawAxisLabel(context, `t₀=${formatNumber(baseTime, 1)} s`, lx, lower.y + lower.h - 5, { maximumWidth: 72 });
  drawAxisLabel(context, `t₀+T`, lx + lw, lower.y + lower.h - 5, { align: 'right', maximumWidth: 72 });

  statusStrip(context, width, height, [
    { label: `t ${formatNumber(currentTime, 2)} s` },
    { label: `xₚ ${formatNumber(probeX, 1)} m` },
    { label: `yₚ ${formatNumber(probeValue, 2)} m`, color: COLORS.amber }
  ]);
}

function drawVerticalSpring(context, x, y1, y2, width, turns, color = COLORS.blueDark) {
  const points = [[x, y1]];
  const span = Math.max(1, y2 - y1);
  const lead = Math.min(9, span * .12);
  points.push([x, y1 + lead]);
  for (let index = 0; index <= turns * 2; index += 1) {
    const amount = index / (turns * 2);
    points.push([x + (index % 2 === 0 ? -width / 2 : width / 2), lerp(y1 + lead, y2 - lead, amount)]);
  }
  points.push([x, y2]);
  line(context, points, color, 2.5);
}

function drawSpringOscillator(context, width, height, spec, result, input, phase) {
  const top = sceneHeader(context, width, spec, '竖直弹簧振子：位移与速度在同一相位上', phase);
  const margin = clamp(width * .035, 10, 24);
  const bottom = height - 46;
  const panelY = top + 5;
  const panelH = Math.max(145, bottom - panelY - 2);
  const leftW = width < 460 ? (width - margin * 2) * .59 : (width - margin * 2) * .62;
  const gap = 7;
  const left = { x: margin, y: panelY, w: leftW, h: panelH };
  const right = { x: margin + leftW + gap, y: panelY, w: width - margin * 2 - leftW - gap, h: panelH };
  box(context, left.x, left.y, left.w, left.h, { radius: 12, fill: 'rgba(255,255,255,.74)', stroke: COLORS.line });
  box(context, right.x, right.y, right.w, right.h, { radius: 12, fill: 'rgba(255,255,255,.82)', stroke: COLORS.line });

  const amplitude = positive(input.amplitude, .1);
  const period = positive(input.period, 2);
  const omega = finite(result.omega, TAU / period);
  const baseTime = Math.max(0, finite(input.time, 0));
  const currentTime = phaseTime(baseTime, period, phase);
  const angle = omega * currentTime;
  const displacement = amplitude * Math.cos(angle);
  const speed = -amplitude * omega * Math.sin(angle);
  const kineticFraction = Math.sin(angle) ** 2;

  const ceilingY = left.y + 18;
  const massH = clamp(left.h * .12, 24, 34);
  const eqY = left.y + left.h * .57;
  const travel = Math.min(left.h * .25, 56);
  const scale = travel / amplitude;
  const topEnd = eqY - travel;
  const bottomEnd = eqY + travel;
  const massY = eqY + displacement * scale;
  const springX = left.x + left.w * .51;
  const labelX = left.x + 8;

  line(context, [[left.x + left.w * .23, ceilingY], [left.x + left.w * .79, ceilingY]], COLORS.ink, 4);
  for (let x = left.x + left.w * .25; x < left.x + left.w * .79; x += 10) {
    line(context, [[x, ceilingY], [x + 7, ceilingY - 7]], '#71869a', 1.2);
  }
  drawVerticalSpring(context, springX, ceilingY + 2, massY - massH / 2, Math.min(28, left.w * .18), 7);

  line(context, [[left.x + 7, topEnd], [left.x + left.w - 7, topEnd]], 'rgba(11,99,199,.35)', 1, [4, 4]);
  line(context, [[left.x + 7, eqY], [left.x + left.w - 7, eqY]], 'rgba(20,115,75,.52)', 1.4, [6, 4]);
  line(context, [[left.x + 7, bottomEnd], [left.x + left.w - 7, bottomEnd]], 'rgba(196,109,8,.36)', 1, [4, 4]);
  fittedText(context, '最高点 −A', labelX, topEnd - 5, { size: 8, weight: 850, color: COLORS.blueDark, maximumWidth: left.w * .42 });
  fittedText(context, '平衡位置 0', labelX, eqY - 5, { size: 8, weight: 900, color: COLORS.green, maximumWidth: left.w * .42 });
  fittedText(context, '最低点 +A', labelX, bottomEnd + 13, { size: 8, weight: 850, color: COLORS.amber, maximumWidth: left.w * .42 });

  const massW = Math.min(64, left.w * .32);
  const massGradient = context.createLinearGradient(springX - massW / 2, 0, springX + massW / 2, 0);
  massGradient.addColorStop(0, '#0a4d91');
  massGradient.addColorStop(.55, '#1575d1');
  massGradient.addColorStop(1, '#073e75');
  box(context, springX - massW / 2, massY - massH / 2, massW, massH, { radius: 6, fill: massGradient, stroke: '#fff', lineWidth: 1.3 });
  fittedText(context, 'm', springX, massY + .5, { size: 11, weight: 950, color: '#fff', align: 'center', baseline: 'middle', maximumWidth: massW - 8 });

  if (Math.abs(displacement) > amplitude * .025) {
    doubleArrow(context, springX + massW / 2 + 12, eqY, springX + massW / 2 + 12, massY, COLORS.amber, 'x');
  }
  const maximumSpeed = amplitude * omega;
  const velocityLength = maximumSpeed > 0 ? clamp(Math.abs(speed) / maximumSpeed) * Math.min(42, left.h * .17) : 0;
  if (velocityLength > 3) {
    const direction = Math.sign(speed);
    arrow(context, springX - massW / 2 - 14, massY, springX - massW / 2 - 14, massY + direction * velocityLength, COLORS.blueDark, 'v');
  } else {
    pill(context, 'v ≈ 0', left.x + left.w - 55, left.y + 9, 46, { height: 20, size: 8, fill: COLORS.amberSoft, color: COLORS.amber, stroke: '#ead09c' });
  }

  fittedText(context, '相图 x—v/ω', right.x + 8, right.y + 18, { size: 9, weight: 950, maximumWidth: right.w - 16 });
  const portraitCenterX = right.x + right.w / 2;
  const portraitCenterY = right.y + right.h * .38;
  const radiusX = Math.max(22, right.w * .34);
  const radiusY = Math.min(right.h * .2, radiusX * .72);
  context.save();
  context.strokeStyle = '#8fb9dc';
  context.lineWidth = 2;
  context.setLineDash([4, 3]);
  context.beginPath();
  context.ellipse(portraitCenterX, portraitCenterY, radiusX, radiusY, 0, 0, TAU);
  context.stroke();
  context.restore();
  line(context, [[portraitCenterX - radiusX - 5, portraitCenterY], [portraitCenterX + radiusX + 5, portraitCenterY]], '#9cb0c1', 1);
  line(context, [[portraitCenterX, portraitCenterY - radiusY - 5], [portraitCenterX, portraitCenterY + radiusY + 5]], '#9cb0c1', 1);
  const phaseX = portraitCenterX + radiusX * displacement / amplitude;
  const phaseY = portraitCenterY - radiusY * speed / maximumSpeed;
  context.fillStyle = COLORS.amber;
  context.beginPath();
  context.arc(phaseX, phaseY, 5.5, 0, TAU);
  context.fill();
  drawAxisLabel(context, 'x', portraitCenterX + radiusX + 2, portraitCenterY - 5, { align: 'right', maximumWidth: 18 });
  drawAxisLabel(context, 'v/ω', portraitCenterX + 4, portraitCenterY - radiusY - 7, { maximumWidth: 28 });

  const cardY = right.y + right.h * .68;
  fittedText(context, `t = ${formatNumber(currentTime, 2)} s`, portraitCenterX, cardY, { size: 10, weight: 950, align: 'center', maximumWidth: right.w - 12 });
  fittedText(context, `x = ${formatNumber(displacement, 3)} m`, portraitCenterX, cardY + 18, { size: 9, weight: 900, color: COLORS.amber, align: 'center', maximumWidth: right.w - 12 });
  fittedText(context, `v = ${formatNumber(speed, 3)} m/s`, portraitCenterX, cardY + 36, { size: 9, weight: 900, color: COLORS.blueDark, align: 'center', maximumWidth: right.w - 12 });
  if (right.h > 166) fittedText(context, `K/Kₘₐₓ ${formatNumber(kineticFraction * 100, 0)}%`, portraitCenterX, right.y + right.h - 11, { size: 8, weight: 850, color: COLORS.green, align: 'center', maximumWidth: right.w - 12 });

  statusStrip(context, width, height, [
    { label: `A ${formatNumber(amplitude, 2)} m` },
    { label: `x ${formatNumber(displacement, 3)} m`, color: COLORS.amber },
    { label: `v ${formatNumber(speed, 3)} m/s`, color: COLORS.blueDark }
  ]);
}

function drawHorizontalSpring(context, x1, x2, y, height, turns, color = COLORS.blueDark) {
  const points = [[x1, y], [x1 + 8, y]];
  const innerStart = x1 + 8;
  const innerEnd = x2 - 8;
  for (let index = 0; index <= turns * 2; index += 1) {
    const amount = index / (turns * 2);
    points.push([lerp(innerStart, innerEnd, amount), y + (index % 2 === 0 ? -height / 2 : height / 2)]);
  }
  points.push([x2, y]);
  line(context, points, color, 2.2);
}

function drawResonanceCurve(context, x, y, width, height, result, currentFrequency) {
  const points = Array.isArray(result.chart) ? result.chart.filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y)) : [];
  if (points.length < 2) return;
  const minX = Math.min(...points.map((point) => point.x));
  const maxX = Math.max(...points.map((point) => point.x));
  const maxY = Math.max(...points.map((point) => point.y), 1);
  const mapped = points.map((point) => [
    x + (point.x - minX) / Math.max(1e-9, maxX - minX) * width,
    y + height - point.y / maxY * height
  ]);
  line(context, [[x, y + height], [x + width, y + height]], '#91a7b9', 1);
  line(context, [[x, y], [x, y + height]], '#91a7b9', 1);
  line(context, mapped, COLORS.blue, 2);
  const cursorX = x + clamp((currentFrequency - minX) / Math.max(1e-9, maxX - minX)) * width;
  const nearest = points.reduce((best, point) => Math.abs(point.x - currentFrequency) < Math.abs(best.x - currentFrequency) ? point : best, points[0]);
  const cursorY = y + height - nearest.y / maxY * height;
  line(context, [[cursorX, y], [cursorX, y + height]], 'rgba(196,109,8,.42)', 1, [4, 3]);
  context.fillStyle = COLORS.amber;
  context.beginPath();
  context.arc(cursorX, cursorY, 4.5, 0, TAU);
  context.fill();
}

function drawSpeaker(context, x, y, size, color = COLORS.amber) {
  context.save();
  context.fillStyle = color;
  context.beginPath();
  context.moveTo(x - size * .46, y - size * .22);
  context.lineTo(x - size * .18, y - size * .22);
  context.lineTo(x + size * .18, y - size * .46);
  context.lineTo(x + size * .18, y + size * .46);
  context.lineTo(x - size * .18, y + size * .22);
  context.lineTo(x - size * .46, y + size * .22);
  context.closePath();
  context.fill();
  context.strokeStyle = color;
  context.lineWidth = 1.8;
  context.beginPath();
  context.arc(x + size * .16, y, size * .34, -Math.PI / 3, Math.PI / 3);
  context.stroke();
  context.restore();
}

function drawMicrophone(context, x, y, size) {
  context.save();
  context.strokeStyle = COLORS.blueDark;
  context.fillStyle = COLORS.blueSoft;
  context.lineWidth = 2;
  roundedPath(context, x - size * .18, y - size * .43, size * .36, size * .58, size * .18);
  context.fill();
  context.stroke();
  context.beginPath();
  context.arc(x, y - size * .03, size * .32, 0, Math.PI);
  context.stroke();
  line(context, [[x, y + size * .29], [x, y + size * .52]], COLORS.blueDark, 2);
  line(context, [[x - size * .23, y + size * .52], [x + size * .23, y + size * .52]], COLORS.blueDark, 2);
  context.restore();
}

function drawForcedDoppler(context, width, height, spec, result, input, phase) {
  const top = sceneHeader(context, width, spec, '共振与多普勒：同样谈频率，比较的量不同', phase);
  const margin = clamp(width * .035, 10, 24);
  const bottom = height - 46;
  const gap = width < 430 ? 5 : 8;
  const panelW = (width - margin * 2 - gap) / 2;
  const panelH = Math.max(150, bottom - top - 2);
  const left = { x: margin, y: top + 3, w: panelW, h: panelH };
  const right = { x: margin + panelW + gap, y: top + 3, w: panelW, h: panelH };
  box(context, left.x, left.y, left.w, left.h, { radius: 12, fill: 'rgba(255,255,255,.8)', stroke: COLORS.line });
  box(context, right.x, right.y, right.w, right.h, { radius: 12, fill: 'rgba(255,255,255,.8)', stroke: COLORS.line });
  fittedText(context, '受迫振动', left.x + 9, left.y + 18, { size: 10, weight: 950, maximumWidth: left.w - 18 });
  fittedText(context, '移动声源与固定接收器', right.x + 9, right.y + 18, { size: 10, minimumSize: 7, weight: 950, maximumWidth: right.w - 18 });

  const naturalFrequency = positive(input.naturalFrequency, 2);
  const driveFrequency = positive(input.driveFrequency, 2);
  const damping = Math.max(0, finite(input.dampingRatio, .08));
  const ratio = finite(result.ratio, driveFrequency / naturalFrequency);
  const response = Math.max(0, finite(result.response, 0));
  const lag = Math.atan2(2 * damping * ratio, 1 - ratio ** 2);
  const rigY = left.y + left.h * .35;
  const wallX = left.x + 11;
  const centerX = left.x + left.w * .61;
  const travel = Math.min(24, left.w * .13) * clamp(response / 3, .12, 1);
  const blockX = centerX + travel * Math.cos(TAU * phase - lag);
  line(context, [[wallX, rigY - 31], [wallX, rigY + 31]], COLORS.ink, 4);
  for (let y = rigY - 28; y < rigY + 29; y += 8) line(context, [[wallX, y], [wallX - 6, y + 6]], '#71869a', 1);
  drawHorizontalSpring(context, wallX + 2, blockX - 21, rigY, 18, 6);
  box(context, blockX - 21, rigY - 19, 42, 38, { radius: 6, fill: COLORS.blue, stroke: '#fff', lineWidth: 1.2 });
  fittedText(context, 'm', blockX, rigY + .5, { size: 10, weight: 950, color: '#fff', align: 'center', baseline: 'middle', maximumWidth: 30 });
  const forceDirection = Math.cos(TAU * phase) >= 0 ? 1 : -1;
  arrow(context, blockX, rigY - 29, blockX + forceDirection * Math.min(34, left.w * .19), rigY - 29, COLORS.amber, 'F(t)');
  fittedText(context, `fₑ ${formatNumber(driveFrequency, 1)} Hz`, left.x + 9, left.y + 39, { size: 8, weight: 900, color: COLORS.blueDark, maximumWidth: left.w * .48 });
  fittedText(context, `f₀ ${formatNumber(naturalFrequency, 1)} Hz`, left.x + left.w - 9, left.y + 39, { size: 8, weight: 900, color: COLORS.amber, align: 'right', maximumWidth: left.w * .48 });

  const curveX = left.x + 13;
  const curveY = left.y + left.h * .61;
  const curveW = left.w - 26;
  const curveH = Math.max(28, left.h * .22);
  drawResonanceCurve(context, curveX, curveY, curveW, curveH, result, driveFrequency);
  fittedText(context, `响应倍数 ${formatNumber(response, 2)}`, left.x + left.w / 2, left.y + left.h - 10, { size: 8, weight: 900, color: COLORS.amber, align: 'center', maximumWidth: left.w - 16 });

  const soundSpeed = positive(input.soundSpeed, 340);
  const sourceFrequency = positive(input.sourceFrequency, 800);
  const relativeSpeed = finite(input.relativeSpeed, 0);
  const receivedFrequency = positive(result.receivedFrequency, sourceFrequency);
  const sourceBaseX = right.x + right.w * .27;
  const observerX = right.x + right.w * .83;
  const acousticY = right.y + right.h * .46;
  const physicalMotionRatio = clamp(Math.abs(relativeSpeed) / soundSpeed, 0, .3);
  const motionDistance = Math.max(2, physicalMotionRatio * right.w * .9);
  const sourceX = sourceBaseX + Math.sign(relativeSpeed) * motionDistance * phase;
  drawSpeaker(context, sourceX, acousticY, Math.min(27, right.w * .17));
  drawMicrophone(context, observerX, acousticY, Math.min(29, right.w * .18));
  if (Math.abs(relativeSpeed) > .01) {
    const direction = Math.sign(relativeSpeed);
    arrow(context, sourceX - direction * 17, acousticY + 38, sourceX + direction * 17, acousticY + 38, COLORS.amber, `u ${formatNumber(relativeSpeed, 0)}`);
  } else {
    fittedText(context, 'u = 0', sourceX, acousticY + 42, { size: 8, weight: 900, color: COLORS.muted, align: 'center', maximumWidth: 48 });
  }

  const travelWidth = Math.max(20, observerX - sourceX - 13);
  const baseSpacing = clamp(right.w * .115, 10, 19);
  const frontSpacing = baseSpacing * clamp((soundSpeed - relativeSpeed) / soundSpeed, .65, 1.35);
  const advance = (phase * frontSpacing * 6) % frontSpacing;
  context.save();
  roundedPath(context, sourceX + 8, acousticY - 31, travelWidth, 62, 8);
  context.clip();
  for (let x = sourceX + 13 + advance; x < observerX; x += frontSpacing) {
    context.strokeStyle = 'rgba(11,99,199,.58)';
    context.lineWidth = 1.5;
    context.beginPath();
    context.arc(x, acousticY, 12, -Math.PI / 2, Math.PI / 2);
    context.stroke();
  }
  context.restore();
  line(context, [[sourceX + 9, acousticY], [observerX - 13, acousticY]], 'rgba(11,99,199,.25)', 1, [4, 4]);
  const motionLabel = relativeSpeed > 0 ? '靠近：波面变密' : relativeSpeed < 0 ? '远离：波面变疏' : '静止：无频移';
  pill(context, motionLabel, right.x + 8, right.y + right.h * .69, right.w - 16, { height: 22, size: 8, fill: COLORS.amberSoft, color: COLORS.amber, stroke: '#ead09c' });
  fittedText(context, `fₛ ${formatNumber(sourceFrequency, 0)} Hz`, right.x + 9, right.y + right.h - 29, { size: 8, weight: 850, color: COLORS.muted, maximumWidth: right.w * .47 });
  fittedText(context, `fᵣ ${formatNumber(receivedFrequency, 1)} Hz`, right.x + right.w - 9, right.y + right.h - 29, { size: 8, weight: 950, color: COLORS.blueDark, align: 'right', maximumWidth: right.w * .49 });
  fittedText(context, `Δf ${formatNumber(receivedFrequency - sourceFrequency, 1)} Hz`, right.x + right.w / 2, right.y + right.h - 10, { size: 8, weight: 900, color: COLORS.amber, align: 'center', maximumWidth: right.w - 16 });

  statusStrip(context, width, height, [
    { label: `fₑ/f₀ ${formatNumber(ratio, 2)}` },
    { label: `响应 ${formatNumber(response, 2)}` },
    { label: `频移 ${formatNumber(receivedFrequency - sourceFrequency, 1)} Hz`, color: COLORS.amber }
  ]);
}

function drawSonarTarget(context, x, y, width, direction) {
  context.save();
  context.translate(x, y);
  if (direction < 0) context.scale(-1, 1);
  const gradient = context.createLinearGradient(-width / 2, 0, width / 2, 0);
  gradient.addColorStop(0, '#284d6b');
  gradient.addColorStop(.55, '#4f7a99');
  gradient.addColorStop(1, '#183b58');
  context.fillStyle = gradient;
  context.strokeStyle = '#fff';
  context.lineWidth = 1;
  context.beginPath();
  context.ellipse(0, 0, width / 2, width * .18, 0, 0, TAU);
  context.fill();
  context.stroke();
  context.beginPath();
  context.moveTo(-width * .43, 0);
  context.lineTo(-width * .64, -width * .22);
  context.lineTo(-width * .62, width * .22);
  context.closePath();
  context.fill();
  context.stroke();
  context.fillStyle = COLORS.amberBright;
  context.beginPath();
  context.arc(width * .25, -width * .03, 2.4, 0, TAU);
  context.fill();
  context.restore();
}

function drawSonarPulse(context, x, y, direction, color, intensity = 1) {
  context.save();
  context.strokeStyle = color;
  context.lineWidth = 2.2;
  context.globalAlpha = clamp(intensity, .2, 1);
  for (let index = 0; index < 3; index += 1) {
    const radius = 7 + index * 7;
    context.beginPath();
    context.arc(x, y, radius, direction > 0 ? -Math.PI / 2 : Math.PI / 2, direction > 0 ? Math.PI / 2 : Math.PI * 1.5, direction < 0);
    context.stroke();
  }
  context.restore();
}

function drawEchoSounder(context, width, height, spec, result, input, phase) {
  const top = sceneHeader(context, width, spec, '声脉冲走完往返，才把时间换成距离', phase);
  const margin = clamp(width * .035, 10, 24);
  const bottom = height - 46;
  const panel = { x: margin, y: top + 4, w: width - margin * 2, h: Math.max(150, bottom - top - 2) };
  box(context, panel.x, panel.y, panel.w, panel.h, { radius: 13, fill: COLORS.water, stroke: '#9fc3df' });
  const surfaceY = panel.y + 27;
  const acousticY = panel.y + panel.h * .53;
  const sensorX = panel.x + Math.max(29, panel.w * .08);
  const baseTargetX = panel.x + panel.w * .82;
  const distance = positive(input.distance, 50);
  const soundSpeed = positive(input.soundSpeed, 1500);
  const frequency = positive(input.frequency, 1500000);
  const targetSpeed = finite(input.targetSpeed, 0);
  const echoTime = positive(result.echoTime, 2 * distance / soundSpeed);
  const wavelength = positive(result.wavelength, soundSpeed / frequency);
  const echoFrequency = positive(result.echoFrequency, frequency);
  const reflectionDistance = positive(result.reflectionDistance, soundSpeed * distance / (soundSpeed + targetSpeed));
  const scaleX = (baseTargetX - sensorX) / distance;
  const currentTargetDistance = echoTargetDistanceAtPhase(distance, targetSpeed, echoTime, phase);
  const targetX = clamp(sensorX + currentTargetDistance * scaleX, sensorX + panel.w * .46, panel.x + panel.w - 35);
  const reflectionX = clamp(sensorX + reflectionDistance * scaleX, sensorX + 24, panel.x + panel.w - 35);

  context.save();
  context.strokeStyle = 'rgba(255,255,255,.76)';
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(panel.x + 8, surfaceY);
  for (let x = panel.x + 8; x <= panel.x + panel.w - 8; x += 8) {
    context.lineTo(x, surfaceY + Math.sin((x - panel.x) / 13 + phase * TAU) * 2.2);
  }
  context.stroke();
  context.restore();
  fittedText(context, '水面', panel.x + 10, surfaceY - 7, { size: 8, weight: 850, color: COLORS.blueDark, maximumWidth: 40 });

  box(context, sensorX - 19, acousticY - 32, 38, 64, { radius: 8, fill: '#174d77', stroke: '#fff', lineWidth: 1.2 });
  context.fillStyle = '#92d4ff';
  context.beginPath();
  context.arc(sensorX + 17, acousticY, 7, -Math.PI / 2, Math.PI / 2);
  context.fill();
  fittedText(context, '探头', sensorX, acousticY + 49, { size: 9, weight: 950, color: COLORS.blueDark, align: 'center', maximumWidth: 50 });

  drawSonarTarget(context, targetX, acousticY, Math.min(68, panel.w * .16), targetSpeed >= 0 ? -1 : 1);
  fittedText(context, '水下目标', targetX, acousticY + 48, { size: 9, weight: 950, color: COLORS.ink, align: 'center', maximumWidth: 80 });
  if (Math.abs(targetSpeed) > .01) {
    const direction = targetSpeed > 0 ? -1 : 1;
    arrow(context, targetX - direction * 22, acousticY - 36, targetX + direction * 22, acousticY - 36, COLORS.amber, `u ${formatNumber(targetSpeed, 1)}`);
  } else {
    pill(context, '目标静止', targetX - 38, acousticY - 48, 76, { height: 21, size: 8, fill: COLORS.amberSoft, color: COLORS.amber, stroke: '#ead09c' });
  }

  line(context, [[sensorX + 24, acousticY], [targetX - 25, acousticY]], 'rgba(16,32,51,.25)', 1.2, [6, 5]);
  let pulseX = sensorX + 20;
  let pulseDirection = 1;
  let pulseColor = COLORS.blue;
  let pulseLabel = '发射';
  if (phase < .08) {
    pulseX = sensorX + 20;
    pulseLabel = '发射声脉冲';
  } else if (phase < .5) {
    const amount = (phase - .08) / .42;
    pulseX = lerp(sensorX + 22, reflectionX - 20, amount);
    pulseLabel = '向目标传播';
  } else if (phase < .58) {
    pulseX = reflectionX - 19;
    pulseDirection = -1;
    pulseColor = COLORS.amber;
    pulseLabel = '到达并反射';
    context.fillStyle = 'rgba(240,161,27,.18)';
    context.beginPath();
    context.arc(reflectionX, acousticY, 31 + Math.sin((phase - .5) / .08 * Math.PI) * 8, 0, TAU);
    context.fill();
  } else {
    const amount = (phase - .58) / .42;
    pulseX = lerp(reflectionX - 20, sensorX + 22, amount);
    pulseDirection = -1;
    pulseColor = COLORS.amber;
    pulseLabel = amount > .88 ? '接收回波' : '回波返回';
  }
  drawSonarPulse(context, pulseX, acousticY, pulseDirection, pulseColor, .95);
  pill(context, pulseLabel, panel.x + 10, panel.y + 8, Math.min(112, panel.w * .32), { height: 21, size: 8, fill: pulseColor === COLORS.amber ? COLORS.amberSoft : COLORS.blueSoft, color: pulseColor === COLORS.amber ? COLORS.amber : COLORS.blueDark, stroke: pulseColor === COLORS.amber ? '#ead09c' : '#a8cbea' });

  const distanceY = panel.y + panel.h - 24;
  doubleArrow(context, sensorX, distanceY, targetX, distanceY, COLORS.muted, `d(t) ${formatNumber(currentTargetDistance, 1)} m`);
  if (panel.w > 390) fittedText(context, `反射点 ${formatNumber(reflectionDistance, 1)} m`, panel.x + panel.w - 10, panel.y + 19, { size: 8, weight: 850, color: COLORS.muted, align: 'right', maximumWidth: 160 });
  const echoActive = phase > .9;
  context.fillStyle = echoActive ? COLORS.amberBright : '#aab8c5';
  context.beginPath();
  context.arc(sensorX - 4, acousticY - 22, 4, 0, TAU);
  context.fill();

  statusStrip(context, width, height, [
    { label: `λ ${formatNumber(wavelength, 4)} m` },
    { label: `往返 ${formatNumber(echoTime, 3)} s` },
    { label: `f回 ${formatNumber(echoFrequency, 0)} Hz`, color: COLORS.amber }
  ]);
}

/**
 * 绘制“振动与波”专题的五个专用 Canvas 场景。
 * 调用前由统一底座完成响应式画布与淡蓝网格背景。
 *
 * @returns {boolean} 命中专用场景时返回 true，否则返回 false。
 */
export function drawWaveScene(context, width, height, spec, result, input, phase) {
  const scene = spec?.scene;
  if (!SCENES.has(scene) || !context) return false;
  const safeWidth = Math.max(1, finite(width, 1));
  const safeHeight = Math.max(1, finite(height, 1));
  const safeResult = result && typeof result === 'object' ? result : {};
  const safeInput = input && typeof input === 'object' ? input : {};
  const safePhase = clamp(finite(phase));
  context.save();
  context.lineCap = 'round';
  context.lineJoin = 'round';
  context.setLineDash([]);
  if (scene === 'ropeWave') drawRopeWave(context, safeWidth, safeHeight, spec, safeResult, safeInput, safePhase);
  else if (scene === 'travelingWave') drawTravelingWave(context, safeWidth, safeHeight, spec, safeResult, safeInput, safePhase);
  else if (scene === 'springOscillator') drawSpringOscillator(context, safeWidth, safeHeight, spec, safeResult, safeInput, safePhase);
  else if (scene === 'forcedDoppler') drawForcedDoppler(context, safeWidth, safeHeight, spec, safeResult, safeInput, safePhase);
  else drawEchoSounder(context, safeWidth, safeHeight, spec, safeResult, safeInput, safePhase);
  context.restore();
  return true;
}

export function runWaveSceneSemanticTests() {
  const tests = [];
  const record = (name, check) => {
    try { tests.push({ name, pass: Boolean(check()) }); }
    catch (error) { tests.push({ name, pass: false, detail: error instanceof Error ? error.message : String(error) }); }
  };
  record('软绳动画phase=.5对应半周期', () => Math.abs(phaseTime(0, 2, .5) - 1) < 1e-12);
  record('行波与弹簧动画从题设t₀继续推进', () => Math.abs(phaseTime(1, 2, .5) - 2) < 1e-12);
  record('移动目标在反射相位与声脉冲相遇', () => {
    const distance = 50; const speed = 5; const soundSpeed = 1500;
    const reflectionTime = distance / (soundSpeed + speed);
    const echoTime = 2 * reflectionTime;
    const reflectionDistance = soundSpeed * reflectionTime;
    return Math.abs(echoTargetDistanceAtPhase(distance, speed, echoTime, .5) - reflectionDistance) < 1e-12;
  });
  return tests;
}
