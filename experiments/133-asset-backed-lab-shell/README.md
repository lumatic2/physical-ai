# M32 - Asset-backed Lab Shell

## What This Proves

Robotics Lab can load a local lightweight glTF lab shell into the public Three.js visual layer.

- Asset: `experiments/03-digital-twin/web/assets/lab/lab_shell.gltf`
- Buffer: `experiments/03-digital-twin/web/assets/lab/lab_shell.bin`
- Manifest: `experiments/03-digital-twin/web/assets/lab/lab_shell_manifest.json`

The asset is loaded asynchronously through `GLTFLoader` and reported in `qaEnvironmentSummary().assetLayer`.

## What This Does Not Prove

This is not photorealistic reconstruction. It is a lightweight visual shell and does not define MuJoCo collision geometry.

## Evidence

- Verify JSON: `verify/asset-lab-shell-smoke.json`
- QA summary: `experiments/03-digital-twin/web/qa/out/g1-walk_flat-lab_asset_shell_summary.json`

## Verification

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/asset_shell_check.mjs --exp=g1-walk --preset=flat-lab
```
