# 06-spot-rl-walk — Spot 4족 joystick 보행 정책 직접 학습 → ONNX → native 검증 → 웹

> M11. [ADR 0005](../../docs/adr/0005-learned-policy-sandbox.md) 학습-정책 sandbox의 **4족 2종 비교**(Go1↔Spot)로 갤러리 확장.
> exp [04](../04-go1-rl-walk/README.md)(Go1)·[05](../05-g1-rl-walk/README.md)(G1) 파이프라인 재사용 — **train.py는 ENV만 교체**(`SpotFlatTerrainJoystick`).
>
> **상태: S1~S6 완료** (2026-06-15) — 학습→ONNX→native→웹 byte-parity 보행까지. 라이브 `?exp=spot-walk`(배포 반영).

## 1. 가설 (Hypothesis)

MuJoCo Playground `SpotFlatTerrainJoystick` env를 로컬 RTX5090(WSL)에서 RL 학습해 ONNX로 export하면,
그 정책 하나가 **native mujoco-python에서 Spot을 command 방향으로 ≥10s 안 넘어지고 걷게** 만들고,
나아가 **브라우저(onnxruntime-web)에서 byte-parity obs로 같은 정책이 closed-loop 보행**한다.

- 반증(FAIL): ① 학습이 수렴 안 함, ② native에서 즉시 넘어짐/전진 실패, ③ 웹 obs parity(81-d) 재현 실패로
  native↔web 행동 발산.

## 2. 방법 (Method) — exp 04/05 파이프라인 재사용, ENV만 교체

| 단계 | 내용 | verify |
|---|---|---|
| **S1** env 조사 | `SpotFlatTerrainJoystick` obs/act 구조 파악 | ✅ obs=81-d(state)/12-act, gait clock 없음(주석 처리됨) → [`obs_spec.json`](obs_spec.json) |
| **S2** 학습 | `train.py`(ENV 교체) PPO, impl=jax, 100M steps, net(128⁴) | ✅ 6.5분, reward 7.96→30.6 수렴, `params.pkl` |
| **S3** ONNX export | ckpt → onnx + obs 정규화 baked | ✅ `spot_policy.onnx`, onnx↔jax parity **4.07e-6** (5층 동적 그래프) |
| **S4** native 검증 ★ | native mujoco closed-loop 롤아웃 | ✅ **PASS** — 12s 안 넘어짐, **11.09m 전진·0.92m/s**, final_h 0.43 |
| **S5** 웹 parity ★★ | main.js obs builder에 **qpos_error_history(36)+feet_pos(12)** 추가 → 번들 씬 byte-parity 0.0 | ✅ 번들 씬 obs == golden **2.91e-07**, 웹 closed-loop 0.93m/s(native 0.92 동급) |
| **S6** 라이브 | `experiments.json` policy 항목 + 번들 씬 + `?exp=spot-walk` | ✅ wasm OK, 로컬 QA PASS(upright·forward), 배포 후 라이브 |

### obs parity 핵심 (S1 발견 — 핸드오프 가정과 다름)

핸드오프는 "Spot은 Go1 유사 48-d 추정"이었으나 **실제 81-d**, 그리고 go1/g1에 없던 2개 컴포넌트 포함:
- **`qpos_error_history` (36)** — `(joint_angles − motor_targets)` 3스텝 롤링 버퍼. **stateful** — 웹 빌더가 motor_target·관절 히스토리를 추적해야 함.
- **`feet_pos` (12)** — 4발 site 위치(FK). 프레임 확인 필요.
- **gait clock 없음 / linear velocity 없음** (정책 obs). g1 대비 단순한 점.

→ **웹 obs 빌더(main.js) 신규 코드 필요** = M11 최대 난관. (g1·go1은 이 두 컴포넌트가 없어 재사용 불가.)

## 3. 결과 (Results) — S2~S4 (학습→ONNX→native)

- **학습(S2)**: 6.5분(100M steps, impl=jax, net 128⁴), reward 7.96→**30.6** 수렴(go1 29.7 동급). `verify/train.log`.
- **export(S3)**: 5층(hidden 4 + 출력) silu MLP → 손그래프 ONNX, **onnx↔jax 4.07e-6**(go1 4.8e-6 동급). `spot_policy.onnx`.
- **native(S4)**: onnx closed-loop, **12s 안 넘어지고 11.09m 전진·0.92m/s**(go1 12s·11.8m·0.99). `native_rollout.mp4`, `golden_obs.json`(웹 parity 기준).
- **웹 parity(S5)**: 번들 씬 rollout obs == 학습 golden **2.91e-07**. 웹 closed-loop 0.93m/s(native 0.92 동급, upright). main.js에 `gravity_projected`(upvector 센서)·`feet_pos`(4 framepos)·`qpos_error_history`(stateful 36) 슬롯 + `advanceHistory`/clip 추가, go1/G1 무회귀(둘 다 보행 유지).
- **번들 byte-parity 함정(S6)**: 번들 씬이 학습과 0.15 발산 → 원인은 env가 런타임에 PD 게인 오버라이드(`base.py`: dof_damping=Kd=1[xml 2], gainprm=Kp=300[xml 400]). xml에 그 값을 박아 **2.91e-07**로 수렴. *학습 씬과 번들 씬의 비자명한 차이는 모델 필드 diff로만 잡힌다*.

## 4. 통찰 / 한계 (Insight) — Go1 ↔ Spot 4족 2종 비교

- **obs 아키텍처가 임베디먼트마다 다르다**: Go1(48-d)=속도+gyro+중력+관절+관절속도+last_act, G1(103-d)=+gait phase clock, **Spot(81-d)=속도·phase 없이 stateful 관절오차 히스토리(36)+발끝 위치(12)**. "4족이면 obs 비슷"이라는 핸드오프 가정은 틀렸다 — 정책망 입력은 env 설계 선택이라 재사용 불가, 매번 소스를 읽어야 한다.
- **그러나 파이프라인은 재사용된다**: train(ENV 1줄)·export(N층 일반화)·native verify·번들 byte-parity·웹 obs(슬롯 기반)까지 동일 골격. 정책별로 *새로운 건 obs 슬롯 정의뿐*. 이게 M10 "확장 플랫폼"의 실증 — 3번째 학습정책(Go1·G1·Spot)을 같은 틀로 흡수.
- **byte-parity의 진짜 적은 숨은 런타임 오버라이드**: playground env가 xml 로드 후 PD 게인을 코드로 바꾼다. 정적 번들은 이를 못 따라가 미세 발산 → 모델 필드 diff(dof_damping/gainprm)로만 발견. 시각·reward로는 안 잡힌다.
- **한계**: 번들 visual 메시는 감축본이라 외형이 거칠다(물리·obs 무영향, watertight 가드로 KEPT). Spot은 flat terrain·command 전진만 검증 — rough terrain·turn 미검증.

---

## 파일

- `train.py` — exp04 미러, ENV=`SpotFlatTerrainJoystick`만 교체.
- `obs_spec.json` — 81-d obs 레이아웃(웹 parity 진실원천).
- `verify/train.log`, `verify/` — raw 출력 박제.
