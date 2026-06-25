// Verifies that the lightweight glTF lab shell asset lazy-loads into the visual layer.
//
// Usage:
//   node qa/asset_shell_check.mjs --exp=g1-walk --preset=flat-lab

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
const exp = (args.find((a) => a.startsWith('--exp=')) || '--exp=g1-walk').split('=')[1];
const preset = (args.find((a) => a.startsWith('--preset=')) || '--preset=flat-lab').split('=')[1];
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
  await page.waitForFunction(() => window.demo.qaEnvironmentSummary().assetLayer?.loaded === true, null, {
    timeout: 30000,
    polling: 250,
  });

  const summary = await page.evaluate(() => window.demo.qaEnvironmentSummary());
  const result = {
    experiment: exp,
    requestedPreset: preset,
    preset: summary.preset,
    activeScene: summary.scene?.activeScene || null,
    assetLayer: summary.assetLayer,
    visualLayer: summary.visualLayer,
    consoleErrors,
  };
  result.pass = Boolean(
    summary.pass &&
    result.assetLayer?.loaded === true &&
    result.assetLayer?.path === 'assets/lab/lab_shell.gltf' &&
    result.assetLayer?.objectCount >= 1 &&
    result.assetLayer?.error === null &&
    result.visualLayer?.collision === 'none-threejs-only' &&
    consoleErrors.length === 0
  );

  const outPath = join(OUT_DIR, `${exp}_${preset}_asset_shell_summary.json`);
  writeFileSync(outPath, JSON.stringify(result, null, 2));
  await page.screenshot({ path: join(OUT_DIR, `${exp}_${preset}_asset_shell.png`) });
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
