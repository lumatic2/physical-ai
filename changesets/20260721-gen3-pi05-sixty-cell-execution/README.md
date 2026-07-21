# Changeset: GEN3 π₀.₅ 60-cell execution

- Status: completed
- Target: ROADMAP `GEN3` step-3 — `pi05-sixty-cell-execution`

## Scope

- `execute_pi05.py`: GEN1의 고정된 π₀.₅ 60개 cell을 하나의 persistent OpenPI server로 순차 실행하고 append-only ledger로 재개한다.
- `pi05_client.py`: 정확한 LIBERO task/state를 reset하고 official OpenPI 전처리·websocket action chunk를 사용해 dual-camera·8D state·7D executed action을 LeRobot episode로 기록한다.
- `pi05_evidence.py`: request/chunk/action/outcome event와 provenance sidecar를 원 episode에서 재계산해 sealed manifest로 승격한다.
- `verify_pi05_execution.py`: ledger, manifest, dataset tree, sidecar, event stream을 60개 cell 전수 재검증하고 canonical index를 만든다.
- GEN2 `run_ledger.py`와 schema: policy id를 명시적으로 받아 OpenVLA와 π₀.₅가 같은 append-only 규약을 재사용한다.

## Contract

- Source of truth: GEN1 π₀.₅ denominator, exact OpenPI revision `15a9616a…`, checkpoint snapshot `11e0f560…`, raw append-only ledger와 sealed episode다.
- Runtime: OpenPI server는 repo 밖 WSL 환경에서 실행하며 tracked artifact에는 cache 절대경로를 넣지 않는다.
- Resume: infrastructure attempt는 policy result와 분리해 보존하고, sealed policy result는 숨은 재시도로 덮어쓰지 않는다.
- Evidence: main+wrist camera와 8D state는 model input이며, 10×7 chunk 중 5 step을 실행한 뒤 재계획한 request/chunk 관계를 기록한다.
- Claim boundary: 실제 π₀.₅-LIBERO simulation rollout 증거이며 OpenVLA와의 우열이나 실물 telemetry를 아직 주장하지 않는다.

## Verification

- [x] ledger policy-id 일반화와 retry/infrastructure 분리 테스트 6개 통과.
- [x] 60개 고정 cell·resume·client command 계약 테스트 3개 통과.
- [x] camera/state/chunk/action causal evidence 변이 테스트 4개 통과.
- [x] missing/duplicate/relabel/invalid-attempt canonical index 변이 테스트 4개 통과.
- [x] 60/60 terminal cell과 raw artifact 전수 hash 재계산 PASS.
- [x] runner, policy server, client process cleanup PASS.

## Result

RTX 5090의 WSL runtime에서 π₀.₅ 60개 cell을 모두 실행했다. 결과는 58 success·2 timeout, 7,608 frames, 1,545 policy requests이며 각 suite가 정확히 20개다. append-only ledger에는 62 attempts가 남는다. 첫 cell의 `LIBERO` import 경로 누락과 PyTorch 2.6 `weights_only=True` 기본값 때문에 생긴 infrastructure error 2건은 policy 결과와 분리했고, 고정된 로컬 LIBERO init만 `weights_only=False`로 읽도록 복구한 뒤 60개 결과를 덮어쓰기 없이 봉인했다.

`openpi-client` editable 설치가 평가 venv의 NumPy를 1.26으로 내리려 한 near-miss는 2.2.6으로 복구하고 실제 client import·rollout으로 확인했다. 완료 직전에는 보조 monitor 셸 하나가 cleanup gate에 걸렸고, 정책 runner와 무관한 해당 PID만 종료한 뒤 process-clean verifier를 재실행해 PASS했다.

## Sources

- [OpenPI LIBERO policy adapter](https://github.com/Physical-Intelligence/openpi/blob/15a9616a00943ada6c20a0f158e3adb39df2ccac/src/openpi/policies/libero_policy.py) (접근일: 2026-07-21)
- [OpenPI LIBERO evaluation client](https://github.com/Physical-Intelligence/openpi/blob/15a9616a00943ada6c20a0f158e3adb39df2ccac/examples/libero/main.py) (접근일: 2026-07-21)
- [OpenPI policy server](https://github.com/Physical-Intelligence/openpi/blob/15a9616a00943ada6c20a0f158e3adb39df2ccac/scripts/serve_policy.py) (접근일: 2026-07-21)
