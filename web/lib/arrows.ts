// The spread vector: a tapered arrow (kite polygon) in lon/lat from a fire's
// historical centroid to its current one. Physical length IS the displacement.

export function arrowPolygon(a: [number, number], b: [number, number]): [number, number][] {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const len = Math.hypot(dx, dy);
  if (len < 1e-9) return [];
  const ux = dx / len, uy = dy / len; // unit along
  const px = -uy, py = ux; // unit perpendicular
  const w = len * 0.09; // tail half-width
  const head = len * 0.32; // head length
  const hb = len - head;
  const hw = w * 2.4; // head half-width
  const pt = (t: number, s: number): [number, number] => [
    a[0] + ux * t + px * s,
    a[1] + uy * t + py * s,
  ];
  return [
    pt(0, w * 0.3),
    pt(hb, w),
    pt(hb, hw),
    [b[0], b[1]],
    pt(hb, -hw),
    pt(hb, -w),
    pt(0, -w * 0.3),
    pt(0, w * 0.3),
  ];
}

// approximate km between two lon/lat points (fine at fire scale)
export function roughKm(a: [number, number], b: [number, number]): number {
  const kmPerDegLat = 111.32;
  const kmPerDegLon = kmPerDegLat * Math.cos(((a[1] + b[1]) / 2) * (Math.PI / 180));
  return Math.hypot((b[0] - a[0]) * kmPerDegLon, (b[1] - a[1]) * kmPerDegLat);
}
