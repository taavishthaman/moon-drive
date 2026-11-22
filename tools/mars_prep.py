"""Mars: globe map, 16 px/deg tiles, 128 px/deg gnomonic patches + colour patches for the featured sites,
graded 4K colour map, and suggested spawn points (tools/mars_spawns.json, then copied by hand into MARS_SITES).
Inputs (dl/mars/, not committed):
  mola463.tif   https://planetarymaps.usgs.gov/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif   (2.1 GB, int16 metres vs areoid)
  viking925.tif https://planetarymaps.usgs.gov/mosaic/Mars_Viking_ClrMosaic_global_925m.tif     (764 MB, 3-band)
Run from the repo root: python3 tools/mars_prep.py
NOTE: the Valles Marineris spawn in index.html was picked by a separate rim search (biggest local relief
within 150 km), not by the steepest-slope rule at the bottom of this script."""
import os
import numpy as np, tifffile, json, sys
from PIL import Image
sys.path.insert(0, 'tools')
from mars_grade import grade

R = 3389500.0
OUT = 'mars/'
t = tifffile.TiffFile('dl/mars/mola463.tif'); pg = t.pages[0]
print('mola', pg.shape, pg.dtype, pg.compression, pg.is_tiled, pg.tags.get('ModelTiepointTag').value, pg.tags.get('ModelPixelScaleTag').value)
H = tifffile.memmap('dl/mars/mola463.tif') if pg.compression == 1 and not pg.is_tiled else pg.asarray()
Hh, Hw = H.shape
ppd = Hw / 360.0
print('ppd', ppd, 'min/max', int(H[::16, ::16].min()), int(H[::16, ::16].max()))

def enc(a):
    v = np.clip(np.round(a.astype(np.float32) * 2 + 20000), 0, 65535).astype(np.uint16)
    rgb = np.zeros(v.shape + (3,), np.uint8); rgb[..., 0] = v >> 8; rgb[..., 1] = v & 255
    return Image.fromarray(rgb)

# 16 px/deg global (8x8 block means), then 4 px/deg
f = int(round(ppd / 16))
h16 = np.zeros((2880, 5760), np.float32)
for r0 in range(0, 2880, 180):
    blk = np.asarray(H[r0 * f:(r0 + 180) * f, :5760 * f], dtype=np.float32)
    h16[r0:r0 + 180] = blk.reshape(180, f, 5760, f).mean(axis=(1, 3))
for ty in range(2):
    for tx in range(4):
        enc(h16[ty * 1440:(ty + 1) * 1440, tx * 1440:(tx + 1) * 1440]).save(f'{OUT}h16_{ty}_{tx}.png', optimize=True)
enc(h16.reshape(720, 4, 1440, 4).mean(axis=(1, 3))).save(OUT + 'height4.png', optimize=True)
print('tiles done')

def frame(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    C = np.array([np.cos(la) * np.cos(lo), np.sin(la), -np.cos(la) * np.sin(lo)])
    E = np.array([-np.sin(lo), 0, -np.cos(lo)]); N = np.cross(C, E)
    return C, E, N
def grid_latlon(lat, lon, n, sp):
    C, E, N = frame(lat, lon)
    xs = (np.arange(n) - (n - 1) / 2) * sp
    X, Y = np.meshgrid(xs, -xs)
    P = C * R + X[..., None] * E + Y[..., None] * N; P /= np.linalg.norm(P, axis=-1, keepdims=True)
    return np.degrees(np.arcsin(P[..., 1])), np.degrees(np.arctan2(-P[..., 2], P[..., 0]))
def local_of(lat0, lon0, lat, lon):
    C, E, N = frame(lat0, lon0)
    la, lo = np.radians(lat), np.radians(lon)
    P = np.array([np.cos(la) * np.cos(lo), np.sin(la), -np.cos(la) * np.sin(lo)])
    d = P @ C
    return float((P @ E) / d * R), float(-(P @ N) / d * R)
def bilinear(img, fx, fy, wrapx=True):
    h, w = img.shape[:2]
    x0 = np.floor(fx).astype(int); y0 = np.floor(fy).astype(int); tx = fx - x0; ty = fy - y0
    if img.ndim == 3: tx = tx[..., None]; ty = ty[..., None]
    def g(yy, xx): return np.asarray(img[np.clip(yy, 0, h - 1), np.mod(xx, w)], dtype=np.float32)
    return (g(y0, x0) * (1 - tx) + g(y0, x0 + 1) * tx) * (1 - ty) + (g(y0 + 1, x0) * (1 - tx) + g(y0 + 1, x0 + 1) * tx) * ty

if not os.path.exists('dl/mars/viking_rgb.npy'):
    v = np.moveaxis(tifffile.imread('dl/mars/viking925.tif'), 0, -1)
    np.save('dl/mars/viking_rgb.npy', v)
    Image.fromarray(grade(np.asarray(Image.fromarray(v).resize((4096, 2048), Image.LANCZOS)))).save(OUT + 'color4k.jpg', quality=88)
rgb = np.load('dl/mars/viking_rgb.npy', mmap_mode='r')
sites = {'olympus': (18.40, -133.90, 700, 1400), 'valles': (-9.80, -72.80, 400, 900), 'jezero': (18.4447, 77.4508, 300, 900), 'gale': (-4.80, 137.60, 300, 900)}
info = {}
for sid, (lat, lon, sp, csp) in sites.items():
    n = 1024
    LA, LO = grid_latlon(lat, lon, n, sp)
    fx = (LO + 180) * ppd - 0.5; fy = (90 - LA) * ppd - 0.5
    patch = bilinear(H, fx, fy)
    enc(patch).save(f'{OUT}patch_{sid}.png', optimize=True)
    LA, LO = grid_latlon(lat, lon, 512, csp)
    ch, cw = rgb.shape[:2]
    c = bilinear(rgb, (LO + 180) / 360 * cw - 0.5, (90 - LA) / 180 * ch - 0.5)
    Image.fromarray(grade(np.clip(c, 0, 255).astype(np.uint8))).save(f'{OUT}cpatch_{sid}.jpg', quality=90)
    info[sid] = {'patch': patch}
    print(sid, 'range', patch.min(), patch.max())

# ---- spawn points chosen from the data
def idx_to_local(iy, ix, sp, n=1024): return float((ix - (n - 1) / 2) * sp), float((iy - (n - 1) / 2) * sp)
out = {}
# Olympus Mons: highest rim point within 60 km of the caldera centre, facing the caldera's lowest point
p = info['olympus']['patch']; sp = 700; c = 511.5; yy, xx = np.mgrid[0:1024, 0:1024]; rr = np.hypot(yy - c, xx - c) * sp
m = np.where(rr < 60000, p, -1e9); iy, ix = np.unravel_index(m.argmax(), p.shape)
m2 = np.where(rr < 40000, p, 1e9); jy, jx = np.unravel_index(m2.argmin(), p.shape)
sx, sz = idx_to_local(iy, ix, sp); tx_, tz_ = idx_to_local(jy, jx, sp)
out['olympus'] = {'spawn': [sx, sz], 'yaw': float(np.arctan2(tx_ - sx, tz_ - sz)), 'poi': [tx_, tz_, 'Caldera floor'], 'top': float(p[iy, ix]), 'floor': float(p[jy, jx])}
# Valles Marineris: steepest drop within 60 km; spawn 1.5 km back from the edge on the high side, facing the canyon
p = info['valles']['patch']; sp = 400
gy, gx = np.gradient(p, sp); g = np.hypot(gx, gy); rr = np.hypot(yy - c, xx - c) * sp
g = np.where(rr < 60000, g, 0); iy, ix = np.unravel_index(g.argmax(), g.shape)
d = np.array([gx[iy, ix], gy[iy, ix]]); d /= np.linalg.norm(d)           # uphill direction in (x, row) space
up = np.array([ix, iy]) + d * (1500 / sp) * 3
sx, sz = idx_to_local(up[1], up[0], sp)
out['valles'] = {'spawn': [sx, sz], 'yaw': float(np.arctan2(-d[0], -d[1])), 'drop_slope': float(g.max()), 'edge_h': float(p[iy, ix])}
# Jezero: spawn at the landing site (patch centre); Gale: spawn at Curiosity's landing site, target Mount Sharp
lx, lz = local_of(-4.80, 137.60, -4.5895, 137.4417); px, pz = local_of(-4.80, 137.60, -5.08, 137.85)
out['gale'] = {'spawn': [lx, lz], 'yaw': float(np.arctan2(px - lx, pz - lz)), 'poi': [px, pz, 'Mount Sharp summit']}
dx, dz = local_of(18.4447, 77.4508, 18.51, 77.40)
out['jezero'] = {'spawn': [0, 0], 'yaw': float(np.arctan2(dx, dz)), 'poi': [dx, dz, 'Delta front']}
print(json.dumps(out, indent=1))
json.dump(out, open('tools/mars_spawns.json', 'w'))
