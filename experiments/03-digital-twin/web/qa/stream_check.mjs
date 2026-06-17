import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const QA_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_DIR = dirname(QA_DIR);
const REPO_ROOT = resolve(WEB_DIR, '..', '..', '..');
const OUT_DIR = join(QA_DIR, 'out');
const WEB_PORT = 8132;
const STREAM_PORT = 8765;
const exp = (process.argv.find(a => a.startsWith('--exp=')) || '--exp=unitree-g1-headless').split('=')[1];
const targetFrames = parseInt((process.argv.find(a => a.startsWith('--frames=')) || '--frames=12').split('=')[1], 10);
const minFps = parseFloat((process.argv.find(a => a.startsWith('--min-fps=')) || '--min-fps=20').split('=')[1]);
const maxHeightRangeArg = process.argv.find(a => a.startsWith('--max-height-range='));
const maxHeightRange = maxHeightRangeArg ? parseFloat(maxHeightRangeArg.split('=')[1]) : null;
const trajectory = (process.argv.find(a => a.startsWith('--trajectory=')) ||
  '--trajectory=experiments/33-unitree-mujoco-g1-bridge-probe/verify/unitree-live-normalized-web-trajectory.json').split('=')[1];
const telemetry = (process.argv.find(a => a.startsWith('--telemetry=')) ||
  '--telemetry=experiments/33-unitree-mujoco-g1-bridge-probe/verify/unitree-live-normalized-telemetry-sidecar.json').split('=')[1];

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function waitForHttp(url, tries = 60) {
  for (let i = 0; i < tries; i++) {
    try { const r = await fetch(url); if (r.ok) return; } catch {}
    await sleep(200);
  }
  throw new Error(`server not up at ${url}`);
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  const web = spawn('python', ['serve_coi.py', String(WEB_PORT)], { cwd: WEB_DIR, stdio: 'ignore' });
  const stream = spawn('python', [
    'experiments/33-unitree-mujoco-g1-bridge-probe/stream_web_telemetry.py',
    '--trajectory', trajectory,
    '--telemetry', telemetry,
    '--port', String(STREAM_PORT),
    '--fps', '50',
  ], { cwd: REPO_ROOT, stdio: 'ignore' });

  try {
    await waitForHttp(`http://127.0.0.1:${WEB_PORT}/index.html`);
    await sleep(500);
    const browser = await chromium.launch({
      headless: true,
      args: ['--disable-background-timer-throttling', '--disable-renderer-backgrounding',
             '--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'],
    });
    const page = await browser.newPage({ viewport: { width: 1280, height: 960 } });
    const consoleErrors = [];
    page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
    page.on('pageerror', e => consoleErrors.push(String(e)));
    const url = `http://127.0.0.1:${WEB_PORT}/?exp=${exp}&stream=${encodeURIComponent(`ws://127.0.0.1:${STREAM_PORT}`)}`;
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await page.waitForFunction(() => window.demo && window.demo.model && window.demo.streamStats?.enabled,
      null, { timeout: 120000, polling: 250 });
    await page.waitForFunction(n => window.demo.streamStats.received >= n,
      targetFrames, { timeout: 120000, polling: 100 });
    const status = await page.evaluate(() => ({
      expName: window.demo.expName,
      stream: window.demo.qaStreamStatus(),
      readout: Array.from(document.querySelectorAll('.telemetry-readout span')).map(el => el.textContent),
      qpos0: Array.from(window.demo.data.qpos.slice(0, 7)),
    }));
    await page.screenshot({ path: join(OUT_DIR, `${exp}_stream.png`) });
    await browser.close();
    const pass = consoleErrors.length === 0 &&
      status.stream.enabled &&
      status.stream.received >= targetFrames &&
      status.stream.droppedOrOutOfOrder === 0 &&
      status.stream.measuredFps >= minFps &&
      (maxHeightRange === null || status.stream.heightRange <= maxHeightRange) &&
      status.stream.telemetry?.stream === true &&
      status.readout.some(text => text.startsWith('stream '));
    console.log(JSON.stringify({ verdict: pass ? 'PASS' : 'FAIL', consoleErrors, ...status }, null, 2));
    process.exitCode = pass ? 0 : 1;
  } finally {
    web.kill();
    stream.kill();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 2;
});
