"""Diviner rock abundance around the Moon sites: where real boulders concentrate (fresh crater ejecta, rilles,
massifs) versus smooth mature regolith. index.html scales the generated boulder density with it (rockDensityAt()).

Source: LRO Diviner Global High-Resolution Mosaic of rock abundance at slope-adjusted midnight (Powell et al. 2023),
128 px/deg, 70S..70N, little-endian float32, NaN = no data, value = fraction of the surface covered by rocks
larger than ~1 m. Row 0 = 70N, column 0 = 0E. 3.3 GB, so only the windows around the sites are range-read.
  https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_ghrm/img/dghrm_ra_sam_70s70n_img.img

Output: ra_<site>.png, 512 x 512 grey, gnomonic at 240 m centred on the site (geometry as heightpng.grid_latlon),
encoded logarithmically: v = round(85 * (log10(RA) + 3)) clipped to 1..255 (RA 0.001..1), 0 = no data.
Run from the repo root: python3 tools/rock_abundance.py [site ...]"""
import sys, os, numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, 'tools')
from heightpng import grid_latlon, bilinear
from sldem_patches import fetch

URL = 'https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_ghrm/img/dghrm_ra_sam_70s70n_img.img'
PPD, W = 128, 46080
R = 1737400.0
N, SP = 512, 240.0
SITES = {   # lat, lon from MOON_SITES (the South Pole site is outside Diviner's 70S..70N mosaic)
    'a11': (0.67408, 23.47297), 'a15': (26.13224, 3.63400), 'a17': (20.19080, 30.77168),
    'tycho': (-43.40, -11.30), 'copernicus': (9.70, -20.10), 'ina': (18.65, 5.30), 'reiner': (7.4, -59.0),
}

def main(ids):
    os.makedirs('dl/diviner', exist_ok=True)
    for sid in ids:
        lat, lon = SITES[sid]
        LA, LO = grid_latlon(lat, lon, N, SP, R)
        lonc = lon % 360
        fx = (lonc + (LO % 360 - lonc + 540) % 360 - 180) * PPD - 0.5
        fy = (70 - LA) * PPD - 0.5
        r0, r1 = int(np.floor(fy.min())) - 2, int(np.ceil(fy.max())) + 3
        c0, c1 = int(np.floor(fx.min())) - 2, int(np.ceil(fx.max())) + 3
        cache = f'dl/diviner/{sid}.npy'
        if os.path.exists(cache): win = np.load(cache)
        else:
            win = np.zeros((r1 - r0, c1 - c0), np.float32)
            def run(r):
                cs = c0 % W                                     # split the row where it wraps at 360
                if cs + (c1 - c0) <= W:
                    win[r - r0] = np.frombuffer(fetch(URL, (r * W + cs) * 4, (c1 - c0) * 4), '<f4')
                else:
                    k = W - cs
                    win[r - r0, :k] = np.frombuffer(fetch(URL, (r * W + cs) * 4, k * 4), '<f4')
                    win[r - r0, k:] = np.frombuffer(fetch(URL, r * W * 4, (c1 - c0 - k) * 4), '<f4')
            with ThreadPoolExecutor(16) as ex: list(ex.map(run, range(r0, r1)))
            np.save(cache, win)
        bad = np.isnan(win)
        ra = bilinear(np.where(bad, 0, win), fx - c0, fy - r0)
        nod = bilinear(bad.astype(np.float32), fx - c0, fy - r0) > 0.5
        v = np.clip(np.round(85 * (np.log10(np.maximum(ra, 1e-4)) + 3)), 1, 255).astype(np.uint8)
        v[nod] = 0
        Image.fromarray(v).save(f'ra_{sid}.png', optimize=True)
        good = ra[~nod]
        print(sid, 'RA median', round(float(np.median(good)), 4), 'p95', round(float(np.percentile(good, 95)), 4),
              'max', round(float(good.max()), 3), 'nodata', round(float(nod.mean()), 3), f'{os.path.getsize(f"ra_{sid}.png") / 1e3:.0f} kB')

if __name__ == '__main__':
    main(sys.argv[1:] or list(SITES))
