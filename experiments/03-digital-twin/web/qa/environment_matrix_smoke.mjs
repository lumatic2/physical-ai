// Verifies that multiple robots expose the same environment scenario contract shape.
//
// Usage:
//   node qa/environment_matrix_smoke.mjs
//   node qa/environment_matrix_smoke.mjs --live

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const QA_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_DIR = dirname(QA_DIR);
const REPO_ROOT = resolve(WEB_DIR, '..', '..', '..');
const EVIDENCE_DIR = join(REPO_ROOT, 'experiments', '141-multi-robot-environment-matrix', 'verify');
const args = process.argv.slice(2);
const live = args.includes('--live');
const PORT = 8140;
const BASE = live ? 'https://robotics.askewly.com' : `http://127.0.0.1:${PORT}`;

const MATRIX = [
  { robot: 'G1', exp: 'g1-walk', scenario: 'flat-lab-v1' },
  { robot: 'G1', exp: 'g1-rough-walk', scenario: 'rough-curb-v1' },
  { robot: 'Go1', exp: 'go1-walk', scenario: 'flat-lab-v1' },
  { robot: 'Go1', exp: 'go1-rough-walk', scenario: 'rough-curb-v1' },
  { robot: 'Spot', exp: 'spot-walk', scenario: 'flat-lab-v1' },
  { robot: 'Spot', exp: 'spot-rough-walk', scenario: 'rough-curb-v1' },
];

function sleep(ms) {
  return new Promise((resolveSleep) => setTimeout(resolveSleep, ms));
}

async function waitForServer(serverUrl, tries = 50) {
  for (let i = 0; i < tries; i++) {
    try {
      const response = await fetch(serverUrl);
      if (response.ok) return;
    } catch {}
    await sleep(200);
  }
  throw new Error(`server not up at ${serverUrl}`);
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

function targetFor(row) {
  const url = new URL(`${BASE}/`);
  url.searchParams.set('exp', row.exp);
  url.searchParams.set('scenario', row.scenario);
  url.searchParams.set('debug', '1');
  return url.toString();
}

let serverProc = null;

async function main() {
  mkdirSync(EVIDENCE_DIR, { recursive: true });
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

  const rows = [];
  for (const row of MATRIX) {
    const targetUrl = targetFor(row);
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await page.waitForFunction(() => window.demo && window.demo.model && window.demo.qaEnvironmentSummary, null, {
      timeout: 120000,
      polling: 500,
    });
    const summary = await page.evaluate(() => window.demo.qaEnvironmentSummary());
    rows.push({
      ...row,
      targetUrl,
      pass: Boolean(
        summary.pass &&
        summary.scenario?.id === row.scenario &&
        summary.scenario?.seed &&
        summary.scenario?.preset === summary.preset &&
        summary.scenario?.claimBoundary &&
        Array.isArray(summary.scenario?.matrixTags) &&
        summary.scene?.activeScene &&
        summary.physicsProfile?.state
      ),
      preset: summary.preset,
      activeScene: summary.scene?.activeScene || null,
      claimBoundary: summary.scenario?.claimBoundary || null,
      terrain: summary.scenario?.terrain || null,
      obstacle: summary.scenario?.obstacle || null,
      physicsProfile: summary.physicsProfile || null,
      availableScenarios: summary.availableScenarios || [],
    });
  }
  await browser.close();

  const evidence = {
    pass: rows.every((row) => row.pass) && consoleErrors.length === 0,
    live,
    checkedAt: new Date().toISOString(),
    rows,
    consoleErrors,
  };
  const suffix = live ? 'live' : 'local';
  const outPath = join(EVIDENCE_DIR, `environment-matrix-smoke-${suffix}.json`);
  writeFileSync(outPath, JSON.stringify(evidence, null, 2));

  console.log(JSON.stringify(evidence, null, 2));
  console.log(`[qa] summary ${outPath}`);
  console.log(evidence.pass ? '[qa] PASS' : '[qa] FAIL');
  process.exitCode = evidence.pass ? 0 : 1;
}

main()
  .catch((error) => {
    console.error('[qa] ERROR', error);
    process.exitCode = 2;
  })
  .finally(() => {
    if (serverProc) serverProc.kill();
  });
