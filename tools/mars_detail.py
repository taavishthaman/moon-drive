import numpy as np
from PIL import Image
N = 1024
rng = np.random.default_rng(7)
def fbm(beta, seed):
    r = np.random.default_rng(seed); f = np.fft.fftfreq(N)
    k = np.sqrt(f[None, :] ** 2 + f[:, None] ** 2); k[0, 0] = 1
    spec = (r.normal(size=(N, N)) + 1j * r.normal(size=(N, N))) / k ** beta; spec[0, 0] = 0
    h = np.real(np.fft.ifft2(spec)); return h / h.std()
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
H = fbm(1.8, 1) * 1.2 + fbm(1.0, 2) * 0.15
A = 0.5 + fbm(1.3, 3) * 0.05
# wind ripples: tileable waves (integer wave numbers), warped, asymmetric profile, in patches
warp = fbm(2.0, 4) * 0.9
for (kx, ky, amp) in [(34, 13, 1.0), (61, 25, 0.35)]:
    ph = (kx * xx + ky * yy) / N + warp * (0.6 if amp > 0.5 else 0.3)
    f = ph - np.floor(ph)
    prof = np.where(f < 0.72, f / 0.72, (1 - f) / 0.28)          # gentle stoss, steep lee
    prof = prof ** 1.4
    mask = np.clip(fbm(2.2, 5 + kx) * 0.8 + 0.35, 0, 1)
    H += prof * amp * 5.0 * mask
    A += (prof - 0.5) * 0.06 * mask * amp                        # dusty crests, darker coarse troughs
# angular stones: convex polygons with flat tops and steep sides, darker basalt
for _ in range(1400):
    cx, cy = rng.uniform(0, N, 2); r = min(rng.pareto(2.4) * 2.0 + 1.5, 26)
    x0, x1 = int(cx - r - 2), int(cx + r + 3); y0, y1 = int(cy - r - 2), int(cy + r + 3)
    ix = np.arange(x0, x1) % N; iy = np.arange(y0, y1) % N
    sx, sy = np.meshgrid(np.arange(x0, x1) - cx, np.arange(y0, y1) - cy)
    k = rng.integers(4, 8); angs = np.sort(rng.uniform(0, 2 * np.pi, k)); rads = r * rng.uniform(0.6, 1.0, k)
    d = np.full(sx.shape, -1e9)
    for a, rr in zip(angs, rads): d = np.maximum(d, (sx * np.cos(a) + sy * np.sin(a)) / rr)
    top = np.clip((1 - d) * 4, 0, 1) * r * 0.5
    sub = H[np.ix_(iy, ix)]; H[np.ix_(iy, ix)] = np.maximum(sub, sub * 0.3 + top)
    A[np.ix_(iy, ix)] += np.where(d < 1, rng.uniform(-0.14, -0.04), 0)
s = 0.8
gx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) * 0.5 * s; gy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) * 0.5 * s
n = np.stack([-gx, gy, np.ones_like(H)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).save('mars/detail_n.png', optimize=True)
Image.fromarray((np.clip(A, 0, 1) * 255).astype(np.uint8)).save('mars/detail_a.png', optimize=True)
Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)[:512, :512]).save('/tmp/mdn.png')
