"""Fine height patches from HiRISE stereo DTMs (1 m posts) at the Mars rover sites, resampled to 2 m and nested
inside the MOLA site patches exactly like the LROC NAC patches on the Moon (PLANETS.mars.finePatches).
Heights are metres above the Mars 2000 areoid, the same datum as the MOLA data.

Sources (dl/hirise/, not committed):
  Jezero: USGS Mars 2020 TRN HiRISE DTM mosaic (21400 x 21488, 1 m, uncompressed GeoTIFF, 1.8 GB). Only the window
    around the landing site and the delta front is fetched, with HTTP range requests, and cached as jezero.npy.
    https://planetarymaps.usgs.gov/mosaic/mars2020_trn/HiRISE/JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40.tif
  Gale: HiRISE PDS DTM of the MSL landing ellipse around Bradbury Landing (7075 x 15040, 1 m, PDS IMG, 426 MB)
    https://hirise-pds.lpl.arizona.edu/PDS/DTM/ESP/ORB_018800_018899/ESP_018854_1755_ESP_018920_1755/DTEEC_018854_1755_018920_1755_U01.IMG
Both are equirectangular on a 3396.19 km sphere; only their lat/lon grid is used here.
Outputs: mars/patch_<id>.png (24-bit heights, see nac_patches.py). Prints the finePatches entries.
Run from the repo root: python3 tools/hirise_patches.py [jezhr galehr]"""
import sys, os, numpy as np, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, 'tools')
import nac_patches as nac
from heightpng import frame

R = 3389500.0
nac.R = R                    # patch geometry on the app's Mars sphere
JEZ_URL = 'https://planetarymaps.usgs.gov/mosaic/mars2020_trn/HiRISE/JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40.tif'
JEZ = dict(W=21400, H=21488, off=172609, x0=4577366.0, y0=1106618.0, Rp=3396190.0)   # from the GeoTIFF header

def local_ll(lat, lon, east, north):
    C, E, N = frame(lat, lon)
    P = C * R + east * E + north * N; P /= np.linalg.norm(P)
    return float(np.degrees(np.arcsin(P[1]))), float(np.degrees(np.arctan2(-P[2], P[0])))

def fetch(url, start, length):
    req = urllib.request.Request(url, headers={'Range': f'bytes={start}-{start + length - 1}', 'User-Agent': 'moon-drive-data-prep'})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                b = r.read()
            if len(b) == length: return b
        except Exception:
            if attempt == 4: raise
    raise IOError('short read')

def jezero_source(clat, clon, half):
    """Window of +-half metres around (clat, clon), as (array, to_pix)."""
    J = JEZ; k = np.pi / 180 * J['Rp']
    def col(lon): return (lon * k - J['x0']) - 0.5
    def row(lat): return (J['y0'] - lat * k) - 0.5
    la0, lo0 = local_ll(clat, clon, -half, half); la1, lo1 = local_ll(clat, clon, half, -half)
    r0, r1 = int(row(la0)) - 4, int(row(la1)) + 5
    c0, c1 = int(col(lo0)) - 4, int(col(lo1)) + 5
    cache = 'dl/hirise/jezero.npy'
    if os.path.exists(cache) and os.path.exists(cache + '.win') and open(cache + '.win').read() == f'{r0} {r1} {c0} {c1}':
        a = np.load(cache)
    else:
        print('jezero: fetching', r1 - r0, 'rows x', c1 - c0, f'cols = {(r1 - r0) * (c1 - c0) * 4 / 1e6:.0f} MB')
        a = np.zeros((r1 - r0, c1 - c0), np.float32)
        def run(r):
            a[r - r0] = np.frombuffer(fetch(JEZ_URL, J['off'] + (r * J['W'] + c0) * 4, (c1 - c0) * 4), '<f4')
        with ThreadPoolExecutor(16) as ex: list(ex.map(run, range(r0, r1)))
        np.save(cache, a); open(cache + '.win', 'w').write(f'{r0} {r1} {c0} {c1}')
    a[a < -1e30] = np.nan
    return a, lambda lat, lon: (col(lon) - c0, row(lat) - r0)

def gale_source():
    W, H, rec = 7075, 15040, 28300
    raw = np.fromfile('dl/hirise/DTEEC_018854_1755_018920_1755_U01.IMG', np.uint8)
    a = raw[rec:rec + W * H * 4].view('<f4').reshape(H, W).astype(np.float32)
    a[a < -1e30] = np.nan
    res, LPO, SPO, lon0 = 58585.55467457, -261165.50000001, 3738.5, 137.4      # PDS label (pixel centres at integer + 0)
    return a, lambda lat, lon: ((lon - lon0) * res + SPO - 0.5, LPO - lat * res - 0.5)

def main(ids):
    os.makedirs('dl/hirise', exist_ok=True)
    jobs = {
        # Jezero: between the landing site (18.4447 N, 77.4508 E) and the delta front poi (2.85 km W, 3.86 km N)
        'jezhr': lambda: (local_ll(18.4447, 77.4508, -1425, 1930), (6000, 6500)),
        # Gale: Bradbury Landing, the app's spawn point
        'galehr': lambda: ((-4.5895, 137.4417), (4600, 7000)),   # the landing point is right at the strip's east edge
    }
    for pid in ids:
        (lat, lon), size = jobs[pid]()
        a, to_pix = jezero_source(lat, lon, 3800) if pid == 'jezhr' else gale_source()
        clat, clon, nx, ny = nac.valid_box(a, to_pix, lat, lon, 2.0, size, contain=pid != 'galehr')
        LA, LO = nac.grid_rect(clat, clon, nx, ny, 2.0)
        fx, fy = to_pix(LA, LO)
        h = nac.bilinear_nan(a, fx, fy)
        bad = np.isnan(h)
        if bad.any():
            print(pid, 'filling', int(bad.sum()), 'nodata samples'); h = np.where(bad, np.nanmean(h), h)
        nac.enc24(h).save(f'mars/patch_{pid}.png', optimize=True)
        print(pid, f"{{ id: '{pid}', lat: {clat:.5f}, lon: {clon:.5f}, sp: 2 }}", f'{nx} x {ny} px = {nx * 2 / 1000:.1f} x {ny * 2 / 1000:.1f} km',
              'height', round(float(h.min()), 1), '..', round(float(h.max()), 1), f'{os.path.getsize(f"mars/patch_{pid}.png") / 1e6:.1f} MB')

if __name__ == '__main__':
    main(sys.argv[1:] or ['jezhr', 'galehr'])
