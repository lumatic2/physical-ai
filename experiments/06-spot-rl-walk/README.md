# 06-spot-rl-walk — Spot 4족 joystick 보행 정책 직접 학습 → ONNX → native 검증 → 웹

> M11. [ADR 0005](../../docs/adr/0005-learned-policy-sandbox.md) 학습-정책 sandbox의 **4족 2종 비교**(Go1↔Spot)로 갤러리 확장.
> exp [04](../04-go1-rl-walk/README.md)(Go1)·[05](../05-g1-rl-walk/README.md)(G1) 파이프라인 재사용 — **train.py는 ENV만 교체**(`SpotFlatTerrainJoystick`).
>
> ⚠ **상태: 진행 중** — 학습 실행 중. 결과·통찰 섹션은 학습/검증 완료 후 채운다 (Judge 규약: 5섹션 다 채우기 전 통찰 확정 금지).

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
| **S2** 학습 | `train.py`(ENV 교체) PPO, impl=jax, 100M steps, net(128⁴) | reward 수렴 + `params.pkl` |
| **S3** ONNX export | ckpt → onnx + obs 정규화 baked | onnx 파일 |
| **S4** native 검증 ★ | native mujoco closed-loop 롤아웃 | Spot ≥10s 보행, command 추종 |
| **S5** 웹 parity ★★ | main.js obs builder에 **qpos_error_history(36)+feet_pos(12)** 추가 → 번들 씬 byte-parity 0.0 | native↔web obs 차 0.0 |
| **S6** 라이브 | `experiments.json` policy 항목 + `add_scene.sh` → `?exp=spot-walk` | 라이브 QA PASS |

### obs parity 핵심 (S1 발견 — 핸드오프 가정과 다름)

핸드오프는 "Spot은 Go1 유사 48-d 추정"이었으나 **실제 81-d**, 그리고 go1/g1에 없던 2개 컴포넌트 포함:
- **`qpos_error_history` (36)** — `(joint_angles − motor_targets)` 3스텝 롤링 버퍼. **stateful** — 웹 빌더가 motor_target·관절 히스토리를 추적해야 함.
- **`feet_pos` (12)** — 4발 site 위치(FK). 프레임 확인 필요.
- **gait clock 없음 / linear velocity 없음** (정책 obs). g1 대비 단순한 점.

→ **웹 obs 빌더(main.js) 신규 코드 필요** = M11 최대 난관. (g1·go1은 이 두 컴포넌트가 없어 재사용 불가.)

## 3. 결과 (Results)

> 학습/검증 완료 후 기록 — reward 곡선·학습 시간·native 보행 시간·web parity 잔차.

## 4. 통찰 / 한계 (Insight)

> 5섹션(여기선 4섹션) 완료 후. Go1↔Spot 4족 비교 서사.

---

## 파일

- `train.py` — exp04 미러, ENV=`SpotFlatTerrainJoystick`만 교체.
- `obs_spec.json` — 81-d obs 레이아웃(웹 parity 진실원천).
- `verify/train.log`, `verify/` — raw 출력 박제.
