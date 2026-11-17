# Moon & Mars Drive

Drive NASA's Perseverance rover (or walk as an astronaut) across the real Moon and Mars, built from NASA elevation and colour data. Open `index.html#mars` to start on Mars.

Everything here is static: no build step and no server code. Upload the whole folder to any static host.

## Run it locally

It won't work by double-clicking `index.html`, because browsers block file loading from `file://` pages. Start a tiny local server in this folder instead:

```
python3 -m http.server 8000
```

Then open http://localhost:8000.

## Host it for free

- **Netlify:** go to https://app.netlify.com/drop and drag this folder onto the page. You get a public link right away.
- **GitHub Pages:** push the folder to a repo, then go to Settings → Pages → Deploy from branch → `main` / root.
- **Vercel:** run `npx vercel` inside this folder.

The page loads three.js from cdn.jsdelivr.net, so viewers need an internet connection.

## What's in here

| File | What it is |
|---|---|
| `index.html` | The whole app (three.js) |
| `height4.png` | Global elevation, 4 px/degree (used for the orbit view) |
| `h16_*.png` | Global elevation, 16 px/degree (~1.9 km), 8 tiles loaded on demand |
| `patch_*.png` | 64 px/degree (~240 m) close-up patches around the eight featured sites |
| `cpatch_*.jpg` | Sharper colour patches from the 8K LROC mosaic (Ina, Reiner Gamma) |
| `color4k.jpg` | LROC colour map |
| `detail_n.png`, `detail_a.png` | Generated tileable regolith detail (normal and albedo maps) |
| `earth.jpg` | NASA Blue Marble Earth texture (NASA SVS) |
| `mars/` | The same set of maps for Mars: MOLA elevation (globe map, 16 px/degree tiles, 128 px/degree patches for Olympus Mons, Valles Marineris, Jezero and Gale) and Viking colour |
| `Caddyfile` | Server config for Railway/Railpack (allows the 3D model decoder) |
| `model_*.js` | Rover, lunar module and astronaut models, stored as base64 inside JS files |

The heightmaps store 16-bit values split across two channels: red is the high byte, green is the low byte. Each value is in half-metres, offset by +20000, relative to a radius of 1737.4 km.

## Credits

- Terrain: NASA / GSFC / Arizona State University, LRO LOLA & LROC, from the NASA SVS "CGI Moon Kit".
- Mars terrain: NASA/GSFC Mars Global Surveyor MOLA (USGS 463 m mosaic). Mars colour: Viking Orbiter MDIM colour mosaic (USGS), public domain.
- Earth: NASA Blue Marble, from NASA's Scientific Visualization Studio.
- Models: NASA 3D Resources (Mars 2020 Perseverance Rover, Apollo Lunar Module, Astronaut).
