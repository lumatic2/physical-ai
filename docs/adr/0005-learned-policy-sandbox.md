# 0005 — 트윈을 학습 정책 sandbox로: 직접 학습한 사족보행 정책의 브라우저 closed-loop 추론 (A+B)

- Status: Accepted (2026-06-12)
- 근거 reference: google-deepmind/mujoco_playground(MJX, 2025), Unitree Go1 joystick locomotion env, ONNX Runtime(web), zalo/mujoco_wasm
- 관련: [[0004-digital-twin-stack]] 되돌림 조건 (a) 발동 — replay → live inference 승격. [[0002-act-deferred-to-m6]](조작계 ACT는 여전히 M7 실물), config-driven 하네스 리팩터(`0ecb94f`, 2026-06-12)

## Context

M6 디지털 트윈(SO-100 + scripted pick-and-place replay)을 완주한 뒤, 저가 로봇팔 구매(M7)가 현재 비현실적이라
하드웨어 게이트를 우회하기로 했다. 대신 **트윈을 "현재의 SO-100 팔 외에도 다양한 피지컬 AI를 실험할 수 있는
sandbox"로 깎는다**(사용자 방향, 2026-06-12).

1단계로 SO-100 하드코딩 파이프라인을 **config-driven 하네스**로 일반화 완료(`experiments.json` 레지스트리 +
`harness.py` + 범용 물리 레코더 `record_trajectory.py`, 커밋 `0ecb94f`). humanoid를 bespoke 코드 0줄로
record→smoke→render→웹 통과시켜 하네스 일반성을 실증했다. 이 위에 **무엇을 다양화할지**가 다음 결정이고,
사용자는 두 축의 결합을 선택했다:

- **축 A (임베디먼트 갤러리)** — 하네스 덕에 거의 실행 비용 0(레지스트리 한 줄 + Menagerie sparse-checkout). 단 폭만 넓고 전부 scripted/물리 재생(AI 없음).
- **축 B (학습 정책 브라우저 추론)** — 녹화된 qpos 재생을 *신경망 정책이 매 제어스텝마다 행동을 계산해 sim을 실시간으로 모는* closed-loop으로 교체. embodied AI의 핵심.

외부 리서치(2026-06-12)로 학습→ONNX→브라우저 경로의 현실성을 확인:

- **MuJoCo Playground**(DeepMind, 2025, MJX/JAX): **Unitree Go1 joystick 보행** env 내장(전/측 선속도 + yaw rate
  command 추종). `train-jax-ppo`로 **flat terrain ~5분 학습**(2×RTX4090 기준; 로컬 RTX5090로 충분). 접근 2026-06-12.
- **배포 경로**: 학습 정책은 **50Hz ONNX Runtime 추론**이 문서화된 정식 배포 방식. RSS 2025 라이브 데모가 Go1
  joystick·휴머노이드·LEAP hand를 보여줌 → onnx 추론이 일급 경로. 접근 2026-06-12.
- **sim2sim**: Playground는 Menagerie 모델을 쓴다 → 같은 Go1 MJCF를 `zalo/mujoco_wasm`이 그대로 렌더. 학습-sim과
  웹-sim이 한 자산을 공유해 모델 드리프트가 없다(parity의 토대).
- **브라우저 추론**: `onnxruntime-web`(WASM/WebGPU). 사이트는 이미 COOP/COEP(SharedArrayBuffer) 충족 — 추가 인프라 불필요.

## Decision

**트윈의 롤아웃을 scripted-replay에서 "직접 학습한 정책의 브라우저 closed-loop 추론"으로 승격한다.
파일럿은 사족보행 보행(Go1 joystick), 정책은 우리가 직접 학습한다(A+B 결합).**

1. **임베디먼트(A)**: Menagerie `unitree_go1`(Playground 학습 대상과 동일 자산)을 갤러리에 추가. SO-100·humanoid와
   같은 `experiments.json` 레지스트리에 한 줄로. 이로써 "어떤 임베디먼트든 세운다"는 폭을 동시에 입증.
2. **정책 출처(B)**: **직접 학습**(사용자 선택, 강한 서사 — "내가 정책을 학습시켜 브라우저에 띄웠다"). MuJoCo
   Playground Go1 joystick env를 로컬 RTX5090에서 RL 학습 → ONNX export.
   - 주 경로: `train-jax-ppo`(JAX/MJX). **리스크**: JAX[cuda12]가 Blackwell(sm_120)에서 동작하는 jaxlib 필요
     (M4 때 JAX gsutil/9p 마찰 이력 — [[0004-digital-twin-stack]] 인접). **폴백**: Playground의
     `train-rsl-ppo`(rsl_rl, PyTorch) — torch cu128이 Blackwell에서 검증됨(experiment 02 이력).
3. **하네스 통합**: `experiments.json`에 optional `policy` 블록(onnx 경로 + obs_spec + action_scale + ctrl_range +
   command) 추가. `policy`가 있으면 데스크탑/웹 모두 *재생 대신* closed-loop 추론(obs 구성 → onnx.run → ctrl → mj_step).
   `make_pick_trajectory.py`(SO-100 IK)는 불변 — 정책 경로는 별도 코드.
4. **브라우저 추론**: `onnxruntime-web`(CDN). 웹 obs 구성이 학습 obs와 **바이트 단위로 일치**해야 함(관절 순서·정규화·
   body-frame 중력·command·clock) — 이 parity가 최대 리스크. 데스크탑 mujoco-python에서 먼저 parity를 잡고 웹 이식.

### 단계 (verify 게이트)

1. **학습 spike** — Playground 설치(WSL) + Go1 joystick 단시간 학습 + ONNX export → verify: **native mujoco-python에서
   onnx 정책이 Go1을 N초 안 넘어지고 command 방향으로 전진**. (JAX 막히면 rsl_rl 폴백)
2. **데스크탑 하네스 통합** — `policy` 블록 + `rollout_policy.py`(같은 onnx를 mujoco-python closed-loop) → verify: mp4 + obs parity 기록.
3. **웹 closed-loop** — onnxruntime-web + obs 구성 → verify: **같은 보행이 라이브에서 실시간 재현, 0 콘솔 에러**(sim2sim parity 데스크탑↔웹).
4. **배포 + 문서** — Vercel 재배포(`?exp=go1-walk`), README "live learned policy", 본 ADR로 0004 조건 (a) 승격 기록.

## Consequences

- **(+)** 트윈이 "예쁜 3D 재생기"에서 **"브라우저에서 도는 학습된 정책"**으로 격상 — 포트폴리오 thesis(논문→실험→쓸만한 SW)의
  embodied AI 핵심(closed-loop control)을 직접 입증. ADR 0004 조건 (a) 충족.
- **(+)** 하드웨어(M7) 없이 GPU만으로 전진 — 저가팔 구매 게이트를 우회하면서도 "실제 AI가 몸을 제어"를 보여준다.
- **(+)** 5-DOF SO-100 조작 한계([[0004-digital-twin-stack]]에 박제: top-down 파지 자세 유지 불가)를 **보행으로 우회** —
  조작은 어렵지만 사족보행은 RL이 잘 풀고 실시간 추론이 trivial.
- **(+)** A와 B가 한 작업으로 결합: 사족보행 모델을 들여오며(폭) 그 위에 정책을 얹는다(깊이).
- **(−)** scripted replay보다 무겁다: RL 학습 인프라(WSL+GPU)·obs parity 디버깅. 첫 산출까지 호흡이 길다.
- **(−)** JAX-on-Blackwell 불확실성 → rsl_rl(PyTorch) 폴백을 1단계에서 즉시 결정.
- **되돌림 조건**: (a) 직접 학습이 sm_120 인프라로 끝내 막히면, 공개 Go1 ckpt를 ONNX 변환해 *추론만* 먼저 띄우고
  (서사는 약화, 출처 명시) 학습은 후속으로. (b) 보행 sim2sim parity가 끝내 안 맞으면 SO-100 reaching 같은
  더 단순한 정책으로 파일럿 축소.
