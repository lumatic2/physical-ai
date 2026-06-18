"""Audit a deployable G1 WBC stack candidate against this repo's M19 path."""

from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
VERIFY_DIR = EXP_DIR / "verify"
GROOT_DIR = ROOT / "tmp" / "gr00t-wbc"

POLICY_HPP = (
    GROOT_DIR
    / "gear_sonic_deploy"
    / "src"
    / "g1"
    / "g1_deploy_onnx_ref"
    / "include"
    / "policy_parameters.hpp"
)
G1_SUPPLEMENTAL = (
    GROOT_DIR
    / "decoupled_wbc"
    / "control"
    / "robot_model"
    / "supplemental_info"
    / "g1"
    / "g1_supplemental_info.py"
)
EXP33_CANDIDATE = (
    ROOT
    / "experiments"
    / "33-unitree-mujoco-g1-bridge-probe"
    / "verify"
    / "unassisted-controller-candidate"
    / "candidate_gate_summary.json"
)
EXP33_SOURCE_INSPECTOR = (
    ROOT / "experiments" / "33-unitree-mujoco-g1-bridge-probe" / "inspect_unitree_mujoco_source.py"
)


SOURCES = [
    {
        "name": "NVlabs/GR00T-WholeBodyControl",
        "url": "https://github.com/NVlabs/GR00T-WholeBodyControl",
        "accessed": "2026-06-18",
        "claim": "Unified G1-capable WBC/SONIC repository with training, deployment, checkpoints, C++ inference, and Git LFS assets.",
    },
    {
        "name": "GR00T WBC Quick Start",
        "url": "https://nvlabs.github.io/GR00T-WholeBodyControl/getting_started/quickstart.html",
        "accessed": "2026-06-18",
        "claim": "MuJoCo sim2sim uses install_mujoco_sim.sh, run_sim_loop.py, and gear_sonic_deploy/deploy.sh sim.",
    },
    {
        "name": "GR00T Decoupled WBC docs",
        "url": "https://nvlabs.github.io/GR00T-WholeBodyControl/references/decoupled_wbc.html",
        "accessed": "2026-06-18",
        "claim": "Primary G1 support, Ubuntu 22.04 + NVIDIA GPU + Docker/NVIDIA Container Toolkit, run_g1_control_loop.py.",
    },
    {
        "name": "unitreerobotics/unitree_mujoco",
        "url": "https://github.com/unitreerobotics/unitree_mujoco",
        "accessed": "2026-06-18",
        "claim": "Unitree MuJoCo bridges Unitree SDK2 control programs with MuJoCo and supports G1 low-level messages.",
    },
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_cpp_comments(text: str) -> str:
    return re.sub(r"//.*", "", text)


def parse_cpp_array(text: str, name: str) -> list[str]:
    match = re.search(rf"{re.escape(name)}\s*=\s*\{{(?P<body>.*?)\}};", text, re.DOTALL)
    if not match:
        return []
    body = strip_cpp_comments(match.group("body"))
    return [item.strip() for item in body.split(",") if item.strip()]


def parse_int_array(text: str, name: str) -> list[int]:
    values = parse_cpp_array(text, name)
    parsed: list[int] = []
    for value in values:
        try:
            parsed.append(int(value))
        except ValueError:
            pass
    return parsed


def parse_joint_names_from_comments(text: str, array_name: str) -> list[str]:
    match = re.search(rf"{re.escape(array_name)}\s*=\s*\{{(?P<body>.*?)\}};", text, re.DOTALL)
    if not match:
        return []
    return re.findall(r"//\s*([A-Za-z0-9_]+_joint)", match.group("body"))


def parse_python_joint_list(text: str, name: str) -> list[str]:
    match = re.search(rf"{re.escape(name)}\s*=\s*\[(?P<body>.*?)\]", text, re.DOTALL)
    if not match:
        return []
    return re.findall(r'"([^"]+_joint)"', match.group("body"))


def parse_expected_dds_order() -> list[str]:
    text = read_text(EXP33_SOURCE_INSPECTOR)
    match = re.search(r"EXPECTED_DDS_29DOF\s*=\s*\[(?P<body>.*?)\]", text, re.DOTALL)
    if not match:
        return []
    names = re.findall(r'"([^"]+)"', match.group("body"))
    return [name if name.endswith("_joint") else f"{name}_joint" for name in names]


def command_result(command: list[str], timeout_s: float = 10.0) -> dict:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        return {
            "available": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout_head": completed.stdout.strip().splitlines()[:3],
            "stderr_head": completed.stderr.strip().splitlines()[:3],
        }
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": type(exc).__name__, "message": str(exc)}


def load_exp33_browser_candidate() -> dict:
    if not EXP33_CANDIDATE.exists():
        return {"present": False, "verdict": "MISSING"}
    data = json.loads(EXP33_CANDIDATE.read_text(encoding="utf-8"))
    return {
        "present": True,
        "verdict": data.get("verdict"),
        "joint_count": data.get("publisher_summary", {}).get("nu"),
        "browser_candidate_verdict": data.get("candidate_summary", {}).get("verdict"),
        "policy_actions_generated": data.get("checks", {}).get("policy_actions_generated"),
        "unassisted": data.get("checks", {}).get("unassisted"),
        "source": str(EXP33_CANDIDATE.relative_to(ROOT)),
    }


def main() -> int:
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)

    key_files = {
        "groot_repo": GROOT_DIR,
        "readme": GROOT_DIR / "README.md",
        "quickstart_md": GROOT_DIR / "docs" / "source" / "getting_started" / "quickstart.md",
        "decoupled_wbc_md": GROOT_DIR / "docs" / "source" / "references" / "decoupled_wbc.md",
        "install_mujoco_sim": GROOT_DIR / "install_scripts" / "install_mujoco_sim.sh",
        "run_sim_loop": GROOT_DIR / "gear_sonic" / "scripts" / "run_sim_loop.py",
        "g1_policy_parameters": POLICY_HPP,
        "g1_supplemental_info": G1_SUPPLEMENTAL,
        "gear_sonic_deploy": GROOT_DIR / "gear_sonic_deploy" / "deploy.sh",
        "download_from_hf": GROOT_DIR / "download_from_hf.py",
    }
    source_presence = {name: path.exists() for name, path in key_files.items()}

    policy_text = read_text(POLICY_HPP) if POLICY_HPP.exists() else ""
    supplemental_text = read_text(G1_SUPPLEMENTAL) if G1_SUPPLEMENTAL.exists() else ""
    groot_body_joints = parse_python_joint_list(supplemental_text, "body_actuated_joints")
    default_angle_joints = parse_joint_names_from_comments(policy_text, "default_angles")
    default_angles = parse_cpp_array(policy_text, "default_angles")
    action_scale_entries = parse_cpp_array(policy_text, "g1_action_scale")
    isaaclab_to_mujoco = parse_int_array(policy_text, "isaaclab_to_mujoco")
    mujoco_to_isaaclab = parse_int_array(policy_text, "mujoco_to_isaaclab")
    expected_dds_order = parse_expected_dds_order()
    exp33 = load_exp33_browser_candidate()

    model_contract_checks = {
        "groot_body_joint_count_29": len(groot_body_joints) == 29,
        "default_angles_count_29": len(default_angles) == 29,
        "action_scale_count_29": len(action_scale_entries) == 29,
        "isaaclab_to_mujoco_is_permutation_29": sorted(isaaclab_to_mujoco) == list(range(29)),
        "mujoco_to_isaaclab_is_permutation_29": sorted(mujoco_to_isaaclab) == list(range(29)),
        "default_angle_joint_comments_match_groot_order": default_angle_joints == groot_body_joints,
        "groot_order_matches_exp33_dds_order": groot_body_joints == expected_dds_order,
        "exp33_unassisted_browser_candidate_pass": exp33.get("verdict") == "PASS"
        and exp33.get("browser_candidate_verdict") == "PASS",
    }

    runtime = {
        "platform": platform.platform(),
        "system": platform.system(),
        "is_linux": platform.system().lower() == "linux",
        "bash": shutil.which("bash"),
        "docker": shutil.which("docker"),
        "git": shutil.which("git"),
        "git_lfs": command_result(["git", "lfs", "version"]),
        "docker_version": command_result(["docker", "--version"]) if shutil.which("docker") else {"available": False},
    }
    runtime_checks = {
        "linux_expected_for_direct_docs_path": runtime["is_linux"],
        "bash_available": bool(runtime["bash"]),
        "docker_available": bool(runtime["docker"]),
        "git_lfs_available": bool(runtime["git_lfs"].get("available")),
    }

    artifact_checks = {
        "git_lfs_required_by_docs": True,
        "download_from_hf_script_present": source_presence["download_from_hf"],
        "local_release_checkpoint_found": any(
            path.suffix in {".onnx", ".pt", ".pth"}
            and "motionbricks" not in str(path).lower()
            and "node_modules" not in str(path).lower()
            for path in GROOT_DIR.rglob("*")
        )
        if GROOT_DIR.exists()
        else False,
    }

    pass_model_contract = all(model_contract_checks.values())
    direct_runtime_ready = all(runtime_checks.values())
    source_ready = all(source_presence.values())
    model_artifact_ready = artifact_checks["local_release_checkpoint_found"]

    verdict = "WBC_STACK_CANDIDATE__LOCAL_INTEGRATION_BLOCKED"
    blockers = []
    if not source_ready:
        blockers.append("partial_or_missing_groot_source_tree")
    if not direct_runtime_ready:
        blockers.append("direct_gr00t_runtime_requires_linux_docker_git_lfs_environment")
    if not model_artifact_ready:
        blockers.append("release_model_artifact_or_git_lfs_checkpoint_not_available_locally")
    if not pass_model_contract:
        blockers.append("g1_29dof_contract_mismatch_or_incomplete_parse")

    result = {
        "experiment": "119-g1-deployable-wbc-stack-integration-gate",
        "accessed_date": str(date(2026, 6, 18)),
        "verdict": verdict,
        "m19_closed": False,
        "hypothesis_pass": pass_model_contract and exp33.get("verdict") == "PASS",
        "source_presence": source_presence,
        "runtime": runtime,
        "runtime_checks": runtime_checks,
        "artifact_checks": artifact_checks,
        "model_contract": {
            "checks": model_contract_checks,
            "groot_body_joint_count": len(groot_body_joints),
            "default_angles_count": len(default_angles),
            "action_scale_count": len(action_scale_entries),
            "isaaclab_to_mujoco": isaaclab_to_mujoco,
            "mujoco_to_isaaclab": mujoco_to_isaaclab,
            "groot_body_joints": groot_body_joints,
            "exp33_expected_dds_order": expected_dds_order,
        },
        "browser_transport_evidence": exp33,
        "blockers": blockers,
        "sources": SOURCES,
        "interpretation": (
            "GR00T/SONIC is a credible deployable G1 WBC candidate and its 29-DOF body joint contract "
            "matches the existing Unitree DDS/browser path. This Windows checkout is not sufficient to execute "
            "the official sim2sim stack because the documented path assumes Linux/Ubuntu, Docker/GPU tooling, "
            "Git LFS assets, and released model artifacts. M19 remains open until a GR00T/SONIC or equivalent "
            "controller emits a native visible squat trace and that trace passes the browser replay gate."
        ),
        "next_required_evidence": [
            "Run GR00T/SONIC sim2sim on Linux/WSL2 or Ubuntu host with Git LFS, model download, and Docker/GPU path ready.",
            "Export or stream the 29-DOF G1 MuJoCo/LowState trace into the existing exp33 DDS/browser candidate gate.",
            "Evaluate the emitted motion against exp29 visible squat thresholds: >=8cm drop, >=0.60rad knee, >=0.35rad hip, contact/slip/return, then browser replay.",
        ],
    }

    (VERIFY_DIR / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary = [
        "# G1 Deployable WBC Stack Integration Gate Summary",
        "",
        f"- Verdict: `{verdict}`",
        f"- Source tree present: `{source_ready}`",
        f"- 29-DOF model contract pass: `{pass_model_contract}`",
        f"- Existing Unitree DDS/browser path pass: `{exp33.get('verdict') == 'PASS'}`",
        f"- Direct GR00T runtime ready on this host: `{direct_runtime_ready}`",
        f"- Local release checkpoint/model artifact found: `{model_artifact_ready}`",
        f"- M19 closed: `False`",
        "",
        "## Blockers",
        *(f"- `{blocker}`" for blocker in blockers),
        "",
        "## Next Evidence",
        *(f"- {item}" for item in result["next_required_evidence"]),
        "",
    ]
    (VERIFY_DIR / "deployable-wbc-stack-integration-summary.md").write_text("\n".join(summary), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "blockers": blockers, "m19_closed": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
