import { memo, useCallback, useRef, useState, type PointerEvent } from "react";
import type { RoverMode, RoverTelemetry } from "../../lib/mars-rover/roverProtocol";
import { clampRange, type LogEntry } from "../../lib/mars-rover/useRover";
import { formatTime } from "./widgets";

export const ControlView = memo(function ControlView({
  canInteract,
  canDrive,
  clearEstop,
  controlMode,
  fanEnabled,
  forward,
  logs,
  sendDriveNow,
  setForward,
  setMode,
  setTurn,
  stopDrive,
  telemetry,
  toggleFan,
  toggleTracker,
  trackerEnabled,
  triggerEstop,
  turn
}: {
  canInteract: boolean;
  canDrive: boolean;
  clearEstop: () => Promise<void>;
  controlMode: RoverMode;
  fanEnabled: boolean;
  forward: number;
  logs: LogEntry[];
  sendDriveNow: (quiet?: boolean) => Promise<void>;
  setForward: (value: number) => void;
  setMode: (mode: RoverMode) => Promise<void>;
  setTurn: (value: number) => void;
  stopDrive: () => Promise<void>;
  telemetry: RoverTelemetry;
  toggleFan: () => Promise<void>;
  toggleTracker: () => Promise<void>;
  trackerEnabled: boolean;
  triggerEstop: () => Promise<void>;
  turn: number;
}) {
  const modeMismatch = controlMode !== telemetry.mode;

  return (
    <main className="control-grid">
      <section className="panel drive-panel">
        <h2 className="panel-title">操控台</h2>

        <div className="mode-row" role="group" aria-label="运行模式">
          {(["SAFE", "MANUAL", "AUTO"] as RoverMode[]).map((mode) => (
            <button
              className={`mode-btn ${controlMode === mode ? "selected" : ""} ${telemetry.mode === mode ? "actual" : ""}`}
              disabled={!canInteract}
              key={mode}
              type="button"
              onClick={() => void setMode(mode)}
            >
              {mode}
              {telemetry.mode === mode && <i className="actual-dot" title="A 板实际模式" />}
            </button>
          ))}
        </div>
        <p className={`mode-truth ${modeMismatch ? "mismatch" : ""}`}>
          A 板实际模式：<strong>{telemetry.mode}</strong>
          {modeMismatch && " ←(与按钮意图不一致：急停/低电量时 A 板会拒绝切换并退回 SAFE)"}
        </p>

        <div className="drive-cluster">
          <Joystick
            disabled={!canDrive}
            forward={forward}
            turn={turn}
            setForward={setForward}
            setTurn={setTurn}
            onRelease={() => void stopDrive()}
          />
          <div className="range-stack">
            <label>
              <span>前进 / 后退</span>
              <output>{forward}</output>
              <input
                aria-label="前进后退"
                disabled={!canDrive}
                max={100}
                min={-100}
                onChange={(event) => setForward(Number(event.currentTarget.value))}
                type="range"
                value={forward}
              />
            </label>
            <label>
              <span>左转 / 右转</span>
              <output>{turn}</output>
              <input
                aria-label="左转右转"
                disabled={!canDrive}
                max={100}
                min={-100}
                onChange={(event) => setTurn(Number(event.currentTarget.value))}
                type="range"
                value={turn}
              />
            </label>
            <div className="drive-actions">
              <button className="button secondary" disabled={!canDrive} type="button" onClick={() => void sendDriveNow(false)}>
                发送指令
              </button>
              <button className="button secondary" disabled={!canInteract} type="button" onClick={() => void stopDrive()}>
                停车
              </button>
            </div>
          </div>
        </div>

        <div className="estop-row">
          <button className="estop-button" disabled={!canInteract} type="button" onClick={() => void triggerEstop()}>
            <span>EMERGENCY</span>
            急停
          </button>
          <button className="button ghost clear-estop" disabled={!canInteract || !telemetry.estop} type="button" onClick={() => void clearEstop()}>
            解除急停
            <small>解除后仍处于 SAFE，需重新选 MANUAL/AUTO</small>
          </button>
        </div>

        <div className="quick-toggles">
          <button className={fanEnabled ? "toggle active" : "toggle"} disabled={!canInteract} type="button" onClick={() => void toggleFan()}>
            <FanIcon spinning={fanEnabled} />
            风扇除尘 <strong>{fanEnabled ? "ON" : "OFF"}</strong>
          </button>
          <button className={trackerEnabled ? "toggle active" : "toggle"} disabled={!canInteract} type="button" onClick={() => void toggleTracker()}>
            <SunIcon active={trackerEnabled} />
            太阳能追光 <strong>{trackerEnabled ? "ON" : "OFF"}</strong>
          </button>
        </div>

        <div className="safety-note">
          网页只发送「控制意图」。急停、低电量、倾角、障碍、坑洞和失联停车全部由 A 板固件最终裁决，
          网页或蓝牙异常时车辆自动停车。
        </div>
      </section>

      <section className="panel log-panel">
        <h2 className="panel-title">链路日志 <small>TX/RX 终端</small></h2>
        <div className="log-list" role="log" aria-live="polite">
          {logs.length === 0 && <p className="empty-log">&gt; 等待链路活动… 连接 BLE 或开启演示模式后这里会滚动显示命令与遥测。</p>}
          {logs.map((entry) => (
            <article className={`log-entry level-${entry.level}`} key={entry.id}>
              <time>{formatTime(entry.time)}</time>
              <strong>{entry.message}</strong>
              {entry.detail && <code>{entry.detail}</code>}
            </article>
          ))}
        </div>
      </section>
    </main>
  );
});

/** 虚拟摇杆：拖动设置 forward/turn，松手回中并停车 */
const Joystick = memo(function Joystick({
  disabled,
  forward,
  turn,
  setForward,
  setTurn,
  onRelease
}: {
  disabled: boolean;
  forward: number;
  turn: number;
  setForward: (value: number) => void;
  setTurn: (value: number) => void;
  onRelease: () => void;
}) {
  const padRef = useRef<HTMLDivElement | null>(null);
  const [dragging, setDragging] = useState(false);

  const applyPointer = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      const pad = padRef.current;
      if (!pad) return;
      const rect = pad.getBoundingClientRect();
      const radius = rect.width / 2;
      const dx = event.clientX - (rect.left + radius);
      const dy = event.clientY - (rect.top + radius);
      setTurn(Math.round(clampRange((dx / radius) * 100, -100, 100)));
      setForward(Math.round(clampRange((-dy / radius) * 100, -100, 100)));
    },
    [setForward, setTurn]
  );

  const handleDown = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      if (disabled) return;
      event.currentTarget.setPointerCapture(event.pointerId);
      setDragging(true);
      applyPointer(event);
    },
    [applyPointer, disabled]
  );

  const handleMove = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      if (!dragging || disabled) return;
      applyPointer(event);
    },
    [applyPointer, disabled, dragging]
  );

  const handleUp = useCallback(() => {
    if (!dragging) return;
    setDragging(false);
    setForward(0);
    setTurn(0);
    onRelease();
  }, [dragging, onRelease, setForward, setTurn]);

  const knobX = (turn / 100) * 42;
  const knobY = (-forward / 100) * 42;

  return (
    <div
      className={`joystick ${disabled ? "disabled" : ""} ${dragging ? "dragging" : ""}`}
      ref={padRef}
      onPointerDown={handleDown}
      onPointerMove={handleMove}
      onPointerUp={handleUp}
      onPointerCancel={handleUp}
      role="application"
      aria-label="虚拟摇杆，拖动控制前进与转向"
    >
      <div className="joystick-cross" />
      <div className="joystick-ring" />
      <div className="joystick-knob" style={{ transform: `translate(${knobX}px, ${knobY}px)` }} />
      <span className="joystick-hint">{disabled ? "需 MANUAL 且无急停" : "拖动驾驶"}</span>
    </div>
  );
});

const FanIcon = memo(function FanIcon({ spinning }: { spinning: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className={`icon-fan ${spinning ? "spinning" : ""}`} aria-hidden="true">
      <g>
        <path d="M12 11 C14 7 13 4 12 3 C8 4 7 8 9 11 Z" />
        <path d="M13 12 C17 14 20 13 21 12 C20 8 16 7 13 9 Z" />
        <path d="M12 13 C10 17 11 20 12 21 C16 20 17 16 15 13 Z" />
        <path d="M11 12 C7 10 4 11 3 12 C4 16 8 17 11 15 Z" />
      </g>
      <circle cx="12" cy="12" r="1.8" />
    </svg>
  );
});

const SunIcon = memo(function SunIcon({ active }: { active: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className={`icon-sun ${active ? "glowing" : ""}`} aria-hidden="true">
      <circle cx="12" cy="12" r="4.5" />
      {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
        <line key={deg} x1="12" y1="2.5" x2="12" y2="5.5" transform={`rotate(${deg} 12 12)`} />
      ))}
    </svg>
  );
});
