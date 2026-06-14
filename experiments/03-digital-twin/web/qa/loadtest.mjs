// Verify a bundled scene compiles in mujoco-js@0.0.7 (the web wasm). Usage: node qa/loadtest.mjs g1/scene_g1_policy.xml
import load_mujoco from '../node_modules/mujoco-js/dist/mujoco_wasm.js';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
const rel = process.argv[2];
const SCENES = join(process.cwd(), 'assets', 'scenes');
const modelDir = rel.split('/')[0];
const mujoco = await load_mujoco();
mujoco.FS.mkdir('/working'); mujoco.FS.mount(mujoco.MEMFS, { root: '.' }, '/working');
function walk(dir, base) {
  for (const f of readdirSync(dir)) {
    const p = join(dir, f), r = (base ? base + '/' : '') + f;
    if (statSync(p).isDirectory()) { try { mujoco.FS.mkdir('/working/' + r); } catch {} walk(p, r); }
    else mujoco.FS.writeFile('/working/' + r, new Uint8Array(readFileSync(p)));
  }
}
try { mujoco.FS.mkdir('/working/' + modelDir); } catch {}
walk(join(SCENES, modelDir), modelDir);
try {
  const model = mujoco.MjModel.loadFromXML('/working/' + rel);
  console.log('WASM OK nq=', model.nq, 'nu=', model.nu, 'nsensor=', model.nsensor);
} catch (e) { console.log('WASM THREW:', e && e.message ? e.message : e); }
