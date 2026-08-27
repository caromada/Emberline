"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { GeoJsonLayer, ScatterplotLayer, SolidPolygonLayer } from "@deck.gl/layers";
import { arrowPolygon, roughKm } from "@/lib/arrows";
import { frpColor, hexToRGB, palette } from "@/lib/palette";
import type { FeatureCollection, FireProps } from "@/lib/types";

// Natural-earth look: satellite imagery (fits a satellite-derived product)
// with a translucent place-label layer on top. Both keyless.
const BASEMAP: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    imagery: {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      ],
      tileSize: 256,
      maxzoom: 19,
      attribution: "Imagery © Esri, Maxar, Earthstar Geographics",
    },
    labels: {
      type: "raster",
      tiles: [
        "https://basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}@2x.png",
      ],
      tileSize: 256,
      attribution: "Labels © CARTO © OpenStreetMap contributors",
    },
  },
  layers: [
    { id: "imagery", type: "raster", source: "imagery" },
    { id: "labels", type: "raster", source: "labels", paint: { "raster-opacity": 0.92 } },
  ],
};

const ACCENT = hexToRGB(palette.accent);
const EMBER = hexToRGB(palette.ember);
const BONE = hexToRGB(palette.bone);

interface Props {
  perimeters: FeatureCollection | null;
  detections: FeatureCollection | null;
  footprint: FeatureCollection | null; // all perimeters up to the scrubbed date
  nifc: FeatureCollection | null;
  showNifc: boolean;
  selected: string | null;
  focus: [number, number] | null;
  names: Record<string, string>;
  onSelect: (fireId: string | null) => void;
  onReady: () => void;
}

interface Arrow {
  fireId: string;
  polygon: [number, number][];
}

function dataBounds(fc: FeatureCollection): [[number, number], [number, number]] | null {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  const eat = (c: unknown) => {
    if (typeof (c as number[])[0] === "number") {
      const [x, y] = c as [number, number];
      minX = Math.min(minX, x); maxX = Math.max(maxX, x);
      minY = Math.min(minY, y); maxY = Math.max(maxY, y);
    } else {
      for (const child of c as unknown[]) eat(child);
    }
  };
  for (const f of fc.features) {
    eat((f.geometry as { coordinates: unknown }).coordinates);
  }
  return minX === Infinity ? null : [[minX, minY], [maxX, maxY]];
}

export default function FireMap({
  perimeters,
  detections,
  footprint,
  nifc,
  showNifc,
  selected,
  focus,
  names,
  onSelect,
  onReady,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const fitted = useRef(false);

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASEMAP,
      center: [-121.6, 40.2],
      zoom: 6.4,
      attributionControl: { compact: true },
    });
    map.on("error", (e) => console.error("maplibre:", e.error?.message ?? e));
    map.on("load", () => {
      setMapReady(true);
      onReady();
    });
    if (process.env.NODE_ENV !== "production") {
      (window as unknown as { __map?: maplibregl.Map }).__map = map;
    }
    const overlay = new MapboxOverlay({ layers: [] });
    map.addControl(overlay);
    overlayRef.current = overlay;
    mapRef.current = map;
    // container size can settle a beat after mount, leaving the render loop
    // parked before the first tiles are ever requested — nudge until loaded
    const kick = window.setInterval(() => {
      if (map.loaded()) {
        window.clearInterval(kick);
        return;
      }
      map.resize();
      map.triggerRepaint();
    }, 700);
    return () => {
      window.clearInterval(kick);
      overlayRef.current = null;
      mapRef.current = null;
      map.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const arrows: Arrow[] = useMemo(() => {
    if (!perimeters) return [];
    const out: Arrow[] = [];
    for (const f of perimeters.features) {
      const track = f.properties.track;
      if (!track || track.length < 2) continue;
      const a = track[0];
      const b = track[track.length - 1];
      if (roughKm(a, b) < 0.6) continue; // no jitter arrows
      const poly = arrowPolygon(a, b);
      if (poly.length) out.push({ fireId: f.properties.fire_id, polygon: poly });
    }
    return out;
  }, [perimeters]);

  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay || !mapReady) return;

    const layers = [
      // cumulative burned footprint: everything up to the scrubbed date as a
      // dim wash under the bright active front, so scrubbing shows the burn
      // growing outward instead of blobs jumping around
      footprint
        ? new GeoJsonLayer({
            id: "footprint",
            data: footprint as unknown as GeoJSON.FeatureCollection,
            stroked: false,
            filled: true,
            getFillColor: [254, 159, 109, 26] as [number, number, number, number],
          })
        : null,
      showNifc && nifc
        ? new GeoJsonLayer({
            id: "nifc",
            data: nifc as unknown as GeoJSON.FeatureCollection,
            stroked: true,
            filled: true,
            getFillColor: [...BONE, 22] as [number, number, number, number],
            getLineColor: [255, 255, 255, 170] as [number, number, number, number],
            getLineWidth: 1.6,
            lineWidthUnits: "pixels" as const,
            transitions: { getLineColor: 240, getFillColor: 240 },
          })
        : null,
      perimeters
        ? new GeoJsonLayer({
            id: "perimeters",
            data: perimeters as unknown as GeoJSON.FeatureCollection,
            stroked: true,
            filled: true,
            pickable: true,
            getFillColor: (f: { properties: FireProps }) => {
              const [r, g, b] = frpColor(
                f.properties.frp_sum / Math.max(f.properties.n_detections, 1),
                30
              );
              return [r, g, b, 82] as [number, number, number, number];
            },
            getLineColor: (f: { properties: FireProps }) =>
              f.properties.fire_id === selected
                ? ([...ACCENT, 255] as [number, number, number, number])
                : ([
                    ...frpColor(
                      f.properties.frp_sum / Math.max(f.properties.n_detections, 1),
                      30
                    ),
                    210,
                  ] as [number, number, number, number]),
            getLineWidth: (f: { properties: FireProps }) =>
              f.properties.fire_id === selected ? 2.8 : 1.8,
            lineWidthUnits: "pixels" as const,
            onClick: (info: { object?: { properties: FireProps } }) => {
              onSelect(info.object ? info.object.properties.fire_id : null);
            },
            updateTriggers: { getLineColor: [selected], getLineWidth: [selected] },
            transitions: { getFillColor: 240, getLineColor: 240 },
          })
        : null,
      detections
        ? new ScatterplotLayer({
            id: "detections",
            data: detections.features,
            getPosition: (f: { geometry: { coordinates: [number, number] } }) =>
              f.geometry.coordinates,
            getFillColor: (f: { properties: { frp?: number } }) =>
              [...frpColor(f.properties.frp ?? 1), 200] as [number, number, number, number],
            getRadius: (f: { properties: { frp?: number } }) =>
              120 + Math.sqrt(f.properties.frp ?? 1) * 60,
            radiusUnits: "meters" as const,
            radiusMinPixels: 1.2,
            radiusMaxPixels: 6,
            transitions: { getFillColor: 240 },
          })
        : null,
      arrows.length
        ? new SolidPolygonLayer({
            id: "spread-arrows",
            data: arrows,
            getPolygon: (a: Arrow) => a.polygon,
            getFillColor: [...EMBER, 235] as [number, number, number, number],
            transitions: {
              getPolygon: { duration: 320, easing: (t: number) => 1 - (1 - t) ** 3 },
            },
          })
        : null,
    ].filter(Boolean);

    overlay.setProps({
      layers,
      getCursor: ({ isHovering }: { isHovering: boolean }) =>
        isHovering ? "pointer" : "grab",
      getTooltip: ({ object }: { object?: { properties: FireProps } }) => {
        const p = object?.properties;
        if (!p?.fire_id) return null;
        const title = names[p.fire_id]
          ? `${names[p.fire_id].toUpperCase()} <span style="opacity:.55">${p.fire_id}</span>`
          : p.fire_id;
        const rows = [
          `<div style="font-weight:700;font-size:13px;letter-spacing:.06em">${title}</div>`,
          `<div>${Math.round(p.area_ha).toLocaleString("en-US")} ha</div>`,
          p.growth_24h_ha != null
            ? `<div style="color:#FE9F6D">${p.growth_24h_ha >= 0 ? "+" : ""}${Math.round(p.growth_24h_ha).toLocaleString("en-US")} ha / 24h</div>`
            : "",
          p.direction && p.speed_km_day != null
            ? `<div>moving ${p.direction} at ${p.speed_km_day.toFixed(1)} km/day</div>`
            : "",
        ].join("");
        return {
          html: rows,
          style: {
            backgroundColor: "rgba(13,18,30,0.95)",
            color: "#F2E8C9",
            border: "1px solid rgba(242,232,201,0.25)",
            padding: "9px 12px",
            fontFamily: "ui-monospace, SFMono-Regular, monospace",
            fontSize: "11.5px",
            lineHeight: "1.55",
          },
        };
      },
    } as Parameters<MapboxOverlay["setProps"]>[0]);
  }, [perimeters, detections, footprint, nifc, showNifc, selected, arrows, mapReady, names, onSelect]);

  // fly to the selected fire
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !focus) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    map.flyTo({
      center: focus,
      zoom: Math.max(map.getZoom(), 8.6),
      duration: reduced ? 0 : 900,
      essential: true,
    });
  }, [focus]);

  // one-time fit to the data extent
  useEffect(() => {
    if (fitted.current || !mapReady || !perimeters?.features.length) return;
    const bounds = dataBounds(perimeters);
    if (!bounds) return;
    fitted.current = true;
    mapRef.current?.fitBounds(bounds, { padding: 90, maxZoom: 9.4, duration: 0 });
  }, [mapReady, perimeters]);

  return <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />;
}
