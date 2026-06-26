// Compares randomized episode outcomes against a deterministic baseline.
//
// Usage:
//   node qa/randomized_episode_comparison.mjs --profile=obstacle-command-noise-v1
//   node qa/randomized_episode_comparison.mjs --live --profile=obstacle-command-noise-v1

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import {
  getEpisodeComparisonProfile,
  getEpisodeRandomizationProfile,
  summarizeEpisodeComparisonProfile,
  summarizeEpisodeRandomizationProfile,
} from '../src/environmentPresets.js';

const QA_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_DIR = dirname(QA_DIR);
const REPO_ROOT = resolve(WEB_DIR, '..', '..', '..');
const EVIDENCE_DIR = join(REPO_ROOT, 'experiments', '144-randomized-episode-comparison', 'verify');
const OUT_DIR = join(QA_DIR, 'out');
const args = process.argv.slice(2);
const live = args.includes('--live');
const requestedProfileId = (args.find((a) => a.startsWith('--profile=')) || '--profile=obstacle-command-noise-v1').split('=')[1];
const comparisonProfileId = (args.find((a) => a.startsWith('--comparison=')) || '--comparison=obstacle-command-noise-comparison-v1').split('=')[1];
const comparisonProfile = getEpisodeComparisonProfile(comparisonProfileId);
const randomizationProfile = getEpisodeRandomizationProfile(requestedProfileId || comparisonProfile.randomizationProfile);
const steps = parseInt((args.find((a) => a.startsWith('--steps=')) || `--steps=${randomizationProfile.steps}`).split('=')[1], 10);
const chunk = parseInt((args.find((a) => a.startsWith('--chunk=')) || `--chunk=${randomizationProfile.chunk}`).split('=')[1], 10);
const PORT = 8143;
const BASE = live ? 'https://robotics.askewly.com' : `http://127.0.0.1:${PORT}`;

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

function angleDelta(a, b) {
  let d = a - b;
  while (d > Math.PI) d -= 2 * Math.PI;
  while (d < -Math.PI) d += 2 * Math.PI;
  return d;
}

function targetFor(episode) {
  const url = new URL(`${BASE}/`);
  url.searchParams.set('exp', randomizationProfile.experiment);
  url.searchParams.set('scenario', randomizationProfile.scenario);
  url.searchParams.set('episodeProfile', randomizationProfile.id);
  url.searchParams.set('comparisonProfile', comparisonProfile.id);
  url.searchParams.set('debug', '1');
  url.searchParams.set('episode', episode.id);
  return url.toString();
}

async function runEpisode(browser, episode) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 960 } });
  const consoleErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => consoleErrors.push(String(error)));

  const targetUrl = targetFor(episode);
  await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForFunction(() => window.demo && window.demo.model && window.demo.session && window.demo.qaStep, null, {
    timeout: 120000,
    polling: 500,
  });
  await page.waitForSelector('[data-testid="episode-comparison-status"]', { timeout: 60000 });
  await page.evaluate((next) => {
    for (let i = 0; i < next.command.length; i++) window.demo.pol.command[i] = next.command[i];
    window.demo.params.ctrlnoisestd = next.ctrlNoiseStd;
    window.demo.params.ctrlnoiserate = next.ctrlNoiseRate;
  }, episode);

  const start = await page.evaluate(() => window.demo.qaStep(0));
  let diag = start;
  let minHeight = Number.isFinite(start.height) ? start.height : Infinity;
  for (let done = 0; done < steps; done += chunk) {
    diag = await page.evaluate((n) => window.demo.qaStep(n), Math.min(chunk, steps - done));
    if (Number.isFinite(diag.height)) minHeight = Math.min(minHeight, diag.height);
  }
  const environment = await page.evaluate(() => window.demo.qaEnvironmentSummary());
  const statusText = await page.locator('[data-testid="episode-comparison-status"]').innerText();
  await page.screenshot({ path: join(OUT_DIR, `${comparisonProfile.id}_${episode.id}_${live ? 'live' : 'local'}.png`) });
  await page.close();

  const dx = diag.x - start.x;
  const dy = diag.y - start.y;
  const dyaw = angleDelta(diag.yaw, start.yaw);
  const distance = Math.hypot(dx, dy);
  const criteria = randomizationProfile.passCriteria;
  const pass = Boolean(
    environment.pass &&
    environment.episodeComparison?.id === comparisonProfile.id &&
    statusText.includes(comparisonProfile.id) &&
    distance >= criteria.minDistanceM &&
    Math.abs(dy) <= criteria.maxAbsYDriftM &&
    minHeight > criteria.maxFallHeightM &&
    !diag.fell &&
    !diag.nan &&
    consoleErrors.length === 0
  );
  const score = Math.max(0, Math.min(1, distance / 0.35)) * (pass ? 1 : 0);
  return {
    id: episode.id,
    seed: episode.seed,
    targetUrl,
    command: episode.command,
    ctrlNoiseStd: episode.ctrlNoiseStd,
    ctrlNoiseRate: episode.ctrlNoiseRate,
    steps,
    chunk,
    dx,
    dy,
    dyaw,
    distance,
    finalHeight: diag.height,
    minHeight,
    fell: Boolean(diag.fell),
    nan: Boolean(diag.nan),
    contactCount: environment.physicsReadout?.contactCount ?? null,
    consoleErrors,
    score,
    pass,
  };
}

function compareEpisode(baseline, episode) {
  const thresholds = comparisonProfile.driftThresholds;
  const delta = {
    distanceDeltaM: episode.distance - baseline.distance,
    yDeltaM: episode.dy - baseline.dy,
    yawDeltaRad: angleDelta(episode.dyaw, baseline.dyaw),
    minHeightDeltaM: episode.minHeight - baseline.minHeight,
    scoreDelta: episode.score - baseline.score,
  };
  const pass = Boolean(
    episode.pass &&
    Math.abs(delta.distanceDeltaM) <= thresholds.maxAbsDistanceDeltaM &&
    Math.abs(delta.yDeltaM) <= thresholds.maxAbsYDeltaM &&
    Math.abs(delta.yawDeltaRad) <= thresholds.maxAbsYawDeltaRad &&
    delta.minHeightDeltaM >= -thresholds.maxMinHeightDropM &&
    delta.scoreDelta >= -thresholds.maxScoreDrop
  );
  return {
    baselineEpisode: baseline.id,
    episode: episode.id,
    command: episode.command,
    ctrlNoiseStd: episode.ctrlNoiseStd,
    ctrlNoiseRate: episode.ctrlNoiseRate,
    delta,
    thresholds,
    pass,
  };
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

  const episodes = [];
  for (const episode of randomizationProfile.episodes) {
    const result = await runEpisode(browser, episode);
    episodes.push(result);
    console.log(
      `[episode] ${episode.id}: distance=${result.distance.toFixed(3)} ` +
      `minHeight=${result.minHeight.toFixed(3)} score=${result.score.toFixed(2)} pass=${result.pass}`,
    );
  }
  await browser.close();

  const baseline = episodes.find((episode) => episode.id === comparisonProfile.baselineEpisode);
  if (!baseline) throw new Error(`baseline episode missing: ${comparisonProfile.baselineEpisode}`);
  const comparisons = episodes
    .filter((episode) => episode.id !== baseline.id)
    .map((episode) => compareEpisode(baseline, episode));

  const evidence = {
    pass: baseline.pass && comparisons.length > 0 && comparisons.every((comparison) => comparison.pass),
    live,
    generatedAt: new Date().toISOString(),
    profile: summarizeEpisodeRandomizationProfile(randomizationProfile.id),
    comparisonProfile: summarizeEpisodeComparisonProfile(comparisonProfile.id),
    baseline,
    comparisons,
    episodes,
    claimBoundary: comparisonProfile.claimBoundary,
  };
  const suffix = live ? 'live' : 'local';
  const outPath = join(EVIDENCE_DIR, `randomized-episode-comparison-${suffix}.json`);
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
