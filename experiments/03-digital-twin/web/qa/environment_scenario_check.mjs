// Verifies the Digital Twin environment scenario manifest contract.
//
// Usage:
//   node qa/environment_scenario_check.mjs --exp=g1-rough-walk --scenario=rough-curb-v1
//   node qa/environment_scenario_check.mjs --live --exp=g1-rough-walk --scenario=rough-curb-v1

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const QA_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_DIR = dirname(QA_DIR);
const REPO_ROOT = resolve(WEB_DIR, '..', '..', '..');
const OUT_DIR = join(QA_DIR, 'out');
const EVIDENCE_DIR = join(REPO_ROOT, 'experiments', '140-environment-scenario-manifest', 'verify');
const args = process.argv.slice(2);
const live = args.includes('--live');
const exp = (args.find((a) => a.startsWith('--exp=')) || '--exp=g1-rough-walk').split('=')[1];
const scenario = (args.find((a) => a.startsWith('--scenario=')) || '--scenario=rough-curb-v1').split('=')[1];
const outArg = args.find((a) => a.startsWith('--out='));
const PORT = 8139;
const BASE = live ? 'https://robotics.askewly.com' : `http://127.0.0.1:${PORT}`;
const url = new URL(`${BASE}/`);
url.searchParams.set('exp', exp);
url.searchParams.set('scenario', scenario);
url.searchParams.set('debug', '1');
const targetUrl = url.toString();

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

let serverProc = null;

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
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

  await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForFunction(() => window.demo && window.demo.model && window.demo.qaEnvironmentSummary, null, {
    timeout: 120000,
    polling: 500,
  });
  await page.waitForSelector('[data-testid="environment-scenario-status"]', { timeout: 60000 });

  const summary = await page.evaluate(() => window.demo.qaEnvironmentSummary());
  const statusText = await page.locator('[data-testid="environment-scenario-status"]').innerText();
  const evidence = {
    pass: false,
    live,
    targetUrl,
    requested: { exp, scenario },
    consoleErrors,
    statusText,
    summary,
  };
  evidence.pass = Boolean(
    summary.pass &&
    summary.scenario?.id === scenario &&
    summary.scenario?.seed &&
    summary.scenario?.terrain?.kind &&
    summary.scenario?.friction &&
    summary.scenario?.lighting?.profile &&
    typeof summary.scenario?.obstacle?.enabled === 'boolean' &&
    summary.scenario?.claimBoundary &&
    summary.scenario?.parameters &&
    summary.availableScenarios?.includes(scenario) &&
    statusText.includes(scenario) &&
    statusText.includes(summary.scenario.seed) &&
    consoleErrors.length === 0
  );

  const suffix = live ? 'live' : 'local';
  const outPath = outArg ? resolve(WEB_DIR, outArg.split('=')[1]) : join(EVIDENCE_DIR, `environment-scenario-manifest-${suffix}.json`);
  writeFileSync(outPath, JSON.stringify(evidence, null, 2));
  await page.screenshot({ path: join(OUT_DIR, `environment_scenario_${scenario}_${suffix}.png`) });
  await browser.close();

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
