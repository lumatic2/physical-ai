# Changesets

| # | Changeset | 날짜 | Scope | Verification | Status |
|---|-----------|------|-------|--------------|--------|
| 1 | [20260720-live-obstacle-release](20260720-live-obstacle-release/README.md) | 2026-07-20 | obstacle 렌더·성능 패치 production 배포와 evidence 갱신 | 5/5 | completed |
| 2 | [20260721-lab1-official-viewer-reuse-probe](20260721-lab1-official-viewer-reuse-probe/README.md) | 2026-07-21 | LeRobot dual-camera episode의 Rerun/Foxglove/UI 재사용률 측정 | 5/5 | completed |
| 3 | [20260721-lab1-canonical-contract-profile](20260721-lab1-canonical-contract-profile/README.md) | 2026-07-21 | LeRobot v3 canonical episode와 provenance sidecar profile 고정 | 5/5 | completed |
| 4 | [20260721-lab1-libero-lerobot-writer](20260721-lab1-libero-lerobot-writer/README.md) | 2026-07-21 | LIBERO observation/action을 official LeRobot writer로 저장 | 5/5 | completed |
| 5 | [20260721-lab1-bounded-official-viewer-smoke](20260721-lab1-bounded-official-viewer-smoke/README.md) | 2026-07-21 | 고정 OpenVLA/LIBERO episode와 official Rerun smoke | 5/5 | completed |
| 6 | [20260721-lab1-canonical-pass-fail-pair](20260721-lab1-canonical-pass-fail-pair/README.md) | 2026-07-21 | 동일 task/policy의 canonical PASS·FAIL episode pair | 5/5 | completed |
| 7 | [20260721-lab2-provenance-event-contract](20260721-lab2-provenance-event-contract/README.md) | 2026-07-21 | 판단·행동 event의 출처·인과·assistance 계약 | 5/5 | completed |
| 8 | [20260721-lab2-direct-vla-causal-emitter](20260721-lab2-direct-vla-causal-emitter/README.md) | 2026-07-21 | 실제 OpenVLA input→action→outcome 인과 event | 5/5 | completed |
| 9 | [20260721-lab2-vlm-bounded-skill-lane](20260721-lab2-vlm-bounded-skill-lane/README.md) | 2026-07-21 | local VLM 관측·skill 선택과 assisted LIBERO 실행 | 5/5 | completed |
| 10 | [20260721-lab2-two-lane-comparison-evidence](20260721-lab2-two-lane-comparison-evidence/README.md) | 2026-07-21 | direct VLA와 VLM→skill 실제 PASS/FAIL 통합 비교 | 5/5 | completed |
| 11 | [20260721-lab3-public-evidence-bundle](20260721-lab3-public-evidence-bundle/README.md) | 2026-07-21 | LAB1/LAB2 정본의 content-hashed 공개 replay bundle | 6/6 | completed |
| 12 | [20260721-lab3-synchronized-dual-camera-player](20260721-lab3-synchronized-dual-camera-player/README.md) | 2026-07-21 | dual camera·state/action 공통 playback 시간축 | 5/5 | completed |
| 13 | [20260721-lab3-causal-timeline-evidence-drawer](20260721-lab3-causal-timeline-evidence-drawer/README.md) | 2026-07-21 | source·parent·assistance 인과 timeline과 raw evidence drawer | 4/4 | completed |
| 14 | [20260721-lab3-public-reviewer-gate](20260721-lab3-public-reviewer-gate/README.md) | 2026-07-21 | human visual gate, production route와 live evidence | 4/4 | completed |
| 15 | [20260721-gen1-suite-task-slice](20260721-gen1-suite-task-slice/README.md) | 2026-07-21 | LIBERO 3 suite × 4 task의 revision·language·BDDL hash 고정 | 5/5 | completed |
| 16 | [20260721-gen1-initial-state-contract](20260721-gen1-initial-state-contract/README.md) | 2026-07-21 | task별 5개 initial-state tensor와 반복 reset fingerprint 고정 | 5/5 | completed |
| 17 | [20260721-gen1-policy-compatibility-registry](20260721-gen1-policy-compatibility-registry/README.md) | 2026-07-21 | OpenVLA/π0.5의 exact artifact와 camera/state/action 차이 고정 | 5/5 | completed |
| 18 | [20260721-gen1-multitask-result-contract](20260721-gen1-multitask-result-contract/README.md) | 2026-07-21 | 120개 immutable run key와 terminal result evidence schema 고정 | 5/5 | completed |
| 19 | [20260721-gen1-clean-contract-gate](20260721-gen1-clean-contract-gate/README.md) | 2026-07-21 | 12×5×2 평가 계약의 통합·변이·clean checkout gate | 5/5 | completed |
| 20 | [20260721-gen2-manifest-driven-runner](20260721-gen2-manifest-driven-runner/README.md) | 2026-07-21 | GEN1 OpenVLA 60 cell의 exact dry-run과 단일-cell 실행 명령 | 5/5 | completed |
| 21 | [20260721-gen2-resumable-run-ledger](20260721-gen2-resumable-run-ledger/README.md) | 2026-07-21 | append-only attempt, explicit retry와 sealed artifact 승격 gate | 5/5 | completed |
| 22 | [20260721-gen2-canonical-episode-export](20260721-gen2-canonical-episode-export/README.md) | 2026-07-21 | LAB1/LAB2 evidence를 GEN2 run key의 sealed episode로 승격 | 5/5 | completed |
| 23 | [20260721-gen2-sixty-cell-execution](20260721-gen2-sixty-cell-execution/README.md) | 2026-07-21 | RTX 5090에서 OpenVLA 60 cell 실행·seal·전수 hash 검증 | 6/6 | completed |
| 24 | [20260721-gen2-baseline-aggregate-gate](20260721-gen2-baseline-aggregate-gate/README.md) | 2026-07-21 | 60-cell outcome·frames·latency 재계산과 raw trace gate | 6/6 | completed |
| 25 | [20260721-gen3-pi05-compatibility-probe](20260721-gen3-pi05-compatibility-probe/README.md) | 2026-07-21 | 고정 π0.5 checkpoint의 actual GEN2 관측→10×7 action 호환성 | 7/7 | completed |
| 26 | [20260721-gen3-shared-policy-adapter-gate](20260721-gen3-shared-policy-adapter-gate/README.md) | 2026-07-21 | 두 VLA의 입력·전처리·chunk·gripper 차이를 노출한 60-pair adapter 계약 | 6/6 | completed |
| 27 | [20260721-gen3-pi05-sixty-cell-execution](20260721-gen3-pi05-sixty-cell-execution/README.md) | 2026-07-21 | π₀.₅ 60개 cell 실행·sealed episode·전수 hash 검증 | 6/6 | completed |
| 28 | [20260721-gen3-paired-statistics](20260721-gen3-paired-statistics/README.md) | 2026-07-21 | 두 60-cell 정본의 raw count·paired difference·bootstrap interval | 6/6 | completed |
| 29 | [20260721-gen3-fairness-and-claim-gate](20260721-gen3-fairness-and-claim-gate/README.md) | 2026-07-21 | exact provenance·retry/exclusion·claim boundary 통합 gate | 6/6 | completed |
| 30 | [20260721-gen4-failure-pattern-contract](20260721-gen4-failure-pattern-contract/README.md) | 2026-07-21 | 관측 가능한 실패 양상·predicate·canonical pointer 계약 | 6/6 | completed |
