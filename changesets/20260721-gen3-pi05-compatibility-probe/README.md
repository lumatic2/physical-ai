# Changeset: GEN3 π₀.₅ compatibility probe

- Status: completed
- Target: ROADMAP `GEN3` step-1 — `pi05-compatibility-probe`

## Scope

- `runtime-lock.json`: OpenPI commit, LIBERO revision, π₀.₅-LIBERO checkpoint snapshot과 input/output shape 고정.
- `probe_pi05.py`: GEN2 actual canonical 관측을 공식 LIBERO transform으로 매핑하고 한 번의 실제 π₀.₅ inference 실행.
- `test_probe_pi05.py`: checkpoint/config, norm stats, image/state, action shape/finite와 deterministic input digest failure probe.
- `verify/pi05-probe-report.json`: 실제 RTX 5090 load/inference 결과와 claim boundary.

## Contract

- Input: GEN2 `libero_spatial/task-00/state-00/frame-000000`의 main+wrist camera, 8D state와 GEN1 instruction.
- Transform: 두 camera를 180° 회전한 뒤 224×224 padding-resize한다.
- Policy: OpenPI `15a9616…`, config `pi05_libero`, GCS snapshot `11e0f560…`만 허용한다.
- Output: 정확히 10×7이며 모든 값이 finite여야 한다.
- Claim boundary: 한 관측의 실제 호환성 증거이며 rollout 성공 또는 정책 순위가 아니다.

## Verification

- [x] RTX 5090을 JAX GPU device로 인식.
- [x] checkpoint 16개 object와 `12,439,085,481` bytes가 GEN1 metadata와 일치.
- [x] actual GEN2 dual-camera·8D state·instruction input digest `04572027…` 고정.
- [x] π₀.₅ actual inference가 finite 10×7 action chunk 생성.
- [x] 두 번째 clean process 기준 load `8.662s`, inference `12.872s` 기록.
- [x] wrong checkpoint config, missing norm stats, 10×8 action과 NaN action이 FAIL.
- [x] contract/negative test 7개와 Ruff E/F/I gate PASS.

## Result

π₀.₅-LIBERO의 정적 declared compatibility를 실제 checkpoint load와 action 생성 증거로 승격했다. OpenVLA와 달리 wrist camera와 8D state를 모델 입력으로 사용한다는 차이는 그대로 노출하며, 성능 비교는 60-cell rollout 이후로 제한한다.

## Sources

- [Physical-Intelligence/openpi pinned commit](https://github.com/Physical-Intelligence/openpi/tree/15a9616a00943ada6c20a0f158e3adb39df2ccac) (접근일: 2026-07-21)
- [OpenPI LIBERO evaluation example](https://github.com/Physical-Intelligence/openpi/tree/15a9616a00943ada6c20a0f158e3adb39df2ccac/examples/libero) (접근일: 2026-07-21)
- [OpenPI π₀.₅-LIBERO checkpoint documentation](https://github.com/Physical-Intelligence/openpi/blob/15a9616a00943ada6c20a0f158e3adb39df2ccac/README.md#model-checkpoints) (접근일: 2026-07-21)
