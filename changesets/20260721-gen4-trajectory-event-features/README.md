# Changeset: GEN4 trajectory and event features

- Status: completed
- Target: ROADMAP `GEN4` step-2 — `trajectory-event-features`

## Scope

- `extract_features.py`: 27개 timeout episode에서 trajectory·gripper·action·controller·camera evidence를 재계산한다.
- `test_extract_features.py`: denominator, camera/event, unit, NaN, raw-integrity 변이를 거부한다.
- `fixtures/invalid-feature-mutations.json`: feature consumer failure probes.
- `verify/features/failure-features.json`: classifier 입력이 되는 derived, content-hashed feature index.

## Contract

- Source of truth: GEN2 OpenVLA와 GEN3 π₀.₅ canonical manifest의 non-success rows와 raw local artifacts.
- Derived only: raw parquet/video/event/manifest는 읽기 전후 hash가 같아야 한다.
- Available: 8D robot state, 7D executed action, dual camera, controller acceptance event.
- Unavailable: object pose/contact와 task-specific goal distance는 `available=false`로 보존한다.
- No label promotion: 이 step은 feature만 만들고 failure pattern을 판정하지 않는다.

## Verification

- [x] canonical non-success 27개(OpenVLA 25, π₀.₅ 2) 전수 추출.
- [x] eef path/displacement, gripper/action, controller acceptance가 finite·typed unit이다.
- [x] dual-camera·trajectory·event source가 relative ref와 SHA-256를 가진다.
- [x] object relation/goal distance 미가용성이 null+reason으로 보존된다.
- [x] missing camera/event, unit mismatch, NaN, raw hash drift와 denominator omission이 FAIL한다.
- [x] actual extraction CLI, focused tests, Ruff와 diff gate PASS.

## Result

OpenVLA 25개와 π₀.₅ 2개 timeout의 27개 feature row를 전수 생성했다. end-effector net displacement는 0.167~0.426m, total path는 0.345~2.153m, terminal window displacement는 0.001~0.492m였다. 모든 episode에서 controller acceptance event가 존재하고 rejected event는 0이었다.

dual camera·trajectory·event는 각각 content hash와 relative ref를 가진다. object pose/contact와 task-specific goal distance는 canonical source에 없으므로 27개 모두 `available=false`와 이유를 기록했다. 추출 전후 raw hash는 모두 동일했고 feature row에 pattern label은 없다.
