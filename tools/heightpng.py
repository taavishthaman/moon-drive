"""Shared helpers for the data scripts.

Height PNG encoding (read by loadHeight() in index.html):
  value = round(metres * 2 + 20000), stored as 16 bits: R = high byte, G = low byte, B = 0.

Gnomonic patch geometry (must match makeFrame()/baseAt() in index.html):
  C = unit vector of the centre, E = east, N = C x E. Pixel (row, col) sits at local
  x = (col - (n-1)/2) * sp metres east and y = -(row - (n-1)/2) * sp metres north on the tangent plane,
  projected back onto the sphere. Row 0 is the north edge.

Equirectangular sources: lon -180..180 left to right, lat 90..-90 top to bottom, pixel centres at +0.5."""
import numpy as np
from PIL import Image

def enc(metres):
    v = np.clip(np.round(np.asarray(metres, np.float32) * 2 + 20000), 0, 65535).astype(np.uint16)
    rgb = np.zeros(v.shape + (3,), np.uint8); rgb[..., 0] = v >> 8; rgb[..., 1] = v & 255
    return Image.fromarray(rgb)

def frame(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    C = np.array([np.cos(la) * np.cos(lo), np.sin(la), -np.cos(la) * np.sin(lo)])
    E = np.array([-np.sin(lo), 0, -np.cos(lo)]); N = np.cross(C, E)
    return C, E, N

def grid_latlon(lat, lon, n, sp, R):
    C, E, N = frame(lat, lon)
    xs = (np.arange(n) - (n - 1) / 2) * sp
    X, Y = np.meshgrid(xs, -xs)
    P = C * R + X[..., None] * E + Y[..., None] * N; P /= np.linalg.norm(P, axis=-1, keepdims=True)
    return np.degrees(np.arcsin(np.clip(P[..., 1], -1, 1))), np.degrees(np.arctan2(-P[..., 2], P[..., 0]))

def bilinear(img, fx, fy):
    h, w = img.shape[:2]
    x0 = np.floor(fx).astype(int); y0 = np.floor(fy).astype(int); tx = fx - x0; ty = fy - y0
    if img.ndim == 3: tx = tx[..., None]; ty = ty[..., None]
    def g(yy, xx): return np.asarray(img[np.clip(yy, 0, h - 1), np.mod(xx, w)], dtype=np.float32)
    return (g(y0, x0) * (1 - tx) + g(y0, x0 + 1) * tx) * (1 - ty) + (g(y0 + 1, x0) * (1 - tx) + g(y0 + 1, x0 + 1) * tx) * ty

def smooth121(h):
    """Light [1 2 1] blur in x and y; softens LOLA ground-track streaks."""
    for ax in (0, 1): h = (np.roll(h, 1, ax) + 2 * h + np.roll(h, -1, ax)) / 4
    h[0, :] = h[1, :]; h[-1, :] = h[-2, :]; h[:, 0] = h[:, 1]; h[:, -1] = h[:, -2]
    return h
