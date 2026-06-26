// Records keyboard command changes and MuJoCo runtime readout snapshots in one timeline.
//
// Usage:
//   node qa/command_contact_timeline.mjs --exp=g1-rough-walk --preset=rough-terrain
//   node qa/command_contact_timeline.mjs --exp=g1-rough-walk --preset=rough-terrain --live

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
const exp = (args.find((a) => a.startsWith('--exp=')) || '--exp=g1-rough-walk').split('=')[1];
const preset = (args.find((a) => a.startsWith('--preset=')) || '--preset=rough-terrain').split('=')[1];
const outArg = args.find((a) => a.startsWith('--out='));
const evidencePath = outArg
  ? outArg.split('=')[1]
  : join(WEB_DIR, '..', '..', '138-command-contact-timeline', 'verify', 'command-contact-timeline.json');
const PORT = 8132;
const BASE = live ? 'https://robotics.askewly.com' : `http://127.0.0.1:${PORT}`;
const url = new URL(`${BASE}/`);
url.searchParams.set('exp', exp);
url.searchParams.set('env', preset);
url.searchParams.set('debug', '1');

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
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

function readEvidence() {
  if (!existsSync(evidencePath)) {
    return {
      milestone: 'M37',
      experiment: exp,
      requestedPreset: preset,
      claimBoundary: 'same-run browser command/readout timeline, not causal proof or real robot telemetry',
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

function fieldSample(readout, name) {
  const field = (readout?.auditedFields || []).find((item) => item.name === name);
  const sample = field?.sample;
  return Array.isArray(sample) ? sample.slice(0, 6) : sample ?? null;
}

function numericDelta(a, b) {
  if (!Array.isArray(a) || !Array.isArray(b)) return null;
  const n = Math.min(a.length, b.length);
  let max = 0;
  for (let i = 0; i < n; i++) {
    const av = Number(a[i]);
    const bv = Number(b[i]);
    if (Number.isFinite(av) && Number.isFinite(bv)) max = Math.max(max, Math.abs(av - bv));
  }
  return max;
}

function isZeroCommand(command) {
  return Array.isArray(command) && command.length === 3 && command.every((value) => Math.abs(value) < 1e-6);
}

let serverProc = null;

async function snapshot(page, label, stepResult = null) {
  return page.evaluate(({ label, stepResult }) => {
    const summary = window.demo.qaWorkbenchSummary();
    return {
      label,
      t: Number(window.demo.data?.time ?? 0),
      command: summary.control?.command || null,
      inputSource: summary.control?.inputSource || null,
      heldCommands: summary.control?.heldCommands || [],
      contactCount: summary.physicsReadout?.contactCount ?? null,
      supported: summary.physicsReadout?.supported || [],
      cfrcExtSample: (summary.physicsReadout?.auditedFields || []).find((field) => field.name === 'cfrc_ext')?.sample?.slice?.(0, 6) || null,
      sensorDataSample: (summary.physicsReadout?.auditedFields || []).find((field) => field.name === 'sensordata')?.sample?.slice?.(0, 6) || null,
      environmentClaimLevel: summary.environment?.claimLevel || null,
      stepResult,
    };
  }, { label, stepResult });
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

  await page.goto(url.toString(), { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForFunction(() => window.demo && window.demo.model && window.demo.qaWorkbenchSummary && window.demo.qaStep, null, {
    timeout: 120000,
    polling: 500,
  });
  await page.waitForFunction(() => window.demo.qaWorkbenchSummary().control?.enabled === true, null, {
    timeout: 30000,
    polling: 250,
  });

  const timeline = [];
  timeline.push(await snapshot(page, 'baseline'));

  await page.keyboard.down('ArrowUp');
  await page.waitForFunction(() => window.demo.qaWorkbenchSummary().control?.command?.[0] > 0, null, {
    timeout: 10000,
    polling: 100,
  });
  timeline.push(await snapshot(page, 'command-held'));

  const firstStep = await page.evaluate(() => window.demo.qaStep(24));
  timeline.push(await snapshot(page, 'after-24-steps-command-held', firstStep));

  const secondStep = await page.evaluate(() => window.demo.qaStep(24));
  timeline.push(await snapshot(page, 'after-48-steps-command-held', secondStep));

  await page.keyboard.up('ArrowUp');
  await page.waitForFunction(() => {
    const command = window.demo.qaWorkbenchSummary().control?.command || [];
    return command.length === 3 && command.every((value) => Math.abs(value) < 1e-6);
  }, null, { timeout: 10000, polling: 100 });
  timeline.push(await snapshot(page, 'released'));

  const finalStep = await page.evaluate(() => window.demo.qaStep(12));
  timeline.push(await snapshot(page, 'after-release-12-steps', finalStep));

  const result = {
    url: url.toString(),
    pass: false,
    experiment: exp,
    requestedPreset: preset,
    claimBoundary: 'same-run browser command/readout timeline, not causal proof or real robot telemetry',
    timeline,
    deltas: {
      baselineToHeldSensorMaxAbs: numericDelta(timeline[0].sensorDataSample, timeline[2].sensorDataSample),
      heldToLaterSensorMaxAbs: numericDelta(timeline[2].sensorDataSample, timeline[3].sensorDataSample),
      baselineToHeldCfrcMaxAbs: numericDelta(timeline[0].cfrcExtSample, timeline[2].cfrcExtSample),
    },
    consoleErrors,
  };
  result.pass = Boolean(
    isZeroCommand(timeline[0].command) &&
    timeline[1].command?.[0] > 0 &&
    timeline[2].stepResult?.command?.[0] > 0 &&
    timeline[3].stepResult?.command?.[0] > 0 &&
    isZeroCommand(timeline[4].command) &&
    isZeroCommand(timeline[5].stepResult?.command) &&
    timeline.every((sample) => Number.isFinite(sample.contactCount) && sample.supported.includes('sensordata')) &&
    ((result.deltas.baselineToHeldSensorMaxAbs ?? 0) > 0 || (result.deltas.heldToLaterSensorMaxAbs ?? 0) > 0) &&
    consoleErrors.length === 0
  );

  await page.screenshot({ path: join(OUT_DIR, `${exp}_${live ? 'live' : 'local'}_command_contact_timeline.png`) });
  await browser.close();

  const evidence = readEvidence();
  evidence.milestone = 'M37';
  evidence.experiment = exp;
  evidence.requestedPreset = preset;
  evidence.claimBoundary = 'same-run browser command/readout timeline, not causal proof or real robot telemetry';
  evidence[live ? 'live' : 'local'] = result;
  evidence.pass = Boolean(evidence.local?.pass && (evidence.live?.pass ?? true));
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
    evidence.pass = Boolean(evidence.local?.pass && (evidence.live?.pass ?? true));
    writeEvidence(evidence);
    console.error('[qa] ERROR', error);
    process.exitCode = 2;
  })
  .finally(() => {
    if (serverProc) serverProc.kill();
  });

