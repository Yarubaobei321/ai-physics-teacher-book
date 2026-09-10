export const LIMITS = Object.freeze({
  massMin: 0.1,
  massMax: 10,
  speedMin: -10,
  speedMax: 10,
  tolerance: 1e-9,
});

export const COLLISION_TYPES = Object.freeze({
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

export function validateInputs(input) {
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

export function solveElasticDirect({ m1, m2, u1, u2 }) {
  const denominator = m1 + m2;
  return {
    v1: ((m1 - m2) * u1 + 2 * m2 * u2) / denominator,
    v2: (2 * m1 * u1 + (m2 - m1) * u2) / denominator,
  };
}

export function solveElasticByCenterOfMass({ m1, m2, u1, u2 }) {
  const centerVelocity = (m1 * u1 + m2 * u2) / (m1 + m2);
  return {
    v1: 2 * centerVelocity - u1,
    v2: 2 * centerVelocity - u2,
    centerVelocity,
  };
}

export function solvePerfectlyInelastic({ m1, m2, u1, u2 }) {
  const commonVelocity = (m1 * u1 + m2 * u2) / (m1 + m2);
  return { v1: commonVelocity, v2: commonVelocity, commonVelocity };
}

export function stateFromVelocities({ m1, m2, velocity1, velocity2 }) {
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

export function mixedClose(actual, expected, tolerance = LIMITS.tolerance) {
  const scale = Math.max(1, Math.abs(actual), Math.abs(expected));
  return Math.abs(actual - expected) <= tolerance * scale;
}

export function auditCandidate(params, candidate) {
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

export function solveCollision(rawInput) {
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

export function formatNumber(value, digits = 4) {
  if (!Number.isFinite(value)) return "—";
  if (Math.abs(value) < 10 ** -(digits + 1)) return "0";
  return Number(value.toFixed(digits)).toString();
}
