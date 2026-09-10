import {
  calculateGaokaoModel,
  getGaokaoModelSpec,
  runGaokaoModelTests
} from './gaokao-models.js';
import { drawMechanicsScene } from './gaokao-scenes-mechanics.js';
import { drawSensorScene } from './gaokao-scenes-sensors.js';
import { drawWaveScene } from './gaokao-scenes-waves.js';

const BUILTIN_SCENES = Object.freeze(['airbag', 'rubberBall', 'harvester']);
const MECHANICS_SCENES = Object.freeze(['twoCarts', 'weighing', 'eddyBrake', 'abacus', 'curtain', 'robot']);
const SENSOR_SCENES = Object.freeze(['thermistor', 'ropeSensor', 'saline', 'lightTracker', 'cotton']);
const WAVE_SCENES = Object.freeze(['ropeWave', 'travelingWave', 'springOscillator', 'forcedDoppler', 'echoSounder']);

// 生成器与浏览器运行时共用这份清单，确保只有专用场景齐备的模型才会生成页面。
export const GAOKAO_READY_SCENES = Object.freeze([
  ...BUILTIN_SCENES,
  ...MECHANICS_SCENES,
  ...SENSOR_SCENES,
  ...WAVE_SCENES
]);

const clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, value));
const escapeHtml = (value) => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;');

export function formatNumber(value, digits = 2) {
  if (Number.isNaN(value)) return '未解锁';
  if (!Number.isFinite(value)) return '∞';
  if (Math.abs(value) >= 100000 || (Math.abs(value) > 0 && Math.abs(value) < 0.001)) {
    return value.toExponential(Math.max(2, Math.min(digits, 3)));
  }
  return value.toFixed(digits);
}

export function validateParameterValues(spec, values = {}) {
  for (const item of spec.parameters) {
    const value = Number(values[item.key] ?? item.value);
    if (!Number.isFinite(value)) return { ok: false, error: `${item.label}须填写有限数值。` };
    if (value < item.minimum || value > item.maximum) {
      const unit = item.unit ? ` ${item.unit}` : '';
      return { ok: false, error: `${item.label}须在 ${item.minimum}—${item.maximum}${unit} 范围内。` };
    }
  }
  return { ok: true };
}

function fieldMarkup(item) {
  const unit = item.unit ? `<span>${escapeHtml(item.unit)}</span>` : '';
  return `
    <div class="gm-field" data-field="${item.key}">
      <div class="gm-field__label">
        <label for="${item.key}">${escapeHtml(item.label)}</label>
        <span class="gm-source">${escapeHtml(item.source)}</span>
      </div>
      <div class="gm-number">
        <input id="${item.key}" name="${item.key}" type="number"
          min="${item.minimum}" max="${item.maximum}" step="${item.step}"
          value="${item.value}" data-original="${item.value}" inputmode="decimal" />
        ${unit}
      </div>
      <input class="gm-range" type="range" min="${item.minimum}" max="${item.maximum}"
        step="${item.step}" value="${item.value}" data-range-for="${item.key}"
        aria-label="调节${escapeHtml(item.label)}" />
      ${item.help ? `<small>${escapeHtml(item.help)}</small>` : ''}
    </div>`;
}

function metricMarkup(item) {
  return `
    <div class="gm-metric">
      <small>${escapeHtml(item.label)}</small>
      <strong data-metric="${item.key}">—</strong>
      <span>${escapeHtml(item.unit)}</span>
    </div>`;
}

function chartCaption(spec) {
  const captions = {
    'process-time': '竖线标出动画对应的物理时刻',
    'operating-point': '竖线标出当前输入对应的工作点',
    probe: '竖线标出固定空间探针',
    none: '图表给出当前参数下的量化关系'
  };
  return captions[spec.chart.cursorMode] || '图表给出当前参数下的量化关系';
}

function pageMarkup(spec) {
  return `
    <header class="gm-sitebar">
      <a class="gm-brand" href="/">
        <img src="/logo-web.png" width="38" height="38" alt="" />
        <span>育才物理创新实验室</span>
      </a>
      <nav aria-label="站点导航">
        <a href="/simulations/">模拟实验室</a>
        <a href="/simulations/gaokao/" aria-current="page">高考真题模拟</a>
      </nav>
    </header>

    <main class="gm-shell" data-gaokao-model-page>
      <section class="gm-hero" aria-labelledby="gm-title">
        <div class="gm-hero__main">
          <a class="gm-back" href="/simulations/gaokao/">← 返回高考真题模拟</a>
          <p class="gm-eyebrow">${spec.year} 广东高考 · ${escapeHtml(spec.topic)}</p>
          <h1 id="gm-title">${escapeHtml(spec.title)}</h1>
          <p class="gm-lead">${escapeHtml(spec.lead)}</p>
          <div class="gm-hero__actions gm-ui-only">
            <button class="gm-button gm-button--primary" type="button" data-scroll-model>进入模型</button>
            <button class="gm-button" type="button" data-toggle-book>打开图书视图</button>
          </div>
        </div>
        <aside class="gm-boundary" aria-labelledby="gm-boundary-title">
          <p class="gm-kicker">题目条件</p>
          <h2 id="gm-boundary-title">这道题给出了什么</h2>
          <p>${escapeHtml(spec.sourceBoundary)}</p>
        </aside>
      </section>

      <section class="gm-model" id="model-workspace" aria-label="交互模型">
        <aside class="gm-card gm-controls gm-ui-only">
          <div class="gm-card__heading">
            <div><p class="gm-kicker">PARAMETERS</p><h2>改变一个量，观察整条证据链</h2></div>
            <button class="gm-reset" type="button" data-reset>恢复默认</button>
          </div>
          <form data-model-form novalidate>${spec.parameters.map(fieldMarkup).join('')}</form>
          <p class="gm-error" data-error role="alert" hidden></p>
        </aside>

        <div class="gm-card gm-workspace">
          <div class="gm-toolbar gm-ui-only" aria-label="动画控制">
            <div>
              <button class="gm-button gm-button--primary" type="button" data-play aria-pressed="false">暂停</button>
              <button class="gm-button" type="button" data-step>单步</button>
              <button class="gm-button" type="button" data-rewind>回到起点</button>
            </div>
            <output data-phase-output aria-live="polite">准备模型</output>
          </div>

          <div class="gm-metrics">${spec.metrics.map(metricMarkup).join('')}</div>
          <p class="gm-warning" data-model-warning role="status" aria-live="polite" hidden></p>

          <div class="gm-stage-wrap">
            <canvas data-model-canvas role="img" aria-label="${escapeHtml(spec.shortTitle)}动态物理示意图">
              当前浏览器不支持画布，可继续读取下方量化图表与模型说明。
            </canvas>
            <div class="gm-stage-caption">
              <strong data-stage-label>${escapeHtml(spec.phases[0])}</strong>
              <span data-stage-detail>动画与图表使用同一组模型参数</span>
            </div>
          </div>

          <div class="gm-phase-buttons gm-ui-only" aria-label="关键阶段">
            ${spec.phases.map((phase, index) => `<button type="button" data-phase="${index / (spec.phases.length - 1)}">${escapeHtml(phase)}</button>`).join('')}
          </div>
          <label class="gm-scrubber gm-ui-only">
            <span>过程时间轴</span>
            <input type="range" min="0" max="1000" step="1" value="0" data-scrubber />
          </label>

          <figure class="gm-chart-card">
            <figcaption>
              <div><p class="gm-kicker">定量图景</p><h2>${escapeHtml(spec.chart.title)}</h2></div>
              <p>${escapeHtml(chartCaption(spec))}</p>
            </figcaption>
            <svg data-model-chart viewBox="0 0 620 290" role="img" aria-label="${escapeHtml(spec.chart.title)}"></svg>
          </figure>
        </div>
      </section>

      <section class="gm-notes" aria-label="模型说明">
        <article class="gm-note gm-note--model">
          <p class="gm-kicker">MODEL ASSUMPTION</p>
          <h2>这张网页计算了什么</h2>
          <p>${escapeHtml(spec.modelNote)}</p>
        </article>
        <article class="gm-note gm-note--reading">
          <p class="gm-kicker">READ THE MODEL</p>
          <h2>阅读时抓住三件事</h2>
          <ol>
            <li>先分清原题参数与标准化输入。</li>
            <li>再看动画、指标与图表是否同步变化。</li>
            <li>最后用边界测试判断公式何时失效。</li>
          </ol>
        </article>
      </section>

      <section class="gm-card gm-tests gm-ui-only" aria-labelledby="gm-tests-title">
        <div class="gm-card__heading">
          <div><p class="gm-kicker">MODEL CHECKS</p><h2 id="gm-tests-title">原题回归与否决性测试</h2></div>
          <span data-test-summary>正在核对</span>
        </div>
        <ul data-model-tests></ul>
      </section>
    </main>
  `;
}

function setupCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(1, Math.round(rect.width * ratio));
  const height = Math.max(1, Math.round(rect.height * ratio));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  const context = canvas.getContext('2d');
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { context, width: rect.width, height: rect.height };
}

function roundRect(context, x, y, width, height, radius, fill, stroke = '') {
  const r = Math.min(radius, width / 2, height / 2);
  context.beginPath();
  context.roundRect(x, y, width, height, r);
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
  if (label) { context.font = '700 12px sans-serif'; context.fillText(label, x2 + 8, y2 + 4); }
  context.restore();
}

function drawBackground(context, width, height) {
  const gradient = context.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, '#f8fbff');
  gradient.addColorStop(1, '#e7f1fa');
  context.fillStyle = gradient;
  context.fillRect(0, 0, width, height);
  context.strokeStyle = 'rgba(11, 99, 199, 0.09)';
  context.lineWidth = 1;
  for (let x = 0; x <= width; x += 36) { context.beginPath(); context.moveTo(x, 0); context.lineTo(x, height); context.stroke(); }
  for (let y = 0; y <= height; y += 36) { context.beginPath(); context.moveTo(0, y); context.lineTo(width, y); context.stroke(); }
}

function drawBall(context, x, y, radius, color = '#0b63c7') {
  const gradient = context.createRadialGradient(x - radius * .35, y - radius * .4, 2, x, y, radius);
  gradient.addColorStop(0, '#fff'); gradient.addColorStop(.3, '#bfe1ff'); gradient.addColorStop(1, color);
  context.fillStyle = gradient;
  context.shadowColor = 'rgba(16,32,51,.2)'; context.shadowBlur = 12;
  context.beginPath(); context.arc(x, y, radius, 0, Math.PI * 2); context.fill();
  context.shadowBlur = 0;
}

function drawAirbag(context, width, height, result, _input, phase) {
  const split = width * .33;
  context.fillStyle = 'rgba(255,255,255,.72)'; context.fillRect(0, 0, split, height);
  context.strokeStyle = '#cad7e5'; context.beginPath(); context.moveTo(split, 0); context.lineTo(split, height); context.stroke();

  const angle = Math.atan(result.tanTheta);
  const baseY = height * .72;
  const rampLength = Math.min(split * .72, 150);
  const x0 = split * .12;
  context.strokeStyle = '#49657f'; context.lineWidth = 5; context.lineCap = 'round';
  context.beginPath(); context.moveTo(x0, baseY); context.lineTo(x0 + rampLength * Math.cos(angle), baseY - rampLength * Math.sin(angle)); context.stroke();
  const trigger = phase > .25;
  const bx = x0 + rampLength * (.38 + .28 * Math.min(phase / .3, 1)) * Math.cos(angle);
  const by = baseY - rampLength * (.38 + .28 * Math.min(phase / .3, 1)) * Math.sin(angle) - 13;
  drawBall(context, bx, by, 13, trigger ? '#f0a11b' : '#0b63c7');
  context.fillStyle = '#102033'; context.font = '800 13px sans-serif'; context.fillText(trigger ? '锁止触发' : '惯性球待机', x0, 36);
  context.font = '600 12px sans-serif'; context.fillStyle = '#5b6b7d'; context.fillText(`θ = ${formatNumber(result.theta, 1)}°`, x0, 57);

  const areaX = split + 24;
  const floorY = height * .79;
  context.strokeStyle = '#334e68'; context.lineWidth = 4; context.beginPath(); context.moveTo(areaX, floorY); context.lineTo(width - 24, floorY); context.stroke();
  const bagCenter = areaX + (width - areaX) * .57;
  const contactStart = .28;
  const contactEnd = .72;
  let ballY;
  let compression = 0;
  if (phase < contactStart) {
    const u = phase / contactStart;
    ballY = 55 + (floorY - 76 - 55) * u * u;
  } else if (phase <= contactEnd) {
    const u = (phase - contactStart) / (contactEnd - contactStart);
    compression = Math.sin(Math.PI * u);
    ballY = floorY - 76 + 25 * compression;
  } else if (result.reboundSpeed > 0) {
    const u = (phase - contactEnd) / (1 - contactEnd);
    ballY = floorY - 76 - Math.sin(Math.PI * u / 2) * height * .34;
  } else {
    ballY = floorY - 56;
    compression = .6;
  }
  context.fillStyle = '#dbeafe';
  context.beginPath(); context.ellipse(bagCenter, floorY - 20 + 12 * compression, 92 + 16 * compression, 42 - 16 * compression, 0, Math.PI, 0); context.fill();
  context.strokeStyle = '#0b63c7'; context.lineWidth = 5; context.stroke();
  drawBall(context, bagCenter, ballY, 31, '#165ea8');
  if (phase >= contactStart && phase <= contactEnd) arrow(context, bagCenter + 42, ballY + 12, bagCenter + 42, ballY - 44, '#c46d08', 'F');
  context.fillStyle = '#102033'; context.font = '800 13px sans-serif'; context.fillText('气囊冲量检验', areaX, 36);
  context.font = '600 12px sans-serif'; context.fillStyle = '#5b6b7d';
  context.fillText(`I = ${formatNumber(result.forceImpulse, 0)} N·s`, areaX, 57);
  context.fillText(result.reboundSpeed > 0 ? `碰后向上 ${formatNumber(result.reboundSpeed, 2)} m/s` : '当前冲量不足以反弹', areaX, 76);
}

function drawRubberBall(context, width, height, result, _input, phase) {
  const gateY = height * .38;
  const padY = height * .78;
  const x = width * .5;
  context.strokeStyle = '#8ba0b5'; context.lineWidth = 4;
  context.beginPath(); context.moveTo(x - 85, gateY); context.lineTo(x - 30, gateY); context.moveTo(x + 30, gateY); context.lineTo(x + 85, gateY); context.stroke();
  roundRect(context, x - 98, gateY - 16, 24, 32, 7, '#102033');
  roundRect(context, x + 74, gateY - 16, 24, 32, 7, '#102033');
  context.strokeStyle = '#f0a11b'; context.lineWidth = 2; context.setLineDash([6, 5]); context.beginPath(); context.moveTo(x - 72, gateY); context.lineTo(x + 72, gateY); context.stroke(); context.setLineDash([]);
  roundRect(context, x - 115, padY, 230, 36, 12, '#254f74');
  for (let i = -90; i <= 90; i += 24) { context.strokeStyle = '#8ec5f4'; context.lineWidth = 2; context.beginPath(); context.moveTo(x + i, padY + 7); context.lineTo(x + i + 12, padY + 29); context.stroke(); }

  let y;
  let label;
  if (phase < .45) { const u = phase / .45; y = 50 + (padY - 26 - 50) * u * u; label = u < .62 ? '下落' : '向下通过光电门'; }
  else if (phase < .58) { const u = (phase - .45) / .13; y = padY - 26 + 9 * Math.sin(Math.PI * u); label = '橡胶形变与能量转移'; }
  else { const u = (phase - .58) / .42; y = padY - 26 - Math.sin(Math.PI * u / 2) * height * .54; label = u > .58 ? '向上通过光电门' : '反弹'; }
  drawBall(context, x, y, 25);
  const speed = phase < .5 ? result.downSpeed : result.upSpeed;
  const direction = phase < .5 ? 1 : -1;
  arrow(context, x + 40, y - 18 * direction, x + 40, y + direction * (24 + 28 * clamp(speed / 2, 0, 1)), direction > 0 ? '#c46d08' : '#0b63c7', 'v');
  context.fillStyle = '#102033'; context.font = '800 14px sans-serif'; context.fillText(label, 22, 34);
  context.font = '600 12px sans-serif'; context.fillStyle = '#5b6b7d'; context.fillText(`光电门只记录遮光时间；当前 v=${formatNumber(speed, 3)} m/s`, 22, 56);
}

function harvesterVisualState(input, phase) {
  const displacement = input.amplitude * Math.sin(2 * Math.PI * phase);
  const speed = 2 * Math.PI * input.frequency * input.amplitude * Math.cos(2 * Math.PI * phase);
  const arrowDelta = speed > .005 ? -65 : speed < -.005 ? 65 : 0;
  const direction = speed > .005
    ? '相对上升 · 逆时针'
    : speed < -.005
      ? '相对下降 · 顺时针'
      : '瞬时速度为零';
  return { displacement, speed, arrowDelta, direction };
}

function drawHarvester(context, width, height, _result, input, phase) {
  const centerX = width * .52;
  const centerY = height * .5;
  const coilW = Math.min(width * .42, 250);
  const coilH = Math.min(height * .64, 250);
  const visual = harvesterVisualState(input, phase);
  const { displacement, speed } = visual;
  const normalized = displacement / (input.side / 2);
  const shift = -normalized * coilH * .35;

  context.save();
  context.beginPath(); context.rect(centerX - coilW / 2, centerY - coilH / 2, coilW, coilH); context.clip();
  context.fillStyle = '#dbeafe'; context.fillRect(centerX - coilW / 2, centerY - coilH / 2 + shift, coilW, coilH / 2);
  context.fillStyle = '#fee2e2'; context.fillRect(centerX - coilW / 2, centerY + shift, coilW, coilH / 2);
  context.fillStyle = 'rgba(255,255,255,.55)';
  for (let x = centerX - coilW / 2 + 15; x < centerX + coilW / 2; x += 30) {
    for (let y = centerY - coilH / 2 + 15; y < centerY + coilH / 2; y += 30) {
      const outward = y < centerY + shift;
      context.beginPath(); context.arc(x, y, 3, 0, Math.PI * 2); context.fill();
      if (!outward) { context.strokeStyle = 'rgba(150,35,35,.55)'; context.beginPath(); context.moveTo(x - 4, y - 4); context.lineTo(x + 4, y + 4); context.moveTo(x + 4, y - 4); context.lineTo(x - 4, y + 4); context.stroke(); }
    }
  }
  context.restore();
  context.strokeStyle = '#0b63c7'; context.lineWidth = 8; context.strokeRect(centerX - coilW / 2, centerY - coilH / 2, coilW, coilH);
  context.strokeStyle = '#f0a11b'; context.lineWidth = 4; context.beginPath(); context.moveTo(centerX - coilW / 2, centerY + shift); context.lineTo(centerX + coilW / 2, centerY + shift); context.stroke();
  if (visual.arrowDelta !== 0) arrow(context, centerX + coilW / 2 + 35, centerY + 25, centerX + coilW / 2 + 35, centerY + 25 + visual.arrowDelta, '#c46d08', speed > 0 ? '上升' : '下降');

  const flux = 2 * input.field * input.side * displacement;
  const emf = -2 * input.field * input.side * speed;
  roundRect(context, 20, 26, Math.min(230, width * .34), 112, 12, 'rgba(255,255,255,.9)', '#cad7e5');
  context.fillStyle = '#102033'; context.font = '800 13px sans-serif'; context.fillText('单分界 · 反向等强磁场', 36, 52);
  context.font = '600 12px sans-serif'; context.fillStyle = '#526579';
  context.fillText(`Φ = ${formatNumber(flux, 4)} Wb`, 36, 76);
  context.fillText(`ε = ${formatNumber(emf, 3)} V`, 36, 98);
  context.fillStyle = Math.abs(speed) > .005 ? '#0b63c7' : '#66788a'; context.fillText(visual.direction, 36, 121);
  context.fillStyle = '#526579'; context.font = '600 11px sans-serif'; context.fillText('方向沿用原题图示约定', 20, height - 20);
}

function drawMissingSceneError(context, width, height, spec) {
  context.fillStyle = 'rgba(255,255,255,.94)';
  context.fillRect(18, 18, width - 36, height - 36);
  context.strokeStyle = '#b42318';
  context.lineWidth = 3;
  context.strokeRect(18, 18, width - 36, height - 36);
  context.fillStyle = '#8f251d';
  context.font = '900 20px "Avenir Next", "PingFang SC", sans-serif';
  context.fillText('专用物理场景尚未接入', 42, 68);
  context.fillStyle = '#40566d';
  context.font = '700 13px "Avenir Next", "PingFang SC", sans-serif';
  context.fillText(`${spec.id} · scene: ${spec.scene}`, 42, 96);
  context.fillText('页面已停止运行，请补齐对应场景模块后重新生成。', 42, 124);
}

function drawScene(canvas, spec, result, phase) {
  const { context, width, height } = setupCanvas(canvas);
  drawBackground(context, width, height);
  const input = result.input;
  let drawn = true;
  if (spec.scene === 'airbag') drawAirbag(context, width, height, result, input, phase);
  else if (spec.scene === 'rubberBall') drawRubberBall(context, width, height, result, input, phase);
  else if (spec.scene === 'harvester') drawHarvester(context, width, height, result, input, phase);
  else if (MECHANICS_SCENES.includes(spec.scene)) drawn = drawMechanicsScene(context, width, height, spec.scene, result, input, phase);
  else if (SENSOR_SCENES.includes(spec.scene)) drawn = drawSensorScene(context, width, height, spec, result, input, phase);
  else if (WAVE_SCENES.includes(spec.scene)) drawn = drawWaveScene(context, width, height, spec, result, input, phase);
  else drawn = false;

  if (!drawn) {
    drawMissingSceneError(context, width, height, spec);
    throw new Error(`专用物理场景未实现：${spec.id} / ${spec.scene}`);
  }
}

function chartState(spec, result, phase) {
  const input = result.input;
  let points = result.chart;
  if (spec.scene === 'ropeWave') {
    const currentTime = phase * result.period;
    points = result.chart.map((point) => ({
      ...point,
      y: input.amplitude * Math.cos(2 * Math.PI * (point.x / result.wavelength - currentTime / result.period))
    }));
  } else if (spec.scene === 'travelingWave') {
    const currentTime = input.probeTime + phase * result.period;
    points = result.chart.map((point) => ({
      ...point,
      y: input.amplitude * Math.sin(2 * Math.PI * (point.x - input.waveSpeed * currentTime) / input.wavelength)
    }));
  }
  const showCursor = spec.chart.cursorMode !== 'none';
  const cursorX = showCursor ? spec.chart.cursorValue(phase, result, input) : undefined;
  return { points, cursorX, showCursor: showCursor && Number.isFinite(cursorX) };
}

function chartMarkup(spec, points, cursorX, showCursor) {
  const width = 620; const height = 290;
  const hasSecondary = points.some((point) => Number.isFinite(point.y2));
  const independentSecondary = hasSecondary && Boolean(spec.chart.secondaryYLabel);
  const left = 68; const right = independentSecondary ? 72 : 26; const top = hasSecondary ? 42 : 22; const bottom = 52;
  const primaryValues = points.map((point) => point.y).filter(Number.isFinite);
  const secondaryValues = points.map((point) => point.y2).filter(Number.isFinite);
  const xs = points.map((point) => point.x).filter(Number.isFinite);
  const xMin = Math.min(...xs); const xMaxRaw = Math.max(...xs); const xMax = xMaxRaw === xMin ? xMin + 1 : xMaxRaw;
  const includeZero = spec.chart.includeZero !== false;
  const bounds = (values) => {
    let minimum = values.length ? Math.min(...values) : 0;
    let maximum = values.length ? Math.max(...values) : 1;
    if (includeZero) {
      if (minimum > 0) minimum = 0;
      if (maximum < 0) maximum = 0;
    } else {
      const spread = maximum - minimum || Math.max(Math.abs(maximum) * .1, 1e-6);
      minimum -= spread * .08;
      maximum += spread * .08;
    }
    if (maximum === minimum) maximum = minimum + Math.max(Math.abs(minimum) * .1, 1);
    return { minimum, maximum };
  };
  const primaryBounds = bounds(independentSecondary ? primaryValues : [...primaryValues, ...secondaryValues]);
  const secondaryBounds = independentSecondary ? bounds(secondaryValues) : primaryBounds;
  const plotW = width - left - right; const plotH = height - top - bottom;
  const px = (x) => left + (x - xMin) / (xMax - xMin) * plotW;
  const pyPrimary = (value) => top + (primaryBounds.maximum - value) / (primaryBounds.maximum - primaryBounds.minimum) * plotH;
  const pySecondary = (value) => top + (secondaryBounds.maximum - value) / (secondaryBounds.maximum - secondaryBounds.minimum) * plotH;
  const line = (key, projectY) => points.filter((point) => Number.isFinite(point[key])).map((point) => `${px(point.x).toFixed(1)},${projectY(point[key]).toFixed(1)}`).join(' ');
  const cursor = showCursor
    ? points[points.reduce((best, point, index) => Math.abs(point.x - cursorX) < Math.abs(points[best].x - cursorX) ? index : best, 0)]
    : null;
  const baselineY = includeZero && primaryBounds.minimum <= 0 && primaryBounds.maximum >= 0
    ? pyPrimary(0)
    : height - bottom;
  const primaryLegend = spec.chart.primaryLabel || spec.chart.yLabel;
  return `
    <title>${escapeHtml(spec.chart.title)}</title>
    <desc>横轴${escapeHtml(spec.chart.xLabel)}，左轴${escapeHtml(spec.chart.yLabel)}${independentSecondary ? `，右轴${escapeHtml(spec.chart.secondaryYLabel)}` : ''}${showCursor ? '；竖线标出当前观察点。' : '。'}</desc>
    ${hasSecondary ? `<g class="gm-chart-legend">
      <line class="gm-chart-line" x1="${left}" y1="15" x2="${left + 20}" y2="15" />
      <text x="${left + 28}" y="19">${escapeHtml(primaryLegend)}</text>
      <line class="gm-chart-line gm-chart-line--secondary" x1="${left + 230}" y1="15" x2="${left + 250}" y2="15" />
      <text x="${left + 258}" y="19">${escapeHtml(spec.chart.secondaryLabel)}</text>
    </g>` : ''}
    <g class="gm-chart-grid">
      <line x1="${left}" y1="${top}" x2="${left}" y2="${height - bottom}" />
      <line x1="${left}" y1="${baselineY}" x2="${width - right}" y2="${baselineY}" />
      <line x1="${left}" y1="${top + plotH / 2}" x2="${width - right}" y2="${top + plotH / 2}" />
      <line x1="${left + plotW / 2}" y1="${top}" x2="${left + plotW / 2}" y2="${height - bottom}" />
    </g>
    <polyline class="gm-chart-line" points="${line('y', pyPrimary)}" />
    ${hasSecondary ? `<polyline class="gm-chart-line gm-chart-line--secondary" points="${line('y2', pySecondary)}" />` : ''}
    ${independentSecondary ? `<line class="gm-chart-axis--secondary" x1="${width - right}" y1="${top}" x2="${width - right}" y2="${height - bottom}" />` : ''}
    ${showCursor && cursor ? `<line class="gm-chart-cursor-line" x1="${px(cursor.x)}" y1="${top}" x2="${px(cursor.x)}" y2="${height - bottom}" />
    <circle class="gm-chart-dot" cx="${px(cursor.x)}" cy="${pyPrimary(cursor.y)}" r="6" />
    ${hasSecondary && Number.isFinite(cursor.y2) ? `<circle class="gm-chart-dot gm-chart-dot--secondary" cx="${px(cursor.x)}" cy="${pySecondary(cursor.y2)}" r="5" />` : ''}` : ''}
    <g class="gm-chart-labels">
      <text x="${left}" y="${height - 20}">${formatNumber(xMin, 2)}</text>
      <text x="${width - right}" y="${height - 20}" text-anchor="end">${formatNumber(xMax, 2)}</text>
      <text x="${width - right}" y="${height - 3}" text-anchor="end">${escapeHtml(spec.chart.xLabel)}</text>
      <text x="${left - 10}" y="${top + 5}" text-anchor="end">${formatNumber(primaryBounds.maximum, 2)}</text>
      <text x="${left - 10}" y="${height - bottom + 5}" text-anchor="end">${formatNumber(primaryBounds.minimum, 2)}</text>
      <text transform="translate(18 ${top + plotH / 2}) rotate(-90)" text-anchor="middle">${escapeHtml(spec.chart.yLabel)}</text>
    </g>
    ${independentSecondary ? `<g class="gm-chart-labels gm-chart-labels--secondary">
      <text x="${width - right + 10}" y="${top + 5}">${formatNumber(secondaryBounds.maximum, 2)}</text>
      <text x="${width - right + 10}" y="${height - bottom + 5}">${formatNumber(secondaryBounds.minimum, 2)}</text>
      <text transform="translate(${width - 13} ${top + plotH / 2}) rotate(90)" text-anchor="middle">${escapeHtml(spec.chart.secondaryYLabel)}</text>
    </g>` : ''}`;
}

function mount() {
  const modelId = document.body.dataset.modelId;
  const spec = getGaokaoModelSpec(modelId);
  if (!spec) {
    document.body.innerHTML = '<main class="gm-boot-error"><h1>模型未登记</h1><p>请返回高考真题模拟目录。</p></main>';
    return;
  }

  document.title = `${spec.title}｜高考真题模拟｜育才物理创新实验室`;
  document.body.innerHTML = pageMarkup(spec);
  const form = document.querySelector('[data-model-form]');
  const canvas = document.querySelector('[data-model-canvas]');
  const chart = document.querySelector('[data-model-chart]');
  const error = document.querySelector('[data-error]');
  const warning = document.querySelector('[data-model-warning]');
  const scrubber = document.querySelector('[data-scrubber]');
  const play = document.querySelector('[data-play]');
  const book = document.querySelector('[data-toggle-book]');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let result = calculateGaokaoModel(spec.id);
  let phase = reducedMotion ? .5 : 0;
  let paused = reducedMotion;
  let animationStart = performance.now() - phase * 7200;
  let frame = null;
  let hasModelWarning = false;

  const formValues = () => Object.fromEntries(new FormData(form).entries());

  const updateMetrics = () => {
    for (const item of spec.metrics) {
      const element = document.querySelector(`[data-metric="${item.key}"]`);
      const transform = spec.metricTransforms?.[item.key];
      const value = transform ? transform(result[item.key], result.input, result) : result[item.key];
      element.textContent = formatNumber(value, item.digits);
    }
  };

  const renderFrame = (nextPhase) => {
    if (!result?.ok) return;
    phase = clamp(nextPhase, 0, 1);
    scrubber.value = String(Math.round(phase * 1000));
    const phaseIndex = Math.min(spec.phases.length - 1, Math.floor(phase * spec.phases.length));
    const label = spec.phases[phaseIndex];
    document.querySelector('[data-phase-output]').textContent = label;
    document.querySelector('[data-stage-label]').textContent = label;
    document.querySelector('[data-stage-detail]').textContent = `过程进度 ${Math.round(phase * 100)}% · 图景与曲线同步`;
    drawScene(canvas, spec, result, phase);
    const chartView = chartState(spec, result, phase);
    chart.innerHTML = chartMarkup(spec, chartView.points, chartView.cursorX, chartView.showCursor);
  };

  const update = () => {
    const values = formValues();
    const validation = validateParameterValues(spec, values);
    result = validation.ok ? calculateGaokaoModel(spec.id, values) : validation;
    document.querySelectorAll('[data-range-for]').forEach((range) => {
      const input = document.getElementById(range.dataset.rangeFor);
      range.value = String(clamp(Number(input.value), Number(range.min), Number(range.max)));
      input.closest('.gm-field')?.classList.toggle('is-adjusted', input.value !== input.dataset.original);
    });
    if (!result.ok) {
      error.hidden = false; error.textContent = result.error;
      warning.hidden = true; warning.textContent = '';
      hasModelWarning = false;
      document.querySelector('[data-stage-detail]').textContent = '请修正参数后继续';
      document.querySelectorAll('[data-metric]').forEach((item) => { item.textContent = '—'; });
      chart.replaceChildren();
      const { context, width, height } = setupCanvas(canvas);
      drawBackground(context, width, height);
      context.fillStyle = '#8f251d'; context.font = '800 15px sans-serif'; context.fillText('当前参数未通过模型前置检查', 24, 42);
      book.disabled = true;
      if (document.body.classList.contains('book-mode')) {
        document.body.classList.remove('book-mode');
        book.textContent = '打开图书视图';
        const url = new URL(location.href);
        url.searchParams.delete('view');
        history.replaceState({}, '', url);
      }
      return;
    }
    error.hidden = true;
    const warningText = Array.isArray(result.warnings)
      ? result.warnings.filter(Boolean).join(' ')
      : String(result.warning || '');
    hasModelWarning = warningText.length > 0;
    warning.hidden = !hasModelWarning;
    warning.textContent = warningText;
    book.disabled = !testsPassed || hasModelWarning;
    if (hasModelWarning && document.body.classList.contains('book-mode')) {
      document.body.classList.remove('book-mode');
      book.textContent = '打开图书视图';
      const url = new URL(location.href);
      url.searchParams.delete('view');
      history.replaceState({}, '', url);
    }
    updateMetrics();
    renderFrame(phase);
  };

  const tests = runGaokaoModelTests(spec.id);
  const testList = document.querySelector('[data-model-tests]');
  testList.innerHTML = tests.map((test) => `
    <li class="${test.pass ? 'is-pass' : 'is-fail'}">
      <span aria-hidden="true">${test.pass ? 'PASS' : 'FAIL'}</span>
      <strong>${escapeHtml(test.name)}</strong>
      <small>${escapeHtml(test.detail)}</small>
    </li>`).join('');
  const testsPassed = tests.every((test) => test.pass);
  const summary = document.querySelector('[data-test-summary]');
  summary.textContent = testsPassed ? `${tests.length} 项全部通过` : `${tests.filter((test) => !test.pass).length} 项未通过`;
  summary.classList.toggle('is-pass', testsPassed);
  book.disabled = !testsPassed;

  const schedule = () => {
    if (paused || frame !== null) return;
    const animate = (now) => {
      if (paused) { frame = null; return; }
      renderFrame(((now - animationStart) % 7200) / 7200);
      frame = window.requestAnimationFrame(animate);
    };
    frame = window.requestAnimationFrame(animate);
  };

  const setPaused = (value) => {
    paused = value;
    play.textContent = paused ? '继续' : '暂停';
    play.setAttribute('aria-pressed', String(paused));
    if (paused && frame !== null) { cancelAnimationFrame(frame); frame = null; }
    if (!paused) { animationStart = performance.now() - phase * 7200; schedule(); }
  };

  form.addEventListener('input', update);
  document.querySelectorAll('[data-range-for]').forEach((range) => range.addEventListener('input', () => {
    const input = document.getElementById(range.dataset.rangeFor);
    input.value = range.value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }));
  document.querySelector('[data-reset]').addEventListener('click', () => {
    spec.parameters.forEach((item) => { form.elements.namedItem(item.key).value = String(item.value); });
    phase = 0; update();
  });
  document.querySelector('[data-step]').addEventListener('click', () => { setPaused(true); renderFrame(phase + .04); });
  document.querySelector('[data-rewind]').addEventListener('click', () => { setPaused(true); renderFrame(0); });
  play.addEventListener('click', () => setPaused(!paused));
  scrubber.addEventListener('input', () => { setPaused(true); renderFrame(Number(scrubber.value) / 1000); });
  document.querySelectorAll('[data-phase]').forEach((button) => button.addEventListener('click', () => { setPaused(true); renderFrame(Number(button.dataset.phase)); }));
  document.querySelector('[data-scroll-model]').addEventListener('click', () => document.getElementById('model-workspace').scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth' }));
  book.addEventListener('click', () => {
    if (!testsPassed || !result?.ok || hasModelWarning) return;
    const enabled = !document.body.classList.contains('book-mode');
    if (enabled) {
      setPaused(true);
      renderFrame(spec.bookPhase);
    }
    document.body.classList.toggle('book-mode', enabled);
    book.textContent = enabled ? '退出图书视图' : '打开图书视图';
    const url = new URL(location.href);
    if (enabled) url.searchParams.set('view', 'book'); else url.searchParams.delete('view');
    history.replaceState({}, '', url);
    requestAnimationFrame(() => renderFrame(phase));
  });
  document.addEventListener('keydown', (event) => {
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement) return;
    if (event.code === 'Space') { event.preventDefault(); setPaused(!paused); }
    if (event.code === 'ArrowRight') { event.preventDefault(); setPaused(true); renderFrame(phase + .025); }
    if (event.code === 'ArrowLeft') { event.preventDefault(); setPaused(true); renderFrame(phase - .025); }
    if (event.code === 'Home') { event.preventDefault(); setPaused(true); renderFrame(0); }
  });
  window.addEventListener('resize', () => renderFrame(phase), { passive: true });

  update();
  if (new URL(location.href).searchParams.get('view') === 'book' && testsPassed && !hasModelWarning) {
    setPaused(true);
    renderFrame(spec.bookPhase);
    document.body.classList.add('book-mode');
    book.textContent = '退出图书视图';
  }
  setPaused(paused);
  if (!paused) schedule();
  document.documentElement.dataset.gaokaoModelReady = 'true';
}

export function runModelPageSemanticTests() {
  const tests = [];
  const record = (name, check) => {
    try { tests.push({ name, pass: Boolean(check()) }); }
    catch (error) { tests.push({ name, pass: false, detail: error instanceof Error ? error.message : String(error) }); }
  };
  record('大数、未解锁与无穷状态均有稳定格式', () => formatNumber(1500000, 0) === '1.50e+6' && formatNumber(Number.NaN) === '未解锁' && formatNumber(Number.POSITIVE_INFINITY) === '∞');
  record('采能器下降映射为画布向下箭头与顺时针', () => {
    const state = harvesterVisualState({ amplitude: .03, frequency: 2 }, .5);
    return state.speed < 0 && state.arrowDelta > 0 && state.direction.includes('下降') && state.direction.includes('顺时针');
  });
  record('数字输入越界时显式否决', () => {
    const spec = { parameters: [{ key: 'x', label: '测试量', unit: 'm', minimum: 0, maximum: 1, value: .5 }] };
    return !validateParameterValues(spec, { x: 2 }).ok && validateParameterValues(spec, { x: .5 }).ok;
  });
  return tests;
}

if (typeof document !== 'undefined') mount();
