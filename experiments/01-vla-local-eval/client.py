"""
client.py — REST 클라이언트: LIBERO 시뮬(EGL) 에서 rollout, raw 관측을 /act 로 POST.

tensorflow 를 import 하지 않는다 (tf↔robosuite-EGL 세그폴트 회피). torch 는 init_states(torch.load)용으로만
쓰며 EGL 에 안전(확정). 전처리는 서버가 전담 — 클라이언트는 raw agentview(256x256x3) 만 전송.
rollout 루프/후처리 출처: references/openvla-openvla/experiments/robot/{libero/run_libero_eval.py, robot_utils.py}
run: PYTHONPATH=$HOME/LIBERO MUJOCO_GL=egl python client.py --suite libero_spatial --tasks 2 --trials 5
"""

import argparse
import json
import os
import pathlib
import time

os.environ.setdefault("MUJOCO_GL", "egl")

import json_numpy  # patch() 는 import 후 main() 에서 (전역 patch 가 라이브러리 json 파싱을 깰 수 있음)

import numpy as np
import requests
import torch  # init_states 로딩용 (EGL 안전 — 확정)
from libero.libero import benchmark, get_libero_path
from libero.libero.envs import OffScreenRenderEnv

# torch 2.6+ weights_only=True 가 LIBERO .pruned_init(numpy) 로딩 차단 → 로컬 신뢰 파일이므로 False
_orig = torch.load
torch.load = lambda *a, **k: _orig(*a, **{**k, "weights_only": False})

# suite 별 max_steps (출처: run_libero_eval.py:173-182, "longest training demo" 기준)
MAX_STEPS = {
    "libero_spatial": 220, "libero_object": 280, "libero_goal": 300,
    "libero_10": 520, "libero_90": 400,
}
NUM_STEPS_WAIT = 10
HERE = pathlib.Path(__file__).resolve().parent
VERIFY = HERE / "verify"
VERIFY.mkdir(exist_ok=True)


def normalize_gripper_action(action):  # robot_utils:75-92 (binarize=True)
    action[..., -1] = 2 * (action[..., -1] - 0.0) / (1.0 - 0.0) - 1
    action[..., -1] = np.sign(action[..., -1])
    return action


def invert_gripper_action(action):  # robot_utils:95-102
    action[..., -1] = action[..., -1] * -1.0
    return action


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="libero_spatial")
    ap.add_argument("--tasks", type=int, default=2)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    url = f"http://127.0.0.1:{args.port}/act"
    max_steps = MAX_STEPS.get(args.suite, 300)  # 미등록 스위트는 보수적 기본
    suite = benchmark.get_benchmark_dict()[args.suite]()
    n_tasks = min(args.tasks, suite.n_tasks)

    per_task, total_ep, total_succ = [], 0, 0
    t_start = time.time()
    for task_id in range(n_tasks):
        task = suite.get_task(task_id)
        init_states = suite.get_task_init_states(task_id)
        bddl = os.path.join(get_libero_path("bddl_files"), task.problem_folder, task.bddl_file)
        env = OffScreenRenderEnv(bddl_file_name=bddl, camera_heights=256, camera_widths=256)
        env.seed(0)
        task_desc = task.language
        task_succ = 0
        for ep in range(args.trials):
            env.reset()
            obs = env.set_init_state(init_states[ep])
            t, done = 0, False
            while t < max_steps + NUM_STEPS_WAIT:
                try:
                    if t < NUM_STEPS_WAIT:
                        obs, _, done, _ = env.step([0, 0, 0, 0, 0, 0, -1])
                        t += 1
                        continue
                    raw = obs["agentview_image"]  # 256x256x3 uint8 (전처리는 서버)
                    resp = requests.post(
                        url,
                        data=json_numpy.dumps({"image": raw, "instruction": task_desc}),
                        headers={"Content-Type": "application/json"},
                        timeout=30,
                    )
                    action = np.array(json_numpy.loads(resp.text), dtype=np.float64)  # 디코드 + writable copy
                    action = normalize_gripper_action(action)
                    action = invert_gripper_action(action)
                    obs, _, done, _ = env.step(action.tolist())
                    if done:
                        break
                    t += 1
                except Exception as e:  # noqa: BLE001
                    print(f"[client] task{task_id} ep{ep} exception: {e}", flush=True)
                    break
            total_ep += 1
            if done:
                task_succ += 1
                total_succ += 1
            print(f"[client] task{task_id} ep{ep}: {'SUCCESS' if done else 'fail'} ({t} steps)", flush=True)
        env.close()
        per_task.append({"task_id": task_id, "task": task.name, "episodes": args.trials, "successes": task_succ})
        print(f"[client] task{task_id} '{task.name}': {task_succ}/{args.trials}", flush=True)

    out = {
        "checkpoint": f"openvla/openvla-7b-finetuned-{args.suite.replace('_', '-')}", "task_suite": args.suite,
        "attn_implementation": "sdpa", "architecture": "REST server/client split",
        "num_tasks": n_tasks, "trials_per_task": args.trials,
        "total_episodes": total_ep, "total_successes": total_succ,
        "success_rate": round(total_succ / max(total_ep, 1), 3),
        "elapsed_s": round(time.time() - t_start, 1), "per_task": per_task,
    }
    print("[client] RESULT", json.dumps(out, ensure_ascii=False), flush=True)
    (VERIFY / "eval.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
