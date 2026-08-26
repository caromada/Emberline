"use client";
import { useMemo } from "react";
import type { FireProps } from "@/lib/types";

interface Props {
  fire: FireProps | null;
  onClose: () => void;
}

const fmtInt = (v: number) => Math.round(v).toLocaleString("en-US");

function Sparkline({ history }: { history: { date: string; area_ha: number }[] }) {
  const spark = useMemo(() => {
    if (history.length < 2) return null;
    const w = 260;
    const h = 48;
    const max = Math.max(...history.map((p) => p.area_ha));
    const min = Math.min(...history.map((p) => p.area_ha));
    const span = max - min || 1;
    const pts = history.map((p, i) => [
      (i / (history.length - 1)) * w,
      h - 4 - ((p.area_ha - min) / span) * (h - 8),
    ]);
    return {
      d: pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" "),
      last: pts[pts.length - 1],
    };
  }, [history]);

  if (!spark) return null;
  return (
    <svg viewBox="0 0 260 48" preserveAspectRatio="none" aria-hidden="true">
      <path d={spark.d} fill="none" stroke="var(--bone)" strokeWidth="1.5" />
      <circle cx={spark.last[0]} cy={spark.last[1]} r="2.5" fill="var(--accent)" />
    </svg>
  );
}

export default function FirePanel({ fire, onClose }: Props) {
  const f = fire;
  return (
    <section className={`fire-panel${f ? " open" : ""}`} aria-hidden={!f}>
      {f && (
        <>
          <div className="head">
            <div>
              <div className="fid display">{f.fire_id}</div>
              <div className="microlabel" style={{ marginTop: 4 }}>
                observed {f.date}
              </div>
            </div>
            <button className="close" onClick={onClose} aria-label="Close panel">
              ✕
            </button>
          </div>

          <div className="headline">
            <div className="big display">
              {fmtInt(f.area_ha)}
              <small>HA</small>
            </div>
            {f.growth_24h_ha != null && (
              <div className="delta">
                {f.growth_24h_ha >= 0 ? "+" : ""}
                {fmtInt(f.growth_24h_ha)} ha in 24h
              </div>
            )}
            {f.direction && f.speed_km_day != null && (
              <div className="moving">
                moving {f.direction} at {f.speed_km_day.toFixed(1)} km/day
              </div>
            )}
          </div>

          {f.history.length > 1 && (
            <div className="sparkline-block">
              <span className="microlabel">Area · full history</span>
              <Sparkline history={f.history} />
            </div>
          )}

          <div className="meta-grid">
            <div>
              <div className="microlabel">First seen</div>
              <div className="v">{f.first_seen}</div>
            </div>
            <div>
              <div className="microlabel">Last seen</div>
              <div className="v">{f.last_seen}</div>
            </div>
            <div>
              <div className="microlabel">FRP total</div>
              <div className="v">{fmtInt(f.frp_sum)} MW</div>
            </div>
            <div>
              <div className="microlabel">Detections</div>
              <div className="v">{f.n_detections}</div>
            </div>
            <div style={{ gridColumn: "1 / -1" }}>
              <div className="microlabel">Centroid</div>
              <div className="v">
                {f.centroid[1].toFixed(4)}°N {Math.abs(f.centroid[0]).toFixed(4)}°W
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
