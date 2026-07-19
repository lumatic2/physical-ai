# 20260720-live-obstacle-release

## Target

- Goal: 커밋돼 있던 obstacle 렌더·성능 패치를 production에 배포하고 실제 화면 증거로 닫는다.
- ROADMAP milestone: maintenance — M44 후속 렌더 이슈 마감이며 새 Milestone을 만들지 않는다.

## Scope

| File/Path | Reason | Expected effect |
|-----------|--------|-----------------|
| `experiments/142-interactive-obstacle-scene/verify/obstacle-scene-smoke-{local,live}.json` | obstacle scene과 최신 렌더 성능 계약 재검증 | local/live evidence가 production 상태를 반영한다. |
| `experiments/145-g1-contactbody-flicker-fix/verify/g1-contactbody-flicker-fix-{local,live}.json` | floor overlay와 contact body 후속 검증 | 중복 visual floor 부재와 contact probe를 재확인한다. |
| `changesets/20260720-live-obstacle-release/README.md` | maintenance 실행·검증 기록 | 배포와 smoke의 완료 근거를 한곳에 남긴다. |

## Contract

- Source of truth: `experiments/03-digital-twin/web/src/main.js`, `experiments/03-digital-twin/web/src/mujocoUtils.js`, canonical `experiments.json`.
- Deploy/sync target: Vercel production `robotics.askewly.com`.
- Compatibility: 기존 MuJoCo WASM policy/physics loop와 QA summary 계약을 유지한다.
- Out of scope: 새 기능, 새 ROADMAP Milestone, 실물 로봇 collision 검증.

## Evidence Contract

- Scenario: `g1-obstacle-walk` + `obstacle-lane-v1` + debug UI.
- Expected evidence: obstacle smoke와 flicker check가 local/live 모두 PASS하고, 실제 브라우저에 큰 tendon/flex helper와 중복 floor overlay가 보이지 않는다.
- Failure mode probe: production bundle이 구 버전이면 `physicalTerrainOverlaySuppressed`와 `renderPerformance`가 evidence에 없거나 live smoke가 실패한다.
- Cleanup receipt: 검증용 Vite 프로세스 종료 후 `physical-ai` web Node 프로세스 0개.
- Not evidence: 시뮬레이션 collision contract는 실물 로봇 telemetry나 안전성 증명이 아니다.

## Verification

- [x] Targeted tests: `npm run build` PASS.
- [x] Smoke: obstacle/flicker local QA 모두 PASS.
- [x] Sync/deploy: Vercel deployment `dpl_DEDrjjwKXtTjLTh73w5dCAJJQk6e` READY, custom alias 갱신.
- [x] Deployed copy: obstacle/flicker live QA 모두 PASS, 브라우저 콘솔 오류 0개.
- [x] Drift/dirty-tree check: 검증용 Node 프로세스 0개, evidence와 changeset만 커밋 대상으로 확인.

## Result

- Status: completed
- Evidence: `experiments/142-interactive-obstacle-scene/verify/obstacle-scene-smoke-live.json`, `experiments/145-g1-contactbody-flicker-fix/verify/g1-contactbody-flicker-fix-live.json`
- Notes: balanced mode는 30fps render target과 shadow disabled를 보고하며, tendon/flex helper는 빈 모델에서 그려지지 않는다.
