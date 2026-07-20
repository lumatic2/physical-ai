# 20260721-lab1-bounded-official-viewer-smoke

## Target

- ROADMAP milestone: LAB1 — 카메라-행동 episode 계약.
- Plan leaf: `plans/2026-07-21-lab1-lerobot-episode-evidence.md` step-3.
- Goal: 고정 task·seed·OpenVLA revision의 bounded LIBERO episode를 생성하고 official LeRobot loader/profile/Rerun에서 같은 두 camera·state·action timeline을 검증한다.

## Planning Gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision:
    remote_background_agents: skip
    reason: "실제 WSL2 evaluator와 로컬 official viewer는 동일 dataset artifact를 순차 소비해야 하며 병렬 실행은 GPU·cache·process 충돌을 만든다."
    target_roles: []
    execution_path: local_manual
  spec_skip_reason: "ADR 0014와 승인 plan이 checkpoint·episode·Rerun 경계를 이미 고정했다."
  perspectives:
    product: "사람이 두 camera와 action/state를 실제 Rerun timeline에서 scrub할 수 있어야 한다."
    architecture: "canonical dataset과 RRD는 hash로 연결된 derived evidence다."
    security: "artifact summary에는 secret·absolute local path를 넣지 않는다."
    qa: "profile, loader, RRD verify, entity/timeline count와 변조 실패를 검사한다."
    skeptic: "synthetic smoke를 실제 OpenVLA 실행으로 오인하지 않고 checkpoint/seed/task provenance를 요구한다."
  role_lanes:
    explorer: "WSL2 OpenVLA/LIBERO와 official Rerun CLI의 현재 실행 상태를 확인한다."
    planner: "bounded rollout→dataset→RRD→summary 순서와 cleanup을 고정한다."
    reviewer: "실제 정책 실행 claim과 public reference replay를 구분한다."
    qa: "machine profile과 Rerun surface를 독립 재실행한다."
    gate: "dataset/RRD hashes와 entity/timeline evidence를 대조한다."
  dod:
    - "고정 task·seed·checkpoint bounded episode가 strict profile을 통과한다."
    - "official Rerun export와 rrd verify가 두 camera·state·action을 확인한다."
    - "dataset/sidecar/RRD hash를 묶은 machine-readable summary가 남는다."
    - "hash 또는 frame count 변조 fixture가 evidence gate에서 실패한다."
```

## Scope

| File/Path | Reason | Expected effect |
|---|---|---|
| `experiments/147-camera-action-episode-contract/verify_bounded_evidence.py` | dataset/RRD/hash gate | viewer evidence를 반복 검증한다. |
| `experiments/147-camera-action-episode-contract/test_verify_bounded_evidence.py` | 변조 failure regression | hash/frame claim drift를 막는다. |
| `experiments/147-camera-action-episode-contract/verify/bounded-smoke/` | bounded run summary와 RRD 검증 | step-4 canonical pair의 기준점을 만든다. |
| `experiments/01-vla-local-eval/` 실행 명령 | 실제 producer surface | mock과 실제 policy evidence를 구분한다. |
| `experiments/01-vla-local-eval/setup.sh`, `requirements.txt` | WSL producer 재현 환경 | Python 3.10과 reviewed LeRobot dataset runtime을 함께 설치한다. |

## Contract

- Source of truth: generated LeRobot dataset + strict provenance sidecar.
- Derived evidence: official Rerun RRD와 summary는 canonical hashes를 가리킨다.
- Compatibility: existing viewer-probe venv와 PyAV fallback을 재사용한다.
- Producer environment: WSL은 `PYTHON_BIN`으로 Python 3.10을 고정하고 LeRobot source는 `--no-deps`로 설치해 OpenVLA transformers pin을 보존한다.
- Deploy/operation: WSL2 OpenVLA server/client, Windows Rerun export를 모두 종료하고 listener/process를 검사한다.
- Out of scope: PASS/FAIL pair, model comparison, public UI.

## Verification

- [x] Producer surface: OpenVLA commit `962318c…`, LIBERO commit `8f1084e…`, seed 0에서 실제 action 3개와 dual camera recording PASS.
- [x] Dataset gate: strict profile와 official loader에서 frames=3, cameras=2, state=8D, action=7D PASS.
- [x] Rerun gate: official export와 `rrd verify`; main/wrist/state/action entity 및 frame/timestamp sorted timeline PASS.
- [x] Negative gate: frame count, RRD hash, missing entity 변조 회귀 4건이 예상대로 FAIL 판정.
- [x] Cleanup/diff: WSL server/client/listener 0, 중복 tmp와 실패 venv 정리, `git diff --check` PASS, tracked evidence 보존.

## Result

- Status: completed 2026-07-21
- Evidence: `experiments/147-camera-action-episode-contract/verify/bounded-smoke/` — canonical LeRobot dataset, official Rerun RRD, `openvla-report.json`, 재현 README.
- Observed: `producer_claim_ready=true`; dataset tree `678ae0b…`; RRD `92c3bf3…`; 첫 request 1683.653ms, 이후 211.380ms/202.956ms.
- Outcome boundary: 3 policy step bounded timeout이라 `success=false`가 맞다. 실제 OpenVLA inference와 simulation action 실행은 증명하지만 과제 성공·실물·live telemetry는 주장하지 않는다.
- Issues resolved:
  - 응답 불능 WSL을 사용자 승인 후 재시작해 `E_UNEXPECTED`를 해소했다.
  - setup의 Python 3.12, LeRobot dataset runtime, 비대화형 LIBERO config 누락을 고쳤다.
  - sidecar의 policy SHA만 기록하고 실제 model load를 pin하지 않던 provenance 결함을 `--ckpt-revision` end-to-end 전달로 막았다.
- Reviewer verdict:
  - Spec: PASS — 실제 producer와 synthetic 호환 smoke가 claim gate에서 분리되고 canonical dataset/RRD/hash가 남는다.
  - Quality: PASS — clean setup, early server failure, required revision, negative mutation과 process cleanup을 모두 검증했다.
