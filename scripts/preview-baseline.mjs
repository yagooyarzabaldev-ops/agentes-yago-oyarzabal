// Offline, deterministic review of the approved visual template; no camera/voice needed.
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath, pathToFileURL} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const arg = (key, fallback) => args.includes(key) ? args[args.indexOf(key) + 1] : fallback;
if (args.includes('--help')) {
  console.log('node scripts/preview-baseline.mjs [--browser CHROME] [--playwright-module ABS_PACKAGE_JSON] [--output DIR] [--params JSON]');
  process.exit(0);
}
const requireFrom = process.env.PLAYWRIGHT_MODULE || arg('--playwright-module', path.join(root, 'package.json'));
let chromium;
try { ({chromium} = createRequire(path.resolve(requireFrom))('playwright-core')); }
catch { throw new Error('Falta playwright-core. Indicá un package.json de una instalación existente con --playwright-module. No se instala automáticamente.'); }
const executablePath = arg('--browser', process.env.CHROME_PATH);
const params = JSON.parse(fs.readFileSync(path.resolve(root, arg('--params', 'production/baseline-params.json')), 'utf8'));
const output = path.resolve(root, arg('--output', 'runtime/baseline-preview'));
fs.mkdirSync(output, {recursive: true});
const browser = await chromium.launch({headless: true, ...(executablePath ? {executablePath} : {})});
try {
  const page = await browser.newPage({viewport: {width: 1080, height: 1920}});
  const errors = [], issues = [];
  page.on('pageerror', error => errors.push(error.message));
  const url = pathToFileURL(path.join(root, 'content/construccion/escena_v10.html'));
  url.hash = 'p=' + encodeURIComponent(JSON.stringify(params));
  await page.goto(url.href);
  await page.waitForFunction(() => window.__mgReady, {timeout: 30000});
  const samples = [...params.captions.map(c => (c[0].start + c.at(-1).end) / 2),
    ...params.shots.flatMap(s => [s.start + .25, (s.start + s.end) / 2, s.end - .05]),
    ...params.transitions.map(tr => tr.at + tr.duration * .5)];
  for (const time of samples) {
    await page.evaluate(t => MG.seek(t), time);
    const bad = await page.evaluate(() => {
      const found = (window.__drawBoxes || []).filter(b => b.x < 60 || b.x + b.w > 965);
      const el = document.getElementById('captions');
      if (el.textContent.trim()) {
        const r = el.firstElementChild.getBoundingClientRect();
        if (r.height > 150 || r.bottom > (window.__cameraVisible ? 984 : 1566) || r.left < 60 || r.right > 945)
          found.push({text: el.textContent, reason: 'caption bounds'});
      }
      return found;
    });
    issues.push(...bad.map(issue => ({time, ...issue})));
  }
  for (const [index, shot] of params.shots.entries()) {
    await page.evaluate(t => MG.seek(t), (shot.start + shot.end) / 2);
    await page.screenshot({path: path.join(output, `${String(index).padStart(2, '0')}.png`), omitBackground: true});
  }
  const report = {ok: !errors.length && !issues.length, samples: samples.length, scenes: params.shots.length,
    errors, issues, scope: 'visual template only; camera, voice, mix and final video not reviewed'};
  fs.writeFileSync(path.join(output, 'review.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report));
  if (!report.ok) process.exitCode = 1;
} finally { await browser.close(); }
