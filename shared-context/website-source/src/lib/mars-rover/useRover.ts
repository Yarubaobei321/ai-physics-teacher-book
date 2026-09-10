import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ROVER_COMMAND_UUID,
  ROVER_DEVICE_NAME_PREFIX,
  ROVER_SERVICE_UUID,
  ROVER_TELEMETRY_UUID,
  clampPercent,
  formatClearEstopCommand,
  formatDriveCommand,
  formatEstopCommand,
  formatFanCommand,
  formatModeCommand,
  formatTrackerCommand,
  parseTelemetryPacket,
  telemetryHistoryToCsv,
  type CommandPacket,
  type RoverMode,
  type RoverTelemetry
} from "./roverProtocol";
import { appendTelemetry, createDemoTelemetry, createInitialTelemetry } from "./demoTelemetry";

export type ViewKey = "dashboard" | "control" | "modules";
export type ConnectionState = "idle" | "connecting" | "connected" | "demo" | "unsupported" | "error";
export type LogLevel = "info" | "warn" | "error" | "tx" | "rx";

export interface LogEntry {
  id: number;
  level: LogLevel;
  message: string;
  detail?: string;
  time: number;
}

const decoder = new TextDecoder();
const encoder = new TextEncoder();

export function clampRange(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/**
 * useRover —— 地面站的全部状态机与副作用都集中在这里：
 * BLE 连接、遥测接收、命令收发、演示数据。组件只消费返回值做渲染。
 *
 * 设计要点：
 * - telemetry/history/logs 是「车辆真值」一侧；
 * - controlMode/forward/turn/fanEnabled/trackerEnabled 是「用户意图」一侧，
 *   不会被遥测回写覆盖（见 updateTelemetry 注释），避免按钮被下一包遥测弹回。
 */
export function useRover() {
  const [activeView, setActiveView] = useState<ViewKey>("dashboard");
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");
  const [deviceName, setDeviceName] = useState("未连接");
  const [telemetry, setTelemetry] = useState<RoverTelemetry>(() => createInitialTelemetry());
  const [history, setHistory] = useState<RoverTelemetry[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [controlMode, setControlMode] = useState<RoverMode>("SAFE");
  const [forward, setForward] = useState(0);
  const [turn, setTurn] = useState(0);
  const [fanEnabled, setFanEnabled] = useState(false);
  const [trackerEnabled, setTrackerEnabled] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [bluetoothSupported, setBluetoothSupported] = useState(true);

  const commandCharacteristicRef = useRef<BluetoothRemoteGATTCharacteristic | null>(null);
  const deviceRef = useRef<BluetoothDevice | null>(null);
  const commandSeqRef = useRef(1);
  const logSeqRef = useRef(1);
  const demoSeqRef = useRef(1);
  const telemetryRef = useRef(telemetry);
  const lastRxLogRef = useRef(0);

  useEffect(() => {
    telemetryRef.current = telemetry;
  }, [telemetry]);

  useEffect(() => {
    const supported = typeof navigator !== "undefined" && "bluetooth" in navigator;
    setBluetoothSupported(supported);
    if (!supported) {
      setConnectionState("unsupported");
    }
  }, []);

  const isConnected = connectionState === "connected";
  const canInteract = isConnected || demoMode;
  const canDrive = canInteract && controlMode === "MANUAL" && !telemetry.estop;
  const batteryPercent = clampRange(((telemetry.batteryV - 6.6) / (8.4 - 6.6)) * 100, 0, 100);
  const riskCount = [
    telemetry.estop,
    telemetry.obstacle,
    telemetry.pit,
    telemetry.batteryV > 0 && telemetry.batteryV < 6.9,
    Math.abs(telemetry.pitch) > 25 || Math.abs(telemetry.roll) > 25
  ].filter(Boolean).length;

  const addLog = useCallback((level: LogLevel, message: string, detail?: string) => {
    const next: LogEntry = {
      id: logSeqRef.current++,
      level,
      message,
      detail,
      time: Date.now()
    };
    setLogs((current) => [next, ...current].slice(0, 80));
  }, []);

  const updateTelemetry = useCallback((next: RoverTelemetry, source: "rx" | "demo" = "rx") => {
    // telemetry 是车辆真值（Dashboard 直接读它显示）；controlMode/fanEnabled/trackerEnabled
    // 只代表用户在控制面板上的“意图”，不在这里被遥测覆盖，否则用户刚点的按钮会被下一包遥测弹回。
    setTelemetry(next);
    setHistory((current) => appendTelemetry(current, next));
    if (source === "rx") {
      // 遥测高频推送，逐包记日志会刷屏；节流到每 2 秒一条，保留“数据在流”的心跳即可。
      const now = Date.now();
      if (now - lastRxLogRef.current >= 2000) {
        lastRxLogRef.current = now;
        addLog("rx", "收到遥测", next.raw);
      }
    }
  }, [addLog]);

  const applyLocalCommand = useCallback((packet: CommandPacket) => {
    setTelemetry((current) => {
      if (packet.kind === "MODE") {
        const mode = packet.payload[0] as RoverMode;
        setControlMode(mode);
        return { ...current, mode, receivedAt: Date.now() };
      }

      if (packet.kind === "ESTOP") {
        return { ...current, mode: "SAFE", estop: true, leftPwm: 0, rightPwm: 0, receivedAt: Date.now() };
      }

      if (packet.kind === "CLEAR_ESTOP") {
        return { ...current, estop: false, receivedAt: Date.now() };
      }

      if (packet.kind === "FAN") {
        const fan = packet.payload[0] === "1";
        setFanEnabled(fan);
        return { ...current, fan, receivedAt: Date.now() };
      }

      if (packet.kind === "DRIVE") {
        const nextForward = Number(packet.payload[0] ?? 0);
        const nextTurn = Number(packet.payload[1] ?? 0);
        return {
          ...current,
          leftPwm: clampPercent(nextForward - nextTurn * 0.7),
          rightPwm: clampPercent(nextForward + nextTurn * 0.7),
          receivedAt: Date.now()
        };
      }

      return current;
    });

    if (packet.kind === "TRACKER") {
      setTrackerEnabled(packet.payload[0] === "1");
    }
  }, []);

  const nextCommandSeq = useCallback(() => commandSeqRef.current++, []);

  const sendPacket = useCallback(async (packet: CommandPacket, options: { quiet?: boolean } = {}) => {
    if (demoMode) {
      applyLocalCommand(packet);
      if (!options.quiet) {
        addLog("tx", "演示命令", packet.text);
      }
      return;
    }

    const characteristic = commandCharacteristicRef.current;
    if (!characteristic || !isConnected) {
      if (!options.quiet) {
        addLog("warn", "命令未发送", "请先连接 ESP32-rover，或打开演示数据模式。");
      }
      return;
    }

    try {
      await characteristic.writeValue(encoder.encode(packet.text));
      if (!options.quiet) {
        addLog("tx", "命令已发送", packet.text);
      }
    } catch (error) {
      addLog("error", "命令发送失败", error instanceof Error ? error.message : String(error));
    }
  }, [addLog, applyLocalCommand, demoMode, isConnected]);

  const sendDriveNow = useCallback(async (quiet = false) => {
    await sendPacket(formatDriveCommand(nextCommandSeq(), forward, turn), { quiet });
  }, [forward, nextCommandSeq, sendPacket, turn]);

  useEffect(() => {
    if (!canDrive) {
      return;
    }

    // DRIVE 心跳：每 320ms 重发一次当前摇杆值。这是 keep-alive，不是状态变更——
    // A 板靠这个刷新做失联停车，超过固件超时（kManualCommandTimeoutMs）即自动停车，请勿删。
    const timer = window.setInterval(() => {
      void sendDriveNow(true);
    }, 320);

    return () => window.clearInterval(timer);
  }, [canDrive, sendDriveNow]);

  useEffect(() => {
    if (!demoMode) {
      return;
    }

    const timer = window.setInterval(() => {
      const next = createDemoTelemetry(demoSeqRef.current++, {
        mode: controlMode,
        estop: telemetryRef.current.estop,
        fan: fanEnabled,
        tracker: trackerEnabled,
        forward,
        turn
      });
      updateTelemetry(next, "demo");
    }, 500);

    return () => window.clearInterval(timer);
  }, [controlMode, demoMode, fanEnabled, forward, trackerEnabled, turn, updateTelemetry]);

  const connect = useCallback(async (strategy: "name" | "all") => {
    if (!bluetoothSupported) {
      setConnectionState("unsupported");
      addLog("warn", "当前浏览器不支持 Web Bluetooth", "请使用桌面版 Chrome 或 Edge，并通过 localhost 或 HTTPS 访问。");
      return;
    }

    setConnectionState("connecting");
    setDemoMode(false);
    addLog("info", strategy === "name" ? "按设备名前缀连接" : "搜索所有蓝牙设备", ROVER_DEVICE_NAME_PREFIX);

    try {
      const device = await navigator.bluetooth.requestDevice(
        strategy === "name"
          ? {
              filters: [{ namePrefix: ROVER_DEVICE_NAME_PREFIX }],
              optionalServices: [ROVER_SERVICE_UUID]
            }
          : {
              acceptAllDevices: true,
              optionalServices: [ROVER_SERVICE_UUID]
            }
      );

      deviceRef.current = device;
      setDeviceName(device.name || "ESP32 Rover");

      device.addEventListener("gattserverdisconnected", () => {
        commandCharacteristicRef.current = null;
        setConnectionState("idle");
        setDeviceName("已断开");
        setForward(0);
        setTurn(0);
        addLog("warn", "蓝牙连接已断开", "A 板会因 DRIVE 刷新停止而停车。");
      });

      if (!device.gatt) {
        throw new Error("设备未暴露 GATT 服务");
      }

      const server = await device.gatt.connect();
      const service = await server.getPrimaryService(ROVER_SERVICE_UUID);
      const telemetryCharacteristic = await service.getCharacteristic(ROVER_TELEMETRY_UUID);
      const commandCharacteristic = await service.getCharacteristic(ROVER_COMMAND_UUID);

      commandCharacteristicRef.current = commandCharacteristic;

      telemetryCharacteristic.addEventListener("characteristicvaluechanged", () => {
        const value = telemetryCharacteristic.value;
        if (!value) {
          addLog("warn", "收到空遥测包");
          return;
        }

        const text = decoder.decode(new Uint8Array(value.buffer, value.byteOffset, value.byteLength));
        const result = parseTelemetryPacket(text);
        if (result.ok) {
          updateTelemetry(result.telemetry);
        } else {
          addLog("warn", "遥测解析失败", result.error);
        }
      });

      await telemetryCharacteristic.startNotifications();
      setConnectionState("connected");
      addLog("info", "BLE 已连接", `${device.name || "ESP32 Rover"} · ${ROVER_SERVICE_UUID}`);
    } catch (error) {
      setConnectionState("error");
      commandCharacteristicRef.current = null;
      addLog("error", "BLE 连接失败", error instanceof Error ? error.message : String(error));
    }
  }, [addLog, bluetoothSupported, updateTelemetry]);

  const disconnect = useCallback(() => {
    const device = deviceRef.current;
    if (device?.gatt?.connected) {
      device.gatt.disconnect();
    }
    commandCharacteristicRef.current = null;
    setConnectionState("idle");
    setDeviceName("未连接");
    setForward(0);
    setTurn(0);
    addLog("info", "已断开连接");
  }, [addLog]);

  const startDemo = useCallback(() => {
    setDemoMode(true);
    setConnectionState("demo");
    setDeviceName("演示数据模式");
    const next = createDemoTelemetry(demoSeqRef.current++, { mode: controlMode, fan: fanEnabled, tracker: trackerEnabled });
    updateTelemetry(next, "demo");
    addLog("info", "演示数据已启动", "演示模式不会向真实 ESP32 写入命令。");
  }, [addLog, controlMode, fanEnabled, trackerEnabled, updateTelemetry]);

  const stopDemo = useCallback(() => {
    setDemoMode(false);
    setConnectionState("idle");
    setDeviceName("未连接");
    setForward(0);
    setTurn(0);
    addLog("info", "演示数据已停止");
  }, [addLog]);

  const setMode = useCallback(async (mode: RoverMode) => {
    setControlMode(mode);
    await sendPacket(formatModeCommand(nextCommandSeq(), mode));
  }, [nextCommandSeq, sendPacket]);

  const triggerEstop = useCallback(async () => {
    setForward(0);
    setTurn(0);
    await sendPacket(formatEstopCommand(nextCommandSeq()));
  }, [nextCommandSeq, sendPacket]);

  const clearEstop = useCallback(async () => {
    await sendPacket(formatClearEstopCommand(nextCommandSeq()));
  }, [nextCommandSeq, sendPacket]);

  const toggleFan = useCallback(async () => {
    const next = !fanEnabled;
    setFanEnabled(next);
    await sendPacket(formatFanCommand(nextCommandSeq(), next));
  }, [fanEnabled, nextCommandSeq, sendPacket]);

  const toggleTracker = useCallback(async () => {
    const next = !trackerEnabled;
    setTrackerEnabled(next);
    await sendPacket(formatTrackerCommand(nextCommandSeq(), next));
  }, [nextCommandSeq, sendPacket, trackerEnabled]);

  const stopDrive = useCallback(async () => {
    setForward(0);
    setTurn(0);
    await sendPacket(formatDriveCommand(nextCommandSeq(), 0, 0));
  }, [nextCommandSeq, sendPacket]);

  const exportCsv = useCallback(() => {
    const rows = history.length > 0 ? history : [telemetry];
    const blob = new Blob([telemetryHistoryToCsv(rows)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `chenguang-rover-telemetry-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.csv`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    addLog("info", "CSV 已导出", `${rows.length} 条遥测记录`);
  }, [addLog, history, telemetry]);

  const statusText = useMemo(() => {
    if (connectionState === "connected") {
      return "BLE 已连接";
    }
    if (connectionState === "demo") {
      return "演示数据";
    }
    if (connectionState === "connecting") {
      return "连接中";
    }
    if (connectionState === "unsupported") {
      return "浏览器不支持";
    }
    if (connectionState === "error") {
      return "连接失败";
    }
    return "待连接";
  }, [connectionState]);

  return {
    // 视图与连接状态
    activeView,
    setActiveView,
    connectionState,
    deviceName,
    bluetoothSupported,
    isConnected,
    demoMode,
    statusText,
    // 车辆真值
    telemetry,
    history,
    logs,
    batteryPercent,
    riskCount,
    // 用户意图
    controlMode,
    forward,
    turn,
    fanEnabled,
    trackerEnabled,
    canInteract,
    canDrive,
    setForward,
    setTurn,
    // 动作
    connect,
    disconnect,
    startDemo,
    stopDemo,
    setMode,
    triggerEstop,
    clearEstop,
    toggleFan,
    toggleTracker,
    stopDrive,
    sendDriveNow,
    exportCsv
  };
}
