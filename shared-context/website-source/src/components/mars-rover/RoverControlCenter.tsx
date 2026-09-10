import { useRover, type ViewKey } from "../../lib/mars-rover/useRover";
import { ROVER_DEVICE_NAME_PREFIX } from "../../lib/mars-rover/roverProtocol";
import { MissionView } from "./MissionView";
import { ControlView } from "./ControlView";
import { AnatomyView } from "./AnatomyView";

const tabs: Array<{ key: ViewKey; label: string; sub: string }> = [
  { key: "dashboard", label: "任务驾驶舱", sub: "MISSION" },
  { key: "control", label: "操控台", sub: "CONTROL" },
  { key: "modules", label: "部件原理", sub: "ANATOMY" }
];

export default function RoverControlCenter() {
  const rover = useRover();
  const {
    activeView,
    setActiveView,
    connectionState,
    deviceName,
    bluetoothSupported,
    isConnected,
    demoMode,
    statusText,
    telemetry,
    history,
    logs,
    batteryPercent,
    riskCount,
    controlMode,
    forward,
    turn,
    fanEnabled,
    trackerEnabled,
    canInteract,
    canDrive,
    setForward,
    setTurn,
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
    sendDriveNow
  } = rover;

  const linkLive = isConnected || demoMode;

  return (
    <div className="hud">
      <div className="hud-bg" aria-hidden="true">
        <div className="stars" />
        <div className="mars-glow" />
        <div className="grid-floor" />
      </div>

      <header className="topbar">
        <div className="mission-id">
          <span className="mission-code">CHENGUANG-01 // MARS PATROL</span>
          <h1>尘光一号 · 火星巡检地面站</h1>
          <p className="lead">双 ESP32 安全架构 · Web Bluetooth 直连 · 能源闭环演示</p>
        </div>

        <div className="link-chain" aria-label="链路状态">
          {["地面站", "BLE", "B 板", "UART", "A 板"].map((node, i) => (
            <span key={node} className={`chain-node ${linkLive ? "live" : ""} ${i % 2 === 1 ? "chain-wire" : ""}`}>
              {node}
            </span>
          ))}
        </div>

        <div className="status-cluster" aria-label="连接状态">
          <span className={`status-dot state-${connectionState}`} />
          <div>
            <strong>{statusText}</strong>
            <span>{deviceName}</span>
          </div>
        </div>
      </header>

      <section className="connection-panel" aria-label="连接与演示">
        <div className="connection-actions">
          <button className="button primary" type="button" onClick={() => void connect("name")} disabled={!bluetoothSupported || connectionState === "connecting"}>
            ◉ 连接 {ROVER_DEVICE_NAME_PREFIX}
          </button>
          <button className="button secondary" type="button" onClick={() => void connect("all")} disabled={!bluetoothSupported || connectionState === "connecting"}>
            搜索所有蓝牙
          </button>
          <button className={demoMode ? "button secondary demo-on" : "button secondary"} type="button" onClick={isConnected ? disconnect : demoMode ? stopDemo : startDemo}>
            {isConnected ? "断开连接" : demoMode ? "停止演示" : "▶ 演示模式"}
          </button>
        </div>
        {demoMode && <span className="demo-hint">演示模式：本地模拟剧情（接近障碍、积尘降功率、风扇恢复），不向真车发命令。</span>}
      </section>

      {!bluetoothSupported && (
        <section className="support-warning" role="status">
          当前浏览器没有开放 Web Bluetooth。请用桌面 Chrome 或 Edge，并通过 localhost 或 HTTPS 打开本页面。
        </section>
      )}

      <nav className="view-tabs" aria-label="地面站功能">
        {tabs.map((tab) => (
          <button
            className={activeView === tab.key ? "active" : ""}
            key={tab.key}
            type="button"
            onClick={() => setActiveView(tab.key)}
          >
            <small>{tab.sub}</small>
            {tab.label}
          </button>
        ))}
      </nav>

      {activeView === "dashboard" && (
        <MissionView telemetry={telemetry} history={history} batteryPercent={batteryPercent} riskCount={riskCount} />
      )}

      {activeView === "control" && (
        <ControlView
          canInteract={canInteract}
          canDrive={canDrive}
          controlMode={controlMode}
          fanEnabled={fanEnabled}
          forward={forward}
          logs={logs}
          setForward={setForward}
          setMode={setMode}
          setTurn={setTurn}
          stopDrive={stopDrive}
          telemetry={telemetry}
          toggleFan={toggleFan}
          toggleTracker={toggleTracker}
          trackerEnabled={trackerEnabled}
          triggerEstop={triggerEstop}
          clearEstop={clearEstop}
          turn={turn}
          sendDriveNow={sendDriveNow}
        />
      )}

      {activeView === "modules" && <AnatomyView telemetry={telemetry} />}

      <footer className="hud-footer">
        <span>SAFETY: A 板最终裁决 · 失联自动停车</span>
        <span>LINK: BLE GATT 7b3f1000-…-4d6172730001</span>
        <span>TELEMETRY v0.2 · 22 字段 CSV</span>
      </footer>
    </div>
  );
}
