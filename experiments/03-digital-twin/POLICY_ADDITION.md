# Policy Addition Routine

새 Playground policy를 브라우저 live demo로 흡수할 때의 최소 gate. M15 Barkour에서 실제로 터진 지점을 기준으로 만든다.

## 1. Target Probe

- Registry env 이름을 확인한다. Menagerie asset만 있고 trainable env가 없으면 policy target이 아니다.
- `registry.load(env, config_overrides={"impl": "jax"})`로 `nq`, `nv`, `nu`, sensor names, keyframe, obs shape를 확인한다.
- `locomotion_params.brax_ppo_config(env)`의 `num_timesteps`, network shape, `policy_obs_key`를 기록한다.

## 2. Train / Export

- `verify/train.log`, `verify/rewards.txt`, `params.pkl` 위치를 남긴다.
- ONNX export는 JAX deterministic policy와 max abs diff를 비교한다. target: `< 1e-4`.
- `obs_spec.json`에는 obs layout, history/gait 같은 stateful input, action scale, default pose, command convention을 적는다.

## 3. Native Parity

- native MuJoCo C engine에서 ONNX closed-loop rollout을 실행한다.
- golden obs는 browser가 재현해야 하는 첫 control steps의 `qpos`, `qvel`, `last_act`, `command`, obs slots, action을 포함한다.
- command convention을 직접 확인한다. user-facing forward와 env command 축이 다르면 registry에 `command_transform`을 둔다.

## 4. XML / Scene Bundle

- ADR 0007 유지: env가 런타임에 모델 필드를 바꾸면 static XML에 bake한다.
- 자주 빠지는 항목:
  - PD gain / actuator gain / actuator bias
  - damping / friction / mass
  - contact sensors or frame sensors added in Python
  - history/gait state needed by obs builder
- `web/assets/scenes/<slug>/`에 scene XML, assets, ONNX, golden obs, obs spec을 같이 둔다.
- `gen_scene_manifest.py`를 반드시 실행한다. scene 단독 loadtest가 통과해도 manifest가 빠지면 app load가 실패한다.

## 5. Registry / Sync / QA

- Canonical source is `experiments/03-digital-twin/experiments.json`.
- `python sync_web.py --check`가 PASS해야 한다.
- `node qa/loadtest.mjs <slug>/<scene>.xml`이 PASS해야 한다.
- `node qa/visual_check.mjs --exp=<exp>` local PASS.
- `node qa/command_sweep.mjs --exp=<exp>` local PASS.
- deploy 후 `--live` visual/command QA까지 닫는다.

## 6. Required Evidence

- exp README 4섹션 완료.
- `verify/` raw artifacts:
  - train/reward/export/native logs
  - ONNX parity output
  - golden obs / obs spec
  - local/live visual QA log
  - local/live command sweep JSON
- ROADMAP and `experiments/README.md` status update.
