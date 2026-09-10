/* 自动生成，请修改 src/model.js 或 src/app.js 后运行 npm run build。 */
(() => {
  "use strict";

const LIMITS = Object.freeze({
  massMin: 0.1,
  massMax: 10,
  speedMin: -10,
  speedMax: 10,
  tolerance: 1e-9,
});

const COLLISION_TYPES = Object.freeze({
  ELASTIC: "elastic",
  INELASTIC: "perfectly-inelastic",
});

function finiteNumber(value, label) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    throw new TypeError(`${label}必须是有限数值`);
  }
  return number;
}

function validateInputs(input) {
  const m1 = finiteNumber(input.m1, "m₁");
  const m2 = finiteNumber(input.m2, "m₂");
  const u1 = finiteNumber(input.u1, "u₁");
  const u2 = finiteNumber(input.u2, "u₂");
  const type = input.type;

  if (m1 < LIMITS.massMin || m1 > LIMITS.massMax) {
    throw new RangeError(`m₁应在${LIMITS.massMin}—${LIMITS.massMax} kg之间`);
  }
  if (m2 < LIMITS.massMin || m2 > LIMITS.massMax) {
    throw new RangeError(`m₂应在${LIMITS.massMin}—${LIMITS.massMax} kg之间`);
  }
  if (u1 < LIMITS.speedMin || u1 > LIMITS.speedMax) {
    throw new RangeError(`u₁应在${LIMITS.speedMin}—${LIMITS.speedMax} m/s之间`);
  }
  if (u2 < LIMITS.speedMin || u2 > LIMITS.speedMax) {
    throw new RangeError(`u₂应在${LIMITS.speedMin}—${LIMITS.speedMax} m/s之间`);
  }
  if (!Object.values(COLLISION_TYPES).includes(type)) {
    throw new RangeError("碰撞类型无效");
  }

  return { m1, m2, u1, u2, type };
}

function solveElasticDirect({ m1, m2, u1, u2 }) {
  const denominator = m1 + m2;
  return {
    v1: ((m1 - m2) * u1 + 2 * m2 * u2) / denominator,
    v2: (2 * m1 * u1 + (m2 - m1) * u2) / denominator,
  };
}

function solveElasticByCenterOfMass({ m1, m2, u1, u2 }) {
  const centerVelocity = (m1 * u1 + m2 * u2) / (m1 + m2);
  return {
    v1: 2 * centerVelocity - u1,
    v2: 2 * centerVelocity - u2,
    centerVelocity,
  };
}

function solvePerfectlyInelastic({ m1, m2, u1, u2 }) {
  const commonVelocity = (m1 * u1 + m2 * u2) / (m1 + m2);
  return { v1: commonVelocity, v2: commonVelocity, commonVelocity };
}

function stateFromVelocities({ m1, m2, velocity1, velocity2 }) {
  const p1 = m1 * velocity1;
  const p2 = m2 * velocity2;
  const totalMomentum = p1 + p2;
  const k1 = 0.5 * m1 * velocity1 ** 2;
  const k2 = 0.5 * m2 * velocity2 ** 2;
  const totalKineticEnergy = k1 + k2;
  return {
    velocity1,
    velocity2,
    p1,
    p2,
    totalMomentum,
    k1,
    k2,
    totalKineticEnergy,
  };
}

function mixedClose(actual, expected, tolerance = LIMITS.tolerance) {
  const scale = Math.max(1, Math.abs(actual), Math.abs(expected));
  return Math.abs(actual - expected) <= tolerance * scale;
}

function auditCandidate(params, candidate) {
  const input = validateInputs(params);
  const candidateV1 = finiteNumber(candidate.v1, "候选v₁");
  const candidateV2 = finiteNumber(candidate.v2, "候选v₂");
  const before = stateFromVelocities({
    m1: input.m1,
    m2: input.m2,
    velocity1: input.u1,
    velocity2: input.u2,
  });
  const after = stateFromVelocities({
    m1: input.m1,
    m2: input.m2,
    velocity1: candidateV1,
    velocity2: candidateV2,
  });
  const expected =
    input.type === COLLISION_TYPES.ELASTIC
      ? solveElasticByCenterOfMass(input)
      : solvePerfectlyInelastic(input);

  const momentumResidual = after.totalMomentum - before.totalMomentum;
  const kineticEnergyChange =
    after.totalKineticEnergy - before.totalKineticEnergy;
  const v1Residual = candidateV1 - expected.v1;
  const v2Residual = candidateV2 - expected.v2;
  const momentumPass = mixedClose(
    after.totalMomentum,
    before.totalMomentum,
  );
  const expectedVelocityPass =
    mixedClose(candidateV1, expected.v1) &&
    mixedClose(candidateV2, expected.v2);
  const energyPass =
    input.type === COLLISION_TYPES.ELASTIC
      ? mixedClose(
          after.totalKineticEnergy,
          before.totalKineticEnergy,
        )
      : after.totalKineticEnergy <=
          before.totalKineticEnergy + LIMITS.tolerance &&
        mixedClose(candidateV1, candidateV2);

  return {
    pass: momentumPass && energyPass && expectedVelocityPass,
    momentumPass,
    energyPass,
    expectedVelocityPass,
    momentumResidual,
    kineticEnergyChange,
    v1Residual,
    v2Residual,
    expected,
  };
}

function solveCollision(rawInput) {
  const input = validateInputs(rawInput);
  const before = stateFromVelocities({
    m1: input.m1,
    m2: input.m2,
    velocity1: input.u1,
    velocity2: input.u2,
  });
  const direct =
    input.type === COLLISION_TYPES.ELASTIC
      ? solveElasticDirect(input)
      : solvePerfectlyInelastic(input);
  const after = stateFromVelocities({
    m1: input.m1,
    m2: input.m2,
    velocity1: direct.v1,
    velocity2: direct.v2,
  });
  const independent =
    input.type === COLLISION_TYPES.ELASTIC
      ? solveElasticByCenterOfMass(input)
      : solvePerfectlyInelastic(input);
  const audit = auditCandidate(input, direct);
  const collisionPossible = input.u1 > input.u2;

  return {
    input,
    before,
    after,
    direct,
    independent,
    audit,
    collisionPossible,
    eventMessage: collisionPossible
      ? "当前初态会发生追碰，可以播放事件示意。"
      : "物体1在左、物体2在右时，u₁≤u₂，当前初态不会在未来发生追碰。",
    identity: "解析模型输出（非实测数据）",
  };
}

function formatNumber(value, digits = 4) {
  if (!Number.isFinite(value)) return "—";
  if (Math.abs(value) < 10 ** -(digits + 1)) return "0";
  return Number(value.toFixed(digits)).toString();
}


const elements = {
  type: document.querySelector("#collision-type"),
  m1: document.querySelector("#m1"),
  m2: document.querySelector("#m2"),
  u1: document.querySelector("#u1"),
  u2: document.querySelector("#u2"),
  predictionV1: document.querySelector("#prediction-v1"),
  predictionV2: document.querySelector("#prediction-v2"),
  reveal: document.querySelector("#reveal-button"),
  reset: document.querySelector("#reset-button"),
  play: document.querySelector("#play-button"),
  inputError: document.querySelector("#input-error"),
  track: document.querySelector("#track"),
  objectOneMass: document.querySelector("#object-one-mass"),
  objectTwoMass: document.querySelector("#object-two-mass"),
  velocityOne: document.querySelector("#velocity-one"),
  velocityTwo: document.querySelector("#velocity-two"),
  collisionMark: document.querySelector("#collision-mark"),
  eventMessage: document.querySelector("#event-message"),
  predictionResult: document.querySelector("#prediction-result"),
  lockedResults: document.querySelector("#locked-results"),
  resultsContent: document.querySelector("#results-content"),
  dataTableBody: document.querySelector("#data-table-body"),
  momentumChart: document.querySelector("#momentum-chart"),
  energyChart: document.querySelector("#energy-chart"),
  auditBadge: document.querySelector("#audit-badge"),
  momentumResidual: document.querySelector("#momentum-residual"),
  energyChange: document.querySelector("#energy-change"),
  solverDifference: document.querySelector("#solver-difference"),
  manualPBefore: document.querySelector("#manual-p-before"),
  manualPAfter: document.querySelector("#manual-p-after"),
  manualKBefore: document.querySelector("#manual-k-before"),
  manualKAfter: document.querySelector("#manual-k-after"),
  checkManual: document.querySelector("#check-manual-button"),
  manualResult: document.querySelector("#manual-result"),
  phaseTabs: [...document.querySelectorAll(".phase-tab")],
  presetButtons: [...document.querySelectorAll("[data-preset]")],
};

const presets = {
  exchange: {
    type: COLLISION_TYPES.ELASTIC,
    m1: 1,
    m2: 1,
    u1: 4,
    u2: 0,
  },
  "zero-momentum": {
    type: COLLISION_TYPES.ELASTIC,
    m1: 2,
    m2: 1,
    u1: 1,
    u2: -2,
  },
  stick: {
    type: COLLISION_TYPES.INELASTIC,
    m1: 1,
    m2: 1,
    u1: 4,
    u2: 0,
  },
  "no-collision": {
    type: COLLISION_TYPES.ELASTIC,
    m1: 1,
    m2: 1.5,
    u1: 1,
    u2: 2,
  },
};

let result = null;
let revealed = false;
let phase = "before";
let playToken = 0;

function readInput() {
  return {
    type: elements.type.value,
    m1: Number(elements.m1.value),
    m2: Number(elements.m2.value),
    u1: Number(elements.u1.value),
    u2: Number(elements.u2.value),
  };
}

function setInput(input) {
  elements.type.value = input.type;
  elements.m1.value = input.m1;
  elements.m2.value = input.m2;
  elements.u1.value = input.u1;
  elements.u2.value = input.u2;
}

function clearManualInputs() {
  for (const input of [
    elements.manualPBefore,
    elements.manualPAfter,
    elements.manualKBefore,
    elements.manualKAfter,
  ]) {
    input.value = "";
  }
  elements.manualResult.hidden = true;
  elements.manualResult.replaceChildren();
}

function directionOf(value) {
  if (mixedClose(value, 0, 1e-7)) return "zero";
  return value > 0 ? "positive" : "negative";
}

function directionText(value) {
  const direction = directionOf(value);
  if (direction === "zero") return "静止";
  return direction === "positive" ? "→ 向右" : "← 向左";
}

function setPhase(nextPhase) {
  phase = nextPhase;
  elements.track.dataset.phase = phase;
  elements.phaseTabs.forEach((tab) => {
    const active = tab.dataset.phase === phase;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  elements.collisionMark.hidden = phase !== "event";
  renderScene();
}

function currentVelocities() {
  if (!result) return { velocity1: 0, velocity2: 0 };
  if (phase === "before") {
    return {
      velocity1: result.before.velocity1,
      velocity2: result.before.velocity2,
    };
  }
  if (phase === "after" && revealed) {
    return {
      velocity1: result.after.velocity1,
      velocity2: result.after.velocity2,
    };
  }
  return { velocity1: null, velocity2: null };
}

function renderVelocity(element, velocity, label) {
  if (velocity === null) {
    element.textContent = `${label}：接触中`;
    return;
  }
  element.textContent = `${label}：${directionText(velocity)} ${formatNumber(
    velocity,
  )} m/s`;
}

function renderScene() {
  if (!result) return;
  const velocities = currentVelocities();
  elements.objectOneMass.textContent = `${formatNumber(result.input.m1)} kg`;
  elements.objectTwoMass.textContent = `${formatNumber(result.input.m2)} kg`;
  renderVelocity(elements.velocityOne, velocities.velocity1, phase === "after" ? "v₁" : "u₁");
  renderVelocity(elements.velocityTwo, velocities.velocity2, phase === "after" ? "v₂" : "u₂");
  elements.eventMessage.textContent = result.eventMessage;
  if (phase === "event") {
    elements.eventMessage.textContent =
      "碰撞过程只作短时事件示意；页面没有生成真实形变或力—时间曲线。";
  }
}

function cell(text) {
  const element = document.createElement("td");
  element.textContent = text;
  return element;
}

function tableRow(label, state) {
  const row = document.createElement("tr");
  row.append(
    cell(label),
    cell(formatNumber(state.velocity1)),
    cell(formatNumber(state.velocity2)),
    cell(formatNumber(state.p1)),
    cell(formatNumber(state.p2)),
    cell(formatNumber(state.totalMomentum)),
    cell(formatNumber(state.totalKineticEnergy)),
  );
  return row;
}

function signedRow(label, value, maximum) {
  const row = document.createElement("div");
  row.className = "signed-row";
  const name = document.createElement("span");
  name.textContent = label;
  const track = document.createElement("div");
  track.className = "signed-track";
  const bar = document.createElement("div");
  const magnitude = maximum === 0 ? 0 : Math.min(50, (Math.abs(value) / maximum) * 50);
  bar.className = `signed-bar ${value < 0 ? "negative" : "positive"}`;
  bar.style.width = `${magnitude}%`;
  track.append(bar);
  const number = document.createElement("strong");
  number.textContent = formatNumber(value);
  row.append(name, track, number);
  return row;
}

function energyRow(label, value, maximum) {
  const row = document.createElement("div");
  row.className = "energy-row";
  const name = document.createElement("span");
  name.textContent = label;
  const track = document.createElement("div");
  track.className = "energy-track";
  const bar = document.createElement("div");
  bar.className = "energy-bar";
  bar.style.width = `${maximum === 0 ? 0 : Math.min(100, (value / maximum) * 100)}%`;
  track.append(bar);
  const number = document.createElement("strong");
  number.textContent = formatNumber(value);
  row.append(name, track, number);
  return row;
}

function renderCharts() {
  const momentumValues = [
    result.before.p1,
    result.before.p2,
    result.before.totalMomentum,
    result.after.p1,
    result.after.p2,
    result.after.totalMomentum,
  ];
  const maximumMomentum = Math.max(1e-12, ...momentumValues.map(Math.abs));
  elements.momentumChart.replaceChildren(
    signedRow("碰前 p₁", result.before.p1, maximumMomentum),
    signedRow("碰前 p₂", result.before.p2, maximumMomentum),
    signedRow("碰前 P总", result.before.totalMomentum, maximumMomentum),
    signedRow("碰后 p₁", result.after.p1, maximumMomentum),
    signedRow("碰后 p₂", result.after.p2, maximumMomentum),
    signedRow("碰后 P总", result.after.totalMomentum, maximumMomentum),
  );

  const maximumEnergy = Math.max(
    1e-12,
    result.before.totalKineticEnergy,
    result.after.totalKineticEnergy,
  );
  elements.energyChart.replaceChildren(
    energyRow("碰前 K总", result.before.totalKineticEnergy, maximumEnergy),
    energyRow("碰后 K总", result.after.totalKineticEnergy, maximumEnergy),
  );
}

function renderPrediction() {
  const prediction1 = elements.predictionV1.value;
  const prediction2 = elements.predictionV2.value;
  if (!prediction1 || !prediction2) {
    elements.predictionResult.textContent =
      "你没有完成两个方向预测；结果仍已揭示，可返回补选后再次比较。";
    elements.predictionResult.hidden = false;
    return;
  }
  const actual1 = directionOf(result.after.velocity1);
  const actual2 = directionOf(result.after.velocity2);
  const first = prediction1 === actual1;
  const second = prediction2 === actual2;
  elements.predictionResult.textContent =
    `预测比较：物体1${first ? "一致" : "不一致"}；物体2${second ? "一致" : "不一致"}。` +
    "这只比较方向，不代表完整解释已经成立。";
  elements.predictionResult.hidden = false;
}

function renderResults() {
  elements.lockedResults.hidden = true;
  elements.resultsContent.hidden = false;
  elements.dataTableBody.replaceChildren(
    tableRow("碰前", result.before),
    tableRow("碰后", result.after),
  );
  renderCharts();

  elements.momentumResidual.textContent =
    `${formatNumber(result.audit.momentumResidual, 8)} kg·m/s`;
  elements.energyChange.textContent =
    `${formatNumber(result.audit.kineticEnergyChange, 8)} J`;
  const solverDifference = Math.max(
    Math.abs(result.direct.v1 - result.independent.v1),
    Math.abs(result.direct.v2 - result.independent.v2),
  );
  elements.solverDifference.textContent =
    `${formatNumber(solverDifference, 10)} m/s`;
  elements.auditBadge.textContent = result.audit.pass
    ? "解析审计通过"
    : "解析审计不过";
  elements.auditBadge.classList.toggle("pass", result.audit.pass);
  elements.auditBadge.classList.toggle("fail", !result.audit.pass);
  renderPrediction();
}

function hideResults() {
  revealed = false;
  elements.lockedResults.hidden = false;
  elements.resultsContent.hidden = true;
  elements.predictionResult.hidden = true;
  elements.auditBadge.textContent = "等待揭示";
  elements.auditBadge.classList.remove("pass", "fail");
  clearManualInputs();
  setPhase("before");
}

function refresh({ keepReveal = false } = {}) {
  try {
    result = solveCollision(readInput());
    elements.inputError.hidden = true;
    if (!keepReveal) hideResults();
    renderScene();
    if (keepReveal) renderResults();
  } catch (error) {
    result = null;
    elements.inputError.textContent = error.message;
    elements.inputError.hidden = false;
    elements.eventMessage.textContent = "请先修正输入。";
    elements.lockedResults.hidden = false;
    elements.resultsContent.hidden = true;
  }
}

function reveal() {
  refresh({ keepReveal: true });
  if (!result) return;
  revealed = true;
  renderResults();
  setPhase("after");
}

async function play() {
  if (!result) refresh();
  if (!result) return;
  if (!revealed) {
    elements.eventMessage.textContent =
      "请先完成预测并揭示结果，再播放三个状态。";
    return;
  }
  if (!result.collisionPossible) {
    setPhase("before");
    elements.eventMessage.textContent = result.eventMessage;
    return;
  }
  const token = ++playToken;
  elements.play.disabled = true;
  for (const [nextPhase, delay] of [
    ["before", 700],
    ["event", 800],
    ["after", 0],
  ]) {
    if (token !== playToken) break;
    setPhase(nextPhase);
    if (delay) {
      await new Promise((resolve) => window.setTimeout(resolve, delay));
    }
  }
  elements.play.disabled = false;
}

function numericValue(input) {
  const value = Number(input.value);
  return Number.isFinite(value) && input.value.trim() !== "" ? value : null;
}

function manualCheckItem(label, actual, expected) {
  const item = document.createElement("div");
  const pass = actual !== null && mixedClose(actual, expected, 1e-4);
  item.className = `manual-check ${pass ? "pass" : "fail"}`;
  item.textContent =
    actual === null
      ? `${label}：未填写`
      : `${label}：${pass ? "吻合" : "需复查"}`;
  return { item, pass };
}

function checkManual() {
  if (!revealed || !result) {
    elements.manualResult.textContent = "请先揭示当前模型结果。";
    elements.manualResult.hidden = false;
    return;
  }
  const checks = [
    manualCheckItem(
      "碰前P总",
      numericValue(elements.manualPBefore),
      result.before.totalMomentum,
    ),
    manualCheckItem(
      "碰后P总",
      numericValue(elements.manualPAfter),
      result.after.totalMomentum,
    ),
    manualCheckItem(
      "碰前K总",
      numericValue(elements.manualKBefore),
      result.before.totalKineticEnergy,
    ),
    manualCheckItem(
      "碰后K总",
      numericValue(elements.manualKAfter),
      result.after.totalKineticEnergy,
    ),
  ];
  const grid = document.createElement("div");
  grid.className = "manual-checks";
  grid.append(...checks.map((check) => check.item));
  const note = document.createElement("p");
  note.textContent = checks.every((check) => check.pass)
    ? "四项复算均与完整精度模型吻合。请继续解释守恒条件和动能变化。"
    : "至少一项需要检查公式、符号、单位或抄写。页面不判断具体原因。";
  elements.manualResult.replaceChildren(grid, note);
  elements.manualResult.hidden = false;
}

for (const control of [
  elements.type,
  elements.m1,
  elements.m2,
  elements.u1,
  elements.u2,
]) {
  control.addEventListener("input", () => refresh());
}

elements.reveal.addEventListener("click", reveal);
elements.play.addEventListener("click", play);
elements.checkManual.addEventListener("click", checkManual);
elements.reset.addEventListener("click", () => {
  setInput(presets.exchange);
  elements.predictionV1.value = "";
  elements.predictionV2.value = "";
  refresh();
});

elements.phaseTabs.forEach((tab) => {
  tab.addEventListener("click", () => setPhase(tab.dataset.phase));
});

elements.presetButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setInput(presets[button.dataset.preset]);
    elements.predictionV1.value = "";
    elements.predictionV2.value = "";
    refresh();
  });
});

setInput(presets.exchange);
refresh();

})();
