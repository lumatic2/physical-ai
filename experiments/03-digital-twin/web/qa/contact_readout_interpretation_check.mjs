// Verifies visible and file-backed interpretation boundaries for MuJoCo runtime readout.
//
// Usage:
//   node qa/contact_readout_interpretation_check.mjs --exp=g1-rough-walk --preset=rough-terrain
//   node qa/contact_readout_interpretation_check.mjs --exp=g1-rough-walk --preset=rough-terrain --live

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const QA_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_DIR = dirname(QA_DIR);
const REPO_DIR = join(WEB_DIR, '..', '..', '..');
const OUT_DIR = join(QA_DIR, 'out');
const args = process.argv.slice(2);
const live = args.includes('--live');
const exp = (args.find((a) => a.startsWith('--exp=')) || '--exp=g1-rough-walk').split('=')[1];
const preset = (args.find((a) => a.startsWith('--preset=')) || '--preset=rough-terrain').split('=')[1];
const outArg = args.find((a) => a.startsWith('--out='));
const evidencePath = outArg
  ? outArg.split('=')[1]
  : join(WEB_DIR, '..', '..', '139-contact-readout-interpretation', 'verify', 'contact-readout-interpretation.json');
const reportPath = join(dirname(evidencePath), 'contact-readout-interpretation.md');
const timelinePath = join(WEB_DIR, '..', '..', '138-command-contact-timeline', 'verify', 'command-contact-timeline.json');
const PORT = 8132;
const BASE = live ? 'https://robotics.askewly.com' : `http://127.0.0.1:${PORT}`;
const url = new URL(`${BASE}/`);
url.searchParams.set('exp', exp);
url.searchParams.set('env', preset);
url.searchParams.set('debug', '1');

const supportedClaims = [
  'Browser MuJoCo runtime exposes ncon/contact/cfrc_ext/sensordata readout fields.',
  'Keyboard command changes and runtime readout snapshots can be recorded in one same-run timeline.',
  'The evidence supports a simulator-state readout claim for the browser workbench.',
];

const unsupportedClaims = [
  'It does not prove calibrated contact force accuracy.',
  'It does not prove causal attribution from command input to every readout delta.',
  'It is not real robot telemetry.',
];

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

function readJson(path, fallback = null) {
  if (!existsSync(path)) return fallback;
  return JSON.parse(readFileSync(path, 'utf8'));
}

function writeEvidence(evidence) {
  mkdirSync(dirname(evidencePath), { recursive: true });
  evidence.generatedAt = new Date().toISOString();
  writeFileSync(evidencePath, JSON.stringify(evidence, null, 2));
  const lines = [
    '# Contact Readout Interpretation',
    '',
    `Generated: ${evidence.generatedAt}`,
    '',
    '## Supported',
    ...supportedClaims.map((claim) => `- ${claim}`),
    '',
    '## Not Supported',
    ...unsupportedClaims.map((claim) => `- ${claim}`),
    '',
    '## Source Evidence',
    `- Timeline: ${evidence.timelineEvidence}`,
    `- Local pass: ${Boolean(evidence.local?.pass)}`,
    `- Live pass: ${Boolean(evidence.live?.pass)}`,
  ];
  writeFileSync(reportPath, `${lines.join('\n')}\n`);
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
  const panel = page.locator('[data-testid="physics-diagnostics-panel"]');
  const uiVisible = await panel.isVisible({ timeout: 10000 });
  const uiText = uiVisible ? await panel.innerText() : '';
  const summary = await page.evaluate(() => window.demo.qaWorkbenchSummary());

  const timelineEvidence = readJson(timelinePath, {});
  const readmeText = existsSync(join(REPO_DIR, 'README.md')) ? readFileSync(join(REPO_DIR, 'README.md'), 'utf8') : '';
  const experimentsIndexText = existsSync(join(REPO_DIR, 'experiments', 'README.md'))
    ? readFileSync(join(REPO_DIR, 'experiments', 'README.md'), 'utf8')
    : '';

  const result = {
    url: url.toString(),
    pass: false,
    uiVisible,
    uiText,
    runtime: summary.runtime,
    physicsReadout: summary.physicsReadout,
    sourceTimelinePass: Boolean(timelineEvidence.pass),
    readmeHasBoundary: /calibrated contact force|force calibration/i.test(readmeText) && /real robot telemetry|실제 로봇 telemetry/i.test(readmeText),
    indexHasM139: /139.*contact-readout-interpretation/i.test(experimentsIndexText),
    supportedClaims,
    unsupportedClaims,
    consoleErrors,
  };
  result.pass = Boolean(
    uiVisible &&
    /Supports:/i.test(uiText) &&
    /Does not support:/i.test(uiText) &&
    /browser MuJoCo runtime state is readable/i.test(uiText) &&
    /calibrated contact forces/i.test(uiText) &&
    /causal attribution/i.test(uiText) &&
    /real robot telemetry/i.test(uiText) &&
    summary.physicsReadout?.supported?.includes('sensordata') &&
    result.sourceTimelinePass &&
    result.readmeHasBoundary &&
    result.indexHasM139 &&
    consoleErrors.length === 0
  );

  await page.screenshot({ path: join(OUT_DIR, `${exp}_${live ? 'live' : 'local'}_contact_readout_interpretation.png`) });
  await browser.close();

  const evidence = readJson(evidencePath, {
    milestone: 'M38',
    experiment: exp,
    requestedPreset: preset,
    timelineEvidence: 'experiments/138-command-contact-timeline/verify/command-contact-timeline.json',
    claimBoundary: 'runtime readout supports browser simulator-state visibility, not calibrated force, causality, or real robot telemetry',
    supportedClaims,
    unsupportedClaims,
    local: null,
    live: null,
  });
  evidence.milestone = 'M38';
  evidence.experiment = exp;
  evidence.requestedPreset = preset;
  evidence.timelineEvidence = 'experiments/138-command-contact-timeline/verify/command-contact-timeline.json';
  evidence.claimBoundary = 'runtime readout supports browser simulator-state visibility, not calibrated force, causality, or real robot telemetry';
  evidence.supportedClaims = supportedClaims;
  evidence.unsupportedClaims = unsupportedClaims;
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
    const evidence = readJson(evidencePath, {
      milestone: 'M38',
      experiment: exp,
      requestedPreset: preset,
      local: null,
      live: null,
    });
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

