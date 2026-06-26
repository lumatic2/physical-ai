// Verifies that keyboard input changes the browser policy command and visible UI.
//
// Usage:
//   node qa/control_smoke.mjs --exp=g1-walk
//   node qa/control_smoke.mjs --exp=g1-walk --live

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const QA_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_DIR = dirname(QA_DIR);
const OUT_DIR = join(QA_DIR, 'out');
const args = process.argv.slice(2);
const live = args.includes('--live');
const exp = (args.find((a) => a.startsWith('--exp=')) || '--exp=g1-walk').split('=')[1];
const outArg = args.find((a) => a.startsWith('--out='));
const evidencePath = outArg
  ? outArg.split('=')[1]
  : join(WEB_DIR, '..', '..', '134-user-controllable-digital-twin', 'verify', 'control-smoke.json');
const PORT = 8132;
const BASE = live ? 'https://robotics.askewly.com' : `http://127.0.0.1:${PORT}`;
const url = new URL(`${BASE}/`);
url.searchParams.set('exp', exp);

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForServer(url, tries = 50) {
  for (let i = 0; i < tries; i++) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {}
    await sleep(200);
  }
  throw new Error(`server not up at ${url}`);
}

function spawnDevServer() {
  if (process.platform === 'win32') {
    return spawn('cmd.exe', ['/d', '/s', '/c', `npm run dev -- --host 127.0.0.1 --port ${PORT}`], {
      cwd: WEB_DIR,
      stdio: 'ignore',
    });
  }
  return spawn('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(PORT)], {
    cwd: WEB_DIR,
    stdio: 'ignore',
  });
}

function readEvidence() {
  if (!existsSync(evidencePath)) {
    return {
      milestone: 'M33',
      experiment: exp,
      claimBoundary: 'browser policy command input, not real robot telemetry',
      local: null,
      live: null,
    };
  }
  return JSON.parse(readFileSync(evidencePath, 'utf8'));
}

function writeEvidence(evidence) {
  mkdirSync(dirname(evidencePath), { recursive: true });
  evidence.generatedAt = new Date().toISOString();
  writeFileSync(evidencePath, JSON.stringify(evidence, null, 2));
}

function isZeroCommand(command) {
  return Array.isArray(command) && command.length === 3 && command.every((value) => Math.abs(value) < 1e-6);
}

async function readControl(page) {
  return page.evaluate(() => window.demo.qaWorkbenchSummary().control);
}

let serverProc = null;

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  if (!live) {
    serverProc = spawnDevServer();
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
  const page = await browser.newPage({ viewport: { width: 1280, height: 960 } });
  const consoleErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => consoleErrors.push(String(error)));

  await page.goto(url.toString(), { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForFunction(() => window.demo && window.demo.model && window.demo.qaWorkbenchSummary, null, {
    timeout: 120000,
    polling: 500,
  });
  await page.waitForFunction(() => window.demo.qaWorkbenchSummary().control?.enabled === true, null, {
    timeout: 30000,
    polling: 250,
  });

  const uiVisible = await page.locator('[data-testid="policy-command-status"]').isVisible({ timeout: 10000 });
  const uiText = uiVisible ? await page.locator('[data-testid="policy-command-status"]').innerText() : '';
  const initial = await readControl(page);

  await page.keyboard.down('ArrowUp');
  await page.waitForFunction(() => {
    const command = window.demo.qaWorkbenchSummary().control?.command || [];
    return command[0] > 0 && Math.abs(command[1] || 0) < 1e-6 && Math.abs(command[2] || 0) < 1e-6;
  }, null, { timeout: 10000, polling: 100 });
  const afterArrowUp = await readControl(page);

  await page.keyboard.up('ArrowUp');
  await page.waitForFunction(() => {
    const command = window.demo.qaWorkbenchSummary().control?.command || [];
    return command.length === 3 && command.every((value) => Math.abs(value) < 1e-6);
  }, null, { timeout: 10000, polling: 100 });
  const afterRelease = await readControl(page);

  await page.keyboard.down('ArrowLeft');
  await page.waitForFunction(() => {
    const command = window.demo.qaWorkbenchSummary().control?.command || [];
    return Math.abs(command[0] || 0) < 1e-6 && command[1] > 0 && Math.abs(command[2] || 0) < 1e-6;
  }, null, { timeout: 10000, polling: 100 });
  const afterArrowLeft = await readControl(page);

  await page.keyboard.up('ArrowLeft');
  await page.waitForFunction(() => {
    const command = window.demo.qaWorkbenchSummary().control?.command || [];
    return command.length === 3 && command.every((value) => Math.abs(value) < 1e-6);
  }, null, { timeout: 10000, polling: 100 });
  const afterArrowLeftRelease = await readControl(page);

  const result = {
    url: url.toString(),
    pass: false,
    initial,
    afterArrowUp,
    afterRelease,
    afterArrowLeft,
    afterArrowLeftRelease,
    uiVisible,
    uiText,
    consoleErrors,
  };
  result.pass = Boolean(
    initial?.enabled === true &&
    isZeroCommand(initial.command) &&
    afterArrowUp?.command?.[0] > 0 &&
    isZeroCommand(afterRelease.command) &&
    afterArrowLeft?.command?.[1] > 0 &&
    isZeroCommand(afterArrowLeftRelease.command) &&
    uiVisible &&
    /policy command/i.test(uiText) &&
    /(browser|브라우저) policy input/i.test(uiText) &&
    consoleErrors.length === 0
  );

  await page.screenshot({ path: join(OUT_DIR, `${exp}_${live ? 'live' : 'local'}_control_smoke.png`) });
  await browser.close();

  const evidence = readEvidence();
  evidence.milestone = 'M33';
  evidence.experiment = exp;
  evidence.claimBoundary = 'browser policy command input, not real robot telemetry';
  evidence[live ? 'live' : 'local'] = result;
  evidence.pass = Boolean(evidence.local?.pass && evidence.live?.pass);
  writeEvidence(evidence);

  console.log(JSON.stringify(result, null, 2));
  console.log(`[qa] evidence ${evidencePath}`);
  console.log(result.pass ? '[qa] PASS' : '[qa] FAIL');
  process.exitCode = result.pass ? 0 : 1;
}

main()
  .catch((error) => {
    const evidence = readEvidence();
    evidence[live ? 'live' : 'local'] = {
      url: url.toString(),
      pass: false,
      error: String(error?.stack || error),
    };
    evidence.pass = Boolean(evidence.local?.pass && evidence.live?.pass);
    writeEvidence(evidence);
    console.error('[qa] ERROR', error);
    process.exitCode = 2;
  })
  .finally(() => {
    if (serverProc) serverProc.kill();
  });
