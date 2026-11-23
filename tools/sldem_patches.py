"""SLDEM2015 (LOLA + SELENE/Kaguya Terrain Camera merge, 512 px/deg, ~59 m) patches at the Moon sites inside
+-60 deg latitude. They sit between the 240 m LOLA site patches and the LROC NAC DTMs in index.html
(PLANETS.moon.finePatches): finest data wins, and detailAt() drops generated features this data resolves.

Source: PDS Geosciences Node, uncompressed float tiles of 30 x 45 degrees (1.4 GB each):
  https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/sldem2015/tiles/float_img/
  sldem2015_512_{00n_30n|30n_60n|30s_00s|60s_30s}_{000_045|045_090|...|315_360}_float.img
  little-endian float32, km relative to 1737.4 km, row 0 = north edge, column 0 = west edge, pixel registered.
Only the rows and columns each patch needs are fetched with HTTP range requests and cached in dl/sldem/<id>.npy.

Outputs: patch_<site>sl.png (24-bit heights, see nac_patches.py), square N x N at SP metres, centred on the site.
Run from the repo root: python3 tools/sldem_patches.py [site ...]"""
import sys, os, numpy as np, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, 'tools')
from heightpng import grid_latlon
from nac_patches import enc24

URL = 'https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/sldem2015/tiles/float_img/'
PPD = 512; TW, TH = 45 * PPD, 30 * PPD
R = 1737400.0
N, SP = 2048, 60.0
SITES = {   # lat, lon from MOON_SITES
    'a11': (0.67408, 23.47297), 'a15': (26.13224, 3.63400), 'a17': (20.19080, 30.77168),
    'tycho': (-43.40, -11.30), 'copernicus': (9.70, -20.10), 'ina': (18.65, 5.30), 'reiner': (7.4, -59.0),
}

def tile_name(band, lon0):
    lat_lab = {60: '30n_60n', 30: '00n_30n', 0: '30s_00s', -30: '60s_30s'}[band]
    return f'sldem2015_512_{lat_lab}_{lon0:03d}_{lon0 + 45:03d}_float.img'

def fetch(url, start, length):
    req = urllib.request.Request(url, headers={'Range': f'bytes={start}-{start + length - 1}', 'User-Agent': 'moon-drive-data-prep'})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                b = r.read()
            if len(b) == length: return b
        except Exception as e:
            if attempt == 4: raise
    raise IOError('short read')

def read_window(r0, r1, c0, c1):
    """Global rows r0..r1-1 (row 0 = 60N) and columns c0..c1-1 (col 0 = 0E, wraps at 360) as float32 metres."""
    out = np.zeros((r1 - r0, c1 - c0), np.float32)
    jobs = []
    for r in range(r0, r1):
        band = 60 - (r // TH) * 30; tr = r % TH
        c = c0
        while c < c1:
            cw = c % (360 * PPD); t = cw // TW; tc = cw % TW
            n = min(c1 - c, TW - tc)
            jobs.append((r - r0, c - c0, URL + tile_name(band, t * 45), (tr * TW + tc) * 4, n))
            c += n
    def run(j):
        i, k, url, start, n = j
        out[i, k:k + n] = np.frombuffer(fetch(url, start, n * 4), '<f4')
    with ThreadPoolExecutor(16) as ex:
        list(ex.map(run, jobs))
    return out * 1000.0

def main(ids):
    os.makedirs('dl/sldem', exist_ok=True)
    for sid in ids:
        lat, lon = SITES[sid]
        LA, LO = grid_latlon(lat, lon, N, SP, R)
        LO360 = LO % 360
        fy = (60 - LA) * PPD - 0.5                    # global row, row 0 centred at 60 - 1/1024 deg
        # columns: unwrap around the site so the window is contiguous
        lonc = lon % 360
        dl = (LO360 - lonc + 540) % 360 - 180
        fx = (lonc + dl) * PPD - 0.5
        r0, r1 = int(np.floor(fy.min())) - 2, int(np.ceil(fy.max())) + 3
        c0, c1 = int(np.floor(fx.min())) - 2, int(np.ceil(fx.max())) + 3
        assert r0 >= 0 and r1 <= 120 * PPD, 'outside +-60 deg'
        cache = f'dl/sldem/{sid}.npy'
        if os.path.exists(cache):
            win = np.load(cache)
        else:
            print(sid, 'fetching', r1 - r0, 'x', c1 - c0, f'= {(r1 - r0) * (c1 - c0) * 4 / 1e6:.0f} MB')
            win = read_window(r0, r1, c0 % (360 * PPD), c0 % (360 * PPD) + (c1 - c0))
            np.save(cache, win)
        from heightpng import bilinear
        h = bilinear(win, fx - c0, fy - r0)
        enc24(h).save(f'patch_{sid}sl.png', optimize=True)
        print(sid, f"{{ id: '{sid}sl', lat: {lat}, lon: {lon}, sp: {SP:g} }}", 'height', round(float(h.min()), 1), '..', round(float(h.max()), 1),
              f'{os.path.getsize(f"patch_{sid}sl.png") / 1e6:.1f} MB')

if __name__ == '__main__':
    main(sys.argv[1:] or list(SITES))
