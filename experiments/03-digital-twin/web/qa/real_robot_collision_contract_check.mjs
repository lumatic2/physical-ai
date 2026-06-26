// Verifies the real-robot collision readiness contract exposed by the browser runtime.
//
// Usage:
//   node qa/real_robot_collision_contract_check.mjs
//   node qa/real_robot_collision_contract_check.mjs --live

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const QA_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_DIR = dirname(QA_DIR);
const REPO_ROOT = resolve(WEB_DIR, '..', '..', '..');
const EVIDENCE_DIR = join(REPO_ROOT, 'experiments', '146-real-robot-collision-contract', 'verify');
const OUT_DIR = join(QA_DIR, 'out');
const args = process.argv.slice(2);
const live = args.includes('--live');
const PORT = 8145;
const BASE = live ? 'https://robotics.askewly.com' : `http://127.0.0.1:${PORT}`;
const url = new URL(`${BASE}/`);
url.searchParams.set('exp', 'g1-obstacle-walk');
url.searchParams.set('scenario', 'obstacle-lane-v1');
url.searchParams.set('debug', '1');

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
  mkdirSync(EVIDENCE_DIR, { recursive: true });
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
  await page.waitForFunction(() => window.demo && window.demo.model && window.demo.qaEnvironmentSummary, null, {
    timeout: 120000,
    polling: 500,
  });

  const result = await page.evaluate(() => {
    const environment = window.demo.qaEnvironmentSummary();
    const contract = environment.realRobotCollision;
    const requiredZones = ['pelvis', 'torso', 'head', 'feet'];
    const zones = contract?.bodyZones || [];
    return {
      environmentPass: environment.pass === true,
      activeScene: environment.scene?.activeScene || null,
      contract,
      requiredZoneCoverage: requiredZones.every((id) => zones.some((zone) => (
        zone.id === id && zone.present === true && zone.contactEligible === true
      ))),
      requiredTelemetryCount: contract?.requiredTelemetry?.length || 0,
      requiredActuationGateCount: contract?.requiredActuationGate?.length || 0,
      hasStopCriteria: Boolean(
        contract?.stopCriteria &&
        Number.isFinite(Number(contract.stopCriteria.maxBaseTiltRad)) &&
        Number.isFinite(Number(contract.stopCriteria.maxJointTorqueRatio))
      ),
    };
  });

  const evidence = {
    pass: Boolean(
      result.environmentPass &&
      result.contract?.applies === true &&
      result.contract?.simEnvelopeCoveragePass === true &&
      result.contract?.hardwareReady === false &&
      result.contract?.realRobotCollisionArmed === false &&
      result.requiredZoneCoverage &&
      result.requiredTelemetryCount >= 6 &&
      result.requiredActuationGateCount >= 3 &&
      result.hasStopCriteria &&
      /not armed without a hardware telemetry bridge/i.test(result.contract?.claimBoundary || '') &&
      consoleErrors.length === 0
    ),
    live,
    targetUrl: url.toString(),
    consoleErrors,
    ...result,
    claimBoundary: 'Real-robot collision readiness contract only; no hardware collision proof or armed real robot control path is claimed.',
  };

  const suffix = live ? 'live' : 'local';
  const outPath = join(EVIDENCE_DIR, `real-robot-collision-contract-${suffix}.json`);
  writeFileSync(outPath, JSON.stringify(evidence, null, 2));
  await page.screenshot({ path: join(OUT_DIR, `real_robot_collision_contract_${suffix}.png`) });
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
