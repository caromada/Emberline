"use client";
import type { FireProps } from "@/lib/types";

interface Props {
  fires: FireProps[];
  names: Record<string, string>;
  selected: string | null;
  onSelect: (fireId: string | null) => void;
}

const fmtHa = (v: number) =>
  v >= 1000 ? `${(v / 1000).toFixed(1)}k` : `${Math.round(v)}`;

export default function FireList({ fires, names, selected, onSelect }: Props) {
  return (
    <aside className="fire-list">
      <header>
        <span className="microlabel">Active fires</span>
        <span className="microlabel">{fires.length}</span>
      </header>
      {fires.map((f) => (
        <button
          key={f.fire_id}
          className={`fire-row${f.fire_id === selected ? " selected" : ""}`}
          onClick={() => onSelect(f.fire_id === selected ? null : f.fire_id)}
        >
          <span className="line1">
            <span className="fid display">
              {(names[f.fire_id] ?? f.fire_id).toUpperCase()}
            </span>
            <span className="area">{fmtHa(f.area_ha)} ha</span>
          </span>
          <span className="line2">
            {f.growth_24h_ha != null && f.growth_24h_ha > 0 ? (
              <span className="growth">
                +{fmtHa(f.growth_24h_ha)} ha/24h
              </span>
            ) : (
              <span>steady</span>
            )}
            {f.direction && f.bearing_deg != null && f.speed_km_day != null &&
              f.speed_km_day >= 0.2 && (
                <span>
                  <span
                    className="dir-glyph"
                    style={{ transform: `rotate(${f.bearing_deg}deg)` }}
                    aria-hidden="true"
                  >
                    ↑
                  </span>{" "}
                  {f.direction} {f.speed_km_day.toFixed(1)} km/d
                </span>
              )}
          </span>
        </button>
      ))}
    </aside>
  );
}
