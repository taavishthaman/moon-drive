"""Moon: globe map, 16 px/deg tiles and 4K colour from the NASA CGI Moon Kit.
Inputs (dl/, not committed): ldem_16.tif (float km rel. 1737.4 km), lroc_color_poles_8k.tif
  https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/ldem_16.tif
  https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/lroc_color_poles_8k.tif
Run from the repo root: python3 tools/moon_prep.py"""
import numpy as np, tifffile
from PIL import Image
from heightpng import enc

h = tifffile.imread('dl/ldem_16.tif').astype(np.float32) * 1000.0      # metres, 5760 x 2880
for ty in range(2):
    for tx in range(4):
        enc(h[ty * 1440:(ty + 1) * 1440, tx * 1440:(tx + 1) * 1440]).save(f'h16_{ty}_{tx}.png', optimize=True)
enc(h.reshape(720, 4, 1440, 4).mean(axis=(1, 3))).save('height4.png', optimize=True)
c = tifffile.imread('dl/lroc_color_poles_8k.tif')[..., :3]
Image.fromarray(c).resize((4096, 2048), Image.LANCZOS).save('color4k.jpg', quality=85)
