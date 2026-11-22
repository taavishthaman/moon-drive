"""Polar cap patches for both poles: gnomonic height + colour patches centred on each pole, loaded by
index.html (PLANETS[*].capPatches) whenever you are poleward of ~78 deg. They replace the equirectangular
grids there, which turn into radial streaks near a pole (pixels a few metres wide in longitude but
~1.9 km (Moon) / ~3.7 km (Mars) long in latitude).

Each source row is first box-averaged in longitude over about one output pixel, so the long thin wedge
pixels near the pole are merged into an isotropic field before resampling. Right at the pole a whole row
is averaged, which also removes the swirl seen in the LOLA 64 px/deg grid there.

Inputs (dl/, not committed):
  Moon: dl/ldem_64_uint.tif (uint16 half-metres + 20000, 23040 x 11520)
          https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/ldem_64_uint.tif
        colour4k.jpg (already in the repo, the LROC colour map)
  Mars: dl/mars/mola463.tif   https://planetarymaps.usgs.gov/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif
        dl/mars/viking925.tif https://planetarymaps.usgs.gov/mosaic/Mars_Viking_ClrMosaic_global_925m.tif
Outputs: patch_ncap.png, patch_scap.png, cpatch_ncap.jpg, cpatch_scap.jpg (Moon, repo root) and the same in mars/.
Run from the repo root: python3 tools/polar_caps.py moon|mars"""
import sys, numpy as np, tifffile
from PIL import Image
sys.path.insert(0, 'tools')
from heightpng import enc, grid_latlon, bilinear, smooth121

# n / sp must match capPatches in index.html
CFG = {
    'moon': dict(R=1737400.0, out='', n=2048, sp=400.0, cn=1024, csp=1200.0),
    'mars': dict(R=3389500.0, out='mars/', n=2048, sp=640.0, cn=1024, csp=1400.0,
                 # MGS never flew poleward of ~87 deg, so MOLA there is filled by interpolation along meridians,
                 # which leaves radial streaks in the source: smooth over up to 30 deg of longitude in that zone
                 fill=(86.5, 87.5, 30.0)),
}

def lon_filter(rows, lat_of_row, R, sp_out, fill=None):
    """Box-average each row in longitude over ~sp_out metres (circular). rows: (h, w[, c]) float32.
    fill = (lat_start, lat_full, degrees): widen the box to `degrees` of longitude poleward of the source's coverage."""
    h, w = rows.shape[:2]
    out = np.empty_like(rows)
    colw = 2 * np.pi * R / w                                       # metres per column at the equator
    for i in range(h):
        la = lat_of_row(i)
        k = int(round(sp_out / max(colw * np.cos(np.radians(la)), 1e-6)))
        if fill:
            t = np.clip((abs(la) - fill[0]) / (fill[1] - fill[0]), 0, 1)
            k = max(k, int(round(t * t * (3 - 2 * t) * fill[2] / 360 * w)))
        r = rows[i]
        if k <= 1: out[i] = r; continue
        if k >= w: out[i] = r.mean(axis=0); continue
        k |= 1                                                      # odd width, centred
        pad = np.concatenate([r[-(k // 2):], r, r[:k // 2]], axis=0)
        cs = np.cumsum(np.concatenate([np.zeros((1,) + r.shape[1:], np.float64), pad.astype(np.float64)]), axis=0)
        out[i] = (cs[k:] - cs[:-k]) / k
    return out

def sample_cap(src, lat0, n, sp, R, convert=lambda a: a.astype(np.float32), fill=None):
    """Gnomonic patch of n x n at spacing sp centred on the pole lat0 (+-90), from an equirectangular src."""
    H, W = src.shape[:2]
    LA, LO = grid_latlon(lat0, 0.0, n, sp, R)
    fy_all = (90 - LA) / 180 * H - 0.5
    r0, r1 = int(np.floor(fy_all.min())) - 2, int(np.ceil(fy_all.max())) + 3
    r0, r1 = max(r0, 0), min(r1, H)
    rows = convert(np.asarray(src[r0:r1]))
    rows = lon_filter(rows, lambda i: 90 - (r0 + i + 0.5) / H * 180, R, sp, fill)
    fx = (LO + 180) / 360 * W - 0.5
    return bilinear(rows, fx, fy_all - r0), LA.min() if lat0 > 0 else LA.max()

def main(planet):
    c = CFG[planet]; R = c['R']
    if planet == 'moon':
        hsrc = tifffile.memmap('dl/ldem_64_uint.tif')
        hconv = lambda a: (a.astype(np.float32) - 20000.0) * 0.5
        col = np.asarray(Image.open('color4k.jpg').convert('RGB'))
        cconv = lambda a: a.astype(np.float32)
        grade = lambda a: a
    else:
        hsrc = tifffile.memmap('dl/mars/mola463.tif')
        hconv = lambda a: a.astype(np.float32)
        col = np.moveaxis(tifffile.memmap('dl/mars/viking925.tif'), 0, -1)        # (h, w, 3) view of planar data
        def cconv(a):                                                  # column 0 of the Viking mosaic is nodata (zeros)
            a = a.astype(np.float32); a[:, 0] = (a[:, 1] + a[:, -1]) / 2; return a
        from mars_grade import grade
    for cid, lat0 in (('ncap', 90.0), ('scap', -90.0)):
        h, edge = sample_cap(hsrc, lat0, c['n'], c['sp'], R, hconv, c.get('fill'))
        h = smooth121(h)
        enc(h).save(f"{c['out']}patch_{cid}.png", optimize=True)
        rgb, _ = sample_cap(col, lat0, c['cn'], c['csp'], R, cconv, c.get('fill'))
        Image.fromarray(grade(np.clip(rgb, 0, 255).astype(np.uint8))).save(f"{c['out']}cpatch_{cid}.jpg", quality=90)
        print(planet, cid, 'height range', float(h.min()), float(h.max()), 'patch edge lat', round(float(edge), 2))

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'moon')
