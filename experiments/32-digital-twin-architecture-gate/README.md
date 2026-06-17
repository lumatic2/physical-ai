# 32-digital-twin-architecture-gate - robotics digital twin stack decision

> M24. 지금 구현한 `robotics.askewly.com`을 "디지털 트윈"으로 부를 수 있는 범위와, 다음 구현에 붙일 backend twin stack을 결정한다.

## 1. 가설 (Hypothesis)

현재 웹 구현은 full digital twin이 아니라 **public-facing MuJoCo web twin layer**이고, 다음 단계는 이를 버리는 것이 아니라 Unitree G1 중심의 연구용 backend twin을 붙이는 architecture로 가야 한다.

반증 기준:
- 현재 구현이 이미 real telemetry/sensor sync/scene authoring까지 포함한 full digital twin이면 별도 backend gate가 불필요하다.
- G1 skill lab에 더 적합한 오픈소스 stack이 MuJoCo/Web보다 public demo와 연구 backend를 동시에 더 잘 만족하면 현 스택을 유지하지 않는다.
- 조사한 OSS 후보가 실제 G1/MuJoCo/Isaac/ROS2 연결 근거를 제공하지 못하면 "digital twin" 방향을 보류한다.

## 2. 방법 (Method)

### 셋업
- 현재 구현: `experiments/03-digital-twin/web`, MuJoCo WASM, Three.js, ONNX Runtime Web, public `robotics.askewly.com`.
- 현재 연구 병목: M19 G1 visible squat. exp30 결과상 target depth가 아니라 controlled descent stability가 병목이다.
- 외부 정의 수집일: 2026-06-17.

### 외부 정의와 후보
| 후보 | 공식/준공식 정의 | 이 레포에서의 의미 |
|---|---|---|
| MuJoCo | free and open source physics engine for robotics, biomechanics, graphics, animation | 빠른 articulated robot/contact 검증의 core truth layer |
| Isaac Sim | Omniverse 기반 robotics simulation, testing, synthetic data generation reference framework | OpenUSD, sensor, photorealistic scene, synthetic data backend 후보 |
| Isaac Lab | robot learning workflow를 단순화하는 modular framework | G1/locomanipulation/Isaac learning backend 후보 |
| Gazebo + ROS 2 | robot simulation, actuator/sensor bridge, ROS visualization/control tutorial ecosystem | real robot bridge와 sensor/telemetry sync 후보 |
| Unitree MuJoCo | Unitree sdk2, unitree_ros2, sdk2_python control code를 MuJoCo simulator에 연결 | G1 sim-to-real interface 후보 |
| Unitree IsaacLab / RL Lab | Unitree G1/H1 계열을 Isaac Lab에서 data collection, playback, generation, validation | G1 high-fidelity backend 후보 |

### 시나리오
- S1: 현재 구현물을 digital twin layer 관점으로 재분류한다.
- S2: MuJoCo/Web, Isaac Sim/Lab, Gazebo/ROS2, Unitree official stacks를 비교한다.
- S3: 다음 milestone의 scope를 "full twin 구현"이 아니라 "backend twin gate"로 좁혀 검증 가능한 결정을 만든다.

### 측정 metric
- public demo 유지성
- G1 skill learning 적합성
- real robot bridge 가능성
- sensor/scene authoring 확장성
- local implementation cost
- portfolio clarity

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1 current stack classification | PASS | local repo audit | 0 | 현재 구현은 browser-based MuJoCo robotics lab이다 |
| S2 OSS stack shortlist | PASS | web/source audit | 0 | MuJoCo/Web 유지 + Unitree MuJoCo/IsaacLab backend gate 추천 |
| S3 roadmap fit | PASS | local roadmap audit | 0 | M23 이후 M24 architecture gate로 배치 가능 |

### 현재 구현의 정확한 이름

현재 구현은 **browser-based MuJoCo robotics lab** 또는 **lightweight public digital twin viewer**다.

이미 갖춘 것:
- MuJoCo physics scene and robot assets.
- learned ONNX policy runtime in browser.
- native rollout, browser replay, command sweep, QA evidence.
- public Robotics Lab UI with robot/motion/evidence/limit framing.

아직 full digital twin이라고 부르기 약한 것:
- real robot telemetry sync 없음.
- sensor model and ROS2 bridge 없음.
- scenario/scene authoring UI 없음.
- backend twin과 public viewer 사이의 state contract 없음.
- G1 visible squat은 아직 micro-dip/fall boundary에 머문다.

### 추천 architecture

| Layer | 책임 | 현재/후보 |
|---|---|---|
| Public twin viewer | 방문자가 로봇, 동작, 증거, 한계를 이해한다 | 현재 MuJoCo WASM + Three.js 유지 |
| Physics truth layer | joint/contact/fall/native metric 판정 | 현재 MuJoCo native 유지 |
| Learning backend | skill policy 학습, controller 실험 | 현재 MuJoCo Playground/MJX, 후보 Unitree RL Mjlab/IsaacLab |
| High-fidelity scene/sensor backend | OpenUSD scene, camera/lidar/synthetic data | 후보 Isaac Sim/Isaac Lab |
| Real robot bridge | SDK/ROS2/DDS telemetry and command sync | 후보 Unitree MuJoCo + Unitree SDK2/ROS2 |
| Visual world-model assistant | reference video, plausibility critic | 선택 후보 Cosmos 3, 증거가 아닌 hypothesis material |

### 박제 위치
- 이 문서 자체가 M24 gate artifact다.
- `verify/web-trajectory-contract.json`에 현재 web replay가 요구하는 trajectory contract를 박제했다.
- 다음 구현이 시작되면 `verify/`에 candidate install/probe logs를 보존한다.

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- 사용자가 원하는 "디지털 트윈"은 Cosmos 3 같은 world model보다 **simulator + robot asset + controller + telemetry + viewer**의 system architecture에 가깝다.
- 지금 구현은 실패가 아니라, full twin 중 public viewer와 policy sandbox layer를 이미 확보한 상태다.
- G1에 한정하면 generic simulator shopping보다 Unitree official MuJoCo/IsaacLab/ROS2 path를 먼저 보는 것이 맞다.
- M19 visible squat을 계속하려면 MuJoCo native/controller가 본선이고, Cosmos 3는 reference/critic 보조선에만 둔다.
- 다음 작업은 코드를 갈아엎는 것이 아니라 backend twin candidate를 하나 골라 "G1 state/action trace를 현재 web viewer contract로 가져올 수 있는가"를 검증하는 것이다.
- 현재 web viewer의 replay 최소 계약은 `fps`, `nq`, `scene`, `qpos[frame][nq]`다. Unitree bridge는 먼저 이 계약을 맞춰야 한다.

### 가설은 통과했나?
- [x] PASS - 현재 구현은 public-facing MuJoCo web twin layer로 유지한다.
- [x] PASS - next gate는 Unitree/MuJoCo/IsaacLab/ROS2 후보를 비교하는 backend twin decision이다.
- [ ] FAIL - full telemetry-synced digital twin 구현은 아직 아니다.

### 정의에 반영
- ROADMAP에 M24 `Digital Twin Architecture Gate`를 추가한다.
- ADR 0009로 "MuJoCo/Web을 public viewer로 유지하고 backend twin gate를 연다"는 의사결정을 보존한다.

### 다음 실험 후보
- `33-unitree-mujoco-g1-bridge-probe`: Unitree MuJoCo를 받아 G1 state/action trace를 내보내고 현재 web trajectory schema와 비교한다.
- `34-isaaclab-g1-backend-probe`: Isaac Lab/Unitree RL Lab의 G1 task가 현재 skill lab에 주는 이득과 설치 비용을 검증한다.
- `35-ros2-telemetry-contract`: real robot 없이 mock DDS/ROS2 telemetry를 현재 web viewer state schema로 stream한다.

## Sources

- MuJoCo: https://mujoco.org/ (accessed 2026-06-17)
- Isaac Sim: https://developer.nvidia.com/isaac/sim (accessed 2026-06-17)
- Isaac Lab: https://isaac-sim.github.io/IsaacLab/ (accessed 2026-06-17)
- Gazebo/ROS 2 tutorial: https://docs.ros.org/en/humble/Tutorials/Advanced/Simulators/Gazebo/Gazebo.html (accessed 2026-06-17)
- Unitree MuJoCo: https://github.com/unitreerobotics/unitree_mujoco (accessed 2026-06-17)
- Unitree IsaacLab simulation: https://github.com/unitreerobotics/unitree_sim_isaaclab (accessed 2026-06-17)
- Unitree RL Lab: https://github.com/unitreerobotics/unitree_rl_lab (accessed 2026-06-17)
