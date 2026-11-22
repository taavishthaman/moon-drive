"""Pick the Olympus Mons basal escarpment site from the existing 700 m patch (mars/patch_olympus.png).
Largest relief within ~20 km, 250-320 km from the caldera. Prints a MARS_SITES entry.
Run from the repo root: python3 tools/olympus_scarp.py"""
import sys, json, numpy as np
from PIL import Image
sys.path.insert(0, 'tools')
from heightpng import grid_latlon

R, SP, N, LAT0, LON0 = 3389500.0, 700.0, 1024, 18.40, -133.90
CALDERA = (19950.0, 22050.0)            # caldera floor, local metres (x east, z south) — the summit site's poi
a = np.asarray(Image.open('mars/patch_olympus.png'), np.int32)
h = ((a[..., 0] << 8 | a[..., 1]) - 20000) * 0.5
c = (N - 1) / 2
xs = (np.arange(N) - c) * SP
X, Z = np.meshgrid(xs, xs)               # row index grows south, as does local z
def filt(img, k, f):
    out = img.copy()
    for ax in (0, 1):
        acc = out.copy()
        for s in range(1, k + 1):
            acc = f(acc, np.roll(out, s, ax)); acc = f(acc, np.roll(out, -s, ax))
        out = acc
    return out
k = int(20000 / SP)
relief = filt(h, k, np.maximum) - filt(h, k, np.minimum)
dist = np.hypot(X - CALDERA[0], Z - CALDERA[1])
edge = k + 2
ok = (dist > 250e3) & (dist < 320e3)
ok[:edge] = ok[-edge:] = False; ok[:, :edge] = ok[:, -edge:] = False
iy, ix = np.unravel_index(np.where(ok, relief, -1).argmax(), h.shape)
win = (slice(iy - k, iy + k + 1), slice(ix - k, ix + k + 1))
sub = h[win]
ty, tx = np.unravel_index(sub.argmax(), sub.shape); by, bx = np.unravel_index(sub.argmin(), sub.shape)
top = np.array([X[win][ty, tx], Z[win][ty, tx]]); foot = np.array([X[win][by, bx], Z[win][by, bx]])
# steepest point of the cliff inside that window, then walk downhill until the ground flattens out
gy, gx = np.gradient(h, SP)
slope = np.hypot(gx, gy)
sl = slope[win]; py, px = np.unravel_index(sl.argmax(), sl.shape); py += iy - k; px += ix - k
p = np.array([px, py], float)
for _ in range(400):                          # 0.5 px steps downhill
    i, j = int(round(p[1])), int(round(p[0]))
    g = np.array([gx[i, j], gy[i, j]]); n = np.linalg.norm(g)
    if n < np.tan(np.radians(5)): break
    p -= g / n * 0.5
p -= (np.array([px, py]) - p) / max(1e-6, np.linalg.norm(np.array([px, py]) - p)) * (800 / SP)    # 0.8 km out onto the apron
sx, sz = int(round(p[0])), int(round(p[1]))
spawn_xz = np.array([X[sz, sx], Z[sz, sx]])
u = np.array([px, py]) - p; u /= np.linalg.norm(u)                        # uphill, in (col, row) = (x, z)
ray = [(int(round(sz + u[1] * t)), int(round(sx + u[0] * t))) for t in range(0, int(40000 / SP))]
hi = max(ray, key=lambda q: h[q]); top = np.array([X[hi], Z[hi]])
LA, LO = grid_latlon(LAT0, LON0, N, SP, R)
lat, lon = float(LA[sz, sx]), float(LO[sz, sx])
# re-express the cliff top relative to the new site's own frame
from heightpng import frame
C, E, Nn = frame(lat, lon)
la, lo = np.radians(LA[hi]), np.radians(LO[hi])
P = np.array([np.cos(la) * np.cos(lo), np.sin(la), -np.cos(la) * np.sin(lo)]); dd = P @ C
poi = [float((P @ E) / dd * R), float(-(P @ Nn) / dd * R)]
yaw = float(np.arctan2(poi[0], poi[1]))   # forward = (sin yaw, cos yaw) in the site's frame
print(json.dumps({'relief_m': float(relief[iy, ix]), 'dist_km': float(dist[iy, ix] / 1000), 'max_slope_deg': float(np.degrees(np.arctan(slope[py, px]))),
                  'spawn_h': float(h[sz, sx]), 'top_h': float(h[hi]), 'lat': round(lat, 4), 'lon': round(lon, 4), 'yaw': round(yaw, 3),
                  'poi': [round(poi[0]), round(poi[1])], 'poi_km': float(np.hypot(*poi) / 1000)}, indent=1))
