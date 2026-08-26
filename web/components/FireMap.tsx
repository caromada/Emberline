"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { GeoJsonLayer, ScatterplotLayer, SolidPolygonLayer } from "@deck.gl/layers";
import { arrowPolygon, roughKm } from "@/lib/arrows";
import { frpColor, hexToRGB, palette } from "@/lib/palette";
import type { FeatureCollection, FireProps } from "@/lib/types";

const BASEMAP =
  "https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json";

const ACCENT = hexToRGB(palette.accent);
const EMBER = hexToRGB(palette.ember);
const BONE = hexToRGB(palette.bone);

interface Props {
  perimeters: FeatureCollection | null;
  detections: FeatureCollection | null;
  nifc: FeatureCollection | null;
  showNifc: boolean;
  selected: string | null;
  focus: [number, number] | null;
  onSelect: (fireId: string | null) => void;
  onReady: () => void;
}

interface Arrow {
  fireId: string;
  polygon: [number, number][];
}

// Recolor the third-party basemap into the project palette. Dark-matter draws
// land as the background and water as fills, so: land = slate, water = space
// navy, boundaries = bone hairlines, everything else near-invisible.
function restyle(map: maplibregl.Map) {
  const style = map.getStyle();
  if (!style.layers) return;
  for (const layer of style.layers) {
    const id = layer.id;
    try {
      if (layer.type === "background") {
        map.setPaintProperty(id, "background-color", palette.slate);
      } else if (layer.type === "fill") {
        const isWater = /water|ocean/i.test(id);
        map.setPaintProperty(
          id,
          "fill-color",
          isWater ? palette.space : "#202A41"
        );
        map.setPaintProperty(id, "fill-outline-color", "rgba(0,0,0,0)");
        map.setPaintProperty(id, "fill-opacity", isWater ? 1 : 0.5);
      } else if (layer.type === "line") {
        const isBoundary = /boundary|admin/i.test(id);
        const isWater = /water|river/i.test(id);
        map.setPaintProperty(
          id,
          "line-color",
          isBoundary
            ? "rgba(242,232,201,0.15)"
            : isWater
              ? "rgba(11,16,32,0.8)"
              : "rgba(242,232,201,0.04)"
        );
      } else if (layer.type === "symbol") {
        map.setLayoutProperty(id, "visibility", "none");
      }
    } catch {
      // some layers reject individual paint props; skip them
    }
  }
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
  nifc,
  showNifc,
  selected,
  focus,
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
    map.on("style.load", () => restyle(map));
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
      showNifc && nifc
        ? new GeoJsonLayer({
            id: "nifc",
            data: nifc as unknown as GeoJSON.FeatureCollection,
            stroked: true,
            filled: true,
            getFillColor: [...BONE, 10] as [number, number, number, number],
            getLineColor: [...BONE, 110] as [number, number, number, number],
            getLineWidth: 1.4,
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
              f.properties.fire_id === selected ? 2.4 : 1.4,
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
    });
  }, [perimeters, detections, nifc, showNifc, selected, arrows, mapReady, onSelect]);

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
