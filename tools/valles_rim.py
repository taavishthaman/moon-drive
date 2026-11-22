"""Pick a Valles Marineris spawn on flat rim ground (< 3 deg) near the old spawn, facing the biggest drop within 12 km.
Reads the existing mars/patch_valles.png. Run from the repo root: python3 tools/valles_rim.py"""
import json, numpy as np
from PIL import Image
SP, C = 400.0, 511.5
OLD = np.array([12434.0, -111234.0])          # previous spawn (on a spur partway down the wall)
a = np.asarray(Image.open('mars/patch_valles.png'), np.int32); h = ((a[..., 0] << 8 | a[..., 1]) - 20000) * 0.5
gy, gx = np.gradient(h, SP); slope = np.degrees(np.arctan(np.hypot(gx, gy)))
flat = slope.copy()
for dy in (-1, 0, 1):
    for dx in (-1, 0, 1): flat = np.maximum(flat, np.roll(np.roll(slope, dy, 0), dx, 1))   # flat over ~1.2 km
oi, oj = int(round(OLD[1] / SP + C)), int(round(OLD[0] / SP + C))
best = None
angs = np.linspace(0, 2 * np.pi, 32, endpoint=False)
for i in range(oi - 60, oi + 61):
    for j in range(oj - 60, oj + 61):
        if flat[i, j] > 3: continue
        for a_ in angs:
            dx, dz = np.sin(a_), np.cos(a_)                         # x east, z south (row grows south)
            ts = np.arange(1, 31)                                    # up to 12 km
            ii = np.clip((i + dz * ts).round().astype(int), 0, 1023); jj = np.clip((j + dx * ts).round().astype(int), 0, 1023)
            if h[ii[:3], jj[:3]].min() < h[i, j] - 150: continue    # keep ~1 km of rim in front of the rover
            drop = h[i, j] - h[ii, jj].min()
            if best is None or drop > best[0]: best = (drop, i, j, a_)
drop, i, j, yaw = best
x, z = (j - C) * SP, (i - C) * SP
print(json.dumps({'spawn': [round(x), round(z)], 'yaw': round(float(yaw), 3), 'h': float(h[i, j]), 'slope_deg': float(flat[i, j]),
                  'drop_12km_m': float(drop), 'moved_km': float(np.hypot(x - OLD[0], z - OLD[1]) / 1000)}, indent=1))
