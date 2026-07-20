# ADR 0014 — LeRobot 정본 episode와 공식 viewer 재사용

- Status: Accepted
- Date: 2026-07-21
- Supersedes: ADR 0013의 독자 versioned manifest와 SmolVLA-first producer 결정

## Context

LAB1의 초기안은 별도 episode manifest를 정의하고 새로운 viewer 경로를 만드는 것이었다. 그러나 공개 [`lerobot/libero`](https://huggingface.co/datasets/lerobot/libero) episode 0에서 두 카메라, 8D state, 7D action, instruction, timestamp가 함께 존재함을 확인했고, LeRobot 공식 Rerun export도 동일 episode를 재생했다(접근일 2026-07-21). 배포된 [LeRobot Dataset Visualizer](https://huggingface.co/spaces/lerobot/visualize_dataset?path=%2Flerobot%2Flibero%2Fepisode_0)는 두 video, instruction, synchronized graph와 scrub을 제공했다(접근일 2026-07-21).

근거 artifact는 `experiments/147-camera-action-episode-contract/verify/official-viewer-reuse/README.md`에 보존한다.

## Decision

1. LAB1의 시계열 정본은 **LeRobot v3 episode**다. camera, state, action, timestamp와 task mapping을 별도 manifest에 복제하지 않는다.
2. 환경·정책·dataset revision, camera role/model-input 여부, latency, outcome과 claim boundary는 **LAB provenance sidecar**에 둔다.
3. sidecar는 canonical episode 필드를 중복 소유할 수 없으며 revision은 움직이는 branch 이름이 아닌 pinned hash여야 한다.
4. 첫 producer는 이미 실행 증거가 있는 OpenVLA+LIBERO 경로다. SmolVLA 비교는 LAB1 선행 조건에서 제외한다.
5. [LeRobot 공식 source](https://github.com/huggingface/lerobot)의 Rerun export를 내부 replay 기준선으로 사용한다(접근일 2026-07-21).
6. [LeRobot Dataset Visualizer source](https://github.com/huggingface/lerobot-dataset-visualizer)의 multi-video/playback/chart interaction만 현재 public app에 선택 이식한다(접근일 2026-07-21). 전체 app은 fork하지 않는다.
7. Foxglove는 선택적 개발 진단으로만 남기고 공개 runtime dependency로 쓰지 않는다.

## Consequences

- 공식 생태계와 호환되는 episode를 바로 Rerun과 향후 LeRobot 도구로 검사할 수 있다.
- LAB 전용 정보는 sidecar에 국한되어 새 데이터 포맷과 adapter 중복을 줄인다.
- wrist camera가 저장돼도 실제 checkpoint 입력이라는 근거가 없으면 `model_input=false`로 공개된다.
- 공개 화면은 recorded simulation을 deterministic replay하며 live inference나 real robot digital twin으로 주장하지 않는다.
- LeRobot v3 profile 또는 viewer contract가 바뀌면 validator fixture와 ADR 후속 결정으로 명시적으로 갱신한다.

