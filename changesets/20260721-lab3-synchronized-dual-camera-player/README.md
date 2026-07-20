# 20260721-lab3-synchronized-dual-camera-player

## Target

- ROADMAP milestone: LAB3 — 공개 관찰형 로봇팔 실험실.
- Plan leaf: `plans/2026-07-21-lab3-public-observable-arm-lab.md` step-2.
- Goal: 주·손목 camera와 상태·행동 graph를 하나의 재생 시간과 frame cursor로 움직인다.

## Planning Gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision:
    remote_background_agents: skip
    reason: "별도 Vite entry 안의 player state와 video refs가 강결합된 단일 UI changeset이다."
    target_roles: []
    execution_path: local_manual
  perspectives:
    product: "첫 화면에서 실제 camera 두 개, 언어 지시, 결과, 공통 scrub, 상태·행동 값을 읽는다."
    architecture: "기존 MuJoCo entry를 보존하고 arm-lab.html 멀티페이지 entry로 분리한다."
    security: "step-1 registry의 allowlisted 상대 경로만 fetch한다."
    qa: "play/pause/seek/frame-step과 두 video·graph cursor의 시간 오차를 검사한다."
    skeptic: "observer-only wrist camera를 model input으로 부르지 않고 recorded simulation 경계를 첫 화면에 둔다."
  dod:
    - "두 video와 graph cursor가 같은 frame/time을 가리킨다."
    - "키보드와 range input으로 모든 playback 동작에 접근한다."
    - "desktop/mobile에서 source order와 주요 정보가 유지된다."
```

## Design Intake

- Source: `https://ui.askewly.com/llms/recipes/layout/responsive-content-grid.md` (accessed 2026-07-21).
- Code asset: `https://ui.askewly.com/r/responsive-content-grid.json` (accessed 2026-07-21).
- Adaptation: stable source order와 `min-w-0` collapse 계약만 이식하고 project `DESIGN.md` tokens와 evidence hierarchy로 다시 입혔다.
- Rejected: generic card copy, three-column decorative grid, nested card frames.

## Verification

- [x] Vite multi-page production build PASS.
- [x] Player local Playwright PASS: seek 3.0s→frame 30, FAIL 220-frame 전환, keyboard frame-step, camera/graph cursor sync delta 0.
- [x] Forced 0.75s desynchronized fixture를 QA가 FAIL로 거부하고 다음 main timeupdate에서 0.08s 이내로 복구.
- [x] Desktop/mobile screenshots, 390px horizontal overflow 0, stable source order, console error 0.
- [x] Askewly style signature self-judgment PASS: project tokens, small signal accent, one camera focal region, interaction states; left-accent card·emoji·한글 중간 잘림·무근거 장식 없음.

## Result

- Status: completed 2026-07-21
- Evidence: `qa/out/arm-lab/player-report.json`, `desktop.png`, `mobile.png` (local QA output, gitignored).
- Reviewer verdict: main/wrist video, scrubber와 inline SVG trace cursor가 하나의 React playback state에서 움직이며 recorded simulation·camera provenance가 첫 화면에 유지된다.
