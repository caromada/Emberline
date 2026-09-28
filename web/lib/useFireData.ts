"use client";
import { useEffect, useState } from "react";
import type { DataIndex, FeatureCollection, FiresSummary } from "./types";

// Relative path: works at "/" in dev and under the GitHub Pages base path in
// production. Files land in public/data via scripts/sync-data.mjs (predev/prebuild).
export const dataUrl = (p: string) => `data/${p}`;

async function getJson<T>(p: string): Promise<T | null> {
  try {
    const r = await fetch(dataUrl(p));
    return r.ok ? ((await r.json()) as T) : null;
  } catch {
    return null;
  }
}

export interface FireData {
  index: DataIndex;
  fires: FiresSummary;
  perimeters: Record<string, FeatureCollection>;
  detections: Record<string, FeatureCollection>;
  nifc: FeatureCollection | null;
  names: Record<string, string>;
}

// Days of history the map exposes on the time slider.
const WINDOW_DAYS = 14;

// Loads the newest day first so the map is usable almost immediately, then
// streams the rest of the window in the background (oldest day last).
export function useFireData(): FireData | null {
  const [data, setData] = useState<FireData | null>(null);
  useEffect(() => {
    let live = true;
    (async () => {
      const [rawIndex, fires, names] = await Promise.all([
        getJson<DataIndex>("index.json"),
        getJson<FiresSummary>("fires.json"),
        getJson<Record<string, string>>("names.json"),
      ]);
      if (!rawIndex || !fires || !rawIndex.dates.length) return;
      const index = { ...rawIndex, dates: rawIndex.dates.slice(-WINDOW_DAYS) };
      const newest = index.dates[index.dates.length - 1];

      const loadDay = (d: string) =>
        Promise.all([
          getJson<FeatureCollection>(`perimeters/${d}.geojson`),
          getJson<FeatureCollection>(`detections/${d}.geojson`),
        ]);

      const [p0, q0] = await loadDay(newest);
      if (!live) return;
      setData({
        index,
        fires,
        perimeters: p0 ? { [newest]: p0 } : {},
        detections: q0 ? { [newest]: q0 } : {},
        nifc: null,
        names: names ?? {},
      });

      getJson<FeatureCollection>(`nifc/${newest}.geojson`).then((nifc) => {
        if (live && nifc) setData((prev) => (prev ? { ...prev, nifc } : prev));
      });

      for (const d of index.dates.slice(0, -1).reverse()) {
        const [p, q] = await loadDay(d);
        if (!live) return;
        setData((prev) =>
          prev
            ? {
                ...prev,
                perimeters: p ? { ...prev.perimeters, [d]: p } : prev.perimeters,
                detections: q ? { ...prev.detections, [d]: q } : prev.detections,
              }
            : prev
        );
      }
    })();
    return () => {
      live = false;
    };
  }, []);
  return data;
}
