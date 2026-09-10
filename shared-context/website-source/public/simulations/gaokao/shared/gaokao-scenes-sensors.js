const COLORS = Object.freeze({
  ink: '#102033',
  muted: '#566a7f',
  line: '#c8d7e4',
  blue: '#0b63c7',
  blueDark: '#064b98',
  blueSoft: '#dbeafe',
  amber: '#c46d08',
  amberSoft: '#fff0cf',
  green: '#14734b',
  greenSoft: '#e7f6ee',
  red: '#b42318',
  paper: 'rgba(255,255,255,.92)'
});

const FONT_STACK = '"Avenir Next", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif';
const clamp = (value, minimum = 0, maximum = 1) => Math.min(maximum, Math.max(minimum, value));
const lerp = (start, end, amount) => start + (end - start) * amount;
const smooth = (value) => {
  const t = clamp(value);
  return t * t * (3 - 2 * t);
};
const finite = (value, fallback = 0) => Number.isFinite(Number(value)) ? Number(value) : fallback;

function ionTravelFraction(charge, travel) {
  return charge > 0 ? 1 - travel : travel;
}

function ropeCircuitState(phase, input) {
  const closed = phase >= .42;
  const baseCurrent = finite(input.current1);
  const totalCurrent = closed ? finite(input.current2) : baseCurrent;
  return { closed, baseCurrent, branchCurrent: closed ? Math.max(0, finite(input.current2) - baseCurrent) : 0, totalCurrent };
}

function trackerErrorAtProgress(initialError, finalError, progress) {
  return lerp(initialError, finalError, smooth(progress));
}

function formatNumber(value, digits = 1) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  if (Math.abs(number) >= 10000 || (Math.abs(number) > 0 && Math.abs(number) < .001)) {
    return number.toExponential(Math.min(digits, 2));
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

function fittedText(context, value, x, y, options = {}) {
  const original = String(value ?? '');
  const weight = options.weight || 700;
  let size = options.size || 12;
  const minimum = options.minimumSize || 8;
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
  if (context.measureText(output).width > maximumWidth && Number.isFinite(maximumWidth)) {
    const characters = Array.from(original);
    while (characters.length > 1 && context.measureText(`${characters.join('')}…`).width > maximumWidth) characters.pop();
    output = `${characters.join('')}…`;
  }
  context.fillText(output, x, y);
  context.restore();
}

function line(context, points, color = COLORS.blue, width = 2, dash = []) {
  if (!points.length) return;
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

function arrow(context, x1, y1, x2, y2, color = COLORS.amber, label = '') {
  const angle = Math.atan2(y2 - y1, x2 - x1);
  const head = 7;
  context.save();
  context.strokeStyle = color;
  context.fillStyle = color;
  context.lineWidth = 2.5;
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
  if (label) fittedText(context, label, (x1 + x2) / 2, (y1 + y2) / 2 - 6, { size: 10, weight: 900, color, align: 'center', maximumWidth: Math.abs(x2 - x1) + 36 });
  context.restore();
}

function doubleArrow(context, x1, y1, x2, y2, color = COLORS.muted) {
  arrow(context, x1, y1, x2, y2, color);
  arrow(context, x2, y2, x1, y1, color);
}

function pill(context, label, x, y, width, options = {}) {
  const height = options.height || 23;
  box(context, x, y, width, height, {
    radius: height / 2,
    fill: options.fill || COLORS.blueSoft,
    stroke: options.stroke || 'rgba(11,99,199,.18)'
  });
  fittedText(context, label, x + width / 2, y + height / 2 + .5, {
    size: options.size || 10,
    minimumSize: 8,
    weight: 900,
    color: options.color || COLORS.blueDark,
    align: 'center',
    baseline: 'middle',
    maximumWidth: width - 12
  });
}

function sceneHeader(context, width, spec, title, phase) {
  const margin = clamp(width * .035, 10, 24);
  const stages = Array.isArray(spec?.phases) && spec.phases.length ? spec.phases : ['传感测量'];
  const stageIndex = Math.min(stages.length - 1, Math.floor(clamp(phase) * stages.length));
  const stage = stages[stageIndex];
  if (width < 455) {
    fittedText(context, title, margin, 21, { size: 14, weight: 950, maximumWidth: width - margin * 2 });
    pill(context, stage, margin, 31, width - margin * 2, { height: 22, size: 9 });
    return 63;
  }
  fittedText(context, title, margin, 29, { size: 16, weight: 950, maximumWidth: width * .47 });
  const chipWidth = clamp(width * .29, 142, 205);
  pill(context, stage, width - margin - chipWidth, 14, chipWidth, { height: 25 });
  return 52;
}

function statusStrip(context, width, height, items) {
  const margin = clamp(width * .035, 10, 24);
  const gap = width < 420 ? 4 : 7;
  const y = height - 39;
  const available = width - margin * 2 - gap * (items.length - 1);
  const itemWidth = available / items.length;
  items.forEach((item, index) => {
    const active = item.active !== false;
    pill(context, item.label, margin + index * (itemWidth + gap), y, itemWidth, {
      height: 25,
      size: width < 420 ? 8 : 9,
      fill: item.fill || (active ? COLORS.paper : 'rgba(255,255,255,.5)'),
      stroke: item.stroke || COLORS.line,
      color: item.color || (active ? COLORS.ink : COLORS.muted)
    });
    if (index < items.length - 1 && width >= 500) {
      const edge = margin + (index + 1) * itemWidth + index * gap;
      arrow(context, edge + 1, y + 12.5, edge + gap - 1, y + 12.5, COLORS.amber);
    }
  });
}

function drawThermometer(context, x, y, height, ratio, label) {
  const bulbRadius = 8;
  context.save();
  context.strokeStyle = '#7f94a8';
  context.lineWidth = 3;
  context.beginPath();
  context.moveTo(x, y + 5);
  context.lineTo(x, y + height - bulbRadius * 1.4);
  context.stroke();
  context.fillStyle = '#eef5fb';
  context.beginPath();
  context.arc(x, y + height - bulbRadius, bulbRadius, 0, Math.PI * 2);
  context.fill();
  context.stroke();
  const columnTop = lerp(y + height - bulbRadius * 1.7, y + 10, clamp(ratio));
  const gradient = context.createLinearGradient(0, y + height, 0, y);
  gradient.addColorStop(0, '#d95d39');
  gradient.addColorStop(1, '#f0a11b');
  context.strokeStyle = gradient;
  context.fillStyle = '#d95d39';
  context.lineWidth = 4;
  context.beginPath();
  context.moveTo(x, y + height - bulbRadius * 1.1);
  context.lineTo(x, columnTop);
  context.stroke();
  context.beginPath();
  context.arc(x, y + height - bulbRadius, bulbRadius - 2, 0, Math.PI * 2);
  context.fill();
  context.restore();
  fittedText(context, label, x, y + height + 15, { size: 9, weight: 850, align: 'center', color: COLORS.muted, maximumWidth: 76 });
}

function drawAnalogMeter(context, x, y, width, height, deflection, valueLabel) {
  box(context, x, y, width, height, { radius: 12, fill: COLORS.paper, stroke: '#aebfd0' });
  fittedText(context, '欧姆表', x + 12, y + 21, { size: 11, weight: 950, maximumWidth: width - 24 });
  const centerX = x + width / 2;
  const centerY = y + height * .63;
  const radius = Math.min(width * .34, height * .38);
  context.save();
  context.strokeStyle = '#8da2b5';
  context.lineWidth = 2;
  context.beginPath();
  context.arc(centerX, centerY, radius, Math.PI * 1.12, Math.PI * 1.88);
  context.stroke();
  for (let index = 0; index <= 6; index += 1) {
    const angle = lerp(Math.PI * 1.12, Math.PI * 1.88, index / 6);
    line(context, [
      [centerX + Math.cos(angle) * (radius - 5), centerY + Math.sin(angle) * (radius - 5)],
      [centerX + Math.cos(angle) * radius, centerY + Math.sin(angle) * radius]
    ], '#6d8295', 1.5);
  }
  const pointerAngle = lerp(Math.PI * 1.12, Math.PI * 1.88, clamp(deflection));
  line(context, [[centerX, centerY], [centerX + Math.cos(pointerAngle) * (radius - 8), centerY + Math.sin(pointerAngle) * (radius - 8)]], COLORS.amber, 3);
  context.fillStyle = COLORS.ink;
  context.beginPath();
  context.arc(centerX, centerY, 4, 0, Math.PI * 2);
  context.fill();
  context.restore();
  fittedText(context, valueLabel, centerX, y + height - 10, { size: 10, weight: 900, align: 'center', color: COLORS.blueDark, maximumWidth: width - 14 });
}

function drawThermistor(context, width, height, spec, result, input, phase) {
  const top = sceneHeader(context, width, spec, '热敏电阻：把温度变成表针偏转', phase);
  const margin = clamp(width * .035, 10, 24);
  const usableWidth = width - margin * 2;
  const sceneBottom = height - 51;
  const sceneHeight = Math.max(150, sceneBottom - top);
  const bathWidth = usableWidth * (width < 500 ? .49 : .46);
  const meterWidth = usableWidth - bathWidth - clamp(usableWidth * .06, 10, 26);
  const meterX = margin + usableWidth - meterWidth;
  const targetTemperature = finite(input.temperature, 25);
  const returnStart = .79;
  const thermalProgress = phase <= returnStart
    ? smooth(phase / returnStart)
    : 1 - smooth((phase - returnStart) / (1 - returnStart));
  const currentTemperature = lerp(25, targetTemperature, thermalProgress);
  const resistance25 = finite(result.resistance25, finite(input.comparisonR1) - finite(input.comparisonR2));
  const beta = finite(input.beta, 3950);
  const kelvin = currentTemperature + 273.15;
  const currentResistance = resistance25 > 0 && kelvin > 0
    ? resistance25 * Math.exp(beta * (1 / kelvin - 1 / 298.15))
    : finite(result.resistance);
  const temperatureRatio = clamp((currentTemperature - 0) / 90);
  const bathX = margin + bathWidth * .07;
  const bathY = top + sceneHeight * .18;
  const bathH = sceneHeight * .58;
  const bathW = bathWidth * .72;

  context.save();
  context.strokeStyle = '#617a91';
  context.lineWidth = 3;
  context.beginPath();
  context.moveTo(bathX, bathY);
  context.lineTo(bathX + 5, bathY + bathH);
  context.quadraticCurveTo(bathX + bathW / 2, bathY + bathH + 9, bathX + bathW - 5, bathY + bathH);
  context.lineTo(bathX + bathW, bathY);
  context.stroke();
  const waterGradient = context.createLinearGradient(0, bathY, 0, bathY + bathH);
  waterGradient.addColorStop(0, `rgba(240,161,27,${.08 + temperatureRatio * .18})`);
  waterGradient.addColorStop(1, `rgba(11,99,199,${.2 - temperatureRatio * .08})`);
  context.fillStyle = waterGradient;
  context.beginPath();
  context.moveTo(bathX + 2, bathY + bathH * .27);
  context.lineTo(bathX + bathW - 2, bathY + bathH * .27);
  context.lineTo(bathX + bathW - 5, bathY + bathH - 2);
  context.quadraticCurveTo(bathX + bathW / 2, bathY + bathH + 5, bathX + 5, bathY + bathH - 2);
  context.closePath();
  context.fill();
  context.strokeStyle = 'rgba(11,99,199,.42)';
  context.lineWidth = 1.5;
  context.beginPath();
  context.ellipse(bathX + bathW / 2, bathY + bathH * .27, bathW / 2 - 2, 4, 0, 0, Math.PI * 2);
  context.stroke();
  context.restore();

  const probeX = bathX + bathW * .58;
  line(context, [[probeX, bathY - 16], [probeX, bathY + bathH * .73]], COLORS.ink, 4);
  box(context, probeX - 8, bathY + bathH * .58, 16, 34, { radius: 7, fill: COLORS.blueDark, stroke: '#fff', lineWidth: 2 });
  fittedText(context, 'NTC', probeX, bathY + bathH * .58 + 21, { size: 8, weight: 950, color: '#fff', align: 'center', maximumWidth: 13 });
  drawThermometer(context, bathX + bathW + 13, bathY + 5, bathH * .78, temperatureRatio, `${formatNumber(currentTemperature, 1)} ℃`);

  const adjusting = Math.abs(targetTemperature - 25) > .2 && phase > .08 && phase < .8;
  if (adjusting) {
    const heatColor = targetTemperature >= 25 ? COLORS.amber : COLORS.blue;
    for (let index = 0; index < 3; index += 1) {
      const waveX = bathX + bathW * (.22 + index * .22);
      const offset = Math.sin(phase * Math.PI * 8 + index) * 3;
      line(context, [[waveX, bathY + bathH + 12], [waveX - 3, bathY + bathH + 4 + offset], [waveX + 3, bathY + bathH - 4 + offset]], heatColor, 1.6);
    }
    fittedText(context, targetTemperature >= 25 ? '恒温水浴加热' : '恒温水浴冷却', bathX + bathW / 2, bathY + bathH + 27, {
      size: 9, weight: 900, color: heatColor, align: 'center', maximumWidth: bathW + 28
    });
  }

  const cableY = Math.max(top + 12, bathY - 15);
  line(context, [[probeX, bathY - 16], [probeX, cableY], [meterX + 11, cableY], [meterX + 11, top + sceneHeight * .29]], COLORS.blueDark, 2.2);
  const deflection = clamp(.5 + Math.log(Math.max(.0001, resistance25 / Math.max(.0001, currentResistance))) / 4);
  const meterY = top + sceneHeight * .12;
  const meterH = Math.min(sceneHeight * .67, sceneBottom - meterY - 16);
  drawAnalogMeter(context, meterX, meterY, meterWidth, meterH, deflection, `R = ${formatNumber(currentResistance, 2)} kΩ`);
  fittedText(context, currentTemperature >= 25 ? '升温：阻值减小，指针右偏' : '降温：阻值增大，指针左偏', meterX + meterWidth / 2, Math.min(sceneBottom - 2, meterY + meterH + 18), {
    size: width < 430 ? 8 : 10,
    weight: 900,
    color: currentTemperature >= 25 ? COLORS.amber : COLORS.blue,
    align: 'center',
    maximumWidth: meterWidth + 8
  });

  statusStrip(context, width, height, [
    { label: `水浴 ${formatNumber(currentTemperature, 1)} ℃` },
    { label: `NTC ${formatNumber(currentResistance, 2)} kΩ` },
    { label: '欧姆表读数' }
  ]);
}

function drawClamp(context, x, y, moving = false) {
  box(context, x - 8, y - 25, 16, 50, { radius: 4, fill: moving ? COLORS.amber : '#49657f', stroke: '#fff', lineWidth: 1.5 });
  line(context, [[x - 13, y - 31], [x + 13, y - 31]], '#526579', 4);
  line(context, [[x - 13, y + 31], [x + 13, y + 31]], '#526579', 4);
}

function drawBraidedRope(context, x1, x2, y, phase, color) {
  const span = Math.max(12, x2 - x1);
  context.save();
  context.lineCap = 'round';
  for (let strand = 0; strand < 3; strand += 1) {
    context.strokeStyle = strand === 1 ? color : (strand === 0 ? '#65a7de' : '#214d72');
    context.lineWidth = strand === 1 ? 4 : 2;
    context.beginPath();
    const steps = Math.max(12, Math.floor(span / 6));
    for (let index = 0; index <= steps; index += 1) {
      const t = index / steps;
      const x = lerp(x1, x2, t);
      const offset = Math.sin(t * Math.PI * 10 + strand * Math.PI * 2 / 3 + phase * Math.PI * 2) * 3.5;
      if (index === 0) context.moveTo(x, y + offset);
      else context.lineTo(x, y + offset);
    }
    context.stroke();
  }
  context.restore();
}

function drawSimpleCircuit(context, x, y, width, height, input, _result, phase) {
  box(context, x, y, width, height, { radius: 11, fill: COLORS.paper, stroke: COLORS.line });
  const circuit = ropeCircuitState(phase, input);
  const left = x + 15;
  const right = x + width - 13;
  const topY = y + Math.max(29, height * .28);
  const returnY = y + height - 12;
  const branchOneY = y + height * .52;
  const branchTwoY = y + height * .74;
  const sourceX = left + 6;
  const meterX = x + width * .37;
  const splitX = x + width * .54;
  const joinX = right;
  line(context, [[sourceX, topY], [meterX - 15, topY]], COLORS.ink, 2);
  line(context, [[sourceX, topY], [sourceX, topY + 8]], COLORS.ink, 2);
  line(context, [[sourceX - 8, topY + 8], [sourceX + 8, topY + 8]], COLORS.ink, 2.5);
  line(context, [[sourceX - 5, topY + 14], [sourceX + 5, topY + 14]], COLORS.ink, 1.5);
  line(context, [[sourceX, topY + 14], [sourceX, returnY], [joinX, returnY], [joinX, branchOneY]], COLORS.ink, 2);
  fittedText(context, `U ${formatNumber(input.voltage, 2)} V`, left, y + 16, { size: 8, weight: 900, color: COLORS.blueDark, maximumWidth: width * .31 });
  context.fillStyle = '#fff';
  context.strokeStyle = COLORS.blueDark;
  context.lineWidth = 2;
  context.beginPath();
  context.arc(meterX, topY, 15, 0, Math.PI * 2);
  context.fill();
  context.stroke();
  fittedText(context, 'A', meterX, topY + .5, { size: 11, weight: 950, color: COLORS.blueDark, align: 'center', baseline: 'middle', maximumWidth: 16 });
  line(context, [[meterX + 15, topY], [splitX, topY], [splitX, branchTwoY]], COLORS.ink, 2);
  line(context, [[splitX, branchOneY], [splitX + 10, branchOneY]], COLORS.ink, 2);
  drawResistor(context, splitX + 10, joinX - 5, branchOneY, COLORS.blueDark);
  fittedText(context, `基准支路 I₁=${formatNumber(circuit.baseCurrent, 2)} mA`, (splitX + joinX) / 2, branchOneY - 8, { size: 7, weight: 850, color: COLORS.blueDark, align: 'center', maximumWidth: joinX - splitX - 5 });
  const switchX = splitX + 20;
  context.fillStyle = COLORS.ink;
  context.beginPath(); context.arc(switchX - 8, branchTwoY, 3, 0, Math.PI * 2); context.fill();
  context.beginPath(); context.arc(switchX + 10, branchTwoY, 3, 0, Math.PI * 2); context.fill();
  line(context, [[splitX, branchTwoY], [switchX - 8, branchTwoY]], COLORS.ink, 2);
  line(context, [[switchX - 8, branchTwoY], [switchX + 8, branchTwoY - (circuit.closed ? 0 : 10)]], circuit.closed ? COLORS.amber : COLORS.muted, 2.5);
  drawBraidedRope(context, switchX + 10, joinX - 4, branchTwoY, 0, circuit.closed ? COLORS.amber : '#9aa9b5');
  fittedText(context, circuit.closed ? `绳支路 I₂−I₁=${formatNumber(circuit.branchCurrent, 2)} mA` : 'S₂断开：绳支路无电流', (switchX + joinX) / 2, branchTwoY - 8, { size: 7, weight: 900, color: circuit.closed ? COLORS.amber : COLORS.muted, align: 'center', maximumWidth: joinX - switchX - 2 });
  fittedText(context, circuit.closed ? 'S₂ 闭合' : 'S₂ 断开', right, y + 16, { size: 8, weight: 900, align: 'right', color: circuit.closed ? COLORS.amber : COLORS.muted, maximumWidth: width * .28 });
  fittedText(context, `总电流 ${circuit.closed ? 'I₂' : 'I₁'}=${formatNumber(circuit.totalCurrent, 2)} mA`, meterX, y + height - 2, { size: 8, weight: 900, align: 'center', color: COLORS.ink, maximumWidth: width * .48 });
  return circuit.totalCurrent;
}

function drawRopeSensor(context, width, height, spec, result, input, phase) {
  const top = sceneHeader(context, width, spec, '弹性导电绳：长度写进电阻，也写进路径', phase);
  const margin = clamp(width * .035, 10, 24);
  const sceneBottom = height - 51;
  const availableHeight = Math.max(170, sceneBottom - top);
  const anchorLength = finite(input.anchorLength, 51.8);
  const loadingLength = finite(result.loadingLength, anchorLength);
  const unloadingLength = finite(result.unloadingLength, loadingLength);
  const startLength = 51;
  let currentLength;
  let unloading = false;
  if (phase < .25) currentLength = lerp(startLength, 51.4, smooth(phase / .25));
  else if (phase < .5) currentLength = lerp(51.4, anchorLength, smooth((phase - .25) / .25));
  else if (phase < .75) currentLength = lerp(anchorLength, loadingLength, smooth((phase - .5) / .25));
  else {
    unloading = true;
    currentLength = lerp(loadingLength, unloadingLength, smooth((phase - .75) / .25));
  }

  const ropeY = top + availableHeight * .24;
  const leftClampX = margin + 20;
  const minimumSpan = Math.max(92, (width - margin * 2) * .42);
  const maximumSpan = width - margin * 2 - 42;
  const normalizedLength = clamp(currentLength - 51);
  const rightClampX = leftClampX + lerp(minimumSpan, maximumSpan, normalizedLength);
  line(context, [[margin, ropeY + 39], [width - margin, ropeY + 39]], '#9fb1c1', 3);
  drawClamp(context, leftClampX, ropeY, false);
  drawClamp(context, rightClampX, ropeY, true);
  drawBraidedRope(context, leftClampX + 8, rightClampX - 8, ropeY, phase, unloading ? COLORS.amber : COLORS.blue);
  const forceDirection = unloading ? -1 : 1;
  arrow(context, rightClampX + 8, ropeY - 43, rightClampX + 8 + forceDirection * Math.min(45, width * .1), ropeY - 43, unloading ? COLORS.amber : COLORS.blue, unloading ? '卸载' : '加载');
  doubleArrow(context, leftClampX + 4, ropeY + 48, rightClampX - 4, ropeY + 48, COLORS.muted);
  fittedText(context, `L = ${formatNumber(currentLength, 2)} cm`, (leftClampX + rightClampX) / 2, ropeY + 65, {
    size: 10, weight: 950, color: unloading ? COLORS.amber : COLORS.blueDark, align: 'center', maximumWidth: Math.max(70, rightClampX - leftClampX)
  });

  const lowerY = top + availableHeight * .52;
  const lowerH = Math.max(76, sceneBottom - lowerY - 5);
  const circuitWidth = width < 460 ? (width - margin * 2) * .56 : (width - margin * 2) * .58;
  drawSimpleCircuit(context, margin, lowerY, circuitWidth, lowerH, input, result, phase);
  const readoutX = margin + circuitWidth + 7;
  const readoutW = width - margin - readoutX;
  box(context, readoutX, lowerY, readoutW, lowerH, { radius: 11, fill: unloading ? '#fff9ed' : '#f4f9ff', stroke: unloading ? '#e7c58c' : '#a8cbea' });
  fittedText(context, `R = ${formatNumber(result.measuredResistance, 2)} kΩ`, readoutX + 10, lowerY + 20, { size: 10, weight: 950, color: COLORS.ink, maximumWidth: readoutW - 20 });
  fittedText(context, `加载 ${formatNumber(loadingLength, 2)} cm`, readoutX + 10, lowerY + 41, { size: 9, weight: unloading ? 700 : 950, color: COLORS.blueDark, maximumWidth: readoutW - 20 });
  fittedText(context, `卸载 ${formatNumber(unloadingLength, 2)} cm`, readoutX + 10, lowerY + 60, { size: 9, weight: unloading ? 950 : 700, color: COLORS.amber, maximumWidth: readoutW - 20 });
  if (lowerH > 88) fittedText(context, `路径差 ${formatNumber(result.lengthDifference, 2)} cm`, readoutX + 10, lowerY + lowerH - 12, { size: 8, weight: 850, color: COLORS.muted, maximumWidth: readoutW - 20 });

  statusStrip(context, width, height, [
    { label: unloading ? '卸载回程' : '缓慢加载', color: unloading ? COLORS.amber : COLORS.blueDark },
    { label: `测得 ${formatNumber(result.measuredResistance, 2)} kΩ` },
    { label: 'R—L 标定' }
  ]);
}

function drawResistor(context, x1, x2, y, color = COLORS.ink) {
  const lead = Math.min(10, (x2 - x1) * .16);
  const start = x1 + lead;
  const end = x2 - lead;
  const steps = 6;
  const points = [[x1, y], [start, y]];
  for (let index = 0; index <= steps; index += 1) {
    points.push([lerp(start, end, index / steps), y + (index % 2 === 0 ? -5 : 5)]);
  }
  points.push([x2, y]);
  line(context, points, color, 2);
}

function drawSalineCircuit(context, x, y, width, height, input, result, switchClosed) {
  const centerY = y + height * .39;
  const branchOffset = Math.min(15, height * .15);
  const returnY = y + height - 8;
  const leftStart = x + 4;
  const leftEnd = x + width * .29;
  const sampleStart = x + width * .35;
  const sampleEnd = x + width * .56;
  const rightStart = x + width * .62;
  const rightEnd = x + width - 4;
  const activeColor = switchClosed ? COLORS.amber : COLORS.blueDark;

  // 左侧网络：S₂断开时只有 R₂，闭合时 R₁ 与 R₂ 并联。
  line(context, [[leftStart, centerY - branchOffset], [leftStart, centerY + branchOffset]], COLORS.ink, 1.8);
  line(context, [[leftEnd, centerY - branchOffset], [leftEnd, centerY + branchOffset]], COLORS.ink, 1.8);
  drawResistor(context, leftStart + 2, leftEnd - 2, centerY - branchOffset, COLORS.blueDark);
  fittedText(context, `R₂ ${formatNumber(input.resistor2, 0)}Ω`, (leftStart + leftEnd) / 2, centerY - branchOffset - 9, { size: 6.8, weight: 900, color: COLORS.blueDark, align: 'center', maximumWidth: leftEnd - leftStart });
  const switchLeft = leftStart + 3;
  const switchRight = leftStart + Math.min(21, (leftEnd - leftStart) * .32);
  line(context, [[leftStart, centerY + branchOffset], [switchLeft, centerY + branchOffset]], COLORS.ink, 1.8);
  context.fillStyle = COLORS.ink;
  context.beginPath(); context.arc(switchLeft, centerY + branchOffset, 2.4, 0, Math.PI * 2); context.fill();
  context.beginPath(); context.arc(switchRight, centerY + branchOffset, 2.4, 0, Math.PI * 2); context.fill();
  line(context, [[switchLeft, centerY + branchOffset], [switchRight - 1, centerY + branchOffset - (switchClosed ? 0 : 9)]], switchClosed ? COLORS.amber : COLORS.muted, 2.2);
  drawResistor(context, switchRight, leftEnd - 2, centerY + branchOffset, switchClosed ? COLORS.amber : '#9aa9b5');
  fittedText(context, `S₂·R₁ ${formatNumber(input.resistor1, 0)}Ω`, (switchRight + leftEnd) / 2, centerY + branchOffset + 11, { size: 6.5, weight: 900, color: switchClosed ? COLORS.amber : COLORS.muted, align: 'center', maximumWidth: leftEnd - switchRight + 12 });

  line(context, [[leftEnd, centerY], [sampleStart, centerY]], COLORS.ink, 1.8);
  drawResistor(context, sampleStart, sampleEnd, centerY, activeColor);
  fittedText(context, `R液 ${formatNumber(result.resistance, 0)}Ω`, (sampleStart + sampleEnd) / 2, centerY - 11, { size: 7, weight: 950, color: activeColor, align: 'center', maximumWidth: sampleEnd - sampleStart + 12 });
  line(context, [[sampleEnd, centerY], [rightStart, centerY]], COLORS.ink, 1.8);

  // 右侧网络：电流表位于 R₃ 支路，R₄ 与其并联。
  line(context, [[rightStart, centerY - branchOffset], [rightStart, centerY + branchOffset]], COLORS.ink, 1.8);
  line(context, [[rightEnd, centerY - branchOffset], [rightEnd, centerY + branchOffset]], COLORS.ink, 1.8);
  const meterX = rightStart + Math.min(12, (rightEnd - rightStart) * .22);
  line(context, [[rightStart, centerY - branchOffset], [meterX - 6, centerY - branchOffset]], COLORS.ink, 1.8);
  context.fillStyle = '#fff'; context.strokeStyle = activeColor; context.lineWidth = 1.8;
  context.beginPath(); context.arc(meterX, centerY - branchOffset, 6, 0, Math.PI * 2); context.fill(); context.stroke();
  fittedText(context, 'A', meterX, centerY - branchOffset + .5, { size: 6.5, weight: 950, color: activeColor, align: 'center', baseline: 'middle', maximumWidth: 9 });
  drawResistor(context, meterX + 6, rightEnd - 2, centerY - branchOffset, COLORS.blueDark);
  fittedText(context, `R₃ ${formatNumber(input.resistor3, 0)}Ω`, (meterX + 6 + rightEnd) / 2, centerY - branchOffset - 9, { size: 6.5, weight: 900, color: COLORS.blueDark, align: 'center', maximumWidth: rightEnd - meterX });
  drawResistor(context, rightStart + 2, rightEnd - 2, centerY + branchOffset, COLORS.blueDark);
  fittedText(context, `R₄ ${formatNumber(input.resistor4, 0)}Ω`, (rightStart + rightEnd) / 2, centerY + branchOffset + 11, { size: 6.5, weight: 900, color: COLORS.blueDark, align: 'center', maximumWidth: rightEnd - rightStart });

  // 回路线和电源，强调两次测量共用同一电动势。
  line(context, [[rightEnd, centerY], [rightEnd, returnY], [x + width * .55, returnY]], COLORS.ink, 1.8);
  const batteryX = x + width * .48;
  line(context, [[batteryX - 5, returnY - 7], [batteryX - 5, returnY + 1]], COLORS.ink, 1.6);
  line(context, [[batteryX + 1, returnY - 11], [batteryX + 1, returnY + 5]], COLORS.ink, 2.2);
  line(context, [[x + width * .55, returnY], [batteryX + 1, returnY]], COLORS.ink, 1.8);
  line(context, [[batteryX - 5, returnY], [leftStart, returnY], [leftStart, centerY]], COLORS.ink, 1.8);
  fittedText(context, `E ${formatNumber(result.voltageA, 0)}V`, batteryX - 2, returnY - 13, { size: 6.5, weight: 900, color: COLORS.muted, align: 'center', maximumWidth: width * .2 });
}

function drawSaline(context, width, height, spec, result, input, phase) {
  const top = sceneHeader(context, width, spec, '盐水电导率：两次测流，再换算材料属性', phase);
  const margin = clamp(width * .035, 10, 24);
  const sceneBottom = height - 51;
  const availableHeight = Math.max(170, sceneBottom - top);
  const beakerWidth = (width - margin * 2) * (width < 500 ? .47 : .44);
  const beakerX = margin + beakerWidth * .08;
  const beakerY = top + availableHeight * .18;
  const beakerH = availableHeight * .63;
  const beakerW = beakerWidth * .78;
  let state = '核对';
  if (phase >= .16 && phase < .43) state = '断开';
  else if (phase >= .43 && phase < .68) state = '闭合';
  else if (phase >= .68) state = phase < .88 ? '分流' : '反演';
  const switchClosed = state === '闭合' || state === '分流' || state === '反演';
  const current = state === '断开' ? finite(result.currentOpen) : state === '核对' ? 0 : finite(result.currentClosed);

  context.save();
  context.strokeStyle = '#617a91';
  context.lineWidth = 3;
  context.beginPath();
  context.moveTo(beakerX, beakerY);
  context.lineTo(beakerX + 5, beakerY + beakerH);
  context.quadraticCurveTo(beakerX + beakerW / 2, beakerY + beakerH + 8, beakerX + beakerW - 5, beakerY + beakerH);
  context.lineTo(beakerX + beakerW, beakerY);
  context.stroke();
  const liquid = context.createLinearGradient(0, beakerY, 0, beakerY + beakerH);
  liquid.addColorStop(0, 'rgba(95,174,228,.20)');
  liquid.addColorStop(1, 'rgba(11,99,199,.34)');
  context.fillStyle = liquid;
  context.beginPath();
  context.moveTo(beakerX + 2, beakerY + beakerH * .23);
  context.lineTo(beakerX + beakerW - 2, beakerY + beakerH * .23);
  context.lineTo(beakerX + beakerW - 5, beakerY + beakerH - 2);
  context.quadraticCurveTo(beakerX + beakerW / 2, beakerY + beakerH + 4, beakerX + 5, beakerY + beakerH - 2);
  context.closePath();
  context.fill();
  context.restore();

  const gapRatio = clamp((finite(input.electrodeGap, .02) - .005) / .095);
  const visualGap = lerp(beakerW * .24, beakerW * .58, gapRatio);
  const centerX = beakerX + beakerW / 2;
  const electrodeLeft = centerX - visualGap / 2;
  const electrodeRight = centerX + visualGap / 2;
  const electrodeTop = beakerY + beakerH * .08;
  const electrodeBottom = beakerY + beakerH * .73;
  [electrodeLeft, electrodeRight].forEach((x, index) => {
    box(context, x - 5, electrodeTop, 10, electrodeBottom - electrodeTop, { radius: 3, fill: index === 0 ? '#334e68' : '#a66a16', stroke: '#fff', lineWidth: 1 });
    fittedText(context, index === 0 ? '−' : '+', x, electrodeTop - 7, { size: 12, weight: 950, align: 'center', maximumWidth: 15 });
  });
  doubleArrow(context, electrodeLeft + 6, electrodeBottom + 12, electrodeRight - 6, electrodeBottom + 12, COLORS.muted);
  fittedText(context, `l ${formatNumber(finite(input.electrodeGap) * 1000, 0)} mm`, centerX, electrodeBottom + 27, { size: 8, weight: 900, color: COLORS.muted, align: 'center', maximumWidth: beakerW });

  context.save();
  roundedPath(context, beakerX + 5, beakerY + beakerH * .25, beakerW - 10, beakerH * .55, 4);
  context.clip();
  const ionCount = width < 420 ? 7 : 11;
  for (let index = 0; index < ionCount; index += 1) {
    const travel = current > 0 ? (phase * (1.4 + current / 80) + index / ionCount) % 1 : index / ionCount;
    const charge = index % 2 === 0 ? 1 : -1;
    const direction = ionTravelFraction(charge, travel);
    const x = lerp(electrodeLeft + 8, electrodeRight - 8, direction);
    const y = beakerY + beakerH * (.34 + (index % 4) * .105);
    context.fillStyle = index % 2 === 0 ? COLORS.amber : COLORS.blueDark;
    context.beginPath();
    context.arc(x, y, 4, 0, Math.PI * 2);
    context.fill();
    fittedText(context, index % 2 === 0 ? '+' : '−', x, y + .5, { size: 7, weight: 950, color: '#fff', align: 'center', baseline: 'middle', maximumWidth: 7 });
  }
  context.restore();
  fittedText(context, `盐水 ${formatNumber(input.temperature, 0)} ℃`, centerX, beakerY + beakerH + 16, { size: 9, weight: 900, color: COLORS.blueDark, align: 'center', maximumWidth: beakerW + 20 });

  const cardX = margin + beakerWidth + 8;
  const cardW = width - margin - cardX;
  const cardY = top + availableHeight * .1;
  const cardH = Math.min(availableHeight * .78, sceneBottom - cardY - 3);
  box(context, cardX, cardY, cardW, cardH, { radius: 12, fill: COLORS.paper, stroke: COLORS.line });
  fittedText(context, '原题四电阻网络', cardX + 10, cardY + 20, { size: 11, weight: 950, maximumWidth: cardW - 20 });
  const switchY = cardY + 43;
  const pillW = Math.max(30, (cardW - 25) / 2);
  pill(context, 'S₂ 断开', cardX + 10, switchY, pillW, { height: 23, fill: state === '断开' ? COLORS.blueSoft : '#f5f7f9', color: state === '断开' ? COLORS.blueDark : COLORS.muted });
  pill(context, 'S₂ 闭合', cardX + 15 + pillW, switchY, pillW, { height: 23, fill: state === '闭合' ? COLORS.amberSoft : '#f5f7f9', color: state === '闭合' ? COLORS.amber : COLORS.muted });
  const circuitTop = cardY + 66;
  const circuitHeight = Math.max(78, cardH * .44);
  drawSalineCircuit(context, cardX + 7, circuitTop, cardW - 14, circuitHeight, input, result, switchClosed);
  const readingY = circuitTop + circuitHeight + 11;
  const reading = state === '断开'
    ? `A=${formatNumber(input.meterOpen, 0)} mA · I液=${formatNumber(result.currentOpen, 0)} mA`
    : state === '闭合'
      ? `A=${formatNumber(input.meterClosed, 0)} mA · I液=${formatNumber(result.currentClosed, 0)} mA`
      : state === '分流'
        ? `R₃∥R₄=${formatNumber(result.rightEquivalent, 0)} Ω · 电流倍率 ${formatNumber(result.currentMultiplier, 0)}`
        : state === '反演'
          ? `R液=${formatNumber(result.resistance, 0)} Ω · σ=${formatNumber(result.conductivity, 3)} S/m`
          : '核对 R₁—R₄ 与 15 mA 量程';
  fittedText(context, reading, cardX + cardW / 2, readingY, {
    size: width < 430 ? 9 : 12,
    weight: 950,
    color: state === '断开' ? COLORS.blueDark : state === '闭合' ? COLORS.amber : COLORS.ink,
    align: 'center',
    maximumWidth: cardW - 14
  });
  if (cardH > 170) {
    fittedText(context, `同一电源 ${formatNumber(result.voltageA, 0)} V · 两状态电压差 ${formatNumber(result.voltageMismatch, 3)} V`, cardX + cardW / 2, cardY + cardH - 13, { size: 7.5, weight: 850, color: COLORS.muted, align: 'center', maximumWidth: cardW - 14 });
  }

  statusStrip(context, width, height, [
    { label: 'S₂断开/闭合' },
    { label: `R液 ${formatNumber(result.resistance, 1)} Ω` },
    { label: `${formatNumber(input.temperature, 0)} ℃ · σ ${formatNumber(result.conductivity, 3)} S/m` }
  ]);
}

function rotatePoint(centerX, centerY, localX, localY, angle) {
  return {
    x: centerX + localX * Math.cos(angle) - localY * Math.sin(angle),
    y: centerY + localX * Math.sin(angle) + localY * Math.cos(angle)
  };
}

function drawSolarPanel(context, centerX, centerY, panelWidth, panelAngle, voltageDifference) {
  const angle = panelAngle * Math.PI / 180;
  const panelHeight = Math.max(22, panelWidth * .18);
  context.save();
  context.translate(centerX, centerY);
  context.rotate(angle);
  roundedPath(context, -panelWidth / 2, -panelHeight / 2, panelWidth, panelHeight, 4);
  const gradient = context.createLinearGradient(-panelWidth / 2, 0, panelWidth / 2, 0);
  gradient.addColorStop(0, '#0f477b');
  gradient.addColorStop(.5, '#176ab6');
  gradient.addColorStop(1, '#0c3d6b');
  context.fillStyle = gradient;
  context.fill();
  context.strokeStyle = '#d8edff';
  context.lineWidth = 1;
  for (let index = -2; index <= 2; index += 1) {
    context.beginPath();
    context.moveTo(index * panelWidth / 6, -panelHeight / 2 + 2);
    context.lineTo(index * panelWidth / 6, panelHeight / 2 - 2);
    context.stroke();
  }
  context.strokeStyle = '#173b5c';
  context.lineWidth = 3;
  context.stroke();
  const sensorOffset = Math.min(18, panelWidth * .13);
  const leftLight = clamp(.5 + voltageDifference * .7, .08, .95);
  const rightLight = clamp(.5 - voltageDifference * .7, .08, .95);
  [
    { x: -sensorOffset, light: leftLight, label: 'L₁' },
    { x: sensorOffset, light: rightLight, label: 'L₂' }
  ].forEach((sensor) => {
    context.fillStyle = `rgba(240,161,27,${.25 + sensor.light * .7})`;
    context.strokeStyle = '#6a4a17';
    context.lineWidth = 1.5;
    context.beginPath();
    context.arc(sensor.x, -panelHeight / 2 - 8, 6, 0, Math.PI * 2);
    context.fill();
    context.stroke();
    fittedText(context, sensor.label, sensor.x, -panelHeight / 2 - 18, { size: 7, weight: 950, align: 'center', color: COLORS.ink, maximumWidth: 18 });
  });
  line(context, [[0, -panelHeight / 2 - 1], [0, -panelHeight / 2 - 32]], COLORS.ink, 4);
  context.restore();
  return {
    angle,
    leftSensor: rotatePoint(centerX, centerY, -Math.min(18, panelWidth * .13), -panelHeight / 2 - 8, angle),
    rightSensor: rotatePoint(centerX, centerY, Math.min(18, panelWidth * .13), -panelHeight / 2 - 8, angle)
  };
}

function drawLightTracker(context, width, height, spec, result, input, phase) {
  const top = sceneHeader(context, width, spec, '光源跟踪：差分电压驱动闭环对准', phase);
  const margin = clamp(width * .035, 10, 24);
  const sceneBottom = height - 51;
  const compact = width < 550;
  const initialAngle = finite(input.panelAngle);
  const lightAngle = finite(input.lightAngle);
  const initialError = finite(result.initialError, lightAngle - initialAngle);
  const direction = finite(result.direction, Math.sign(initialError));
  const motion = result.active ? clamp((phase - .24) / .62) : 0;
  const currentError = trackerErrorAtProgress(initialError, finite(result.finalError, initialError), motion);
  const currentPanelAngle = lightAngle - currentError;
  const currentDifference = 2 * finite(input.sensitivity, .45) * Math.sin(currentError * Math.PI / 180);

  const visualWidth = compact ? width - margin * 2 : width * .62;
  const controllerX = compact ? margin : visualWidth + margin;
  const controllerY = compact ? sceneBottom - Math.max(82, (sceneBottom - top) * .28) : top + 24;
  const controllerW = compact ? width - margin * 2 : width - margin - controllerX;
  const controllerH = compact ? sceneBottom - controllerY : sceneBottom - controllerY - 5;
  const visualBottom = compact ? controllerY - 6 : sceneBottom;
  const centerX = margin + visualWidth * .53;
  const centerY = top + (visualBottom - top) * .65;
  const sunDistance = Math.min(visualWidth * .42, (visualBottom - top) * .47);
  const sunAngle = lightAngle * Math.PI / 180;
  const sunX = centerX + Math.sin(sunAngle) * sunDistance;
  const sunY = centerY - Math.cos(sunAngle) * sunDistance;

  const glow = context.createRadialGradient(sunX, sunY, 2, sunX, sunY, 27);
  glow.addColorStop(0, '#fff8ce');
  glow.addColorStop(.48, '#f5bb3c');
  glow.addColorStop(1, 'rgba(240,161,27,0)');
  context.fillStyle = glow;
  context.beginPath();
  context.arc(sunX, sunY, 28, 0, Math.PI * 2);
  context.fill();
  context.fillStyle = '#f0a11b';
  context.beginPath();
  context.arc(sunX, sunY, 11, 0, Math.PI * 2);
  context.fill();
  fittedText(context, `光源 ${formatNumber(lightAngle, 0)}°`, sunX, sunY - 19, { size: 8, weight: 900, color: COLORS.amber, align: 'center', maximumWidth: 78 });

  const panelWidth = Math.min(visualWidth * .58, compact ? 130 : 210);
  const panel = drawSolarPanel(context, centerX, centerY, panelWidth, currentPanelAngle, currentDifference);
  line(context, [[sunX, sunY], [panel.leftSensor.x, panel.leftSensor.y]], 'rgba(240,161,27,.55)', 1.5, [5, 4]);
  line(context, [[sunX, sunY], [panel.rightSensor.x, panel.rightSensor.y]], 'rgba(240,161,27,.55)', 1.5, [5, 4]);
  const standTop = rotatePoint(centerX, centerY, 0, 10, panel.angle);
  line(context, [[standTop.x, standTop.y], [centerX, visualBottom - 20]], '#526579', 4);
  box(context, centerX - 26, visualBottom - 24, 52, 18, { radius: 8, fill: '#334e68', stroke: '#fff' });
  fittedText(context, '伺服电机', centerX, visualBottom - 15, { size: 8, weight: 900, color: '#fff', align: 'center', baseline: 'middle', maximumWidth: 46 });
  if (result.active && phase > .22 && phase < .9) {
    const arrowY = centerY + 42;
    arrow(context, centerX - direction * 28, arrowY, centerX + direction * 28, arrowY, COLORS.amber, direction > 0 ? '右转' : '左转');
  }
  fittedText(context, `板面 ${formatNumber(currentPanelAngle, 1)}° · 误差 ${formatNumber(currentError, 1)}°`, centerX, visualBottom - 32, {
    size: 9, weight: 900, color: Math.abs(currentDifference) <= finite(input.deadZone) ? COLORS.green : COLORS.blueDark, align: 'center', maximumWidth: visualWidth - 10
  });

  box(context, controllerX, controllerY, controllerW, controllerH, { radius: 12, fill: COLORS.paper, stroke: COLORS.line });
  fittedText(context, '差分控制器', controllerX + 11, controllerY + 19, { size: 11, weight: 950, maximumWidth: controllerW - 22 });
  const barAreaTop = controllerY + 31;
  const barWidth = Math.max(16, (controllerW - 33) / 2);
  const relative = clamp(.5 + currentDifference / Math.max(.01, 4 * finite(input.sensitivity, .45)));
  const values = [clamp(relative), clamp(1 - relative)];
  values.forEach((value, index) => {
    const x = controllerX + 11 + index * (barWidth + 9);
    box(context, x, barAreaTop, barWidth, 12, { radius: 6, fill: '#edf2f6', stroke: false });
    box(context, x, barAreaTop, barWidth * value, 12, { radius: 6, fill: index === 0 ? COLORS.blue : COLORS.amber, stroke: false });
    fittedText(context, index === 0 ? 'U₁' : 'U₂', x + barWidth / 2, barAreaTop + 25, { size: 8, weight: 950, align: 'center', color: COLORS.muted, maximumWidth: barWidth });
  });
  const differenceY = compact ? controllerY + controllerH - 26 : controllerY + controllerH * .56;
  fittedText(context, `ΔU = ${formatNumber(currentDifference, 3)} V`, controllerX + controllerW / 2, differenceY, { size: compact ? 10 : 12, weight: 950, align: 'center', color: Math.abs(currentDifference) <= finite(input.deadZone) ? COLORS.green : COLORS.ink, maximumWidth: controllerW - 18 });
  const stopped = Math.abs(currentDifference) <= finite(input.deadZone);
  const action = stopped ? '死区内：电机停止' : currentDifference > 0 ? '控制输出：向右点动' : '控制输出：向左点动';
  if (!compact || controllerH > 91) {
    pill(context, action, controllerX + 9, controllerY + controllerH - 31, controllerW - 18, {
      height: 22,
      size: 8,
      fill: stopped ? COLORS.greenSoft : COLORS.amberSoft,
      color: stopped ? COLORS.green : COLORS.amber,
      stroke: stopped ? '#b6dec9' : '#ead09c'
    });
  }

  statusStrip(context, width, height, [
    { label: 'L₁ / L₂ 受光' },
    { label: `比较 ΔU ${formatNumber(currentDifference, 2)} V` },
    { label: stopped ? '停止' : '电机点动', color: stopped ? COLORS.green : COLORS.amber }
  ]);
}

function drawSpring(context, x, y1, y2, width, turns, color = COLORS.blueDark) {
  const points = [[x, y1]];
  const lead = Math.min(8, (y2 - y1) * .12);
  points.push([x, y1 + lead]);
  for (let index = 0; index <= turns * 2; index += 1) {
    const t = index / (turns * 2);
    points.push([x + (index % 2 === 0 ? -width / 2 : width / 2), lerp(y1 + lead, y2 - lead, t)]);
  }
  points.push([x, y2]);
  line(context, points, color, 2.4);
}

function drawCottonCloud(context, x, y, width, height, density) {
  context.save();
  const fill = context.createLinearGradient(0, y, 0, y + height);
  fill.addColorStop(0, '#fffdf8');
  fill.addColorStop(1, `rgba(215,226,235,${.55 + density * .3})`);
  context.fillStyle = fill;
  context.strokeStyle = '#9db1c3';
  context.lineWidth = 1.5;
  const lobes = 7;
  for (let index = 0; index < lobes; index += 1) {
    const cx = x + width * (.08 + index * .14);
    const cy = y + height * (.43 + (index % 2) * .11);
    const radiusX = width * (.12 + density * .015);
    const radiusY = Math.max(5, height * (.38 - density * .07));
    context.beginPath();
    context.ellipse(cx, cy, radiusX, radiusY, 0, 0, Math.PI * 2);
    context.fill();
    context.stroke();
  }
  context.restore();
}

function drawCottonMeasurementRow(context, x, y, width, height, input, closed, active) {
  box(context, x, y, width, height, {
    radius: 8,
    fill: active ? (closed ? COLORS.blueSoft : COLORS.amberSoft) : '#f6f8fa',
    stroke: active ? (closed ? '#a8cbea' : '#ead09c') : COLORS.line
  });
  fittedText(context, closed ? 'S₂闭合' : 'S₂断开', x + 7, y + 13, { size: 7.5, weight: 950, color: closed ? COLORS.blueDark : COLORS.amber, maximumWidth: width * .25 });
  const circuitY = y + height * .62;
  const pathStart = x + width * .24;
  const resistorJoin = x + width * .55;
  const pathEnd = x + width - 7;
  drawResistor(context, pathStart, resistorJoin - 4, circuitY, active ? COLORS.blueDark : COLORS.muted);
  fittedText(context, `R箱 ${formatNumber(closed ? input.boxBefore : input.boxAfter, 1)}`, (pathStart + resistorJoin) / 2, circuitY - 9, { size: 6.8, weight: 900, color: COLORS.muted, align: 'center', maximumWidth: resistorJoin - pathStart + 8 });
  drawResistor(context, resistorJoin + 4, pathEnd, circuitY, closed ? '#9aa9b5' : COLORS.amber);
  fittedText(context, 'R_c', (resistorJoin + pathEnd) / 2, circuitY - 9, { size: 7, weight: 950, color: closed ? COLORS.muted : COLORS.amber, align: 'center', maximumWidth: pathEnd - resistorJoin });
  const bypassY = circuitY - 18;
  line(context, [[resistorJoin, circuitY], [resistorJoin, bypassY], [resistorJoin + 8, bypassY]], COLORS.ink, 1.5);
  line(context, [[pathEnd, circuitY], [pathEnd, bypassY], [pathEnd - 7, bypassY]], COLORS.ink, 1.5);
  context.fillStyle = COLORS.ink;
  context.beginPath(); context.arc(resistorJoin + 8, bypassY, 2.2, 0, Math.PI * 2); context.fill();
  context.beginPath(); context.arc(pathEnd - 7, bypassY, 2.2, 0, Math.PI * 2); context.fill();
  line(context, [[resistorJoin + 8, bypassY], [pathEnd - 8, bypassY - (closed ? 0 : 8)]], closed ? COLORS.blue : COLORS.muted, 2);
  fittedText(context, closed ? '旁路 R_c' : 'R_c 串入', x + width - 6, y + 12, { size: 6.8, weight: 900, color: closed ? COLORS.blueDark : COLORS.amber, align: 'right', maximumWidth: width * .3 });
}

function drawCotton(context, width, height, spec, result, input, phase) {
  const top = sceneHeader(context, width, spec, '棉花回潮率：先统一压力，再允许读数', phase);
  const margin = clamp(width * .035, 10, 24);
  const sceneBottom = height - 51;
  const rigWidth = (width - margin * 2) * (width < 500 ? .56 : .58);
  const rigX = margin;
  const rigTop = top + 13;
  const rigBottom = sceneBottom - 6;
  const rigHeight = rigBottom - rigTop;
  const pressProgress = phase < .18 ? 0 : smooth((phase - .18) / .42);
  const targetCompression = finite(input.compression);
  const currentCompression = targetCompression * pressProgress;
  const currentForce = finite(input.springConstant) * currentCompression;
  const unlockedNow = currentForce >= finite(input.minimumForce);
  const centerX = rigX + rigWidth * .5;
  const frameLeft = rigX + 11;
  const frameRight = rigX + rigWidth - 11;
  const supportY = rigTop + 5;
  const bottomPlateY = rigBottom - 19;
  const visualCompression = clamp(currentCompression / 40) * Math.min(50, rigHeight * .3);
  const pressY = bottomPlateY - Math.min(86, rigHeight * .5) + visualCompression;
  line(context, [[frameLeft, rigBottom], [frameLeft, supportY], [frameRight, supportY], [frameRight, rigBottom]], '#536d84', 4);
  line(context, [[frameLeft - 5, rigBottom], [frameRight + 5, rigBottom]], '#334e68', 6);
  drawSpring(context, centerX, supportY + 2, pressY - 7, Math.min(30, rigWidth * .18), 6, COLORS.blueDark);
  box(context, centerX - rigWidth * .3, pressY - 7, rigWidth * .6, 14, { radius: 3, fill: '#365d7e', stroke: '#fff', lineWidth: 1 });
  box(context, centerX - rigWidth * .34, bottomPlateY, rigWidth * .68, 12, { radius: 3, fill: '#365d7e', stroke: '#fff', lineWidth: 1 });
  const cottonVisible = phase >= .12;
  if (cottonVisible) {
    const cottonTop = pressY + 7;
    const cottonHeight = Math.max(10, bottomPlateY - cottonTop);
    drawCottonCloud(context, centerX - rigWidth * .27, cottonTop, rigWidth * .54, cottonHeight, clamp(currentCompression / 40));
    fittedText(context, '棉花样品', centerX, cottonTop + cottonHeight * .56, { size: 8, weight: 900, color: '#526579', align: 'center', maximumWidth: rigWidth * .46 });
  } else {
    fittedText(context, '装入待测棉花', centerX, (pressY + bottomPlateY) / 2, { size: 9, weight: 900, color: COLORS.muted, align: 'center', maximumWidth: rigWidth * .7 });
  }
  if (currentCompression > .1) arrow(context, centerX + rigWidth * .35, pressY - 20, centerX + rigWidth * .35, pressY + 17, COLORS.amber, 'F');
  fittedText(context, `k ${formatNumber(input.springConstant, 1)} N/mm`, frameLeft + 2, supportY + 17, { size: 8, weight: 900, color: COLORS.blueDark, maximumWidth: rigWidth * .42 });
  fittedText(context, `x ${formatNumber(currentCompression, 1)} mm`, frameLeft + 2, supportY + 34, { size: 8, weight: 900, color: COLORS.muted, maximumWidth: rigWidth * .42 });
  pill(context, `F = ${formatNumber(currentForce, 1)} N`, centerX - Math.min(54, rigWidth * .28), rigBottom - 10, Math.min(108, rigWidth * .56), {
    height: 22,
    size: 9,
    fill: unlockedNow ? COLORS.greenSoft : COLORS.amberSoft,
    color: unlockedNow ? COLORS.green : COLORS.amber,
    stroke: unlockedNow ? '#b6dec9' : '#ead09c'
  });

  const cardX = rigX + rigWidth + 8;
  const cardW = width - margin - cardX;
  const cardY = rigTop;
  const cardH = rigBottom - cardY;
  box(context, cardX, cardY, cardW, cardH, { radius: 12, fill: COLORS.paper, stroke: COLORS.line });
  fittedText(context, unlockedNow ? '压力门禁已通过' : '压力门禁锁定', cardX + 10, cardY + 20, {
    size: 10,
    weight: 950,
    color: unlockedNow ? COLORS.green : COLORS.amber,
    maximumWidth: cardW - 20
  });
  fittedText(context, `门槛 ${formatNumber(input.minimumForce, 0)} N`, cardX + 10, cardY + 38, { size: 8, weight: 850, color: COLORS.muted, maximumWidth: cardW - 20 });
  const gateY = cardY + 50;
  box(context, cardX + 10, gateY, cardW - 20, 8, { radius: 4, fill: '#edf2f6', stroke: false });
  box(context, cardX + 10, gateY, (cardW - 20) * clamp(currentForce / Math.max(.001, finite(input.minimumForce))), 8, { radius: 4, fill: unlockedNow ? COLORS.green : COLORS.amber, stroke: false });

  const measurementY = cardY + cardH * .47;
  if (cardH > 190) {
    const rowX = cardX + 8;
    const rowW = cardW - 16;
    const rowHeight = Math.min(42, cardH * .17);
    const firstY = cardY + 65;
    drawCottonMeasurementRow(context, rowX, firstY, rowW, rowHeight, input, true, phase >= .55 && phase < .7);
    drawCottonMeasurementRow(context, rowX, firstY + rowHeight + 5, rowW, rowHeight, input, false, phase >= .7 && phase < .84);
    fittedText(context, phase < .55 ? '同偏转替代测阻待命' : `R_c = R₁ − R₂ = ${formatNumber(result.measuredResistance, 1)} kΩ`, cardX + cardW / 2, firstY + rowHeight * 2 + 17, {
      size: 8.5, weight: 950, color: unlockedNow && phase >= .55 ? COLORS.blueDark : COLORS.muted, align: 'center', maximumWidth: cardW - 16
    });
  } else {
    fittedText(context, phase < .6 ? '替代测阻待命' : `R_c = R₁ − R₂ = ${formatNumber(result.measuredResistance, 1)} kΩ`, cardX + cardW / 2, measurementY, {
      size: 9, weight: 950, color: unlockedNow && phase >= .6 ? COLORS.blueDark : COLORS.muted, align: 'center', maximumWidth: cardW - 16
    });
  }

  const moisture = Number(result.moistureIndex);
  const moistureAvailable = unlockedNow && Number.isFinite(moisture) && phase >= .76;
  const gaugeY = cardY + cardH - 37;
  pill(context, moistureAvailable ? `含水指标 ${formatNumber(moisture * 100, 0)}%` : '含水指标 —', cardX + 8, gaugeY, cardW - 16, {
    height: 25,
    size: 9,
    fill: moistureAvailable ? COLORS.blueSoft : '#f1f4f7',
    color: moistureAvailable ? COLORS.blueDark : COLORS.muted,
    stroke: moistureAvailable ? '#a8cbea' : COLORS.line
  });
  line(context, [[centerX + rigWidth * .28, pressY + 3], [cardX, pressY + 3], [cardX, measurementY - 5]], unlockedNow ? COLORS.blue : '#9aabba', 2, unlockedNow ? [] : [5, 4]);

  statusStrip(context, width, height, [
    { label: `压力 ${formatNumber(currentForce, 1)} N`, color: unlockedNow ? COLORS.green : COLORS.amber },
    { label: unlockedNow ? `测阻 ${formatNumber(result.measuredResistance, 1)} kΩ` : '测阻锁定' },
    { label: moistureAvailable ? `反演 ${formatNumber(moisture * 100, 0)}%` : '定标待命' }
  ]);
}

/**
 * 绘制“传感与控制”专题的专用 Canvas 场景。
 * 调用前由统一底座完成画布尺寸与淡蓝网格背景设置。
 *
 * @returns {boolean} 命中专用场景时返回 true，否则返回 false。
 */
export function drawSensorScene(context, width, height, spec, result, input, phase) {
  const scene = spec?.scene;
  if (!['thermistor', 'ropeSensor', 'saline', 'lightTracker', 'cotton'].includes(scene)) return false;
  const safeWidth = Math.max(1, finite(width, 1));
  const safeHeight = Math.max(1, finite(height, 1));
  const safeResult = result && typeof result === 'object' ? result : {};
  const safeInput = input && typeof input === 'object' ? input : {};
  const safePhase = clamp(finite(phase));
  context.save();
  context.lineCap = 'round';
  context.lineJoin = 'round';
  context.setLineDash([]);
  if (scene === 'thermistor') drawThermistor(context, safeWidth, safeHeight, spec, safeResult, safeInput, safePhase);
  else if (scene === 'ropeSensor') drawRopeSensor(context, safeWidth, safeHeight, spec, safeResult, safeInput, safePhase);
  else if (scene === 'saline') drawSaline(context, safeWidth, safeHeight, spec, safeResult, safeInput, safePhase);
  else if (scene === 'lightTracker') drawLightTracker(context, safeWidth, safeHeight, spec, safeResult, safeInput, safePhase);
  else drawCotton(context, safeWidth, safeHeight, spec, safeResult, safeInput, safePhase);
  context.restore();
  return true;
}

export function runSensorSceneSemanticTests() {
  const open = ropeCircuitState(0, { current1: 1, current2: 2 });
  const closed = ropeCircuitState(.5, { current1: 1, current2: 2 });
  return [
    { name: '盐水正离子迁向左侧负极、负离子迁向右侧正极', pass: ionTravelFraction(1, 0) > ionTravelFraction(1, 1) && ionTravelFraction(-1, 0) < ionTravelFraction(-1, 1) },
    { name: 'S₂闭合只新增导电绳并联支路电流', pass: !open.closed && open.totalCurrent === 1 && open.branchCurrent === 0 && closed.closed && closed.totalCurrent === 2 && closed.branchCurrent === 1 },
    { name: '光跟踪动画在死区边缘停止而非机械归零', pass: Math.abs(trackerErrorAtProgress(50, 3.18, 1) - 3.18) < 1e-12 }
  ];
}
