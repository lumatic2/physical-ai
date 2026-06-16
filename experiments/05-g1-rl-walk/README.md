# 05-g1-rl-walk — G1 휴머노이드 joystick 보행 정책 학습 → ONNX → 브라우저 live closed-loop

> [ADR 0005](../../docs/adr/0005-learned-policy-sandbox.md) 학습 정책 sandbox의 **두 번째 임베디먼트**.
> [04-go1-rl-walk](../04-go1-rl-walk/README.md)(4족 Go1)와 동일 파이프라인을 **휴머노이드**에 적용 —
> "직접 학습한 정책이 *사람형 로봇*을 브라우저에서 걷게 한다". 04와 겹치는 셋업은 04 README를 참조하고,
> 여기서는 G1 고유의 난관(obs parity)과 결과만 기록한다.

## 결과 (한눈에)

| 단계 | 결과 |
|---|---|
| 학습 | `G1JoystickFlatTerrain` PPO **200M step / 46.5분** (RTX5090, jax 0.9.2, impl=jax). reward −6.4 → **+14.8 수렴** |
| ONNX export | 손작성 그래프, **onnx vs jax parity 2.1e-6** (obs/act 크기 env 자동유도) |
| native 검증 (S4) | native mujoco closed-loop: **안 넘어지고 12s · 9.38m 전진 · 0.78 m/s** |
| 번들 씬 parity | desktop rollout: obs **byte parity 0.00e+00** (layout + scene 둘 다 — 학습 씬과 완전 동일) |
| 브라우저 (Phase 3) | onnxruntime-web live closed-loop: **5.0 m 전진 · 0 콘솔 에러**, gait phase clock JS 구현 |

**라이브: [robotics.askewly.com/?exp=g1-walk](https://robotics.askewly.com/?exp=g1-walk)**

## 파이프라인 (= 04, ENV만 G1)

```bash
# WSL venv (jax 0.9.2 + playground + onnx). 04 README의 셋업과 동일.
python train.py          /home/.../runs/g1flat        # PPO 200M → params.pkl + rewards.txt
python export_onnx.py    /home/.../runs/g1flat        # → g1_policy.onnx + obs_spec.json (parity assert)
python verify_native.py  /home/.../runs/g1flat 12 1.0 # native closed-loop → golden_obs.json (S4)
# 03 통합: rollout_g1.py(번들 씬 parity + traj + indices 박제) → main.js JS closed-loop
```

## G1이 Go1보다 어려운 지점 — obs parity (핵심 난관)

Go1 obs는 48-d였지만 G1은 **103-d**이고 구성이 다르다 (obs_spec.json 진실원천):

```
[ local_linvel(3), gyro(3), gravity(3), command(3),       ← command가 중간 (Go1은 끝)
  joint_angles−default(29), joint_vel(29), last_act(29),  ← 29 관절 (다리12+허리3+팔14)
  phase_cos_sin(4) ]                                       ← gait phase clock (Go1엔 없음)
```

- **gait phase clock**: 2-벡터 `phase=[0,π]`를 매 제어 step `phase += 2π·dt·gait_freq` 로 전진시키고
  `concat([cos(phase), sin(phase)])`(4-d)를 obs에 넣는다. sim 상태가 아닌 **stateful 외부 클록**이라
  native·desktop·JS 세 곳에서 동일하게 굴려야 한다 (gait_freq=1.375 박제).
- **default_pose**: `keyframe("knees_bent").qpos[7:]`(29) — Go1의 `home`과 다른 키프레임.
- **gravity**: `imu_in_pelvis` 사이트의 `site_xmat.T @ [0,0,−1]` (= −third row).

→ 이 셋을 틀리면 정책이 즉시 넘어진다. **golden_obs.json**(native 첫 5스텝의 입력→obs103 박제)에
desktop·web obs builder를 바이트 단위로 맞춰(0.00e+00) 검증했다. JS는 `experiments.json`의
`obs_layout`을 그대로 걷는 일반 빌더라 Go1·G1이 한 코드 경로를 공유한다.

## 함정 (04와 공유 + G1 신규)

- **jax 0.9.2 다운핀** (brax 0.14.2 ↔ jax 0.10 비호환) · **impl="jax"** (mujoco_warp 미설치) — 04와 동일.
- **n_substeps=10** (sim_dt 0.002 / ctrl_dt 0.02) — Go1의 5와 다름. JS·desktop 모두 env에서 유도.
- **mujoco-js 0.0.7 wasm 호환**: 휴머노이드 mjx feetonly 씬이 브라우저에서 컴파일되는지 `qa/loadtest.mjs`로
  선검증(통과). 메시는 g1-stand 번들 35개를 재사용(무복제).

## 파일

`train.py` · `export_onnx.py` · `verify_native.py` (파이프라인) · `obs_spec.json` (103-d 진실원천) ·
`golden_obs.json` (parity fixture) · `rewards.txt` (학습 곡선). 03 통합은 `../03-digital-twin/rollout_g1.py`.
`*.pkl`/`*.onnx`/`*.mp4`/`train.log`는 gitignored (재생성 가능).
