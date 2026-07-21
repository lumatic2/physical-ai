# ADR 0016 — 로컬 policy server와 실험 session 경계

- 상태: proposed
- 날짜: 2026-07-21

## 결정

- WSL GPU policy server는 localhost WebSocket inference만 담당한다.
- Windows/browser session controller가 task selection, pause/stop, timeout, action limit과 evidence recording을 소유한다.
- 지원 task catalog 밖 지시는 실행하지 않고 명시적으로 거부한다.
- live stream은 source-tagged observation/action/result만 노출하고 hidden reasoning을 만들지 않는다.
- public deployment는 live server에 연결하지 않고 canonical recording만 사용한다.

## 근거

- https://github.com/Physical-Intelligence/openpi/blob/main/docs/remote_inference.md (접근일: 2026-07-21)
- `research/2026-07-21-live-instruction-execution-lab-policy-server.md`
