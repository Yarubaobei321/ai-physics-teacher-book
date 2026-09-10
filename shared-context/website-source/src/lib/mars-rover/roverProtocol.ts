export const ROVER_DEVICE_NAME_PREFIX = "ESP32-rover";

export const ROVER_SERVICE_UUID = "7b3f1000-6d75-4a7e-9f63-4d6172730001";
export const ROVER_TELEMETRY_UUID = "7b3f1001-6d75-4a7e-9f63-4d6172730001";
export const ROVER_COMMAND_UUID = "7b3f1002-6d75-4a7e-9f63-4d6172730001";

export type RoverMode = "MANUAL" | "AUTO" | "SAFE";
export type CommandKind = "MODE" | "DRIVE" | "ESTOP" | "CLEAR_ESTOP" | "FAN" | "TRACKER";

export interface RoverTelemetry {
  raw: string;
  seq: number;
  ms: number;
  mode: RoverMode;
  estop: boolean;
  leftPwm: number;
  rightPwm: number;
  batteryV: number;
  solarW: number;
  lux: number;
  pitch: number;
  roll: number;
  obstacle: boolean;
  pit: boolean;
  fan: boolean;
  tracker: boolean;
  distF: number; // 前方障碍距离 mm，-1 = 传感器不可用
  distD: number; // 前下对地距离 mm，-1 = 传感器不可用
  line: number; // 五路循迹位图 0-31，bit0=最左
  speedL: number; // 左代表轮 RPM
  speedR: number; // 右代表轮 RPM
  dust: boolean; // TCRT5000 积尘
  receivedAt: number;
}

export type TelemetryParseResult =
  | { ok: true; telemetry: RoverTelemetry }
  | { ok: false; raw: string; error: string };

export interface CommandPacket {
  seq: number;
  kind: CommandKind;
  payload: string[];
  text: string;
}

// 遥测包字段顺序：单一真源（协议 v0.2，去掉 PM2.5，新增 lux/dist/line/speed/dust）。
// 修改任何字段顺序/数量时，必须同步 firmware/src/shared/rover_protocol.h 的
// TelemetryField 枚举，否则两端会静默错位。
export const TELEMETRY_FIELD = {
  TAG: 0, // "ROVER"
  SEQ: 1,
  MS: 2,
  MODE: 3,
  ESTOP: 4,
  LEFT_PWM: 5,
  RIGHT_PWM: 6,
  BATTERY_V: 7,
  SOLAR_W: 8,
  LUX: 9,
  PITCH: 10,
  ROLL: 11,
  OBSTACLE: 12,
  PIT: 13,
  FAN: 14,
  TRACKER: 15,
  DIST_F: 16,
  DIST_D: 17,
  LINE: 18,
  SPEED_L: 19,
  SPEED_R: 20,
  DUST: 21
} as const;

export const TELEMETRY_FIELD_COUNT = 22;

const ROVER_MODES: RoverMode[] = ["MANUAL", "AUTO", "SAFE"];

export function isRoverMode(value: string): value is RoverMode {
  return ROVER_MODES.includes(value as RoverMode);
}

export function clampPercent(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(-100, Math.min(100, Math.round(value)));
}

export function parseTelemetryPacket(rawPacket: string): TelemetryParseResult {
  const raw = rawPacket.trim();
  const fields = raw.split(",");

  if (fields[TELEMETRY_FIELD.TAG] !== "ROVER") {
    return { ok: false, raw, error: "不是 ROVER 遥测包" };
  }

  if (fields.length < TELEMETRY_FIELD_COUNT) {
    return { ok: false, raw, error: `字段数量不足：收到 ${fields.length} 个，期望 ${TELEMETRY_FIELD_COUNT} 个` };
  }

  const mode = fields[TELEMETRY_FIELD.MODE]?.trim();
  if (!isRoverMode(mode)) {
    return { ok: false, raw, error: `未知运行模式：${mode || "空"}` };
  }

  try {
    const telemetry: RoverTelemetry = {
      raw,
      seq: parseFiniteNumber(fields[TELEMETRY_FIELD.SEQ], "seq"),
      ms: parseFiniteNumber(fields[TELEMETRY_FIELD.MS], "ms"),
      mode,
      estop: parseBooleanField(fields[TELEMETRY_FIELD.ESTOP]),
      leftPwm: parseFiniteNumber(fields[TELEMETRY_FIELD.LEFT_PWM], "left_pwm"),
      rightPwm: parseFiniteNumber(fields[TELEMETRY_FIELD.RIGHT_PWM], "right_pwm"),
      batteryV: parseFiniteNumber(fields[TELEMETRY_FIELD.BATTERY_V], "battery_v"),
      solarW: parseFiniteNumber(fields[TELEMETRY_FIELD.SOLAR_W], "solar_w"),
      lux: parseFiniteNumber(fields[TELEMETRY_FIELD.LUX], "lux"),
      pitch: parseFiniteNumber(fields[TELEMETRY_FIELD.PITCH], "pitch"),
      roll: parseFiniteNumber(fields[TELEMETRY_FIELD.ROLL], "roll"),
      obstacle: parseBooleanField(fields[TELEMETRY_FIELD.OBSTACLE]),
      pit: parseBooleanField(fields[TELEMETRY_FIELD.PIT]),
      fan: parseBooleanField(fields[TELEMETRY_FIELD.FAN]),
      tracker: parseBooleanField(fields[TELEMETRY_FIELD.TRACKER]),
      distF: parseFiniteNumber(fields[TELEMETRY_FIELD.DIST_F], "dist_f"),
      distD: parseFiniteNumber(fields[TELEMETRY_FIELD.DIST_D], "dist_d"),
      line: parseFiniteNumber(fields[TELEMETRY_FIELD.LINE], "line"),
      speedL: parseFiniteNumber(fields[TELEMETRY_FIELD.SPEED_L], "speed_l"),
      speedR: parseFiniteNumber(fields[TELEMETRY_FIELD.SPEED_R], "speed_r"),
      dust: parseBooleanField(fields[TELEMETRY_FIELD.DUST]),
      receivedAt: Date.now()
    };

    return { ok: true, telemetry };
  } catch (error) {
    return { ok: false, raw, error: error instanceof Error ? error.message : String(error) };
  }
}

export function formatModeCommand(seq: number, mode: RoverMode): CommandPacket {
  return buildCommand(seq, "MODE", [mode]);
}

export function formatDriveCommand(seq: number, forward: number, turn: number): CommandPacket {
  return buildCommand(seq, "DRIVE", [String(clampPercent(forward)), String(clampPercent(turn))]);
}

export function formatEstopCommand(seq: number): CommandPacket {
  return buildCommand(seq, "ESTOP", ["1"]);
}

export function formatClearEstopCommand(seq: number): CommandPacket {
  return buildCommand(seq, "CLEAR_ESTOP", ["1"]);
}

export function formatFanCommand(seq: number, enabled: boolean): CommandPacket {
  return buildCommand(seq, "FAN", [enabled ? "1" : "0"]);
}

export function formatTrackerCommand(seq: number, enabled: boolean): CommandPacket {
  return buildCommand(seq, "TRACKER", [enabled ? "1" : "0"]);
}

export function telemetryHistoryToCsv(history: RoverTelemetry[]): string {
  const header = [
    "received_at",
    "seq",
    "ms",
    "mode",
    "estop",
    "left_pwm",
    "right_pwm",
    "battery_v",
    "solar_w",
    "lux",
    "pitch",
    "roll",
    "obstacle",
    "pit",
    "fan",
    "tracker",
    "dist_f_mm",
    "dist_d_mm",
    "line_bits",
    "speed_l_rpm",
    "speed_r_rpm",
    "dust"
  ];

  const rows = history.map((item) =>
    [
      new Date(item.receivedAt).toISOString(),
      item.seq,
      item.ms,
      item.mode,
      numberBoolean(item.estop),
      item.leftPwm,
      item.rightPwm,
      item.batteryV.toFixed(2),
      item.solarW.toFixed(2),
      item.lux.toFixed(0),
      item.pitch.toFixed(1),
      item.roll.toFixed(1),
      numberBoolean(item.obstacle),
      numberBoolean(item.pit),
      numberBoolean(item.fan),
      numberBoolean(item.tracker),
      item.distF,
      item.distD,
      item.line,
      item.speedL,
      item.speedR,
      numberBoolean(item.dust)
    ].join(",")
  );

  return `${header.join(",")}\n${rows.join("\n")}\n`;
}

function buildCommand(seq: number, kind: CommandKind, payload: string[]): CommandPacket {
  const safeSeq = Number.isFinite(seq) ? Math.max(1, Math.round(seq)) : 1;
  const text = ["CMD", String(safeSeq), kind, ...payload].join(",");

  return {
    seq: safeSeq,
    kind,
    payload,
    text
  };
}

function parseFiniteNumber(value: string | undefined, label: string): number {
  const parsed = Number(value);

  if (!Number.isFinite(parsed)) {
    throw new Error(`字段 ${label} 不是有效数字：${value ?? "空"}`);
  }

  return parsed;
}

function parseBooleanField(value: string | undefined): boolean {
  const normalized = String(value ?? "").trim().toLowerCase();
  return normalized === "1" || normalized === "true" || normalized === "yes" || normalized === "on";
}

function numberBoolean(value: boolean): 0 | 1 {
  return value ? 1 : 0;
}
