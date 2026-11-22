import numpy as np
from PIL import Image
rng = np.random.default_rng(42)
N = 1024
def fbm(beta, seed):
    r = np.random.default_rng(seed)
    f = np.fft.fftfreq(N)
    k = np.sqrt(f[None,:]**2 + f[:,None]**2); k[0,0] = 1
    spec = (r.normal(size=(N,N)) + 1j*r.normal(size=(N,N))) / k**beta
    spec[0,0] = 0
    h = np.real(np.fft.ifft2(spec)); return h / h.std()
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
H = fbm(1.6, 1) * 1.5 + fbm(1.0, 2) * 0.25          # soft regolith undulation + grain
A = 0.5 + fbm(1.2, 3) * 0.05
def wrapd(cx, cy):
    dx = (xx - cx + N/2) % N - N/2; dy = (yy - cy + N/2) % N - N/2; return dx, dy
# micro craters (rim + bowl)
for _ in range(90):
    cx, cy = rng.uniform(0, N, 2); r = rng.pareto(1.6) * 8 + 6; r = min(r, 120)
    x0, x1 = int(cx - 2*r), int(cx + 2*r); y0, y1 = int(cy - 2*r), int(cy + 2*r)
    ix = np.arange(x0, x1) % N; iy = np.arange(y0, y1) % N
    sx, sy = np.meshgrid(np.arange(x0, x1) - cx, np.arange(y0, y1) - cy)
    t = np.sqrt(sx**2 + sy**2) / r
    d = np.where(t < 1, -(1 - t**2) + 0.25 * t**4, 0.25 * np.clip(1 - (t - 1) / 0.8, 0, 1)**2) * r * 0.18
    H[np.ix_(iy, ix)] += d
    A[np.ix_(iy, ix)] += np.where(t < 1.6, 0.03 * rng.uniform(-1, 1), 0)
# pebbles and small stones (domes)
for _ in range(3200):
    cx, cy = rng.uniform(0, N, 2); r = rng.pareto(2.6) * 1.3 + 1.0; r = min(r, 16)
    x0, x1 = int(cx - r - 1), int(cx + r + 2); y0, y1 = int(cy - r - 1), int(cy + r + 2)
    ix = np.arange(x0, x1) % N; iy = np.arange(y0, y1) % N
    sx, sy = np.meshgrid(np.arange(x0, x1) - cx, np.arange(y0, y1) - cy)
    sx = sx / rng.uniform(0.7, 1.3)
    th = np.arctan2(sy, sx); a1, a2 = rng.uniform(0, 6.28, 2)
    rr = r * (1 + 0.13*np.sin(3*th + a1) + 0.1*np.sin(5*th + a2) + 0.06*np.sin(7*th + a1*2))
    t2 = (sx**2 + sy**2) / (rr*rr)
    dome = np.clip(1 - t2, 0, 1)**0.6 * r * 0.38
    sub = H[np.ix_(iy, ix)]; H[np.ix_(iy, ix)] = np.maximum(sub, sub + dome * 0 + dome)
    A[np.ix_(iy, ix)] += np.where(t2 < 1, rng.uniform(0.04, 0.14), 0)
# normals (texel = 1 unit; height scale chosen for a nice relief)
s = 0.9
gx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) * 0.5 * s
gy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) * 0.5 * s
n = np.stack([-gx, gy, np.ones_like(H)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).save('detail_n.png', optimize=True)
A = np.clip(A, 0, 1)
Image.fromarray((A * 255).astype(np.uint8)).save('detail_a.png', optimize=True)

