# 09-real-arm-gate — M7 실물 도달 구매 전 게이트

> M7. sim/browser 포트폴리오 다음 단계인 실물 로봇팔로 넘어갈지 판단한다.
> 상태: 게이트 패키지 완료 — SO-101 2-arm + ACT-first로 경로를 좁혔고, 실제 구매/조립은 외부 입력 필요.

## 1. 가설 (Hypothesis)

SO-101 2-arm teleoperation setup을 구매·조립할 수 있는 예산/공간/시간이 확보되면, 이 레포의 다음 실물 산출물은 ACT imitation learning으로 tabletop pick/place를 수행하는 영상과 reality-gap 회고가 된다.

반증 조건:
- SO-101 2-arm 조달 비용/배송/조립 시간이 현재 감당 불가능하다.
- leader/follower teleop 없이 충분한 demonstration data를 모으기 어렵다.
- 첫 task를 stack으로 잡으면 M6에서 확인한 5-DOF reach/orientation 한계가 다시 발목을 잡는다.

## 2. 방법 (Method)

### 최신 소스 확인

접근일: 2026-06-15.

| Source | 확인한 내용 | M7 판단 |
|---|---|---|
| [TheRobotStudio/SO-ARM100 GitHub](https://github.com/TheRobotStudio/SO-ARM100) | SO-101은 SO-100 후속. SO-100 docs는 deprecated. SO-101은 wiring 개선, 조립 용이, leader motor 업데이트 | 신규 구매는 SO-101 우선 |
| [Hugging Face LeRobot SO-101 docs](https://huggingface.co/docs/lerobot/so101) | follower/leader motor gear ratio가 다름. assembly/calibration가 LeRobot 경로에 있음 | leader+follower 부품 구분 필수 |
| [HF ACT-on-SO-101 blog](https://huggingface.co/blog/sherryxychen/train-act-on-so-101) | SO-101에서 ACT 학습 사례가 있음. webcams, clamp, gaming desktop 기반 | ACT-first가 실행 가능한 방향 |
| [NVIDIA GR00T N1.5 SO-101 blog](https://huggingface.co/blog/nvidia/gr00t-n1-5-so101-tuning) | 단일 SO-101 arm teleoperation data로 post-training 예제 존재 | ACT 이후 확장 후보 |

### 후보 비교

| Option | 장점 | 리스크 | 판단 |
|---|---|---|---|
| SO-101 follower-only | 비용 낮음, 조립 단순 | demo data 수집이 어려움. ACT 장점이 약함 | 보류 |
| SO-101 leader+follower | LeRobot 표준 teleop, ACT 데이터 수집 적합 | 비용/공간/배선 증가 | **추천** |
| SO-100 신규 | 기존 sim 자산과 이름 일치 | deprecated, 조립/배선 이슈 | 제외 |
| 더 비싼 arm | 성능/강성 우위 | 포트폴리오 ROI 낮음 | 제외 |

### 구매 전 체크리스트

- [ ] 예산: 2-arm parts/kit + 배송 + 예비 servo + 카메라/삼각대/클램프까지 감당 가능.
- [ ] 작업 공간: 두 팔 고정 가능한 책상, 조명, 카메라 2대 시야 확보.
- [ ] 전원/USB: 전원 어댑터와 USB 포트/허브 안정성 확보.
- [ ] 조립 시간: 최소 반나절~하루를 calibration 포함해 비울 수 있음.
- [ ] 태스크 범위: 첫 task는 `pick cube -> place into zone`, stack 금지.
- [ ] 산출물 범위: dataset snippet, train log, eval video, failure analysis를 공개 가능한 형태로 남길 수 있음.

### M7 실행 순서

1. **Acquisition**: SO-101 leader+follower kit 또는 BOM sourcing, 카메라 2대, clamp, 예비 부품 확보.
2. **Bring-up**: LeRobot install, arm detection, motor calibration, safety limit 확인.
3. **Data**: tabletop pick/place demonstrations 50~100 episodes 수집.
4. **Train**: ACT baseline 학습. 작은 task success를 먼저 본다.
5. **Deploy/Eval**: held-out object pose에서 real rollout 20회 이상 평가.
6. **Package**: 영상, dataset schema, train/eval log, reality-gap 회고.

## 3. 결과 (Results)

### 게이트 판단

| Gate | Verdict | 근거 |
|---|---|---|
| 하드웨어 후보 | PASS | SO-101 2-arm으로 좁힘 |
| SW 경로 | PASS | LeRobot + ACT 사례 존재 |
| 첫 task 정의 | PASS | pick/place로 낮춤 |
| 구매 실행 | BLOCKED | 실제 예산/배송/공간 확인 필요 |

### 박제 위치

- ADR: [`docs/adr/0008-m7-real-arm-gate.md`](../../docs/adr/0008-m7-real-arm-gate.md)
- Roadmap: [`ROADMAP.md`](../../ROADMAP.md) M7

## 4. 통찰 (Insights)

### 무엇을 알아냈나

- M7은 지금 코드 작업으로 끝나는 마일스톤이 아니다. 구매/배송/조립이 실제 gate다.
- 신규 구매라면 SO-100이 아니라 SO-101로 가야 한다. 기존 SO-100 sim은 계속 유효하지만, 실물 구매 기준은 바뀌었다.
- ACT를 실측할 무대는 여전히 실물 imitation learning이다. M4에서 ACT를 억지로 LIBERO에 올리지 않은 결정과 일관된다.
- 첫 실물 task를 stacking으로 잡으면 실패 리스크가 불필요하게 커진다. pick/place 성공 후 stack으로 확장해야 한다.

### 가설은 통과했나?

- [x] PASS — 경로는 선명해졌다: SO-101 leader+follower + LeRobot + ACT-first.
- [ ] FAIL

### 정의에 반영

- M7은 `구매 전 게이트 완료`, `실물 구매/조립 대기` 상태로 둔다.
- 다음 실제 M7 작업은 하드웨어가 확보된 뒤 `M7a bring-up`으로 시작한다.

### 다음 실험 후보

- M15: Barkour/Go2/H1 등 새 Playground policy 학습.
- M7a: SO-101 bring-up, calibration, first dataset capture.
