import { memo, useEffect, useMemo, useState } from "react";

type ConsoleView = "dashboard" | "control" | "principle";
type CarMode = "PARKED" | "AVOID" | "LINE" | "MANUAL";

type SensorKey =
  | "obstacleLeft"
  | "obstacleCenter"
  | "obstacleRight"
  | "lineLeft"
  | "lineCenter"
  | "lineRight"
  | "remoteAlive"
  | "estop";

interface SensorState {
  obstacleLeft: boolean;
  obstacleCenter: boolean;
  obstacleRight: boolean;
  lineLeft: boolean;
  lineCenter: boolean;
  lineRight: boolean;
  remoteAlive: boolean;
  estop: boolean;
}

interface DerivedState {
  action: string;
  detail: string;
  leftPwm: number;
  rightPwm: number;
  ledPulses: number;
  serialLine: string;
  safety: "ok" | "warn" | "stop";
}

const modeMeta: Record<CarMode, { label: string; short: string; desc: string }> = {
  PARKED: {
    label: "停车 / 待机",
    short: "STOP",
    desc: "所有电机输出 0，LED 不闪，适合接线和传感器检查。"
  },
  AVOID: {
    label: "三红外避障",
    short: "AVOID",
    desc: "读取车头左、中、右三个红外避障模块，遇到障碍时先避开再恢复前进。"
  },
  LINE: {
    label: "三路循迹",
    short: "LINE",
    desc: "读取车头下方左、中、右三个 TCRT5000 模块，让中间探头重新压回黑线。"
  },
  MANUAL: {
    label: "2.4G 手动",
    short: "REMOTE",
    desc: "只在手动模式响应遥控器帧，超过 400ms 没有有效帧就停车。"
  }
};

const tabs: Array<{ key: ConsoleView; title: string; sub: string }> = [
  { key: "dashboard", title: "状态驾驶舱", sub: "STATUS" },
  { key: "control", title: "教学操控台", sub: "CONTROL" },
  { key: "principle", title: "原理透视", sub: "PRINCIPLE" }
];

const sensorLabels: Array<{ key: SensorKey; label: string; hint: string }> = [
  { key: "obstacleLeft", label: "左红外有障碍", hint: "GPIO36 = LOW" },
  { key: "obstacleCenter", label: "中红外有障碍", hint: "GPIO39 = LOW" },
  { key: "obstacleRight", label: "右红外有障碍", hint: "GPIO34 = LOW" },
  { key: "lineLeft", label: "左循迹压黑线", hint: "GPIO35 = HIGH" },
  { key: "lineCenter", label: "中循迹压黑线", hint: "GPIO32 = HIGH" },
  { key: "lineRight", label: "右循迹压黑线", hint: "GPIO33 = HIGH" },
  { key: "remoteAlive", label: "遥控帧在线", hint: "400ms 内有效帧" },
  { key: "estop", label: "急停锁定", hint: "强制 PWM = 0" }
];

const pinRows = [
  ["DRV8833 左轮", "GPIO25 / GPIO26", "AIN1 / AIN2 输出 PWM"],
  ["DRV8833 右轮", "GPIO27 / GPIO14", "BIN1 / BIN2 输出 PWM"],
  ["红外避障", "GPIO36 / 39 / 34", "LOW 表示有障碍"],
  ["TCRT5000 循迹", "GPIO35 / 32 / 33", "HIGH 表示压到黑线"],
  ["模式按键", "GPIO21 / 22 / 23", "按下接 GND，INPUT_PULLUP"],
  ["2.4G 接收", "GPIO16 RX2", "9600 baud，6 字节校验帧"]
];

const clampPwm = (value: number) => Math.max(-255, Math.min(255, Math.round(value)));

function deriveState(mode: CarMode, sensors: SensorState, manualForward: number, manualTurn: number): DerivedState {
  const ledPulses = mode === "AVOID" ? 1 : mode === "LINE" ? 2 : mode === "MANUAL" ? 3 : 0;

  if (sensors.estop) {
    return {
      action: "急停锁定",
      detail: "任何模式下急停优先，左右轮 PWM 立即归零。",
      leftPwm: 0,
      rightPwm: 0,
      ledPulses,
      serialLine: "[安全] ESTOP=1 -> stopMotors()",
      safety: "stop"
    };
  }

  if (mode === "PARKED") {
    return {
      action: "停车待机",
      detail: "当前没有运行任务，适合调阈值、查共地和确认串口输出。",
      leftPwm: 0,
      rightPwm: 0,
      ledPulses,
      serialLine: "[状态] 模式=停车/待机 LED=0闪 | 动作=停车",
      safety: "ok"
    };
  }

  if (mode === "AVOID") {
    const { obstacleLeft: left, obstacleCenter: center, obstacleRight: right } = sensors;

    if (left && center && right) {
      return avoidResult("三向受阻", "先后退，再按上一次安全方向原地转向。", -115, -115, ledPulses, "warn");
    }
    if (center && left) {
      return avoidResult("左前受阻", "左侧和正前方都有障碍，右轮慢、左轮快，向右绕开。", 135, 55, ledPulses, "warn");
    }
    if (center && right) {
      return avoidResult("右前受阻", "右侧和正前方都有障碍，左轮慢、右轮快，向左绕开。", 55, 135, ledPulses, "warn");
    }
    if (center) {
      return avoidResult("正前方受阻", "正前方挡住时不硬顶，先短暂后退。", -115, -115, ledPulses, "warn");
    }
    if (left) {
      return avoidResult("左侧有障碍", "向右小幅修正，避开左侧物体。", 140, 70, ledPulses, "warn");
    }
    if (right) {
      return avoidResult("右侧有障碍", "向左小幅修正，避开右侧物体。", 70, 140, ledPulses, "warn");
    }
    return avoidResult("低速前进", "三个红外都没有触发，小车保持低速巡航。", 120, 120, ledPulses, "ok");
  }

  if (mode === "LINE") {
    const { lineLeft: left, lineCenter: center, lineRight: right } = sensors;

    if (left && center && right) {
      return lineResult("宽线 / 交叉口", "三个探头都在黑线上，降低速度通过交叉区域。", 115, 115, ledPulses, "ok");
    }
    if (left && center) {
      return lineResult("小幅左转", "黑线偏左，左轮慢、右轮快，让中间探头回到线上。", 110, 180, ledPulses, "ok");
    }
    if (right && center) {
      return lineResult("小幅右转", "黑线偏右，左轮快、右轮慢，让中间探头回到线上。", 180, 110, ledPulses, "ok");
    }
    if (center) {
      return lineResult("沿线直行", "中间探头压线，左右轮同速前进。", 145, 145, ledPulses, "ok");
    }
    if (left) {
      return lineResult("大幅左转", "只有左探头看到黑线，说明偏差较大，需要明显向左修正。", 55, 165, ledPulses, "warn");
    }
    if (right) {
      return lineResult("大幅右转", "只有右探头看到黑线，说明偏差较大，需要明显向右修正。", 165, 55, ledPulses, "warn");
    }
    return lineResult("丢线停车", "三个循迹探头都没有压线，超过搜索时间后停车，避免盲跑。", 0, 0, ledPulses, "stop");
  }

  if (!sensors.remoteAlive) {
    return {
      action: "遥控失联停车",
      detail: "手动模式超过 400ms 没有有效帧，程序会自动停车。",
      leftPwm: 0,
      rightPwm: 0,
      ledPulses,
      serialLine: "[手动] 遥控失联 -> 停车",
      safety: "stop"
    };
  }

  const leftPwm = clampPwm(manualForward - manualTurn * 0.7);
  const rightPwm = clampPwm(manualForward + manualTurn * 0.7);
  return {
    action: "手动驾驶",
    detail: "网页滑杆只模拟遥控器意图：前后方向决定油门，左右方向决定差速转向。",
    leftPwm,
    rightPwm,
    ledPulses,
    serialLine: `[手动] 链路=在线 油门=${manualForward} 转向=${manualTurn} | 当前速度 L=${leftPwm} R=${rightPwm}`,
    safety: "ok"
  };
}

function avoidResult(
  action: string,
  detail: string,
  leftPwm: number,
  rightPwm: number,
  ledPulses: number,
  safety: DerivedState["safety"]
): DerivedState {
  return {
    action,
    detail,
    leftPwm,
    rightPwm,
    ledPulses,
    serialLine: `[避障] 动作=${action} | 当前速度 L=${leftPwm} R=${rightPwm}`,
    safety
  };
}

function lineResult(
  action: string,
  detail: string,
  leftPwm: number,
  rightPwm: number,
  ledPulses: number,
  safety: DerivedState["safety"]
): DerivedState {
  return {
    action,
    detail,
    leftPwm,
    rightPwm,
    ledPulses,
    serialLine: `[循迹] 动作=${action} | 当前速度 L=${leftPwm} R=${rightPwm}`,
    safety
  };
}

const DEMO_BASE: SensorState = {
  obstacleLeft: false,
  obstacleCenter: false,
  obstacleRight: false,
  lineLeft: false,
  lineCenter: true,
  lineRight: false,
  remoteAlive: true,
  estop: false
};

type DemoStep = {
  note: string;
  mode: CarMode;
  sensors: Partial<SensorState>;
  forward?: number;
  turn?: number;
};

const demoSteps: DemoStep[] = [
  { note: "循迹：中间探头压线，左右轮同速沿黑线直行。", mode: "LINE", sensors: { lineCenter: true } },
  { note: "循迹：黑线偏左，左轮放慢、右轮加快，小幅左转修正。", mode: "LINE", sensors: { lineLeft: true, lineCenter: true } },
  { note: "循迹：只有左探头压线，偏差较大，明显向左找回。", mode: "LINE", sensors: { lineLeft: true, lineCenter: false } },
  { note: "循迹：黑线偏右，左轮加快、右轮放慢，小幅右转修正。", mode: "LINE", sensors: { lineRight: true, lineCenter: true } },
  { note: "循迹：三个探头都没压线，超时后停车，避免盲跑。", mode: "LINE", sensors: { lineCenter: false } },
  { note: "切到避障：三个红外都没触发，小车低速巡航前进。", mode: "AVOID", sensors: { lineCenter: false } },
  { note: "避障：左侧有障碍，向右小幅修正避开。", mode: "AVOID", sensors: { lineCenter: false, obstacleLeft: true } },
  { note: "避障：正前方受阻，不硬顶，先短暂后退。", mode: "AVOID", sensors: { lineCenter: false, obstacleCenter: true } },
  { note: "避障：三向受阻，先后退再原地转向脱困。", mode: "AVOID", sensors: { lineCenter: false, obstacleLeft: true, obstacleCenter: true, obstacleRight: true } },
  { note: "切到手动：遥控帧在线，前进 + 右转，按差速驱动左右轮。", mode: "MANUAL", sensors: { lineCenter: false, remoteAlive: true }, forward: 160, turn: 70 },
  { note: "手动：超过 400ms 没有有效遥控帧，自动失联停车。", mode: "MANUAL", sensors: { lineCenter: false, remoteAlive: false } },
  { note: "急停演示：任何模式下急停优先，左右轮 PWM 立即归零。", mode: "AVOID", sensors: { lineCenter: false, estop: true } }
];

export default function SmartCarConsole() {
  const [activeView, setActiveView] = useState<ConsoleView>("dashboard");
  const [mode, setMode] = useState<CarMode>("LINE");
  const [manualForward, setManualForward] = useState(120);
  const [manualTurn, setManualTurn] = useState(0);
  const [sensors, setSensors] = useState<SensorState>({
    obstacleLeft: false,
    obstacleCenter: false,
    obstacleRight: false,
    lineLeft: false,
    lineCenter: true,
    lineRight: false,
    remoteAlive: true,
    estop: false
  });

  const [demoMode, setDemoMode] = useState(false);
  const [demoNote, setDemoNote] = useState("");

  const derived = useMemo(
    () => deriveState(mode, sensors, manualForward, manualTurn),
    [manualForward, manualTurn, mode, sensors]
  );

  useEffect(() => {
    if (!demoMode) return;
    let index = 0;
    const apply = (idx: number) => {
      const step = demoSteps[idx];
      setMode(step.mode);
      setSensors({ ...DEMO_BASE, ...step.sensors });
      if (step.forward !== undefined) setManualForward(step.forward);
      if (step.turn !== undefined) setManualTurn(step.turn);
      setDemoNote(step.note);
    };
    apply(0);
    const timer = window.setInterval(() => {
      index = (index + 1) % demoSteps.length;
      apply(index);
    }, 2800);
    return () => window.clearInterval(timer);
  }, [demoMode]);

  const toggleSensor = (key: SensorKey) => {
    setSensors((current) => ({ ...current, [key]: !current[key] }));
  };

  // 演示进行中，任何手动操作都会暂停演示，把控制权交还给用户。
  const stopDemoThen = <T extends unknown[]>(fn: (...args: T) => void) => (...args: T) => {
    setDemoMode(false);
    fn(...args);
  };
  const userSetMode = stopDemoThen(setMode);
  const userToggleSensor = stopDemoThen(toggleSensor);
  const userSetManualForward = stopDemoThen(setManualForward);
  const userSetManualTurn = stopDemoThen(setManualTurn);

  const loadPreset = (preset: "straight" | "left" | "right" | "obstacle" | "lost" | "remoteLost") => {
    const next: SensorState = {
      obstacleLeft: false,
      obstacleCenter: false,
      obstacleRight: false,
      lineLeft: false,
      lineCenter: true,
      lineRight: false,
      remoteAlive: true,
      estop: false
    };

    if (preset === "left") {
      next.lineLeft = true;
      next.lineCenter = false;
      setMode("LINE");
    } else if (preset === "right") {
      next.lineRight = true;
      next.lineCenter = false;
      setMode("LINE");
    } else if (preset === "obstacle") {
      next.lineCenter = false;
      next.obstacleCenter = true;
      setMode("AVOID");
    } else if (preset === "lost") {
      next.lineCenter = false;
      setMode("LINE");
    } else if (preset === "remoteLost") {
      next.lineCenter = false;
      next.remoteAlive = false;
      setMode("MANUAL");
    } else {
      setMode("LINE");
    }

    setSensors(next);
  };
  const userLoadPreset = stopDemoThen(loadPreset);

  return (
    <div className="smartcar-console">
      <div className="smartcar-backdrop" aria-hidden="true">
        <div className="track-line track-line-a" />
        <div className="track-line track-line-b" />
      </div>

      <header className="smartcar-topbar">
        <div>
          <span className="console-code">CAR01 V3.5 // TEACHING CONSOLE</span>
          <h1>智能小车三红外循迹教学控制台</h1>
          <p>
            这是网页端教学演示，不连接蓝牙，不向真车发送指令。所有状态来自最终版代码的决策逻辑，用来帮助同学理解传感器、状态机和电机 PWM。
          </p>
        </div>
        <div className={`console-status status-${derived.safety}`}>
          <span />
          <strong>{derived.action}</strong>
          <small>{modeMeta[mode].label}</small>
        </div>
      </header>

      <div className={demoMode ? "smartcar-demobar is-on" : "smartcar-demobar"}>
        <button
          type="button"
          className={demoMode ? "demo-toggle on" : "demo-toggle"}
          onClick={() => setDemoMode((value) => !value)}
          aria-pressed={demoMode}
        >
          {demoMode ? "■ 停止演示" : "▶ 演示模式"}
        </button>
        <p className="demo-note">
          {demoMode
            ? demoNote
            : "点击后自动播放“循迹 → 避障 → 手动 → 急停”的完整决策剧情；演示时进行任何手动操作都会暂停演示。"}
        </p>
      </div>

      <nav className="smartcar-tabs" aria-label="智能小车控制台视图">
        {tabs.map((tab) => (
          <button
            className={activeView === tab.key ? "active" : ""}
            key={tab.key}
            type="button"
            onClick={() => setActiveView(tab.key)}
          >
            <small>{tab.sub}</small>
            {tab.title}
          </button>
        ))}
      </nav>

      {activeView === "dashboard" && (
        <DashboardView mode={mode} derived={derived} sensors={sensors} />
      )}

      {activeView === "control" && (
        <ControlView
          derived={derived}
          manualForward={manualForward}
          manualTurn={manualTurn}
          mode={mode}
          sensors={sensors}
          loadPreset={userLoadPreset}
          setManualForward={userSetManualForward}
          setManualTurn={userSetManualTurn}
          setMode={userSetMode}
          toggleSensor={userToggleSensor}
        />
      )}

      {activeView === "principle" && <PrincipleView derived={derived} mode={mode} sensors={sensors} />}
    </div>
  );
}

const DashboardView = memo(function DashboardView({
  mode,
  derived,
  sensors
}: {
  mode: CarMode;
  derived: DerivedState;
  sensors: SensorState;
}) {
  return (
    <main className="smartcar-grid dashboard-grid">
      <section className="smartcar-panel car-visual-panel">
        <div className="panel-heading">
          <h2>车辆状态</h2>
          <span className={`mode-chip mode-${mode.toLowerCase()}`}>{modeMeta[mode].short}</span>
        </div>
        <CarDiagram mode={mode} sensors={sensors} derived={derived} />
      </section>

      <section className="smartcar-panel metrics-panel">
        <h2>实时决策</h2>
        <div className="metric-row">
          <span>动作</span>
          <strong>{derived.action}</strong>
        </div>
        <div className="metric-row">
          <span>左轮 PWM</span>
          <strong>{derived.leftPwm}</strong>
        </div>
        <div className="metric-row">
          <span>右轮 PWM</span>
          <strong>{derived.rightPwm}</strong>
        </div>
        <div className="metric-row">
          <span>LED 闪烁</span>
          <strong>{derived.ledPulses === 0 ? "不闪" : `${derived.ledPulses} 闪`}</strong>
        </div>
        <p className="decision-detail">{derived.detail}</p>
      </section>

      <section className="smartcar-panel sensor-panel">
        <h2>传感器电平</h2>
        <div className="sensor-readout">
          <SignalRow label="左红外" active={sensors.obstacleLeft} onText="有障碍 / LOW" offText="无障碍 / HIGH" />
          <SignalRow label="中红外" active={sensors.obstacleCenter} onText="有障碍 / LOW" offText="无障碍 / HIGH" />
          <SignalRow label="右红外" active={sensors.obstacleRight} onText="有障碍 / LOW" offText="无障碍 / HIGH" />
          <SignalRow label="左循迹" active={sensors.lineLeft} onText="黑线 / HIGH" offText="白底 / LOW" />
          <SignalRow label="中循迹" active={sensors.lineCenter} onText="黑线 / HIGH" offText="白底 / LOW" />
          <SignalRow label="右循迹" active={sensors.lineRight} onText="黑线 / HIGH" offText="白底 / LOW" />
        </div>
      </section>

      <section className="smartcar-panel serial-panel">
        <h2>串口观察</h2>
        <code>{derived.serialLine}</code>
        <p>
          课堂调试时先看模式是否正确，再看传感器电平是否随手挡、放黑线变化，最后才调整速度参数。
        </p>
      </section>
    </main>
  );
});

const ControlView = memo(function ControlView({
  mode,
  sensors,
  derived,
  manualForward,
  manualTurn,
  setMode,
  toggleSensor,
  loadPreset,
  setManualForward,
  setManualTurn
}: {
  mode: CarMode;
  sensors: SensorState;
  derived: DerivedState;
  manualForward: number;
  manualTurn: number;
  setMode: (mode: CarMode) => void;
  toggleSensor: (key: SensorKey) => void;
  loadPreset: (preset: "straight" | "left" | "right" | "obstacle" | "lost" | "remoteLost") => void;
  setManualForward: (value: number) => void;
  setManualTurn: (value: number) => void;
}) {
  return (
    <main className="smartcar-grid control-grid">
      <section className="smartcar-panel mode-panel">
        <h2>模式按键</h2>
        <div className="mode-buttons">
          {(["PARKED", "AVOID", "LINE", "MANUAL"] as CarMode[]).map((item) => (
            <button
              className={mode === item ? "selected" : ""}
              key={item}
              type="button"
              onClick={() => setMode(item)}
            >
              <small>{modeMeta[item].short}</small>
              {modeMeta[item].label}
            </button>
          ))}
        </div>
        <p>{modeMeta[mode].desc}</p>
      </section>

      <section className="smartcar-panel sensor-switch-panel">
        <h2>模拟输入</h2>
        <div className="sensor-switches">
          {sensorLabels.map((sensor) => (
            <label key={sensor.key} className={sensors[sensor.key] ? "checked" : ""}>
              <input type="checkbox" checked={sensors[sensor.key]} onChange={() => toggleSensor(sensor.key)} />
              <span>{sensor.label}</span>
              <small>{sensor.hint}</small>
            </label>
          ))}
        </div>
      </section>

      <section className="smartcar-panel preset-panel">
        <h2>课堂情境</h2>
        <div className="preset-list">
          <button type="button" onClick={() => loadPreset("straight")}>中间压线直行</button>
          <button type="button" onClick={() => loadPreset("left")}>黑线偏左修正</button>
          <button type="button" onClick={() => loadPreset("right")}>黑线偏右修正</button>
          <button type="button" onClick={() => loadPreset("obstacle")}>正前方避障</button>
          <button type="button" onClick={() => loadPreset("lost")}>丢线停车</button>
          <button type="button" onClick={() => loadPreset("remoteLost")}>遥控失联</button>
        </div>
      </section>

      <section className="smartcar-panel manual-panel">
        <h2>手动模式滑杆</h2>
        <label>
          <span>前进 / 后退</span>
          <output>{manualForward}</output>
          <input
            type="range"
            min={-180}
            max={180}
            value={manualForward}
            onChange={(event) => setManualForward(Number(event.currentTarget.value))}
          />
        </label>
        <label>
          <span>左转 / 右转</span>
          <output>{manualTurn}</output>
          <input
            type="range"
            min={-120}
            max={120}
            value={manualTurn}
            onChange={(event) => setManualTurn(Number(event.currentTarget.value))}
          />
        </label>
        <div className={`action-banner status-${derived.safety}`}>
          <strong>{derived.action}</strong>
          <span>L {derived.leftPwm} / R {derived.rightPwm}</span>
        </div>
      </section>
    </main>
  );
});

const PrincipleView = memo(function PrincipleView({
  mode,
  sensors,
  derived
}: {
  mode: CarMode;
  sensors: SensorState;
  derived: DerivedState;
}) {
  return (
    <main className="principle-stack">
      <section className="smartcar-panel principle-intro">
        <h2>从电平到动作</h2>
        <p>
          最终版程序的核心不是“让电机转”，而是把输入拆成清楚的链条：
          传感器电平、模式状态机、动作决策、左右轮 PWM、安全保护。哪一环错了，就查哪一环。
        </p>
      </section>

      <section className="smartcar-panel flow-panel">
        <h2>状态机链路</h2>
        <StateMachineDiagram mode={mode} sensors={sensors} derived={derived} />
      </section>

      <section className="smartcar-panel pin-panel">
        <h2>关键接线</h2>
        <div className="pin-table">
          {pinRows.map(([part, pins, note]) => (
            <div key={part}>
              <strong>{part}</strong>
              <span>{pins}</span>
              <small>{note}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="smartcar-panel concept-panel">
        <h2>这版程序解决的 4 个真实问题</h2>
        <div className="concept-grid">
          <article>
            <h3>共地和使能</h3>
            <p>ESP32、DRV8833、传感器和电机电源必须共地；驱动板的 STBY / SLEEP / EN 要接高电平。</p>
          </article>
          <article>
            <h3>模式切换先停车</h3>
            <p>按键切换模式前先 `stopMotors()`，避免旧模式留下的速度让学生误判算法。</p>
          </article>
          <article>
            <h3>起步冲量</h3>
            <p>TT 电机低速容易堵转，程序先给短暂 kick，再用斜坡平滑过渡到目标 PWM。</p>
          </article>
          <article>
            <h3>遥控失联保护</h3>
            <p>手动模式只有 400ms 内收到有效帧才继续输出，否则自动停车。</p>
          </article>
        </div>
      </section>
    </main>
  );
});

function SignalRow({ label, active, onText, offText }: { label: string; active: boolean; onText: string; offText: string }) {
  return (
    <div className={active ? "signal-row active" : "signal-row"}>
      <span>{label}</span>
      <strong>{active ? onText : offText}</strong>
    </div>
  );
}

const CarDiagram = memo(function CarDiagram({
  mode,
  sensors,
  derived
}: {
  mode: CarMode;
  sensors: SensorState;
  derived: DerivedState;
}) {
  const moving = derived.leftPwm !== 0 || derived.rightPwm !== 0;
  const leftSpeed = Math.max(0.35, Math.abs(derived.leftPwm) / 180);
  const rightSpeed = Math.max(0.35, Math.abs(derived.rightPwm) / 180);

  return (
    <svg className="car-diagram" viewBox="0 0 520 320" role="img" aria-label="智能小车状态示意图">
      <defs>
        <linearGradient id="carBody" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stopColor="#2563eb" />
          <stop offset="100%" stopColor="#0f766e" />
        </linearGradient>
      </defs>
      <rect className="bench" x="0" y="0" width="520" height="320" rx="18" />
      <path className="black-line" d="M38 250 C128 210 186 288 260 238 C326 192 393 214 482 172" />
      <g className={`car-body ${moving ? "moving" : ""}`} transform="translate(155 70)">
        <rect className="wheel left-wheel" x="18" y="34" width="42" height="28" rx="8" style={{ animationDuration: `${1 / leftSpeed}s` }} />
        <rect className="wheel left-wheel" x="18" y="154" width="42" height="28" rx="8" style={{ animationDuration: `${1 / leftSpeed}s` }} />
        <rect className="wheel right-wheel" x="208" y="34" width="42" height="28" rx="8" style={{ animationDuration: `${1 / rightSpeed}s` }} />
        <rect className="wheel right-wheel" x="208" y="154" width="42" height="28" rx="8" style={{ animationDuration: `${1 / rightSpeed}s` }} />
        <rect className="chassis" x="50" y="48" width="166" height="120" rx="18" />
        <rect className="board" x="78" y="72" width="48" height="36" rx="6" />
        <text className="svg-label" x="102" y="95" textAnchor="middle">ESP32</text>
        <rect className="driver" x="142" y="72" width="48" height="36" rx="6" />
        <text className="svg-label" x="166" y="95" textAnchor="middle">DRV</text>
        <circle className={mode === "AVOID" ? "mode-led on" : "mode-led"} cx="92" cy="134" r="6" />
        <circle className={mode === "LINE" ? "mode-led on" : "mode-led"} cx="112" cy="134" r="6" />
        <circle className={mode === "MANUAL" ? "mode-led on" : "mode-led"} cx="132" cy="134" r="6" />
        <SensorDot x={216} y={62} active={sensors.obstacleLeft} label="L" />
        <SensorDot x={238} y={108} active={sensors.obstacleCenter} label="C" />
        <SensorDot x={216} y={154} active={sensors.obstacleRight} label="R" />
        <LineDot x={82} y={184} active={sensors.lineLeft} />
        <LineDot x={116} y={190} active={sensors.lineCenter} />
        <LineDot x={150} y={184} active={sensors.lineRight} />
      </g>
      <g className="pwm-bars">
        <text x="34" y="44">LEFT PWM</text>
        <rect x="34" y="56" width="120" height="10" rx="5" />
        <rect className="pwm-fill" x="94" y="56" width={Math.abs(derived.leftPwm) / 255 * 60} height="10" rx="5" transform={derived.leftPwm < 0 ? "scale(-1 1) translate(-188 0)" : undefined} />
        <text x="34" y="92">RIGHT PWM</text>
        <rect x="34" y="104" width="120" height="10" rx="5" />
        <rect className="pwm-fill right" x="94" y="104" width={Math.abs(derived.rightPwm) / 255 * 60} height="10" rx="5" transform={derived.rightPwm < 0 ? "scale(-1 1) translate(-188 0)" : undefined} />
      </g>
      <text className="action-label" x="260" y="42" textAnchor="middle">{derived.action}</text>
    </svg>
  );
});

function SensorDot({ x, y, active, label }: { x: number; y: number; active: boolean; label: string }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <circle className={active ? "sensor-dot active obstacle" : "sensor-dot"} r="10" />
      <text className="svg-label" y="4" textAnchor="middle">{label}</text>
    </g>
  );
}

function LineDot({ x, y, active }: { x: number; y: number; active: boolean }) {
  return <circle className={active ? "line-dot active" : "line-dot"} cx={x} cy={y} r="7" />;
}

const StateMachineDiagram = memo(function StateMachineDiagram({
  mode,
  sensors,
  derived
}: {
  mode: CarMode;
  sensors: SensorState;
  derived: DerivedState;
}) {
  const lineBits = `${sensors.lineLeft ? 1 : 0}${sensors.lineCenter ? 1 : 0}${sensors.lineRight ? 1 : 0}`;
  const obstacleBits = `${sensors.obstacleLeft ? 1 : 0}${sensors.obstacleCenter ? 1 : 0}${sensors.obstacleRight ? 1 : 0}`;

  return (
    <svg className="flow-diagram" viewBox="0 0 780 260" role="img" aria-label="智能小车状态机流程">
      {[
        { x: 30, y: 54, title: "读取输入", text: `避障 ${obstacleBits} / 循迹 ${lineBits}` },
        { x: 210, y: 54, title: "判断模式", text: modeMeta[mode].label },
        { x: 390, y: 54, title: "状态机决策", text: derived.action },
        { x: 570, y: 54, title: "输出 PWM", text: `L ${derived.leftPwm} / R ${derived.rightPwm}` }
      ].map((node, index) => (
        <g key={node.title}>
          <rect className={index === 1 ? "flow-node current" : "flow-node"} x={node.x} y={node.y} width="150" height="92" rx="12" />
          <text className="flow-title" x={node.x + 75} y={node.y + 34} textAnchor="middle">{node.title}</text>
          <text className="flow-text" x={node.x + 75} y={node.y + 62} textAnchor="middle">{node.text}</text>
          {index < 3 && <path className="flow-arrow" d={`M${node.x + 150} 100 L${node.x + 178} 100`} />}
        </g>
      ))}
      <path className="safety-loop" d="M645 160 C645 214 134 214 134 160" />
      <text className="flow-text" x="390" y="220" textAnchor="middle">急停、共地、电机供电和遥控失联保护始终优先于动作算法</text>
    </svg>
  );
});
