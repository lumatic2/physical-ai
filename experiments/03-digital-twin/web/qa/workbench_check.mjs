// Verifies the visitor-facing Digital Twin Workbench summary for one registered experiment.
//
// Usage:
//   node qa/workbench_check.mjs --exp=unitree-g1-elastic-stand

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const QA_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_DIR = dirname(QA_DIR);
const OUT_DIR = join(QA_DIR, 'out');
const args = process.argv.slice(2);
const live = args.includes('--live');
const exp = (args.find((a) => a.startsWith('--exp=')) || '--exp=unitree-g1-elastic-stand').split('=')[1];
const PORT = 8132;
const BASE = live ? 'https://robotics.askewly.com' : `http://127.0.0.1:${PORT}`;
const URL = `${BASE}/?exp=${exp}`;

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

let serverProc = null;
function spawnDevServer() {
  if (process.platform === 'win32') {
    return spawn('cmd.exe', ['/d', '/s', '/c', `npm run dev -- --host 127.0.0.1 --port ${PORT}`], {
      cwd: WEB_DIR,
      stdio: 'ignore',
    });
  }
  const npmCmd = 'npm';
  return spawn(npmCmd, ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(PORT)], {
    cwd: WEB_DIR,
    stdio: 'ignore',
  });
}

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

  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForFunction(() => window.demo && window.demo.model && window.demo.qaWorkbenchSummary, null, {
    timeout: 120000,
    polling: 500,
  });

  const summary = await page.evaluate(() => window.demo.qaWorkbenchSummary());
  summary.consoleErrors = consoleErrors.length;
  summary.pass = Boolean(
    summary.pass &&
    summary.stateContract &&
    summary.stateContract.nq > 0 &&
    Array.isArray(summary.evidenceLanes) &&
    summary.evidenceLanes.length > 0 &&
    consoleErrors.length === 0
  );

  const outPath = join(OUT_DIR, `${exp}_workbench_summary.json`);
  writeFileSync(outPath, JSON.stringify(summary, null, 2));
  await page.screenshot({ path: join(OUT_DIR, `${exp}_workbench.png`) });
  await browser.close();

  console.log(JSON.stringify(summary, null, 2));
  console.log(`[qa] summary ${outPath}`);
  console.log(summary.pass ? '[qa] PASS' : '[qa] FAIL');
  process.exitCode = summary.pass ? 0 : 1;
}

main()
  .catch((error) => {
    console.error('[qa] ERROR', error);
    process.exitCode = 2;
  })
  .finally(() => {
    if (serverProc) serverProc.kill();
  });
