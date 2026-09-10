const finite = (value) => Number.isFinite(value);
const positive = (value) => finite(value) && value > 0;
const nonNegative = (value) => finite(value) && value >= 0;
const clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, value));
const near = (actual, expected, tolerance = 1e-9) => Math.abs(actual - expected) <= tolerance;

const parameter = (key, label, unit, minimum, maximum, step, value, source, help = '') => ({
  key,
  label,
  unit,
  minimum,
  maximum,
  step,
  value,
  source,
  help
});

const metric = (key, label, unit, digits = 2) => ({ key, label, unit, digits });

const ok = (values) => ({ ok: true, ...values });
const fail = (error) => ({ ok: false, error });

function readInputs(spec, values = {}) {
  return Object.fromEntries(spec.parameters.map((item) => [
    item.key,
    values[item.key] === undefined ? item.value : Number(values[item.key])
  ]));
}

function sample(count, callback) {
  return Array.from({ length: count }, (_, index) => callback(index / (count - 1), index));
}

function harvesterDirection(field, side, relativeVelocity) {
  const fluxRate = 2 * field * side * relativeVelocity;
  const inducedEmf = -fluxRate;
  const currentDirection = inducedEmf > 0 ? 'clockwise' : inducedEmf < 0 ? 'counterclockwise' : 'none';
  return { fluxRate, inducedEmf, currentDirection };
}

function ropeDisplacement(amplitude, wavelength, period, x, time) {
  return amplitude * Math.cos(2 * Math.PI * (x / wavelength - time / period));
}

function originalTrackerDirection(voltage1, voltage2) {
  if (near(voltage1, voltage2)) return 'stop';
  return voltage1 < voltage2 ? 'counterclockwise' : 'clockwise';
}

function calculateSafetyAirbag(input) {
  const { acceleration, sensorMass, armForce, headMass, dropHeight, contactTime, peakForce, gravity } = input;
  if (![sensorMass, headMass, dropHeight, contactTime, peakForce, gravity].every(positive) || !nonNegative(acceleration) || !nonNegative(armForce)) {
    return fail('质量、高度、接触时间、峰值力和重力加速度须为正数；加速度与压臂力不能为负。');
  }
  const tanTheta = sensorMass * acceleration / (sensorMass * gravity + armForce);
  const theta = Math.atan(tanTheta) * 180 / Math.PI;
  const forceImpulse = 0.5 * peakForce * contactTime;
  const impactSpeed = Math.sqrt(2 * gravity * dropHeight);
  const reboundSpeed = (forceImpulse - headMass * gravity * contactTime - headMass * impactSpeed) / headMass;
  const reboundHeight = reboundSpeed > 0 ? reboundSpeed ** 2 / (2 * gravity) : 0;
  const chart = sample(81, (u) => ({ x: u * contactTime, y: peakForce * (1 - Math.abs(2 * u - 1)) }));
  return ok({ tanTheta, theta, forceImpulse, impactSpeed, reboundSpeed, reboundHeight, chart, warning: reboundSpeed <= 0 ? '当前冲量不足以使头锤反弹；高度记为 0。' : '' });
}

function calculateRubberCollision(input) {
  const { mass, diameter, downTime, upTime } = input;
  if (![mass, diameter, downTime, upTime].every(positive)) return fail('质量、球径和两次遮光时间都须为正数。');
  const downSpeed = diameter / downTime;
  const upSpeed = diameter / upTime;
  const energyBefore = 0.5 * mass * downSpeed ** 2;
  const energyAfter = 0.5 * mass * upSpeed ** 2;
  const energyLoss = energyBefore - energyAfter;
  const retainedRatio = energyAfter / energyBefore;
  const chart = [
    { x: 0, y: energyBefore },
    { x: 0.48, y: energyBefore },
    { x: 0.52, y: energyAfter },
    { x: 1, y: energyAfter }
  ];
  return ok({ downSpeed, upSpeed, energyBefore, energyAfter, energyLoss, retainedRatio, chart, warning: energyLoss < 0 ? '反弹速度大于碰前速度，单纯“机械能损失”模型不适用，请检查外部能量输入或读数。' : '' });
}

function calculateEnergyAbsorber(input) {
  const { cartMass, flagWidth, beforeTime, cart1Time, cart2Time } = input;
  if (![cartMass, flagWidth, beforeTime, cart1Time, cart2Time].every(positive)) return fail('质量、遮光条宽度和遮光时间都须为正数。');
  const beforeSpeed = 10 * flagWidth / beforeTime;
  const cart1Speed = 10 * flagWidth / cart1Time;
  const cart2Speed = 10 * flagWidth / cart2Time;
  const momentumBefore = cartMass * beforeSpeed;
  const momentumAfter = cartMass * (cart1Speed + cart2Speed);
  const retainedRatio = (cart1Speed ** 2 + cart2Speed ** 2) / beforeSpeed ** 2;
  const momentumError = (momentumAfter - momentumBefore) / momentumBefore;
  const warnings = [];
  if (Math.abs(momentumError) > 0.05) warnings.push('碰撞前后动量差超过 5%，请检查一维模型、遮光读数或外力冲量。');
  if (retainedRatio > 1 + 1e-12) warnings.push('碰后平动动能大于碰前；被动吸能材料模型不适用，请检查外部能量输入或遮光读数。');
  const chart = [
    { x: 0, y: beforeSpeed, y2: 0 },
    { x: 0.48, y: beforeSpeed, y2: 0 },
    { x: 0.52, y: cart1Speed, y2: cart2Speed },
    { x: 1, y: cart1Speed, y2: cart2Speed }
  ];
  return ok({ beforeSpeed, cart1Speed, cart2Speed, momentumBefore, momentumAfter, momentumError, retainedRatio, absorbedRatio: 1 - retainedRatio, chart, warning: warnings.join(' ') });
}

function calculateHarvester(input) {
  const { field, side, amplitude, frequency } = input;
  if (![field, side, amplitude, frequency].every(positive)) return fail('磁感应强度、线圈边长、振幅与频率都须为正数。');
  if (amplitude > side / 2) return fail('相对振幅不能超过 L/2，否则单条磁场分界会离开线圈，2BLx 模型失效。');
  const omega = 2 * Math.PI * frequency;
  const maxSpeed = omega * amplitude;
  const maxEmf = 2 * field * side * maxSpeed;
  const downwardState = harvesterDirection(field, side, -maxSpeed);
  const chart = sample(121, (u) => {
    const phase = 2 * Math.PI * u;
    const displacement = amplitude * Math.sin(phase);
    const speed = maxSpeed * Math.cos(phase);
    return { x: u / frequency, y: 2 * field * side * displacement, y2: -2 * field * side * speed };
  });
  return ok({
    omega,
    maxSpeed,
    maxEmf,
    centeredFlux: 0,
    downwardFluxRate: downwardState.fluxRate,
    downwardInducedEmf: downwardState.inducedEmf,
    downwardCurrentDirection: downwardState.currentDirection,
    chart
  });
}

function calculateElectromagneticWeighing(input) {
  const { frameMass, current, emf, fieldSpeed, gravity } = input;
  if (![frameMass, current, emf, fieldSpeed, gravity].every(positive)) return fail('框架质量、电流、电动势、磁场速度和重力加速度都须为正数。');
  const bl = emf / fieldSpeed;
  const magneticForce = bl * current;
  const measuredMass = magneticForce / gravity - frameMass;
  if (!nonNegative(measuredMass)) return fail('EI/(gv) 小于框架质量 M，当前输入不能对应非负待测质量。');
  const minimumCurrent = frameMass * gravity / bl;
  const maximumCurrent = Math.max(current * 1.6, minimumCurrent * 1.1);
  const chart = sample(81, (u) => {
    const testCurrent = minimumCurrent + (maximumCurrent - minimumCurrent) * u;
    return { x: testCurrent, y: bl * testCurrent / gravity - frameMass };
  });
  return ok({ bl, magneticForce, measuredMass, chart });
}

function calculateThermistor(input) {
  const { comparisonR1, comparisonR2, beta, temperature } = input;
  if (![comparisonR1, comparisonR2, beta].every(positive) || comparisonR1 <= comparisonR2 || !finite(temperature) || temperature <= -273.15) return fail('R₀₁、R₀₂、B 常数须为正数，且 R₀₁>R₀₂；温度须高于绝对零度。');
  const resistance25 = comparisonR1 - comparisonR2;
  const kelvin = temperature + 273.15;
  const referenceKelvin = 298.15;
  const resistance = resistance25 * Math.exp(beta * (1 / kelvin - 1 / referenceKelvin));
  const chart = sample(91, (u) => {
    const celsius = 0 + 90 * u;
    const t = celsius + 273.15;
    return { x: celsius, y: resistance25 * Math.exp(beta * (1 / t - 1 / referenceKelvin)) };
  });
  return ok({ resistance25, resistance, conductance: 1 / resistance, chart });
}

function calculateConductiveRope(input) {
  const { voltage, current1, current2, loadingSlope, hysteresis } = input;
  const anchorResistance = 1.33;
  const anchorLength = 51.8;
  if (![voltage, current1, current2, loadingSlope].every(positive) || current2 <= current1 || !nonNegative(hysteresis)) return fail('电压、电流与斜率须为正数，且 I₂>I₁；迟滞量不能为负。');
  const measuredResistance = voltage / (current2 - current1);
  const loadingLength = anchorLength + (measuredResistance - anchorResistance) / loadingSlope;
  const unloadingLength = anchorLength + (measuredResistance - anchorResistance - hysteresis) / loadingSlope;
  if (loadingLength < 51 || loadingLength > 52 || unloadingLength < 51 || unloadingLength > 52) return fail('当前电阻反演长度超出原题图 51.00—52.00 cm 的局部标定范围。');
  const chart = sample(81, (u) => {
    const length = 51 + u;
    const loadR = anchorResistance + loadingSlope * (length - anchorLength);
    const point = { x: length, y: loadR };
    if (hysteresis > 0) point.y2 = loadR + hysteresis;
    return point;
  });
  return ok({ measuredResistance, loadingLength, unloadingLength, lengthDifference: Math.abs(loadingLength - unloadingLength), chart, warning: hysteresis > 0 ? '卸载迟滞是原题标定线之外的扩展示意，图书视图已停用。' : '' });
}

function calculateSaline(input) {
  const { meterOpen, meterClosed, resistor1, resistor2, resistor3, resistor4, electrodeGap, electrodeArea, temperature } = input;
  if (![meterOpen, meterClosed, resistor1, resistor2, resistor3, resistor4, electrodeGap, electrodeArea].every(positive) || near(meterOpen, meterClosed) || !finite(temperature)) return fail('两次表读、R₁—R₄、电极间距和面积须为正数，且两次表读不能相同；温度须为有限数。');
  const currentMultiplier = 1 + resistor3 / resistor4;
  const currentOpen = meterOpen * currentMultiplier;
  const currentClosed = meterClosed * currentMultiplier;
  const rightEquivalent = resistor3 * resistor4 / (resistor3 + resistor4);
  const leftOpen = resistor2;
  const leftClosed = resistor1 * resistor2 / (resistor1 + resistor2);
  const resistance = (currentClosed * (leftClosed + rightEquivalent) - currentOpen * (leftOpen + rightEquivalent)) / (currentOpen - currentClosed);
  if (!positive(resistance)) return fail('两状态输入反演得到的样品电阻不为正，请检查电流与等效串联电阻。');
  const voltageA = currentOpen / 1000 * (resistance + leftOpen + rightEquivalent);
  const voltageB = currentClosed / 1000 * (resistance + leftClosed + rightEquivalent);
  const conductivity = electrodeGap / (resistance * electrodeArea);
  const chart = [{ x: 1, y: currentOpen }, { x: 2, y: currentClosed }];
  return ok({ resistance, conductivity, voltageA, voltageB, voltageMismatch: voltageB - voltageA, resistivity: 1 / conductivity, currentMultiplier, currentOpen, currentClosed, rightEquivalent, leftOpen, leftClosed, temperature, chart });
}

function calculateLightTracker(input) {
  const { lightAngle, panelAngle, sensitivity, deadZone, motorSpeed } = input;
  if (![sensitivity, motorSpeed].every(positive) || !nonNegative(deadZone) || ![lightAngle, panelAngle].every(finite)) return fail('角度须为有限数，灵敏度与电机速度须为正数，死区不能为负。');
  const initialError = lightAngle - panelAngle;
  if (Math.abs(initialError) > 90) return fail('光源超出 ±90° 前向跟踪视场，正弦差分不再单调，装置进入失锁状态。');
  if (deadZone >= 2 * sensitivity) return fail('停止死区必须小于最大差分电压 2S，否则控制器无法可靠启动。');
  const initialDifference = 2 * sensitivity * Math.sin(initialError * Math.PI / 180);
  const active = Math.abs(initialDifference) > deadZone;
  const direction = active ? Math.sign(initialDifference) : 0;
  const stopErrorMagnitude = Math.asin(clamp(deadZone / (2 * sensitivity), 0, 1)) * 180 / Math.PI;
  const finalError = active ? Math.sign(initialError) * stopErrorMagnitude : initialError;
  const turnDistance = active ? Math.max(0, Math.abs(initialError) - stopErrorMagnitude) : 0;
  const turnTime = turnDistance / motorSpeed;
  const chart = sample(101, (u) => {
    const time = Math.max(turnTime, 1) * u;
    const moved = direction * Math.min(motorSpeed * time, turnDistance);
    const error = initialError - moved;
    return { x: time, y: 2 * sensitivity * Math.sin(error * Math.PI / 180), y2: error };
  });
  const originalVoltage1 = 1.60;
  const originalVoltage2 = 1.17;
  const originalDarkerSideHasLargerResistance = originalVoltage1 > originalVoltage2;
  const originalTrackingDirection = originalTrackerDirection(1.17, 1.60);
  return ok({
    initialError,
    initialDifference,
    active,
    direction,
    turnTime,
    finalError,
    stopErrorMagnitude,
    originalVoltage1,
    originalVoltage2,
    originalDarkerSideHasLargerResistance,
    originalTrackingDirection,
    chart
  });
}

function calculateEddyBrake(input) {
  const { current, calibrationSlope, initialSpeed, dampingAt15mT } = input;
  if (![calibrationSlope, initialSpeed, dampingAt15mT].every(positive) || !nonNegative(current)) return fail('标定斜率、初始转速与参考阻尼须为正数，电流不能为负。');
  const fieldMilliTesla = calibrationSlope * current;
  const dampingRate = dampingAt15mT * (fieldMilliTesla / 15) ** 2;
  const timeToTenPercent = dampingRate > 0 ? Math.log(10) / dampingRate : Number.POSITIVE_INFINITY;
  const horizon = finite(timeToTenPercent) ? timeToTenPercent * 1.15 : 8;
  const chart = sample(101, (u) => ({ x: horizon * u, y: dampingRate > 0 ? initialSpeed * Math.exp(-dampingRate * horizon * u) : initialSpeed }));
  return ok({ fieldMilliTesla, dampingRate, timeToTenPercent, chart, warning: current === 0 ? 'B=0 时标准化涡流阻尼为零，圆盘不会在此模型中自行停下。' : '' });
}

function calculateCotton(input) {
  const { springConstant, compression, minimumForce, boxBefore, boxAfter, dryResistance, wetResistance } = input;
  if (![springConstant, minimumForce, boxBefore, boxAfter, dryResistance, wetResistance].every(positive) || boxBefore <= boxAfter || !nonNegative(compression)) return fail('劲度系数、压力门槛与电阻须为正数，且 R₁>R₂；压缩量不能为负。');
  if (dryResistance <= wetResistance) return fail('归一化示意曲线要求干态电阻大于湿态电阻。');
  const pressureForce = springConstant * compression;
  const measuredResistance = boxBefore - boxAfter;
  const calibrationUnlocked = pressureForce >= minimumForce;
  const moistureIndex = calibrationUnlocked ? clamp((dryResistance - measuredResistance) / (dryResistance - wetResistance), 0, 1) : Number.NaN;
  const chart = sample(81, (u) => ({ x: u, y: dryResistance + (wetResistance - dryResistance) * u }));
  const warning = !calibrationUnlocked
    ? `压力尚未达到 ${minimumForce.toFixed(1)} N 的示意门槛，归一化读数已锁定。`
    : (measuredResistance > dryResistance || measuredResistance < wetResistance ? '测得电阻超出当前示意定标范围，归一化指标已截到边界。' : '');
  return ok({ pressureForce, measuredResistance, calibrationUnlocked, moistureIndex, chart, warning });
}

function calculateAbacus(input) {
  const { initialSpeed, friction, firstGap, secondGap, beadAAfter, gravity } = input;
  if (![initialSpeed, firstGap, secondGap, gravity].every(positive) || !nonNegative(friction) || !nonNegative(beadAAfter)) return fail('速度、间距和重力加速度须为正数；摩擦因数与碰后速度不能为负。');
  const deceleration = friction * gravity;
  const speedSquaredAtCollision = initialSpeed ** 2 - 2 * deceleration * firstGap;
  if (speedSquaredAtCollision < -1e-12) return fail('算珠甲在到达乙之前已经停下，当前参数没有碰撞事件。');
  const speedAtCollision = Math.sqrt(Math.max(0, speedSquaredAtCollision));
  if (beadAAfter > speedAtCollision) return fail('碰后甲速度大于碰前速度，等质量、无外冲量碰撞模型无法给出乙的非负速度。');
  const beadBAfter = speedAtCollision - beadAAfter;
  if (beadAAfter > beadBAfter + 1e-12) return fail('碰后甲仍快于乙，两算珠会再次碰撞；当前单次碰撞模型不适用。');
  const stoppingDistanceB = deceleration > 0 ? beadBAfter ** 2 / (2 * deceleration) : (beadBAfter === 0 ? 0 : Number.POSITIVE_INFINITY);
  const reachesFrame = stoppingDistanceB + 1e-12 >= secondGap;
  const crossesFrameWithSpeed = stoppingDistanceB > secondGap + 1e-9;
  const framePosition = firstGap + secondGap;
  const timeBefore = deceleration > 0 ? (initialSpeed - speedAtCollision) / deceleration : firstGap / initialSpeed;
  const timeAAfter = deceleration > 0 ? beadAAfter / deceleration : (beadAAfter === 0 ? 0 : Number.POSITIVE_INFINITY);
  const totalTimeA = timeBefore + timeAAfter;
  const timeBAfter = deceleration > 0 ? beadBAfter / deceleration : (beadBAfter === 0 ? 0 : Number.POSITIVE_INFINITY);
  const finiteMotionEnd = Math.max(totalTimeA, timeBefore + timeBAfter);
  const horizon = finite(finiteMotionEnd) ? Math.max(finiteMotionEnd, 1e-6) : Math.max(timeBefore + 1, 1);
  const collisionPhase = clamp(timeBefore / horizon, 0, 1);
  const chart = sample(121, (u) => {
    const t = horizon * u;
    const before = Math.min(t, timeBefore);
    let xA = initialSpeed * before - 0.5 * deceleration * before ** 2;
    let xB = firstGap;
    if (t > timeBefore) {
      const after = t - timeBefore;
      const ta = deceleration > 0 ? Math.min(after, beadAAfter / deceleration) : after;
      const tb = deceleration > 0 ? Math.min(after, beadBAfter / deceleration) : after;
      xA = firstGap + beadAAfter * ta - 0.5 * deceleration * ta ** 2;
      xB = Math.min(framePosition, firstGap + beadBAfter * tb - 0.5 * deceleration * tb ** 2);
    }
    return { x: t, y: xA, y2: xB };
  });
  const warnings = [];
  if (friction === 0) warnings.push('μ=0 时两算珠不会在此模型中自行停下。');
  if (crossesFrameWithSpeed) warnings.push('乙在当前参数下会以非零速度触及右边框；图线在边框处停止，触框后的碰撞需切换模型。');
  return ok({ deceleration, speedAtCollision, beadBAfter, stoppingDistanceB, reachesFrame, crossesFrameWithSpeed, framePosition, timeBefore, horizon, collisionPhase, totalTimeA, chart, warning: warnings.join(' ') });
}

function calculateCurtain(input) {
  const { mass1, mass2, beforeSpeed1, beforeSpeed2, motorForce, contactTime } = input;
  if (![mass1, mass2, beforeSpeed1, contactTime].every(positive) || !nonNegative(beforeSpeed2) || !nonNegative(motorForce)) return fail('两车质量、滑块1碰前速度和碰撞时间须为正数；滑块2速度与电机力不能为负。');
  if (beforeSpeed1 <= beforeSpeed2) return fail('滑块1速度必须大于滑块2速度，二者才会发生追及碰撞。');
  const momentumBefore = mass1 * beforeSpeed1 + mass2 * beforeSpeed2;
  const externalImpulse = motorForce * contactTime;
  const momentumAfter = momentumBefore + externalImpulse;
  const commonSpeed = momentumAfter / (mass1 + mass2);
  const cart1Impulse = mass1 * (commonSpeed - beforeSpeed1);
  const cart2Impulse = mass2 * (commonSpeed - beforeSpeed2);
  const contactForce = cart2Impulse / contactTime;
  const noMotorCommonSpeed = momentumBefore / (mass1 + mass2);
  const chart = sample(81, (u) => ({ x: u * contactTime, y: momentumBefore + externalImpulse * u, y2: momentumBefore }));
  return ok({ momentumBefore, momentumAfter, commonSpeed, externalImpulse, motorForce, cart1Impulse, cart2Impulse, contactForce, noMotorCommonSpeed, chart });
}

function calculateRobot(input) {
  const { totalMass, hammerMass, radius, initialSpeed, gravity } = input;
  if (![totalMass, hammerMass, radius, initialSpeed, gravity].every(positive)) return fail('总质量、摆锤质量、绳长、初速度和重力加速度须为正数。');
  if (totalMass < 2 * hammerMass) return fail('机器人总质量 M 不能小于两只摆锤质量 2m。');
  const atStopSpeedSquared = initialSpeed ** 2 - 2 * gravity * radius;
  if (atStopSpeedSquared < 0) return fail('v₀²<2gR，两摆锤无法到达水平挡板。');
  const hammerSpeed = Math.sqrt(atStopSpeedSquared);
  const commonSpeed = 2 * hammerMass * hammerSpeed / totalMass;
  const kineticAfterImpact = 0.5 * totalMass * commonSpeed ** 2;
  const jumpHeight = commonSpeed ** 2 / (2 * gravity);
  const initialEnergy = hammerMass * initialSpeed ** 2;
  const energyAfterLanding = hammerMass * commonSpeed ** 2 + 2 * hammerMass * gravity * radius;
  const energyLoss = initialEnergy - energyAfterLanding;
  const chart = [
    { x: 0, y: initialEnergy },
    { x: 1, y: hammerMass * hammerSpeed ** 2 + 2 * hammerMass * gravity * radius },
    { x: 2, y: kineticAfterImpact + 2 * hammerMass * gravity * radius },
    { x: 3, y: kineticAfterImpact + 2 * hammerMass * gravity * radius },
    { x: 4, y: energyAfterLanding }
  ];
  return ok({ hammerSpeed, commonSpeed, kineticAfterImpact, jumpHeight, initialEnergy, energyAfterLanding, energyLoss, chart });
}

function calculateRopeWave(input) {
  const { amplitude, waveSpeed, frequency, markerX } = input;
  if (![amplitude, waveSpeed, frequency].every(positive) || !nonNegative(markerX)) return fail('振幅、波速和频率须为正数，标记位置不能为负。');
  const wavelength = waveSpeed / frequency;
  const period = 1 / frequency;
  const physicalSpan = Math.max(3 * wavelength, markerX + .7 * wavelength);
  const chart = sample(161, (u) => {
    const x = physicalSpan * u;
    return { x, y: ropeDisplacement(amplitude, wavelength, period, x, 0) };
  });
  const markerInitial = ropeDisplacement(amplitude, wavelength, period, markerX, 0);
  const markerHalfPeriod = ropeDisplacement(amplitude, wavelength, period, markerX, period / 2);
  const markerAfterPeriod = ropeDisplacement(amplitude, wavelength, period, markerX, period);
  return ok({ wavelength, period, markerInitial, markerHalfPeriod, markerAfterPeriod, chart });
}

function calculateTravelingWave(input) {
  const { amplitude, waveSpeed, wavelength, probeX, probeTime } = input;
  if (![amplitude, waveSpeed, wavelength].every(positive) || ![probeX, probeTime].every(nonNegative)) return fail('振幅、波速和波长须为正数，位置与时刻不能为负。');
  const period = wavelength / waveSpeed;
  const probeDisplacement = amplitude * Math.sin(2 * Math.PI * (probeX - waveSpeed * probeTime) / wavelength);
  const physicalSpan = Math.max(2 * wavelength, probeX + .45 * wavelength);
  const chart = sample(161, (u) => {
    const x = physicalSpan * u;
    return { x, y: amplitude * Math.sin(2 * Math.PI * (x - waveSpeed * probeTime) / wavelength) };
  });
  return ok({ period, frequency: 1 / period, probeDisplacement, chart });
}

function calculateSpringOscillator(input) {
  const { amplitude, period, time } = input;
  if (![amplitude, period].every(positive) || !nonNegative(time)) return fail('振幅与周期须为正数，时刻不能为负。');
  const omega = 2 * Math.PI / period;
  const displacement = amplitude * Math.cos(omega * time);
  const speed = -amplitude * omega * Math.sin(omega * time);
  const heightAboveLowest = amplitude - displacement;
  const kineticFraction = Math.sin(omega * time) ** 2;
  const chart = sample(161, (u) => {
    const t = period * u;
    return { x: t, y: amplitude * Math.cos(omega * t), y2: Math.sin(omega * t) ** 2 };
  });
  return ok({ omega, displacement, speed, heightAboveLowest, heightFraction: heightAboveLowest / amplitude, kineticFraction, chart });
}

function calculateForcedDoppler(input) {
  const { naturalFrequency, driveFrequency, dampingRatio, sourceFrequency, soundSpeed, relativeSpeed } = input;
  if (![naturalFrequency, driveFrequency, sourceFrequency, soundSpeed].every(positive) || !nonNegative(dampingRatio) || !finite(relativeSpeed) || Math.abs(relativeSpeed) >= soundSpeed) return fail('频率、声速须为正数；阻尼不能为负；相对速度大小须小于声速。');
  const ratio = driveFrequency / naturalFrequency;
  const response = 1 / Math.sqrt((1 - ratio ** 2) ** 2 + (2 * dampingRatio * ratio) ** 2);
  const receivedFrequency = sourceFrequency * soundSpeed / (soundSpeed - relativeSpeed);
  const chart = sample(161, (u) => {
    const testRatio = 0.2 + 2.3 * u;
    const amplitudeRatio = 1 / Math.sqrt((1 - testRatio ** 2) ** 2 + (2 * dampingRatio * testRatio) ** 2);
    return { x: testRatio * naturalFrequency, y: amplitudeRatio };
  });
  return ok({ naturalFrequency, driveFrequency, ratio, response, receivedFrequency, frequencyShift: receivedFrequency - sourceFrequency, chart });
}

function calculateEchoSounder(input) {
  const { soundSpeed, frequency, distance, targetSpeed } = input;
  if (![soundSpeed, frequency, distance].every(positive) || !finite(targetSpeed) || Math.abs(targetSpeed) >= soundSpeed) return fail('声速、频率和距离须为正数；目标速度大小须小于声速。');
  const wavelength = soundSpeed / frequency;
  const reflectionTime = distance / (soundSpeed + targetSpeed);
  const reflectionDistance = soundSpeed * reflectionTime;
  const echoTime = 2 * reflectionTime;
  const echoFrequency = frequency * (soundSpeed + targetSpeed) / (soundSpeed - targetSpeed);
  const chart = sample(121, (u) => {
    const t = echoTime * u;
    const outbound = Math.min(soundSpeed * t, reflectionDistance);
    const returnPosition = t <= reflectionTime ? outbound : Math.max(0, reflectionDistance - soundSpeed * (t - reflectionTime));
    return { x: t, y: returnPosition };
  });
  return ok({ wavelength, reflectionTime, reflectionDistance, echoTime, echoFrequency, frequencyShift: echoFrequency - frequency, chart });
}

const calculators = {
  safetyAirbag: calculateSafetyAirbag,
  rubberCollision: calculateRubberCollision,
  energyAbsorber: calculateEnergyAbsorber,
  harvester: calculateHarvester,
  electromagneticWeighing: calculateElectromagneticWeighing,
  thermistor: calculateThermistor,
  conductiveRope: calculateConductiveRope,
  saline: calculateSaline,
  lightTracker: calculateLightTracker,
  eddyBrake: calculateEddyBrake,
  cotton: calculateCotton,
  abacus: calculateAbacus,
  curtain: calculateCurtain,
  robot: calculateRobot,
  ropeWave: calculateRopeWave,
  travelingWave: calculateTravelingWave,
  springOscillator: calculateSpringOscillator,
  forcedDoppler: calculateForcedDoppler,
  echoSounder: calculateEchoSounder
};

export const GAOKAO_MODEL_SPECS = [
  {
    id: '02-01-02', slug: '2024-seatbelt-airbag', year: 2024, title: '刹车的一瞬间，安全装置怎样响应', shortTitle: '安全带锁止与安全气囊', topic: '碰撞与动量', family: 'safetyAirbag', scene: 'airbag',
    lead: '同一场刹车里，敏感球用加速度触发锁止，头锤用力—时间面积检验气囊。页面把两个装置放在同一条“受力—冲量—结果”证据链上。',
    sourceBoundary: '头锤 M=30 kg、H=3.2 m、接触 0.10 s、三角形峰值 6600 N 来自 2024 广东原题；敏感球演示的 a、m、Fₙ 为可调示意输入。',
    modelNote: '敏感球忽略摩擦；气囊力按原题三角形图线，接触阶段保留重力冲量，头锤视为质点。',
    parameters: [parameter('acceleration', '汽车减速度 a', 'm/s²', 0, 15, 0.1, 5, '标准化输入'), parameter('sensorMass', '敏感球质量 m', 'kg', 0.01, 0.5, 0.01, 0.05, '标准化输入'), parameter('armForce', '敏感臂压力 Fₙ', 'N', 0, 5, 0.05, 0.25, '标准化输入'), parameter('headMass', '头锤质量 M', 'kg', 1, 100, 1, 30, '原题参数'), parameter('dropHeight', '下落高度 H', 'm', 0.1, 10, 0.1, 3.2, '原题参数'), parameter('contactTime', '接触时间', 's', 0.01, 0.5, 0.01, 0.1, '原题读图'), parameter('peakForce', '气囊峰值力', 'N', 100, 10000, 100, 6600, '原题读图'), parameter('gravity', '重力加速度 g', 'm/s²', 1, 20, 0.1, 10, '原题参数')],
    metrics: [metric('theta', '锁止斜面角', '°', 1), metric('forceImpulse', '气囊力冲量', 'N·s', 0), metric('reboundSpeed', '碰后速度（向上为正）', 'm/s', 2), metric('reboundHeight', '最大反弹高度', 'm', 2)],
    chart: { title: '气囊作用力—时间', xLabel: 't / s', yLabel: 'F / N', cursorMode: 'process-time', cursorValue: (phase, _result, input) => input.contactTime * clamp((phase - .28) / .44, 0, 1) }, bookPhase: .52, phases: ['自由下落', '接触增力', '峰值作用', '接触卸力', '反弹'],
    tests: [{ name: '原题气囊力冲量为 330 N·s', check: (r) => near(r.forceImpulse, 330) }, { name: '原题碰后速度为 2 m/s', check: (r) => near(r.reboundSpeed, 2) }, { name: '原题最大上升高度为 0.20 m', check: (r) => near(r.reboundHeight, 0.2) }, { name: '默认敏感球满足 tanθ=1/3', check: (r) => near(r.tanTheta, 1 / 3) && near(r.theta, Math.atan(1 / 3) * 180 / Math.PI) }, { name: '气囊冲量不足时不得画出反弹高度', custom: () => { const r = calculateSafetyAirbag({ acceleration: 5, sensorMass: .05, armForce: .25, headMass: 30, dropHeight: 3.2, contactTime: .1, peakForce: 1000, gravity: 10 }); return r.ok && r.reboundSpeed <= 0 && near(r.reboundHeight, 0) && r.warning.includes('不足'); } }]
  },
  {
    id: '15-01-05', slug: '2022-rubber-collision', year: 2022, title: '一颗球反弹以后，能量去了哪里', shortTitle: '小球与橡胶碰撞', topic: '实验测量', family: 'rubberCollision', scene: 'rubberBall',
    lead: '光电门记录的是遮光时间。先把球径和两次遮光时间变成速度，再比较同一高度处的平动动能。',
    sourceBoundary: '球径默认 7.884 mm 来自原题读数；原题未给出 t₁、t₂ 的一组数值，页面默认时间是标准化演示输入。',
    modelNote: '遮光区间内速度近似不变；两次比较位置相同；忽略空气阻力、转动和偏斜反弹。',
    parameters: [parameter('mass', '小球质量 m', 'kg', 0.005, 0.5, 0.005, 0.05, '标准化输入'), parameter('diameter', '小球直径 d', 'mm', 1, 20, 0.001, 7.884, '原题读数'), parameter('downTime', '下落遮光时间 t₁', 'ms', 1, 50, 0.1, 8, '标准化输入'), parameter('upTime', '反弹遮光时间 t₂', 'ms', 1, 80, 0.1, 12, '标准化输入')],
    metrics: [metric('downSpeed', '碰前速度', 'm/s', 3), metric('upSpeed', '反弹速度', 'm/s', 3), metric('energyLoss', '平动能差', 'J', 4), metric('retainedRatio', '能量保留率', '%', 1)], metricTransforms: { retainedRatio: (v) => v * 100 },
    chart: { title: '碰撞前后平动动能', xLabel: '归一化过程', yLabel: 'Eₖ / J', cursorMode: 'process-time', cursorValue: (phase) => phase }, bookPhase: .52, phases: ['下落过门', '接近橡胶', '碰撞形变', '离开橡胶', '反弹过门'],
    tests: [{ name: '球径与时间的单位换算保持 d/t', check: (r) => near(r.downSpeed, 7.884 / 8) }, { name: 't₁=t₂ 时平动能差为零', custom: () => near(calculateRubberCollision({ mass: .05, diameter: 7.884, downTime: 8, upTime: 8 }).energyLoss, 0) }, { name: '反弹遮光更久时能量保留率小于 1', check: (r) => r.retainedRatio < 1 }]
  },
  {
    id: '15-01-02', slug: '2025-energy-absorber', year: 2025, title: '三次遮光，怎样评价一块吸能材料', shortTitle: '小车与吸能材料', topic: '碰撞与动量', family: 'energyAbsorber', scene: 'twoCarts',
    lead: '相同遮光条把三次时间变成三个速度。动量核对模型边界，动能保留率描述材料吸收平动能的程度。',
    sourceBoundary: '遮光条 1.00 cm，三次遮光时间 10.00、15.00、30.00 ms 均来自 2025 广东原题；小车质量只影响绝对能量，默认值为标准化输入。',
    modelNote: '两车质量相同、沿一条直线运动，吸能材料质量忽略；能量保留率不等同于材料全部性能。',
    parameters: [parameter('cartMass', '单车质量', 'kg', .05, 2, .05, .5, '标准化输入'), parameter('flagWidth', '遮光条宽度', 'cm', .2, 5, .01, 1, '原题参数'), parameter('beforeTime', '碰前遮光时间', 'ms', 1, 60, .1, 10, '原题参数'), parameter('cart1Time', '车1碰后遮光时间', 'ms', 1, 80, .1, 15, '原题参数'), parameter('cart2Time', '车2碰后遮光时间', 'ms', 1, 100, .1, 30, '原题参数')],
    metrics: [metric('beforeSpeed', '碰前速度', 'm/s', 2), metric('cart1Speed', '车1碰后速度', 'm/s', 2), metric('cart2Speed', '车2碰后速度', 'm/s', 2), metric('retainedRatio', '动能保留率', '%', 0)], metricTransforms: { retainedRatio: (v) => v * 100 },
    chart: { title: '两车速度随碰撞阶段变化', xLabel: '归一化过程', yLabel: 'v / (m·s⁻¹)', primaryLabel: '车1', secondaryLabel: '车2', cursorMode: 'process-time', cursorValue: (phase) => phase }, bookPhase: .52, phases: ['车2入射', '接触前', '材料压缩', '两车分离', '通过光电门B'],
    tests: [{ name: '原题三次遮光回归速度 1、2/3、1/3 m/s', check: (r) => near(r.beforeSpeed, 1) && near(r.cart1Speed, 2 / 3) && near(r.cart2Speed, 1 / 3) }, { name: '原题动能保留率为 5/9≈0.56', check: (r) => near(r.retainedRatio, 5 / 9) }, { name: '原题参数下一维动量守恒', check: (r) => Math.abs(r.momentumError) < 1e-12 }, { name: '保留率大于1时否决被动吸能解释', custom: () => { const r = calculateEnergyAbsorber({ cartMass: .5, flagWidth: 1, beforeTime: 10, cart1Time: 5, cart2Time: 5 }); return r.ok && r.retainedRatio > 1 && r.warning.includes('被动吸能材料模型不适用'); } }]
  },
  {
    id: '10-02-01', slug: '2024-electromagnetic-harvester', year: 2024, title: '磁通量为零时，电压为什么仍会出现', shortTitle: '电磁俘能器', topic: '电磁过程', family: 'harvester', scene: 'harvester',
    lead: '图示位置的正、负磁通量相互抵消；只要磁场分界继续移动，磁通量变化率仍不为零。',
    sourceBoundary: '原题只给符号 B、L 和定性运动；线圈内由一条直线分界隔开大小相等、方向相反的磁场，图示中心位置净磁通量为零。永磁铁相对线圈下降时，原题判定电流为顺时针（答案D）。数值 B、L、振幅与频率均为演示输入。',
    modelNote: '单条分界在线圈内移动 x 时，两侧有向面积同步改变，故 Φ=2BLx、|ε|=2BL|u|；相对下降按原题图示约定为顺时针。振幅超过 L/2 后分界离开线圈，线性关系失效。',
    parameters: [parameter('field', '磁感应强度 B', 'T', .05, 1, .01, .4, '标准化输入'), parameter('side', '线圈边长 L', 'm', .05, .5, .01, .2, '标准化输入'), parameter('amplitude', '相对振幅 A', 'm', .005, .08, .001, .03, '标准化输入'), parameter('frequency', '振动频率 f', 'Hz', .2, 8, .1, 2, '标准化输入')],
    metrics: [metric('centeredFlux', '中心位置净磁通量', 'Wb', 3), metric('maxSpeed', '最大相对速度', 'm/s', 3), metric('maxEmf', '最大感应电动势', 'V', 3), metric('frequency', '输入频率', 'Hz', 2)], metricTransforms: { frequency: (_, p) => p.frequency },
    chart: { title: '磁通量与感应电动势的相位关系', xLabel: 't / s', yLabel: 'Φ / Wb', primaryLabel: '磁通量 Φ', secondaryLabel: '感应电动势 ε', secondaryYLabel: 'ε / V', cursorMode: 'process-time', cursorValue: (phase, _result, input) => phase / input.frequency }, bookPhase: .5, phases: ['上移最快', '上端位', '下移最快', '下端位', '回到中心'],
    tests: [{ name: '图示中心位置净磁通量为 0', check: (r) => near(r.centeredFlux, 0) }, { name: '默认参数独立回归 uₘₐₓ=0.12π m/s、εₘₐₓ=0.0192π V', check: (r) => near(r.maxSpeed, .12 * Math.PI) && near(r.maxEmf, .0192 * Math.PI) }, { name: '下降时 dΦ/dt<0、感应电动势为正并映射顺时针', check: (r) => r.downwardFluxRate < 0 && r.downwardInducedEmf > 0 && r.downwardCurrentDirection === 'clockwise' }, { name: '频率翻倍时最大电动势翻倍', custom: () => { const a = calculateHarvester({ field: .4, side: .2, amplitude: .03, frequency: 2 }); const b = calculateHarvester({ field: .4, side: .2, amplitude: .03, frequency: 4 }); return near(b.maxEmf, 2 * a.maxEmf); } }, { name: '振幅超过 L/2 时拒绝线性几何', custom: () => !calculateHarvester({ field: .4, side: .05, amplitude: .03, frequency: 2 }).ok }]
  },
  {
    id: '10-03-01', slug: '2025-electromagnetic-scale', year: 2025, title: '两个过程，怎样消去看不见的 BL', shortTitle: '电磁称重装置', topic: '电磁过程', family: 'electromagneticWeighing', scene: 'weighing',
    lead: '通电平衡得到安培力，移动磁场得到动生电动势。两个步骤共享 BL，于是待测质量可以从可测量量中被消元出来。',
    sourceBoundary: '原题给出符号关系，不给具体数值。默认 M=1 kg、I=15 A、E=1 V、v=1 m/s、g=10 m/s² 是用于回归公式的标准化参数。',
    modelNote: '平衡阶段 (M+m)g=BIL；断路动生阶段 E=BLv。E 与 I 来自不同状态，E/I 不能解释为线圈电阻。',
    parameters: [parameter('frameMass', '框架质量 M', 'kg', .1, 5, .1, 1, '标准化输入'), parameter('current', '平衡电流 I', 'A', .1, 30, .1, 15, '标准化输入'), parameter('emf', '断路感应电动势 E', 'V', .05, 5, .05, 1, '标准化输入'), parameter('fieldSpeed', '磁场移动速度 v', 'm/s', .05, 5, .05, 1, '标准化输入'), parameter('gravity', '重力加速度 g', 'm/s²', 1, 20, .1, 10, '标准化输入')],
    metrics: [metric('bl', '消元得到 BL', 'T·m', 3), metric('magneticForce', '安培力', 'N', 2), metric('measuredMass', '待测质量 m', 'kg', 3), metric('current', '平衡电流', 'A', 2)], metricTransforms: { current: (_, p) => p.current },
    chart: { title: '平衡电流与反演质量', xLabel: 'I / A', yLabel: 'm / kg', cursorMode: 'operating-point', cursorValue: (_phase, _result, input) => input.current }, bookPhase: .72, phases: ['放入物块', '通电调平衡', '记录电流', '取下并断路', '移动磁场测 E'],
    tests: [{ name: '标准化原式回归 m=0.5 kg', check: (r) => near(r.measuredMass, .5) }, { name: 'E/v 恢复 BL=1 T·m，图线从 m=0 起', check: (r) => near(r.bl, 1) && r.chart.every((point) => point.y >= -1e-12) && near(r.chart[0].y, 0) }, { name: '电流增加时反演质量增加', custom: () => calculateElectromagneticWeighing({ frameMass: 1, current: 16, emf: 1, fieldSpeed: 1, gravity: 10 }).measuredMass > .5 }]
  },
  {
    id: '15-02-06', slug: '2021-thermistor', year: 2021, title: '温度升高，欧姆表指针为什么向右', shortTitle: '热敏电阻', topic: '传感与控制', family: 'thermistor', scene: 'thermistor',
    lead: '欧姆表先判断趋势，再用替代测量与 R—T 标定把“热”变成可比较的电阻。',
    sourceBoundary: '原题的替代法结论是在同一测量温度下 Rₓ=R₀₁−R₀₂，且只要求判断 NTC 阻值随温度升高而减小。页面把这次比较明确标准化为 25 ℃参考点；完整 R—T 数值表、R₂₅ 与 B 常数都不是原题数据。',
    modelNote: '先在标准化 25 ℃参考态用同偏转比较得到 R₂₅=R₀₁−R₀₂，再用常见 NTC B 参数方程外推目标温度的示意阻值。B 参数曲线不能代替具体元件标定。',
    parameters: [parameter('comparisonR1', '25 ℃参考态 R₀₁', 'kΩ', 1, 100, .5, 15, '标准化参考测阻'), parameter('comparisonR2', '25 ℃参考态 R₀₂', 'kΩ', .5, 99, .5, 5, '标准化参考测阻'), parameter('beta', '示意 B 常数', 'K', 1000, 6000, 50, 3950, '标准化曲线'), parameter('temperature', '目标温度 T', '℃', 0, 90, 1, 50, '用户输入')],
    metrics: [metric('resistance25', '25 ℃参考电阻 R₂₅', 'kΩ', 2), metric('resistance', '目标温度示意电阻', 'kΩ', 2), metric('temperature', '目标温度', '℃', 1), metric('beta', '示意 B 常数', 'K', 0)], metricTransforms: { temperature: (_, p) => p.temperature, beta: (_, p) => p.beta },
    chart: { title: '标准化 NTC 电阻—温度曲线', xLabel: 'T / ℃', yLabel: 'R / kΩ', cursorMode: 'operating-point', cursorValue: (_phase, _result, input) => input.temperature }, bookPhase: .62, phases: ['25 ℃参考态', '开始升温', '目标温度测量', '记录电阻', '回到 25 ℃'],
    tests: [{ name: '25 ℃参考态同偏转比较满足 R₂₅=R₀₁−R₀₂', check: (r) => near(r.resistance25, 10) }, { name: '参考点 25 ℃处曲线严格等于比较差值', custom: () => { const r = calculateThermistor({ comparisonR1: 15, comparisonR2: 5, beta: 3950, temperature: 25 }); return r.ok && near(r.resistance, r.resistance25); } }, { name: '目标温度 50 ℃时标准化 NTC 阻值低于 R₂₅', check: (r) => r.resistance < r.resistance25 }, { name: 'R₀₁≤R₀₂ 时拒绝负阻值', custom: () => !calculateThermistor({ comparisonR1: 5, comparisonR2: 5, beta: 3950, temperature: 25 }).ok }]
  },
  {
    id: '15-02-05', slug: '2022-conductive-rope', year: 2022, title: '一根绳的长度，怎样藏在电阻里', shortTitle: '弹性导电绳', topic: '传感与控制', family: 'conductiveRope', scene: 'ropeSensor',
    lead: '保持同一电压，两次测流得到导电绳支路电流；电阻再经原题 R—L 图线反演长度。可选迟滞用来观察加载历史造成的歧义。',
    sourceBoundary: '原题图线覆盖约 51.00—52.00 cm、1.15—1.38 kΩ，并给出 R=1.33 kΩ 时 L=51.80 cm。页面以清晰题图拟合局部斜率约 0.23 kΩ/cm；迟滞量是可关闭的扩展示意。',
    modelNote: '原题锚点固定为 1.33 kΩ@51.80 cm，仅在 51.00—52.00 cm 内作线性读图。默认迟滞为 0；启用迟滞后页面会标明它不属于原题数据。',
    parameters: [parameter('voltage', '两次测量保持电压 U', 'V', .1, 5, .01, 1.33, '标准化比较测阻'), parameter('current1', 'S₂断开总电流 I₁', 'mA', .1, 8, .01, 1, '标准化比较测阻'), parameter('current2', 'S₂闭合总电流 I₂', 'mA', .2, 10, .01, 2, '标准化比较测阻'), parameter('loadingSlope', '原图局部斜率', 'kΩ/cm', .1, .4, .01, .23, '原题图线拟合'), parameter('hysteresis', '卸载迟滞 ΔR', 'kΩ', 0, .1, .005, 0, '扩展示意')],
    metrics: [metric('loadingLength', '加载路径反演长度', 'cm', 2), metric('unloadingLength', '卸载路径反演长度', 'cm', 2), metric('lengthDifference', '路径差', 'cm', 2), metric('measuredResistance', '当前电阻', 'kΩ', 2)],
    chart: { title: '原题局部 R—L 标定与可选迟滞', xLabel: 'L / cm', yLabel: 'R / kΩ', primaryLabel: '原题拟合线', secondaryLabel: '卸载扩展', includeZero: false, cursorMode: 'operating-point', cursorValue: (phase, result) => phase < .75 ? result.loadingLength : result.unloadingLength }, bookPhase: .55, phases: ['51.00 cm起点', '缓慢加载', '接近锚点', '读出长度', '可选卸载'],
    tests: [{ name: '保持同一电压时增量测流回归 Rₓ=U/(I₂−I₁)=1.33 kΩ', check: (r) => near(r.measuredResistance, 1.33) }, { name: '原题锚点回归 1.33 kΩ→51.80 cm', check: (r) => near(r.loadingLength, 51.8) }, { name: '原图端点拟合约为 51.00→1.15、52.00→1.38 kΩ', check: (r) => near(r.chart[0].y, 1.146, .002) && near(r.chart[r.chart.length - 1].y, 1.376, .002) }, { name: '迟滞为零时只有原题拟合线，越界输入被拒绝', custom: () => { const r = calculateConductiveRope({ voltage: 1.35, current1: 1, current2: 2, loadingSlope: .23, hysteresis: 0 }); const invalid = calculateConductiveRope({ voltage: 2, current1: 1, current2: 2, loadingSlope: .23, hysteresis: 0 }); return r.ok && near(r.loadingLength, r.unloadingLength) && r.chart.every((point) => !('y2' in point)) && !invalid.ok; } }]
  },
  {
    id: '15-02-04', slug: '2023-saltwater-conductivity', year: 2023, title: '一池盐水，电阻怎样变成电导率', shortTitle: '盐水电导率', topic: '传感与控制', family: 'saline', scene: 'saline',
    lead: '电路先反演样品电阻，再用电极几何把电阻换成电导率；温度始终是结果的一部分。',
    sourceBoundary: '原题电路与数据为 R₁=500 Ω、R₂=500 Ω、R₃=600 Ω、R₄=200 Ω；S₂断开、闭合时电流表分别读 10 mA、15 mA。由 R₃/R₄ 分流可得样品回路总电流 40 mA、60 mA，并反演盐水电阻 100 Ω。电极几何采用标准化输入。',
    modelNote: 'S₂断开时左侧为 R₂，闭合时为 R₁∥R₂；右侧始终为 R₃∥R₄，电流表位于 R₃ 支路。两状态共用同一电源电动势。电导率采用均匀电场近似 σ=l/(RA)，忽略电极极化、边缘场和交流细节。',
    parameters: [parameter('meterOpen', 'S₂断开电流表读数', 'mA', 1, 15, .5, 10, '原题读数（量程15 mA）'), parameter('meterClosed', 'S₂闭合电流表读数', 'mA', 1, 15, .5, 15, '原题读数（量程15 mA）'), parameter('resistor1', '电阻 R₁', 'Ω', 100, 1000, 10, 500, '原题参数'), parameter('resistor2', '电阻 R₂', 'Ω', 100, 1000, 10, 500, '原题参数'), parameter('resistor3', '电阻 R₃', 'Ω', 100, 1000, 10, 600, '原题参数'), parameter('resistor4', '电阻 R₄', 'Ω', 50, 800, 10, 200, '原题参数'), parameter('electrodeGap', '电极间距 l', 'm', .005, .1, .001, .02, '标准化输入'), parameter('electrodeArea', '有效面积 A', 'm²', .0001, .002, .0001, .0004, '标准化输入'), parameter('temperature', '盐水温度', '℃', 0, 80, 1, 25, '测量条件')],
    metrics: [metric('resistance', '反演样品电阻', 'Ω', 1), metric('conductivity', '电导率', 'S/m', 3), metric('voltageA', '共同电源电压', 'V', 2), metric('temperature', '测量温度', '℃', 1)], metricTransforms: { temperature: (_, p) => p.temperature },
    chart: { title: '开关两状态的样品回路总电流', xLabel: 'S₂断开 / 闭合', yLabel: 'I / mA', cursorMode: 'none' }, bookPhase: .62, phases: ['核对四个电阻', 'S₂断开读10 mA', 'S₂闭合读15 mA', '分流得到40/60 mA', '反演盐水电阻'],
    tests: [{ name: '原题四电阻与10/15 mA回归 Rₓ=100 Ω、样品总流40/60 mA', check: (r) => near(r.resistance, 100) && near(r.currentOpen, 40) && near(r.currentClosed, 60) && near(r.rightEquivalent, 150) }, { name: '两状态共用同一30 V电源', check: (r) => near(r.voltageA, 30) && near(r.voltageB, 30) && near(r.voltageMismatch, 0) }, { name: '电极间距加倍时 σ 加倍（R、A 固定）', custom: () => { const base = { meterOpen: 10, meterClosed: 15, resistor1: 500, resistor2: 500, resistor3: 600, resistor4: 200, electrodeArea: .0004, temperature: 25 }; const a = calculateSaline({ ...base, electrodeGap: .02 }); const b = calculateSaline({ ...base, electrodeGap: .04 }); return near(b.conductivity, 2 * a.conductivity); } }]
  },
  {
    id: '15-02-03', slug: '2024-light-tracker', year: 2024, title: '两束电压怎样把电池板带向光源', shortTitle: '光源跟踪装置', topic: '传感与控制', family: 'lightTracker', scene: 'lightTracker',
    lead: '隔板制造两只光敏电阻的受光差，电压差决定转向；闭环不断缩小误差，直到进入停止死区。',
    sourceBoundary: '原题读数 U₁=1.60 V、U₂=1.17 V 支持弱光侧光敏电阻更大；原图跟踪态 U₁<U₂ 时电池板逆时针转动，并以 U₁=U₂ 为停止条件。角度、灵敏度、死区与电机速度均为标准化控制参数。',
    modelNote: '两传感器完全对称，差分电压按 sin(角度误差) 近似；忽略电机惯性、环境光与元件离散性。',
    parameters: [parameter('lightAngle', '光源方向', '°', -80, 80, 1, 30, '标准化输入'), parameter('panelAngle', '电池板初始角', '°', -80, 80, 1, -20, '标准化输入'), parameter('sensitivity', '差分灵敏度', 'V', .05, 1, .01, .45, '标准化输入'), parameter('deadZone', '停止死区 |ΔU|', 'V', 0, .3, .01, .05, '标准化输入'), parameter('motorSpeed', '电机角速度', '°/s', 1, 60, 1, 20, '标准化输入')],
    metrics: [metric('initialError', '初始角误差', '°', 1), metric('initialDifference', '初始差分电压', 'V', 3), metric('turnTime', '预计转动时间', 's', 2), metric('finalError', '停止时角误差', '°', 1)],
    chart: { title: '闭环中的差分电压与角度误差', xLabel: 't / s', yLabel: 'ΔU / V', primaryLabel: '差分电压 ΔU', secondaryLabel: '角度误差', secondaryYLabel: '角误差 / °', cursorMode: 'process-time', cursorValue: (phase, result) => result.chart[result.chart.length - 1].x * phase }, bookPhase: .45, phases: ['读取两路电压', '判断方向', '低速点动', '再次比较', '进入死区'],
    tests: [{ name: '原题测试读数回归 U₁=1.60 V、U₂=1.17 V', check: (r) => near(r.originalVoltage1, 1.60) && near(r.originalVoltage2, 1.17) && r.originalDarkerSideHasLargerResistance }, { name: '原图 U₁<U₂ 时回归逆时针转动', check: (r) => r.originalTrackingDirection === 'counterclockwise' }, { name: '默认点动在死区边缘停止并保留约 3.18° 误差', check: (r, p) => near(Math.abs(r.finalError), Math.asin(p.deadZone / (2 * p.sensitivity)) * 180 / Math.PI) && near(r.turnTime, (Math.abs(r.initialError) - Math.abs(r.finalError)) / p.motorSpeed) }, { name: '死区内停机，视场外或死区覆盖全量程时拒绝', custom: () => { const stopped = calculateLightTracker({ lightAngle: 1, panelAngle: 0, sensitivity: .45, deadZone: .05, motorSpeed: 20 }); const outOfView = calculateLightTracker({ lightAngle: 80, panelAngle: -20, sensitivity: .45, deadZone: .05, motorSpeed: 20 }); const invalidZone = calculateLightTracker({ lightAngle: 30, panelAngle: -20, sensitivity: .1, deadZone: .2, motorSpeed: 20 }); return stopped.ok && !stopped.active && !outOfView.ok && !invalidZone.ok; } }, { name: '交换左右后差分与转向同时反号', custom: () => { const a = calculateLightTracker({ lightAngle: 30, panelAngle: -20, sensitivity: .45, deadZone: .05, motorSpeed: 20 }); const b = calculateLightTracker({ lightAngle: -30, panelAngle: 20, sensitivity: .45, deadZone: .05, motorSpeed: 20 }); return near(a.initialDifference, -b.initialDifference) && a.direction === -b.direction; } }]
  },
  {
    id: '15-02-02', slug: '2025-eddy-current-brake', year: 2025, title: '看不见的涡流，怎样让圆盘慢下来', shortTitle: '涡流制动装置', topic: '电磁过程', family: 'eddyBrake', scene: 'eddyBrake',
    lead: '先用 B—I 图线把电流标定成磁场，再观察同一初始转速下的衰减。控制量与物理量在这里不能混写。',
    sourceBoundary: '原题给出最大电流 0.58 A、读数 0.48 A、B—I 斜率 30 mT/A，并确认 B 越大制动时间越短；衰减系数和初始转速为标准化模型。',
    modelNote: '标准化模型取 dω/dt=-γω 且 γ∝B²，只用于比较趋势；真实圆盘可能同时有轴承摩擦、风阻和非线性涡流。',
    parameters: [parameter('current', '电磁铁电流 I', 'A', 0, .58, .01, .48, '原题读数'), parameter('calibrationSlope', 'B—I 斜率', 'mT/A', 5, 60, 1, 30, '原题读图'), parameter('initialSpeed', '初始角速度', 'rad/s', 1, 30, .5, 12, '标准化输入'), parameter('dampingAt15mT', '15 mT参考阻尼率', 's⁻¹', .1, 3, .1, .9, '标准化输入')],
    metrics: [metric('fieldMilliTesla', '磁感应强度 B', 'mT', 1), metric('dampingRate', '衰减率 γ', 's⁻¹', 3), metric('timeToTenPercent', '降至10%用时', 's', 2), metric('current', '线圈电流', 'A', 2)], metricTransforms: { current: (_, p) => p.current },
    chart: { title: '标准化转速衰减', xLabel: 't / s', yLabel: 'ω / (rad·s⁻¹)', cursorMode: 'process-time', cursorValue: (phase, result) => result.chart[result.chart.length - 1].x * phase }, bookPhase: .65, phases: ['圆盘稳态转动', '断开电机', '进入磁场', '涡流制动', '低速尾段'],
    tests: [{ name: '原题读数回归 B=14.4 mT', check: (r) => near(r.fieldMilliTesla, 14.4) }, { name: 'B=0 时标准化制动率为 0', custom: () => near(calculateEddyBrake({ current: 0, calibrationSlope: 30, initialSpeed: 12, dampingAt15mT: .9 }).dampingRate, 0) }, { name: '电流增大使降至10%用时缩短', custom: () => { const a = calculateEddyBrake({ current: .3, calibrationSlope: 30, initialSpeed: 12, dampingAt15mT: .9 }); const b = calculateEddyBrake({ current: .5, calibrationSlope: 30, initialSpeed: 12, dampingAt15mT: .9 }); return b.timeToTenPercent < a.timeToTenPercent; } }]
  },
  {
    id: '15-02-01', slug: '2026-cotton-moisture', year: 2026, title: '棉花含水多少，为什么要先压到同一状态', shortTitle: '棉花回潮率', topic: '传感与控制', family: 'cotton', scene: 'cotton',
    lead: '弹簧先把压力变成可控条件，电路再测电阻，最后才由定标曲线反演材料状态。任何一步缺失，回潮率都失去依据。',
    sourceBoundary: '本地原题图可核对真实装置、R—R₀—R_c测量电路、S₂跨接 R_c 与六档电阻箱；后续 R₂ 数值和回潮率定标曲线仍缺失。页面保留同偏转测 R_c 的原题电路逻辑，不生成原题回潮率答案。',
    modelNote: '先用 F=kx 统一压紧状态；S₂闭合时旁路 R_c，S₂断开时串入 R_c，调电阻箱使表头同偏转可得 R_c=R₁−R₂。归一化含水指标只在用户给定的干、湿锚点间插值，明确属于扩展示意。',
    parameters: [parameter('springConstant', '弹簧劲度系数 k', 'N/mm', .1, 5, .1, 1, '标准化输入'), parameter('compression', '弹簧压缩量 x', 'mm', 0, 40, .5, 20, '标准化输入'), parameter('minimumForce', '示意压力门槛', 'N', 1, 40, 1, 15, '标准化门禁'), parameter('boxBefore', 'S₂闭合时电阻箱 R₁', 'kΩ', 1, 20, .1, 10, '标准化替代测阻'), parameter('boxAfter', 'S₂断开时电阻箱 R₂', 'kΩ', .5, 19, .1, 4, '标准化替代测阻'), parameter('dryResistance', '示意干态锚点', 'kΩ', 5, 20, .5, 10, '标准化定标'), parameter('wetResistance', '示意湿态锚点', 'kΩ', .5, 8, .5, 2, '标准化定标')],
    metrics: [metric('pressureForce', '当前压力', 'N', 1), metric('moistureIndex', '归一化含水指标', '%', 0), metric('measuredResistance', '棉花电阻', 'kΩ', 1), metric('compression', '压缩量', 'mm', 1)], metricTransforms: { moistureIndex: (v) => v * 100, compression: (_, p) => p.compression },
    chart: { title: '示意定标曲线（非原题数据）', xLabel: '归一化含水指标', yLabel: 'R / kΩ', cursorMode: 'operating-point', cursorValue: (_phase, result) => result.moistureIndex }, bookPhase: .84, phases: ['弹簧标定', '装入棉花', '压到目标状态', '替代测阻', '查示意曲线'],
    tests: [{ name: '胡克定律 F=kx', check: (r) => near(r.pressureForce, 20) }, { name: '替代法同偏转满足 R_c=R₁-R₂=6 kΩ', check: (r) => near(r.measuredResistance, 6) }, { name: '干湿锚点中值对应 50%', check: (r) => near(r.moistureIndex, .5) }, { name: '压力不足时锁住归一化读数', custom: () => !finite(calculateCotton({ springConstant: 1, compression: 5, minimumForce: 15, boxBefore: 10, boxAfter: 4, dryResistance: 10, wetResistance: 2 }).moistureIndex) }]
  },
  {
    id: '06-03-05', slug: '2021-abacus-collision', year: 2021, title: '两颗算珠，为什么恰好停在边框前', shortTitle: '算盘算珠碰撞', topic: '碰撞与动量', family: 'abacus', scene: 'abacus',
    lead: '摩擦先改变碰前速度，极短碰撞再分配动量，摩擦随后决定停止位置。三个阶段缺一不可。',
    sourceBoundary: 'v₀=0.4 m/s、μ=0.1、s₁=3.5 cm、s₂=2.0 cm、碰后甲速 0.1 m/s、g=10 m/s² 均来自 2021 广东原题。',
    modelNote: '两算珠等质量；滑动摩擦恒定；碰撞时间极短且外力冲量忽略；运动沿同一直线。',
    parameters: [parameter('initialSpeed', '甲初速度 v₀', 'm/s', .05, 1, .01, .4, '原题参数'), parameter('friction', '动摩擦因数 μ', '', 0, .5, .01, .1, '原题参数'), parameter('firstGap', '甲乙间距 s₁', 'm', .005, .1, .001, .035, '原题参数'), parameter('secondGap', '乙到边框 s₂', 'm', .005, .1, .001, .02, '原题参数'), parameter('beadAAfter', '碰后甲速度', 'm/s', 0, .5, .01, .1, '原题参数'), parameter('gravity', '重力加速度 g', 'm/s²', 1, 20, .1, 10, '原题参数')],
    metrics: [metric('speedAtCollision', '甲碰前速度', 'm/s', 2), metric('beadBAfter', '乙碰后速度', 'm/s', 2), metric('stoppingDistanceB', '乙停止距离', 'm', 3), metric('totalTimeA', '甲总运动时间', 's', 2)],
    chart: { title: '两颗算珠的位置—时间', xLabel: 't / s', yLabel: 'x / m', primaryLabel: '甲', secondaryLabel: '乙', cursorMode: 'process-time', cursorValue: (phase, result) => result.chart[result.chart.length - 1].x * phase }, bookPhase: .34, phases: ['甲受摩擦滑行', '碰撞前', '极短碰撞', '两珠分别减速', '停止/触框'],
    tests: [{ name: '原题甲碰前速度 0.30 m/s', check: (r) => near(r.speedAtCollision, .3) }, { name: '原题乙碰后速度 0.20 m/s', check: (r) => near(r.beadBAfter, .2) }, { name: '乙停止距离恰为 s₂=0.020 m', check: (r) => near(r.stoppingDistanceB, .02) }, { name: '甲总运动时间 0.20 s 且碰撞相位来自真实时刻', check: (r) => near(r.totalTimeA, .2) && near(r.collisionPhase, r.timeBefore / r.horizon) }, { name: 'μ=0零速分支与再次碰撞均有明确边界', custom: () => { const moving = calculateAbacus({ initialSpeed: .4, friction: 0, firstGap: .035, secondGap: .02, beadAAfter: .1, gravity: 10 }); const aStops = calculateAbacus({ initialSpeed: .4, friction: 0, firstGap: .035, secondGap: .2, beadAAfter: 0, gravity: 10 }); const bothStop = calculateAbacus({ initialSpeed: .4, friction: .16 / (.7), firstGap: .035, secondGap: .02, beadAAfter: 0, gravity: 10 }); const repeats = calculateAbacus({ initialSpeed: .4, friction: 0, firstGap: .035, secondGap: .2, beadAAfter: .25, gravity: 10 }); return moving.ok && !finite(moving.totalTimeA) && moving.chart.every((point) => point.y2 <= moving.framePosition + 1e-12) && aStops.ok && near(aStops.totalTimeA, aStops.timeBefore) && bothStop.ok && near(bothStop.beadBAfter, 0) && near(bothStop.stoppingDistanceB, 0) && !repeats.ok; } }]
  },
  {
    id: '06-02-01', slug: '2023-electric-curtain', year: 2023, title: '电机仍在拉，碰撞为什么不再守恒', shortTitle: '电动窗帘', topic: '碰撞与动量', family: 'curtain', scene: 'curtain',
    lead: '碰撞很短，电机的外力冲量仍被题目保留。系统动量多出的部分应与这段外冲量逐项对上。',
    sourceBoundary: '两滑块各 1 kg、碰前 0.40 m/s、碰后共同 0.22 m/s、碰撞 0.04 s 均来自 2023 广东原题。',
    modelNote: '轨道阻力忽略；滑块2初始静止；碰后粘连；电机在碰撞期间提供近似恒定外力。',
    parameters: [parameter('mass1', '滑块1质量 m₁', 'kg', .1, 5, .1, 1, '原题参数'), parameter('mass2', '滑块2质量 m₂', 'kg', .1, 5, .1, 1, '原题参数'), parameter('beforeSpeed1', '滑块1碰前速度', 'm/s', .05, 1, .01, .4, '原题参数'), parameter('beforeSpeed2', '滑块2碰前速度', 'm/s', 0, 1, .01, 0, '原题参数'), parameter('motorForce', '碰撞期间电机力', 'N', 0, 10, .1, 1, '由原题结果反演'), parameter('contactTime', '碰撞时间', 's', .005, .2, .005, .04, '原题参数')],
    metrics: [metric('externalImpulse', '系统外力冲量', 'N·s', 2), metric('motorForce', '电机平均力', 'N', 2), metric('cart1Impulse', '滑块1合冲量', 'N·s', 2), metric('contactForce', '对滑块2平均力', 'N', 1)],
    chart: { title: '系统动量：保留电机与关闭电机', xLabel: 't / s', yLabel: 'p / (kg·m·s⁻¹)', primaryLabel: '保留电机', secondaryLabel: '关闭电机', cursorMode: 'process-time', cursorValue: (phase, _result, input) => input.contactTime * clamp((phase - .5) / .11, 0, 1) }, bookPhase: .56, phases: ['滑块1接近', '开始接触', '碰撞与牵引并存', '达到共同速度', '整体前进'],
    tests: [{ name: '原题共同速度回归 0.22 m/s', check: (r) => near(r.commonSpeed, .22) }, { name: '系统外冲量回归 0.04 N·s', check: (r) => near(r.externalImpulse, .04) }, { name: '滑块1合冲量大小 0.18 N·s', check: (r) => near(Math.abs(r.cart1Impulse), .18) }, { name: '滑块2平均作用力 5.5 N', check: (r) => near(r.contactForce, 5.5) }, { name: '关闭电机回归0.20 m/s，无法追及时拒绝碰撞', check: (r) => near(r.noMotorCommonSpeed, .2) && !calculateCurtain({ mass1: 1, mass2: 1, beforeSpeed1: .2, beforeSpeed2: .2, motorForce: 1, contactTime: .04 }).ok }]
  },
  {
    id: '06-03-04', slug: '2026-spherical-robot', year: 2026, title: '碰挡板、腾空、落地：模型何时必须切换', shortTitle: '球形机器人', topic: '碰撞与动量', family: 'robot', scene: 'robot',
    lead: '摆锤上摆、撞击挡板、整体腾空和外壳落地各用不同研究对象。页面把五个事件暂停点和能量台账放在一起。',
    sourceBoundary: 'M=4 kg、两摆锤各 m=1 kg、R=0.4 m、v₀=4 m/s、g=10 m/s² 均来自 2026 广东原题。',
    modelNote: '上摆与腾空阶段机械能守恒；极短碰挡板阶段仅沿竖直方向用题设动量模型；落地时外壳速度清零，摆锤保持速度并分离。',
    parameters: [parameter('totalMass', '机器人总质量 M', 'kg', 1, 10, .1, 4, '原题参数'), parameter('hammerMass', '单摆锤质量 m', 'kg', .1, 3, .1, 1, '原题参数'), parameter('radius', '摆长 R', 'm', .1, 1, .05, .4, '原题参数'), parameter('initialSpeed', '摆锤初速度 v₀', 'm/s', .5, 8, .1, 4, '原题参数'), parameter('gravity', '重力加速度 g', 'm/s²', 1, 20, .1, 10, '原题参数')],
    metrics: [metric('hammerSpeed', '碰挡板前摆锤速度', 'm/s', 3), metric('commonSpeed', '碰后共同速度', 'm/s', 3), metric('kineticAfterImpact', '碰后动能', 'J', 2), metric('jumpHeight', '外壳上升高度', 'm', 2), metric('energyLoss', '首次落地总损失', 'J', 2)],
    chart: { title: '五个事件节点的机械能台账', xLabel: '事件序号', yLabel: 'E / J', cursorMode: 'process-time', cursorValue: (phase) => clamp(phase * 5, 0, 4) }, bookPhase: .82, phases: ['摆锤上摆', '碰挡板前', '碰后起跳', '最高点/落地前', '落地后分离'],
    tests: [{ name: '碰前摆锤速度 2√2 m/s', check: (r) => near(r.hammerSpeed, 2 * Math.sqrt(2)) }, { name: '碰后共同速度 √2 m/s', check: (r) => near(r.commonSpeed, Math.sqrt(2)) }, { name: '碰后动能 4 J', check: (r) => near(r.kineticAfterImpact, 4) }, { name: '上升高度 0.10 m', check: (r) => near(r.jumpHeight, .1) }, { name: '首次落地后总损失 6 J', check: (r) => near(r.energyLoss, 6) }, { name: 'v₀²<2gR 时拒绝到达挡板', custom: () => !calculateRobot({ totalMass: 4, hammerMass: 1, radius: .4, initialSpeed: 2, gravity: 10 }).ok }]
  },
  {
    id: '13-02-05', slug: '2022-rope-wave', year: 2022, title: '波峰向前走，绳上的红点去了哪里', shortTitle: '软绳简谐波', topic: '振动与波', family: 'ropeWave', scene: 'ropeWave',
    lead: '波形向前传播，介质质点只在平衡位置附近振动。固定标记把这两种运动同时显示出来。',
    sourceBoundary: '原题只要求半周期后质点位置与“加快抖动时波速不变”。振幅、波速、频率和标记位置采用标准化输入。',
    modelNote: '同一根理想软绳、张力不变，波速由介质条件决定；频率改变时 λ=v/f 随之改变。',
    parameters: [parameter('amplitude', '振幅 A', 'm', .02, .3, .01, .15, '标准化输入'), parameter('waveSpeed', '波速 v', 'm/s', .2, 5, .1, 2, '标准化输入'), parameter('frequency', '振源频率 f', 'Hz', .2, 5, .1, 1.5, '标准化输入'), parameter('markerX', '标记平衡位置 xₘ', 'm', 0, 5, .05, 0, '标准化输入')],
    metrics: [metric('wavelength', '波长 λ', 'm', 2), metric('period', '周期 T', 's', 2), metric('markerInitial', '标记初始位移', 'm', 2), metric('markerHalfPeriod', '半周期后位移', 'm', 2)],
    chart: { title: '同一时刻的 y—x 波形', xLabel: 'x / m', yLabel: 'y / m', cursorMode: 'probe', cursorValue: (_phase, _result, input) => input.markerX }, bookPhase: .5, phases: ['t=0', 't=T/4', 't=T/2', 't=3T/4', 't=T'],
    tests: [{ name: '半周期后固定质点位移反号', check: (r) => near(r.markerHalfPeriod, -r.markerInitial) }, { name: '同一介质中频率翻倍，波速不变且波长减半', custom: () => { const a = calculateRopeWave({ amplitude: .15, waveSpeed: 2, frequency: 1.5, markerX: .3 }); const b = calculateRopeWave({ amplitude: .15, waveSpeed: 2, frequency: 3, markerX: .3 }); return near(b.wavelength, a.wavelength / 2); } }, { name: '指定质点推进一周期后真实回到初位移', check: (r) => near(r.markerAfterPeriod, r.markerInitial) }, { name: '整条初始波形满足|y|≤A且标记在图域内', check: (r, p) => r.chart.every((point) => Math.abs(point.y) <= p.amplitude + 1e-12) && r.chart[0].x <= p.markerX && r.chart[r.chart.length - 1].x >= p.markerX }]
  },
  {
    id: '13-02-02', slug: '2024-wave-snapshot', year: 2024, title: '一张波形图，怎样走到一秒以后', shortTitle: '简谐横波波形图', topic: '振动与波', family: 'travelingWave', scene: 'travelingWave',
    lead: '上方波形沿 +x 平移，下方固定质点只记录自己的 y—t 历史；两幅图在探针位置必须始终同值。',
    sourceBoundary: 'v=1 m/s、λ=2 m、A=0.1 m、t=1 s、x=1.5 m 来自 2024 广东原题及题图读值。',
    modelNote: '采用 y=A sin[2π(x-vt)/λ] 复现题图相位，波沿 +x 传播且不衰减。',
    parameters: [parameter('amplitude', '振幅 A', 'm', .02, .3, .01, .1, '原题读图'), parameter('waveSpeed', '波速 v', 'm/s', .1, 5, .1, 1, '原题参数'), parameter('wavelength', '波长 λ', 'm', .5, 5, .1, 2, '原题读图'), parameter('probeX', '探针位置 x', 'm', 0, 6, .1, 1.5, '原题参数'), parameter('probeTime', '观察时刻 t', 's', 0, 6, .1, 1, '原题参数')],
    metrics: [metric('period', '周期 T', 's', 2), metric('frequency', '频率 f', 'Hz', 2), metric('probeDisplacement', '探针位移', 'm', 2), metric('probeTime', '观察时刻', 's', 1)], metricTransforms: { probeTime: (_, p) => p.probeTime },
    chart: { title: '观察时刻的 y—x 波形', xLabel: 'x / m', yLabel: 'y / m', cursorMode: 'probe', cursorValue: (_phase, _result, input) => input.probeX }, bookPhase: .5, phases: ['题设时刻 t₀', 't₀+T/4', 't₀+T/2', 't₀+3T/4', 't₀+T'],
    tests: [{ name: '原题 t=1 s、x=1.5 m 时 y=0.10 m', check: (r) => near(r.probeDisplacement, .1) }, { name: '原题周期 T=2 s', check: (r) => near(r.period, 2) }, { name: '推进一周期同点位移不变且探针始终在图域内', custom: () => { const a = calculateTravelingWave({ amplitude: .1, waveSpeed: 1, wavelength: 2, probeX: 6, probeTime: 0 }); const b = calculateTravelingWave({ amplitude: .1, waveSpeed: 1, wavelength: 2, probeX: 6, probeTime: 2 }); return near(a.probeDisplacement, b.probeDisplacement) && a.chart[0].x <= 6 && a.chart[a.chart.length - 1].x >= 6; } }]
  },
  {
    id: '13-01-02', slug: '2021-spring-oscillator', year: 2021, title: '从端点释放，前八分之一周期走了多远', shortTitle: '竖直弹簧振子', topic: '振动与波', family: 'springOscillator', scene: 'springOscillator',
    lead: '端点附近速度很小，靠近平衡位置速度增大。位移、速度与动能在同一相位轴上同步推进。',
    sourceBoundary: '原题给出符号 A、T，不给具体数值。默认 A=0.10 m、T=2.0 s 只用于可视化，t 默认取 T/8。',
    modelNote: '以最低点为 x=+A，从静止释放；x=A cos(2πt/T)，平衡位置为 x=0。',
    parameters: [parameter('amplitude', '振幅 A', 'm', .02, .5, .01, .1, '标准化输入'), parameter('period', '周期 T', 's', .5, 6, .1, 2, '标准化输入'), parameter('time', '观察时刻 t', 's', 0, 6, .05, .25, '对应原题 T/8')],
    metrics: [metric('displacement', '相对平衡位置 x', 'm', 3), metric('heightAboveLowest', '相对最低点高度', 'm', 3), metric('heightFraction', '相对最低点高度/A', '%', 1), metric('kineticFraction', '动能/最大动能', '%', 1)], metricTransforms: { heightFraction: (v) => v * 100, kineticFraction: (v) => v * 100 },
    chart: { title: '位移与动能随相位变化', xLabel: 't / s', yLabel: 'x / m', primaryLabel: '位移 x', secondaryLabel: '归一化动能', secondaryYLabel: 'Eₖ/Eₖ,max', cursorMode: 'process-time', cursorValue: (phase, _result, input) => ((input.time + phase * input.period) % input.period + input.period) % input.period }, bookPhase: 0, phases: ['题设时刻 t₀', 't₀+T/4', 't₀+T/2', 't₀+3T/4', 't₀+T'],
    tests: [{ name: 'T/8 相对最低点高度小于 A/2', check: (r) => r.heightFraction < .5 }, { name: 'T/8 相对最低点高度为 (1-√2/2)A', check: (r) => near(r.heightFraction, 1 - Math.sqrt(2) / 2) }, { name: 'T/4 动能达到最大', custom: () => near(calculateSpringOscillator({ amplitude: .1, period: 2, time: .5 }).kineticFraction, 1) }]
  },
  {
    id: '13-01-01', slug: '2025-forced-doppler', year: 2025, title: '共振峰和频移，分别在比较什么', shortTitle: '受迫振动与多普勒', topic: '振动与波', family: 'forcedDoppler', scene: 'forcedDoppler',
    lead: '左侧幅频曲线标出当前驱动力频率与系统响应；右侧改变相对速度，观察接收频率。两种现象共享“频率”，物理条件并不相同。',
    sourceBoundary: '原题为概念选择题，没有装置数值。固有频率、阻尼、声源频率和相对速度均为标准化演示参数。',
    modelNote: '受迫振动采用线性稳态幅频响应；多普勒采用静止观察者、移动声源的一维近似，正速度表示靠近。',
    parameters: [parameter('naturalFrequency', '系统固有频率 f₀', 'Hz', .5, 8, .1, 2, '标准化输入'), parameter('driveFrequency', '驱动力频率 f_d', 'Hz', .2, 12, .1, 2, '标准化输入'), parameter('dampingRatio', '阻尼比 ζ', '', .02, .4, .01, .08, '标准化输入'), parameter('sourceFrequency', '声源频率', 'Hz', 100, 2000, 10, 800, '标准化输入'), parameter('soundSpeed', '声速 c', 'm/s', 250, 400, 1, 340, '标准化输入'), parameter('relativeSpeed', '声源靠近速度', 'm/s', -60, 60, 1, 20, '标准化输入')],
    metrics: [metric('ratio', '频率比 f_d/f₀', '', 2), metric('response', '稳态响应倍数', '', 2), metric('receivedFrequency', '接收频率', 'Hz', 1), metric('frequencyShift', '频移', 'Hz', 1)],
    chart: { title: '标准化受迫振动幅频曲线', xLabel: 'f_d / Hz', yLabel: '响应倍数', cursorMode: 'operating-point', cursorValue: (_phase, _result, input) => input.driveFrequency }, bookPhase: .25, phases: ['平衡位置向右', '右端附近', '回到平衡', '左端附近', '完成一周期'],
    tests: [{ name: '改变驱动力频率不改变系统固有频率', custom: () => { const common = { naturalFrequency: 2, dampingRatio: .08, sourceFrequency: 800, soundSpeed: 340, relativeSpeed: 0 }; const lowDrive = calculateForcedDoppler({ ...common, driveFrequency: 1 }); const highDrive = calculateForcedDoppler({ ...common, driveFrequency: 4 }); return lowDrive.ok && highDrive.ok && near(lowDrive.naturalFrequency, highDrive.naturalFrequency) && !near(lowDrive.driveFrequency, highDrive.driveFrequency); } }, { name: '默认共振响应6.25倍、靠近20 m/s时接收850 Hz', check: (r) => near(r.response, 6.25) && near(r.receivedFrequency, 850) }, { name: '远离时接收频率降低', custom: () => calculateForcedDoppler({ naturalFrequency: 2, driveFrequency: 2, dampingRatio: .08, sourceFrequency: 800, soundSpeed: 340, relativeSpeed: -20 }).receivedFrequency < 800 }, { name: '驱动接近固有频率时响应高于远离共振', custom: () => { const a = calculateForcedDoppler({ naturalFrequency: 2, driveFrequency: 2, dampingRatio: .08, sourceFrequency: 800, soundSpeed: 340, relativeSpeed: 0 }); const b = calculateForcedDoppler({ naturalFrequency: 2, driveFrequency: 4, dampingRatio: .08, sourceFrequency: 800, soundSpeed: 340, relativeSpeed: 0 }); return a.response > b.response; } }]
  },
  {
    id: '13-02-03', slug: '2023-echo-sounder', year: 2023, title: '一毫米波长，怎样找到水下目标', shortTitle: '回声探测器', topic: '振动与波', family: 'echoSounder', scene: 'echoSounder',
    lead: '频率和水中声速先决定波长；往返时间给出距离；目标相对运动还会改变回声频率。',
    sourceBoundary: '水中声速 1500 m/s、发射频率 1.5×10⁶ Hz 来自 2023 广东原题；目标距离与速度为标准化演示输入。',
    modelNote: '目标靠近速度为 u 时，声脉冲在 t₁=d/(c+u) 相遇，反射点为 cd/(c+u)，往返时间为 2d/(c+u)；频移采用理想一维移动反射体的双多普勒近似。u=0 时退化为 2d/c。',
    parameters: [parameter('soundSpeed', '水中声速 c', 'm/s', 1000, 1800, 10, 1500, '原题参数'), parameter('frequency', '发射频率 f', 'Hz', 100000, 3000000, 10000, 1500000, '原题参数'), parameter('distance', '目标距离 d', 'm', 1, 300, 1, 50, '标准化输入'), parameter('targetSpeed', '目标靠近速度 u', 'm/s', -20, 20, .5, 0, '标准化输入')],
    metrics: [metric('wavelength', '声波波长', 'm', 4), metric('echoTime', '回声往返时间', 's', 3), metric('echoFrequency', '回声频率', 'Hz', 0), metric('frequencyShift', '回声频移', 'Hz', 1)],
    chart: { title: '声脉冲的往返位置—时间', xLabel: 't / s', yLabel: '距探测器 / m', cursorMode: 'process-time', cursorValue: (phase, result) => result.echoTime * phase }, bookPhase: .62, phases: ['发射脉冲', '向目标传播', '到达并反射', '回波返回', '探测器接收'],
    tests: [{ name: '原题波长回归 1.0×10⁻³ m', check: (r) => near(r.wavelength, .001) }, { name: '静止目标回声频率等于发射频率', check: (r, p) => p.targetSpeed !== 0 || near(r.echoFrequency, p.frequency) }, { name: '目标靠近时回声频率升高', custom: () => calculateEchoSounder({ soundSpeed: 1500, frequency: 1500000, distance: 50, targetSpeed: 5 }).echoFrequency > 1500000 }, { name: 'u=5 m/s时移动反射点与往返时间满足相遇运动学', custom: () => { const r = calculateEchoSounder({ soundSpeed: 1500, frequency: 1500000, distance: 50, targetSpeed: 5 }); return r.ok && near(r.reflectionTime, 50 / 1505) && near(r.reflectionDistance, 75000 / 1505) && near(r.echoTime, 100 / 1505); } }]
  }
];

export function getGaokaoModelSpec(idOrSlug) {
  return GAOKAO_MODEL_SPECS.find((item) => item.id === idOrSlug || item.slug === idOrSlug);
}

export function calculateGaokaoModel(idOrSlug, values = {}) {
  const spec = getGaokaoModelSpec(idOrSlug);
  if (!spec) return fail(`未知高考模型：${idOrSlug}`);
  const input = readInputs(spec, values);
  const result = calculators[spec.family](input);
  return result.ok ? { ...result, input } : result;
}

export function runGaokaoModelTests(idOrSlug) {
  const spec = getGaokaoModelSpec(idOrSlug);
  if (!spec) return [{ name: '模型存在', pass: false, detail: `未知模型 ${idOrSlug}` }];
  const input = readInputs(spec);
  const result = calculators[spec.family](input);
  if (!result.ok) return [{ name: '默认参数可计算', pass: false, detail: result.error }];
  return spec.tests.map((test) => {
    try {
      const pass = Boolean(test.custom ? test.custom() : test.check(result, input));
      return { name: test.name, pass, detail: pass ? '通过' : '结果不满足预期' };
    } catch (error) {
      return { name: test.name, pass: false, detail: error instanceof Error ? error.message : String(error) };
    }
  });
}

export function runAllGaokaoModelTests() {
  return GAOKAO_MODEL_SPECS.flatMap((spec) => runGaokaoModelTests(spec.id).map((test) => ({ ...test, id: spec.id, title: spec.shortTitle })));
}
