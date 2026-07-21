# BACKLOG

> Compressed milestone archive. ROADMAP.md is capped at 150 lines.

## Completed

### 2026-06
- M26 - Digital Twin Workbench Foundation
  - Completed: 2026-06-24
  - Result: Digital Twin Workbench panel and QA summary expose runtime mode, qpos contract, telemetry evidence, and gate status.
  - Evidence: experiments/127-digital-twin-workbench-foundation/verify/unitree-g1-elastic-stand-workbench-summary.json

### 2026-06
- M29 - M29 - Public drift audit
  - Completed: 2026-06-26
  - Result: Public drift audit found stale live deploy and Askewly project copy, with no real-telemetry overclaim.
  - Evidence: experiments/130-public-drift-audit/verify/public-drift-audit.json

### 2026-06
- M39 - Environment Scenario Manifest
  - Completed: 2026-06-26
  - Result: Scenario manifest/URL/UI/QA evidence가 `rough-curb-v1` contract를 local/live로 검증한다.
  - Evidence: experiments/140-environment-scenario-manifest/verify/environment-scenario-manifest.json

- M40 - Multi-Robot Environment Matrix
  - Completed: 2026-06-26
  - Result: G1/Go1/Spot x flat/rough 6-row matrix가 local/live에서 scenario shape와 claim boundary를 검증한다.
  - Evidence: experiments/141-multi-robot-environment-matrix/verify/environment-matrix-smoke.json

- M41 - Interactive Obstacle Scene
  - Completed: 2026-06-26
  - Result: `g1-obstacle-walk`와 `obstacle-lane-v1`이 active MJCF obstacle geoms, UI status, local/live smoke evidence로 검증된다.
  - Evidence: experiments/142-interactive-obstacle-scene/verify/obstacle-scene-smoke.json

- M42 - Randomized Episode Scorecard
  - Completed: 2026-06-26
  - Result: `obstacle-command-noise-v1` profile이 3개 command/control-noise episode를 local/live에서 실행하고 scorecard evidence로 검증한다.
  - Evidence: experiments/143-randomized-episode-scorecard/verify/randomized-episode-scorecard.json

- M43 - Randomized Episode Comparison
  - Completed: 2026-06-26
  - Result: `obstacle-command-noise-comparison-v1`이 baseline 대비 noisy/diagonal episode delta를 local/live evidence로 검증한다.
  - Evidence: experiments/144-randomized-episode-comparison/verify/randomized-episode-comparison.json

- M44 - G1 Contact Body & Flicker Fix
  - Completed: 2026-06-26
  - Result: G1 pelvis/torso/head floor-contact collision geoms를 추가하고 duplicate visual floor overlay를 제거했다. local/live QA에서 non-foot contact eligibility, overlay absence, post-fall contact probe가 PASS다.
  - Evidence: experiments/145-g1-contactbody-flicker-fix/verify/g1-contactbody-flicker-fix.json

### 2026-06
- M45 - Real Robot Collision Contract
  - Completed: 2026-06-26
  - Result: G1 pelvis/torso/head/feet collision readiness를 real-robot body zone, required telemetry, actuator stop gate, e-stop requirement, stop criteria로 매핑했다. local/live QA에서 sim envelope coverage와 hardware-unarmed gate가 PASS다.
  - Evidence: experiments/146-real-robot-collision-contract/verify/real-robot-collision-contract.json

### 2026-07
- GEN1 - 고정된 다과제 평가 계약
  - Completed: 2026-07-21
  - Result: 12 task×5 state×2 policy 평가 계약과 clean gate PASS.
  - Evidence: archive/reports/2026-07-21-gen1-multitask-evaluation-contract.md

- GEN2 - OpenVLA 다과제 기준선
  - Completed: 2026-07-21
  - Result: OpenVLA 60개 actual rollout과 aggregate gate PASS.
  - Evidence: archive/reports/2026-07-21-gen2-openvla-multitask-baseline.md

- GEN3 - 두 VLA의 공정 비교
  - Completed: 2026-07-21
  - Result: 두 VLA 60쌍의 실제 실행·paired 통계·공정성 경계를 완료했다.
  - Evidence: archive/reports/2026-07-21-gen3-paired-vla-comparison.md

- GEN4 - 증거 기반 실패 양상
  - Completed: 2026-07-21
  - Result: 27/27 non-success를 관측 가능한 양상 또는 unknown으로 완전 집계했다.
  - Evidence: archive/reports/2026-07-21-gen4-observable-failure-patterns.md

- GEN5 - 공개 일반화 비교 실험실
  - Completed: 2026-07-21
  - Result: 60 paired cell·120 episode·27 failure를 production reviewer path로 공개했다.
  - Evidence: archive/reports/2026-07-21-gen5-public-generalization-lab.md
