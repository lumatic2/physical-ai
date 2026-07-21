# Changeset: GEN2 canonical episode export

- Status: completed
- Target: ROADMAP `GEN2` step-3 — `canonical-episode-export`

## Scope

- `episode_export.py`: LAB1 episode와 LAB2 direct-VLA event를 run key에 대조하고 atomic sealed manifest 생성.
- `test_episode_export.py`: 정본 seal·ledger 승격과 camera/action/path 변이 검사.
- `verify_episode_export.py`, `verify/episode-export-report.json`: 기존 실제 PASS episode의 exporter proof.

## Contract

- Identity: suite/task/state, environment/policy/adapter revision이 GEN1 run key와 일치한다.
- Observation: main camera는 OpenVLA model input, wrist camera는 observer-only이며 8D state와 timestamp가 존재한다.
- Action: 모든 frame의 raw 7D proposal이 executed 7D action hash와 controller event로 이어진다.
- Promotion: success/timeout bundle만 atomic sealed manifest가 되고, 그 hash로 동일 ledger attempt를 완료한다.
- Public safety: manifest에는 local input path 대신 relative artifact ref와 content hash만 남는다.

## Verification

- [x] 기존 실제 OpenVLA PASS 78 frame / 235 causal event seal PASS.
- [x] dual camera, state `[8]`, action `[7]`, raw→executed link와 outcome PASS.
- [x] manifest single-write+fsync+atomic rename 뒤 matching ledger terminal 승격 PASS.
- [x] wrist camera model-input relabel, executed action 누락, local path leak가 FAIL.
- [x] canonical report path/secret scrub PASS.

## Result

GEN2 runner가 생성할 각 valid rollout은 LAB1/LAB2 증거 계약을 복제하지 않고 재사용해 sealed episode가 된다. proof에는 기존 LAB1/LAB2 실제 PASS를 사용했으며 새 rollout은 아직 실행하지 않았다.
