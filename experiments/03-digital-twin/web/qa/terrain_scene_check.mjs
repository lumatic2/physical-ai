// Verifies that rough-terrain preset is backed by active MJCF terrain geoms.
//
// Usage:
//   node qa/terrain_scene_check.mjs --exp=g1-rough-walk --preset=rough-terrain

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
const exp = (args.find((a) => a.startsWith('--exp=')) || '--exp=g1-rough-walk').split('=')[1];
const preset = (args.find((a) => a.startsWith('--preset=')) || '--preset=rough-terrain').split('=')[1];
const PORT = 8132;
const BASE = live ? 'https://robotics.askewly.com' : `http://127.0.0.1:${PORT}`;
const url = new URL(`${BASE}/`);
url.searchParams.set('exp', exp);
url.searchParams.set('env', preset);

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

let serverProc = null;

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  if (!live) {
    serverProc = spawnDevServer();
    await waitForServer(`${BASE}/index.html`);
  }

  const browser = await chromium.launch({
    headless: true,
    args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'],
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

  const summary = await page.evaluate(() => window.demo.qaEnvironmentSummary());
  const result = {
    experiment: exp,
    requestedPreset: preset,
    activeScene: summary.scene?.activeScene || null,
    preset: summary.preset,
    claimLevel: summary.claimLevel,
    sceneMode: summary.scene?.mode || null,
    contactBearingTerrain: summary.scene?.contactBearingTerrain === true,
    terrainGeomCount: summary.scene?.terrainGeomCount || 0,
    terrainGeomNames: summary.scene?.terrainGeomNames || [],
    changedRuntime: summary.changedRuntime,
    visualOnly: summary.visualLayer?.visualOnly === true,
    visualCollision: summary.visualLayer?.collision || null,
    consoleErrors,
  };
  result.pass = Boolean(
    summary.pass &&
    result.preset === 'rough-terrain' &&
    /rough/i.test(result.activeScene || '') &&
    result.claimLevel === 'contact-bearing-scene' &&
    result.sceneMode === 'active-rough-scene-variant' &&
    result.contactBearingTerrain &&
    result.terrainGeomCount >= 3 &&
    result.changedRuntime === true &&
    result.visualOnly &&
    result.visualCollision === 'none-threejs-only' &&
    consoleErrors.length === 0
  );

  const outPath = join(OUT_DIR, `${exp}_${preset}_terrain_scene_summary.json`);
  writeFileSync(outPath, JSON.stringify(result, null, 2));
  await page.screenshot({ path: join(OUT_DIR, `${exp}_${preset}_terrain_scene.png`) });
  await browser.close();

  console.log(JSON.stringify(result, null, 2));
  console.log(`[qa] summary ${outPath}`);
  console.log(result.pass ? '[qa] PASS' : '[qa] FAIL');
  process.exitCode = result.pass ? 0 : 1;
}

main()
  .catch((error) => {
    console.error('[qa] ERROR', error);
    process.exitCode = 2;
  })
  .finally(() => {
    if (serverProc) serverProc.kill();
  });
