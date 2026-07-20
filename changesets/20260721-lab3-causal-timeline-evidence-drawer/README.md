# 20260721-lab3-causal-timeline-evidence-drawer

## Target

- ROADMAP milestone: LAB3 — 공개 관찰형 로봇팔 실험실.
- Plan leaf: `plans/2026-07-21-lab3-public-observable-arm-lab.md` step-3.
- Goal: 현재 frame의 관찰·판단·행동·결과를 실제 source/parent/assistance와 연결하고 원문 evidence까지 내려간다.

## Planning Gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision:
    remote_background_agents: skip
    reason: "player의 현재 frame, selected event와 drawer provenance가 하나의 consumer state로 결합된다."
    target_roles: []
    execution_path: local_manual
  perspectives:
    product: "VLM/VLA의 차이와 실제 행동 생성 주체를 사전지식 없이 읽을 수 있어야 한다."
    architecture: "public event 문서는 read-only이며 selected event가 camera/chart timestep과 parent chain을 공유한다."
    security: "hidden reasoning, unknown source, broken parent와 claim/camera relabel을 client contract에서도 거부한다."
    qa: "lane 전환, event click/seek, parent/source/assistance, raw link와 drawer keyboard dismissal을 검사한다."
    skeptic: "VLM skill selection 뒤의 canonical scripted controller를 모델 행동으로 둔갑시키지 않는다."
  dod:
    - "direct VLA와 VLM→skill lane의 실제 source/assistance 차이가 보인다."
    - "selected event가 frame, parents, component revision과 raw artifact를 가리킨다."
    - "free-form chain-of-thought 없이 구조화된 관찰·결정·행동·결과만 표시한다."
```

## Verification

- [x] Claim contract PASS: fail/pass × direct_vla/vlm_skill 4 streams; hidden reasoning, unknown source, live/real claim과 camera relabel negative probes 거부.
- [x] Timeline/drawer local Playwright PASS: VLM lane, parent/assistance, 4 raw links, native dialog Escape dismissal.
- [x] Vite multi-page build PASS, browser console error 0.
- [x] Askewly style signature PASS; desktop dark/light, drawer dark와 mobile dark screenshot을 직접 검토하고 390px overflow 0 확인.

## Result

- Status: completed 2026-07-21
- Evidence: `qa/out/arm-lab/player-report.json`, `desktop-dark.png`, `desktop-light.png`, `drawer-dark.png`, `mobile-dark.png` (local QA output, gitignored).
- Reviewer verdict: 현재 camera/chart frame과 source-tagged event, causal parents, component revision, assistance와 raw artifact가 연결되며 VLM skill 선택을 scripted controller action으로 둔갑시키지 않는다.
