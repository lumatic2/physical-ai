# 20260721-lab3-public-evidence-bundle

## Target

- ROADMAP milestone: LAB3 — 공개 관찰형 로봇팔 실험실.
- Plan leaf: `plans/2026-07-21-lab3-public-observable-arm-lab.md` step-1.
- Goal: LAB1/LAB2 정본을 수정하지 않고 브라우저가 읽는 content-hashed 공개 증거 bundle을 결정론적으로 만든다.

## Planning Gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision:
    remote_background_agents: skip
    reason: "canonical episode와 causal trace를 하나의 공개 registry로 변환하는 단일 changeset이다."
    target_roles: []
    execution_path: local_manual
  perspectives:
    product: "PASS/FAIL 모두 주·손목 camera, 지시, 상태·행동, 두 event lane을 같은 밀도로 제공한다."
    architecture: "LAB1/LAB2가 정본이고 assets/arm-lab은 언제든 다시 만드는 파생물이다."
    security: "allowlist, content hash, 크기 제한, local path/token scrub을 build 전에 적용한다."
    qa: "byte identity, missing media, hash drift, secret/path, unknown source failure probe를 실행한다."
    skeptic: "손목 camera를 model input으로 둔갑시키거나 recorded simulation을 live/real로 부르지 않는다."
  dod:
    - "동일 입력에서 byte-identical bundle과 registry hash를 만든다."
    - "모든 공개 artifact가 size/hash/reference 검사를 통과한다."
    - "민감 경로·token·지원하지 않는 source·잘못된 claim을 거부한다."
```

## Verification

- [x] Converter unit tests 6/6 PASS.
- [x] Generated bundle verify-only PASS: 13 files, 2,897,274 bytes, registry SHA-256 `6d1a09eaea764d7be11fb70920cf83e04d5c5f83e02e4da78ab37062f4531140`.
- [x] Python compile와 `git diff --check` PASS.

## Result

- Status: completed 2026-07-21
- Evidence: `experiments/03-digital-twin/web/assets/arm-lab/registry.json`.
- Reviewer verdict: canonical 정본을 변경하지 않는 공개 파생 bundle이 camera provenance와 recorded-simulation claim을 보존하고, 변조·민감값·지원하지 않는 source를 build 전에 거부한다.
