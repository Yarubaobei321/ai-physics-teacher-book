export const FILM_IMPACT_ORIGINAL = Object.freeze({
  massGrams: 30,
  s1Cm: 6.26,
  s2Cm: 6.66,
  frameIntervalMs: 20,
  maxForceN: 100,
  pulseShape: 'triangle'
});

export const PULSE_SHAPES = Object.freeze({
  triangle: {
    label: '线性增长（三角形，题式等效）',
    shortLabel: '三角形',
    averageCoefficient: 0.5,
    forceFraction: (u) => u,
    velocityFraction: (u) => 1 - u * u,
    displacementFraction: (u) => (u - (u * u * u) / 3) / (2 / 3)
  },
  rectangle: {
    label: '恒力（矩形）',
    shortLabel: '矩形',
    averageCoefficient: 1,
    forceFraction: () => 1,
    velocityFraction: (u) => 1 - u,
    displacementFraction: (u) => (u - (u * u) / 2) / 0.5
  },
  halfSine: {
    label: '正弦增长（四分之一周期）',
    shortLabel: '四分之一周期正弦',
    averageCoefficient: 2 / Math.PI,
    forceFraction: (u) => Math.sin((Math.PI * u) / 2),
    velocityFraction: (u) => Math.cos((Math.PI * u) / 2),
    displacementFraction: (u) => Math.sin((Math.PI * u) / 2)
  }
});

const GRAVITY = 9.8;
const GRAVITY_WARNING_RATIO = 0.05;
const ACCELERATION_WARNING_RATIO = 0.2;
const DISPLAY_CYCLE_MS = 5200;
const DISPLAY_COMPRESSION_FRACTION = 0.32;
const DISPLAY_COMPRESSION_MS = DISPLAY_CYCLE_MS * DISPLAY_COMPRESSION_FRACTION;

const finitePositive = (value) => Number.isFinite(value) && value > 0;
const clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, value));
const format = (value, digits = 2) => Number.isFinite(value) ? value.toFixed(digits) : '—';

export function calculateFilmImpact(values) {
  const input = {
    massGrams: Number(values.massGrams),
    s1Cm: Number(values.s1Cm),
    s2Cm: Number(values.s2Cm),
    frameIntervalMs: Number(values.frameIntervalMs),
    maxForceN: Number(values.maxForceN),
    pulseShape: values.pulseShape
  };

  const numericValues = [
    input.massGrams,
    input.s1Cm,
    input.s2Cm,
    input.frameIntervalMs,
    input.maxForceN
  ];

  if (!numericValues.every(finitePositive)) {
    return { ok: false, error: '质量、位移、帧间隔和最大力都必须是大于零的有限数。' };
  }

  const pulse = PULSE_SHAPES[input.pulseShape];
  if (!pulse) {
    return { ok: false, error: '请选择有效的力时程形状。' };
  }

  const massKg = input.massGrams / 1000;
  const s1M = input.s1Cm / 100;
  const s2M = input.s2Cm / 100;
  const intervalSeconds = input.frameIntervalMs / 1000;
  const middleVelocity = (s1M + s2M) / (2 * intervalSeconds);
  const acceleration = (s2M - s1M) / (intervalSeconds * intervalSeconds);
  const impactVelocity = (3 * s2M - s1M) / (2 * intervalSeconds);

  if (!finitePositive(impactVelocity)) {
    return { ok: false, error: '当前位移组合得到的接触前速度不为正，请检查 s₁、s₂ 和时间间隔。' };
  }

  const averageContactForceN = pulse.averageCoefficient * input.maxForceN;
  const weightN = massKg * GRAVITY;
  if (averageContactForceN <= weightN) {
    return {
      ok: false,
      error: '平均接触力 kFmax 不足以克服重力，当前模型没有让小球速度降为零的停止解。'
    };
  }

  const momentumChange = massKg * impactVelocity;
  const compressionTimeSeconds = momentumChange / averageContactForceN;
  const gravityCorrectedCompressionTimeSeconds = momentumChange / (averageContactForceN - weightN);

  if (!finitePositive(compressionTimeSeconds) || !finitePositive(gravityCorrectedCompressionTimeSeconds)) {
    return { ok: false, error: '当前参数无法得到有效的压缩时间。' };
  }

  const gravityImpulseRatio = (weightN * compressionTimeSeconds) / momentumChange;
  const accelerationRelativeDifference = Math.abs(acceleration - GRAVITY) / GRAVITY;
  const warnings = [];

  if (gravityImpulseRatio > GRAVITY_WARNING_RATIO) {
    warnings.push('重力冲量已超过动量变化量的 5%，忽略重力的题式近似可能失效。');
  }
  if (accelerationRelativeDifference > ACCELERATION_WARNING_RATIO) {
    warnings.push('三帧位移反推的加速度与 g 偏差超过 20%，请检查读图、帧间隔或匀加速假设。');
  }

  return {
    ok: true,
    input,
    pulse,
    massKg,
    intervalSeconds,
    middleVelocity,
    acceleration,
    accelerationRelativeDifference,
    impactVelocity,
    momentumChange,
    averageContactForceN,
    weightN,
    compressionTimeSeconds,
    compressionTimeMs: compressionTimeSeconds * 1000,
    gravityCorrectedCompressionTimeSeconds,
    gravityCorrectedCompressionTimeMs: gravityCorrectedCompressionTimeSeconds * 1000,
    gravityImpulseRatio,
    warnings
  };
}

export function sampleFilmImpactProfile(result, count = 81) {
  if (!result || !result.ok) return [];
  const safeCount = Math.max(2, Math.floor(count));

  return Array.from({ length: safeCount }, (_, index) => {
    const u = index / (safeCount - 1);
    return {
      u,
      timeMs: result.compressionTimeMs * u,
      forceN: result.input.maxForceN * result.pulse.forceFraction(u),
      velocity: result.impactVelocity * result.pulse.velocityFraction(u),
      displacementFraction: result.pulse.displacementFraction(u)
    };
  });
}

export function runFilmImpactRegression() {
  const result = calculateFilmImpact(FILM_IMPACT_ORIGINAL);
  const expectedMs = 2.058;
  const toleranceMs = 0.006;
  return {
    name: '原题参数内部回归',
    pass: result.ok && Math.abs(result.compressionTimeMs - expectedMs) <= toleranceMs,
    expectedMs,
    actualMs: result.ok ? result.compressionTimeMs : Number.NaN,
    toleranceMs,
    displayMs: 2.06
  };
}

export function runFilmImpactExtremeTests() {
  const original = calculateFilmImpact(FILM_IMPACT_ORIGINAL);
  const zeroForce = calculateFilmImpact({ ...FILM_IMPACT_ORIGINAL, maxForceN: 0 });
  const negativeMass = calculateFilmImpact({ ...FILM_IMPACT_ORIGINAL, massGrams: -1 });
  const weakForce = calculateFilmImpact({ ...FILM_IMPACT_ORIGINAL, maxForceN: 10 });
  const rectangle = calculateFilmImpact({ ...FILM_IMPACT_ORIGINAL, pulseShape: 'rectangle' });
  const noStopThresholdForce = (FILM_IMPACT_ORIGINAL.massGrams / 1000 * GRAVITY) / PULSE_SHAPES.triangle.averageCoefficient;
  const noStop = calculateFilmImpact({
    ...FILM_IMPACT_ORIGINAL,
    maxForceN: noStopThresholdForce
  });
  const gravitySensitive = calculateFilmImpact({ ...FILM_IMPACT_ORIGINAL, maxForceN: 1 });

  return [
    { name: '最大力为零时拒绝计算', pass: zeroForce.ok === false },
    { name: '质量为负时拒绝计算', pass: negativeMass.ok === false },
    {
      name: '平均接触力不超过重力时拒绝停止解',
      pass: noStop.ok === false && noStop.error.includes('不足以克服重力')
    },
    {
      name: '峰值力减小，压缩时间增大',
      pass: original.ok && weakForce.ok && weakForce.compressionTimeMs > original.compressionTimeMs
    },
    {
      name: '相同峰值下矩形力时程用时更短',
      pass: original.ok && rectangle.ok && rectangle.compressionTimeMs < original.compressionTimeMs
    },
    {
      name: '重力占比超过 5% 时触发近似警告',
      pass: gravitySensitive.ok &&
        gravitySensitive.gravityImpulseRatio > GRAVITY_WARNING_RATIO &&
        gravitySensitive.warnings.some((warning) => warning.includes('5%'))
    }
  ];
}

function trapezoidImpulse(profile) {
  let impulse = 0;
  for (let index = 1; index < profile.length; index += 1) {
    const previous = profile[index - 1];
    const current = profile[index];
    const dtSeconds = (current.timeMs - previous.timeMs) / 1000;
    impulse += 0.5 * (previous.forceN + current.forceN) * dtSeconds;
  }
  return impulse;
}

export function runFilmImpactProfileInvariantTests() {
  return Object.keys(PULSE_SHAPES).map((pulseShape) => {
    const result = calculateFilmImpact({ ...FILM_IMPACT_ORIGINAL, pulseShape });
    if (!result.ok) {
      return { name: `${PULSE_SHAPES[pulseShape].shortLabel}力时程不变量`, pass: false };
    }

    const profile = sampleFilmImpactProfile(result, 2001);
    const impulse = trapezoidImpulse(profile);
    const impulseRelativeError = Math.abs(impulse - result.momentumChange) / result.momentumChange;
    const terminalVelocity = profile.at(-1)?.velocity ?? Number.NaN;
    const terminalVelocityError = Math.abs(terminalVelocity);
    return {
      name: `${result.pulse.shortLabel}：力面积守恒且末速度归零`,
      pass: impulseRelativeError < 1e-5 && terminalVelocityError < 1e-9,
      impulseRelativeError,
      terminalVelocityError
    };
  });
}

function createPolyline(points, width, height, xMax, yMax, valueKey) {
  const left = 52;
  const top = 18;
  const right = 18;
  const bottom = 42;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;

  return points.map((point) => {
    const x = left + (point.timeMs / xMax) * plotWidth;
    const y = top + plotHeight - (point[valueKey] / yMax) * plotHeight;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
}

function renderChart(svg, points, options) {
  const width = 520;
  const height = 230;
  const left = 52;
  const top = 18;
  const right = 18;
  const bottom = 42;
  const baseline = height - bottom;
  const xMax = Math.max(points.at(-1)?.timeMs || 1, 0.01);
  const yMax = Math.max(options.yMax, 0.01);
  const polyline = createPolyline(points, width, height, xMax, yMax, options.valueKey);
  const areaPoints = `${left},${baseline} ${polyline} ${width - right},${baseline}`;
  const xMid = xMax / 2;
  const yMid = yMax / 2;

  svg.innerHTML =
    `<title>${options.title}</title>` +
    `<desc>${options.description}</desc>` +
    '<g class="chart-grid">' +
    `<line x1="${left}" y1="${top}" x2="${left}" y2="${baseline}"></line>` +
    `<line x1="${left}" y1="${baseline}" x2="${width - right}" y2="${baseline}"></line>` +
    `<line x1="${left}" y1="${top + (baseline - top) / 2}" x2="${width - right}" y2="${top + (baseline - top) / 2}"></line>` +
    `<line x1="${left + (width - left - right) / 2}" y1="${top}" x2="${left + (width - left - right) / 2}" y2="${baseline}"></line>` +
    '</g>' +
    `<polygon class="chart-area ${options.areaClass}" points="${areaPoints}"></polygon>` +
    `<polyline class="chart-line ${options.lineClass}" points="${polyline}"></polyline>` +
    `<line class="chart-time-line" data-chart-time="${options.valueKey}" x1="${left}" y1="${top}" x2="${left}" y2="${baseline}" opacity="0"></line>` +
    `<circle class="chart-cursor ${options.cursorClass}" data-chart-cursor="${options.valueKey}" cx="${left}" cy="${baseline}" r="5" opacity="0"></circle>` +
    '<g class="chart-labels">' +
    `<text x="${left}" y="${height - 15}">0</text>` +
    `<text x="${left + (width - left - right) / 2}" y="${height - 15}" text-anchor="middle">${format(xMid, 2)}</text>` +
    `<text x="${width - right}" y="${height - 15}" text-anchor="end">${format(xMax, 2)}</text>` +
    `<text x="${width - right}" y="${height - 2}" text-anchor="end" class="axis-name">t / ms</text>` +
    `<text x="${left - 7}" y="${baseline + 4}" text-anchor="end">0</text>` +
    `<text x="${left - 7}" y="${top + (baseline - top) / 2 + 4}" text-anchor="end">${format(yMid, options.yDigits)}</text>` +
    `<text x="${left - 7}" y="${top + 4}" text-anchor="end">${format(yMax, options.yDigits)}</text>` +
    `<text transform="translate(15 ${(top + baseline) / 2}) rotate(-90)" text-anchor="middle" class="axis-name">${options.yAxis}</text>` +
    '</g>';
}

function chartCursorPosition(result, valueKey, u) {
  const width = 520;
  const height = 230;
  const left = 52;
  const top = 18;
  const right = 18;
  const bottom = 42;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const fraction = valueKey === 'forceN'
    ? result.pulse.forceFraction(u)
    : result.pulse.velocityFraction(u);
  return {
    x: left + u * plotWidth,
    y: top + plotHeight - fraction * plotHeight
  };
}

function drawArrow(context, x1, y1, x2, y2, color, label) {
  const angle = Math.atan2(y2 - y1, x2 - x1);
  context.save();
  context.strokeStyle = color;
  context.fillStyle = color;
  context.lineWidth = 3;
  context.lineCap = 'round';
  context.beginPath();
  context.moveTo(x1, y1);
  context.lineTo(x2, y2);
  context.stroke();
  context.beginPath();
  context.moveTo(x2, y2);
  context.lineTo(x2 - 9 * Math.cos(angle - Math.PI / 6), y2 - 9 * Math.sin(angle - Math.PI / 6));
  context.lineTo(x2 - 9 * Math.cos(angle + Math.PI / 6), y2 - 9 * Math.sin(angle + Math.PI / 6));
  context.closePath();
  context.fill();
  context.font = '700 12px "Avenir Next", "PingFang SC", sans-serif';
  context.fillText(label, x2 + 8, y2 + 4);
  context.restore();
}

function drawFilmImpact(canvas, result, normalizedPhase) {
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const targetWidth = Math.max(Math.round(rect.width * ratio), 1);
  const targetHeight = Math.max(Math.round(rect.height * ratio), 1);
  if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
    canvas.width = targetWidth;
    canvas.height = targetHeight;
  }

  const context = canvas.getContext('2d');
  if (!context) return { phase: '模型未加载', collisionU: null, displayTimeMs: 0 };
  context.setTransform(ratio, 0, 0, ratio, 0, 0);

  const width = rect.width;
  const height = rect.height;
  const filmY = height * 0.72;
  const radius = Math.max(17, Math.min(width, height) * 0.054);
  const contactY = filmY - radius;
  let ballY = contactY;
  let compression = 0;
  let phase = '下落';
  let collisionU = null;
  let displayTimeMs = 0;

  if (normalizedPhase < 0.3) {
    const u = normalizedPhase / 0.3;
    ballY = 52 + (contactY - 52) * (u * u);
    phase = '下落';
  } else if (normalizedPhase < 0.62) {
    collisionU = (normalizedPhase - 0.3) / 0.32;
    compression = result.pulse.displacementFraction(collisionU);
    ballY = contactY + compression * 19;
    displayTimeMs = collisionU * result.compressionTimeMs;
    phase = '压缩（统一节拍慢放）';
  } else if (normalizedPhase < 0.74) {
    collisionU = 1;
    compression = 1;
    ballY = contactY + 19;
    displayTimeMs = result.compressionTimeMs;
    phase = '最大压缩';
  } else {
    const u = (normalizedPhase - 0.74) / 0.26;
    ballY = contactY - Math.sin((Math.PI * u) / 2) * height * 0.36;
    compression = 1 - u;
    displayTimeMs = result.compressionTimeMs;
    phase = '反弹示意';
  }

  const gradient = context.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, '#f8fbff');
  gradient.addColorStop(1, '#eaf3fa');
  context.fillStyle = gradient;
  context.fillRect(0, 0, width, height);

  context.strokeStyle = 'rgba(11, 99, 199, 0.12)';
  context.lineWidth = 1;
  for (let x = 0; x <= width; x += 32) {
    context.beginPath();
    context.moveTo(x, 0);
    context.lineTo(x, height);
    context.stroke();
  }
  for (let y = 0; y <= height; y += 32) {
    context.beginPath();
    context.moveTo(0, y);
    context.lineTo(width, y);
    context.stroke();
  }

  const filmLeft = width * 0.1;
  const filmRight = width * 0.9;
  const filmCenter = width / 2;
  const deformation = compression * 18;
  const contactForceFraction = collisionU === null ? 0 : result.pulse.forceFraction(collisionU);

  if (collisionU !== null && contactForceFraction > 0.02) {
    const glow = context.createRadialGradient(filmCenter, filmY, 2, filmCenter, filmY, 54 + contactForceFraction * 28);
    glow.addColorStop(0, `rgba(244, 165, 28, ${0.5 + contactForceFraction * 0.25})`);
    glow.addColorStop(1, 'rgba(244, 165, 28, 0)');
    context.fillStyle = glow;
    context.fillRect(filmCenter - 90, filmY - 85, 180, 140);
  }

  context.fillStyle = '#d8ecff';
  context.beginPath();
  context.moveTo(filmLeft, filmY);
  context.quadraticCurveTo(filmCenter, filmY + deformation, filmRight, filmY);
  context.lineTo(filmRight, height);
  context.lineTo(filmLeft, height);
  context.closePath();
  context.fill();

  context.strokeStyle = '#0b63c7';
  context.lineWidth = 5;
  context.lineCap = 'round';
  context.beginPath();
  context.moveTo(filmLeft, filmY);
  context.quadraticCurveTo(filmCenter, filmY + deformation, filmRight, filmY);
  context.stroke();

  context.save();
  context.translate(width / 2, ballY);
  const ballGradient = context.createRadialGradient(-radius * 0.35, -radius * 0.4, 2, 0, 0, radius);
  ballGradient.addColorStop(0, '#ffffff');
  ballGradient.addColorStop(0.32, '#b7dcff');
  ballGradient.addColorStop(1, '#0b63c7');
  context.fillStyle = ballGradient;
  context.shadowColor = 'rgba(16, 32, 51, 0.18)';
  context.shadowBlur = 14;
  context.beginPath();
  context.arc(0, 0, radius, 0, Math.PI * 2);
  context.fill();
  context.restore();

  if (normalizedPhase < 0.62) {
    const velocityFraction = collisionU === null ? 1 : result.pulse.velocityFraction(collisionU);
    if (velocityFraction > 0.04) {
      drawArrow(context, filmCenter + radius + 12, ballY - 18, filmCenter + radius + 12, ballY + 18 + velocityFraction * 24, '#c46d08', 'v');
    }
  }
  if (collisionU !== null && contactForceFraction > 0.04) {
    drawArrow(context, filmCenter - radius - 15, ballY + 22, filmCenter - radius - 15, ballY - 16 - contactForceFraction * 30, '#0b63c7', 'F');
  }

  context.fillStyle = '#102033';
  context.font = '800 14px "Avenir Next", "PingFang SC", sans-serif';
  context.fillText(phase, 20, 30);
  context.font = '600 12px "Avenir Next", "PingFang SC", sans-serif';
  context.fillStyle = '#526579';
  const timeLabel = collisionU === null ? '碰撞尚未开始' : `模型内压缩时间 ${format(displayTimeMs, 3)} ms`;
  context.fillText(timeLabel, 20, 51);
  context.textAlign = 'right';
  context.fillText('薄膜形变：归一化示意', width - 20, 30);
  context.textAlign = 'left';

  return { phase, collisionU, displayTimeMs };
}

function mountFilmImpactLab() {
  const form = document.querySelector('[data-film-impact-form]');
  if (!form) return;

  const app = document.querySelector('[data-film-impact-app]');
  const loading = document.querySelector('[data-loading-state]');
  const bootError = document.querySelector('[data-boot-error]');
  const empty = document.querySelector('[data-empty-state]');
  const error = document.querySelector('[data-error-state]');
  const warning = document.querySelector('[data-approximation-warning]');
  const consistency = document.querySelector('[data-consistency-status]');
  const status = document.querySelector('[data-model-status]');
  const canvas = document.querySelector('[data-impact-canvas]');
  const forceChart = document.querySelector('[data-force-chart]');
  const velocityChart = document.querySelector('[data-velocity-chart]');
  const pauseButton = document.querySelector('[data-pause-animation]');
  const resetAnimationButton = document.querySelector('[data-reset-animation]');
  const stepAnimationButton = document.querySelector('[data-step-animation]');
  const resetOriginalButton = document.querySelector('[data-reset-original]');
  const testButton = document.querySelector('[data-run-tests]');
  const screenshotButton = document.querySelector('[data-toggle-book-mode]');
  const scrubber = document.querySelector('[data-scrub-animation]');
  const timeReadout = document.querySelector('[data-time-readout]');
  const slowMotionNote = document.querySelector('[data-slow-motion-note]');
  const inputElements = Array.from(form.querySelectorAll('input[name], select[name]'));
  const rangeElements = Array.from(form.querySelectorAll('[data-sync-input]'));
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  let currentResult = calculateFilmImpact(FILM_IMPACT_ORIGINAL);
  let animationStart = performance.now();
  let paused = reducedMotion;
  let pausedPhase = reducedMotion ? 0.46 : 0;
  let testsPassed = false;
  let frameRequest = null;

  const valuesFromForm = () => Object.fromEntries(new FormData(form).entries());

  const setText = (selector, value) => {
    const element = document.querySelector(selector);
    if (element) element.textContent = value;
  };

  const syncRangesFromNumbers = () => {
    for (const range of rangeElements) {
      const number = document.getElementById(range.dataset.syncInput);
      if (!number) continue;
      const value = Number(number.value);
      range.value = String(clamp(value, Number(range.min), Number(range.max)));
    }
  };

  const updateSourceBadges = () => {
    for (const element of inputElements) {
      const original = element.dataset.original;
      if (original === undefined) continue;
      const field = element.closest('.control-field');
      const changed = String(element.value) !== String(original);
      field?.classList.toggle('is-adjusted', changed);
      const badge = field?.querySelector('[data-source-badge]');
      if (!badge) continue;
      const modelSource = field.dataset.sourceKind === 'model';
      badge.textContent = changed
        ? (modelSource ? '用户模型选择' : '用户调整')
        : (modelSource ? '题式等效假设' : (badge.dataset.originalLabel || badge.textContent));
      if (!badge.dataset.originalLabel && !changed) badge.dataset.originalLabel = badge.textContent;
    }
  };

  const updateScreenshotAccess = () => {
    const available = testsPassed && Boolean(currentResult?.ok);
    screenshotButton.disabled = !available;
    screenshotButton.setAttribute('aria-disabled', String(!available));
    if (!available) {
      screenshotButton.textContent = testsPassed ? '参数有效后可截图' : '验收通过后可截图';
      screenshotButton.title = testsPassed ? '请先修正当前参数' : '整组模型测试尚未通过';
    } else if (!document.body.classList.contains('book-mode')) {
      screenshotButton.textContent = '进入图书截图模式';
      screenshotButton.removeAttribute('title');
    }
  };

  const renderCharts = (result) => {
    const profile = sampleFilmImpactProfile(result);
    renderChart(forceChart, profile, {
      title: '力—时间图',
      description: '当前简化模型中，力曲线下面积等于小球接触前动量。',
      yMax: result.input.maxForceN,
      valueKey: 'forceN',
      lineClass: 'force-line',
      areaClass: 'force-area',
      cursorClass: 'force-cursor',
      yDigits: 0,
      yAxis: 'F / N'
    });
    renderChart(velocityChart, profile, {
      title: '速度—时间图',
      description: '速度由同一力时程积分得到，压缩末速度降到零。',
      yMax: result.impactVelocity,
      valueKey: 'velocity',
      lineClass: 'velocity-line',
      areaClass: 'velocity-area',
      cursorClass: 'velocity-cursor',
      yDigits: 2,
      yAxis: 'v / (m·s⁻¹)'
    });
  };

  const renderResult = () => {
    updateSourceBadges();
    syncRangesFromNumbers();
    const result = calculateFilmImpact(valuesFromForm());
    empty.hidden = true;
    error.hidden = true;
    warning.hidden = true;

    if (!result.ok) {
      currentResult = null;
      app.dataset.valid = 'false';
      empty.hidden = false;
      error.hidden = false;
      error.textContent = result.error;
      status.textContent = '模型暂停：请修正参数';
      consistency.textContent = '当前参数未通过模型前置检查。';
      consistency.dataset.state = 'error';
      updateScreenshotAccess();
      return;
    }

    currentResult = result;
    app.dataset.valid = 'true';
    setText('[data-result="middleVelocity"]', `${format(result.middleVelocity, 3)} m/s`);
    setText('[data-result="acceleration"]', `${format(result.acceleration, 2)} m/s²`);
    setText('[data-result="impactVelocity"]', `${format(result.impactVelocity, 3)} m/s`);
    setText('[data-result="compressionTime"]', `${format(result.compressionTimeMs, 2)} ms`);
    setText('[data-result="compressionChecksum"]', '三角形等效力时程');
    setText('[data-result="pulseCoefficient"]', format(result.pulse.averageCoefficient, 3));
    setText('[data-result="gravityRatio"]', `${format(result.gravityImpulseRatio * 100, 2)}%`);
    setText('[data-result="gravityCorrectedTime"]', `${format(result.gravityCorrectedCompressionTimeMs, 2)} ms`);
    setText('[data-result="pulseLabel"]', result.pulse.label);

    const accelerationMatches = result.accelerationRelativeDifference <= ACCELERATION_WARNING_RATIO;
    consistency.textContent = accelerationMatches
      ? `一致性检查：a=${format(result.acceleration, 2)} m/s²，与 g=${GRAVITY.toFixed(1)} m/s² 相容。`
      : `一致性提醒：a=${format(result.acceleration, 2)} m/s²，与 g 偏差 ${format(result.accelerationRelativeDifference * 100, 0)}%。`;
    consistency.dataset.state = accelerationMatches ? 'pass' : 'warning';

    if (result.warnings.length > 0) {
      warning.hidden = false;
      warning.textContent = result.warnings.join(' ');
    }

    renderCharts(result);
    const slowFactor = DISPLAY_COMPRESSION_MS / result.compressionTimeMs;
    slowMotionNote.textContent = `碰撞段按统一 1.664 s 展示，当前约慢放 ${format(slowFactor, 0)} 倍`;
    status.textContent = result.warnings.length > 0
      ? '当前参数触发近似边界提醒'
      : '三帧测速、动画与图像共用同一组状态量';
    animationStart = performance.now() - pausedPhase * DISPLAY_CYCLE_MS;
    updateScreenshotAccess();
    renderFrame(pausedPhase);
  };

  const renderTests = () => {
    const regression = runFilmImpactRegression();
    const extremeTests = runFilmImpactExtremeTests();
    const invariantTests = runFilmImpactProfileInvariantTests();
    const results = [
      {
        name: regression.name,
        pass: regression.pass,
        detail: `题意显示 ${format(regression.displayMs, 2)} ms；内部 checksum ${format(regression.actualMs, 3)} ms`
      },
      ...extremeTests.map((item) => ({ ...item, detail: item.pass ? '通过' : '未通过' })),
      ...invariantTests.map((item) => ({
        ...item,
        detail: item.pass
          ? `面积误差 ${(item.impulseRelativeError * 100).toExponential(1)}%；末速误差 ${item.terminalVelocityError.toExponential(1)} m/s`
          : '不变量未满足'
      }))
    ];
    const list = document.querySelector('[data-test-results]');
    list.replaceChildren();
    for (const item of results) {
      const row = document.createElement('li');
      row.className = item.pass ? 'test-pass' : 'test-fail';
      const flag = document.createElement('span');
      flag.setAttribute('aria-hidden', 'true');
      flag.textContent = item.pass ? 'PASS' : 'FAIL';
      const name = document.createElement('strong');
      name.textContent = item.name;
      const detail = document.createElement('small');
      detail.textContent = item.detail;
      row.append(flag, name, detail);
      list.appendChild(row);
    }
    testsPassed = results.every((item) => item.pass);
    const summary = document.querySelector('[data-test-summary]');
    summary.textContent = testsPassed
      ? `${results.length} 项测试全部通过，图书截图门禁已解锁`
      : `${results.filter((item) => !item.pass).length} 项测试未通过，图书截图模式保持锁定`;
    summary.dataset.pass = String(testsPassed);
    updateScreenshotAccess();
    return testsPassed;
  };

  const applyBookMode = (enabled) => {
    if (enabled && (!testsPassed || !currentResult?.ok)) {
      status.textContent = '截图模式已拒绝：整组测试与当前参数必须同时有效';
      updateScreenshotAccess();
      return false;
    }
    if (enabled) {
      setPaused(true);
      renderFrame(0.46);
    }
    document.body.classList.toggle('book-mode', enabled);
    screenshotButton.textContent = enabled ? '退出图书截图模式' : '进入图书截图模式';
    screenshotButton.setAttribute('aria-pressed', String(enabled));
    const url = new URL(window.location.href);
    if (enabled) url.searchParams.set('view', 'book');
    else url.searchParams.delete('view');
    window.history.replaceState({}, '', url);
    return true;
  };

  function renderFrame(phase) {
    if (!currentResult || !canvas) return;
    const normalized = ((phase % 1) + 1) % 1;
    pausedPhase = normalized;
    scrubber.value = String(Math.round(normalized * 1000));
    timeReadout.textContent = `演示 t = ${format(normalized * DISPLAY_CYCLE_MS / 1000, 2)} s`;
    const visual = drawFilmImpact(canvas, currentResult, normalized);
    setText('[data-animation-stage]', visual.phase);

    const cursors = document.querySelectorAll('[data-chart-cursor]');
    const timeLines = document.querySelectorAll('[data-chart-time]');
    if (visual.collisionU === null) {
      cursors.forEach((cursor) => cursor.setAttribute('opacity', '0'));
      timeLines.forEach((line) => line.setAttribute('opacity', '0'));
      setText('[data-chart-value="forceN"]', '—');
      setText('[data-chart-value="velocity"]', '—');
      return;
    }

    cursors.forEach((cursor) => {
      const point = chartCursorPosition(currentResult, cursor.dataset.chartCursor, visual.collisionU);
      cursor.setAttribute('cx', String(point.x));
      cursor.setAttribute('cy', String(point.y));
      cursor.setAttribute('opacity', '1');
    });
    timeLines.forEach((line) => {
      const point = chartCursorPosition(currentResult, line.dataset.chartTime, visual.collisionU);
      line.setAttribute('x1', String(point.x));
      line.setAttribute('x2', String(point.x));
      line.setAttribute('opacity', '1');
    });
    setText('[data-chart-value="forceN"]', `${format(currentResult.input.maxForceN * currentResult.pulse.forceFraction(visual.collisionU), 1)} N`);
    setText('[data-chart-value="velocity"]', `${format(currentResult.impactVelocity * currentResult.pulse.velocityFraction(visual.collisionU), 2)} m/s`);
  }

  const scheduleAnimation = () => {
    if (frameRequest !== null || paused) return;
    const animate = (now) => {
      if (paused) {
        frameRequest = null;
        return;
      }
      renderFrame(((now - animationStart) % DISPLAY_CYCLE_MS) / DISPLAY_CYCLE_MS);
      frameRequest = window.requestAnimationFrame(animate);
    };
    frameRequest = window.requestAnimationFrame(animate);
  };

  const setPaused = (nextPaused) => {
    paused = nextPaused;
    pauseButton.textContent = paused ? '继续' : '暂停';
    pauseButton.setAttribute('aria-pressed', String(paused));
    if (paused && frameRequest !== null) {
      window.cancelAnimationFrame(frameRequest);
      frameRequest = null;
    }
    if (!paused) {
      animationStart = performance.now() - pausedPhase * DISPLAY_CYCLE_MS;
      scheduleAnimation();
    }
  };

  inputElements.forEach((element) => element.addEventListener('input', renderResult));
  rangeElements.forEach((range) => range.addEventListener('input', () => {
    const number = document.getElementById(range.dataset.syncInput);
    if (!number) return;
    number.value = range.value;
    number.dispatchEvent(new Event('input', { bubbles: true }));
  }));

  resetOriginalButton.addEventListener('click', () => {
    for (const [key, value] of Object.entries(FILM_IMPACT_ORIGINAL)) {
      const element = form.elements.namedItem(key);
      if (element) element.value = String(value);
    }
    pausedPhase = 0;
    renderResult();
    renderTests();
  });

  testButton.addEventListener('click', renderTests);
  screenshotButton.addEventListener('click', () => applyBookMode(!document.body.classList.contains('book-mode')));
  pauseButton.addEventListener('click', () => setPaused(!paused));
  resetAnimationButton.addEventListener('click', () => {
    setPaused(true);
    renderFrame(0);
  });
  stepAnimationButton.addEventListener('click', () => {
    setPaused(true);
    renderFrame((pausedPhase + 0.04) % 1);
  });
  document.querySelectorAll('[data-jump-phase]').forEach((button) => {
    button.addEventListener('click', () => {
      setPaused(true);
      renderFrame(Number(button.dataset.jumpPhase));
    });
  });
  scrubber.addEventListener('input', () => {
    setPaused(true);
    renderFrame(Number(scrubber.value) / 1000);
  });

  const initialBookMode = new URL(window.location.href).searchParams.get('view') === 'book';
  renderResult();
  renderTests();
  setPaused(paused);
  if (initialBookMode) applyBookMode(true);

  document.documentElement.dataset.gaokaoModelReady = 'true';
  loading.hidden = true;
  bootError.hidden = true;
  app.hidden = false;
  app.setAttribute('aria-busy', 'false');
  renderFrame(pausedPhase);
  if (!paused) scheduleAnimation();

  window.addEventListener('resize', () => renderFrame(pausedPhase), { passive: true });
}

if (typeof document !== 'undefined') {
  mountFilmImpactLab();
}
