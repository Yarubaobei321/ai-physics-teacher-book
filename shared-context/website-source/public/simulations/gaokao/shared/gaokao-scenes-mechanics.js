const clamp = (value, minimum = 0, maximum = 1) => Math.min(maximum, Math.max(minimum, value));

function commonScaleFractions(first, second) {
  const scale = Math.max(Math.abs(first), Math.abs(second), 1e-12);
  return { first: Math.abs(first) / scale, second: Math.abs(second) / scale };
}

function separatedHammerAngles(delta) {
  return { left: Math.PI - delta, right: delta };
}

function abacusVisualStage(phase, collisionPhase) {
  const halfWindow = .04;
  const epsilon = 1e-12;
  if (phase < collisionPhase - halfWindow - epsilon) return 'before';
  if (phase <= collisionPhase + halfWindow + epsilon) return 'collision';
  return 'after';
}

function format(value, digits = 2) {
  if (Number.isNaN(value)) return '—';
  if (!Number.isFinite(value)) return '∞';
  return value.toFixed(digits);
}

function rounded(context, x, y, width, height, radius, fill, stroke = '') {
  context.beginPath();
  context.roundRect(x, y, width, height, Math.min(radius, width / 2, height / 2));
  if (fill) { context.fillStyle = fill; context.fill(); }
  if (stroke) { context.strokeStyle = stroke; context.stroke(); }
}

function arrow(context, x1, y1, x2, y2, color, label = '') {
  const angle = Math.atan2(y2 - y1, x2 - x1);
  context.save();
  context.strokeStyle = color;
  context.fillStyle = color;
  context.lineWidth = 3;
  context.lineCap = 'round';
  context.beginPath(); context.moveTo(x1, y1); context.lineTo(x2, y2); context.stroke();
  context.beginPath();
  context.moveTo(x2, y2);
  context.lineTo(x2 - 9 * Math.cos(angle - Math.PI / 6), y2 - 9 * Math.sin(angle - Math.PI / 6));
  context.lineTo(x2 - 9 * Math.cos(angle + Math.PI / 6), y2 - 9 * Math.sin(angle + Math.PI / 6));
  context.closePath(); context.fill();
  if (label) {
    context.font = '800 12px "Avenir Next", "PingFang SC", sans-serif';
    context.fillText(label, x2 + 8, y2 + 4);
  }
  context.restore();
}

function title(context, heading, detail) {
  context.fillStyle = '#102033';
  context.font = '900 15px "Avenir Next", "PingFang SC", sans-serif';
  context.fillText(heading, 22, 31);
  context.fillStyle = '#526579';
  context.font = '650 12px "Avenir Next", "PingFang SC", sans-serif';
  context.fillText(detail, 22, 52);
}

function cart(context, x, y, width, color, label, bumper = false) {
  const height = 38;
  rounded(context, x, y - height, width, height, 7, color, '#17324d');
  if (bumper) {
    context.fillStyle = '#f0a11b';
    context.fillRect(x + width - 7, y - height + 6, 12, height - 12);
  }
  context.fillStyle = '#fff';
  context.font = '900 12px sans-serif';
  context.textAlign = 'center';
  context.fillText(label, x + width / 2, y - 14);
  context.textAlign = 'left';
  for (const wheelX of [x + 12, x + width - 12]) {
    context.fillStyle = '#102033'; context.beginPath(); context.arc(wheelX, y + 3, 7, 0, Math.PI * 2); context.fill();
    context.fillStyle = '#d8e6f2'; context.beginPath(); context.arc(wheelX, y + 3, 2.5, 0, Math.PI * 2); context.fill();
  }
}

function energyBar(context, x, y, width, value, label, color) {
  context.fillStyle = '#5b6b7d';
  context.font = '750 11px sans-serif';
  context.fillText(label, x, y - 7);
  rounded(context, x, y, width, 12, 6, '#e2eaf1');
  rounded(context, x, y, width * clamp(value), 12, 6, color);
}

function interpolateChart(points, phase) {
  if (!Array.isArray(points) || points.length === 0) return { x: 0, y: 0, y2: 0 };
  const position = clamp(phase) * (points.length - 1);
  const lower = Math.floor(position);
  const upper = Math.min(points.length - 1, lower + 1);
  const fraction = position - lower;
  const a = points[lower];
  const b = points[upper];
  return {
    x: a.x + (b.x - a.x) * fraction,
    y: a.y + (b.y - a.y) * fraction,
    y2: (a.y2 ?? 0) + ((b.y2 ?? 0) - (a.y2 ?? 0)) * fraction
  };
}

function drawPhotogate(context, x, railY, label) {
  context.strokeStyle = '#506b84';
  context.lineWidth = 5;
  context.beginPath(); context.moveTo(x - 18, railY); context.lineTo(x - 18, railY - 84); context.lineTo(x + 18, railY - 84); context.lineTo(x + 18, railY); context.stroke();
  context.strokeStyle = '#f0a11b'; context.lineWidth = 2; context.setLineDash([5, 5]);
  context.beginPath(); context.moveTo(x - 15, railY - 48); context.lineTo(x + 15, railY - 48); context.stroke(); context.setLineDash([]);
  context.fillStyle = '#526579'; context.font = '800 11px sans-serif'; context.textAlign = 'center'; context.fillText(label, x, railY + 30); context.textAlign = 'left';
}

function drawEnergyAbsorber(context, width, height, result, _input, phase) {
  title(context, '三次遮光共同约束速度与能量', `K后/K前 = ${format(result.retainedRatio * 100, 0)}% · p误差 ${format(result.momentumError * 100, 1)}%`);
  const railY = height * .66;
  const left = width * .12;
  const right = width * .88;
  context.strokeStyle = '#38546f'; context.lineWidth = 5; context.beginPath(); context.moveTo(left, railY + 10); context.lineTo(right, railY + 10); context.stroke();
  drawPhotogate(context, width * .2, railY, '光电门 A');
  drawPhotogate(context, width * .82, railY, '光电门 B');

  const contactX = width * .53;
  let cart2X;
  let cart1X;
  let compressed = false;
  if (phase < .46) {
    const u = phase / .46;
    cart2X = width * (.18 + .28 * u);
    cart1X = contactX + 68;
  } else if (phase < .58) {
    const u = (phase - .46) / .12;
    cart2X = contactX - 57 + 8 * Math.sin(Math.PI * u);
    cart1X = contactX + 3 - 8 * Math.sin(Math.PI * u);
    compressed = true;
  } else {
    const u = (phase - .58) / .42;
    cart1X = contactX + 3 + u * width * .25;
    cart2X = contactX - 57 + u * width * .13;
  }
  cart(context, cart2X, railY, 58, '#0b63c7', '车2', true);
  cart(context, cart1X, railY, 58, '#365c7d', '车1');
  const velocity2 = phase < .46 ? result.beforeSpeed : result.cart2Speed;
  const velocity1 = phase < .58 ? 0 : result.cart1Speed;
  if (velocity2 > .01) arrow(context, cart2X + 10, railY - 52, cart2X + 10 + 45 * clamp(velocity2 / result.beforeSpeed), railY - 52, '#0b63c7', `v₂=${format(velocity2, 2)}`);
  if (velocity1 > .01) arrow(context, cart1X + 12, railY - 75, cart1X + 12 + 45 * clamp(velocity1 / result.beforeSpeed), railY - 75, '#c46d08', `v₁=${format(velocity1, 2)}`);
  if (compressed) {
    context.fillStyle = 'rgba(240,161,27,.18)'; context.beginPath(); context.arc(contactX, railY - 20, 46, 0, Math.PI * 2); context.fill();
    context.fillStyle = '#9b5a00'; context.font = '850 11px sans-serif'; context.fillText('材料压缩', contactX - 28, railY - 92);
  }
  energyBar(context, width * .12, height - 51, width * .30, 1, '碰前平动动能', '#0b63c7');
  energyBar(context, width * .56, height - 51, width * .30, result.retainedRatio, '碰后平动动能', '#f0a11b');
  return true;
}

function magneticField(context, x, y, width, height) {
  rounded(context, x, y, width, height, 8, '#e4effa', '#8db5d8');
  context.fillStyle = '#477ca8'; context.font = '800 12px sans-serif';
  for (let px = x + 17; px < x + width; px += 30) {
    for (let py = y + 17; py < y + height; py += 30) context.fillText('×', px, py);
  }
  context.fillText('B', x + 8, y + 17);
}

function coil(context, x, y, width, height, color = '#c46d08') {
  context.strokeStyle = color; context.lineWidth = 6; context.strokeRect(x, y, width, height);
}

function drawElectromagneticWeighing(context, width, height, result, input, phase) {
  title(context, '同一个 BL，连接两个测量步骤', `m = EI/(gv) − M = ${format(result.measuredMass, 3)} kg`);
  const mid = width / 2;
  context.strokeStyle = '#d1dde8'; context.lineWidth = 1; context.beginPath(); context.moveTo(mid, 68); context.lineTo(mid, height - 28); context.stroke();

  context.fillStyle = phase < .5 ? '#0b63c7' : '#66788a'; context.font = '900 13px sans-serif'; context.fillText('① 通电平衡', 24, 82);
  const leftX = width * .24;
  const trayY = height * .39;
  context.strokeStyle = '#38546f'; context.lineWidth = 5; context.beginPath(); context.moveTo(leftX - 72, trayY); context.lineTo(leftX + 72, trayY); context.stroke();
  context.beginPath(); context.moveTo(leftX - 58, trayY); context.lineTo(leftX - 40, trayY + 35); context.moveTo(leftX + 58, trayY); context.lineTo(leftX + 40, trayY + 35); context.stroke();
  rounded(context, leftX - 32, trayY - 53, 64, 48, 7, '#365c7d');
  context.fillStyle = '#fff'; context.font = '900 13px sans-serif'; context.textAlign = 'center'; context.fillText('m', leftX, trayY - 23); context.textAlign = 'left';
  magneticField(context, leftX - 92, trayY + 48, 184, 82);
  coil(context, leftX - 58, trayY + 28, 116, 92);
  arrow(context, leftX + 82, trayY + 88, leftX + 82, trayY + 35, '#0b63c7', 'BIL');
  arrow(context, leftX + 110, trayY + 35, leftX + 110, trayY + 88, '#c46d08', '(M+m)g');
  context.fillStyle = '#526579'; context.font = '750 11px sans-serif'; context.fillText(`I=${format(input.current, 2)} A`, leftX - 42, trayY + 148);

  context.fillStyle = phase >= .5 ? '#0b63c7' : '#66788a'; context.font = '900 13px sans-serif'; context.fillText('② 断路移动磁场', mid + 24, 82);
  const rightX = width * .75;
  coil(context, rightX - 63, trayY - 18, 126, 132, '#0b63c7');
  const fieldShift = phase < .5 ? -20 : -20 + 55 * ((phase - .5) / .5);
  magneticField(context, rightX - 92, trayY + fieldShift, 184, 70);
  arrow(context, rightX + 112, trayY + 5, rightX + 112, trayY + 70, '#c46d08', `v=${format(input.fieldSpeed, 2)}`);
  rounded(context, rightX - 72, trayY + 142, 144, 42, 8, '#f7fafc', '#b8cad9');
  context.fillStyle = '#102033'; context.font = '900 15px sans-serif'; context.textAlign = 'center'; context.fillText(`E = ${format(input.emf, 2)} V`, rightX, trayY + 168); context.textAlign = 'left';

  rounded(context, mid - 72, height - 62, 144, 38, 19, '#eaf4ff', '#9ac4e9');
  context.fillStyle = '#0b63c7'; context.font = '900 13px sans-serif'; context.textAlign = 'center'; context.fillText(`BL = E/v = ${format(result.bl, 3)}`, mid, height - 38); context.textAlign = 'left';
  return true;
}

function drawEddyBrake(context, width, height, result, _input, phase) {
  const finiteStop = Number.isFinite(result.timeToTenPercent) ? result.timeToTenPercent : 8;
  const time = phase * finiteStop;
  const speedFraction = result.dampingRate > 0 ? Math.exp(-result.dampingRate * time) : 1;
  title(context, '磁场越强，圆盘转速衰减越快', `B=${format(result.fieldMilliTesla, 1)} mT · ω/ω₀=${format(speedFraction, 2)}`);
  const cx = width * .47;
  const cy = height * .52;
  const radius = Math.min(width, height) * .24;
  const angle = phase * Math.PI * 10 * (0.25 + speedFraction);
  context.save(); context.translate(cx, cy); context.rotate(angle);
  const diskGradient = context.createRadialGradient(-radius * .25, -radius * .3, 3, 0, 0, radius);
  diskGradient.addColorStop(0, '#f8fbfd'); diskGradient.addColorStop(1, '#8da6b9');
  context.fillStyle = diskGradient; context.beginPath(); context.arc(0, 0, radius, 0, Math.PI * 2); context.fill();
  context.strokeStyle = '#526b80'; context.lineWidth = 3; context.stroke();
  for (let i = 0; i < 10; i += 1) { const a = i * Math.PI / 5; context.beginPath(); context.moveTo(radius * .18 * Math.cos(a), radius * .18 * Math.sin(a)); context.lineTo(radius * .88 * Math.cos(a), radius * .88 * Math.sin(a)); context.stroke(); }
  context.restore();
  context.fillStyle = '#263e55'; context.beginPath(); context.arc(cx, cy, 12, 0, Math.PI * 2); context.fill();

  const magnetX = cx + radius * .55;
  rounded(context, magnetX - 42, cy - radius - 45, 84, 38, 6, '#d94a45');
  rounded(context, magnetX - 42, cy + radius + 7, 84, 38, 6, '#2f73b6');
  context.fillStyle = '#fff'; context.font = '900 13px sans-serif'; context.textAlign = 'center'; context.fillText('N', magnetX, cy - radius - 21); context.fillText('S', magnetX, cy + radius + 31); context.textAlign = 'left';
  context.strokeStyle = '#f0a11b'; context.lineWidth = 3;
  for (const offset of [-22, 0, 22]) { context.beginPath(); context.arc(magnetX + offset, cy, 18 + 4 * speedFraction, 0, Math.PI * 1.55); context.stroke(); }
  context.fillStyle = '#9b5a00'; context.font = '800 11px sans-serif'; context.fillText('涡流回路', magnetX - 34, cy + 5);

  context.strokeStyle = '#0b63c7'; context.lineWidth = 4; context.beginPath(); context.arc(cx, cy, radius + 20, -2.5, -0.5); context.stroke();
  arrow(context, cx - radius * .7, cy - radius * .72, cx - radius * .42, cy - radius * .95, '#0b63c7', 'ω');
  energyBar(context, width * .73, height * .34, width * .20, speedFraction ** 2, '转动能比例', '#0b63c7');
  energyBar(context, width * .73, height * .51, width * .20, 1 - speedFraction ** 2, '转化为内能', '#f0a11b');
  context.fillStyle = '#526579'; context.font = '750 11px sans-serif'; context.fillText(`t=${format(time, 2)} s`, width * .73, height * .67);
  return true;
}

function drawAbacus(context, width, height, result, input, phase) {
  const state = interpolateChart(result.chart, phase);
  const boundaryDetail = result.crossesFrameWithSpeed
    ? '乙以非零速度触框；触框后需切换模型'
    : (result.reachesFrame ? '乙恰好在右边框处停下' : '乙将在右边框前停下');
  title(context, '摩擦—碰撞—摩擦三段模型', boundaryDetail);
  const left = width * .1;
  const right = width * .9;
  const railY = height * .55;
  const framePosition = result.framePosition ?? input.firstGap + input.secondGap;
  const beadTrackEnd = right - 28;
  const mapX = (position) => left + clamp(position / framePosition) * (beadTrackEnd - left);
  rounded(context, left - 18, railY - 90, right - left + 36, 180, 14, 'rgba(255,255,255,.5)', '#8aa0b5');
  context.strokeStyle = '#8a663f'; context.lineWidth = 7; context.beginPath(); context.moveTo(left, railY); context.lineTo(right, railY); context.stroke();
  context.fillStyle = '#724b29'; context.fillRect(left - 10, railY - 76, 12, 152); context.fillRect(right - 2, railY - 76, 12, 152);
  const beadA = mapX(state.y);
  const beadB = mapX(state.y2);
  const atFrame = state.y2 >= framePosition - 1e-7;
  const visualStage = abacusVisualStage(phase, result.collisionPhase);
  for (const [x, color, label] of [[beadA, '#0b63c7', '甲'], [beadB, '#f0a11b', '乙']]) {
    context.fillStyle = color; context.beginPath(); context.ellipse(x, railY, 25, 38, 0, 0, Math.PI * 2); context.fill();
    context.fillStyle = '#fff'; context.beginPath(); context.arc(x, railY, 7, 0, Math.PI * 2); context.fill();
    context.fillStyle = '#102033'; context.font = '900 12px sans-serif'; context.textAlign = 'center'; context.fillText(label, x, railY - 51); context.textAlign = 'left';
  }
  if (visualStage === 'before') arrow(context, beadA - 25, railY - 52, beadA + 18, railY - 52, '#0b63c7', 'v甲');
  else if (visualStage === 'collision') {
    context.fillStyle = 'rgba(240,161,27,.2)'; context.beginPath(); context.arc((beadA + beadB) / 2, railY, 58, 0, Math.PI * 2); context.fill();
  } else if (!atFrame) arrow(context, beadB - 18, railY - 52, beadB + 25, railY - 52, '#c46d08', 'v乙');
  else {
    context.fillStyle = '#8f4c00'; context.font = '850 10px sans-serif'; context.textAlign = 'right';
    context.fillText(result.crossesFrameWithSpeed ? '触框，后续停止推演' : '在边框处停下', right - 4, railY - 51);
    context.textAlign = 'left';
  }

  const stages = ['甲受摩擦', '极短碰撞', '两珠再减速'];
  const active = visualStage === 'before' ? 0 : visualStage === 'collision' ? 1 : 2;
  stages.forEach((stage, index) => {
    const x = width * (.24 + index * .26);
    rounded(context, x - 55, height - 56, 110, 30, 15, index === active ? '#0b63c7' : '#e4ebf2');
    context.fillStyle = index === active ? '#fff' : '#526579'; context.font = '850 11px sans-serif'; context.textAlign = 'center'; context.fillText(stage, x, height - 37); context.textAlign = 'left';
  });
  return true;
}

function drawCurtain(context, width, height, result, input, phase) {
  title(context, '碰撞期间，电机外力仍在做冲量', `FΔt=${format(result.externalImpulse, 2)} N·s · 共同速度 ${format(result.commonSpeed, 2)} m/s`);
  const top = height * .22;
  const railY = height * .34;
  const floor = height * .81;
  rounded(context, width * .08, top, width * .84, floor - top, 6, '#eaf4fb', '#a9bdcf');
  context.fillStyle = '#d9e5ef'; context.fillRect(width * .5 - 4, top, 8, floor - top);
  context.strokeStyle = '#38546f'; context.lineWidth = 7; context.beginPath(); context.moveTo(width * .12, railY); context.lineTo(width * .88, railY); context.stroke();
  const collisionX = width * .54;
  let x1;
  let x2;
  if (phase < .5) { x1 = width * (.18 + .30 * phase / .5); x2 = collisionX + 54; }
  else if (phase < .61) { const u = (phase - .5) / .11; x1 = collisionX - 54 + 7 * Math.sin(Math.PI * u); x2 = collisionX + 5 - 7 * Math.sin(Math.PI * u); }
  else { const u = (phase - .61) / .39; x1 = collisionX - 54 + u * width * .20; x2 = collisionX + 5 + u * width * .20; }
  cart(context, x1, railY + 54, 56, '#0b63c7', '1');
  cart(context, x2, railY + 54, 56, '#365c7d', '2');

  context.fillStyle = 'rgba(34,98,151,.28)';
  const panelLeft = Math.min(x1 + 28, width * .5);
  context.fillRect(width * .1, railY + 66, Math.max(0, panelLeft - width * .1), floor - railY - 66);
  context.fillStyle = 'rgba(240,161,27,.24)';
  context.fillRect(x2 + 28, railY + 66, Math.max(0, width * .9 - x2 - 28), floor - railY - 66);
  arrow(context, x1 - 40, railY - 15, x1 + 18, railY - 15, '#c46d08', `F电机=${format(input.motorForce, 1)} N`);
  if (phase >= .5 && phase < .61) {
    context.fillStyle = 'rgba(240,161,27,.2)'; context.beginPath(); context.arc(collisionX, railY + 30, 52, 0, Math.PI * 2); context.fill();
    context.fillStyle = '#9b5a00'; context.font = '850 11px sans-serif'; context.fillText('内力冲量等大反向', collisionX - 50, railY + 105);
  }
  const momentumFractions = commonScaleFractions(result.momentumBefore, result.momentumAfter);
  energyBar(context, width * .15, height - 39, width * .27, momentumFractions.first, `p前=${format(result.momentumBefore, 2)}`, '#365c7d');
  energyBar(context, width * .58, height - 39, width * .27, momentumFractions.second, `p后=${format(result.momentumAfter, 2)}`, '#0b63c7');
  return true;
}

function eventTimeline(context, width, height, phase, labels) {
  const left = width * .12;
  const right = width * .88;
  const y = height - 34;
  context.strokeStyle = '#b7c8d8'; context.lineWidth = 3; context.beginPath(); context.moveTo(left, y); context.lineTo(right, y); context.stroke();
  labels.forEach((label, index) => {
    const fraction = index / (labels.length - 1);
    const x = left + fraction * (right - left);
    const active = Math.abs(fraction - phase) <= .13 || (index === labels.length - 1 && phase > .87);
    context.fillStyle = active ? '#0b63c7' : '#dce6ef'; context.beginPath(); context.arc(x, y, active ? 8 : 6, 0, Math.PI * 2); context.fill();
    context.fillStyle = active ? '#0b63c7' : '#66788a'; context.font = '800 9px sans-serif'; context.textAlign = 'center'; context.fillText(label, x, y - 13); context.textAlign = 'left';
  });
}

function drawRobot(context, width, height, result, _input, phase) {
  const groundY = height * .78;
  const radius = Math.min(width, height) * .23;
  let shellY = groundY - radius;
  let hammerAngle;
  let separationDelta = 0;
  let separated = false;
  let phaseLabel;
  if (phase < .25) {
    const u = phase / .25;
    hammerAngle = Math.PI / 2 * u;
    phaseLabel = '摆锤上摆：单摆锤—地球机械能守恒';
  } else if (phase < .34) {
    hammerAngle = Math.PI / 2;
    phaseLabel = '撞击挡板：竖直动量关系';
  } else if (phase < .72) {
    const u = (phase - .34) / .38;
    shellY -= Math.sin(Math.PI * u) * Math.min(height * .22, result.jumpHeight * 750);
    hammerAngle = Math.PI / 2;
    phaseLabel = u < .5 ? '整体腾空上升' : '整体下落接近地面';
  } else {
    const u = (phase - .72) / .28;
    hammerAngle = Math.PI / 2;
    separationDelta = u * Math.PI * .42;
    separated = true;
    phaseLabel = '落地后：外壳静止，摆锤保持速度并分离';
  }
  title(context, phaseLabel, `v碰前=${format(result.hammerSpeed, 3)} m/s · V共同=${format(result.commonSpeed, 3)} m/s · ΔE=${format(result.energyLoss, 1)} J`);
  context.strokeStyle = '#6f879c'; context.lineWidth = 5; context.beginPath(); context.moveTo(width * .08, groundY + 4); context.lineTo(width * .92, groundY + 4); context.stroke();
  const cx = width * .5;
  context.fillStyle = separated ? 'rgba(219,233,245,.68)' : 'rgba(173,213,247,.58)';
  context.strokeStyle = '#0b63c7'; context.lineWidth = 7; context.beginPath(); context.arc(cx, shellY, radius, 0, Math.PI * 2); context.fill(); context.stroke();
  context.strokeStyle = '#38546f'; context.lineWidth = 5; context.beginPath(); context.moveTo(cx - radius * .65, shellY); context.lineTo(cx + radius * .65, shellY); context.stroke();
  const separatedAngles = separated ? separatedHammerAngles(separationDelta) : null;
  for (const side of [-1, 1]) {
    const angle = separated
      ? (side < 0 ? separatedAngles.left : separatedAngles.right)
      : (side < 0 ? Math.PI / 2 + hammerAngle : Math.PI / 2 - hammerAngle);
    const length = radius * .70;
    const hx = cx + Math.cos(angle) * length;
    const hy = shellY + Math.sin(angle) * length;
    context.strokeStyle = separated ? '#c46d08' : '#526b80'; context.lineWidth = 3; context.beginPath(); context.moveTo(cx, shellY); context.lineTo(hx, hy); context.stroke();
    context.fillStyle = side < 0 ? '#f0a11b' : '#d57812'; context.beginPath(); context.arc(hx, hy, radius * .13, 0, Math.PI * 2); context.fill();
    if (separated) arrow(context, hx, hy - 18, hx, hy + 24, '#c46d08', 'v锤');
  }
  if (phase >= .34 && phase < .72) {
    if (phase < .53) arrow(context, cx + radius + 24, shellY + 25, cx + radius + 24, shellY - 35, '#0b63c7', 'V↑');
    else arrow(context, cx + radius + 24, shellY - 35, cx + radius + 24, shellY + 25, '#0b63c7', 'V↓');
  }
  if (separated) {
    context.fillStyle = '#102033'; context.font = '900 12px sans-serif'; context.fillText('v外壳 = 0', cx - 36, shellY + radius + 25);
  }
  eventTimeline(context, width, height, phase, ['最低点', '碰板前', '碰后', '最高/落地前', '落地后']);
  return true;
}

/**
 * 绘制六个力学/电磁真题的专用场景。
 * 已识别并绘制时返回 true；未知 scene 返回 false，由调用方决定后续处理。
 */
export function drawMechanicsScene(context, width, height, scene, result, input, phase) {
  if (!context || !result?.ok) return false;
  const safePhase = clamp(Number(phase));
  context.save();
  let drawn = false;
  if (scene === 'twoCarts' || scene === 'energyAbsorber') drawn = drawEnergyAbsorber(context, width, height, result, input, safePhase);
  else if (scene === 'weighing' || scene === 'electromagneticWeighing') drawn = drawElectromagneticWeighing(context, width, height, result, input, safePhase);
  else if (scene === 'eddyBrake') drawn = drawEddyBrake(context, width, height, result, input, safePhase);
  else if (scene === 'abacus') drawn = drawAbacus(context, width, height, result, input, safePhase);
  else if (scene === 'curtain') drawn = drawCurtain(context, width, height, result, input, safePhase);
  else if (scene === 'robot') drawn = drawRobot(context, width, height, result, input, safePhase);
  context.restore();
  return drawn;
}

export function runMechanicsSceneSemanticTests() {
  const momentum = commonScaleFractions(.40, .44);
  const angles = separatedHammerAngles(Math.PI * .2);
  return [
    { name: '球形机器人落地后两摆锤均从水平位置向下运动', pass: Math.sin(angles.left) > 0 && Math.sin(angles.right) > 0 },
    { name: '窗帘碰前碰后动量条使用同一标尺', pass: momentum.first < momentum.second && Math.abs(momentum.first - .40 / .44) < 1e-12 && momentum.second === 1 },
    { name: '算盘碰撞视觉窗口由真实碰撞相位驱动', pass: abacusVisualStage(.29, .33) === 'collision' && abacusVisualStage(.20, .33) === 'before' && abacusVisualStage(.40, .33) === 'after' }
  ];
}
