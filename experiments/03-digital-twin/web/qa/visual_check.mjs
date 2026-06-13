// Automated visual QA for the go1-walk closed-loop demo — so Claude can verify the robot
// without a human eyeballing the live site every time.
//
// Why this exists: runPolicyLoop() paces with setTimeout(~20ms) which headless chromium
// throttles to ~1Hz, so the robot doesn't visibly walk in an automated capture. Instead we
// drive window.demo.qaStep(n) (added in src/main.js), which steps the policy+sim synchronously
// and renders one frame — deterministic, throttle-immune. We screenshot at intervals and read
// back diagnostics (height / x-progress / NaN) to assert the robot is intact and walking.
//
// Usage:
//   node qa/visual_check.mjs                 # local: spawns serve_coi.py, tests the working tree
//   node qa/visual_check.mjs --live          # tests https://physical-ai-arm.askewly.com
//   node qa/visual_check.mjs --exp=go1-walk --steps=400 --chunk=50
//
// Screenshots land in qa/out/*.png. Exit code 0 = pass (intact + walking + 0 console errors).

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const QA_DIR  = dirname(fileURLToPath(import.meta.url));
const WEB_DIR = dirname(QA_DIR);
const OUT_DIR = join(QA_DIR, 'out');

const args   = process.argv.slice(2);
const live   = args.includes('--live');
const exp    = (args.find(a => a.startsWith('--exp='))   || '--exp=go1-walk').split('=')[1];
const steps  = parseInt((args.find(a => a.startsWith('--steps=')) || '--steps=400').split('=')[1], 10);
const chunk  = parseInt((args.find(a => a.startsWith('--chunk=')) || '--chunk=50').split('=')[1], 10);
const PORT   = 8132;
const BASE   = live ? 'https://physical-ai-arm.askewly.com' : `http://127.0.0.1:${PORT}`;
const URL    = `${BASE}/?exp=${exp}`;

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function waitForServer(url, tries = 50) {
  for (let i = 0; i < tries; i++) {
    try { const r = await fetch(url); if (r.ok) return; } catch {}
    await sleep(200);
  }
  throw new Error(`server not up at ${url}`);
}

let serverProc = null;
async function main() {
  mkdirSync(OUT_DIR, { recursive: true });

  if (!live) {
    serverProc = spawn('python', ['serve_coi.py', String(PORT)], { cwd: WEB_DIR, stdio: 'ignore' });
    await waitForServer(`${BASE}/index.html`);
  }

  const browser = await chromium.launch({
    headless: true,
    args: ['--disable-background-timer-throttling',
           '--disable-renderer-backgrounding',
           '--disable-backgrounding-occluded-windows',
           '--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'],
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 960 } });

  const consoleErrors = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => consoleErrors.push(String(e)));

  console.log(`[qa] navigate ${URL}`);
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 120000 });

  // Wait for the live policy session (onnx + mujoco wasm loaded from CDN — can be slow).
  await page.waitForFunction(() => window.demo && window.demo.session, null,
    { timeout: 120000, polling: 500 });
  console.log('[qa] policy session ready');

  // Baseline (home pose, before stepping).
  await page.screenshot({ path: join(OUT_DIR, `${exp}_000.png`) });

  let diag = null;
  for (let done = 0; done < steps; done += chunk) {
    diag = await page.evaluate(n => window.demo.qaStep(n), chunk);
    const tag = String(done + chunk).padStart(3, '0');
    await page.screenshot({ path: join(OUT_DIR, `${exp}_${tag}.png`) });
    console.log(`[qa] step ${done + chunk}: x=${diag.x?.toFixed(3)} h=${diag.height?.toFixed(3)} fell=${diag.fell} nan=${diag.nan}`);
  }

  await browser.close();

  const pass = diag && !diag.nan && !diag.fell && diag.x > 0.3 && consoleErrors.length === 0;
  console.log('\n[qa] RESULT', JSON.stringify({ exp, live, steps, diag, consoleErrors: consoleErrors.length }, null, 2));
  if (consoleErrors.length) console.log('[qa] console errors:', consoleErrors.slice(0, 5));
  console.log(`[qa] screenshots in ${OUT_DIR}`);
  console.log(pass ? '[qa] PASS ✅' : '[qa] FAIL ❌');
  process.exitCode = pass ? 0 : 1;
}

main()
  .catch(e => { console.error('[qa] ERROR', e); process.exitCode = 2; })
  .finally(() => { if (serverProc) serverProc.kill(); });
