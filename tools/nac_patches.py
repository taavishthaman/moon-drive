"""Fine height patches from LROC NAC stereo DTMs at the Apollo sites (2 m posts at Apollo 11 and 15, 5 m at 17).
They nest inside the 240 m site patches; index.html (PLANETS.moon.finePatches) composites the finest data first
and fades out generated detail the DTM already resolves (detailAt / unresolved()).

Each patch is a rectangular gnomonic grid (nx columns, ny rows, spacing sp) with its own centre, chosen inside the
DTM's valid data and as close to the landing site as possible. Geometry as in heightpng.grid_latlon (row 0 north).

Height encoding: the usual value = metres*2 + 20000 in R (high byte) and G (low byte), plus a fraction in B:
metres = ((R*256 + G) + B/256 - 20000) / 2. Files with B = 0 decode exactly as before. Half-metre steps alone
would leave terraces on gentle slopes at 2 m spacing. B is rounded to multiples of FRAC_Q to help PNG compression.

Inputs (dl/nac/, not committed), GeoTIFF versions of the PDS products:
  https://pds.lroc.im-ldi.com/data/LRO-L-LROC-5-RDR-V1.0/LROLRC_2001/DATA/SDP/NAC_DTM/APOLLO11/NAC_DTM_APOLLO11.TIF
  .../NAC_DTM/APOLLO15/NAC_DTM_APOLLO15.TIF
  .../NAC_DTM/APOLLO17/NAC_DTM_APOLLO17.TIF
  (equirectangular, sphere R = 1737400 m, centre longitude 180, heights in metres relative to R)
Outputs: patch_<id>.png in the repo root. Prints the finePatches entries for index.html.
Run from the repo root: python3 tools/nac_patches.py [id ...]"""
import sys, numpy as np, tifffile
from PIL import Image
sys.path.insert(0, 'tools')
from heightpng import frame

R = 1737400.0
FRAC_Q = 16           # B channel step: 16/256 of 0.5 m = 3 cm
MARGIN = 60           # metres kept clear of nodata
# site lat/lon from MOON_SITES; size in metres (east, north) is the most we want, trimmed to the valid data
SITES = {
    'a11nac': dict(file='APOLLO11', site=(0.67408, 23.47297), sp=2.0, size=(4200, 6000)),
    'a15nac': dict(file='APOLLO15', site=(26.13224, 3.63400), sp=2.0, size=(4200, 6000)),
    'a17nac': dict(file='APOLLO17', site=(20.19080, 30.77168), sp=5.0, size=(12000, 12000)),
}

def load_dtm(name):
    t = tifffile.TiffFile(f'dl/nac/NAC_DTM_{name}.TIF'); p = t.pages[0]
    a = p.asarray().astype(np.float32)
    sx, sy = p.tags['ModelPixelScaleTag'].value[:2]
    tie = p.tags['ModelTiepointTag'].value
    g = t.geotiff_metadata
    lat1 = np.radians(g['ProjStdParallel1GeoKey']); lon0 = g['ProjCenterLongGeoKey']
    a[a < -1e30] = np.nan
    def to_pix(lat, lon):                     # degrees -> fractional (col, row) of pixel centres
        dl = (lon - lon0 + 540) % 360 - 180
        x = R * np.radians(dl) * np.cos(lat1); y = R * np.radians(lat)
        return (x - tie[3]) / sx - 0.5, (tie[4] - y) / sy - 0.5
    return a, to_pix

def grid_rect(lat, lon, nx, ny, sp):
    C, E, N = frame(lat, lon)
    X, Y = np.meshgrid((np.arange(nx) - (nx - 1) / 2) * sp, -(np.arange(ny) - (ny - 1) / 2) * sp)
    P = C * R + X[..., None] * E + Y[..., None] * N; P /= np.linalg.norm(P, axis=-1, keepdims=True)
    return np.degrees(np.arcsin(np.clip(P[..., 1], -1, 1))), np.degrees(np.arctan2(-P[..., 2], P[..., 0]))

def bilinear_nan(img, fx, fy):
    h, w = img.shape
    x0 = np.floor(fx).astype(int); y0 = np.floor(fy).astype(int); tx = fx - x0; ty = fy - y0
    def g(yy, xx):
        ok = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
        out = np.full(yy.shape, np.nan, np.float32); out[ok] = img[yy[ok], xx[ok]]; return out
    return (g(y0, x0) * (1 - tx) + g(y0, x0 + 1) * tx) * (1 - ty) + (g(y0 + 1, x0) * (1 - tx) + g(y0 + 1, x0 + 1) * tx) * ty

def valid_box(a, to_pix, lat, lon, sp, size, contain=True):
    """Largest box of at most `size` metres, as near (lat, lon) as possible, whose samples are all valid.
    contain=False also allows boxes that stop short of the site (when it sits right at the edge of the data).
    Works on a coarse 20 m grid in the site's tangent plane, then returns the centre and pixel counts."""
    step = 20.0; half = 40000
    n = int(2 * half / step) + 1
    LA, LO = grid_rect(lat, lon, n, n, step)
    fx, fy = to_pix(LA, LO)
    ok = ~np.isnan(bilinear_nan(a, fx, fy))
    m = int(MARGIN / step) + 1                 # shrink valid area by the margin (cheap erosion)
    for _ in range(m):
        ok = ok & np.roll(ok, 1, 0) & np.roll(ok, -1, 0) & np.roll(ok, 1, 1) & np.roll(ok, -1, 1)
    S = np.cumsum(np.cumsum(np.pad(ok, ((1, 0), (1, 0))).astype(np.int64), 0), 1)
    def full(r0, c0, hr, wc): return S[r0 + hr, c0 + wc] - S[r0, c0 + wc] - S[r0 + hr, c0] + S[r0, c0] == hr * wc
    c = n // 2
    best = None
    for frac in np.linspace(1.0, 0.3, 15):     # shrink until a box fits near the site
        wc = int(size[0] * frac / step); hr = int(size[1] * min(1.0, frac * 1.5) / step)
        wc = min(wc, int(size[0] / step)); hr = min(hr, int(size[1] / step))
        cand = []
        for dr in range(-hr // 2 - 60, hr // 2 + 61, 5):          # box centre offsets around the site
            for dc in range(-wc // 2 - 60, wc // 2 + 61, 5):
                r0 = c + dr - hr // 2; c0 = c + dc - wc // 2
                if r0 < 0 or c0 < 0 or r0 + hr >= n or c0 + wc >= n: continue
                inside = r0 + 30 <= c <= r0 + hr - 30 and c0 + 30 <= c <= c0 + wc - 30
                if contain and not inside: continue
                if full(r0, c0, hr, wc):
                    gap = max(r0 - c, 0, c - (r0 + hr)) ** 2 + max(c0 - c, 0, c - (c0 + wc)) ** 2   # site to box, in cells
                    cand.append((gap * 1e6 + dr * dr + dc * dc, r0, c0))
        if cand:
            _, r0, c0 = min(cand); best = (r0, c0, hr, wc); break
    assert best, 'no valid box around the site'
    r0, c0, hr, wc = best
    cr, cc = r0 + hr / 2, c0 + wc / 2
    ex, ny_ = (cc - (n - 1) / 2) * step, -(cr - (n - 1) / 2) * step   # box centre in metres east / north of the site
    C, E, N = frame(lat, lon)
    P = C * R + ex * E + ny_ * N; P /= np.linalg.norm(P)
    clat = float(np.degrees(np.arcsin(P[1]))); clon = float(np.degrees(np.arctan2(-P[2], P[0])))
    return clat, clon, int(wc * step / sp), int(hr * step / sp)

def enc24(metres):
    v = np.round((np.asarray(metres, np.float64) * 2 + 20000) * 256 / FRAC_Q) * FRAC_Q
    v = np.clip(v, 0, 65535 * 256 + 255).astype(np.int64)
    rgb = np.zeros(v.shape + (3,), np.uint8)
    rgb[..., 0] = v >> 16; rgb[..., 1] = (v >> 8) & 255; rgb[..., 2] = v & 255
    return Image.fromarray(rgb)

def main(ids):
    for pid in ids:
        c = SITES[pid]
        a, to_pix = load_dtm(c['file'])
        lat, lon = c['site']
        clat, clon, nx, ny = valid_box(a, to_pix, lat, lon, c['sp'], c['size'])
        LA, LO = grid_rect(clat, clon, nx, ny, c['sp'])
        fx, fy = to_pix(LA, LO)
        h = bilinear_nan(a, fx, fy)
        bad = np.isnan(h)
        if bad.any():                          # stray holes inside the box: fill from the mean of valid neighbours
            print(pid, 'filling', int(bad.sum()), 'nodata samples')
            hv = np.where(bad, np.nanmean(h), h); h = hv
        enc24(h).save(f'patch_{pid}.png', optimize=True)
        print(pid, f"{{ id: '{pid}', lat: {clat:.5f}, lon: {clon:.5f}, sp: {c['sp']:g} }}",
              f'{nx} x {ny} px = {nx * c["sp"] / 1000:.1f} x {ny * c["sp"] / 1000:.1f} km',
              'height', round(float(h.min()), 1), '..', round(float(h.max()), 1))

if __name__ == '__main__':
    main(sys.argv[1:] or list(SITES))
