#!/usr/bin/env python3
"""Probe whether upstream motor-actuated G1 XMLs make G1 Moves policy viable.

Previous adapters ran a torque-oriented public policy against the local
position-actuated web scene. This experiment keeps the policy/observation
contract close to upstream and changes the model side to public motor-actuated
G1 XML candidates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

import mujoco
import numpy as np
import onnxruntime as ort


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify" / "g1-upstream-motor-xml-squat-policy-probe"
MESH_SOURCE = ROOT / "experiments/03-digital-twin/web/assets/scenes/g1/assets"
BASE = "https://huggingface.co/datasets/exptech/g1-moves/resolve/main/dance/J_Dance4_Broadway"
ONNX_URL = f"{BASE}/policy/J_Dance4_Broadway_policy.onnx"
NPZ_URL = f"{BASE}/training/J_Dance4_Broadway.npz"
ACCESS_DATE = "2026-06-18"

XML_CANDIDATES = [
    {
        "name": "unitree_ros_g1_29dof",
        "url": "https://raw.githubusercontent.com/unitreerobotics/unitree_ros/master/robots/g1_description/g1_29dof_rev_1_0.xml",
    },
    {
        "name": "roboJudo_g1_29dof",
        "url": "https://raw.githubusercontent.com/HansZ8/RoboJuDo/release/assets/robots/g1/g1_29dof_rev_1_0.xml",
    },
]

KP = np.array(
    [
        40.2, 99.1, 40.2, 99.1, 28.6, 28.6,
        40.2, 99.1, 40.2, 99.1, 28.6, 28.6,
        40.2, 28.6, 28.6,
        14.3, 14.3, 14.3, 14.3, 14.3, 16.8, 16.8,
        14.3, 14.3, 14.3, 14.3, 14.3, 16.8, 16.8,
    ],
    dtype=np.float32,
)
KD = np.array(
    [
        2.6, 6.3, 2.6, 6.3, 1.8, 1.8,
        2.6, 6.3, 2.6, 6.3, 1.8, 1.8,
        2.6, 1.8, 1.8,
        0.9, 0.9, 0.9, 0.9, 0.9, 1.1, 1.1,
        0.9, 0.9, 0.9, 0.9, 0.9, 1.1, 1.1,
    ],
    dtype=np.float32,
)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "physical-ai-exp100/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def quat_to_rot_matrix(quat_wxyz: np.ndarray) -> np.ndarray:
    w, x, y, z = quat_wxyz
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def upstream_6d(rot_matrix: np.ndarray) -> np.ndarray:
    return rot_matrix[:, :2].T.flatten()


def make_obs(model: mujoco.MjModel, data: mujoco.MjData, motion: dict[str, np.ndarray], frame: int, last_action: np.ndarray) -> np.ndarray:
    robot_pos = data.qpos[:3].copy()
    robot_quat = data.qpos[3:7].copy()
    r_robot = quat_to_rot_matrix(robot_quat)
    anchor_pos_b = r_robot.T @ (motion["body_pos_w"][frame, 0].astype(np.float64) - robot_pos)
    anchor_ori_b = upstream_6d(r_robot.T @ quat_to_rot_matrix(motion["body_quat_w"][frame, 0].astype(np.float64)))

    if data.sensordata.size >= 6:
        base_ang_vel = data.sensordata[:3].astype(np.float32)
        base_lin_vel = data.sensordata[3:6].astype(np.float32)
    else:
        base_ang_vel = np.zeros(3, dtype=np.float32)
        base_lin_vel = data.qvel[:3].astype(np.float32)

    return np.concatenate(
        [
            motion["joint_pos"][frame].astype(np.float32),
            motion["joint_vel"][frame].astype(np.float32),
            anchor_pos_b.astype(np.float32),
            anchor_ori_b.astype(np.float32),
            base_ang_vel,
            base_lin_vel,
            data.qpos[7:36].astype(np.float32),
            data.qvel[6:35].astype(np.float32),
            last_action.astype(np.float32),
        ]
    ).astype(np.float32)


def name_id(model: mujoco.MjModel, obj_type: int, name: str) -> int | None:
    found = mujoco.mj_name2id(model, obj_type, name)
    return None if found < 0 else int(found)


def joint_qpos_index(model: mujoco.MjModel, name: str) -> int:
    jid = name_id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    if jid is None:
        raise KeyError(name)
    return int(model.jnt_qposadr[jid])


def actuator_type_counts(model: mujoco.MjModel) -> dict[str, int]:
    counts: dict[str, int] = {}
    for i in range(model.nu):
        transmission = int(model.actuator_trntype[i])
        dyn = int(model.actuator_dyntype[i])
        gain = int(model.actuator_gaintype[i])
        key = f"trn{transmission}/dyn{dyn}/gain{gain}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def prepare_xml_workspace(tmp: Path, candidate: dict[str, str], xml_blob: bytes) -> Path:
    work = tmp / candidate["name"]
    meshes = work / "meshes"
    meshes.mkdir(parents=True, exist_ok=True)
    for mesh in MESH_SOURCE.glob("*.STL"):
        shutil.copy2(mesh, meshes / mesh.name)
    text = xml_blob.decode("utf-8")
    if "name=\"floor\"" not in text:
        floor = '\n    <geom name="floor" size="0 0 0.05" type="plane" rgba="0.35 0.35 0.35 1"/>\n'
        text = text.replace("<worldbody>", "<worldbody>" + floor, 1)
    xml_path = work / "g1_29dof_rev_1_0.xml"
    xml_path.write_text(text, encoding="utf-8")
    return xml_path


def init_from_motion(model: mujoco.MjModel, data: mujoco.MjData, motion: dict[str, np.ndarray]) -> None:
    data.qpos[:3] = motion["body_pos_w"][0, 0]
    data.qpos[3:7] = motion["body_quat_w"][0, 0]
    data.qpos[7:36] = motion["joint_pos"][0]
    data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)


def visible_gate(run: dict[str, Any]) -> bool:
    return (
        run["fell_at"] is None
        and run["visible_drop"] >= 0.08
        and run["max_knee_delta_rad"] >= 0.60
        and run["max_hip_pitch_delta_rad"] >= 0.35
        and run["return_to_stand"]
    )


def run_policy(candidate: dict[str, str], model: mujoco.MjModel, sess: ort.InferenceSession, motion: dict[str, np.ndarray], seconds: float, out_dir: Path) -> dict[str, Any]:
    data = mujoco.MjData(model)
    model.opt.timestep = 0.005
    init_from_motion(model, data, motion)
    input_name = sess.get_inputs()[0].name
    last_action = np.zeros(29, dtype=np.float32)
    fps = float(np.asarray(motion["fps"]).reshape(-1)[0])
    ctrl_dt = 0.02
    total_steps = int(seconds / ctrl_dt)
    start_qpos = data.qpos.copy()
    start_height = float(data.qpos[2])
    knee_indices = [joint_qpos_index(model, "left_knee_joint"), joint_qpos_index(model, "right_knee_joint")]
    hip_indices = [joint_qpos_index(model, "left_hip_pitch_joint"), joint_qpos_index(model, "right_hip_pitch_joint")]
    foot_body_ids = [
        name_id(model, mujoco.mjtObj.mjOBJ_BODY, "left_ankle_roll_link"),
        name_id(model, mujoco.mjtObj.mjOBJ_BODY, "right_ankle_roll_link"),
    ]
    foot_body_ids = [i for i in foot_body_ids if i is not None]
    initial_foot_xy = np.array([data.xpos[i, :2].copy() for i in foot_body_ids]) if foot_body_ids else np.zeros((0, 2))

    samples: list[dict[str, Any]] = []
    qpos_frames: list[list[float]] = []
    min_height = start_height
    final_height = start_height
    fell_at = None
    max_knee = 0.0
    max_hip = 0.0
    max_slip = 0.0
    action_min = float("inf")
    action_max = -float("inf")
    obs_abs_max = 0.0
    first_action: list[float] | None = None
    first_obs80: list[float] | None = None

    for step in range(total_steps):
        frame = int((step * ctrl_dt * fps) % motion["joint_pos"].shape[0])
        obs = make_obs(model, data, motion, frame, last_action)
        action = sess.run(["actions"], {input_name: obs[None, :]})[0][0].astype(np.float32)
        if first_action is None:
            first_action = [float(v) for v in action]
            first_obs80 = [float(v) for v in obs[:80]]
        obs_abs_max = max(obs_abs_max, float(np.max(np.abs(obs))))
        action_min = min(action_min, float(np.min(action)))
        action_max = max(action_max, float(np.max(action)))
        torques = KP * (action - data.qpos[7:36].astype(np.float32)) - KD * data.qvel[6:35].astype(np.float32)
        data.ctrl[:29] = torques
        for _ in range(4):
            mujoco.mj_step(model, data)

        last_action = action
        height = float(data.qpos[2])
        final_height = height
        min_height = min(min_height, height)
        max_knee = max(max_knee, *(abs(float(data.qpos[i] - start_qpos[i])) for i in knee_indices))
        max_hip = max(max_hip, *(abs(float(data.qpos[i] - start_qpos[i])) for i in hip_indices))
        if foot_body_ids:
            foot_xy = np.array([data.xpos[i, :2].copy() for i in foot_body_ids])
            max_slip = max(max_slip, float(np.max(np.linalg.norm(foot_xy - initial_foot_xy, axis=1))))
        mat = np.empty(9)
        mujoco.mju_quat2Mat(mat, data.qpos[3:7])
        up_z = float(mat.reshape(3, 3)[2, 2])
        if fell_at is None and (height < 0.45 or up_z < 0.30):
            fell_at = round(step * ctrl_dt, 3)
        if step % 10 == 0:
            samples.append(
                {
                    "t": round(step * ctrl_dt, 3),
                    "height": height,
                    "visible_drop": start_height - height,
                    "knee_delta": max_knee,
                    "hip_delta": max_hip,
                    "foot_slip_body_xy": max_slip,
                    "up_z": up_z,
                    "action_min": float(np.min(action)),
                    "action_max": float(np.max(action)),
                }
            )
        qpos_frames.append([float(v) for v in data.qpos[: model.nq]])

    run = {
        "candidate": candidate,
        "nq": int(model.nq),
        "nv": int(model.nv),
        "nu": int(model.nu),
        "nsensor": int(model.nsensor),
        "actuator_type_counts": actuator_type_counts(model),
        "start_height": start_height,
        "min_height": min_height,
        "visible_drop": start_height - min_height,
        "fell_at": fell_at,
        "final_height": final_height,
        "return_to_stand": final_height >= start_height - 0.03,
        "max_knee_delta_rad": max_knee,
        "max_hip_pitch_delta_rad": max_hip,
        "foot_slip_body_xy": max_slip,
        "action_min": action_min,
        "action_max": action_max,
        "obs_abs_max": obs_abs_max,
        "first_action29": first_action,
        "first_obs80": first_obs80,
        "samples": samples,
    }
    run["visible_8cm_gate"] = visible_gate(run)
    run["visible_verdict"] = "PASS_VISIBLE_NATIVE" if run["visible_8cm_gate"] else ("FAIL_FALL" if fell_at is not None else "FAIL_VISIBLE_GATE")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "native-eval.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    (out_dir / "native_rollout_qpos_trajectory.json").write_text(
        json.dumps(
            {
                "schema": "physical-ai-native-qpos-trajectory-v1",
                "source": "g1-upstream-motor-xml-squat-policy-probe",
                "candidate": candidate["name"],
                "fps": 50,
                "nq": int(model.nq),
                "frames": len(qpos_frames),
                "qpos": qpos_frames,
            }
        ),
        encoding="utf-8",
    )
    return run


def write_summary(result: dict[str, Any]) -> None:
    lines = [
        "# G1 Upstream Motor XML Squat Policy Probe Summary",
        "",
        "| Candidate | Compile | Verdict | Drop | Knee | Hip | Fell | Action range | Obs max | Sensors |",
        "|---|---|---|---:|---:|---:|---|---|---:|---:|",
    ]
    for run in result["runs"]:
        if run.get("compile_error"):
            lines.append(f"| {run['candidate']['name']} | FAIL | COMPILE_ERROR | - | - | - | - | - | - | - |")
            continue
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {run['candidate']['name']} | PASS | {run['visible_verdict']} | {run['visible_drop']:.3f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | {fell} | "
            f"{run['action_min']:.2f}..{run['action_max']:.2f} | {run['obs_abs_max']:.2f} | {run['nsensor']} |"
        )
    lines.extend(["", f"Verdict: **{result['verdict']}**", ""])
    (VERIFY / "g1-upstream-motor-xml-squat-policy-summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    VERIFY.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="g1_exp100_") as tmp_name:
        tmp = Path(tmp_name)
        onnx_blob = fetch(ONNX_URL)
        npz_blob = fetch(NPZ_URL)
        onnx_path = tmp / "policy.onnx"
        npz_path = tmp / "motion.npz"
        onnx_path.write_bytes(onnx_blob)
        npz_path.write_bytes(npz_blob)
        sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        with np.load(npz_path) as motion_npz:
            motion = {key: motion_npz[key].copy() for key in motion_npz.files}

        runs: list[dict[str, Any]] = []
        xml_artifacts = []
        for candidate in XML_CANDIDATES:
            xml_blob = fetch(candidate["url"])
            xml_artifacts.append(
                {
                    "name": candidate["name"],
                    "url": candidate["url"],
                    "accessed": ACCESS_DATE,
                    "sha256": sha256(xml_blob),
                    "size_bytes": len(xml_blob),
                }
            )
            try:
                xml_path = prepare_xml_workspace(tmp, candidate, xml_blob)
                model = mujoco.MjModel.from_xml_path(str(xml_path))
                run = run_policy(candidate, model, sess, motion, args.seconds, VERIFY / candidate["name"])
            except Exception as exc:  # compile/runtime errors are experiment evidence.
                run = {"candidate": candidate, "compile_error": repr(exc), "visible_8cm_gate": False}
                out = VERIFY / candidate["name"]
                out.mkdir(parents=True, exist_ok=True)
                (out / "native-eval.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
            runs.append(run)

    visible = [run for run in runs if run.get("visible_8cm_gate")]
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 policy route now tests public G1 motor-actuator XML parity before additional controller tweaks.",
            "perspectives": {
                "product": "checks whether the target robot class has public evidence and a compatible model path for squat",
                "architecture": "separates local browser position-actuator limitations from upstream motor-actuated policy semantics",
                "security": "downloads public XML/ONNX/NPZ artifacts only and stores hashes, not vendored binaries",
                "qa": "native rollout records fall/drop/knee/hip/action/obs metrics; browser replay stays gated",
                "skeptic": "public XML candidates may still differ from the exact g1_mode15_square.xml used by G1 Moves",
            },
            "dod": [
                "web evidence supports G1 squat feasibility",
                "public motor-actuated XML candidate compiles",
                "same ONNX policy runs natively or records the mismatch as evidence",
            ],
        },
        "sources": [
            {"url": "https://www.unitree.com/g1/", "accessed": ACCESS_DATE},
            {"url": "https://robotsguide.com/robots/unitree-g1", "accessed": ACCESS_DATE},
            {"url": "https://hub-robot.github.io/", "accessed": ACCESS_DATE},
            {"url": "https://arxiv.org/html/2505.07294v1", "accessed": ACCESS_DATE},
        ],
        "artifacts": {
            "onnx": {"url": ONNX_URL, "accessed": ACCESS_DATE, "sha256": sha256(onnx_blob), "size_bytes": len(onnx_blob)},
            "npz": {"url": NPZ_URL, "accessed": ACCESS_DATE, "sha256": sha256(npz_blob), "size_bytes": len(npz_blob)},
            "xml": xml_artifacts,
        },
        "runs": runs,
        "verdict": "PASS_VISIBLE_NATIVE__BROWSER_REPLAY_REQUIRED" if visible else "FAIL_VISIBLE_NATIVE",
        "next": "If both public motor XMLs fail, locate the exact G1 Moves g1_mode15_square.xml or build a local motor-actuated web scene adapter before browser replay.",
    }
    (VERIFY / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_summary(result)
    print(json.dumps({"verdict": result["verdict"], "visible_candidates": [run["candidate"]["name"] for run in visible]}, indent=2))
    return 0 if visible else 1


if __name__ == "__main__":
    raise SystemExit(main())
