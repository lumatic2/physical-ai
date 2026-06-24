# PRD - Physical AI Digital Twin Workbench

## 목적

`robotics.askewly.com`을 단순 갤러리가 아니라, 로봇 asset, physics runtime, learned policy, replay trace, telemetry stream, evidence gate를 구분해서 보여주는 디지털 트윈 workbench로 발전시킨다.

## 사용자

- 채용/포트폴리오 리뷰어: 5분 안에 무엇이 실제 검증됐고 무엇이 한계인지 이해해야 한다.
- 연구자/개발자: scene, controller, qpos contract, telemetry sidecar, QA evidence의 연결을 확인해야 한다.
- 미래의 실물 bring-up 작업자: real robot telemetry가 들어왔을 때 기존 sim evidence와 같은 gate로 비교해야 한다.

## 핵심 기능

1. Scene별 runtime mode 구분: learned policy, replay, comparison, telemetry stream, assisted fixture를 명확히 표시한다.
2. State contract 표시: `qpos[nq]`, fps, trajectory frames, telemetry sidecar, stream 여부를 공개 UI와 QA hook에서 확인한다.
3. Evidence-first copy: 능력 주장과 current limit을 같은 카드에 둔다.
4. 자동 검증: Playwright QA가 workbench summary를 JSON artifact로 남긴다.
5. Robotics Lab v2 UI: shadcn/ui + Tailwind 기반 app shell로 robot picker, evidence/workbench panels, environment controls, QA status를 재구성한다.
6. Favicon/app icon: imagegen으로 생성한 project-bound icon을 `assets/favicon.png`와 필요한 sibling formats로 반영한다.
7. Environment workbench: 실험실 배경, floor/terrain/environment preset, grounding/contact/physics knobs를 visitor-facing control로 노출한다.

## 범위

- 포함: 기존 MuJoCo WASM viewer, experiments registry, telemetry sidecar, stream QA, comparison QA를 workbench UI/QA로 묶는다.
- 포함: React/Vite/Tailwind/shadcn shell migration, favicon/app icon asset pass, laboratory visual environment, environment preset controls, grounding/contact/physics tuning controls.
- 제외: real robot DDS capture, Isaac/Gazebo backend migration, full neural RL training, secret/API 기반 외부 서비스.

## 성공 기준

- `unitree-g1-elastic-stand`에서 telemetry sidecar와 replay state contract가 UI/QA summary에 드러난다.
- `g1-squat-reference-vs-wbc`에서 comparison gate가 UI/QA summary에 드러난다.
- 기존 replay/policy visual QA가 깨지지 않는다.
- M27: shadcn/Tailwind app shell에서 기존 MuJoCo scenes가 desktop/mobile Playwright QA를 통과하고 새 favicon이 로드된다.
- M28: 최소 3개 environment preset과 grounding/physics setting summary가 visible UI + QA artifact로 검증된다.
