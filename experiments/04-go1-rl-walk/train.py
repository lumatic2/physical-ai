"""S2 — Go1JoystickFlatTerrain 정책 학습 (brax PPO, Playground 튜닝 config).

learning/train_jax_ppo.py 의 하이퍼파라미터를 locomotion_params 로 그대로 미러링하되,
mujoco_warp(미설치) 회피를 위해 impl="jax"(클래식 MJX) 로 오버라이드한다.
산출: <out>/params.pkl (brax inference params), <out>/rewards.txt (학습 곡선).

실행: python train.py [out_dir] [num_timesteps]
"""
import functools, os, pickle, sys, time
import jax
from brax.training.agents.ppo import train as ppo
from brax.training.agents.ppo import networks as ppo_networks
from mujoco_playground import registry, wrapper
from mujoco_playground.config import locomotion_params

ENV = "Go1JoystickFlatTerrain"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/yusun/playground-go1/runs/go1flat"
os.makedirs(OUT, exist_ok=True)

env = registry.load(ENV, config_overrides={"impl": "jax"})
eval_env = registry.load(ENV, config_overrides={"impl": "jax"})
ppo_params = locomotion_params.brax_ppo_config(ENV)
if len(sys.argv) > 2:
    ppo_params.num_timesteps = int(sys.argv[2])
print("ENV", ENV, "| num_timesteps", ppo_params.num_timesteps,
      "| net", tuple(ppo_params.network_factory.policy_hidden_layer_sizes), flush=True)

net_factory = functools.partial(ppo_networks.make_ppo_networks,
                                **ppo_params.network_factory)
tp = dict(ppo_params)
tp.pop("network_factory", None)
num_eval_envs = tp.pop("num_eval_envs", 128)

rewards = []
def progress(step, metrics):
    r = metrics.get("eval/episode_reward")
    if r is not None:
        rewards.append((int(step), float(r)))
        print(f"{step}: reward={r:.3f}", flush=True)

t0 = time.monotonic()
make_inference_fn, params, _ = ppo.train(
    environment=env, eval_env=eval_env,
    **tp, network_factory=net_factory, seed=0,
    wrap_env_fn=wrapper.wrap_for_brax_training,
    num_eval_envs=num_eval_envs, progress_fn=progress,
)
dt = time.monotonic() - t0
print(f"TRAIN DONE in {dt/60:.1f} min", flush=True)

with open(os.path.join(OUT, "params.pkl"), "wb") as f:
    pickle.dump(params, f)
with open(os.path.join(OUT, "rewards.txt"), "w") as f:
    f.write(f"# {ENV} impl=jax num_timesteps={ppo_params.num_timesteps} train_min={dt/60:.1f}\n")
    for s, r in rewards:
        f.write(f"{s}\t{r}\n")
print("saved ->", os.path.join(OUT, "params.pkl"), flush=True)
