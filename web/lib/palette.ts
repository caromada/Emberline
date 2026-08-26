export const palette = {
  space: "#0B1020", // deep space navy — water and page ground
  slate: "#1B2438", // landmass + panels
  bone: "#F2E8C9", // primary type
  accent: "#7FB6C9", // glacier blue — UI accent + selection (fire data owns all warm hues)
  ember: "#FE9F6D", // spread vectors
} as const;

// magma-style FRP ramp, dark -> bright
export const frpRamp: [number, string][] = [
  [0.0, "#2B0A3D"],
  [0.45, "#B63679"],
  [0.75, "#FE9F6D"],
  [1.0, "#FCFDBF"],
];

const rampRGB: [number, [number, number, number]][] = frpRamp.map(([t, hex]) => [
  t,
  [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as [number, number, number],
]);

export function frpColor(frp: number, max = 60): [number, number, number] {
  const t = Math.min(Math.max(frp / max, 0), 1);
  for (let i = 1; i < rampRGB.length; i++) {
    const [t1, c1] = rampRGB[i - 1];
    const [t2, c2] = rampRGB[i];
    if (t <= t2) {
      const u = (t - t1) / (t2 - t1 || 1);
      return c1.map((c, k) => Math.round(c + (c2[k] - c) * u)) as [number, number, number];
    }
  }
  return rampRGB[rampRGB.length - 1][1];
}

export function hexToRGB(hex: string): [number, number, number] {
  return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as [number, number, number];
}
