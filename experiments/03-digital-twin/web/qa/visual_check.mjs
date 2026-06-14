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
const cmdArg = args.find(a => a.startsWith('--cmd='));   // e.g. --cmd=1,0,1  (vx,vy,vyaw) to steer
const cmd    = cmdArg ? cmdArg.split('=')[1].split(',').map(Number) : null;
const keysArg = args.find(a => a.startsWith('--keys=')); // e.g. --keys=w  hold real keys (WASD/QE)
const keys   = keysArg ? keysArg.split('=')[1].split('') : null;
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
  // Use 'domcontentloaded' not 'networkidle': heavy scenes (many MB of meshes across dozens
  // of files) keep the network busy past the timeout. The real readiness gate is the
  // window.demo.model waitForFunction below.
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });

  // Wait for the model to load (mujoco wasm from CDN — slow). Policy experiments additionally
  // need the onnx session before we can drive qaStep.
  await page.waitForFunction(() => window.demo && window.demo.model, null,
    { timeout: 120000, polling: 500 });
  const isPolicy = await page.evaluate(() => !!window.demo.policy);
  if (isPolicy) {
    await page.waitForFunction(() => window.demo.session, null, { timeout: 120000, polling: 500 });
  }
  console.log(`[qa] ready (${isPolicy ? 'policy closed-loop' : 'replay'})`);

  let diag = null, pass = false;
  if (isPolicy) {
    if (cmd) {
      await page.evaluate(c => { for (let i = 0; i < c.length; i++) window.demo.pol.command[i] = c[i]; }, cmd);
      console.log('[qa] command set to', cmd);
    }
    // Keyboard steering test: hold real keys (page.keyboard.down fires the keydown the
    // bindCommandKeys listener catches) and assert the policy command vector actually moved
    // off zero — proves the WASD→command path, not just the slider path (--cmd).
    let keysCmd = null;
    if (keys) {
      await page.click('canvas').catch(() => {});   // focus the page so key events land
      for (const k of keys) { await page.keyboard.down(k); }
      keysCmd = await page.evaluate(() => Array.from(window.demo.pol.command));
      console.log('[qa] keys held', keys.join('+'), '-> command', keysCmd);
    }
    await page.screenshot({ path: join(OUT_DIR, `${exp}_000.png`) });
    for (let done = 0; done < steps; done += chunk) {
      diag = await page.evaluate(n => window.demo.qaStep(n), chunk);
      const tag = String(done + chunk).padStart(3, '0');
      await page.screenshot({ path: join(OUT_DIR, `${exp}_${tag}.png`) });
      console.log(`[qa] step ${done + chunk}: x=${diag.x?.toFixed(3)} h=${diag.height?.toFixed(3)} fell=${diag.fell} nan=${diag.nan}`);
    }
    // Forward walk: assert x-progress. Steering test (--cmd): assert it moved off the origin
    // (curved trajectories may have small/negative x), upright, no NaN/console errors.
    const moved = diag ? Math.hypot(diag.x, diag.y) : 0;
    const progressed = (cmd || keys) ? moved > 0.5 : (diag && diag.x > 0.3);
    // Keyboard test additionally requires the held keys to have driven the command off zero.
    const keysOk = !keys || (keysCmd && keysCmd.some(v => Math.abs(v) > 1e-6));
    pass = diag && !diag.nan && !diag.fell && progressed && keysOk && consoleErrors.length === 0;
  } else {
    // Replay experiment: sample frames across the trajectory and screenshot each.
    for (const frac of [0, 0.33, 0.66, 1.0]) {
      diag = await page.evaluate(f => window.demo.qaSeek(f), frac);
      const tag = String(Math.round(frac * 100)).padStart(3, '0');
      await page.screenshot({ path: join(OUT_DIR, `${exp}_${tag}.png`) });
      console.log(`[qa] frame ${diag.frame}/${diag.nframes} nq=${diag.nq}`);
    }
    pass = diag && !diag.error && consoleErrors.length === 0;
  }

  await browser.close();
  console.log('\n[qa] RESULT', JSON.stringify({ exp, live, mode: isPolicy ? 'policy' : 'replay', diag, consoleErrors: consoleErrors.length }, null, 2));
  if (consoleErrors.length) console.log('[qa] console errors:', consoleErrors.slice(0, 5));
  console.log(`[qa] screenshots in ${OUT_DIR}`);
  console.log(pass ? '[qa] PASS ✅' : '[qa] FAIL ❌');
  process.exitCode = pass ? 0 : 1;
}

main()
  .catch(e => { console.error('[qa] ERROR', e); process.exitCode = 2; })
  .finally(() => { if (serverProc) serverProc.kill(); });
