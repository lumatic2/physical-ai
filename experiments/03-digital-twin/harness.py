"""Digital-twin experiment harness — single source of truth for "what to run".

An *experiment* = (scene MJCF, recorded trajectory, camera, end-effector body). All of
it lives in experiments.json so smoke/render/record (and the web) read one registry
instead of hardcoding the SO-100 scene. Adding a new embodiment/task = one JSON entry
+ a trajectory (scripted IK like make_pick_trajectory.py, or the generic physics
recorder record_trajectory.py). The replay format (qpos frames) is the universal
interchange — desktop mp4 and web replay both just set qpos + mj_forward.

Scene paths resolve under either asset root, so menagerie models and the web-bundled
self-contained scenes (e.g. humanoid.xml) both work without per-environment config."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "experiments.json"
SCENE_ROOTS = [HERE / "vendor" / "mujoco_menagerie", HERE / "web" / "assets" / "scenes"]


def load_registry():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def resolve_scene(rel):
    for root in SCENE_ROOTS:
        p = root / rel
        if p.exists():
            return p
    roots = ", ".join(str(r) for r in SCENE_ROOTS)
    raise FileNotFoundError(f"scene '{rel}' not found under any root: {roots}")


def get_experiment(name=None):
    """Return the experiment config dict with resolved absolute paths."""
    reg = load_registry()
    name = name or reg["default"]
    if name not in reg["experiments"]:
        avail = ", ".join(reg["experiments"])
        raise KeyError(f"experiment '{name}' not in registry. available: {avail}")
    exp = dict(reg["experiments"][name])
    exp["name"] = name
    exp["scene_path"] = resolve_scene(exp["scene"])
    exp["trajectory_path"] = HERE / exp["trajectory"]
    return exp
