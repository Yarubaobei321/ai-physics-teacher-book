import { memo } from "react";
import type { RoverTelemetry } from "../../lib/mars-rover/roverProtocol";
import { clampRange } from "../../lib/mars-rover/useRover";

export function formatTime(value: number): string {
  if (!value) {
    return "待更新";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(value);
}

/** 弧形仪表：270° 圆弧 + 发光指针，科幻 HUD 风格 */
export const ArcGauge = memo(function ArcGauge({
  label,
  unit,
  value,
  display,
  min,
  max,
  color,
  caption,
  warn = false
}: {
  label: string;
  unit: string;
  value: number;
  display: string;
  min: number;
  max: number;
  color: string;
  caption?: string;
  warn?: boolean;
}) {
  const ratio = clampRange((value - min) / (max - min), 0, 1);
  const circumference = 2 * Math.PI * 42;
  const arcLength = circumference * 0.75;

  return (
    <article className={`arc-gauge ${warn ? "warn" : ""}`}>
      <svg viewBox="0 0 100 100" role="img" aria-label={`${label} ${display}${unit}`}>
        <circle className="arc-track" cx="50" cy="50" r="42" strokeDasharray={`${arcLength} ${circumference}`} transform="rotate(135 50 50)" />
        <circle
          className="arc-value"
          cx="50"
          cy="50"
          r="42"
          stroke={color}
          strokeDasharray={`${arcLength * ratio} ${circumference}`}
          transform="rotate(135 50 50)"
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        />
        <text className="arc-display" x="50" y="48">{display}</text>
        <text className="arc-unit" x="50" y="63">{unit}</text>
      </svg>
      <strong>{label}</strong>
      {caption && <span>{caption}</span>}
    </article>
  );
});

/** 迷你趋势图 */
export const Sparkline = memo(function Sparkline({
  color,
  data,
  fallback,
  accessor,
  decimals,
  max,
  min,
  title,
  unit
}: {
  color: string;
  data: RoverTelemetry[];
  fallback: number;
  accessor: (item: RoverTelemetry) => number;
  decimals: number;
  max: number;
  min: number;
  title: string;
  unit: string;
}) {
  const values = data.length > 1 ? data.map(accessor) : [fallback, fallback];
  const points = values
    .map((v, index) => {
      const x = (index / Math.max(1, values.length - 1)) * 100;
      const normalized = clampRange((v - min) / (max - min), 0, 1);
      const y = 42 - normalized * 34;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  const latest = values[values.length - 1] ?? fallback;

  return (
    <article className="sparkline-card">
      <div>
        <strong>{title}</strong>
        <span style={{ color }}>{latest.toFixed(decimals)} {unit}</span>
      </div>
      <svg viewBox="0 0 100 48" role="img" aria-label={`${title}趋势`} preserveAspectRatio="none">
        <path className="spark-base" d="M0 42 H100" />
        <polyline points={points} style={{ stroke: color, filter: `drop-shadow(0 0 3px ${color})` }} />
      </svg>
    </article>
  );
});

/** 安全状态行 */
export const StatusRow = memo(function StatusRow({
  active,
  danger = false,
  detail,
  label
}: {
  active: boolean;
  danger?: boolean;
  detail?: string;
  label: string;
}) {
  return (
    <div className={`status-row ${active ? "active" : ""} ${danger && active ? "danger" : ""}`}>
      <span className="status-lamp" />
      <strong>{label}</strong>
      <em>{detail ?? (active ? "触发" : "正常")}</em>
    </div>
  );
});

/** 人工地平仪：横滚旋转 + 俯仰平移 */
export const AttitudeHorizon = memo(function AttitudeHorizon({ pitch, roll }: { pitch: number; roll: number }) {
  const pitchOffset = clampRange(pitch, -40, 40) * 0.9;
  const danger = Math.abs(pitch) > 25 || Math.abs(roll) > 25;

  return (
    <div className={`horizon ${danger ? "danger" : ""}`} aria-label={`姿态 俯仰${pitch.toFixed(1)}度 横滚${roll.toFixed(1)}度`}>
      <svg viewBox="0 0 120 120">
        <defs>
          <clipPath id="horizonClip">
            <circle cx="60" cy="60" r="50" />
          </clipPath>
        </defs>
        <g clipPath="url(#horizonClip)">
          <g transform={`rotate(${-roll} 60 60) translate(0 ${pitchOffset})`}>
            <rect x="-40" y="-80" width="200" height="140" className="horizon-sky" />
            <rect x="-40" y="60" width="200" height="140" className="horizon-ground" />
            <line x1="-40" y1="60" x2="160" y2="60" className="horizon-line" />
            {[-30, -20, -10, 10, 20, 30].map((deg) => (
              <g key={deg}>
                <line x1={deg % 20 === 0 ? 44 : 50} y1={60 + deg * 0.9} x2={deg % 20 === 0 ? 76 : 70} y2={60 + deg * 0.9} className="horizon-tick" />
              </g>
            ))}
          </g>
        </g>
        <circle cx="60" cy="60" r="50" className="horizon-ring" />
        {/* 固定的飞行器符号 */}
        <path d="M35 60 H50 L56 66 H64 L70 60 H85" className="horizon-marker" />
        <circle cx="60" cy="60" r="2" className="horizon-dot" />
      </svg>
      <div className="horizon-readout">
        <span>PITCH {pitch.toFixed(1)}°</span>
        <span>ROLL {roll.toFixed(1)}°</span>
      </div>
    </div>
  );
});
