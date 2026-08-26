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
}

// Loads the whole (small) dataset up front so the time scrub never waits on IO.
export function useFireData(): FireData | null {
  const [data, setData] = useState<FireData | null>(null);
  useEffect(() => {
    let live = true;
    (async () => {
      const index = await getJson<DataIndex>("index.json");
      const fires = await getJson<FiresSummary>("fires.json");
      if (!index || !fires) return;
      const per: Record<string, FeatureCollection> = {};
      const det: Record<string, FeatureCollection> = {};
      await Promise.all(
        index.dates.map(async (d) => {
          const [p, q] = await Promise.all([
            getJson<FeatureCollection>(`perimeters/${d}.geojson`),
            getJson<FeatureCollection>(`detections/${d}.geojson`),
          ]);
          if (p) per[d] = p;
          if (q) det[d] = q;
        })
      );
      const last = index.dates[index.dates.length - 1];
      const nifc = await getJson<FeatureCollection>(`nifc/${last}.geojson`);
      if (live) setData({ index, fires, perimeters: per, detections: det, nifc });
    })();
    return () => {
      live = false;
    };
  }, []);
  return data;
}
