// Verifies G1 non-foot contact geoms and removal of the z-fighting visual floor overlay.
//
// Usage:
//   node qa/g1_contactbody_flicker_check.mjs
//   node qa/g1_contactbody_flicker_check.mjs --live

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const QA_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_DIR = dirname(QA_DIR);
const REPO_ROOT = resolve(WEB_DIR, '..', '..', '..');
const EVIDENCE_DIR = join(REPO_ROOT, 'experiments', '145-g1-contactbody-flicker-fix', 'verify');
const OUT_DIR = join(QA_DIR, 'out');
const args = process.argv.slice(2);
const live = args.includes('--live');
const PORT = 8144;
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
    const demo = window.demo;
    const model = demo.model;
    const decoder = new TextDecoder('utf-8');
    const nullChar = decoder.decode(new ArrayBuffer(1));
    function readName(addressArray, index) {
      return decoder.decode(model.names.subarray(addressArray[index])).split(nullChar)[0];
    }
    const geoms = [];
    for (let i = 0; i < model.ngeom; i++) {
      geoms.push({
        index: i,
        name: readName(model.name_geomadr, i),
        bodyId: model.geom_bodyid?.[i] ?? null,
        contype: model.geom_contype?.[i] ?? null,
        conaffinity: model.geom_conaffinity?.[i] ?? null,
        group: model.geom_group?.[i] ?? null,
      });
    }
    const required = ['pelvis_floor_collision', 'torso_floor_collision', 'head_floor_collision'];
    const requiredGeoms = required.map((name) => geoms.find((geom) => geom.name === name) || { name, missing: true });
    const footGeoms = geoms.filter((geom) => /foot/i.test(geom.name));
    const environment = demo.qaEnvironmentSummary();
    const visualObjects = environment.visualLayer?.objects || [];
    const visualFloorOverlayPresent = visualObjects.includes('Matte visual floor overlay');

    demo.params.paused = true;
    if (model.nq >= 7) {
      demo.data.qpos[0] = 0;
      demo.data.qpos[1] = 0;
      demo.data.qpos[2] = 0.20;
      demo.data.qpos[3] = 0.70710678;
      demo.data.qpos[4] = 0.70710678;
      demo.data.qpos[5] = 0;
      demo.data.qpos[6] = 0;
    }
    demo.mujoco.mj_forward(model, demo.data);
    for (let i = 0; i < 80; i++) demo.mujoco.mj_step(model, demo.data);
    demo.render(0);
    return {
      activeScene: environment.scene?.activeScene || null,
      requiredGeoms,
      requiredContactEligible: requiredGeoms.every((geom) => !geom.missing && geom.contype > 0 && geom.conaffinity > 0),
      footGeomNames: footGeoms.map((geom) => geom.name),
      visualObjects,
      visualFloorOverlayPresent,
      postFallProbe: {
        contactCount: Number(demo.data.ncon || 0),
        rootZ: Number(demo.data.qpos[2]),
        finiteRootZ: Number.isFinite(Number(demo.data.qpos[2])),
      },
      environmentPass: environment.pass === true,
    };
  });

  const evidence = {
    pass: Boolean(
      result.environmentPass &&
      result.requiredContactEligible &&
      result.requiredGeoms.length >= 3 &&
      result.footGeomNames.length >= 2 &&
      !result.visualFloorOverlayPresent &&
      result.postFallProbe.finiteRootZ &&
      result.postFallProbe.contactCount > 0 &&
      consoleErrors.length === 0
    ),
    live,
    targetUrl: url.toString(),
    consoleErrors,
    ...result,
    claimBoundary: 'Browser MuJoCo collision/rendering contract check; not a real robot collision validation.',
  };

  const suffix = live ? 'live' : 'local';
  const outPath = join(EVIDENCE_DIR, `g1-contactbody-flicker-fix-${suffix}.json`);
  writeFileSync(outPath, JSON.stringify(evidence, null, 2));
  await page.screenshot({ path: join(OUT_DIR, `g1_contactbody_flicker_${suffix}.png`) });
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
