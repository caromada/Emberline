"use client";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
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

  return (
    <main className="shell">
      <div className={`map-root${mapReady && data ? " ready" : ""}`}>
        <FireMap
          perimeters={perimeters}
          detections={detections}
          nifc={data?.nifc ?? null}
          showNifc={showNifc}
          selected={selected}
          focus={focus}
          onSelect={handleSelect}
          onReady={handleReady}
        />
      </div>

      {!data && (
        <div className="boot">
          <span className="microlabel">acquiring detections…</span>
        </div>
      )}

      <header className="masthead">
        <div className="wordmark">
          EMBERLINE<span className="tick">_</span>
        </div>
        <div className="sub microlabel">live wildfire perimeter telemetry</div>
        {updated && <div className="stamp">updated {updated}</div>}
      </header>

      {firesOnDate.length > 0 && (
        <FireList fires={firesOnDate} selected={selected} onSelect={handleSelect} />
      )}

      <FirePanel fire={selectedFire} onClose={() => setSelected(null)} />

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
