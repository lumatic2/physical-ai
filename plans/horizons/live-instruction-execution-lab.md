# HORIZON — 지시를 바꿔 실행하는 로컬 피지컬 AI 실험실

> 생성: 2026-07-21 · 연쇄: 2/3 · 상태: active-approved

## 목표

- 검증된 task와 실행 레인을 사용자가 선택하면 local GPU가 실제 inference를 실행하고 camera·state·action·event가 실시간 화면과 canonical recording으로 이어지게 한다.
- OpenVLA·π₀.₅의 direct VLA action과 Qwen3-VL의 구조화된 장면 관찰·허용 기술 선택을 서로 다른 source로 보여, VLM과 VLA의 역할 차이를 화면에서 이해하게 한다.
- Objective의 **데모에서 실험 플랫폼으로** 축을 recorded replay에서 operator-controlled execution으로 전진시킨다.
- **예상 분량: ~26 changeset** — LIVE1 6 + LIVE2~LIVE5 각 5 step/changeset의 bottom-up 합계다.

## 왜 지금

- GEN Horizon은 여러 과제와 두 정책의 신뢰 가능한 정본을 만들지만 실행은 batch다.
- LAB3 viewer와 GEN result contract가 있으므로 새 모델보다 session control, live observability와 recording promotion에 집중할 수 있다.

## 범위

- 포함: localhost inference server, OpenVLA/π₀.₅ direct VLA adapter, Qwen3-VL bounded observation/skill adapter, supported instruction catalog, exclusive GPU lease, session safety controls, live dual-camera/event stream, canonical recording, local interactive UI와 public recorded proof.
- 제외: arbitrary task generation, always-on public GPU, new fine-tuning, chain-of-thought, real robot.
- 실행 모드: `continuous`; GEN Horizon 완료 후 자동 승격 가능.

## 담을 Milestone — 설계 번들 인덱스

| Milestone | 제목 | plan doc | 승인 | 리서치 입력 |
|---|---|---|---|---|
| **LIVE1** | 통합 inference server 계약 | `plans/2026-07-21-live1-unified-policy-server.md` | approved | `research/2026-07-21-live-instruction-execution-lab-policy-server.md` + LAB2 Qwen3-VL evidence |
| **LIVE2** | 안전한 실험 session 제어 | `plans/2026-07-21-live2-safe-experiment-session.md` | approved | LIVE1 + ADR 0016 |
| **LIVE3** | 실시간 관찰 stream | `plans/2026-07-21-live3-observable-live-stream.md` | approved | LIVE1/LIVE2 |
| **LIVE4** | 실행 기록과 replay 승격 | `plans/2026-07-21-live4-session-recording-promotion.md` | approved | LIVE1~LIVE3 |
| **LIVE5** | 로컬 실행형 실험실과 공개 증명 | `plans/2026-07-21-live5-interactive-local-lab.md` | approved | LIVE1~LIVE4 |

## 닫는 기준

- OpenVLA·π₀.₅·Qwen3-VL 세 실행 레인이 exact revision과 공통 request/result envelope, exclusive GPU lease, health/inference/stop gate를 통과한다.
- 두 task×두 instruction form×세 실행 레인의 12 session에서 pause/stop/timeout/action limit가 deterministic하게 작동한다.
- dual-camera/state/action/event stream의 frame sync와 source provenance가 live QA에서 PASS한다.
- 모든 valid session이 canonical episode로 승격되고 live와 replay summary/hash가 연결된다.
- local interactive UI와 public recorded session이 claim boundary·desktop/mobile gate를 통과한다.

## 미리 쓰는 실패 회고

- **free-form 지시를 임의 task로 실행해 성공 여부가 무의미했다.** → catalog 밖 지시는 LIVE2가 거부한다.
- **GPU server 오류로 session이 멈추지 않고 action이 계속됐다.** → controller-owned heartbeat, action limit와 fail-closed stop을 LIVE1/2 DoD로 둔다.
- **VLM 설명을 VLA의 숨은 생각으로 보이게 했다.** → Qwen3-VL 구조화 출력과 direct VLA action을 별도 실행 레인·source·assistance로 고정하고 free-form chain-of-thought를 거부한다.
- **세 모델을 동시에 올려 VRAM이 고갈됐다.** → session controller가 한 번에 한 실행 레인만 소유하는 exclusive GPU lease와 unload 검증을 강제한다.
- **live 화면은 멋지지만 evidence로 재현되지 않았다.** → LIVE4 canonical promotion 전에는 LIVE5 public proof를 시작하지 않는다.

## 결정 로그

- status: resolved
- OpenVLA와 π₀.₅ direct VLA, Qwen3-VL→bounded skill을 localhost-only inference adapter로 제공한다.
- GPU에는 한 번에 한 실행 레인만 적재하며 전환 시 이전 model process·VRAM·port 정리를 검증한다.
- supported task catalog와 explicit paraphrase만 실행한다.
- public site는 recorded session만 제공한다.

## 링크

- 위: `OBJECTIVE.md`
- 연쇄: `plans/horizons/CANDIDATES.md`
- 리서치: `research/2026-07-21-live-instruction-execution-lab-policy-server.md`
- 결정: `docs/adr/0016-local-policy-server-and-session-boundary.md`
