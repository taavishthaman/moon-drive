import numpy as np
def grade(rgb):
    x = rgb.astype(np.float32) / 255.0
    lum = x[..., 0] * 0.45 + x[..., 1] * 0.4 + x[..., 2] * 0.15
    tint = np.array([1.0, 0.66, 0.46], np.float32)
    toned = lum[..., None] * tint * 1.45
    out = x * 0.35 + toned * 0.65
    # keep bright polar ice whitish
    ice = np.clip((lum - 0.55) / 0.25, 0, 1)[..., None]
    out = out * (1 - ice) + x * ice
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)
