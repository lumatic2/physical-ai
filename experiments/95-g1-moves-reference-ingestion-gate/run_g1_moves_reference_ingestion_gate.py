"""Ingest G1 Moves retargeted reference clips into the local G1 trajectory contract."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import mujoco
import numpy as np


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify" / "g1-moves-reference-ingestion-gate"
EXP67_PATH = ROOT / "experiments/67-g1-qfrc-wbc-return-selector/run_qfrc_wbc_return_selector.py"
CONTRACT_CHECKER = ROOT / "experiments/33-unitree-mujoco-g1-bridge-probe/check_web_trajectory_contract.py"
MANIFEST_URL = "https://huggingface.co/datasets/exptech/g1-moves/resolve/main/manifest.json"
DATASET_BASE = "https://huggingface.co/datasets/exptech/g1-moves/resolve/main"

G1_MOVES_JOINTS = [
    "left_hip_pitch",
    "left_hip_roll",
    "left_hip_yaw",
    "left_knee",
    "left_ankle_pitch",
    "left_ankle_roll",
    "right_hip_pitch",
    "right_hip_roll",
    "right_hip_yaw",
    "right_knee",
    "right_ankle_pitch",
    "right_ankle_roll",
    "waist_yaw",
    "waist_roll",
    "waist_pitch",
    "left_shoulder_pitch",
    "left_shoulder_roll",
    "left_shoulder_yaw",
    "left_elbow",
    "left_wrist_roll",
    "left_wrist_pitch",
    "left_wrist_yaw",
    "right_shoulder_pitch",
    "right_shoulder_roll",
    "right_shoulder_yaw",
    "right_elbow",
    "right_wrist_roll",
    "right_wrist_pitch",
    "right_wrist_yaw",
]

LOCAL_JOINTS = [
    "left_hip_pitch_joint",
    "left_hip_roll_joint",
    "left_hip_yaw_joint",
    "left_knee_joint",
    "left_ankle_pitch_joint",
    "left_ankle_roll_joint",
    "right_hip_pitch_joint",
    "right_hip_roll_joint",
    "right_hip_yaw_joint",
    "right_knee_joint",
    "right_ankle_pitch_joint",
    "right_ankle_roll_joint",
    "waist_yaw_joint",
    "waist_roll_joint",
    "waist_pitch_joint",
    "left_shoulder_pitch_joint",
    "left_shoulder_roll_joint",
    "left_shoulder_yaw_joint",
    "left_elbow_joint",
    "left_wrist_roll_joint",
    "left_wrist_pitch_joint",
    "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint",
    "right_shoulder_roll_joint",
    "right_shoulder_yaw_joint",
    "right_elbow_joint",
    "right_wrist_roll_joint",
    "right_wrist_pitch_joint",
    "right_wrist_yaw_joint",
]


def load_exp67():
    spec = importlib.util.spec_from_file_location("exp67_qfrc_wbc", EXP67_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP67_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_csv_matrix(url: str, max_rows: int | None = None) -> np.ndarray:
    with urlopen(url, timeout=60) as response:
        text = response.read().decode("utf-8")
    rows: list[list[float]] = []
    for idx, row in enumerate(csv.reader(text.splitlines())):
        if max_rows is not None and idx >= max_rows:
            break
        if not row:
            continue
        rows.append([float(value) for value in row])
    return np.asarray(rows, dtype=np.float64)


def clip_url(clip_name: str, category: str) -> str:
    return f"{DATASET_BASE}/{category}/{clip_name}/retarget/{clip_name}.csv"


def score_clip(name: str, clip: dict[str, Any]) -> dict[str, Any]:
    mins = np.asarray(clip["joint_range"]["min"], dtype=np.float64)
    maxs = np.asarray(clip["joint_range"]["max"], dtype=np.float64)
    knee_range = float(max(maxs[3] - mins[3], maxs[9] - mins[9]))
    hip_pitch_range = float(max(maxs[0] - mins[0], maxs[6] - mins[6]))
    knee_max = float(max(maxs[3], maxs[9]))
    hip_pitch_min = float(min(mins[0], mins[6]))
    static_gate_like = knee_range >= 0.60 and hip_pitch_range >= 0.35 and knee_max >= 0.60
    return {
        "clip": name,
        "category": clip["category"],
        "duration_s": clip["duration_s"],
        "frames": clip["frames"],
        "fps": clip["fps"],
        "has_policy": clip["has_policy"],
        "knee_range_rad": knee_range,
        "hip_pitch_range_rad": hip_pitch_range,
        "knee_max_rad": knee_max,
        "hip_pitch_min_rad": hip_pitch_min,
        "mean_joint_velocity": clip["motion_stats"]["mean_joint_velocity"],
        "max_joint_velocity": clip["motion_stats"]["max_joint_velocity"],
        "root_displacement_m": clip["motion_stats"]["root_displacement_m"],
        "score": knee_range * 2.0 + hip_pitch_range + max(0.0, knee_max) - 0.002 * clip["motion_stats"]["max_joint_velocity"],
        "static_gate_like": static_gate_like,
    }


def local_joint_order_check(model: mujoco.MjModel) -> dict[str, Any]:
    qpos_names = []
    missing = []
    qpos_indices = []
    for name in LOCAL_JOINTS:
        try:
            joint_id = model.joint(name).id
        except KeyError:
            missing.append(name)
            qpos_indices.append(None)
            continue
        qpos_names.append(name)
        qpos_indices.append(int(model.jnt_qposadr[joint_id]))
    expected = list(range(7, 36))
    return {
        "expected_g1_moves_joint_count": len(G1_MOVES_JOINTS),
        "local_joint_count": len(qpos_names),
        "missing": missing,
        "qpos_indices": qpos_indices,
        "matches_qpos_7_to_35": qpos_indices == expected,
        "mapping": [
            {"g1_moves": src, "local": dst, "qpos_index": idx}
            for src, dst, idx in zip(G1_MOVES_JOINTS, LOCAL_JOINTS, qpos_indices)
        ],
    }


def best_window(matrix: np.ndarray, fps: int, window_s: float) -> dict[str, Any]:
    n = min(len(matrix), max(2, int(window_s * fps)))
    joints = matrix[:, 7:36]
    root_z = matrix[:, 2]
    best: dict[str, Any] | None = None
    for start in range(0, max(1, len(matrix) - n + 1), max(1, int(fps / 2))):
        end = min(len(matrix), start + n)
        segment = joints[start:end]
        root_segment = root_z[start:end]
        left_knee = segment[:, 3]
        right_knee = segment[:, 9]
        left_hip = segment[:, 0]
        right_hip = segment[:, 6]
        metrics = {
            "start_frame": start,
            "end_frame": end,
            "duration_s": (end - start) / fps,
            "root_height_drop_m": float(np.max(root_segment) - np.min(root_segment)),
            "left_knee_range_rad": float(np.max(left_knee) - np.min(left_knee)),
            "right_knee_range_rad": float(np.max(right_knee) - np.min(right_knee)),
            "left_hip_pitch_range_rad": float(np.max(left_hip) - np.min(left_hip)),
            "right_hip_pitch_range_rad": float(np.max(right_hip) - np.min(right_hip)),
            "max_knee_delta_rad": float(max(np.max(left_knee) - np.min(left_knee), np.max(right_knee) - np.min(right_knee))),
            "max_hip_pitch_delta_rad": float(max(np.max(left_hip) - np.min(left_hip), np.max(right_hip) - np.min(right_hip))),
            "knee_max_rad": float(max(np.max(left_knee), np.max(right_knee))),
            "hip_pitch_min_rad": float(min(np.min(left_hip), np.min(right_hip))),
        }
        metrics["reference_gate_like"] = (
            metrics["root_height_drop_m"] >= 0.08
            and metrics["max_knee_delta_rad"] >= 0.60
            and metrics["max_hip_pitch_delta_rad"] >= 0.35
        )
        metrics["score"] = (
            2.0 * metrics["max_knee_delta_rad"]
            + metrics["max_hip_pitch_delta_rad"]
            + metrics["root_height_drop_m"]
        )
        if best is None or metrics["score"] > best["score"]:
            best = metrics
    assert best is not None
    return best


def write_excerpt(matrix: np.ndarray, clip: str, category: str, fps: int, window: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    excerpt = matrix[int(window["start_frame"]) : int(window["end_frame"])]
    qpos = excerpt[:, :36].astype(float)
    trajectory = {
        "schema": "physical-ai-web-trajectory-v1",
        "source": "g1-moves-retarget-csv",
        "source_url": clip_url(clip, category),
        "scene": "g1/scene_g1_policy.xml",
        "robot": "unitree_g1",
        "fps": fps,
        "nq": 36,
        "frames": int(len(qpos)),
        "duration_s": float(len(qpos) / fps),
        "qpos": qpos.tolist(),
        "note": "Kinematic G1 Moves retargeted reference excerpt. This is not a native dynamics rollout.",
    }
    path = out_dir / "g1_moves_reference_excerpt_web_trajectory.json"
    path.write_text(json.dumps(trajectory), encoding="utf-8")
    return {
        "path": str(path.relative_to(ROOT)),
        "frames": trajectory["frames"],
        "duration_s": trajectory["duration_s"],
        "nq": trajectory["nq"],
    }


def run_contract_checker(path: Path) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("check_web_trajectory_contract", CONTRACT_CHECKER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {CONTRACT_CHECKER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    summary = module.validate_trajectory(module.load_json(path))
    (VERIFY / "web-trajectory-contract-check.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-s", type=float, default=6.0)
    parser.add_argument("--top-k", type=int, default=8)
    args = parser.parse_args()
    VERIFY.mkdir(parents=True, exist_ok=True)

    exp67 = load_exp67()
    env = exp67.EXP28.ContactAwareSquat(
        stage_height=0.67,
        controller_blend=0.5,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=1.0,
        config_overrides={"impl": "jax"},
    )
    order_check = local_joint_order_check(env.mj_model)

    manifest = fetch_json(MANIFEST_URL)
    skipped = [
        {"clip": name, "reason": "missing joint_range metadata"}
        for name, clip in manifest["clips"].items()
        if "joint_range" not in clip
    ]
    candidates = [
        score_clip(name, clip)
        for name, clip in manifest["clips"].items()
        if "joint_range" in clip
    ]
    candidates.sort(key=lambda item: item["score"], reverse=True)
    top = candidates[: args.top_k]
    selected = next((item for item in top if item["static_gate_like"] and item["has_policy"]), top[0])
    csv_url = clip_url(selected["clip"], selected["category"])
    matrix = fetch_csv_matrix(csv_url)
    if matrix.ndim != 2 or matrix.shape[1] != 36:
        raise RuntimeError(f"expected 36-column G1 Moves CSV, got shape {matrix.shape}")
    window = best_window(matrix, int(selected["fps"]), args.window_s)
    excerpt = write_excerpt(matrix, selected["clip"], selected["category"], int(selected["fps"]), window, VERIFY)
    contract = run_contract_checker(ROOT / excerpt["path"])

    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 uses external retargeted G1 motion/policy ingestion as the next reference-policy route after exp94 showed local controller injection cannot satisfy knee tracking.",
            "perspectives": {
                "product": "turns the web-found G1 motion-tracking route into a local artifact path instead of another scalar controller tweak",
                "architecture": "maps G1 Moves root_pos/root_quat/dof_pos[29] directly into the existing qpos[36] web trajectory contract",
                "security": "downloads only public manifest plus one selected CSV from Hugging Face; no credentials",
                "qa": "validates dataset metadata, local joint order, selected CSV shape, excerpt metrics, and web trajectory contract",
                "skeptic": "kinematic reference ingestion is not yet a native dynamics policy and cannot close M19 alone",
            },
            "dod": [
                "manifest top candidates ranked by knee/hip suitability",
                "one selected retargeted CSV ingested as qpos[36]",
                "web trajectory contract check PASS or explicit failure evidence",
            ],
        },
        "sources": [
            {
                "url": "https://huggingface.co/datasets/exptech/g1-moves",
                "accessed": "2026-06-18",
                "note": "Dataset card documents 60+ Unitree G1 clips, retargeted 29-DoF CSV/PKL format, NPZ training references, and trained ONNX policies.",
            },
            {
                "url": "https://github.com/YanjieZe/GMR",
                "accessed": "2026-06-18",
                "note": "GMR supports real-time retargeting and Unitree G1 visualization, reinforcing the retargeted-motion-to-tracker path.",
            },
            {
                "url": "https://arxiv.org/abs/2604.17335",
                "accessed": "2026-06-18",
                "note": "Recent whole-body humanoid work combines reference motion generation with a reference tracker and deploys on Unitree G1.",
            },
        ],
        "manifest": {
            "url": MANIFEST_URL,
            "version": manifest["version"],
            "generated": manifest["generated"],
            "robot": manifest["robot"],
            "dof": manifest["dof"],
            "total_clips": manifest["total_clips"],
            "total_duration_s": manifest["total_duration_s"],
            "categories": manifest["categories"],
        },
        "local_joint_order_check": order_check,
        "top_candidates": top,
        "skipped_candidates": skipped,
        "selected": selected,
        "selected_csv_url": csv_url,
        "selected_csv_shape": list(matrix.shape),
        "best_window": window,
        "excerpt": excerpt,
        "contract_check": contract,
    }
    result["verdict"] = (
        "PASS_INGESTION_GATE"
        if order_check["matches_qpos_7_to_35"]
        and result["selected_csv_shape"][1] == 36
        and contract.get("verdict") == "PASS"
        else "FAIL_INGESTION_GATE"
    )
    (VERIFY / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [
        "# G1 Moves Reference Ingestion Gate Summary",
        "",
        f"Verdict: {result['verdict']}",
        f"Selected clip: {selected['clip']} ({selected['category']})",
        f"CSV: {csv_url}",
        "",
        "| Rank | Clip | Category | Knee range | Hip pitch range | Knee max | Has policy | Score |",
        "|---:|---|---|---:|---:|---:|---|---:|",
    ]
    for rank, item in enumerate(top, start=1):
        lines.append(
            f"| {rank} | {item['clip']} | {item['category']} | {item['knee_range_rad']:.3f} | "
            f"{item['hip_pitch_range_rad']:.3f} | {item['knee_max_rad']:.3f} | {item['has_policy']} | {item['score']:.3f} |"
        )
    lines.extend([
        "",
        f"Best 6s window: {window}",
        f"Contract check: {contract}",
        "",
        "This gate proves ingestion only. M19 still requires a native dynamics rollout and browser replay that pass exp29 visible metrics.",
    ])
    (VERIFY / "g1-moves-reference-ingestion-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(result["verdict"], json.dumps({
        "selected": selected,
        "best_window": window,
        "excerpt": excerpt,
        "contract_ok": contract.get("verdict") == "PASS",
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
