# 보고 판단하고 움직이는 로봇팔 실험실 — 기술·증거 구조 조사

- 조사일: 2026-07-20
- 소비처: `see-understand-act-robot-lab`
- 질문: 카메라·센서·언어 지시가 로봇 행동으로 변환되는 과정을 사용자가 이해하고 검증할 수 있는 첫 제품 slice는 무엇인가?

## 사용자 의도

사용자가 원하는 대표 화면은 특정 제조사나 로봇 기종의 시뮬레이터가 아니다. 카메라가 달린 로봇 팔이 장면을 관측하고, 자연어 지시와 센서 상태를 함께 받아 물체를 잡거나 옮기며, 관측·판단·행동·결과가 같은 시간축에 보이는 피지컬 AI 실험실이다.

확정 문구:

> 카메라와 센서로 세상을 보고, 언어 지시를 이해하고, 로봇 행동을 생성·실행하며, 그 전 과정을 사람이 관찰할 수 있는 피지컬 AI 실험실.

## 개념 경계

- **VLM**은 이미지와 언어를 함께 받아 장면 설명·질의응답·의미 특징을 만든다. 그 자체가 로봇 관절 명령을 낸다는 뜻은 아니다.
- **VLA**는 이미지·언어·로봇 상태를 받아 로봇 action 또는 action chunk를 낸다.
- **계층형 에이전트**는 VLM/멀티모달 LLM의 구조화된 판단과 skill/controller 실행을 분리하므로 `관측 → 선택한 skill → 실행 결과`를 인과적인 판단 기록으로 남길 수 있다.
- **end-to-end VLA**는 입력에서 행동을 직접 생성한다. 공개 UI는 모델 입력, action, 지연시간, 실행 결과를 보여줄 수 있지만 존재하지 않는 자연어 사고 과정을 사후 생성해 내부 추론처럼 표시하면 안 된다.
- 실물 로봇과 상태 동기화가 없는 첫 Horizon은 `시뮬레이션 기반 피지컬 AI 실험실`이다. 실물 telemetry가 붙기 전에는 실물 디지털 트윈으로 주장하지 않는다.

## 현재 레포에서 재사용할 수 있는 기반

- `experiments/01-vla-local-eval/client.py`는 LIBERO `agentview_image`와 자연어 instruction을 REST policy server에 보내고 7차원 action을 받아 `env.step()`으로 실행한다.
- `experiments/01-vla-local-eval/server.py`는 OpenVLA 입력 전처리와 action 생성을 이미 수행한다.
- `experiments/02-action-repr-bench`에는 서로 다른 VLA action representation을 같은 LIBERO 과제군에서 비교한 실측이 있다.
- `experiments/03-digital-twin/web`에는 Vite/React/Tailwind/shadcn shell, replay/stream/runtime summary, Playwright QA와 Vercel 공개 배포 경로가 있다.

현재 빠진 것은 새로운 물리 엔진이 아니라 다음 연결이다.

1. main/wrist camera, robot state, instruction, raw/normalized action, latency, reward/success를 한 episode trace로 보존한다.
2. VLM의 구조화된 관측 또는 계층형 skill 선택과 VLA의 연속 action을 출처가 다른 기록으로 구분한다.
3. 공개 브라우저가 canonical PASS/FAIL episode를 같은 타임라인에서 재생하고 원시 증거로 내려갈 수 있게 한다.

## 외부 공식 자료

### LIBERO 관측·행동 계약

LeRobot의 LIBERO 통합은 다음 관측과 행동을 정식으로 노출한다.

- `observation.images.image`: main camera
- `observation.images.image2`: wrist camera (`robot0_eye_in_hand_image`)
- `observation.state`: end-effector position/orientation과 gripper 상태를 합친 8차원 proprioception
- action: 6D end-effector delta + 1D gripper의 7차원 연속 제어

따라서 첫 slice는 새 simulation scene을 만들지 않고 LIBERO의 카메라·상태·성공 판정을 그대로 episode evidence로 사용할 수 있다.

출처: https://huggingface.co/docs/lerobot/libero (접근일: 2026-07-20)

### SmolVLA 입력·출력 구조

SmolVLA는 여러 카메라 영상, 현재 sensorimotor state, 자연어 instruction을 입력으로 받고 action expert가 연속 action chunk를 생성한다. 작은 공개 모델과 LeRobot 통합이 있어 카메라→언어→행동을 설명하는 첫 VLA 후보로 적합하다. 첫 구현은 공개 checkpoint 재현을 우선하며 이 Horizon 안에서 새 foundation model을 학습하지 않는다.

출처: https://huggingface.co/docs/lerobot/smolvla (접근일: 2026-07-20)

### 환경과 정책 처리 분리

LeRobot environment processor는 raw observation, 환경별 좌표/이미지 변환, 정책별 전처리, action 후처리, `env.step()`을 분리한다. 공개 trace도 이 경계를 보존해야 어떤 값이 센서 원본이고 어떤 값이 모델 입력 또는 제어 명령인지 설명할 수 있다.

출처: https://huggingface.co/docs/lerobot/env_processor (접근일: 2026-07-20)

### 카메라·센서 가시화

robosuite는 robot body에 붙은 eye-in-hand camera, RGB/depth/segmentation observation, joint/gripper proprioception을 같은 observation dict로 반환할 수 있다. sensor delay와 corruption도 Observable API로 모델링할 수 있지만 첫 Horizon에서는 범위를 넓히지 않고 RGB 두 시점과 기본 proprioception만 사용한다.

출처: https://robosuite.ai/docs/modules/sensors.html (접근일: 2026-07-20)

### VLM backbone과 action 출력의 차이

OpenVLA는 visual encoder와 LLM backbone이 image/language feature를 처리한 뒤 tokenized action을 생성하고 이를 연속 action으로 복원한다. 이 구조는 “VLM이 장면을 이해한다”와 “VLA가 로봇 행동을 낸다”가 같은 문장이 아님을 보여준다.

출처: https://openvla.github.io/ (접근일: 2026-07-20)

## 첫 제품 slice 권고

- **시뮬레이터:** 기존 LIBERO/robosuite/MuJoCo 평가 경로
- **로봇:** LIBERO가 제공하는 단일 로봇 팔. 제조사 정체성보다 camera/state/action 계약을 우선한다.
- **과제:** target과 destination이 시각적으로 분명한 단일 pick-and-place. 기존 suite를 검사해 성공·실패 episode가 모두 재현되는 과제를 기술 기준으로 고른다.
- **VLA:** LeRobot-compatible SmolVLA checkpoint를 첫 후보로 probe한다. 호환 실패 시 기존 OpenVLA path를 fallback으로 사용하되 실제 model input camera를 UI에 정확히 표시한다.
- **VLM/판단 기록:** 로컬 open-weight VLM이 구조화된 scene/skill JSON을 만들 수 있는지 별도 lane으로 probe한다. VLA의 숨은 사고 과정으로 표시하지 않는다.
- **공개 실행:** 모델 추론은 로컬 GPU에서 canonical episode를 만들고, Vercel 정적 앱은 trace와 camera frames를 결정론적으로 재생한다. `recorded evidence`와 `live/local inference`를 badge로 구분한다.

## 증거 계약 초안

한 episode는 최소 다음을 포함한다.

- run id, schema version, environment revision, policy id/revision, task instruction, seed
- timestep과 동기화된 main camera, wrist camera
- raw robot state와 policy-normalized state의 shape/source
- raw action, controller-ready action, gripper command
- inference latency, reward, termination, success
- 선택적 `semantic_observation`과 `selected_skill`; 생성 주체와 model id 필수
- 숨은 chain-of-thought 필드 금지

## 실패 시나리오에서 역으로 얻은 게이트

1. **예쁜 replay만 남고 실제 정책 실행과 연결되지 않는다.** → 모든 UI event가 trace timestep과 raw artifact path를 가진다.
2. **보조 VLM 설명을 VLA의 생각처럼 오인시킨다.** → event source를 `sensor`, `vlm`, `vla`, `controller`, `environment`로 구분하고 UI에 표시한다.
3. **모델 학습과 인프라 범위가 커져 화면이 완성되지 않는다.** → 첫 Horizon은 공개 checkpoint, 단일 과제, recorded evidence를 사용하고 새 학습·상시 추론 backend를 제외한다.

## 조사 종료 판단

LIBERO 관측 계약, SmolVLA 입력·action chunk 구조, LeRobot 처리 경계, robosuite 센서 API, OpenVLA action 구조를 확인했다. 마지막 세 자료는 새 제품 경로를 추가하지 않고 동일한 `camera/state/instruction → policy → action → environment` 경계와 가시화 필드만 보강했다. 후보 지형이 포화되어 조사를 종료한다.
