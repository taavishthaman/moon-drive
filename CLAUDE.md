# Moon & Mars Drive

Drive NASA's Perseverance rover (or walk as an astronaut) on the real Moon and Mars in the browser, built from NASA elevation and colour data. Static site, no build step. Deployed on Railway (Railpack static + the `Caddyfile` here). Repo: github.com/taavishthaman/moon-drive.

Current work is listed in `TASKS.md`.

## Run and test

```bash
python3 -m http.server 8765        # from the repo root; open http://localhost:8765 (add #mars for Mars)
cd tools/test && npm i && cd ../..  # once, for headless checks
node tools/test/shot.mjs mars olympus '[[14,0.28],[3000,0.4]]' 5
```

- Headless Chrome uses software rendering (~1 fps). Judge visuals from screenshots, and judge physics with `window.__moon.sim(seconds, ['KeyW', ...])`, which steps the simulation at a fixed 1/120 s.
- Debug hooks on `window.__moon`: `land(site)`, `loadPlanet(id)`, `sim(sec, keys)`, `state()`, `SITES`, `planet`, `rover`, `astro`, `camState`, `toggleExit()`, `cycleCamera()`.
- Check after every change: no page errors, a Moon landing (`a15`) and a Mars landing (`olympus`) both render, and driving with `sim` works.

## Files

| Path | What |
|---|---|
| `index.html` | The whole app: one ES module (~1,700 lines), three.js r187 from jsDelivr via an importmap |
| `height4.png`, `h16_{ty}_{tx}.png`, `color4k.jpg`, `patch_*.png`, `cpatch_*.jpg`, `detail_{n,a}.png` | Moon data |
| `mars/…` | The same set for Mars |
| `earth.jpg` | NASA Blue Marble, for Earth in the lunar sky |
| `model_{rover,lm,astronaut}.js` | glTF models (meshopt-compressed) stored as base64 strings in JS modules. Done originally because the first host wouldn't serve `.glb`; fine to keep |
| `Caddyfile` | Replaces Railpack's default. Its CSP must allow `'wasm-unsafe-eval'` (meshopt decoder) and `blob:` in `connect-src`/`img-src` (glTF textures), or the models fail to load |
| `tools/*.py` | Data preparation. Raw downloads go in `dl/` (git-ignored). Source URLs are in each script's docstring |
| `tools/test/shot.mjs` | Headless landing + screenshot script |

## Data formats (keep these consistent between Python and JS)

- **Height PNG:** `value = round(metres * 2 + 20000)`, 16 bits, R = high byte, G = low byte. Read by `loadHeight()`. Heights are relative to the reference radius (Moon 1737.4 km) or the areoid (Mars).
- **Equirectangular maps:** lon −180..180 left to right, lat 90..−90 top to bottom.
  - `height4.png`: 1440×720.
  - `h16_*`: a 5760×2880 grid split into 4×2 tiles of 1440², loaded on demand by `ensureTile()`.
  - `color4k.jpg`: 4096×2048.
- **Gnomonic patches** around sites (`patch_<id>.png`, 1024², spacing `site.sp`, default 240 m) and colour patches (`cpatch_<id>.jpg`, 512², spacing `site.csp`, default 480 m):
  - Centred exactly on the site's lat/lon. Geometry is in `tools/heightpng.py`, matching `makeFrame()` and `baseAt()`.
  - `ensurePatchesNear()` loads any site patch within range of the landing point.
  - `baseAt()` blends a patch in over its outer 40 px.

## Architecture (index.html, top to bottom)

- **`PLANETS` / `MOON_SITES` / `MARS_SITES`:** per-planet settings (radius `R`, gravity `G`, data folder, quadtree `root`, `atmo`, crater/rock/albedo factors, HUD labels) and landing sites (`spawn` in local metres, `yaw`, `poi` target, `sp`/`csp`, `colour`, `quiet`). `loadPlanet(id)` swaps everything.
- **Height function:**
  - `surfaceAt(unit vector, step) = baseAt()` (measured data: patch, else 16 px/° tile, else 4 px/°) `+ detailAt()` (generated).
  - `detailAt()` adds value noise, `craterField()` (3D cell hashing; each crater must stay inside its own cell, or it gets sliced along cell planes), and on Mars `duneField()`.
  - Side outputs: `SRC` (data source label), `BRIGHT` (fresh crater), `DUNE` (dune coverage).
  - The `step` argument drops features smaller than the mesh spacing (LOD-aware).
- **Local frame:** a tangent plane at `FR` with x east, y up, z **south**. Heading: forward = `(sin yaw, cos yaw)`, so `yaw = π` faces north. `localToUnit()` / `unitToLocal()` convert. `recentre()` moves the frame onto the rover beyond 16 km and remaps rover, astronaut, tracks and lander.
- **Terrain mesh:** quadtree of 32×32 chunks (`selectLeaves`, `updateTerrain`, `buildChunk`).
  - Leaves down to 32 m, so 1 m vertex spacing near the focus.
  - Edges are stitched to coarser neighbours (resampled with the neighbour's `step`); the cache key includes the edge config.
  - All chunks share one index buffer. Chunks are built on the main thread with a per-frame time budget.
  - The Moon's curvature is applied in the vertex shader relative to the camera (`uCamXZ`, `uInv2R`); physics uses the flat plane.
- **Terrain material:** `MeshStandardMaterial` patched in `onBeforeCompile`:
  - CSM shadows.
  - Curvature.
  - Triplanar regolith detail at 2.5/21/170 m, single-projection fast path on flat ground.
  - Mars rock layers on steep slopes.
- **Physics:**
  - `hPhys(x, z)` reproduces the finest mesh triangulation from cached 1 m samples.
  - `stepRover()` samples four wheel points and follows the ground with a suspension threshold; it goes airborne when the ground drops away.
  - `rockCollide()` handles boulders.
  - `stepAstro()` handles the walking astronaut.
- **Rocks:** deterministic per 48 m tile (`genRockTile`). Instanced meshes with near/far LOD; Mars uses its own angular geometry and material (`setRockStyle`).
- **Rendering:**
  - Cascaded shadows (3 cascades, 2.5 km).
  - Headlight spotlights.
  - EffectComposer: MSAA HDR, bloom, grade, output.
  - Dynamic resolution (`adaptPerf`); High/Low quality (`setQuality`, key G).
  - Mars: sky dome shader plus `FogExp2` haze (`applyAtmosphere`).

## Conventions and gotchas

- Keep it a single static `index.html` + data files. No bundler.
- **Keep the stated units:** metres everywhere, degrees in site tables, radians internally.
- **Reload on data changes:** anything that changes height data must bump `terrainVersion` (chunks rebuild) and clear `PH` (physics cache).
- **Hand-tuned values:** performance work cut a frame from 6.7 M to 2.3 M triangles and 2,805 to 968 draw calls. Bounding spheres, shadow casters (`castShadow` only for chunks ≤ 1024 m) and rock LOD were all tuned for this, so re-measure if you touch them.
- **No made-up features presented as real:** generated detail must not hide or impersonate real features. Use `quiet` zones (see Ina) where a real feature is smaller than the data resolution.
- **File sizes:** largest data files are ~3 MB. Keep each new file well under GitHub's 100 MB limit (aim < 10 MB).
