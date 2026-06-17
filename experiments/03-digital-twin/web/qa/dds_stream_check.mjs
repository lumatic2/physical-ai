import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const QA_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_DIR = dirname(QA_DIR);
const REPO_ROOT = resolve(WEB_DIR, '..', '..', '..');
const OUT_DIR = join(QA_DIR, 'out');
const WEB_PORT = parseInt((process.argv.find(a => a.startsWith('--web-port=')) || '--web-port=8134').split('=')[1], 10);
const STREAM_PORT = parseInt((process.argv.find(a => a.startsWith('--stream-port=')) || '--stream-port=8886').split('=')[1], 10);
const domainId = parseInt((process.argv.find(a => a.startsWith('--domain-id=')) || '--domain-id=21').split('=')[1], 10);
const exp = (process.argv.find(a => a.startsWith('--exp=')) || '--exp=unitree-g1-elastic-stand').split('=')[1];
const targetFrames = parseInt((process.argv.find(a => a.startsWith('--frames=')) || '--frames=60').split('=')[1], 10);
const publisherFrames = parseInt((process.argv.find(a => a.startsWith('--publisher-frames=')) || '--publisher-frames=160').split('=')[1], 10);
const minFps = parseFloat((process.argv.find(a => a.startsWith('--min-fps=')) || '--min-fps=15').split('=')[1]);
const maxHeightRangeArg = process.argv.find(a => a.startsWith('--max-height-range='));
const maxHeightRange = maxHeightRangeArg ? parseFloat(maxHeightRangeArg.split('=')[1]) : null;
const sdkPath = (process.argv.find(a => a.startsWith('--sdk-path=')) || `--sdk-path=${process.env.UNITREE_SDK2_PYTHON || ''}`).split('=').slice(1).join('=');
const unitreeRoot = (process.argv.find(a => a.startsWith('--unitree-root=')) || `--unitree-root=${process.env.UNITREE_MUJOCO_ROOT || ''}`).split('=').slice(1).join('=');
const elasticBand = !process.argv.includes('--no-elastic-band');
const artifactLabel = (process.argv.find(a => a.startsWith('--label=')) || `--label=${elasticBand ? 'elastic' : 'collapse'}`).split('=')[1];
const publisherMode = (process.argv.find(a => a.startsWith('--publisher=')) || '--publisher=unitree-mujoco').split('=')[1];

if (!sdkPath || (publisherMode === 'unitree-mujoco' && !unitreeRoot)) {
  console.error('Missing --sdk-path/--unitree-root or UNITREE_SDK2_PYTHON/UNITREE_MUJOCO_ROOT.');
  process.exit(2);
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function waitForHttp(url, tries = 60) {
  for (let i = 0; i < tries; i++) {
    try { const r = await fetch(url); if (r.ok) return; } catch {}
    await sleep(200);
  }
  throw new Error(`server not up at ${url}`);
}

function collect(proc, name) {
  let stdout = '';
  let stderr = '';
  proc.stdout?.on('data', d => { stdout += d.toString(); });
  proc.stderr?.on('data', d => { stderr += d.toString(); });
  return {
    dump() {
      writeFileSync(join(OUT_DIR, `${name}_stdout.txt`), stdout);
      writeFileSync(join(OUT_DIR, `${name}_stderr.txt`), stderr);
    },
    stdout() { return stdout; },
    stderr() { return stderr; },
  };
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  const web = spawn('python', ['serve_coi.py', String(WEB_PORT)], { cwd: WEB_DIR, stdio: 'ignore' });
  const bridge = spawn('python', [
    'experiments/33-unitree-mujoco-g1-bridge-probe/stream_dds_to_websocket.py',
    '--sdk-path', sdkPath,
    '--domain-id', String(domainId),
    '--port', String(STREAM_PORT),
    '--fps', '50',
  ], { cwd: REPO_ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
  const bridgeLogs = collect(bridge, 'dds_bridge');

  let publisher = null;
  let publisherLogs = null;
  if (publisherMode === 'unitree-mujoco') {
    const publisherArgs = [
      'experiments/33-unitree-mujoco-g1-bridge-probe/publish_unitree_mujoco_g1_dds.py',
      '--sdk-path', sdkPath,
      '--unitree-root', unitreeRoot,
      '--frames', String(publisherFrames),
      '--fps', '50',
      '--domain-id', String(domainId),
      '--warmup-s', '0.5',
    ];
    if (elasticBand) {
      publisherArgs.push('--elastic-band', '--band-length', '0.5', '--band-stiffness', '200', '--band-damping', '100');
    }
    publisher = spawn('python', publisherArgs, { cwd: REPO_ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
    publisherLogs = collect(publisher, 'dds_publisher');
  } else if (publisherMode !== 'external') {
    console.error(`Unsupported --publisher=${publisherMode}`);
    process.exit(2);
  }

  try {
    await waitForHttp(`http://127.0.0.1:${WEB_PORT}/index.html`);
    await sleep(800);
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
    await page.screenshot({ path: join(OUT_DIR, `${exp}_${artifactLabel}_dds_stream.png`) });
    await browser.close();
    const pass = consoleErrors.length === 0 &&
      status.stream.enabled &&
      status.stream.received >= targetFrames &&
      status.stream.droppedOrOutOfOrder === 0 &&
      status.stream.measuredFps >= minFps &&
      (maxHeightRange === null || status.stream.heightRange <= maxHeightRange) &&
      status.stream.telemetry?.stream === true &&
      status.readout.some(text => text.startsWith('stream '));
    const summary = { verdict: pass ? 'PASS' : 'FAIL', domainId, streamPort: STREAM_PORT, publisherMode, elasticBand, consoleErrors, ...status };
    writeFileSync(join(OUT_DIR, `${exp}_${artifactLabel}_dds_stream_summary.json`), JSON.stringify(summary, null, 2));
    console.log(JSON.stringify(summary, null, 2));
    process.exitCode = pass ? 0 : 1;
  } finally {
    web.kill();
    bridge.kill();
    publisher?.kill();
    bridgeLogs.dump();
    publisherLogs?.dump();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 2;
});
