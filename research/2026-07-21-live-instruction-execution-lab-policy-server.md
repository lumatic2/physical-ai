# 로컬 실시간 지시 실행 실험실 조사

- 조사일: 2026-07-21
- 소비처: `live-instruction-execution-lab`
- 질문: recorded LAB3를 사용자가 지시·정책을 선택해 실제 local inference를 실행하는 관찰형 실험실로 확장할 때 어떤 경계를 써야 하는가?

## 결론

GPU policy 환경과 browser/session runtime을 분리한 localhost WebSocket server가 가장 작은 재사용 경계다. free-form 지시를 임의 BDDL task로 생성하지 않고, GEN1에서 검증한 task catalog의 canonical instruction과 명시적 paraphrase만 허용한다. 실행 중 dual-camera/state/action/event를 stream하고 종료 뒤 기존 LAB canonical episode로 승격한다.

## 근거

- openpi는 policy server와 최소 의존 client를 분리하고 observation image, wrist image, state, prompt를 WebSocket으로 보내 action chunk를 받는 공식 remote inference 경로를 제공한다. 출처: https://github.com/Physical-Intelligence/openpi/blob/main/docs/remote_inference.md (접근일: 2026-07-21)
- openpi는 inference에 8GB 이상 GPU, Ubuntu 22.04를 공식 지원 환경으로 제시하고 π₀.₅-LIBERO checkpoint와 policy server를 제공한다. Windows UI와 WSL GPU runtime을 분리하는 근거다. 출처: https://github.com/Physical-Intelligence/openpi (접근일: 2026-07-21)
- OpenVLA는 기존 direct action 기준선이며 OFT가 multi-image와 25~50배 빠른 inference를 지원한다고 안내한다. Horizon 1의 비교 정책을 live server adapter로 재사용하되 Horizon 2에서 새 fine-tuning은 하지 않는다. 출처: https://github.com/openvla/openvla (접근일: 2026-07-21)

## 채택 결정

1. localhost-only policy server와 session orchestrator를 분리한다.
2. 지원 task catalog 밖 자유 지시는 실행하지 않고 `unsupported_instruction`으로 기록한다.
3. OpenVLA와 π₀.₅-LIBERO를 선택 가능하게 하되 실제 source와 latency를 stream한다.
4. stop/pause/timeout/action-limit을 server보다 session controller가 우선 적용한다.
5. 공개 사이트는 live backend에 연결하지 않고 검증된 session recording만 재생한다.

## 조사 종료 판단

OpenVLA, openpi server/client와 기존 LAB contracts를 대조한 뒤 추가 자료는 transport와 preprocessing 세부만 보강했다. policy server, session controller, observable stream, canonical recorder의 네 경계로 포화되어 종료한다.
