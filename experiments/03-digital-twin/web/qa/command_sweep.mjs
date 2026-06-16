// M12 command robustness QA.
//
// Runs joystick-conditioned policy experiments under several command vectors and records
// displacement, yaw drift, fall/NaN status, and console errors. Each scenario uses a fresh
// page so stateful policies (G1 phase, Spot qpos_error_history) start from the same initial
// condition.
//
// Usage:
//   node qa/command_sweep.mjs --exp=go1-walk
//   node qa/command_sweep.mjs --exp=spot-walk --out=../../07-command-terrain-robustness/verify/spot-command-sweep.json
//   node qa/command_sweep.mjs --exp=go1-rough-walk --measure-only

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const QA_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_DIR = dirname(QA_DIR);
const OUT_DIR = join(QA_DIR, 'out');

const args = process.argv.slice(2);
const live = args.includes('--live');
const exp = (args.find(a => a.startsWith('--exp=')) || '--exp=go1-walk').split('=')[1];
const steps = parseInt((args.find(a => a.startsWith('--steps=')) || '--steps=300').split('=')[1], 10);
const chunk = parseInt((args.find(a => a.startsWith('--chunk=')) || '--chunk=50').split('=')[1], 10);
const measureOnly = args.includes('--measure-only');
const outArg = args.find(a => a.startsWith('--out='));
const outPath = outArg ? resolve(WEB_DIR, outArg.split('=')[1]) : null;
const PORT = 8133;
const BASE = live ? 'https://robotics.askewly.com' : `http://127.0.0.1:${PORT}`;

const SCENARIOS = [
  { name: 'forward', cmd: [1.0, 0.0, 0.0], expect: 'x+' },
  { name: 'strafe-left', cmd: [0.0, 0.5, 0.0], expect: 'y+' },
  { name: 'strafe-right', cmd: [0.0, -0.5, 0.0], expect: 'y-' },
  { name: 'turn-left', cmd: [0.0, 0.0, 0.8], expect: 'yaw+' },
  { name: 'turn-right', cmd: [0.0, 0.0, -0.8], expect: 'yaw-' },
  { name: 'diagonal-left', cmd: [0.8, 0.4, 0.0], expect: 'x+y+' },
];

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function waitForServer(url, tries = 50) {
  for (let i = 0; i < tries; i++) {
    try { const r = await fetch(url); if (r.ok) return; } catch {}
    await sleep(200);
  }
  throw new Error(`server not up at ${url}`);
}

function angleDelta(a, b) {
  let d = a - b;
  while (d > Math.PI) d -= 2 * Math.PI;
  while (d < -Math.PI) d += 2 * Math.PI;
  return d;
}

async function runScenario(browser, scenario) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 960 } });
  const consoleErrors = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => consoleErrors.push(String(e)));

  const url = `${BASE}/?exp=${exp}`;
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForFunction(() => window.demo && window.demo.model, null, { timeout: 120000, polling: 500 });
  await page.waitForFunction(() => window.demo && window.demo.session, null, { timeout: 120000, polling: 500 });
  await page.evaluate(c => { for (let i = 0; i < c.length; i++) window.demo.pol.command[i] = c[i]; }, scenario.cmd);

  const start = await page.evaluate(() => window.demo.qaStep(0));
  let diag = start;
  for (let done = 0; done < steps; done += chunk) {
    diag = await page.evaluate(n => window.demo.qaStep(n), Math.min(chunk, steps - done));
  }
  await page.screenshot({ path: join(OUT_DIR, `${exp}_${scenario.name}.png`) });
  await page.close();

  const dx = diag.x - start.x;
  const dy = diag.y - start.y;
  const dyaw = angleDelta(diag.yaw, start.yaw);
  return {
    name: scenario.name,
    command: scenario.cmd,
    expect: scenario.expect,
    steps,
    dx,
    dy,
    distance: Math.hypot(dx, dy),
    dyaw,
    finalHeight: diag.height,
    fell: !!diag.fell,
    nan: !!diag.nan,
    consoleErrors,
  };
}

let serverProc = null;
try {
  mkdirSync(OUT_DIR, { recursive: true });
  if (!live) {
    serverProc = spawn('python', ['serve_coi.py', String(PORT)], { cwd: WEB_DIR, stdio: 'ignore' });
    await waitForServer(`${BASE}/index.html`);
  }

  const browser = await chromium.launch({
    headless: true,
    args: [
      '--disable-background-timer-throttling',
      '--disable-renderer-backgrounding',
      '--disable-backgrounding-occluded-windows',
      '--use-gl=swiftshader',
      '--enable-webgl',
      '--ignore-gpu-blocklist',
    ],
  });

  const results = [];
  for (const scenario of SCENARIOS) {
    const result = await runScenario(browser, scenario);
    results.push(result);
    console.log(
      `[sweep] ${exp}/${scenario.name}: ` +
      `dx=${result.dx.toFixed(3)} dy=${result.dy.toFixed(3)} ` +
      `dyaw=${result.dyaw.toFixed(3)} h=${result.finalHeight.toFixed(3)} ` +
      `fell=${result.fell} nan=${result.nan} errors=${result.consoleErrors.length}`
    );
  }
  await browser.close();

  const report = {
    exp,
    live,
    steps,
    chunk,
    generatedAt: new Date().toISOString(),
    results,
  };
  if (outPath) {
    mkdirSync(dirname(outPath), { recursive: true });
    writeFileSync(outPath, JSON.stringify(report, null, 2) + '\n');
    console.log(`[sweep] wrote ${outPath}`);
  }

  const failed = results.filter(r => r.fell || r.nan || r.consoleErrors.length);
  console.log(failed.length ? '[sweep] FAIL' : '[sweep] PASS');
  process.exitCode = failed.length && !measureOnly ? 1 : 0;
} catch (e) {
  console.error('[sweep] ERROR', e);
  process.exitCode = 2;
} finally {
  if (serverProc) serverProc.kill();
}
