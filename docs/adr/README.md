# Architecture Decision Records

Michael Nygard ADR 포맷. 굵직한 의사결정·의도적 비활성·외부 제약을 보존.

각 ADR: Status / Context / Decision / Consequences. 한 번 쓰면 본문 수정 X
(supersede 만 허용). 자세한 가이드:
~/projects/agent-orchestration/docs/adr/README.md

## 인덱스
- [0001 — VLA 동작 표현(action representation) 분류 정의](0001-vla-action-representation.md) — Accepted 2026-06-09
- [0002 — ACT 실측은 M4 아닌 M6](0002-act-deferred-to-m6.md) — Accepted 2026-06-10
- [0003 — 2번째 정책은 별도 하네스·동일 벤치마크](0003-second-policy-separate-harness.md) — Accepted 2026-06-10
- [0004 — M6 디지털 트윈 스택: SO-100 MJCF + MuJoCo WASM 웹 replay](0004-digital-twin-stack.md) — Accepted 2026-06-12
- [0005 — 트윈을 학습 정책 sandbox로: 직접 학습한 사족보행 정책 브라우저 추론 (A+B)](0005-learned-policy-sandbox.md) — Accepted 2026-06-12
- [0006 — 확장 가능한 트윈 플랫폼: 단일 소스 config + 한 커맨드 파이프라인 + 메시 가드 (M10)](0006-extensible-twin-platform.md) — Accepted 2026-06-15
- [0007 — 번들 정책 씬 byte-parity: env 런타임 모델 변경을 정적 번들 xml에 박는다 (M11)](0007-bundled-policy-scene-byte-parity.md) — Accepted 2026-06-15
- [0008 — M7 실물 도달 게이트: SO-101 2-arm teleop + ACT](0008-m7-real-arm-gate.md) — Accepted 2026-06-15
- [0009 — Digital twin layering: MuJoCo/Web public viewer + backend twin gate](0009-digital-twin-layering.md) — Accepted 2026-06-17
