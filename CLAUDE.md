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
- Debug hooks on `window.__moon`: `land(site)`, `loadPlanet(id)`, `sim(sec, keys)`, `state()`, `SITES`, `planet`, `rover`, `astro`, `camState`, `toggleExit()`, `cycleCamera()`, `toggleOverlay()`, `globe`, `gCam`, `probe(x, z, step)` (data source, fine-DTM weight, generated detail and crater flag at a local point).
- Check after every change: no page errors, a Moon landing (`a15`) and a Mars landing (`olympus`) both render, and driving with `sim` works.

## Files

| Path | What |
|---|---|
| `index.html` | The whole app: one ES module (~1,700 lines), three.js r187 from jsDelivr via an importmap |
| `height4.png`, `h16_{ty}_{tx}.png`, `color4k.jpg`, `patch_*.png`, `cpatch_*.jpg`, `detail_{n,a}.png` | Moon data (`patch_a1{1,5,7}nac.png`: LROC NAC DTM patches; `patch_<site>sl.png`: SLDEM2015 60 m patches; `ra_<site>.png`: Diviner rock abundance) |
| `mars/…` | The same set for Mars |
| `earth.jpg` | NASA Blue Marble, for Earth in the lunar sky |
| `model_{rover,lm,astronaut}.js` | glTF models (meshopt-compressed) stored as base64 strings in JS modules. Done originally because the first host wouldn't serve `.glb`; fine to keep |
| `Caddyfile` | Replaces Railpack's default. Its CSP must allow `'wasm-unsafe-eval'` (meshopt decoder) and `blob:` in `connect-src`/`img-src` (glTF textures), or the models fail to load |
| `tools/*.py` | Data preparation. Raw downloads go in `dl/` (git-ignored). Source URLs are in each script's docstring |
| `tools/test/shot.mjs` | Headless landing + screenshot script |

## Data formats (keep these consistent between Python and JS)

- **Height PNG:** `value = round(metres * 2 + 20000)`, 16 bits, R = high byte, G = low byte. B is an optional fraction of a step (`metres = (R*256 + G + B/256 - 20000) / 2`); only the fine DTM patches use it, every other file has B = 0. Read by `loadHeight()`. Heights are relative to the reference radius (Moon 1737.4 km) or the areoid (Mars).
- **Equirectangular maps:** lon −180..180 left to right, lat 90..−90 top to bottom.
  - `height4.png`: 1440×720.
  - `h16_*`: a 5760×2880 grid split into 4×2 tiles of 1440², loaded on demand by `ensureTile()`.
  - `color4k.jpg`: 4096×2048.
- **Gnomonic patches** around sites (`patch_<id>.png`, 1024², spacing `site.sp`, default 240 m) and colour patches (`cpatch_<id>.jpg`, 512², spacing `site.csp`, default 480 m):
  - Centred exactly on the site's lat/lon. Geometry is in `tools/heightpng.py`, matching `makeFrame()` and `baseAt()`.
  - `ensurePatchesNear()` loads any site patch within range of the landing point, and the polar cap patches (`PL.capPatches`, ids `ncap`/`scap`, centred on ±90°) poleward of `CAP_LAT` (78°).
  - `baseAt()` composites `PATCHES` finest first (`addPatch()` keeps them sorted: fine DTMs, site patches, caps), each blended in over its outer `blend` px (default 40). Cap colour patches are drawn first so site colour paints over them.
  - **Fine DTM patches** (`PL.finePatches`): Moon: LROC NAC stereo models at Apollo 11/15 (2 m) and 17 (5 m) (`tools/nac_patches.py`), and SLDEM2015 at 60 m around the seven sites inside ±60° (`tools/sldem_patches.py`, 2048², centred on the site via `site:`). Mars: HiRISE DTMs at Jezero and Gale, resampled to 2 m (`tools/hirise_patches.py`; the Gale one stops just west of Bradbury Landing, which is at the edge of the strip). Rectangular (`n` × `m`), 24-bit heights, a `blend` band in metres (default 450), loaded within `range` (default `FINE_RANGE`, 60 km). The data tools fetch only the windows they need with HTTP range requests. Over them `detailAt()` fades out generated noise and craters larger than 2.5–4.5× the post spacing (`unresolved()`). The suppression adds up over every fine data set at the point (`FINEW`/`FINES`/`NFINE`, e.g. NAC blending into SLDEM), and ramps in over the outer third of each blend band, faster than the heights, so generated detail never sits beside the real craters. `FINE`/`FINESP` only name the dominant one (for `probe()`).
  - A site with `patchId` reuses another site's patch files (the Olympus escarpment uses `patch_olympus`).
  - Caps come from `tools/polar_caps.py`, which box-filters source rows in longitude before resampling. Mars has no MOLA tracks poleward of ~87° (`fillLat`); the HUD labels that zone as interpolated.

## Architecture (index.html, top to bottom)

- **Last position:** `saveLast()` stores the rover's (or astronaut's) spot per planet in `localStorage['moonDrive.lastPosition']` (`{ v: 1, moon: { lat, lon, bearing, site, walking, t }, mars: … }`) every 5 s on the surface, on tab hide/close and on return to orbit. The site list shows "Continue where you left off"; `resumeLast()` lands in the trip's site frame with the spawn moved to the saved spot, so the site's target and notes still apply. No backend: it lives in that browser only.
- **`PLANETS` / `MOON_SITES` / `MARS_SITES`:** per-planet settings (radius `R`, gravity `G`, data folder, quadtree `root`, `atmo`, crater/rock/albedo factors, HUD labels) and landing sites (`spawn` in local metres, `yaw`, `poi` target, `sp`/`csp`, `colour`, `quiet`). `loadPlanet(id)` swaps everything.
- **Height function:**
  - `surfaceAt(unit vector, step) = baseAt()` (measured data: patch, else 16 px/° tile, else 4 px/°) `+ detailAt()` (generated).
  - `detailAt()` adds value noise, `craterField()` (3D cell hashing; each crater must stay inside its own cell, or it gets sliced along cell planes), and on Mars `duneField()`.
  - Craters: four `CRATER_LEVELS` with a truncated power law inside each level, together a continuous cumulative N(>D) ∝ D⁻² at ~60–70% of Trask's mare equilibrium. Cells are 2 × `rmax` (the 1.8 r reach must stay within the neighbouring cell). Ages skew old (`ha^0.6`); fresh bowls are ~0.19 D deep rim to floor. Mars thins them with `craterScale`.
  - Side outputs: `SRC` (data source label), `SRCI` (numeric: 1 fine DTM, 0.75 site/cap patch, 0.5 tile, 0 fallback), `BRIGHT` (fresh crater), `DUNE` (dune coverage), `CRAT` (inside a generated crater).
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
  - On the Moon, density is scaled by the Diviner rock-abundance maps around the sites (`RAMAPS`, `rockMul()`): relative to typical mare (`RA_REF` = 0.36% rock cover), clamped to 0.15–8×. The absolute count is still tuned for performance (about 10× fewer >1 m rocks than Diviner implies), so only the pattern is real.
- **Rendering:**
  - Cascaded shadows (3 cascades, 2.5 km).
  - Headlight spotlights.
  - EffectComposer: MSAA HDR, bloom, grade, output.
  - Dynamic resolution (`adaptPerf`); High/Low quality (`setQuality`, key G).
  - Mars: sky dome shader plus `FogExp2` haze (`applyAtmosphere`). `updateAir()` scales both by the mean air density between camera and rover (11.1 km scale height, capped at the low-site level).
  - Data overlay (key O): `buildChunk()` bakes an `aOvl` attribute (source, generated slope, dune, crater); toggling only flips `uOverlay` and the rock colour.

## Conventions and gotchas

- Keep it a single static `index.html` + data files. No bundler.
- **Keep the stated units:** metres everywhere, degrees in site tables, radians internally.
- **Reload on data changes:** anything that changes height data must bump `terrainVersion` (chunks rebuild) and clear `PH` (physics cache).
- **Hand-tuned values:** performance work cut a frame from 6.7 M to 2.3 M triangles and 2,805 to 968 draw calls. Bounding spheres, shadow casters (`castShadow` only for chunks ≤ 1024 m) and rock LOD were all tuned for this, so re-measure if you touch them.
- **No made-up features presented as real:** generated detail must not hide or impersonate real features. Use `quiet` zones (see Ina) where a real feature is smaller than the data resolution.
- **File sizes:** data files are up to ~7 MB (the SLDEM and HiRISE patches; ~155 MB of data in all). Keep each new file well under GitHub's 100 MB limit (aim < 10 MB).
  - Git keeps every version of every binary, so avoid regenerating large data files casually. If the data grows much further, move it to Git LFS or cloud storage (e.g. Cloudflare R2) loaded by URL; the CSP already allows `https:` in `connect-src`/`img-src`, but the bucket needs CORS.
