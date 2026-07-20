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
import sys
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
LAB1_DIR = HERE.parent / "147-camera-action-episode-contract"
if str(LAB1_DIR) not in sys.path:
    sys.path.insert(0, str(LAB1_DIR))

from libero_writer import LeRobotEpisodeWriter


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
    ap.add_argument("--task-offset", type=int, default=0)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--trial-offset", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-policy-steps", type=int)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--record-root", type=pathlib.Path)
    ap.add_argument("--record-repo-id", default="physical-ai/libero-openvla")
    ap.add_argument("--record-fps", type=int, default=10)
    ap.add_argument("--dataset-revision")
    ap.add_argument("--environment-revision")
    ap.add_argument("--policy-revision")
    ap.add_argument("--direct-vla-event-dir", type=pathlib.Path)
    args = ap.parse_args()

    revision_args = (args.dataset_revision, args.environment_revision, args.policy_revision)
    if args.record_root and not all(revision_args):
        ap.error("--record-root requires dataset, environment, and policy revision hashes")
    if args.direct_vla_event_dir and not args.record_root:
        ap.error("--direct-vla-event-dir requires --record-root")

    url = f"http://127.0.0.1:{args.port}/act"
    max_steps = MAX_STEPS.get(args.suite, 300)  # 미등록 스위트는 보수적 기본
    if args.max_policy_steps is not None:
        if args.max_policy_steps < 1:
            ap.error("--max-policy-steps must be at least 1")
        max_steps = min(max_steps, args.max_policy_steps)
    if args.trial_offset < 0:
        ap.error("--trial-offset must be non-negative")
    suite = benchmark.get_benchmark_dict()[args.suite]()
    if args.task_offset < 0 or args.task_offset + args.tasks > suite.n_tasks:
        ap.error(
            f"suite has {suite.n_tasks} tasks; requested offset {args.task_offset} + {args.tasks} tasks"
        )
    task_ids = range(args.task_offset, args.task_offset + args.tasks)
    n_tasks = len(task_ids)

    per_task, total_ep, total_succ = [], 0, 0
    episode_writer = None
    record_failure = False
    t_start = time.time()
    for task_id in task_ids:
        task = suite.get_task(task_id)
        init_states = suite.get_task_init_states(task_id)
        if args.trial_offset + args.trials > len(init_states):
            ap.error(
                f"task {task_id} has {len(init_states)} init states; "
                f"requested offset {args.trial_offset} + {args.trials} trials"
            )
        bddl = os.path.join(get_libero_path("bddl_files"), task.problem_folder, task.bddl_file)
        env = OffScreenRenderEnv(bddl_file_name=bddl, camera_heights=256, camera_widths=256)
        env.seed(args.seed)
        task_desc = task.language
        task_succ = 0
        for trial_index in range(args.trials):
            ep = args.trial_offset + trial_index
            env.reset()
            obs = env.set_init_state(init_states[ep])
            t, done = 0, False
            recorded_frames = 0
            last_reward = 0.0
            episode_error = None
            while t < max_steps + NUM_STEPS_WAIT:
                try:
                    if t < NUM_STEPS_WAIT:
                        obs, _, done, _ = env.step([0, 0, 0, 0, 0, 0, -1])
                        t += 1
                        continue
                    raw = obs["agentview_image"]  # 256x256x3 uint8 (전처리는 서버)
                    pre_step_obs = obs
                    request_started = time.perf_counter()
                    resp = requests.post(
                        url,
                        data=json_numpy.dumps({"image": raw, "instruction": task_desc}),
                        headers={"Content-Type": "application/json"},
                        timeout=30,
                    )
                    resp.raise_for_status()
                    request_latency_ms = (time.perf_counter() - request_started) * 1000.0
                    raw_policy_action = np.array(json_numpy.loads(resp.text), dtype=np.float64)
                    action = raw_policy_action.copy()  # 후처리는 writable copy에만 적용
                    action = normalize_gripper_action(action)
                    action = invert_gripper_action(action)
                    obs, reward, done, _ = env.step(action.tolist())
                    last_reward = float(reward)
                    if args.record_root:
                        if episode_writer is None:
                            episode_writer = LeRobotEpisodeWriter.create(
                                root=args.record_root,
                                repo_id=args.record_repo_id,
                                fps=args.record_fps,
                                image_shape=tuple(raw.shape),
                                dataset_revision=args.dataset_revision,
                                environment_revision=args.environment_revision,
                                policy_revision=args.policy_revision,
                            )
                        episode_writer.add_executed_step(
                            observation=pre_step_obs,
                            raw_policy_action=raw_policy_action,
                            executed_action=action,
                            instruction=task_desc,
                            request_latency_ms=request_latency_ms,
                        )
                        recorded_frames += 1
                    if done:
                        break
                    t += 1
                except Exception as e:  # noqa: BLE001
                    print(f"[client] task{task_id} ep{ep} exception: {e}", flush=True)
                    episode_error = type(e).__name__
                    record_failure = record_failure or bool(args.record_root)
                    break
            if episode_writer is not None and recorded_frames:
                termination = "success" if done else "error" if episode_error else "timeout"
                sidecar_path = episode_writer.save_episode(
                    success=bool(done),
                    termination=termination,
                    reward=last_reward,
                    error_code=episode_error,
                    rollout_context={
                        "suite": args.suite,
                        "task_id": task_id,
                        "init_state_index": ep,
                        "environment_seed": args.seed,
                        "max_policy_steps": max_steps,
                    },
                )
                print(f"[client] recorded {recorded_frames} frames → {sidecar_path}", flush=True)
                if args.direct_vla_event_dir:
                    lab2_dir = HERE.parent / "148-observable-decision-action-trace"
                    if str(lab2_dir) not in sys.path:
                        sys.path.insert(0, str(lab2_dir))
                    from direct_vla import emit_direct_vla_trace

                    event_path = args.direct_vla_event_dir / f"{sidecar_path.stem}.json"
                    event_report = emit_direct_vla_trace(args.record_root, sidecar_path, event_path)
                    print(f"[client] direct VLA events {event_report['events']} → {event_path}", flush=True)
            total_ep += 1
            if done:
                task_succ += 1
                total_succ += 1
            print(f"[client] task{task_id} ep{ep}: {'SUCCESS' if done else 'fail'} ({t} steps)", flush=True)
        env.close()
        per_task.append({"task_id": task_id, "task": task.name, "episodes": args.trials, "successes": task_succ})
        print(f"[client] task{task_id} '{task.name}': {task_succ}/{args.trials}", flush=True)

    if episode_writer is not None:
        episode_writer.close()

    out = {
        "checkpoint": f"openvla/openvla-7b-finetuned-{args.suite.replace('_', '-')}", "task_suite": args.suite,
        "attn_implementation": "sdpa", "architecture": "REST server/client split",
        "seed": args.seed, "task_offset": args.task_offset,
        "trial_offset": args.trial_offset, "max_policy_steps": max_steps,
        "num_tasks": n_tasks, "trials_per_task": args.trials,
        "total_episodes": total_ep, "total_successes": total_succ,
        "success_rate": round(total_succ / max(total_ep, 1), 3),
        "elapsed_s": round(time.time() - t_start, 1), "per_task": per_task,
        "recording": {
            "enabled": bool(args.record_root),
            "artifact_location": "local-only" if args.record_root else None,
            "repo_id": args.record_repo_id if args.record_root else None,
            "failed": record_failure,
        },
    }
    print("[client] RESULT", json.dumps(out, ensure_ascii=False), flush=True)
    (VERIFY / "eval.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return 1 if record_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
