import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const QA_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_DIR = dirname(QA_DIR);
const OUT_DIR = join(QA_DIR, 'out');
const PORT = 8132;
const BASE = `http://127.0.0.1:${PORT}`;

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

function pngInfo(bytes) {
  const sig = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
  for (let i = 0; i < sig.length; i++) {
    if (bytes[i] !== sig[i]) throw new Error('not a PNG');
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  return {
    width: view.getUint32(16),
    height: view.getUint32(20),
  };
}

let serverProc = null;

async function checkAsset(path, expectedSize) {
  const response = await fetch(`${BASE}${path}`);
  const bytes = new Uint8Array(await response.arrayBuffer());
  const info = pngInfo(bytes);
  return {
    path,
    status: response.status,
    bytes: bytes.byteLength,
    ...info,
    pass: response.ok && info.width === expectedSize && info.height === expectedSize,
  };
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  serverProc = spawnDevServer();
  await waitForServer(`${BASE}/index.html`);
  const assets = [
    await checkAsset('/assets/favicon.png', 256),
    await checkAsset('/assets/robotics-lab-icon-512.png', 512),
  ];
  const summary = {
    pass: assets.every((asset) => asset.pass),
    assets,
  };
  writeFileSync(join(OUT_DIR, 'favicon_check_summary.json'), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary, null, 2));
  console.log(summary.pass ? '[qa] PASS' : '[qa] FAIL');
  process.exitCode = summary.pass ? 0 : 1;
}

main()
  .catch((error) => {
    console.error('[qa] ERROR', error);
    process.exitCode = 2;
  })
  .finally(() => {
    if (serverProc) serverProc.kill();
  });
