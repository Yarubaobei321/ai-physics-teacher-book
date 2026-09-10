import { memo, type CSSProperties } from "react";
import type { RoverTelemetry } from "../../lib/mars-rover/roverProtocol";
import { clampRange } from "../../lib/mars-rover/useRover";
import { ArcGauge, AttitudeHorizon, Sparkline, StatusRow, formatTime } from "./widgets";

export const MissionView = memo(function MissionView({
  telemetry,
  history,
  batteryPercent,
  riskCount
}: {
  telemetry: RoverTelemetry;
  history: RoverTelemetry[];
  batteryPercent: number;
  riskCount: number;
}) {
  const tiltWarn = Math.abs(telemetry.pitch) > 25 || Math.abs(telemetry.roll) > 25;

  return (
    <main className="mission-grid">
      <section className="panel gauges-panel" aria-label="能源与环境">
        <h2 className="panel-title">能源 / 环境</h2>
        <div className="gauge-stack">
          <ArcGauge
            label="电池电压"
            unit="V"
            value={telemetry.batteryV}
            display={telemetry.batteryV.toFixed(2)}
            min={6.4}
            max={8.4}
            color={telemetry.batteryV > 0 && telemetry.batteryV < 6.9 ? "#ff4757" : "#51f5a3"}
            caption={`电量约 ${Math.round(batteryPercent)}%`}
            warn={telemetry.batteryV > 0 && telemetry.batteryV < 6.9}
          />
          <ArcGauge
            label="太阳能功率"
            unit="W"
            value={telemetry.solarW}
            display={telemetry.solarW.toFixed(2)}
            min={0}
            max={3.5}
            color="#ffb547"
            caption={telemetry.dust ? "⚠ 面板积尘，功率受损" : telemetry.tracker ? "追光运行中" : "固定朝向"}
            warn={telemetry.dust}
          />
          <ArcGauge
            label="光照强度"
            unit="lx"
            value={telemetry.lux}
            display={telemetry.lux >= 1000 ? `${(telemetry.lux / 1000).toFixed(1)}k` : telemetry.lux.toFixed(0)}
            min={0}
            max={40000}
            color="#3ce6ff"
            caption="BH1750 环境光"
          />
        </div>
      </section>

      <section className="panel rover-panel" aria-label="车辆实时状态">
        <div className="panel-heading">
          <h2 className="panel-title">尘光一号 · 实时态势</h2>
          <span className={`mode-badge mode-${telemetry.mode.toLowerCase()}`}>{telemetry.mode}</span>
        </div>
        <RoverTopView telemetry={telemetry} />
        <div className="rover-readout">
          <div><label>左轮 PWM</label><strong>{telemetry.leftPwm}</strong></div>
          <div><label>右轮 PWM</label><strong>{telemetry.rightPwm}</strong></div>
          <div><label>左轮转速</label><strong>{telemetry.speedL} <small>RPM</small></strong></div>
          <div><label>右轮转速</label><strong>{telemetry.speedR} <small>RPM</small></strong></div>
          <div><label>前方距离</label><strong>{telemetry.distF < 0 ? "—" : `${telemetry.distF}`} <small>mm</small></strong></div>
          <div><label>对地距离</label><strong>{telemetry.distD < 0 ? "—" : `${telemetry.distD}`} <small>mm</small></strong></div>
        </div>
        <p className="update-stamp">遥测 #{telemetry.seq} · 最后更新 {formatTime(telemetry.receivedAt)}</p>
      </section>

      <section className="panel safety-panel" aria-label="安全状态">
        <h2 className="panel-title">安全裁决 <span className={riskCount > 0 ? "risk-badge danger" : "risk-badge"}>{riskCount > 0 ? `${riskCount} 项告警` : "全部正常"}</span></h2>
        <AttitudeHorizon pitch={telemetry.pitch} roll={telemetry.roll} />
        <div className="status-list">
          <StatusRow label="急停 ESTOP" active={telemetry.estop} danger />
          <StatusRow label="前方障碍" active={telemetry.obstacle} danger detail={telemetry.obstacle ? `${telemetry.distF}mm` : undefined} />
          <StatusRow label="坑洞风险" active={telemetry.pit} danger detail={telemetry.pit ? `${telemetry.distD}mm` : undefined} />
          <StatusRow label="倾角告警" active={tiltWarn} danger />
          <StatusRow label="低电量" active={telemetry.batteryV > 0 && telemetry.batteryV < 6.9} danger />
          <StatusRow label="面板积尘" active={telemetry.dust} />
          <StatusRow label="风扇除尘" active={telemetry.fan} detail={telemetry.fan ? "运行" : "停止"} />
          <StatusRow label="太阳能追光" active={telemetry.tracker} detail={telemetry.tracker ? "追踪中" : "关闭"} />
        </div>
      </section>

      <section className="panel trends-panel" aria-label="遥测趋势">
        <h2 className="panel-title">遥测趋势 <small>{history.length || 1} 条记录</small></h2>
        <div className="chart-grid">
          <Sparkline title="电池电压" data={history} accessor={(t) => t.batteryV} unit="V" decimals={2} color="#51f5a3" min={6.4} max={8.4} fallback={telemetry.batteryV} />
          <Sparkline title="太阳能功率" data={history} accessor={(t) => t.solarW} unit="W" decimals={2} color="#ffb547" min={0} max={3.5} fallback={telemetry.solarW} />
          <Sparkline title="光照强度" data={history} accessor={(t) => t.lux} unit="lx" decimals={0} color="#3ce6ff" min={0} max={40000} fallback={telemetry.lux} />
          <Sparkline title="前方距离" data={history} accessor={(t) => (t.distF < 0 ? 2000 : t.distF)} unit="mm" decimals={0} color="#c792ff" min={0} max={2000} fallback={telemetry.distF < 0 ? 2000 : telemetry.distF} />
        </div>
      </section>
    </main>
  );
});

/** 火星车俯视动画：车轮随 PWM 转动、TOF 波束随距离伸缩、循迹探头实时点亮 */
const RoverTopView = memo(function RoverTopView({ telemetry }: { telemetry: RoverTelemetry }) {
  const moving = telemetry.leftPwm !== 0 || telemetry.rightPwm !== 0;
  // 波束长度：120~900mm 映射到 20~120px
  const beamLen = telemetry.distF < 0 ? 120 : clampRange((telemetry.distF / 900) * 120, 18, 120);
  const obstacleX = 170 + beamLen;

  const wheelStyle = (pwm: number): CSSProperties => ({
    // PWM 越大滚动越快；0 时暂停
    animationDuration: pwm === 0 ? undefined : `${clampRange(1.4 - (Math.abs(pwm) / 255) * 1.15, 0.25, 1.4)}s`,
    animationPlayState: pwm === 0 ? "paused" : "running",
    animationDirection: pwm < 0 ? "reverse" : "normal"
  });

  return (
    <div className={`rover-topview ${telemetry.estop ? "estop" : ""}`}>
      <svg viewBox="0 0 320 200" role="img" aria-label="火星车俯视示意">
        <defs>
          <linearGradient id="beamGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#3ce6ff" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#3ce6ff" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* 火星地表网格 */}
        <g className="ground-grid">
          {[0, 40, 80, 120, 160, 200].map((y) => (
            <line key={`h${y}`} x1="0" y1={y} x2="320" y2={y} />
          ))}
          {[0, 40, 80, 120, 160, 200, 240, 280, 320].map((x) => (
            <line key={`v${x}`} x1={x} y1="0" x2={x} y2="200" />
          ))}
        </g>

        {/* 前方 TOF 波束（车头朝右） */}
        <polygon
          className={`tof-beam ${telemetry.obstacle ? "alert" : ""}`}
          points={`170,86 ${obstacleX},${100 - beamLen * 0.18} ${obstacleX},${100 + beamLen * 0.18} 170,114`}
          fill="url(#beamGrad)"
        />
        {telemetry.distF >= 0 && telemetry.distF < 900 && (
          <g className={`obstacle-rock ${telemetry.obstacle ? "alert" : ""}`} transform={`translate(${obstacleX} 100)`}>
            <path d="M-8 8 L-10 -2 L-3 -9 L6 -7 L10 2 L5 9 Z" />
            <text y="22" textAnchor="middle" className="dist-label">{telemetry.distF}mm</text>
          </g>
        )}

        {/* 车体（按横滚小幅倾斜以示姿态） */}
        <g transform={`rotate(${clampRange(telemetry.roll, -12, 12) * 0.6} 120 100)`}>
          {/* 六轮 */}
          {[58, 110, 162].map((x, i) => (
            <g key={`wl${i}`}>
              <rect className="wheel" x={x} y="44" width="30" height="16" rx="5" style={wheelStyle(telemetry.leftPwm)} />
              <rect className="wheel" x={x} y="140" width="30" height="16" rx="5" style={wheelStyle(telemetry.rightPwm)} />
            </g>
          ))}
          {/* 底盘 */}
          <rect className="rover-body" x="52" y="62" width="146" height="76" rx="10" />
          {/* 太阳能板 */}
          <g className={telemetry.tracker ? "solar-deck tracking" : "solar-deck"}>
            <rect x="64" y="72" width="58" height="56" rx="4" />
            <line x1="83" y1="72" x2="83" y2="128" />
            <line x1="102" y1="72" x2="102" y2="128" />
            <line x1="64" y1="91" x2="122" y2="91" />
            <line x1="64" y1="110" x2="122" y2="110" />
            {telemetry.dust && <circle className="dust-dot" cx="78" cy="84" r="2.4" />}
            {telemetry.dust && <circle className="dust-dot" cx="98" cy="102" r="2" />}
            {telemetry.dust && <circle className="dust-dot" cx="112" cy="88" r="2.6" />}
          </g>
          {/* A/B 板 */}
          <rect className="board-chip board-a-chip" x="132" y="72" width="28" height="24" rx="3" />
          <text className="chip-label" x="146" y="87" textAnchor="middle">A</text>
          <rect className="board-chip board-b-chip" x="132" y="104" width="28" height="24" rx="3" />
          <text className="chip-label" x="146" y="119" textAnchor="middle">B</text>
          {/* 风扇 */}
          <g className={telemetry.fan ? "fan-rotor spinning" : "fan-rotor"} transform="translate(178 100)">
            <circle r="11" className="fan-ring" />
            <g className="fan-blades">
              <path d="M0 -9 C4 -5 4 -2 0 0 C-4 -2 -4 -5 0 -9" />
              <path d="M9 4.5 C4 6 2 4 0 0 C3 -1 7 1 9 4.5" transform="rotate(0)" />
              <path d="M-9 4.5 C-4 6 -2 4 0 0 C-3 -1 -7 1 -9 4.5" />
            </g>
          </g>
          {/* 循迹探头（车头下方 5 点，bit0=最左=上侧） */}
          {[0, 1, 2, 3, 4].map((i) => (
            <circle
              key={`line${i}`}
              className={`line-probe ${telemetry.line & (1 << i) ? "on" : ""}`}
              cx="204"
              cy={78 + i * 11}
              r="3.4"
            />
          ))}
          {/* 坑洞传感器 */}
          <circle className={`pit-sensor ${telemetry.pit ? "alert" : ""}`} cx="212" cy="100" r="4.5" />
        </g>

        {/* 急停遮罩 */}
        {telemetry.estop && (
          <g className="estop-overlay">
            <rect x="0" y="0" width="320" height="200" />
            <text x="160" y="104" textAnchor="middle">■ EMERGENCY STOP ■</text>
          </g>
        )}

        {/* 运动指示 */}
        {moving && !telemetry.estop && (
          <g className="motion-trail">
            <line x1="20" y1="86" x2="46" y2="86" />
            <line x1="12" y1="100" x2="44" y2="100" />
            <line x1="20" y1="114" x2="46" y2="114" />
          </g>
        )}
      </svg>
    </div>
  );
});
