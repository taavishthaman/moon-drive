# Tasks

Do them in this order. After each one: run the checks in CLAUDE.md, take before/after screenshots, and commit separately.

## 1. Fix polar terrain artefacts (Moon and Mars)

**Symptom:** a free landing near either pole (e.g. 89.74°N 52.83°E on the Moon) shows long radial streaks, as ridges in the ground and in the colour. Driving there is glitchy. The orbit globe shows a "starburst" around the poles. Parts of Mars show it too.

**Cause:** away from the featured sites, terrain comes from equirectangular grids (`h16_*` at 16 px/°, `height4`, `color4k`). Near a pole each pixel is a few metres wide in longitude but ~1.9 km (Moon) / ~3.7 km (Mars) long in latitude. Bicubic sampling in lat/lon space turns that into radial ridges. The South Pole *site* looks fine only because it has its own gnomonic patch (`patch_spole`).

**Fix:** polar cap patches for both poles of both planets, loaded automatically whenever you're near a pole.
- Support data-only patches that aren't landing sites, e.g. `PL.capPatches = [{ id: 'ncap', lat: 90, lon: 0, sp, csp }, …]`. Load them through the same path as site patches: `ensurePatchesNear()`, `PATCHES`/`CPATCHES`, `cosLim`, blended in `baseAt()`. Load when the landing point or rover is poleward of ~78–80°. Site patches should still win where both exist.
- Coverage from ~80° to the pole is ~300 km radius on the Moon and ~600 km on Mars. Use a larger `n` (e.g. 2048) or a coarser `sp`, and keep each file < ~10 MB.
- **Moon source:**
  - Check first whether `ldem_64_uint.tif` from the CGI Moon Kit is clean enough near the poles. The existing `patch_spole` came from it and looked fine, apart from a swirl right at the pole.
  - If not, use LOLA's polar stereographic products from the PDS Geosciences node (gridded LDEMs poleward of 75°/80°S/N). Verify product names and units before downloading.
- **Mars source:**
  - MOLA's 463 m equirectangular map may be acceptable sampled through a gnomonic patch.
  - Otherwise use the polar stereographic MEGDR products (PDS) for both caps.
  - Use the Viking colour (graded with `tools/mars_grade.py`) for colour cap patches.
- **Height function at the pole:** make sure `sample16()` and `colourAt()` don't produce NaN or seams at exactly ±90°. Also check `tilesAround()` and `recentre()` exactly at the pole.
- **Optional:** the orbit globe has the same starburst. Sample the cap patches when building the globe mesh near the poles, or blend a polar texture there.
- **Done when:** landings at 89.7°N/S on both planets show no radial streaks, driving there is smooth, and the existing South Pole site looks unchanged.

## 2. "Measured vs generated" overlay (requested by a viewer on LinkedIn)

Toggle with **O**, with a button in the right-hand panel. The goal: drive the same route with the overlay on and off, and tell which features come from NASA data and which are generated.
- **Measured data source:** tint the terrain by which source dominates `baseAt()`. For example: site/cap patch = green, 16 px/° tile = yellow, 4 px/° fallback = red.
  - Add a numeric side output next to `SRC` (e.g. `SRCI`).
  - Store it per vertex in `buildChunk()` as an extra attribute.
- **Generated contribution:** show how much height `detailAt()` adds at that spot (craters, noise, dunes) as a second channel, e.g. magenta intensity from `|detail|` normalised over ~0–10 m.
  - Also flag `DUNE > 0.3` and crater interiors distinctly.
- **Rocks:** all procedural, so tint the instanced rocks magenta while the overlay is on.
- **HUD legend:** a small legend appears while the overlay is on.
- **Performance:** attributes are baked at chunk build, so toggling should only flip a shader uniform, with no rebuild. It must not cost measurable fps when off.
- **Done when:** toggling is instant and the overlay looks sensible at `a15`, `ina` (a quiet zone: real data, no generated craters) and Mars `jezero` (dunes).

## 3. Olympus Mons is hard to see

The terrain is correct: the rover spawns on the summit caldera rim at +21.1 km. But the view is a featureless orange haze:
- The volcano is ~600 km wide with gentle slopes, so from the top it looks like a plain.
- **Main bug:** `applyAtmosphere()` uses the same haze (`FogExp2`, 1/45 km) and sky at every altitude. Mars's atmosphere has a ~11.1 km scale height, so at 21 km the air is ~15% as dense: haze should be much thinner and the sky darker.

**Fix:**
- **Altitude-dependent atmosphere:** scale fog density by `exp(-elevation / 11100)`, using the camera's elevation (local y is elevation) and updating as you move. Darken and desaturate the sky dome toward the zenith at high altitude. Check that low sites (Jezero −2.5 km, Valles floor) look about the same as now.
- **Larger zoom limit on Mars:** let the camera go higher (e.g. 60–80 km) so you can see the volcano's shape from above. The terrain quadtree covers ±524 km on Mars, which is enough.
- **New site "Olympus Mons · basal escarpment":** the cliffs at the volcano's edge (up to ~6–8 km tall, ~250–300 km from the summit) are the dramatic view from below.
  - Find a spot from the data, similar to how `tools/mars_prep.py` picks spawns: the largest relief within ~20 km, ~250–320 km from the caldera.
  - Reuse the existing 700 m `patch_olympus` (it covers ±358 km) by adding an optional `patchId` field to sites, instead of a new file.
- **Done when:** from the summit you can make out the caldera pits and a clearer horizon, and the escarpment site shows a big cliff.

## 4. Small housekeeping

- Hide repo-only files from the public site: add `hide tools CLAUDE.md TASKS.md .gitignore dl` to the `file_server` block in the `Caddyfile`.
- The Valles Marineris spawn starts on a slope partway down the canyon wall. Optionally move it back onto the flat rim, still facing the canyon.
