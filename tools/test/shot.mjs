// Headless check: land somewhere, optionally drive, take screenshots, print page errors.
// Usage (from repo root, with `python3 -m http.server 8765` running):
//   node tools/test/shot.mjs <planet> <siteId|lat,lon> [views JSON] [driveSeconds]
//   e.g. node tools/test/shot.mjs mars olympus '[[14,0.28],[3000,0.4]]' 5
// Software rendering runs at ~1 fps, so it waits several seconds per view. Use window.__moon.sim()
// for physics (fixed 1/120 s steps) instead of real-time driving.
import puppeteer from 'puppeteer';
const [planet = 'moon', where = 'a15', viewsArg = '[[11,0.28]]', drive = '0'] = process.argv.slice(2);
const views = JSON.parse(viewsArg);
const b = await puppeteer.launch({ headless: 'shell', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const p = await b.newPage(); await p.setViewport({ width: 1280, height: 760 });
p.on('pageerror', e => console.log('[pageerror]', e.message));
p.on('console', m => { if (['error', 'warning'].includes(m.type())) console.log(`[${m.type()}]`, m.text().slice(0, 300)); });
await p.goto('http://localhost:8765/index.html' + (planet === 'mars' ? '#mars' : ''));
await p.waitForFunction(() => window.__moon && window.__moon.state() === 'globe', { timeout: 180000 });
await p.evaluate(where => {
  const M = window.__moon, site = M.SITES.find(s => s.id === where);
  if (site) return M.land(site);
  const [lat, lon] = where.split(',').map(Number);
  return M.land({ name: 'Test landing', lat, lon });
}, where);
await p.waitForFunction(() => window.__moon.state() === 'surface', { timeout: 300000 });
if (+drive > 0) console.log('drive', JSON.stringify(await p.evaluate(s => window.__moon.sim(s, ['KeyW']), +drive)));
let i = 0;
for (const [dist, pitch] of views) {
  await p.evaluate((d, pi) => { window.__moon.camState.dist = d; window.__moon.camState.pitch = pi; }, dist, pitch);
  await new Promise(r => setTimeout(r, 7000));
  const f = `/tmp/shot_${planet}_${where.replace(/[^\w.-]/g, '_')}_${i++}.png`;
  await p.screenshot({ path: f }); console.log('saved', f);
}
await b.close();
