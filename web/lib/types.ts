export interface FireProps {
  fire_id: string;
  date: string;
  area_ha: number;
  frp_sum: number;
  n_detections: number;
  first_seen: string;
  last_seen: string;
  centroid: [number, number];
  history: { date: string; area_ha: number }[];
  track: [number, number][];
  growth_24h_ha: number | null;
  speed_km_day: number | null;
  bearing_deg: number | null;
  direction: string | null;
}

export interface FeatureCollection {
  type: "FeatureCollection";
  features: {
    type: "Feature";
    geometry: GeoJSON.Geometry;
    properties: FireProps & { frp?: number };
  }[];
}

export interface DataIndex {
  dates: string[];
  updated_at: string;
}

export interface FiresSummary {
  fires: FireProps[];
  updated_at: string;
}
