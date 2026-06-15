"""Evaluate a scripted G1 squat baseline from the compiled behavior spec.

This is the pre-RL baseline for M19. It verifies that the target skill is
physically representable in the current G1 scene before a custom reward wrapper
spends GPU time.
"""

from __future__ import annotations

import json
from pathlib import Path

import mujoco
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_policy.xml"
SPEC = ROOT / "experiments/14-skill-authoring/verify/g1_squat.compiled.json"
VERIFY = Path(__file__).resolve().parent / "verify"


def lerp(a: np.ndarray, b: np.ndarray, alpha: float) -> np.ndarray:
    return a * (1.0 - alpha) + b * alpha


def joint_limit_violation(model: mujoco.MjModel, data: mujoco.MjData) -> float:
    worst = 0.0
    for jid in range(model.njnt):
        if model.jnt_type[jid] == mujoco.mjtJoint.mjJNT_FREE:
            continue
        qadr = model.jnt_qposadr[jid]
        lo, hi = model.jnt_range[jid]
        q = data.qpos[qadr]
        if q < lo:
            worst = max(worst, float(lo - q))
        elif q > hi:
            worst = max(worst, float(q - hi))
    return worst


def run_variant(model: mujoco.MjModel, spec: dict, name: str, start: np.ndarray, squat: np.ndarray) -> dict:
    model = mujoco.MjModel.from_xml_path(str(SCENE))
    data = mujoco.MjData(model)

    key = model.keyframe("knees_bent")
    data.qpos[:] = key.qpos
    data.ctrl[:] = key.ctrl
    mujoco.mj_forward(model, data)

    dt = float(model.opt.timestep)
    horizon_s = float(spec["done_conditions"]["max_time_s"])
    steps = int(horizon_s / dt)
    descend = int(2.0 / dt)
    hold = int(1.0 / dt)
    ascend_start = descend + hold
    energy = 0.0
    samples = []
    min_height = float("inf")
    max_joint_violation = 0.0
    fell_at = None

    for step in range(steps):
        if step < descend:
            target = lerp(start, squat, step / max(descend - 1, 1))
        elif step < ascend_start:
            target = squat
        else:
            alpha = (step - ascend_start) / max(steps - ascend_start - 1, 1)
            target = lerp(squat, start, alpha)

        data.ctrl[:] = target
        mujoco.mj_step(model, data)
        height = float(data.qpos[2])
        min_height = min(min_height, height)
        max_joint_violation = max(max_joint_violation, joint_limit_violation(model, data))
        energy += float(np.sum(np.square(data.ctrl)) * dt)

        quat = data.qpos[3:7]
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, quat)
        up_z = float(mat.reshape(3, 3)[2, 2])
        fallen = height < spec["done_conditions"]["min_base_height_m"] or up_z < 0.35
        if fallen and fell_at is None:
            fell_at = step * dt
        if step % int(0.2 / dt) == 0:
            samples.append(
                {
                    "t": round(step * dt, 3),
                    "base_height": height,
                    "up_z": up_z,
                    "target_knee": float(target[3]),
                    "joint_limit_violation": max_joint_violation,
                }
            )

    result = {
        "source_spec": "experiments/14-skill-authoring/verify/g1_squat.compiled.json",
        "scene": "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_policy.xml",
        "horizon_s": horizon_s,
        "min_height": min_height,
        "target_min_height": spec["done_conditions"]["min_base_height_m"],
        "max_joint_limit_violation": max_joint_violation,
        "energy_proxy": energy,
        "fell_at": fell_at,
        "variant": name,
        "verdict": "PASS" if fell_at is None and max_joint_violation <= 1e-6 else "FAIL",
        "samples": samples,
    }
    return result


def main() -> None:
    VERIFY.mkdir(parents=True, exist_ok=True)
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    model = mujoco.MjModel.from_xml_path(str(SCENE))
    key = model.keyframe("knees_bent")
    start = key.ctrl.copy()

    # Joint order follows scene ctrl: L leg 6, R leg 6, waist 3, L arm 7, R arm 7.
    mild = start.copy()
    for offset in (0, 6):
        mild[offset + 0] = -0.40
        mild[offset + 3] = 0.82
        mild[offset + 4] = -0.42
    mild[14] = 0.10

    deep = start.copy()
    for offset in (0, 6):
        deep[offset + 0] = -0.62
        deep[offset + 3] = 1.18
        deep[offset + 4] = -0.58
    deep[14] = 0.18

    variants = [
        run_variant(model, spec, "hold_knees_bent", start, start),
        run_variant(model, spec, "mild_squat", start, mild),
        run_variant(model, spec, "deep_squat", start, deep),
    ]
    result = {
        "source_spec": "experiments/14-skill-authoring/verify/g1_squat.compiled.json",
        "scene": "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_policy.xml",
        "variants": variants,
        "best_variant": next((v["variant"] for v in variants if v["verdict"] == "PASS"), None),
        "verdict": "PASS" if any(v["verdict"] == "PASS" for v in variants) else "FAIL",
        "next": "Open-loop position control is only a baseline. If all variants fail, M19 must start with balance reward/controller stabilization before squat RL.",
    }
    (VERIFY / "g1-squat-scripted-baseline.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    report = [
        "# G1 Squat Scripted Baseline",
        "",
        f"- Verdict: {result['verdict']}",
        f"- Best variant: {result['best_variant']}",
        "",
        "| Variant | Verdict | Min height | Fell at | Max joint-limit violation |",
        "|---|---|---:|---:|---:|",
    ]
    for variant in variants:
        report.append(
            f"| {variant['variant']} | {variant['verdict']} | {variant['min_height']:.3f} | "
            f"{variant['fell_at'] if variant['fell_at'] is not None else 'never'} | "
            f"{variant['max_joint_limit_violation']:.6f} |"
        )
    report.extend([
        "",
        "This is not a learned policy. It is the native feasibility baseline for the first G1 custom skill.",
        "",
    ])
    (VERIFY / "g1-squat-scripted-baseline.md").write_text("\n".join(report), encoding="utf-8")
    print(result["verdict"], "best_variant=", result["best_variant"])


if __name__ == "__main__":
    main()
