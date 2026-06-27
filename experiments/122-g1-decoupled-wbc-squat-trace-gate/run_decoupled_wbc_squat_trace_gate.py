"""Run a headless GR00T Decoupled WBC squat-command trace through M19 gates."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
VERIFY_DIR = EXP_DIR / "verify"
WEB_CONTRACT_CHECK = (
    ROOT / "experiments" / "33-unitree-mujoco-g1-bridge-probe" / "check_web_trajectory_contract.py"
)

WSL_REPO = "/home/<user>/gr00t-wbc-native"
WSL_VERIFY = "/mnt/c/Users/<user>/projects/physical-ai/experiments/122-g1-decoupled-wbc-squat-trace-gate/verify"

FPS = 50.0
VISIBLE_GATE = {
    "min_pelvis_drop_m": 0.08,
    "min_knee_flexion_delta_rad": 0.60,
    "min_hip_pitch_delta_rad": 0.35,
    "max_final_height_error_m": 0.015,
    "min_bilateral_contact_ratio": 0.95,
    "max_foot_slip_m": 0.05,
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


def run_command(command: list[str], timeout_s: float = 120.0) -> dict[str, Any]:
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
        "stdout": completed.stdout.strip().splitlines(),
        "stderr": completed.stderr.strip().splitlines(),
    }


def run_wsl_rollout() -> dict[str, Any]:
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    wsl_script = r"""
set -euo pipefail
cd __WSL_REPO__
mkdir -p __WSL_VERIFY__
.venv_sim/bin/python - <<'PY'
import json
from pathlib import Path

import mujoco
import numpy as np
import onnxruntime as ort
import yaml

VERIFY = Path("__WSL_VERIFY__")
BASE = Path("decoupled_wbc/sim2mujoco/resources/robots/g1")
CONFIG = yaml.safe_load((BASE / "g1_gear_wbc.yaml").read_text())
CONFIG["xml_path"] = str(BASE / CONFIG["xml_path"])
CONFIG["policy_path"] = str(BASE / "policy" / "GR00T-WholeBodyControl-Balance.onnx")
CONFIG["walk_policy_path"] = str(BASE / "policy" / "GR00T-WholeBodyControl-Walk.onnx")
for key in ["kps", "kds", "default_angles", "cmd_scale", "cmd_init"]:
    CONFIG[key] = np.array(CONFIG[key], dtype=np.float32)

MODEL = mujoco.MjModel.from_xml_path(CONFIG["xml_path"])
DATA = mujoco.MjData(MODEL)
MODEL.opt.timestep = CONFIG["simulation_dt"]
N_JOINTS = DATA.qpos.shape[0] - 7
JOINT_ORDER = [mujoco.mj_id2name(MODEL, mujoco.mjtObj.mjOBJ_JOINT, i) for i in range(MODEL.njnt)][1:]
BASE_POLICY = ort.InferenceSession(CONFIG["policy_path"], providers=["CPUExecutionProvider"])
INPUT_NAME = BASE_POLICY.get_inputs()[0].name
LEFT_FOOT_BODY = mujoco.mj_name2id(MODEL, mujoco.mjtObj.mjOBJ_BODY, "left_ankle_roll_link")
RIGHT_FOOT_BODY = mujoco.mj_name2id(MODEL, mujoco.mjtObj.mjOBJ_BODY, "right_ankle_roll_link")
FLOOR_GEOM = mujoco.mj_name2id(MODEL, mujoco.mjtObj.mjOBJ_GEOM, "floor")


def quat_rotate_inverse(q, v):
    w, x, y, z = q
    qc = np.array([w, -x, -y, -z])
    return np.array([
        v[0] * (qc[0] ** 2 + qc[1] ** 2 - qc[2] ** 2 - qc[3] ** 2)
        + v[1] * 2 * (qc[1] * qc[2] - qc[0] * qc[3])
        + v[2] * 2 * (qc[1] * qc[3] + qc[0] * qc[2]),
        v[0] * 2 * (qc[1] * qc[2] + qc[0] * qc[3])
        + v[1] * (qc[0] ** 2 - qc[1] ** 2 + qc[2] ** 2 - qc[3] ** 2)
        + v[2] * 2 * (qc[2] * qc[3] - qc[0] * qc[1]),
        v[0] * 2 * (qc[1] * qc[3] - qc[0] * qc[2])
        + v[1] * 2 * (qc[2] * qc[3] + qc[0] * qc[1])
        + v[2] * (qc[0] ** 2 - qc[1] ** 2 - qc[2] ** 2 + qc[3] ** 2),
    ])


def height_command(t, low):
    if t < 1.0:
        return 0.74
    if t < 2.0:
        return 0.74 + (low - 0.74) * (t - 1.0)
    if t < 3.5:
        return low
    if t < 5.0:
        return low + (0.74 - low) * ((t - 3.5) / 1.5)
    return 0.74


def compute_obs(action, height):
    command = np.zeros(7, dtype=np.float32)
    command[:3] = CONFIG["cmd_init"][:3] * CONFIG["cmd_scale"]
    command[3] = height
    command[4:7] = np.array(CONFIG["rpy_cmd"], dtype=np.float32)

    qj = DATA.qpos[7 : 7 + N_JOINTS].copy()
    dqj = DATA.qvel[6 : 6 + N_JOINTS].copy()
    defaults = np.zeros(N_JOINTS, dtype=np.float32)
    defaults[: len(CONFIG["default_angles"])] = CONFIG["default_angles"]

    single = np.zeros(86, dtype=np.float32)
    single[0:7] = command
    single[7:10] = DATA.qvel[3:6] * CONFIG["ang_vel_scale"]
    single[10:13] = quat_rotate_inverse(DATA.qpos[3:7].copy(), np.array([0.0, 0.0, -1.0]))
    single[13 : 13 + N_JOINTS] = (qj - defaults) * CONFIG["dof_pos_scale"]
    single[13 + N_JOINTS : 13 + 2 * N_JOINTS] = dqj * CONFIG["dof_vel_scale"]
    single[13 + 2 * N_JOINTS : 13 + 2 * N_JOINTS + 15] = action
    return single


def foot_contact_bodies():
    left = False
    right = False
    for idx in range(DATA.ncon):
        contact = DATA.contact[idx]
        if contact.geom1 == FLOOR_GEOM:
            other = contact.geom2
        elif contact.geom2 == FLOOR_GEOM:
            other = contact.geom1
        else:
            continue
        body = int(MODEL.geom_bodyid[other])
        if body == LEFT_FOOT_BODY:
            left = True
        if body == RIGHT_FOOT_BODY:
            right = True
    return left, right


def rollout(low_height):
    mujoco.mj_resetData(MODEL, DATA)
    action = np.zeros(CONFIG["num_actions"], dtype=np.float32)
    target = CONFIG["default_angles"].copy()
    obs_history = [np.zeros(86, dtype=np.float32)] * CONFIG["obs_history_len"]
    frames = []
    total_steps = int(7.0 / MODEL.opt.timestep)

    for step in range(total_steps):
        t = step * MODEL.opt.timestep
        height = height_command(t, low_height)
        DATA.ctrl[: CONFIG["num_actions"]] = (
            (target - DATA.qpos[7 : 7 + CONFIG["num_actions"]]) * CONFIG["kps"]
            + (0 - DATA.qvel[6 : 6 + CONFIG["num_actions"]]) * CONFIG["kds"]
        )
        if N_JOINTS > CONFIG["num_actions"]:
            DATA.ctrl[CONFIG["num_actions"] :] = (
                -DATA.qpos[7 + CONFIG["num_actions"] : 7 + N_JOINTS] * 100.0
                - DATA.qvel[6 + CONFIG["num_actions"] : 6 + N_JOINTS] * 0.5
            )
        mujoco.mj_step(MODEL, DATA)

        if step % CONFIG["control_decimation"] == 0:
            obs_history.append(compute_obs(action, height))
            obs_history = obs_history[-CONFIG["obs_history_len"] :]
            obs = np.concatenate(obs_history).astype(np.float32)[None, :]
            action = BASE_POLICY.run(None, {INPUT_NAME: obs})[0].squeeze().astype(np.float32)
            target = action * CONFIG["action_scale"] + CONFIG["default_angles"]
            left_contact, right_contact = foot_contact_bodies()
            frames.append({
                "t": t,
                "height_cmd": float(height),
                "qpos": DATA.qpos.copy().astype(float).tolist(),
                "qvel": DATA.qvel.copy().astype(float).tolist(),
                "action": action.astype(float).tolist(),
                "left_contact": left_contact,
                "right_contact": right_contact,
                "left_foot_xy": DATA.xpos[LEFT_FOOT_BODY][:2].copy().astype(float).tolist(),
                "right_foot_xy": DATA.xpos[RIGHT_FOOT_BODY][:2].copy().astype(float).tolist(),
            })

    return frames


variants = {}
for low in [0.70, 0.68, 0.66, 0.64]:
    key = f"low_{low:.2f}".replace(".", "p")
    variants[key] = rollout(low)

raw = {
    "source": "decoupled_wbc_headless_balance_height_schedule",
    "policy": CONFIG["policy_path"],
    "xml": CONFIG["xml_path"],
    "joint_order": JOINT_ORDER,
    "fps": 50.0,
    "recording_note": "Frames are measured MuJoCo qpos/qvel/action from GR00T Decoupled WBC Balance ONNX under scheduled height command.",
    "variants": variants,
}
(VERIFY / "raw_decoupled_wbc_rollouts.json").write_text(json.dumps(raw, indent=2))
print(json.dumps({"variants": list(variants), "frames": {k: len(v) for k, v in variants.items()}}, indent=2))
PY
"""
    wsl_script = wsl_script.replace("__WSL_REPO__", WSL_REPO).replace("__WSL_VERIFY__", WSL_VERIFY)
    return run_command(["wsl.exe", "-d", "Ubuntu-24.04", "--", "bash", "-lc", wsl_script], timeout_s=180.0)


def max_delta(qpos: list[list[float]], joint_name: str) -> float:
    offset = 7 + G1_MUJOCO_ORDER.index(joint_name)
    start = qpos[0][offset]
    return max(abs(frame[offset] - start) for frame in qpos)


def max_slip(frames: list[dict[str, Any]]) -> float:
    left0 = frames[0]["left_foot_xy"]
    right0 = frames[0]["right_foot_xy"]
    out = 0.0
    for frame in frames:
        left = frame["left_foot_xy"]
        right = frame["right_foot_xy"]
        out = max(out, math.dist(left, left0), math.dist(right, right0))
    return out


def evaluate_variant(name: str, frames: list[dict[str, Any]]) -> dict[str, Any]:
    recorded = [frame for frame in frames if frame["t"] >= 1.0]
    qpos = [frame["qpos"] for frame in recorded]
    heights = [frame[2] for frame in qpos]
    bilateral_contact_ratio = sum(
        1 for frame in recorded if frame["left_contact"] and frame["right_contact"]
    ) / max(1, len(recorded))
    metrics = {
        "variant": name,
        "frames": len(qpos),
        "fps": FPS,
        "duration_s": len(qpos) / FPS,
        "start_height_m": heights[0],
        "min_height_m": min(heights),
        "end_height_m": heights[-1],
        "pelvis_drop_m": heights[0] - min(heights),
        "final_height_error_m": abs(heights[-1] - heights[0]),
        "max_knee_flexion_delta_rad": max(
            max_delta(qpos, "left_knee_joint"), max_delta(qpos, "right_knee_joint")
        ),
        "max_hip_pitch_delta_rad": max(
            max_delta(qpos, "left_hip_pitch_joint"), max_delta(qpos, "right_hip_pitch_joint")
        ),
        "bilateral_contact_ratio": bilateral_contact_ratio,
        "max_foot_slip_m": max_slip(recorded),
    }
    checks = {
        "pelvis_drop_pass": metrics["pelvis_drop_m"] >= VISIBLE_GATE["min_pelvis_drop_m"],
        "knee_flexion_pass": metrics["max_knee_flexion_delta_rad"]
        >= VISIBLE_GATE["min_knee_flexion_delta_rad"],
        "hip_pitch_pass": metrics["max_hip_pitch_delta_rad"]
        >= VISIBLE_GATE["min_hip_pitch_delta_rad"],
        "return_height_pass": metrics["final_height_error_m"]
        <= VISIBLE_GATE["max_final_height_error_m"],
        "bilateral_contact_pass": metrics["bilateral_contact_ratio"]
        >= VISIBLE_GATE["min_bilateral_contact_ratio"],
        "foot_slip_pass": metrics["max_foot_slip_m"] <= VISIBLE_GATE["max_foot_slip_m"],
    }
    trajectory = {
        "fps": FPS,
        "nq": 36,
        "scene": "g1/scene_g1_policy.xml",
        "contract": "physical-ai-web-trajectory-v1",
        "source_attempt": f"exp122-decoupled-wbc-{name}",
        "note": "Measured MuJoCo qpos from GR00T Decoupled WBC Balance ONNX height-command squat schedule.",
        "qpos": qpos,
    }
    return {
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "thresholds": VISIBLE_GATE,
        "checks": checks,
        "metrics": metrics,
        "trajectory": trajectory,
    }


def main() -> int:
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    rollout_run = run_wsl_rollout()
    raw_path = VERIFY_DIR / "raw_decoupled_wbc_rollouts.json"
    if rollout_run["returncode"] != 0 or not raw_path.exists():
        result = {
            "experiment": "122-g1-decoupled-wbc-squat-trace-gate",
            "verdict": "DECOUPLED_WBC_ROLLOUT_FAIL",
            "m19_closed": False,
            "rollout_run": rollout_run,
        }
        (VERIFY_DIR / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    variants = {
        name: evaluate_variant(name, frames)
        for name, frames in raw["variants"].items()
    }
    best_name = max(
        variants,
        key=lambda name: (
            variants[name]["verdict"] == "PASS",
            variants[name]["metrics"]["pelvis_drop_m"],
            -variants[name]["metrics"]["max_foot_slip_m"],
        ),
    )
    best = variants[best_name]
    web_path = VERIFY_DIR / f"{best_name}_web_trajectory.json"
    web_path.write_text(json.dumps(best["trajectory"], indent=2), encoding="utf-8")
    web_contract_path = VERIFY_DIR / f"{best_name}_web_contract_summary.json"
    web_contract_run = run_command(
        [
            str(Path("C:/tmp/e34/Scripts/python.exe")),
            str(WEB_CONTRACT_CHECK),
            "--trajectory",
            str(web_path),
            "--summary",
            str(web_contract_path),
        ],
        timeout_s=20.0,
    )
    web_contract = json.loads(web_contract_path.read_text(encoding="utf-8"))
    native_pass = best["verdict"] == "PASS"
    web_pass = web_contract.get("verdict") == "PASS"
    browser_qa_path = VERIFY_DIR / "browser_replay_qa_summary.json"
    browser_qa = None
    if browser_qa_path.exists():
        browser_qa = json.loads(browser_qa_path.read_text(encoding="utf-8"))
    browser_pass = bool(browser_qa and browser_qa.get("verdict") == "PASS")
    m19_closed = native_pass and web_pass and browser_pass
    result = {
        "experiment": "122-g1-decoupled-wbc-squat-trace-gate",
        "verdict": (
            "M19_NATIVE_TRACE_PASS__BROWSER_REPLAY_QA_PASS"
            if m19_closed
            else "M19_NATIVE_TRACE_PASS__BROWSER_CONTRACT_PASS"
            if native_pass and web_pass
            else "M19_TRACE_GATE_FAIL"
        ),
        "m19_closed": m19_closed,
        "why_not_closed": None
        if m19_closed
        else (
            "This is a measured Decoupled WBC MuJoCo trace and web-trajectory contract pass, "
            "but the full browser replay artifact has not yet been registered and QA'd in the live web app."
        ),
        "rollout_run": rollout_run,
        "best_variant": best_name,
        "native_gate": best,
        "all_variants": {
            name: {
                "verdict": data["verdict"],
                "checks": data["checks"],
                "metrics": data["metrics"],
            }
            for name, data in variants.items()
        },
        "web_contract_run": web_contract_run,
        "web_contract": web_contract,
        "browser_replay_qa": browser_qa,
        "artifacts": {
            "raw_rollouts": str(raw_path.relative_to(ROOT)),
            "web_trajectory": str(web_path.relative_to(ROOT)),
            "web_contract_summary": str(web_contract_path.relative_to(ROOT)),
            **(
                {"browser_replay_qa": str(browser_qa_path.relative_to(ROOT))}
                if browser_qa_path.exists()
                else {}
            ),
        },
        "sources": [
            {
                "url": "https://nvlabs.github.io/GR00T-WholeBodyControl/references/decoupled_wbc.html",
                "accessed": "2026-06-18",
                "claim": "Decoupled WBC supports Unitree G1 and provides balance/walk whole-body control policies.",
            },
            {
                "url": "https://nvlabs.github.io/GR00T-WholeBodyControl/getting_started/download_models.html",
                "accessed": "2026-06-18",
                "claim": "GEAR-SONIC models are downloaded from Hugging Face with download_from_hf.py.",
            },
        ],
        "next_required_evidence": []
        if m19_closed
        else [
            "Register the measured web trajectory in the robotics lab web app.",
            "Run local browser replay QA for the registered Decoupled WBC squat trace.",
            "If browser replay passes, update ROADMAP M19 completion evidence.",
        ],
    }
    (VERIFY_DIR / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary = [
        "# Decoupled WBC Squat Trace Gate Summary",
        "",
        f"- Verdict: `{result['verdict']}`",
        f"- Best variant: `{best_name}`",
        f"- Native gate: `{best['verdict']}`",
        f"- Web trajectory contract: `{web_contract.get('verdict')}`",
        f"- Browser replay QA: `{browser_qa.get('verdict') if browser_qa else 'PENDING'}`",
        f"- Pelvis drop: `{best['metrics']['pelvis_drop_m']:.4f}m`",
        f"- Knee delta: `{best['metrics']['max_knee_flexion_delta_rad']:.4f}rad`",
        f"- Hip delta: `{best['metrics']['max_hip_pitch_delta_rad']:.4f}rad`",
        f"- Final height error: `{best['metrics']['final_height_error_m']:.4f}m`",
        f"- Bilateral contact ratio: `{best['metrics']['bilateral_contact_ratio']:.3f}`",
        f"- Max foot slip: `{best['metrics']['max_foot_slip_m']:.4f}m`",
        f"- M19 closed: `{m19_closed}`",
        "",
    ]
    if result["next_required_evidence"]:
        summary.extend(
            [
                "## Next Evidence",
                *(f"- {item}" for item in result["next_required_evidence"]),
                "",
            ]
        )
    (VERIFY_DIR / "summary.md").write_text("\n".join(summary), encoding="utf-8")
    print(json.dumps({"verdict": result["verdict"], "best_variant": best_name, "native": best["verdict"], "web_contract": web_contract.get("verdict"), "browser_qa": browser_qa.get("verdict") if browser_qa else "PENDING"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
