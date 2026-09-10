import type { RoverMode, RoverTelemetry } from "./roverProtocol";

export interface DemoTelemetryOptions {
  mode?: RoverMode;
  estop?: boolean;
  fan?: boolean;
  tracker?: boolean;
  forward?: number;
  turn?: number;
}

export function createInitialTelemetry(): RoverTelemetry {
  return {
    raw: "ROVER,0,0,SAFE,0,0,0,7.40,0.00,0,0.0,0.0,0,0,0,0,-1,-1,0,0,0,0",
    seq: 0,
    ms: 0,
    mode: "SAFE",
    estop: false,
    leftPwm: 0,
    rightPwm: 0,
    batteryV: 7.4,
    solarW: 0,
    lux: 0,
    pitch: 0,
    roll: 0,
    obstacle: false,
    pit: false,
    fan: false,
    tracker: false,
    distF: -1,
    distD: -1,
    line: 0,
    speedL: 0,
    speedR: 0,
    dust: false,
    receivedAt: 0
  };
}

// 演示剧情的持续状态：积尘缓慢累积压低太阳能功率，开风扇快速清除。
// 这让"功率下降 → 除尘 → 恢复"的能源闭环不连真车也能讲清楚。
let dustLevel = 0.18;

export function createDemoTelemetry(sequence: number, options: DemoTelemetryOptions = {}): RoverTelemetry {
  const t = sequence / 6;
  const mode = options.mode ?? (options.estop ? "SAFE" : "MANUAL");
  const driving = !options.estop && mode !== "SAFE";

  // 驱动：MANUAL 用滑杆值；AUTO 模拟巡线小幅修正
  let forward = 0;
  let turn = 0;
  if (driving && mode === "MANUAL") {
    forward = Math.round(options.forward ?? 0);
    turn = Math.round(options.turn ?? 0);
  } else if (driving && mode === "AUTO") {
    forward = 35;
    turn = Math.round(14 * Math.sin(t / 1.6));
  }

  // 前方障碍剧情：周期性"接近一块岩石"再远离
  const obstacleCycle = sequence % 90;
  let distF = 900;
  if (obstacleCycle > 60) {
    distF = Math.max(120, 900 - (obstacleCycle - 60) * 55);
  } else {
    distF = 400 + 500 * Math.abs(Math.sin(t / 5));
  }
  const obstacle = distF < 200 && !options.estop;
  if (obstacle && forward > 0) forward = 0;

  // 坑洞剧情：偶发
  const pit = sequence % 130 > 124 && !options.estop;
  const distD = pit ? 220 : 58 + Math.round(4 * Math.sin(t));
  if (pit && forward > 0) forward = 0;

  const leftPwm = clampPwm((forward + turn) * 2.55);
  const rightPwm = clampPwm((forward - turn) * 2.55);
  const speedL = Math.round((leftPwm / 255) * 120);
  const speedR = Math.round((rightPwm / 255) * 120);

  // 积尘与除尘：风扇开 → 快速清灰；否则慢慢积灰
  if (options.fan) {
    dustLevel = Math.max(0, dustLevel - 0.045);
  } else {
    dustLevel = Math.min(0.75, dustLevel + 0.0035);
  }
  const dust = dustLevel > 0.4;

  // 光照与太阳能：追光器开 → 对准太阳，lux 与功率提升；积灰压低功率
  const sunPhase = 0.65 + 0.35 * Math.sin(t / 9);
  const trackerGain = options.tracker ? 1.0 : 0.62;
  const lux = Math.max(40, Math.round(32000 * sunPhase * trackerGain + 600 * Math.sin(t * 2)));
  const solarW = Math.max(0, 3.0 * sunPhase * trackerGain * (1 - dustLevel) + 0.08 * Math.sin(t * 3));

  const batteryV = clamp(7.55 - sequence * 0.00022 - Math.abs(forward) * 0.0016 + solarW * 0.012, 6.7, 8.35);

  const pitch = 3.6 * Math.sin(t / 3.2) + (pit ? -6 : 0);
  const roll = 2.8 * Math.cos(t / 2.7);

  // 五路循迹：AUTO 模式下黑线在探头下来回扫过
  let line = 0;
  if (mode === "AUTO" && driving) {
    const center = 2 + Math.round(1.4 * Math.sin(t / 1.6));
    line = 1 << clamp(center, 0, 4);
    if (Math.abs(Math.sin(t / 1.6)) < 0.4) line |= 1 << 2;
  }

  const fan = Boolean(options.fan);
  const tracker = Boolean(options.tracker);
  const estop = Boolean(options.estop);

  const raw = [
    "ROVER",
    sequence,
    sequence * 500,
    mode,
    estop ? 1 : 0,
    estop ? 0 : leftPwm,
    estop ? 0 : rightPwm,
    batteryV.toFixed(2),
    solarW.toFixed(2),
    lux.toFixed(0),
    pitch.toFixed(1),
    roll.toFixed(1),
    obstacle ? 1 : 0,
    pit ? 1 : 0,
    fan ? 1 : 0,
    tracker ? 1 : 0,
    Math.round(distF),
    Math.round(distD),
    line,
    estop ? 0 : speedL,
    estop ? 0 : speedR,
    dust ? 1 : 0
  ].join(",");

  return {
    raw,
    seq: sequence,
    ms: sequence * 500,
    mode,
    estop,
    leftPwm: estop ? 0 : leftPwm,
    rightPwm: estop ? 0 : rightPwm,
    batteryV,
    solarW,
    lux,
    pitch,
    roll,
    obstacle,
    pit,
    fan,
    tracker,
    distF: Math.round(distF),
    distD: Math.round(distD),
    line,
    speedL: estop ? 0 : speedL,
    speedR: estop ? 0 : speedR,
    dust,
    receivedAt: Date.now()
  };
}

export function appendTelemetry(history: RoverTelemetry[], telemetry: RoverTelemetry, limit = 160): RoverTelemetry[] {
  return [...history, telemetry].slice(-limit);
}

function clampPwm(value: number): number {
  return Math.max(-255, Math.min(255, Math.round(value)));
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}
