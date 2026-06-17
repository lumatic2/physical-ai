#!/usr/bin/env python3
"""Record a headless Unitree MuJoCo G1 rollout as a web replay trajectory."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import mujoco


DEFAULT_SCENE = "g1/scene_g1_policy.xml"
EXPECTED_NQ = 36
EXPECTED_NU = 29


def finite_matrix(values: list[list[float]]) -> bool:
    return all(math.isfinite(v) for row in values for v in row)


def record_headless(
    unitree_root: Path,
    seconds: float,
    fps: float,
    kp: float,
    kd: float,
    scene: str,
    elastic_band: bool,
    band_length: float,
    band_stiffness: float,
    band_damping: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    xml_path = unitree_root / "unitree_robots" / "g1" / "scene.xml"
    model = mujoco.MjModel.from_xml_path(str(xml_path))
    data = mujoco.MjData(model)

    if model.nq != EXPECTED_NQ or model.nu != EXPECTED_NU:
        raise ValueError(f"expected Unitree G1 nq={EXPECTED_NQ}, nu={EXPECTED_NU}; got nq={model.nq}, nu={model.nu}")

    mujoco.mj_resetData(model, data)
    data.qpos[:] = model.qpos0
    data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)

    desired = [float(v) for v in data.qpos[7 : 7 + model.nu]]
    band_body_id = -1
    if elastic_band:
        band_body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "torso_link")
        if band_body_id < 0:
            raise ValueError("elastic band requested but body 'torso_link' was not found")
    dt = float(model.opt.timestep)
    substeps = max(1, round((1.0 / fps) / dt))
    nframes = max(1, round(seconds * fps))
    qpos_frames: list[list[float]] = []

    for _ in range(nframes):
        qpos_frames.append([float(v) for v in data.qpos])
        for _ in range(substeps):
            data.xfrc_applied[:] = 0.0
            if elastic_band:
                point = [0.0, 0.0, 3.0]
                dx = [point[i] - float(data.qpos[i]) for i in range(3)]
                distance = math.sqrt(sum(v * v for v in dx))
                if distance > 1e-9:
                    direction = [v / distance for v in dx]
                    velocity = sum(float(data.qvel[i]) * direction[i] for i in range(3))
                    force_mag = band_stiffness * (distance - band_length) - band_damping * velocity
                    for i in range(3):
                        data.xfrc_applied[band_body_id, i] = force_mag * direction[i]
            for i in range(model.nu):
                q_err = desired[i] - float(data.qpos[7 + i])
                dq = float(data.qvel[6 + i])
                data.ctrl[i] = kp * q_err - kd * dq
            mujoco.mj_step(model, data)

    heights = [frame[2] for frame in qpos_frames]
    output = {
        "fps": fps,
        "nq": int(model.nq),
        "scene": scene,
        "note": "Headless Unitree MuJoCo G1 qpos rollout converted directly to the physical-ai web trajectory contract.",
        "source_attempt": "unitree-mujoco-headless-elastic-stand" if elastic_band else "unitree-mujoco-headless-pd-hold",
        "qpos": qpos_frames,
    }
    summary = {
        "verdict": "PASS" if finite_matrix(qpos_frames) else "FAIL_NAN",
        "source": "unitreerobotics/unitree_mujoco/unitree_robots/g1/scene.xml",
        "source_kind": "unitree_mujoco_headless_runtime",
        "contract": "physical-ai-web-trajectory-v1",
        "frames": len(qpos_frames),
        "fps": fps,
        "duration_s": len(qpos_frames) / fps,
        "model_timestep_s": dt,
        "substeps_per_frame": substeps,
        "nq": int(model.nq),
        "nu": int(model.nu),
        "nv": int(model.nv),
        "kp": kp,
        "kd": kd,
        "elastic_band": elastic_band,
        "band_length": band_length if elastic_band else None,
        "band_stiffness": band_stiffness if elastic_band else None,
        "band_damping": band_damping if elastic_band else None,
        "start_height_m": heights[0],
        "min_height_m": min(heights),
        "max_height_m": max(heights),
        "end_height_m": heights[-1],
        "root_height_drop_m": heights[0] - min(heights),
        "finite_valid": finite_matrix(qpos_frames),
        "scene": scene,
        "source_xml": str(xml_path),
        "next_required_evidence": "Register this trajectory in the web registry and run local browser replay QA, or replace the PD hold with DDS LowCmd/LowState runtime capture.",
    }
    return output, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unitree-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--seconds", type=float, default=2.0)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--kp", type=float, default=80.0)
    parser.add_argument("--kd", type=float, default=3.0)
    parser.add_argument("--elastic-band", action="store_true")
    parser.add_argument("--band-length", type=float, default=0.5)
    parser.add_argument("--band-stiffness", type=float, default=200.0)
    parser.add_argument("--band-damping", type=float, default=100.0)
    parser.add_argument("--scene", default=DEFAULT_SCENE)
    args = parser.parse_args()

    trajectory, summary = record_headless(
        unitree_root=args.unitree_root,
        seconds=args.seconds,
        fps=args.fps,
        kp=args.kp,
        kd=args.kd,
        scene=args.scene,
        elastic_band=args.elastic_band,
        band_length=args.band_length,
        band_stiffness=args.band_stiffness,
        band_damping=args.band_damping,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(trajectory, indent=2) + "\n", encoding="utf-8")
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
