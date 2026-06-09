"""
eval_m4.py — M4: LIBERO-spatial success rate (H3).

OpenVLA 의 전처리/추론 헬퍼를 *출처 명시하고 인라인* 한다 — experiments.robot.* 를 import 하면
prismatic 전체 훈련 스택(draccus 등)을 끌어오므로, 필요한 순수 함수만 그대로 복사(아래 주석에 원본 위치).
get_vla 의 flash_attention_2 하드코딩은 우회: sdpa 로 직접 로딩 (flash-attn 빌드 마찰 회피).
rollout 루프는 run_libero_eval.py:160-238 를 따른다. bounded(소수 task·trial).

체크포인트: openvla/openvla-7b-finetuned-libero-spatial (README:546, 접근 2026-06-09)
인라인 출처: references/openvla-openvla/experiments/robot/{libero/libero_utils.py, openvla_utils.py, robot_utils.py}
run: PYTHONPATH=$HOME/LIBERO MUJOCO_GL=egl python eval_m4.py --num-tasks 2 --trials 5
"""

import argparse
import faulthandler
import json
import math
import os
import pathlib
import sys
import time

faulthandler.enable()
os.environ.setdefault("MUJOCO_GL", "egl")


def dbg(msg):
    print(f"[dbg] {msg}", flush=True)

HERE = pathlib.Path(__file__).resolve().parent
VERIFY = HERE / "verify"
VERIFY.mkdir(exist_ok=True)

CKPT = "openvla/openvla-7b-finetuned-libero-spatial"
TASK_SUITE = "libero_spatial"
RESIZE = 224           # robot_utils.get_image_resize_size (openvla)
MAX_STEPS = 220        # run_libero_eval.py:174 (libero_spatial)
NUM_STEPS_WAIT = 10    # GenerateConfig default


# === 인라인 헬퍼 (출처: libero_utils.py) ===
def resize_image(tf, img, resize_size):  # libero_utils:33-47
    img = tf.image.encode_jpeg(img)
    img = tf.io.decode_image(img, expand_animations=False, dtype=tf.uint8)
    img = tf.image.resize(img, resize_size, method="lanczos3", antialias=True)
    img = tf.cast(tf.clip_by_value(tf.round(img), 0, 255), tf.uint8)
    return img.numpy()


def get_libero_image(tf, obs, resize_size):  # libero_utils:50-58
    if isinstance(resize_size, int):
        resize_size = (resize_size, resize_size)
    img = obs["agentview_image"]
    img = img[::-1, ::-1]  # rotate 180 to match train preprocessing
    return resize_image(tf, img, resize_size)


def quat2axisangle(np, quat):  # libero_utils:77-101
    if quat[3] > 1.0:
        quat[3] = 1.0
    elif quat[3] < -1.0:
        quat[3] = -1.0
    den = np.sqrt(1.0 - quat[3] * quat[3])
    if math.isclose(den, 0.0):
        return np.zeros(3)
    return (quat[:3] * 2.0 * math.acos(quat[3])) / den


# === 인라인 헬퍼 (출처: openvla_utils.py) ===
def crop_and_resize(tf, image, crop_scale, batch_size):  # openvla_utils:81-124
    if image.shape.ndims == 3:
        image = tf.expand_dims(image, axis=0)
        expanded = True
    else:
        expanded = False
    new_h = tf.reshape(tf.clip_by_value(tf.sqrt(crop_scale), 0, 1), shape=(batch_size,))
    new_w = tf.reshape(tf.clip_by_value(tf.sqrt(crop_scale), 0, 1), shape=(batch_size,))
    h_off = (1 - new_h) / 2
    w_off = (1 - new_w) / 2
    boxes = tf.stack([h_off, w_off, h_off + new_h, w_off + new_w], axis=1)
    image = tf.image.crop_and_resize(image, boxes, tf.range(batch_size), (224, 224))
    if expanded:
        image = image[0]
    return image


def get_vla_action(tf, torch, Image, np, vla, processor, obs, task_label, unnorm_key, dev):  # openvla_utils:127-170
    image = Image.fromarray(obs["full_image"]).convert("RGB")
    # center_crop=True (LIBERO 체크포인트는 image_aug 로 finetune)
    image = tf.convert_to_tensor(np.array(image))
    orig_dtype = image.dtype
    image = tf.image.convert_image_dtype(image, tf.float32)
    image = crop_and_resize(tf, image, 0.9, 1)
    image = tf.clip_by_value(image, 0, 1)
    image = tf.image.convert_image_dtype(image, orig_dtype, saturate=True)
    image = Image.fromarray(image.numpy()).convert("RGB")
    prompt = f"In: What action should the robot take to {task_label.lower()}?\nOut:"
    inputs = processor(prompt, image).to(dev, dtype=torch.bfloat16)
    return vla.predict_action(**inputs, unnorm_key=unnorm_key, do_sample=False)


# === 인라인 헬퍼 (출처: robot_utils.py) ===
def normalize_gripper_action(np, action, binarize=True):  # robot_utils:75-92
    action[..., -1] = 2 * (action[..., -1] - 0.0) / (1.0 - 0.0) - 1
    if binarize:
        action[..., -1] = np.sign(action[..., -1])
    return action


def invert_gripper_action(action):  # robot_utils:95-102
    action[..., -1] = action[..., -1] * -1.0
    return action


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--num-tasks", type=int, default=2)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    import random

    import numpy as np
    import tensorflow as tf
    import torch
    from PIL import Image
    from transformers import AutoModelForVision2Seq, AutoProcessor

    from libero.libero import benchmark, get_libero_path
    from libero.libero.envs import OffScreenRenderEnv

    # torch 2.6+ 의 weights_only=True 기본값이 LIBERO 의 .pruned_init(numpy 객체) 로딩을 막음.
    # 로컬 신뢰 파일이므로 weights_only=False 로 복원 (monkeypatch).
    _orig_torch_load = torch.load
    torch.load = lambda *a, **k: _orig_torch_load(*a, **{**k, "weights_only": False})

    # seed (robot_utils.set_seed_everywhere)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    dev = torch.device("cuda:0")

    # ── EGL(env) 를 CUDA(model) 전에 생성 ──
    # robosuite EGL 컨텍스트를 torch CUDA 컨텍스트보다 먼저 띄워야 한다. 순서가 반대(model→env)면
    # egl_context.py:136 (eglQueryDevicesEXT) 에서 세그폴트 — EGL↔CUDA GPU 컨텍스트 충돌.
    suite = benchmark.get_benchmark_dict()[TASK_SUITE]()
    n_tasks = min(args.num_tasks, suite.n_tasks)
    envs = []
    for task_id in range(n_tasks):
        task = suite.get_task(task_id)
        init_states = suite.get_task_init_states(task_id)
        task_bddl = os.path.join(get_libero_path("bddl_files"), task.problem_folder, task.bddl_file)
        dbg(f"creating env task{task_id} (before CUDA)")
        env = OffScreenRenderEnv(bddl_file_name=task_bddl, camera_heights=256, camera_widths=256)
        env.seed(0)
        envs.append((task_id, task, init_states, env))
    dbg(f"{len(envs)} env(s) created before CUDA")

    # ── 이제 모델 로드 (CUDA after EGL) ──
    print(f"[m4] loading {CKPT} (sdpa)")
    processor = AutoProcessor.from_pretrained(CKPT, trust_remote_code=True)
    vla = AutoModelForVision2Seq.from_pretrained(
        CKPT, attn_implementation="sdpa", torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True, trust_remote_code=True,
    ).to(dev)
    if TASK_SUITE not in getattr(vla, "norm_stats", {}):
        from huggingface_hub import hf_hub_download
        with open(hf_hub_download(repo_id=CKPT, filename="dataset_statistics.json")) as f:
            vla.norm_stats = json.load(f)
    assert TASK_SUITE in vla.norm_stats, f"{TASK_SUITE} not in {list(vla.norm_stats.keys())}"
    print(f"[m4] norm_stats keys: {list(vla.norm_stats.keys())}")

    per_task, total_ep, total_succ = [], 0, 0
    t_start = time.time()
    for task_id, task, init_states, env in envs:
        task_desc = task.language
        task_succ = 0
        for ep in range(args.trials):
            env.reset()
            dbg(f"ep{ep} reset done")
            obs = env.set_init_state(init_states[ep])
            dbg(f"ep{ep} init state set")
            t, done = 0, False
            while t < MAX_STEPS + NUM_STEPS_WAIT:
                try:
                    if t < NUM_STEPS_WAIT:
                        obs, _, done, _ = env.step([0, 0, 0, 0, 0, 0, -1])
                        if t == 0:
                            dbg("first dummy step ok")
                        t += 1
                        continue
                    img = get_libero_image(tf, obs, RESIZE)
                    if t == NUM_STEPS_WAIT:
                        dbg("first get_libero_image (tf) ok")
                    observation = {
                        "full_image": img,
                        "state": np.concatenate(
                            (obs["robot0_eef_pos"], quat2axisangle(np, obs["robot0_eef_quat"]), obs["robot0_gripper_qpos"])
                        ),
                    }
                    action = get_vla_action(tf, torch, Image, np, vla, processor, observation, task_desc, TASK_SUITE, dev)
                    if t == NUM_STEPS_WAIT:
                        dbg(f"first get_vla_action ok, action={action}")
                    action = normalize_gripper_action(np, action, binarize=True)
                    action = invert_gripper_action(action)
                    obs, _, done, _ = env.step(action.tolist())
                    if t == NUM_STEPS_WAIT:
                        dbg("first policy env.step ok")
                    if done:
                        break
                    t += 1
                except Exception as e:  # noqa: BLE001
                    print(f"[m4] task{task_id} ep{ep} exception: {e}")
                    break
            total_ep += 1
            if done:
                task_succ += 1
                total_succ += 1
            print(f"[m4] task{task_id} ep{ep}: {'SUCCESS' if done else 'fail'} ({t} steps)")
        env.close()
        per_task.append({"task_id": task_id, "task": task.name, "episodes": args.trials, "successes": task_succ})
        print(f"[m4] task{task_id} '{task.name}': {task_succ}/{args.trials}")

    out = {
        "checkpoint": CKPT, "task_suite": TASK_SUITE, "attn_implementation": "sdpa",
        "num_tasks": n_tasks, "trials_per_task": args.trials, "seed": args.seed,
        "total_episodes": total_ep, "total_successes": total_succ,
        "success_rate": round(total_succ / max(total_ep, 1), 3),
        "elapsed_s": round(time.time() - t_start, 1), "per_task": per_task,
    }
    print("[m4] RESULT", json.dumps(out, ensure_ascii=False))
    (VERIFY / "m4-eval.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
