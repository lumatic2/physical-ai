# Changeset: GEN1 policy compatibility registry

- Status: completed
- Target: ROADMAP `GEN1` step-3 — `policy-compatibility-registry`

## Scope

- `policy-registry.json`: OpenVLA/π0.5의 exact checkpoint, source, camera/state/action adapter 계약.
- `pi05-checkpoint-metadata.json`: 공개 GCS checkpoint 16개 object generation/CRC snapshot.
- `verify_policy_registry.py`, tests와 fixtures: 24개 task-policy pair와 mismatch 거부 gate.
- `verify/canonical/policy-registry-report.json`: registry canonical evidence.

## Contract

- Source of truth: `policy-registry.json`; task denominator는 `benchmark-manifest.json`.
- OpenVLA: suite별 HF revision 3개, main camera+instruction input, wrist/state observer-only, single 7D action.
- π0.5: openpi `15a9616…`, GCS snapshot `11e0f560…`, main+wrist+8D state+prompt, 10×32 model chunk에서 10×7 노출.
- Out of scope: π0.5 weight load, policy latency/success, adapter parity runtime; GEN3에서 실행한다.

## Verification

- [x] OpenVLA 3 suite checkpoint revision과 local adapter source hash PASS.
- [x] openpi revision/source hash와 π0.5 GCS 16-object snapshot PASS.
- [x] 12 task×2 policy=24 pair가 declared-compatible 또는 reasoned exclusion.
- [x] action dimension, wrist relabel, suite checkpoint mismatch fixture가 FAIL.
- [x] path/secret scrub, Python tests와 canonical report PASS.

## Result

OpenVLA suite별 HF revision 3개와 openpi source commit·4개 source hash를 고정했다. π0.5 checkpoint는 16개 GCS object의 generation·CRC·size를 snapshot SHA-256으로 묶고 live listing과 다시 대조했다. 24개 pair는 모두 정적 계약상 declared-compatible이며, 실제 load/rollout을 통과하기 전 성공 증거로 승격하지 않는다.
