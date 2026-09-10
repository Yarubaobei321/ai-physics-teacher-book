import assert from "node:assert/strict";
import {
  COLLISION_TYPES,
  LIMITS,
  auditCandidate,
  mixedClose,
  solveCollision,
  solveElasticByCenterOfMass,
  solveElasticDirect,
} from "../src/model.js";

const reports = [];

function record(id, description, input, expected, actual, pass) {
  reports.push({ id, description, input, expected, actual, pass });
  assert.equal(pass, true, `${id} failed`);
}

function close(actual, expected, tolerance = LIMITS.tolerance) {
  return mixedClose(actual, expected, tolerance);
}

{
  const input = {
    m1: 1,
    m2: 1,
    u1: 4,
    u2: 0,
    type: COLLISION_TYPES.ELASTIC,
  };
  const result = solveCollision(input);
  record(
    "T1",
    "等质量弹性碰撞交换速度",
    input,
    { v1: 0, v2: 4 },
    result.direct,
    close(result.direct.v1, 0) && close(result.direct.v2, 4),
  );
}

{
  const input = {
    m1: 1,
    m2: 1,
    u1: 4,
    u2: 0,
    type: COLLISION_TYPES.INELASTIC,
  };
  const result = solveCollision(input);
  record(
    "T2",
    "等质量完全非弹性碰撞共同速度与动能损失",
    input,
    { v1: 2, v2: 2, kineticEnergyRatio: 0.5 },
    {
      v1: result.direct.v1,
      v2: result.direct.v2,
      kineticEnergyRatio:
        result.after.totalKineticEnergy /
        result.before.totalKineticEnergy,
    },
    close(result.direct.v1, 2) &&
      close(result.direct.v2, 2) &&
      close(
        result.after.totalKineticEnergy /
          result.before.totalKineticEnergy,
        0.5,
      ),
  );
}

{
  const input = {
    m1: 2,
    m2: 2,
    u1: 3,
    u2: -3,
    type: COLLISION_TYPES.ELASTIC,
  };
  const result = solveCollision(input);
  record(
    "T3",
    "等质量反向运动时交换速度",
    input,
    { v1: -3, v2: 3, totalMomentum: 0 },
    {
      v1: result.direct.v1,
      v2: result.direct.v2,
      totalMomentum: result.after.totalMomentum,
    },
    close(result.direct.v1, -3) &&
      close(result.direct.v2, 3) &&
      close(result.after.totalMomentum, 0),
  );
}

{
  const input = {
    m1: 2,
    m2: 1,
    u1: 1,
    u2: -2,
    type: COLLISION_TYPES.ELASTIC,
  };
  const result = solveCollision(input);
  record(
    "T4",
    "碰前总动量为0时碰后仍为0",
    input,
    { totalMomentumBefore: 0, totalMomentumAfter: 0 },
    {
      totalMomentumBefore: result.before.totalMomentum,
      totalMomentumAfter: result.after.totalMomentum,
    },
    close(result.before.totalMomentum, 0) &&
      close(result.after.totalMomentum, 0),
  );
}

{
  const input = {
    m1: 1,
    m2: 1,
    u1: 1,
    u2: 2,
    type: COLLISION_TYPES.ELASTIC,
  };
  const result = solveCollision(input);
  record(
    "T5",
    "同向且后车速度不大于前车时提示不会追碰",
    input,
    { collisionPossible: false },
    { collisionPossible: result.collisionPossible },
    result.collisionPossible === false,
  );
}

{
  const inputs = [
    {
      m1: LIMITS.massMin,
      m2: LIMITS.massMax,
      u1: LIMITS.speedMax,
      u2: LIMITS.speedMin,
      type: COLLISION_TYPES.ELASTIC,
    },
    {
      m1: LIMITS.massMax,
      m2: LIMITS.massMin,
      u1: LIMITS.speedMax,
      u2: 0,
      type: COLLISION_TYPES.INELASTIC,
    },
  ];
  const actual = inputs.map((input) => solveCollision(input));
  record(
    "T6",
    "允许范围两端无NaN且残差通过",
    inputs,
    { allFinite: true, allAuditPass: true },
    actual.map((item) => ({
      v1: item.direct.v1,
      v2: item.direct.v2,
      auditPass: item.audit.pass,
    })),
    actual.every(
      (item) =>
        Number.isFinite(item.direct.v1) &&
        Number.isFinite(item.direct.v2) &&
        item.audit.pass,
    ),
  );
}

{
  const input = {
    m1: 1.5,
    m2: 2,
    u1: 4,
    u2: -1,
    type: COLLISION_TYPES.ELASTIC,
  };
  const correct = solveElasticDirect(input);
  const injected = { v1: correct.v1 + 0.25, v2: correct.v2 };
  const audit = auditCandidate(input, injected);
  record(
    "T7",
    "故意注入错误末速度时独立审计必须不过",
    { input, injected },
    { pass: false },
    {
      pass: audit.pass,
      momentumResidual: audit.momentumResidual,
      kineticEnergyChange: audit.kineticEnergyChange,
    },
    audit.pass === false,
  );
}

{
  let seed = 20260831;
  const random = () => {
    seed = (1664525 * seed + 1013904223) >>> 0;
    return seed / 2 ** 32;
  };
  let maxVelocityDifference = 0;
  let maxMomentumResidual = 0;
  let maxEnergyResidual = 0;
  for (let index = 0; index < 500; index += 1) {
    const input = {
      m1: 0.1 + random() * 9.9,
      m2: 0.1 + random() * 9.9,
      u1: -10 + random() * 20,
      u2: -10 + random() * 20,
      type: COLLISION_TYPES.ELASTIC,
    };
    const direct = solveElasticDirect(input);
    const independent = solveElasticByCenterOfMass(input);
    const solved = solveCollision(input);
    maxVelocityDifference = Math.max(
      maxVelocityDifference,
      Math.abs(direct.v1 - independent.v1),
      Math.abs(direct.v2 - independent.v2),
    );
    maxMomentumResidual = Math.max(
      maxMomentumResidual,
      Math.abs(solved.audit.momentumResidual),
    );
    maxEnergyResidual = Math.max(
      maxEnergyResidual,
      Math.abs(solved.audit.kineticEnergyChange),
    );
    assert.equal(solved.audit.pass, true);
  }
  record(
    "R1",
    "500组确定性随机参数比较通式与质心系第二求解器",
    { seed: 20260831, count: 500 },
    { solverAgreement: true, conservationAudit: true },
    {
      maxVelocityDifference,
      maxMomentumResidual,
      maxEnergyResidual,
    },
    maxVelocityDifference < 1e-10 &&
      maxMomentumResidual < 1e-10 &&
      maxEnergyResidual < 1e-9,
  );
}

{
  const invalidInputs = [
    {
      m1: 0,
      m2: 1,
      u1: 1,
      u2: 0,
      type: COLLISION_TYPES.ELASTIC,
    },
    {
      m1: 1,
      m2: 1,
      u1: Number.NaN,
      u2: 0,
      type: COLLISION_TYPES.ELASTIC,
    },
  ];
  let rejected = 0;
  for (const input of invalidInputs) {
    try {
      solveCollision(input);
    } catch {
      rejected += 1;
    }
  }
  record(
    "B1",
    "非法质量与非有限速度被拒绝",
    invalidInputs,
    { rejected: invalidInputs.length },
    { rejected },
    rejected === invalidInputs.length,
  );
}

for (const report of reports) {
  console.log(
    `${report.pass ? "PASS" : "FAIL"} ${report.id} ${report.description}`,
  );
  console.log(`  input: ${JSON.stringify(report.input)}`);
  console.log(`  expected: ${JSON.stringify(report.expected)}`);
  console.log(`  actual: ${JSON.stringify(report.actual)}`);
}

console.log(
  `SUMMARY ${reports.filter((item) => item.pass).length}/${reports.length} checks passed`,
);
