"use client";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import FireList from "@/components/FireList";
import FirePanel from "@/components/FirePanel";
import TimeSlider from "@/components/TimeSlider";
import { useFireData } from "@/lib/useFireData";
import type { FireProps } from "@/lib/types";

const FireMap = dynamic(() => import("@/components/FireMap"), { ssr: false });

export default function Page() {
  const data = useFireData();
  const [dateIdx, setDateIdx] = useState<number | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [showNifc, setShowNifc] = useState(false);
  const [mapReady, setMapReady] = useState(false);

  const dates = data?.index.dates ?? [];
  const idx = dateIdx ?? Math.max(dates.length - 1, 0);
  const date = dates[idx];
  const names = data?.names ?? {};

  // shareable URLs: ?fire=F0165&date=2026-08-25
  const urlApplied = useRef(false);
  useEffect(() => {
    if (!data || urlApplied.current) return;
    urlApplied.current = true;
    const sp = new URLSearchParams(window.location.search);
    const d = sp.get("date");
    if (d) {
      const i = data.index.dates.indexOf(d);
      if (i >= 0) setDateIdx(i);
    }
    const f = sp.get("fire");
    if (f) setSelected(f);
  }, [data]);

  useEffect(() => {
    if (!data || !urlApplied.current) return;
    const sp = new URLSearchParams();
    if (dateIdx !== null) sp.set("date", dates[dateIdx]);
    if (selected) sp.set("fire", selected);
    const q = sp.toString();
    window.history.replaceState(null, "", q ? `?${q}` : window.location.pathname);
  }, [data, dateIdx, selected, dates]);

  // keyboard scrub
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;
      if (e.key === "ArrowLeft") setDateIdx(Math.max(idx - 1, 0));
      if (e.key === "ArrowRight") setDateIdx(Math.min(idx + 1, dates.length - 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [idx, dates.length]);

  const perimeters = date ? data?.perimeters[date] ?? null : null;
  const detections = date ? data?.detections[date] ?? null : null;

  // everything burned up to the scrubbed date, for the cumulative wash layer
  const footprint = useMemo(() => {
    if (!data || !dates.length) return null;
    return {
      type: "FeatureCollection" as const,
      features: dates
        .slice(0, idx + 1)
        .flatMap((d) => data.perimeters[d]?.features ?? []),
    };
  }, [data, dates, idx]);

  // fires visible on the scrubbed date, largest first, for the rail
  const firesOnDate: FireProps[] = useMemo(() => {
    if (!perimeters) return [];
    return perimeters.features
      .map((f) => f.properties)
      .sort((a, b) => b.area_ha - a.area_ha);
  }, [perimeters]);

  const selectedFire = useMemo(() => {
    if (!selected) return null;
    const hit = firesOnDate.find((f) => f.fire_id === selected);
    if (hit) return hit;
    // fire absent on this date: walk backwards to its most recent perimeter
    if (!data) return null;
    for (let i = idx; i >= 0; i--) {
      const day = data.perimeters[dates[i]];
      const p = day?.features.find((f) => f.properties.fire_id === selected);
      if (p) return p.properties;
    }
    return null;
  }, [selected, firesOnDate, data, dates, idx]);

  const focus = useMemo<[number, number] | null>(
    () => (selectedFire ? selectedFire.centroid : null),
    [selectedFire]
  );

  const handleSelect = useCallback((id: string | null) => setSelected(id), []);
  const handleReady = useCallback(() => setMapReady(true), []);
  const handleDate = useCallback((i: number) => setDateIdx(i), []);

  const updated = data?.index.updated_at?.replace("T", " ").replace("+00:00", "Z");

  const stats = useMemo(() => {
    if (!firesOnDate.length) return null;
    const area = firesOnDate.reduce((s, f) => s + f.area_ha, 0);
    const growth = firesOnDate.reduce(
      (s, f) => s + Math.max(f.growth_24h_ha ?? 0, 0),
      0
    );
    const fastest = firesOnDate.reduce(
      (best, f) =>
        (f.speed_km_day ?? 0) > (best?.speed_km_day ?? 0) ? f : best,
      null as FireProps | null
    );
    return {
      count: firesOnDate.length,
      area,
      growth,
      detections: detections?.features.length ?? 0,
      fastest,
    };
  }, [firesOnDate, detections]);

  return (
    <main className="shell">
      <div className={`map-root${mapReady && data ? " ready" : ""}`}>
        <FireMap
          perimeters={perimeters}
          detections={detections}
          footprint={footprint}
          nifc={data?.nifc ?? null}
          showNifc={showNifc}
          selected={selected}
          focus={focus}
          names={names}
          onSelect={handleSelect}
          onReady={handleReady}
        />
      </div>

      {!data && (
        <div className="boot">
          <span className="microlabel">acquiring detections…</span>
        </div>
      )}

      <div className="left-rail">
      <header className="masthead">
        <div className="wordmark">
          EMBERLINE<span className="tick">_</span>
        </div>
        <div className="sub microlabel">live wildfire perimeter telemetry</div>
        {updated && <div className="stamp">updated {updated}</div>}
        {stats && (
          <div className="stats-strip">
            <div>
              <span className="microlabel">fires</span>
              <span className="v">{stats.count}</span>
            </div>
            <div>
              <span className="microlabel">burning</span>
              <span className="v">{Math.round(stats.area).toLocaleString("en-US")} ha</span>
            </div>
            <div>
              <span className="microlabel">24h growth</span>
              <span className="v grow">+{Math.round(stats.growth).toLocaleString("en-US")} ha</span>
            </div>
            <div>
              <span className="microlabel">detections</span>
              <span className="v">{stats.detections}</span>
            </div>
            {stats.fastest?.speed_km_day != null && stats.fastest.speed_km_day >= 0.5 && (
              <div>
                <span className="microlabel">fastest mover</span>
                <span className="v">
                  {(names[stats.fastest.fire_id] ?? stats.fastest.fire_id).toUpperCase()} · {stats.fastest.speed_km_day.toFixed(1)} km/d {stats.fastest.direction}
                </span>
              </div>
            )}
          </div>
        )}
        <a
          className="src-chip"
          href="https://github.com/caromada/Emberline"
          target="_blank"
          rel="noreferrer"
        >
          VIIRS 375m thermal · DBSCAN + concave hulls · refreshed every 3h · source ↗
        </a>
      </header>

      {firesOnDate.length > 0 && (
        <FireList
          fires={firesOnDate}
          names={names}
          selected={selected}
          onSelect={handleSelect}
        />
      )}
      </div>

      <FirePanel
        fire={selectedFire}
        name={selectedFire ? names[selectedFire.fire_id] ?? null : null}
        onClose={() => setSelected(null)}
      />

      <div className="map-controls">
        <button
          className={`nifc-toggle${showNifc ? " on" : ""}`}
          onClick={() => setShowNifc(!showNifc)}
          aria-pressed={showNifc}
        >
          <span className="dot" />
          official perimeter · NIFC
        </button>
        <div className="legend">
          <span className="microlabel">fire radiative power</span>
          <div className="bar" />
          <div className="ends">
            <span>low</span>
            <span>high</span>
          </div>
        </div>
      </div>

      {dates.length > 0 && (
        <TimeSlider dates={dates} index={idx} onChange={handleDate} />
      )}
    </main>
  );
}
