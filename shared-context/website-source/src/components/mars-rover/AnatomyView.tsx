import { memo, type ReactNode } from "react";
import type { RoverTelemetry } from "../../lib/mars-rover/roverProtocol";
import { clampRange } from "../../lib/mars-rover/useRover";

/**
 * 部件原理视图：每个模块一张「会动的原理图」。
 * 所有动画都绑定实时遥测——评委看到的不是贴图，而是车上正在发生的事。
 */
export const AnatomyView = memo(function AnatomyView({ telemetry }: { telemetry: RoverTelemetry }) {
  return (
    <main className="anatomy-grid">
      <section className="panel anatomy-intro">
        <h2 className="panel-title">部件原理 · 实时动画</h2>
        <p>
          下面每张图都在用<strong>当前遥测数据</strong>驱动：拖动操控台的摇杆、触发障碍、打开风扇，
          图中的电流、激光、脉冲会跟着变化。这是整车工作原理的「透视图」。
        </p>
      </section>

      <AnatomyCard
        tag="指挥链路"
        title="网页 ⇄ BLE ⇄ B 板 ⇄ UART ⇄ A 板"
        live={`遥测 #${telemetry.seq}`}
        explain="网页用 Web Bluetooth 直连 B 板；B 板把命令经 UART 转发给 A 板，并把 A 板状态 + 能源数据打包成 CSV 遥测回推网页。任何一段断开，A 板都会因失联而自动停车。"
      >
        <LinkChainDiagram telemetry={telemetry} />
      </AnatomyCard>

      <AnatomyCard
        tag="安全核心"
        title="A 板安全裁决门"
        live={telemetry.estop ? "急停拦截中" : "通行检查中"}
        explain="网页命令只是「意图」。每条驾驶指令要依次通过急停、模式、失联超时、障碍/坑洞/倾角四道闸门，全部放行才会变成电机 PWM——这就是为什么网页崩溃也不会失控。"
      >
        <SafetyGateDiagram telemetry={telemetry} />
      </AnatomyCard>

      <AnatomyCard
        tag="动力"
        title="TB6612 H 桥电机驱动"
        live={`左轮 PWM ${telemetry.leftPwm}`}
        explain="H 桥由四个电子开关组成：对角导通决定电流方向，电流方向决定车轮正反转；PWM 快速通断的占空比决定平均电压，也就是车速。图中高亮路径是此刻真实的电流通路。"
      >
        <HBridgeDiagram pwm={telemetry.leftPwm} />
      </AnatomyCard>

      <AnatomyCard
        tag="测速"
        title="MC130 霍尔编码器"
        live={`左 ${telemetry.speedL} / 右 ${telemetry.speedR} RPM`}
        explain="电机尾部磁环旋转，霍尔元件感应出方波脉冲。13 线磁环 × 1:90 减速箱 = 每圈约 1170 个脉冲，数一秒内的脉冲数就得到轮速，用于直线修正与卡死判断。"
      >
        <EncoderDiagram speedL={telemetry.speedL} speedR={telemetry.speedR} />
      </AnatomyCard>

      <AnatomyCard
        tag="避障"
        title="VL53L0X 激光飞行时间测距"
        live={telemetry.distF < 0 ? "前向传感器未接入" : `前方 ${telemetry.distF} mm`}
        explain="发射一束 940nm 激光，光打到障碍物反弹回来。距离 = 光速 × 飞行时间 ÷ 2。一前一下两颗：前方测岩石障碍，前下方测对地距离——距离突然变大就是坑洞或台阶边缘。"
      >
        <TofDiagram distF={telemetry.distF} distD={telemetry.distD} obstacle={telemetry.obstacle} pit={telemetry.pit} />
      </AnatomyCard>

      <AnatomyCard
        tag="防侧翻"
        title="MPU6050 姿态感知"
        live={`Roll ${telemetry.roll.toFixed(1)}°`}
        explain="加速度计测出重力方向在三个轴上的分量，反算出车身俯仰与横滚角。横滚超 25° 进入警告区，超 35° A 板直接锁存急停——比驾驶员反应快得多。"
      >
        <ImuDiagram pitch={telemetry.pitch} roll={telemetry.roll} />
      </AnatomyCard>

      <AnatomyCard
        tag="自动巡线"
        title="五路红外循迹"
        live={`探头状态 ${telemetry.line.toString(2).padStart(5, "0")}`}
        explain="五个红外探头照向地面：黑线吸收红外（无反射），白地反射。哪个探头压线就知道黑线偏左还是偏右，加权平均算出误差，按比例修正左右轮速差——丢线超过 0.3 秒立即停车。"
      >
        <LineFollowDiagram line={telemetry.line} mode={telemetry.mode} />
      </AnatomyCard>

      <AnatomyCard
        tag="新能源"
        title="二维太阳能追光"
        live={`光照 ${telemetry.lux >= 1000 ? `${(telemetry.lux / 1000).toFixed(1)}k` : telemetry.lux.toFixed(0)} lx`}
        explain="四个光敏电阻分布在挡板四象限：太阳偏向哪边，哪边更亮。比较对边亮度差，驱动水平 + 俯仰两个舵机一步步把太阳能板转向太阳，发电功率随之提升。"
      >
        <SolarTrackerDiagram tracker={telemetry.tracker} lux={telemetry.lux} />
      </AnatomyCard>

      <AnatomyCard
        tag="能源闭环"
        title="积尘检测与风扇除尘"
        live={`太阳能 ${telemetry.solarW.toFixed(2)} W`}
        explain="火星沙尘是真实任务的头号杀手。TCRT5000 红外对管检测面板反射率：积尘 → 反射变差 → 发电功率下降；开启 5015 涡轮风扇吹扫 → 功率恢复。这套「检测-除尘-恢复」就是本车的能源管理闭环。"
      >
        <DustFanDiagram dust={telemetry.dust} fan={telemetry.fan} solarW={telemetry.solarW} />
      </AnatomyCard>
    </main>
  );
});

function AnatomyCard({
  tag,
  title,
  live,
  explain,
  children
}: {
  tag: string;
  title: string;
  live: string;
  explain: string;
  children: ReactNode;
}) {
  return (
    <article className="anatomy-card">
      <header>
        <span className="anatomy-tag">{tag}</span>
        <h3>{title}</h3>
        <span className="anatomy-live">{live}</span>
      </header>
      <div className="anatomy-diagram">{children}</div>
      <p>{explain}</p>
    </article>
  );
}

/* ---------- 1. 指挥链路 ---------- */
const LinkChainDiagram = memo(function LinkChainDiagram({ telemetry }: { telemetry: RoverTelemetry }) {
  return (
    <svg viewBox="0 0 360 110">
      {[
        { x: 10, label: "网页", sub: "地面站" },
        { x: 105, label: "B 板", sub: "能源网关" },
        { x: 200, label: "A 板", sub: "运动安全" },
        { x: 295, label: "电机", sub: "执行" }
      ].map((node) => (
        <g key={node.label} transform={`translate(${node.x} 32)`}>
          <rect className="node-box" width="56" height="44" rx="6" />
          <text className="node-label" x="28" y="20" textAnchor="middle">{node.label}</text>
          <text className="node-sub" x="28" y="35" textAnchor="middle">{node.sub}</text>
        </g>
      ))}
      {/* 链路标签 */}
      <text className="wire-label" x="85" y="24" textAnchor="middle">BLE</text>
      <text className="wire-label" x="180" y="24" textAnchor="middle">UART 115200</text>
      <text className="wire-label" x="275" y="24" textAnchor="middle">PWM</text>
      {/* 命令流（向右） */}
      <line className="wire" x1="66" y1="44" x2="105" y2="44" />
      <line className="wire" x1="161" y1="44" x2="200" y2="44" />
      <line className="wire" x1="256" y1="44" x2="295" y2="44" />
      <circle className="packet cmd" r="3.4"><animateMotion dur="2.4s" repeatCount="indefinite" path="M66 44 L295 44" /></circle>
      {/* 遥测流（向左） */}
      <line className="wire dim" x1="105" y1="64" x2="66" y2="64" />
      <line className="wire dim" x1="200" y1="64" x2="161" y2="64" />
      <circle className="packet telem" r="3.4"><animateMotion dur="2s" repeatCount="indefinite" path="M200 64 L66 64" /></circle>
      <text className="wire-label dim" x="133" y="92" textAnchor="middle">遥测 CSV ×{telemetry.seq}</text>
    </svg>
  );
});

/* ---------- 2. 安全裁决门 ---------- */
const SafetyGateDiagram = memo(function SafetyGateDiagram({ telemetry }: { telemetry: RoverTelemetry }) {
  const tiltBad = Math.abs(telemetry.pitch) > 35 || Math.abs(telemetry.roll) > 35;
  const gates = [
    { label: "急停", blocked: telemetry.estop },
    { label: "模式", blocked: telemetry.mode === "SAFE" },
    { label: "失联", blocked: false },
    { label: "障碍/坑洞/倾角", blocked: telemetry.obstacle || telemetry.pit || tiltBad }
  ];
  const anyBlocked = gates.some((g) => g.blocked);

  return (
    <svg viewBox="0 0 360 110">
      <text className="node-label" x="8" y="58">CMD</text>
      <line className="wire" x1="40" y1="54" x2="58" y2="54" />
      {gates.map((gate, i) => {
        const x = 58 + i * 66;
        return (
          <g key={gate.label} transform={`translate(${x} 0)`}>
            <rect className={`gate ${gate.blocked ? "blocked" : "open"}`} x="0" y="30" width="50" height="48" rx="6" />
            <text className="gate-label" x="25" y="50" textAnchor="middle">{gate.label.length > 4 ? "环境" : gate.label}</text>
            <text className={`gate-state ${gate.blocked ? "blocked" : "open"}`} x="25" y="68" textAnchor="middle">
              {gate.blocked ? "拦截" : "放行"}
            </text>
            {i < 3 && <line className="wire" x1="50" y1="54" x2="66" y2="54" />}
          </g>
        );
      })}
      <line className="wire" x1="372" y1="54" x2="332" y2="54" transform="translate(-50 0)" />
      <g transform={`translate(330 36)`}>
        <circle className={`motor-node ${anyBlocked ? "off" : "on"}`} cx="14" cy="18" r="16" />
        <text className="gate-label" x="14" y="22" textAnchor="middle">M</text>
      </g>
      {!anyBlocked && <circle className="packet cmd" r="3.2"><animateMotion dur="1.6s" repeatCount="indefinite" path="M40 54 L330 54" /></circle>}
      <text className="wire-label" x="180" y="100" textAnchor="middle">
        {anyBlocked ? "⛔ 指令在闸门处被拦截，电机输出 0" : "✅ 四道闸门全部放行，意图变成 PWM"}
      </text>
    </svg>
  );
});

/* ---------- 3. TB6612 H 桥 ---------- */
const HBridgeDiagram = memo(function HBridgeDiagram({ pwm }: { pwm: number }) {
  const fwd = pwm > 0;
  const rev = pwm < 0;
  const duty = Math.round((Math.abs(pwm) / 255) * 100);

  return (
    <svg viewBox="0 0 360 130">
      {/* 电源轨 */}
      <line className="rail" x1="60" y1="14" x2="240" y2="14" />
      <text className="wire-label" x="46" y="18" textAnchor="end">VM 7.4V</text>
      <line className="rail" x1="60" y1="116" x2="240" y2="116" />
      <text className="wire-label" x="46" y="120" textAnchor="end">GND</text>
      {/* 四个开关 */}
      <Switch x={90} y={28} on={fwd} label="Q1" />
      <Switch x={190} y={28} on={rev} label="Q2" />
      <Switch x={90} y={78} on={rev} label="Q3" />
      <Switch x={190} y={78} on={fwd} label="Q4" />
      {/* 电机 */}
      <circle className={`motor-node ${pwm !== 0 ? "on" : "off"}`} cx="150" cy="65" r="14" />
      <text className="gate-label" x="150" y="69" textAnchor="middle">M</text>
      {/* 电流路径 */}
      {fwd && (
        <path className="current-path" d="M100 14 L100 46 L100 56 L136 65 L164 65 L200 74 L200 96 L200 116" fill="none">
        </path>
      )}
      {rev && (
        <path className="current-path reverse" d="M200 14 L200 46 L200 56 L164 65 L136 65 L100 74 L100 96 L100 116" fill="none">
        </path>
      )}
      {/* PWM 占空比 */}
      <g transform="translate(262 24)">
        <text className="wire-label" x="42" y="0" textAnchor="middle">PWM 占空比 {duty}%</text>
        <rect className="duty-track" x="0" y="8" width="84" height="10" rx="3" />
        <rect className="duty-fill" x="0" y="8" width={84 * (duty / 100)} height="10" rx="3" />
        {/* 方波示意 */}
        <path
          className={`pwm-wave ${pwm !== 0 ? "active" : ""}`}
          d="M0 52 h10 v-14 h12 v14 h10 v-14 h12 v14 h10 v-14 h12 v14 h10"
          fill="none"
        />
        <text className="wire-label dim" x="42" y="74" textAnchor="middle">{pwm === 0 ? "停止" : pwm > 0 ? "正转 → 前进" : "反转 → 后退"}</text>
      </g>
    </svg>
  );
});

const Switch = memo(function Switch({ x, y, on, label }: { x: number; y: number; on: boolean; label: string }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect className={`switch-box ${on ? "on" : ""}`} x="-12" y="0" width="24" height="28" rx="4" />
      <text className="gate-label" x="0" y="18" textAnchor="middle">{label}</text>
      <text className={`switch-state ${on ? "on" : ""}`} x="22" y="18">{on ? "通" : "断"}</text>
    </g>
  );
});

/* ---------- 4. 编码器 ---------- */
const EncoderDiagram = memo(function EncoderDiagram({ speedL, speedR }: { speedL: number; speedR: number }) {
  const rpm = Math.abs(speedL);
  const spinning = rpm > 0;
  const dur = spinning ? clampRange(60 / rpm, 0.25, 4) : 0;

  return (
    <svg viewBox="0 0 360 120">
      {/* 磁环码盘 */}
      <g transform="translate(70 60)">
        <g
          className="encoder-disk"
          style={{
            animationDuration: spinning ? `${dur}s` : undefined,
            animationPlayState: spinning ? "running" : "paused",
            animationDirection: speedL < 0 ? "reverse" : "normal"
          }}
        >
          <circle className="disk-body" r="36" />
          {Array.from({ length: 13 }).map((_, i) => (
            <rect key={i} className={i % 2 === 0 ? "pole n" : "pole s"} x="-4" y="-36" width="8" height="11" transform={`rotate(${(360 / 13) * i})`} />
          ))}
          <circle className="disk-hub" r="8" />
        </g>
        <rect className="hall-sensor" x="40" y="-7" width="14" height="14" rx="3" />
        <text className="wire-label" x="47" y="24" textAnchor="middle">霍尔</text>
      </g>
      {/* 脉冲波形 */}
      <g transform="translate(150 28)">
        <text className="wire-label" x="0" y="0">脉冲输出（数脉冲 = 测速）</text>
        <g className="pulse-window">
          <path
            className={`pulse-wave ${spinning ? "active" : ""}`}
            d="M0 40 h12 v-22 h12 v22 h12 v-22 h12 v22 h12 v-22 h12 v22 h12 v-22 h12 v22 h12 v-22 h12 v22 h12 v-22 h12 v22 h12 v-22 h12 v22 h12"
            fill="none"
            style={{ animationDuration: spinning ? `${clampRange(dur / 4, 0.15, 1.5)}s` : undefined }}
          />
        </g>
        <text className="node-label" x="0" y="74">左 {speedL} RPM</text>
        <text className="node-label" x="100" y="74">右 {speedR} RPM</text>
        <text className="wire-label dim" x="0" y="90">13 极磁环 × 1:90 减速 ≈ 1170 脉冲/圈</text>
      </g>
    </svg>
  );
});

/* ---------- 5. VL53L0X ToF ---------- */
const TofDiagram = memo(function TofDiagram({
  distF,
  distD,
  obstacle,
  pit
}: {
  distF: number;
  distD: number;
  obstacle: boolean;
  pit: boolean;
}) {
  const wallX = distF < 0 ? 330 : 90 + clampRange((distF / 900) * 230, 36, 230);

  return (
    <svg viewBox="0 0 360 120">
      {/* 传感器 */}
      <g transform="translate(40 30)">
        <rect className="node-box" x="0" y="0" width="44" height="34" rx="5" />
        <text className="node-sub" x="22" y="14" textAnchor="middle">发射</text>
        <text className="node-sub" x="22" y="28" textAnchor="middle">接收</text>
      </g>
      {/* 激光往返 */}
      <line className="laser-path" x1="84" y1="38" x2={wallX} y2="38" />
      <line className="laser-path return" x1={wallX} y1="56" x2="84" y2="56" />
      <circle className="photon out" r="3"><animateMotion dur="1.1s" repeatCount="indefinite" path={`M84 38 L${wallX} 38`} /></circle>
      <circle className="photon back" r="3"><animateMotion dur="1.1s" begin="0.55s" repeatCount="indefinite" path={`M${wallX} 56 L84 56`} /></circle>
      {/* 障碍墙 */}
      <rect className={`tof-wall ${obstacle ? "alert" : ""}`} x={wallX} y="22" width="8" height="48" rx="2" />
      <text className="node-label" x={wallX + 4} y="86" textAnchor="middle">{distF < 0 ? "—" : `${distF}mm`}</text>
      {/* 公式 */}
      <text className="formula" x="40" y="104">距离 = 光速 × 飞行时间 ÷ 2</text>
      {/* 坑洞通道 */}
      <g transform="translate(250 92)">
        <text className={`wire-label ${pit ? "alert-text" : ""}`} x="0" y="0">
          ↓ 对地 {distD < 0 ? "—" : `${distD}mm`} {pit ? "⚠ 坑洞!" : ""}
        </text>
      </g>
    </svg>
  );
});

/* ---------- 6. MPU6050 ---------- */
const ImuDiagram = memo(function ImuDiagram({ pitch, roll }: { pitch: number; roll: number }) {
  const angle = clampRange(roll, -45, 45);
  const zone = Math.abs(roll) > 35 ? "estop" : Math.abs(roll) > 25 ? "warn" : "ok";

  return (
    <svg viewBox="0 0 360 120">
      {/* 阈值扇区 */}
      <g transform="translate(110 96)">
        <path className="tilt-zone ok" d={arcPath(70, -25, 25)} />
        <path className="tilt-zone warn" d={arcPath(70, 25, 35)} />
        <path className="tilt-zone warn" d={arcPath(70, -35, -25)} />
        <path className="tilt-zone danger" d={arcPath(70, 35, 50)} />
        <path className="tilt-zone danger" d={arcPath(70, -50, -35)} />
        {/* 车体侧影随横滚旋转 */}
        <g transform={`rotate(${angle})`} className={`tilt-rover ${zone}`}>
          <rect x="-34" y="-26" width="68" height="16" rx="5" />
          <circle cx="-20" cy="-6" r="8" />
          <circle cx="0" cy="-6" r="8" />
          <circle cx="20" cy="-6" r="8" />
        </g>
        {/* 重力矢量：始终竖直向下 */}
        <line className="gravity-vector" x1="0" y1="-58" x2="0" y2="-34" />
        <text className="wire-label" x="0" y="-62" textAnchor="middle">g</text>
      </g>
      <g transform="translate(230 30)">
        <text className="node-label" x="0" y="0">Pitch {pitch.toFixed(1)}°</text>
        <text className="node-label" x="0" y="20">Roll {roll.toFixed(1)}°</text>
        <text className="wire-label" x="0" y="44">&lt; 25° 正常</text>
        <text className="wire-label warn-text" x="0" y="60">25–35° 警告</text>
        <text className="wire-label alert-text" x="0" y="76">&gt; 35° 锁存急停</text>
      </g>
    </svg>
  );
});

function arcPath(r: number, fromDeg: number, toDeg: number): string {
  const a0 = ((fromDeg - 90) * Math.PI) / 180;
  const a1 = ((toDeg - 90) * Math.PI) / 180;
  const x0 = r * Math.cos(a0);
  const y0 = r * Math.sin(a0);
  const x1 = r * Math.cos(a1);
  const y1 = r * Math.sin(a1);
  return `M0 0 L${x0.toFixed(1)} ${y0.toFixed(1)} A${r} ${r} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)} Z`;
}

/* ---------- 7. 五路循迹 ---------- */
const LineFollowDiagram = memo(function LineFollowDiagram({ line, mode }: { line: number; mode: string }) {
  const bits = [0, 1, 2, 3, 4].map((i) => Boolean(line & (1 << i)));
  const weights = [-2, -1, 0, 1, 2];
  const activeCount = bits.filter(Boolean).length;
  const error = activeCount > 0 ? bits.reduce((sum, b, i) => sum + (b ? weights[i] : 0), 0) / activeCount : 0;

  return (
    <svg viewBox="0 0 360 120">
      {/* 地面与黑线 */}
      <rect className="track-ground" x="20" y="58" width="320" height="46" rx="6" />
      <path className="track-line" d={`M20 81 C 120 ${81 + error * 14}, 240 ${81 + error * 14}, 340 81`} />
      {/* 探头 */}
      {bits.map((on, i) => (
        <g key={i} transform={`translate(${110 + i * 35} 26)`}>
          <rect className={`probe ${on ? "on" : ""}`} x="-8" y="0" width="16" height="18" rx="3" />
          <line className={`probe-beam ${on ? "absorbed" : ""}`} x1="0" y1="18" x2="0" y2="46" />
          <text className="wire-label dim" x="0" y="-6" textAnchor="middle">{i + 1}</text>
        </g>
      ))}
      <text className="formula" x="20" y="20">误差 = 加权平均（压线探头） = {error.toFixed(1)}</text>
      <text className="wire-label" x="20" y="116">
        {mode !== "AUTO" ? "AUTO 模式下启用巡线" : activeCount === 0 ? "⚠ 丢线 → 0.3s 内停车" : error === 0 ? "居中直行" : error > 0 ? "线偏右 → 右修" : "线偏左 → 左修"}
      </text>
    </svg>
  );
});

/* ---------- 8. 太阳能追光 ---------- */
const SolarTrackerDiagram = memo(function SolarTrackerDiagram({ tracker, lux }: { tracker: boolean; lux: number }) {
  const brightness = clampRange(lux / 40000, 0.15, 1);

  return (
    <svg viewBox="0 0 360 120">
      {/* 太阳 */}
      <g transform="translate(60 34)" className="anim-sun" style={{ opacity: 0.45 + brightness * 0.55 }}>
        <circle r="16" className="sun-core" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
          <line key={deg} className="sun-ray" x1="0" y1="-20" x2="0" y2="-26" transform={`rotate(${deg})`} />
        ))}
      </g>
      {/* 光线 */}
      <line className="light-ray" x1="78" y1="44" x2="170" y2="68" />
      {/* 四象限光敏 */}
      <g transform="translate(180 50)">
        <rect className="ldr-quad q1 lit" x="-22" y="-22" width="20" height="20" rx="3" />
        <rect className="ldr-quad q2" x="2" y="-22" width="20" height="20" rx="3" />
        <rect className="ldr-quad q3 lit" x="-22" y="2" width="20" height="20" rx="3" />
        <rect className="ldr-quad q4" x="2" y="2" width="20" height="20" rx="3" />
        <text className="wire-label dim" x="0" y="40" textAnchor="middle">四路光敏</text>
      </g>
      {/* 舵机与面板 */}
      <g transform="translate(290 60)">
        <g className={`tracker-panel ${tracker ? "tracking" : ""}`}>
          <rect x="-30" y="-34" width="60" height="40" rx="4" className="panel-cell" />
          <line x1="-10" y1="-34" x2="-10" y2="6" className="panel-grid-line" />
          <line x1="10" y1="-34" x2="10" y2="6" className="panel-grid-line" />
          <line x1="-30" y1="-14" x2="30" y2="-14" className="panel-grid-line" />
        </g>
        <rect className="servo-base" x="-8" y="8" width="16" height="14" rx="3" />
        <text className="wire-label" x="0" y="40" textAnchor="middle">水平+俯仰舵机</text>
      </g>
      <text className="formula" x="120" y="112">亮度差 → 舵机步进 → 板面正对太阳 {tracker ? "（追光中）" : "（追光关闭）"}</text>
    </svg>
  );
});

/* ---------- 9. 积尘与风扇 ---------- */
const DustFanDiagram = memo(function DustFanDiagram({ dust, fan, solarW }: { dust: boolean; fan: boolean; solarW: number }) {
  const power = clampRange(solarW / 3.5, 0, 1);

  return (
    <svg viewBox="0 0 360 120">
      {/* 太阳能板 */}
      <g transform="translate(40 24)">
        <rect className="panel-cell big" width="120" height="64" rx="5" />
        <line className="panel-grid-line" x1="40" y1="0" x2="40" y2="64" />
        <line className="panel-grid-line" x1="80" y1="0" x2="80" y2="64" />
        <line className="panel-grid-line" x1="0" y1="32" x2="120" y2="32" />
        {/* 尘埃粒子 */}
        {dust &&
          [
            [18, 12], [44, 26], [66, 10], [92, 40], [30, 48], [104, 18], [56, 52], [80, 30]
          ].map(([x, y], i) => <circle key={i} className={`dust-particle ${fan ? "blown" : ""}`} cx={x} cy={y} r="2.6" style={{ animationDelay: `${i * 0.12}s` }} />)}
      </g>
      <text className="wire-label dim" x="100" y="104" textAnchor="middle">TCRT5000 反射检测：{dust ? "⚠ 积尘" : "清洁"}</text>
      {/* 风扇 */}
      <g transform="translate(196 56)">
        <circle className="fan-ring" r="16" />
        <g className={`fan-blades big ${fan ? "spinning" : ""}`}>
          <path d="M0 -13 C6 -7 6 -3 0 0 C-6 -3 -6 -7 0 -13" />
          <path d="M13 6.5 C6 9 3 6 0 0 C5 -1.5 11 1.5 13 6.5" />
          <path d="M-13 6.5 C-6 9 -3 6 0 0 C-5 -1.5 -11 1.5 -13 6.5" />
        </g>
        {fan && (
          <g className="airflow">
            <line x1="-26" y1="-8" x2="-44" y2="-14" />
            <line x1="-26" y1="0" x2="-48" y2="0" />
            <line x1="-26" y1="8" x2="-44" y2="14" />
          </g>
        )}
        <text className="wire-label" x="0" y="34" textAnchor="middle">5015 风扇 {fan ? "ON" : "OFF"}</text>
      </g>
      {/* 功率条 */}
      <g transform="translate(258 24)">
        <text className="wire-label" x="42" y="0" textAnchor="middle">INA219 实测功率</text>
        <rect className="duty-track" x="0" y="8" width="84" height="12" rx="3" />
        <rect className={`duty-fill solar ${dust ? "dimmed" : ""}`} x="0" y="8" width={84 * power} height="12" rx="3" />
        <text className="node-label" x="42" y="40" textAnchor="middle">{solarW.toFixed(2)} W</text>
        <text className="wire-label dim" x="42" y="58" textAnchor="middle">{dust ? "积尘压低发电" : fan ? "除尘后恢复" : "正常发电"}</text>
      </g>
    </svg>
  );
});
