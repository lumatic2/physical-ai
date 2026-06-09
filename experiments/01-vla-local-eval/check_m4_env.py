"""check_m4_env.py — M4 선행: LIBERO import + benchmark 레지스트리 + mujoco EGL headless 검증."""
import os
os.environ.setdefault("MUJOCO_GL", "egl")

print("[env] MUJOCO_GL=", os.environ.get("MUJOCO_GL"))

import numpy as np
print("[env] numpy", np.__version__)

import mujoco
print("[env] mujoco", mujoco.__version__)

from libero.libero import benchmark
bdict = benchmark.get_benchmark_dict()
print("[env] libero benchmarks:", list(bdict.keys()))

# libero_spatial 태스크 수 확인
suite = bdict["libero_spatial"]()
print("[env] libero_spatial n_tasks:", suite.n_tasks)
print("[env] task[0]:", suite.get_task(0).name)
print("[env] OK")
