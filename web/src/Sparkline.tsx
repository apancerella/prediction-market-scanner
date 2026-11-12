import { useState } from "react";
import { cents, etTime } from "./format";

/** Price of the pick across recent scans: one series, so no legend; hover shows the point. */
export function Sparkline({ samples }: { samples: [string, number][] }) {
  const [hover, setHover] = useState<number | null>(null);
  if (samples.length < 2) return <div className="spark-empty">Price history builds up with each scan</div>;
  const W = 240, H = 44, P = 4;
  const prices = samples.map((s) => s[1]);
  const lo = Math.min(...prices), hi = Math.max(...prices);
  const span = hi - lo || 0.01;
  const x = (i: number) => P + (i / (samples.length - 1)) * (W - 2 * P);
  const y = (p: number) => H - P - ((p - lo) / span) * (H - 2 * P);
  const d = samples.map((s, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(s[1]).toFixed(1)}`).join("");
  const h = hover ?? samples.length - 1;
  return (
    <div className="spark">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Price moved from ${cents(prices[0])} to ${cents(prices[prices.length - 1])} over ${samples.length} scans`}
        onMouseLeave={() => setHover(null)}
        onMouseMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          const i = Math.round(((e.clientX - r.left) / r.width) * (samples.length - 1));
          setHover(Math.max(0, Math.min(samples.length - 1, i)));
        }}
      >
        <path d={d} className="spark-line" />
        <line x1={x(h)} x2={x(h)} y1={P} y2={H - P} className="spark-cross" />
        <circle cx={x(h)} cy={y(samples[h][1])} r={4} className="spark-dot" />
      </svg>
      <div className="spark-label">
        {cents(samples[h][1])} <span className="muted">· {etTime(samples[h][0])}</span>
      </div>
    </div>
  );
}
