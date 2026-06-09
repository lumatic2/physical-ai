"""check_m4_render.py — M4 선행: LIBERO OffScreenRenderEnv 가 WSL2 EGL 헤드리스로 실제 렌더되는지.
14GB finetuned 체크포인트 다운로드 전, 시뮬+렌더 경로가 살아있는지 확인 (실패 시 M4 자체 불가)."""
import os
os.environ.setdefault("MUJOCO_GL", "egl")

import numpy as np
from libero.libero import benchmark, get_libero_path
from libero.libero.envs import OffScreenRenderEnv

bd = benchmark.get_benchmark_dict()
suite = bd["libero_spatial"]()
task = suite.get_task(0)
bddl = os.path.join(get_libero_path("bddl_files"), task.problem_folder, task.bddl_file)
print("[render] task:", task.name)
print("[render] bddl:", bddl)

env = OffScreenRenderEnv(bddl_file_name=bddl, camera_heights=256, camera_widths=256)
env.seed(0)
obs = env.reset()
img = obs["agentview_image"]
print("[render] agentview_image shape:", img.shape, "dtype:", img.dtype)
print("[render] pixel stats: min", int(img.min()), "max", int(img.max()), "mean", round(float(img.mean()), 1))
# 렌더가 살아있으면 픽셀이 전부 0이 아님 (비어있지 않은 장면)
ok = img.shape == (256, 256, 3) and int(img.max()) > 0
print("[render]", "PASS" if ok else "FAIL", "- EGL headless render produces non-empty frame")
env.close()
