# M35 Claim Audit

Date: 2026-06-26

## Scope

- `README.md`
- `experiments/README.md`
- `ROADMAP.md`
- M33 evidence: `experiments/134-user-controllable-digital-twin/verify/control-smoke.json`
- M34 evidence: `experiments/135-mujoco-contact-force-readout/verify/contact-readout-probe.json`

## Findings

1. Root README still described the browser demo mainly as a policy gallery up to M17. It did not mention M27-M34 Robotics Lab workbench evidence: React shell, environment controls, asset-backed lab shell, visible command status, and MuJoCo readout probe.
2. Root README said keyboard command changes exist, but did not cite the new local/live command smoke artifact that proves `g1-walk` down/release transitions and visible UI.
3. Root README mentioned rough terrain QA, but did not distinguish contact-bearing scene evidence from read-only runtime fields. M34 should be described as `ncon`/`contact`/`cfrc_ext`/`sensordata` browser readout availability, not as a new force-control claim.
4. `experiments/README.md` stopped its public workbench index at M30-era audit entries. M31-M35 evidence rows were missing.

## Claim Boundary

- Allowed: browser MuJoCo WASM, learned ONNX policy, keyboard policy command input, contact-bearing rough MJCF scene, read-only runtime readout probe.
- Not allowed: real robot telemetry, unassisted real-world control, new physics engine, fake visual contact cues, force-control success claim.
