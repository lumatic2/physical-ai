# PRD - Observable Physical AI Laboratory

## 목적

`robotics.askewly.com`을 단순 로봇 갤러리가 아니라, 카메라·센서·언어 지시가 로봇 행동으로 변환되는 과정을 사람이 관찰하고 검증할 수 있는 피지컬 AI 실험실로 발전시킨다. 기존 디지털 트윈 workbench는 그 안의 physics/controller evidence lane으로 유지한다.

## 사용자

- 채용/포트폴리오 리뷰어: 5분 안에 무엇이 실제 검증됐고 무엇이 한계인지 이해해야 한다.
- 연구자/개발자: scene, controller, qpos contract, telemetry sidecar, QA evidence의 연결을 확인해야 한다.
- 미래의 실물 bring-up 작업자: real robot telemetry가 들어왔을 때 기존 sim evidence와 같은 gate로 비교해야 한다.
- 피지컬 AI 학습자: VLM의 장면 이해, VLA의 action 생성, controller 실행의 차이를 한 episode에서 이해해야 한다.

## 핵심 기능

1. Scene별 runtime mode 구분: learned policy, replay, comparison, telemetry stream, assisted fixture를 명확히 표시한다.
2. State contract 표시: `qpos[nq]`, fps, trajectory frames, telemetry sidecar, stream 여부를 공개 UI와 QA hook에서 확인한다.
3. Evidence-first copy: 능력 주장과 current limit을 같은 카드에 둔다.
4. 자동 검증: Playwright QA가 workbench summary를 JSON artifact로 남긴다.
5. Robotics Lab v2 UI: shadcn/ui + Tailwind 기반 app shell로 robot picker, evidence/workbench panels, environment controls, QA status를 재구성한다.
6. Favicon/app icon: imagegen으로 생성한 project-bound icon을 `assets/favicon.png`와 필요한 sibling formats로 반영한다.
7. Environment workbench: 실험실 배경, floor/terrain/environment preset, grounding/contact/physics knobs를 visitor-facing control로 노출한다.
8. Environment realism ladder: visual-only lab scenes, physical rough terrain scene, asset-backed lab shell을 별도 milestone으로 분리해 claim level을 단계적으로 올린다.
9. Controllable policy workbench: keyboard command 입력이 policy command vector와 runtime QA summary에 visible하게 연결된다.
10. Physics evidence readout: contact/force/sensor 값은 visual cue가 아니라 MuJoCo runtime에서 읽히는 값만 공개 claim으로 사용한다.
11. Public evidence refresh: README/live copy가 최신 Robotics Lab evidence와 claim boundary를 5분 안에 이해 가능한 흐름으로 갱신된다.
12. Dual-camera episode: main camera와 wrist camera, robot state, instruction, action, reward/success를 같은 timestep 계약으로 기록한다.
13. Observable decision trace: `sensor`, `vlm`, `vla`, `controller`, `environment` event를 출처와 함께 구분하고 숨은 사고 과정을 사후 생성하지 않는다.
14. Arm laboratory view: main scene, wrist camera, instruction, structured decision record, action/result timeline을 한 화면에서 재생한다.
15. Evidence mode labels: `recorded evidence`, `live/local inference`, `simulation`, `real telemetry`를 눈에 보이는 badge와 QA summary로 구분한다.

## 범위

- 포함: 기존 MuJoCo WASM viewer, experiments registry, telemetry sidecar, stream QA, comparison QA를 workbench UI/QA로 묶는다.
- 포함: React/Vite/Tailwind/shadcn shell migration, favicon/app icon asset pass, laboratory visual environment, environment preset controls, grounding/contact/physics tuning controls.
- 포함: LIBERO/robosuite 기반 로봇 팔 episode producer, main/wrist camera trace, LeRobot-compatible VLM/VLA policy evidence, deterministic public replay.
- 제외: real robot DDS capture, Isaac/Gazebo backend migration, full neural RL training, secret/API 기반 외부 서비스.
- 제외: 첫 Horizon의 신규 foundation model 학습, 상시 GPU inference backend, 공개 UI에서 생성한 가짜 chain-of-thought, 실물 동기화 없는 real digital twin 주장.

## 성공 기준

- `unitree-g1-elastic-stand`에서 telemetry sidecar와 replay state contract가 UI/QA summary에 드러난다.
- `g1-squat-reference-vs-wbc`에서 comparison gate가 UI/QA summary에 드러난다.
- 기존 replay/policy visual QA가 깨지지 않는다.
- M27: shadcn/Tailwind app shell에서 기존 MuJoCo scenes가 desktop/mobile Playwright QA를 통과하고 새 favicon이 로드된다.
- M28: 최소 3개 environment preset과 grounding/physics setting summary가 visible UI + QA artifact로 검증된다.
- M30: preset별 visual composition이 색/라인 차이를 넘어 공간 차이로 보이고, visual-only QA contract를 유지한다.
- M31: rough terrain claim은 실제 contact-bearing scene variant와 QA evidence가 있을 때만 공개한다.
- M32: GLB/glTF 또는 generated asset 기반 lab shell은 lazy-load/performance QA를 통과한 뒤 공개한다.
- M33: `g1-walk` keyboard command가 visible UI, QA summary, local/live Playwright evidence로 검증된다.
- M34: contact/force readout은 browser runtime에서 실제 노출 가능한 MuJoCo state만 probe하고, 실패 시 unsupported evidence로 명시한다.
- M35: public README/live story는 M27-M34 evidence를 반영하되 real robot telemetry나 unassisted controller proof로 과장하지 않는다.
- LAB1: canonical PASS/FAIL episode가 main/wrist camera, state, instruction, action, timing, outcome을 versioned trace로 보존한다.
- LAB2: structured VLM/skill event와 direct VLA action event가 source-tagged timeline에서 구분되고, 숨은 reasoning을 증거처럼 표시하지 않는다.
- LAB3: 공개 브라우저가 dual-camera episode와 decision/action/result timeline을 재생하고 local/live QA가 raw evidence linkage를 검증한다.
