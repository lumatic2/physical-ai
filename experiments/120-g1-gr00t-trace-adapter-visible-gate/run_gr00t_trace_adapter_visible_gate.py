"""Adapt GR00T/SONIC-style G1 traces into the M19 visible/browser gate."""

from __future__ import annotations

import csv
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
VERIFY_DIR = EXP_DIR / "verify"
GROOT_DIR = ROOT / "tmp" / "gr00t-wbc"

WEB_CONTRACT_CHECK = ROOT / "experiments" / "33-unitree-mujoco-g1-bridge-probe" / "check_web_trajectory_contract.py"

FPS = 50.0
SCENE = "g1/scene_g1_policy.xml"
VISIBLE_GATE = {
    "min_pelvis_drop_m": 0.08,
    "min_knee_flexion_delta_rad": 0.60,
    "min_hip_pitch_delta_rad": 0.35,
    "max_final_height_error_m": 0.015,
}

G1_MUJOCO_ORDER = [
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

DEFAULT_Q = {
    "left_hip_pitch_joint": -0.312,
    "left_hip_roll_joint": 0.0,
    "left_hip_yaw_joint": 0.0,
    "left_knee_joint": 0.669,
    "left_ankle_pitch_joint": -0.363,
    "left_ankle_roll_joint": 0.0,
    "right_hip_pitch_joint": -0.312,
    "right_hip_roll_joint": 0.0,
    "right_hip_yaw_joint": 0.0,
    "right_knee_joint": 0.669,
    "right_ankle_pitch_joint": -0.363,
    "right_ankle_roll_joint": 0.0,
    "waist_yaw_joint": 0.0,
    "waist_roll_joint": 0.0,
    "waist_pitch_joint": 0.0,
    "left_shoulder_pitch_joint": 0.2,
    "left_shoulder_roll_joint": 0.2,
    "left_shoulder_yaw_joint": 0.0,
    "left_elbow_joint": 0.6,
    "left_wrist_roll_joint": 0.0,
    "left_wrist_pitch_joint": 0.0,
    "left_wrist_yaw_joint": 0.0,
    "right_shoulder_pitch_joint": 0.2,
    "right_shoulder_roll_joint": -0.2,
    "right_shoulder_yaw_joint": 0.0,
    "right_elbow_joint": 0.6,
    "right_wrist_roll_joint": 0.0,
    "right_wrist_pitch_joint": 0.0,
    "right_wrist_yaw_joint": 0.0,
}


def finite_list(name: str, values: Any, width: int) -> list[float]:
    if not isinstance(values, list) or len(values) != width:
        raise ValueError(f"{name} must be a list of length {width}")
    out: list[float] = []
    for idx, value in enumerate(values):
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"{name}[{idx}] must be finite")
        out.append(float(value))
    return out


def run_command(command: list[str], timeout_s: float = 20.0) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip().splitlines()[:20],
            "stderr": completed.stderr.strip().splitlines()[:20],
        }
    except Exception as exc:
        return {"returncode": None, "error": type(exc).__name__, "message": str(exc)}


def wsl_preflight() -> dict[str, Any]:
    if not shutil.which("wsl.exe"):
        return {"available": False, "reason": "wsl.exe not found"}
    script = (
        "set -o pipefail; "
        "echo WSL_OK; "
        "uname -a; "
        "python3 --version; "
        "git --version; "
        "(git lfs version || true); "
        "(docker --version || true); "
        "(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true)"
    )
    result = run_command(["wsl.exe", "-d", "Ubuntu-24.04", "--", "bash", "-lc", script], timeout_s=30.0)
    lines = result.get("stdout", [])
    stderr = result.get("stderr", [])
    text = "\n".join(lines + stderr)
    return {
        "available": result.get("returncode") == 0 and any("WSL_OK" in line for line in lines),
        "raw": result,
        "checks": {
            "ubuntu_24_04_running": "Ubuntu" in text or "WSL_OK" in text,
            "python3_available": "Python 3" in text,
            "git_available": "git version" in text,
            "git_lfs_healthy": "git-lfs/" in text,
            "docker_cli_available": "Docker version" in text,
            "gpu_visible": "NVIDIA" in text or "RTX" in text,
        },
    }


def synthesize_gr00t_debug_trace(path: Path) -> dict[str, Any]:
    frames: list[dict[str, Any]] = []
    total = 51
    for idx in range(total):
        phase = idx / (total - 1)
        if phase < 0.35:
            alpha = phase / 0.35
        elif phase < 0.65:
            alpha = 1.0
        else:
            alpha = 1.0 - ((phase - 0.65) / 0.35)
        alpha = max(0.0, min(1.0, alpha))

        joints = DEFAULT_Q.copy()
        for side in ("left", "right"):
            joints[f"{side}_hip_pitch_joint"] += -0.42 * alpha
            joints[f"{side}_knee_joint"] += 0.72 * alpha
            joints[f"{side}_ankle_pitch_joint"] += -0.18 * alpha

        body_q = [joints[name] for name in G1_MUJOCO_ORDER]
        base_trans = [0.0, 0.0, 0.793 - 0.10 * alpha]
        frame = {
            "frame_index": idx,
            "base_trans_target": base_trans,
            "base_quat_target": [1.0, 0.0, 0.0, 0.0],
            "body_q_target": body_q,
            "base_trans_measured": base_trans,
            "base_quat_measured": [1.0, 0.0, 0.0, 0.0],
            "body_q_measured": body_q,
        }
        frames.append(frame)

    trace = {
        "format": "gr00t-debug-json-v0",
        "source": "synthetic-visible-squat-contract-probe",
        "fps": FPS,
        "joint_order": G1_MUJOCO_ORDER,
        "frames": frames,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    return trace


def write_synthetic_gr00t_motion_dir(path: Path, trace: dict[str, Any]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    headers = {
        "joint_pos.csv": [f"j{i}" for i in range(29)],
        "body_pos.csv": ["x", "y", "z"],
        "body_quat.csv": ["w", "x", "y", "z"],
    }
    files = {
        "joint_pos.csv": [[*frame["body_q_target"]] for frame in trace["frames"]],
        "body_pos.csv": [[*frame["base_trans_target"]] for frame in trace["frames"]],
        "body_quat.csv": [[*frame["base_quat_target"]] for frame in trace["frames"]],
    }
    for filename, rows in files.items():
        with (path / filename).open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers[filename])
            writer.writerows(rows)


def convert_debug_trace(trace: dict[str, Any], use_measured: bool) -> dict[str, Any]:
    suffix = "measured" if use_measured else "target"
    qpos: list[list[float]] = []
    for idx, frame in enumerate(trace.get("frames", [])):
        if not isinstance(frame, dict):
            raise ValueError(f"frames[{idx}] must be an object")
        root_pos = finite_list(f"frames[{idx}].base_trans_{suffix}", frame.get(f"base_trans_{suffix}"), 3)
        root_quat = finite_list(f"frames[{idx}].base_quat_{suffix}", frame.get(f"base_quat_{suffix}"), 4)
        body_q = finite_list(f"frames[{idx}].body_q_{suffix}", frame.get(f"body_q_{suffix}"), 29)
        qpos.append(root_pos + root_quat + body_q)

    fps = trace.get("fps", FPS)
    if not isinstance(fps, (int, float)) or float(fps) <= 0:
        raise ValueError("trace.fps must be positive")
    return {
        "fps": float(fps),
        "nq": 36,
        "scene": SCENE,
        "note": f"Converted from GR00T/SONIC debug {suffix} fields.",
        "source_attempt": trace.get("source", "gr00t-debug-trace"),
        "qpos": qpos,
    }


def visible_gate(trajectory: dict[str, Any]) -> dict[str, Any]:
    qpos = trajectory["qpos"]
    heights = [frame[2] for frame in qpos]

    def max_delta(joint_name: str) -> float:
        offset = 7 + G1_MUJOCO_ORDER.index(joint_name)
        start = qpos[0][offset]
        return max(abs(frame[offset] - start) for frame in qpos)

    knee = max(max_delta("left_knee_joint"), max_delta("right_knee_joint"))
    hip = max(max_delta("left_hip_pitch_joint"), max_delta("right_hip_pitch_joint"))
    pelvis_drop = heights[0] - min(heights)
    final_height_error = abs(heights[-1] - heights[0])
    checks = {
        "pelvis_drop_pass": pelvis_drop >= VISIBLE_GATE["min_pelvis_drop_m"],
        "knee_flexion_pass": knee >= VISIBLE_GATE["min_knee_flexion_delta_rad"],
        "hip_pitch_pass": hip >= VISIBLE_GATE["min_hip_pitch_delta_rad"],
        "return_height_pass": final_height_error <= VISIBLE_GATE["max_final_height_error_m"],
    }
    return {
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "thresholds": VISIBLE_GATE,
        "checks": checks,
        "metrics": {
            "frames": len(qpos),
            "fps": trajectory["fps"],
            "duration_s": len(qpos) / trajectory["fps"],
            "pelvis_drop_m": pelvis_drop,
            "max_knee_flexion_delta_rad": knee,
            "max_hip_pitch_delta_rad": hip,
            "final_height_error_m": final_height_error,
            "start_height_m": heights[0],
            "min_height_m": min(heights),
            "end_height_m": heights[-1],
        },
    }


def main() -> int:
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    trace_path = VERIFY_DIR / "synthetic_gr00t_debug_trace.json"
    motion_dir = VERIFY_DIR / "synthetic_gr00t_motion_dir"
    web_path = VERIFY_DIR / "synthetic_gr00t_visible_web_trajectory.json"
    contract_path = VERIFY_DIR / "web_contract_summary.json"
    visible_path = VERIFY_DIR / "visible_gate_summary.json"

    trace = synthesize_gr00t_debug_trace(trace_path)
    write_synthetic_gr00t_motion_dir(motion_dir, trace)
    trajectory = convert_debug_trace(trace, use_measured=True)
    web_path.write_text(json.dumps(trajectory, indent=2), encoding="utf-8")

    contract_cmd = [
        str(Path("C:/tmp/e34/Scripts/python.exe")),
        str(WEB_CONTRACT_CHECK),
        "--trajectory",
        str(web_path),
        "--summary",
        str(contract_path),
    ]
    contract_run = run_command(contract_cmd, timeout_s=20.0)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    visible = visible_gate(trajectory)
    visible_path.write_text(json.dumps(visible, indent=2), encoding="utf-8")

    gr00t_files = {
        "visualize_motion_py": (GROOT_DIR / "gear_sonic_deploy" / "visualize_motion.py").exists(),
        "zmq_doc_md": (GROOT_DIR / "docs" / "source" / "tutorials" / "zmq.md").exists(),
        "state_logger_hpp": (
            GROOT_DIR
            / "gear_sonic_deploy"
            / "src"
            / "g1"
            / "g1_deploy_onnx_ref"
            / "include"
            / "state_logger.hpp"
        ).exists(),
        "zmq_output_handler_hpp": (
            GROOT_DIR
            / "gear_sonic_deploy"
            / "src"
            / "g1"
            / "g1_deploy_onnx_ref"
            / "include"
            / "output_interface"
            / "zmq_output_handler.hpp"
        ).exists(),
    }
    wsl = wsl_preflight()
    checks = {
        "gr00t_trace_sources_present": all(gr00t_files.values()),
        "wsl_available": bool(wsl.get("available")),
        "wsl_docker_cli_available": bool(wsl.get("checks", {}).get("docker_cli_available")),
        "wsl_gpu_visible": bool(wsl.get("checks", {}).get("gpu_visible")),
        "wsl_git_lfs_healthy": bool(wsl.get("checks", {}).get("git_lfs_healthy")),
        "synthetic_web_contract_pass": contract.get("verdict") == "PASS",
        "synthetic_visible_gate_pass": visible.get("verdict") == "PASS",
    }
    verdict = (
        "TRACE_ADAPTER_READY__RUNTIME_PREFLIGHT_PARTIAL"
        if checks["synthetic_web_contract_pass"] and checks["synthetic_visible_gate_pass"]
        else "TRACE_ADAPTER_FAIL"
    )
    blockers = []
    if not checks["wsl_git_lfs_healthy"]:
        blockers.append("wsl_git_lfs_broken_or_missing")
    if not checks["wsl_docker_cli_available"]:
        blockers.append("wsl_docker_unavailable")
    if not checks["wsl_gpu_visible"]:
        blockers.append("wsl_gpu_not_visible")

    result = {
        "experiment": "120-g1-gr00t-trace-adapter-visible-gate",
        "verdict": verdict,
        "m19_closed": False,
        "checks": checks,
        "blockers": blockers,
        "gr00t_trace_contract": {
            "debug_fields": [
                "base_trans_target",
                "base_quat_target",
                "body_q_target",
                "base_trans_measured",
                "base_quat_measured",
                "body_q_measured",
            ],
            "motion_dir_files": ["joint_pos.csv", "body_pos.csv", "body_quat.csv"],
            "joint_order": "GR00T/SONIC debug body_q_* is MuJoCo order; ZMQ protocol v1 joint_pos is IsaacLab order.",
        },
        "wsl_preflight": wsl,
        "contract_run": contract_run,
        "web_contract": contract,
        "visible_gate": visible,
        "artifacts": {
            "synthetic_debug_trace": str(trace_path.relative_to(ROOT)),
            "synthetic_motion_dir": str(motion_dir.relative_to(ROOT)),
            "web_trajectory": str(web_path.relative_to(ROOT)),
            "web_contract_summary": str(contract_path.relative_to(ROOT)),
            "visible_gate_summary": str(visible_path.relative_to(ROOT)),
        },
        "sources": [
            {
                "url": "https://nvlabs.github.io/GR00T-WholeBodyControl/tutorials/zmq.html",
                "accessed": "2026-06-18",
                "claim": "ZMQ streaming supports G1 whole-body joint positions from external sources, with Protocol v1 joint_pos/joint_vel shape [N,29].",
            },
            {
                "url": "https://nvlabs.github.io/GR00T-WholeBodyControl/getting_started/quickstart.html",
                "accessed": "2026-06-18",
                "claim": "Online visualization connects to g1_deploy realtime debug on tcp://localhost:5557 topic g1_debug.",
            },
        ],
        "next_required_evidence": [
            "Fix WSL git-lfs, then run python download_from_hf.py and GR00T sim2sim in WSL/Ubuntu.",
            "Capture realtime g1_debug or CSV logs from g1_deploy and feed measured fields through this adapter.",
            "Only close M19 if the real controller trace passes native exp29 visible/contact/slip/return gates and browser replay.",
        ],
    }
    (VERIFY_DIR / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary = [
        "# GR00T Trace Adapter Visible Gate Summary",
        "",
        f"- Verdict: `{verdict}`",
        f"- Synthetic web contract: `{contract.get('verdict')}`",
        f"- Synthetic visible gate: `{visible.get('verdict')}`",
        f"- WSL available: `{checks['wsl_available']}`",
        f"- WSL Docker CLI: `{checks['wsl_docker_cli_available']}`",
        f"- WSL GPU visible: `{checks['wsl_gpu_visible']}`",
        f"- WSL git-lfs healthy: `{checks['wsl_git_lfs_healthy']}`",
        f"- M19 closed: `False`",
        "",
        "## Blockers",
        *(f"- `{blocker}`" for blocker in blockers),
        "",
        "## Next Evidence",
        *(f"- {item}" for item in result["next_required_evidence"]),
        "",
    ]
    (VERIFY_DIR / "summary.md").write_text("\n".join(summary), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "checks": checks, "blockers": blockers}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
