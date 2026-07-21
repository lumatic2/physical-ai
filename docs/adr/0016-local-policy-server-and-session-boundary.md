# ADR 0016 — 로컬 policy server와 실험 session 경계

- 상태: accepted
- 날짜: 2026-07-21

## 결정

- WSL GPU inference server는 OpenVLA·π₀.₅ direct VLA와 Qwen3-VL bounded observation/skill의 localhost WebSocket inference만 담당한다.
- session controller는 exclusive GPU lease를 소유해 한 번에 한 실행 레인만 적재하고, 전환 전에 이전 model process·port·VRAM 정리를 검증한다.
- Windows/browser session controller가 task selection, pause/stop, timeout, action limit과 evidence recording을 소유한다.
- 지원 task catalog 밖 지시는 실행하지 않고 명시적으로 거부한다.
- live stream은 source-tagged observation/action/result만 노출하고 hidden reasoning을 만들지 않는다.
- Qwen3-VL 출력은 별도 `vlm` source의 구조화된 scene/allowlisted skill이며, VLA의 숨은 생각이나 저수준 action으로 표시하지 않는다.
- public deployment는 live server에 연결하지 않고 canonical recording만 사용한다.

## 근거

- https://github.com/Physical-Intelligence/openpi/blob/main/docs/remote_inference.md (접근일: 2026-07-21)
- `research/2026-07-21-live-instruction-execution-lab-policy-server.md`
