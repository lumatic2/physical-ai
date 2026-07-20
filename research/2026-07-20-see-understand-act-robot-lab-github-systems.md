# 관찰 가능한 피지컬 AI 실험실 — GitHub 기존 시스템 조사

- 조사일: 2026-07-20
- 소비처: `see-understand-act-robot-lab`
- 질문: 카메라·센서·언어 지시·로봇 행동·판단 기록을 한 화면에서 관찰하는 시스템을 어디까지 재사용할 수 있는가?

## 결론

요구를 완제품 하나로 충족하는 공개 저장소는 찾지 못했다. 그러나 핵심 바퀴 세 개는 이미 있다.

1. **episode 생산·표준화:** LeRobot + LIBERO
2. **실시간/재생 관찰:** LeRobot 공식 Rerun·Foxglove backend
3. **공개 웹 episode UI:** LeRobot Dataset Tool and Visualizer의 복수 video·graph·language timeline

따라서 이 레포가 새로 만들어야 할 것은 범용 로봇 viewer가 아니다. 기존 episode 위에 `instruction`, model revision, latency, PASS/FAIL, `sensor|vlm|vla|controller|environment` 출처를 검증하고 5분 안에 읽히게 만드는 **얇은 provenance·story layer**다.

## 조사 방법

GitHub CLI로 다음 검색군을 조회한 뒤 README, repository metadata, code search와 상위 후보의 실제 파일을 확인했다.

- `robotics visualization`, `robotics web visualization`
- `vision language action`, `VLA visualization robot`
- `robot manipulation benchmark`, `robot episode viewer camera action`
- `web interface LeRobot`, `robot learning workbench web`

상위 7개는 `references/*/ANALYSIS.md`의 5섹션 형식으로 코드 줄까지 분석했다. 별 수는 선별 신호로만 사용하고 적합성 판단에는 포함하지 않았다.

## 후보 지형

| 후보 | 이미 해결한 것 | 빠진 것 | 판정 |
|---|---|---|---|
| **Hugging Face LeRobot** | robot/dataset/policy 표준화, live Rerun, seekable Foxglove episode, image/state/action/reward/success | VLM/VLA provenance와 reviewer narrative | **채택 기준선** |
| **Rerun** | image·3D·state·action·text의 동기 timeline, Blueprint, web viewer | 정책 실행과 로봇 의미론 | **내부 증거 뷰어로 채택** |
| **LeRobot Dataset Visualizer** | 복수 camera, 공통 scrub, action/state graph, language instruction/annotation, URDF | inference 실행과 source 검증 | **공개 UI 기준선·재사용 probe** |
| **Foxglove SDK/Studio** | MCAP/WebSocket 중심 로봇 관찰·diagnosis | Studio 저장소 archived, 제품 UI 의존성·범용 message UX | **비교 probe만** |
| **Lichtblick** | 공개 browser/desktop robotics viewer | ROS/message 중심, VLA semantics 없음 | **채택 보류** |
| **LeLab backend + UI** | 실물 camera 설정, teleop, recording, joint WS, URDF, training shell | replay camera가 placeholder, VLA 판단 trace 없음, license 미표기 | **실물 UX 참고만** |
| **VoxPoser** | language decomposition, 3D value map, planned trajectory, controller 분리 | 공개 perception pipeline 부재, LeRobot/LIBERO episode 비호환 | **LAB2 시각화 패턴 차용** |
| **Franka LABS** | ROS2 sensor/actuator recording, MCAP, LeRobot export, data UI | replay/analyze UI가 README상 미완성 | **장기 실물 수집 참고** |
| **LIBERO / ManiSkill / RoboCasa / CALVIN** | 조작 task, camera/state, simulation/benchmark | 관찰 제품과 판단 trace | **환경 공급자** |
| **RoboVLA-Workbench** | command→symbolic plan→Gradio 2D frame | 물리, 연속 action, 실제 camera/state trace | **negative reference** |

## 가장 중요한 발견

### 1. LeRobot가 이미 LAB1 viewer의 대부분을 구현했다

`lerobot-dataset-viz`는 camera image와 action, state, reward, done, success를 Rerun Blueprint에 놓고 dataset timestamp로 기록한다. 같은 CLI가 Foxglove WebSocket으로 탐색 가능한 episode도 제공한다. 별도 custom timeline을 먼저 만드는 계획은 중복 가능성이 높다.

- 소스: [huggingface/lerobot](https://github.com/huggingface/lerobot/blob/ddc2aa7a27ba725ae527959c7e4814aed550e452/src/lerobot/scripts/lerobot_dataset_viz.py) (접근일: 2026-07-20)
- 상세 분석: `references/huggingface-lerobot/ANALYSIS.md`

### 2. Rerun은 “로봇의 생각을 관찰하는 debugger”에 가장 가까운 기반이다

Rerun은 multi-rate camera, point cloud, transform, joint state, time series와 text를 같은 시간축에 놓고 episode scrub과 live stream을 지원한다. Blueprint로 camera·plot·TextDocument layout도 코드로 고정할 수 있다. 다만 generic viewer이므로 VLM 관측과 VLA action의 인과 경계를 스스로 알지는 못한다.

- 소스: [rerun-io/rerun](https://github.com/rerun-io/rerun) (접근일: 2026-07-20)
- 상세 분석: `references/rerun-io-rerun/ANALYSIS.md`

### 3. 공개 웹 화면도 절반 이상 존재한다

공식 LeRobot Dataset Visualizer는 Next.js/React에서 복수 episode video를 공통 시간으로 seek하고, Language Instruction, interactive action/state graph, annotation timeline과 URDF를 조합한다. 이 레포의 LAB3와 화면 구성이 직접 겹친다.

- 소스: [huggingface/lerobot-dataset-visualizer](https://github.com/huggingface/lerobot-dataset-visualizer) (접근일: 2026-07-20)
- 상세 분석: `references/huggingface-lerobot-dataset-visualizer/ANALYSIS.md`

### 4. 비슷해 보이는 “로봇 실험실 UI”는 핵심이 비어 있을 수 있다

LeLab은 camera setup, joint monitoring, recording과 training UI를 갖지만 현재 공개 replay visualizer의 네 camera feed는 placeholder다. `RoboVLA-Workbench`도 이름은 정확히 맞지만 symbolic state를 Matplotlib PNG로 그리는 교육 prototype이다. 화면 캡처보다 raw episode와 action execution을 우선 검증해야 한다.

- 소스: [nicolas-rabault/leLab](https://github.com/nicolas-rabault/leLab), [jurmy24/leLab-space](https://github.com/jurmy24/leLab-space) (접근일: 2026-07-20)
- 소스: [2419924948gyt/RoboVLA-Workbench](https://github.com/2419924948gyt/RoboVLA-Workbench) (접근일: 2026-07-20)

### 5. “판단이 보이는 화면”은 VoxPoser에서 패턴을 빌릴 수 있다

VoxPoser는 언어 분해, value map, waypoint, controller를 분리하고 3D target/cost map과 planned path를 표시한다. end-to-end VLA의 숨은 생각을 꾸미지 않으면서 계층형 system의 실제 중간 산출물을 보여주는 좋은 패턴이다.

- 소스: [huangwl18/VoxPoser](https://github.com/huangwl18/VoxPoser) (접근일: 2026-07-20)
- 상세 분석: `references/huangwl18-VoxPoser/ANALYSIS.md`

## 보조 후보 판정

- Foxglove SDK는 live WebSocket와 MCAP 기록을 제공하지만, 공개 `foxglove/studio` 저장소는 archived다. LeRobot가 이미 Foxglove adapter를 제공하므로 SDK를 직접 통합하기보다 비교 viewer로만 실행한다. 소스: [foxglove/foxglove-sdk](https://github.com/foxglove/foxglove-sdk), [foxglove/studio](https://github.com/foxglove/studio) (접근일: 2026-07-20)
- Lichtblick은 browser/desktop 공개 viewer로는 강하지만 ROS/message 진단 도구이며 VLM/VLA provenance를 제공하지 않는다. 소스: [lichtblick-suite/lichtblick](https://github.com/lichtblick-suite/lichtblick) (접근일: 2026-07-20)
- Franka LABS는 sensor/actuator를 MCAP에 수집하고 LeRobot로 export하지만 README가 replay/analyze UI를 아직 미지원으로 표시한다. 소스: [frankarobotics/labs](https://github.com/frankarobotics/labs) (접근일: 2026-07-20)
- LIBERO, ManiSkill, RoboCasa, CALVIN은 task와 simulation을 확장할 후보이지 관찰 가능한 실험실 shell은 아니다. 소스: [Lifelong-Robot-Learning/LIBERO](https://github.com/Lifelong-Robot-Learning/LIBERO), [mani-skill/ManiSkill](https://github.com/mani-skill/ManiSkill), [robocasa/robocasa](https://github.com/robocasa/robocasa), [mees/calvin](https://github.com/mees/calvin) (접근일: 2026-07-20)

## 권고 아키텍처

```text
LIBERO/LeRobot policy run
        ↓
LeRobot episode (camera/state/action/reward/success)
        ├─ Rerun: live + internal evidence/debug
        ├─ Foxglove: seekable comparison probe
        └─ provenance extension
             instruction/model/latency/source/causal-role/outcome
                    ↓
        public reviewer UI
        (LeRobot Visualizer patterns + current Robotics Lab shell)
```

정본 후보는 “새 custom trace 하나”가 아니라 **LeRobot-compatible episode + 검증된 provenance extension**이다. Rerun `.rrd`와 public web JSON은 이 정본에서 파생되는 viewer artifact로 둔다.

## 기존 LAB 계획에 미치는 영향

### LAB1

- 첫 step을 schema 구현이 아니라 **공식 viewer 재현 probe**로 바꾼다.
- LIBERO/LeRobot의 main+wrist camera, state, action, reward/success가 Rerun과 Foxglove에서 실제로 동기 재생되는지 확인한다.
- 확인 뒤에도 없는 field만 provenance extension으로 추가한다.

### LAB2

- VoxPoser처럼 실제 생성된 semantic observation, selected skill, target/value map, planned path만 계층형 lane에 기록한다.
- end-to-end VLA는 model input, raw action, latency, controller/environment result만 표시한다.
- LeRobot v3 language event와 Rerun TextDocument가 source/provenance를 충분히 담는지 먼저 probe한다.

### LAB3

- 공식 Dataset Visualizer를 샘플 episode로 실행해 dual-camera sync, graph, language UI를 기준선으로 캡처한다.
- 기존 Vite Robotics Lab을 유지할지, 필요한 component만 이식할지, Next 앱을 fork할지는 이 probe 후 결정한다.
- Rerun web viewer를 public 제품으로 바로 노출하는 안은 설명 UX와 정적 배포 비용을 확인하기 전 채택하지 않는다.

## 즉시 다음 조사/검증

1. 작은 공개 LeRobot dual-camera episode를 `lerobot-dataset-viz` Rerun/Foxglove 양쪽으로 실행한다.
2. 현재 LIBERO evaluator output을 LeRobot episode로 기록할 수 있는 최소 adapter 경계를 찾는다.
3. 공식 Dataset Visualizer에 해당 episode를 넣어 public UI 재사용률을 실측한다.
4. 그 결과로 LAB1–LAB3 plan의 changeset을 수정한다.

## 조사 종료 판단

마지막 검색군인 `VLA visualization robot`, `robot episode viewer camera action`, `robot learning workbench web`은 `RoboVLA-Workbench` 같은 symbolic prototype과 LeRobot wrapper를 추가했을 뿐 새로운 시스템 부류를 만들지 않았다. 후보가 `실행/데이터`, `범용 관찰`, `웹 episode UI`, `계층형 판단 시각화`, `실물 운영 shell` 다섯 부류로 포화되어 GitHub landscape 조사를 종료한다.
