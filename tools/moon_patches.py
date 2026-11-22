"""Moon: 1024x1024 gnomonic height patches (240 m) around the featured sites, plus 512x512 colour
patches (480 m) for sites with `colour: true` in index.html (Ina, Reiner Gamma).
Inputs (dl/): ldem_64_uint.tif (uint16 half-metres + 20000, 23040 x 11520), lroc_color_poles_8k.tif
  https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/ldem_64_uint.tif   (~506 MB)
Patch centres MUST equal the site lat/lon in MOON_SITES (index.html). Run from the repo root."""
import json, numpy as np, tifffile
from PIL import Image
from heightpng import enc, grid_latlon, bilinear, smooth121

R = 1737400.0
sites = json.load(open('tools/moon_sites.json'))
h = tifffile.imread('dl/ldem_64_uint.tif')
metres = lambda v: (v - 20000.0) * 0.5
for s in sites:
    LA, LO = grid_latlon(s['lat'], s['lon'], 1024, s.get('sp', 240.0), R)
    v = bilinear(h, (LO + 180) * 64 - 0.5, (90 - LA) * 64 - 0.5)
    enc(smooth121(metres(v))).save(f"patch_{s['id']}.png", optimize=True)
    print(s['id'], 'height patch')
c = tifffile.imread('dl/lroc_color_poles_8k.tif')[..., :3]
H, W = c.shape[:2]
for s in [x for x in sites if x.get('colour')]:
    LA, LO = grid_latlon(s['lat'], s['lon'], 512, s.get('csp', 480.0), R)
    v = bilinear(c, (LO + 180) / 360 * W - 0.5, (90 - LA) / 180 * H - 0.5)
    Image.fromarray(np.clip(v, 0, 255).astype(np.uint8)).save(f"cpatch_{s['id']}.jpg", quality=92)
    print(s['id'], 'colour patch')
