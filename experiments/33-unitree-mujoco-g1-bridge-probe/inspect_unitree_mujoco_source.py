#!/usr/bin/env python3
"""Inspect a unitreerobotics/unitree_mujoco checkout for G1 bridge compatibility."""

from __future__ import annotations

import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


EXPECTED_DDS_29DOF = [
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


def git_head(root: Path) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return out or None
    except Exception:
        return None


def parse_g1_xml(xml_path: Path) -> dict[str, Any]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    free_joints: list[str] = []
    hinge_joints: list[str] = []
    motors: list[str] = []
    motor_joints: list[str] = []
    jointpos_sensors: list[str] = []
    jointpos_sensor_joints: list[str] = []

    for elem in root.iter("joint"):
        name = elem.attrib.get("name", "")
        if not name:
            continue
        if elem.attrib.get("type") == "free":
            free_joints.append(name)
        else:
            hinge_joints.append(name)

    for elem in root.iter("motor"):
        motors.append(elem.attrib.get("name", ""))
        motor_joints.append(elem.attrib.get("joint", ""))

    for elem in root.iter("jointpos"):
        jointpos_sensors.append(elem.attrib.get("name", ""))
        jointpos_sensor_joints.append(elem.attrib.get("joint", ""))

    normalized_hinge = [name.removesuffix("_joint") for name in hinge_joints]
    normalized_sensor = [name.removesuffix("_joint") for name in jointpos_sensor_joints]

    return {
        "xml": str(xml_path),
        "free_joints": free_joints,
        "hinge_joint_count": len(hinge_joints),
        "hinge_joints": hinge_joints,
        "normalized_hinge_order": normalized_hinge,
        "motor_count": len(motors),
        "motor_order": motors,
        "motor_joints": motor_joints,
        "jointpos_sensor_count": len(jointpos_sensors),
        "jointpos_sensor_order": jointpos_sensors,
        "jointpos_sensor_joints": jointpos_sensor_joints,
        "normalized_jointpos_order": normalized_sensor,
    }


def inspect_source(unitree_root: Path) -> dict[str, Any]:
    readme = unitree_root / "readme.md"
    config_yaml = unitree_root / "simulate" / "config.yaml"
    py_config = unitree_root / "simulate_python" / "config.py"
    g1_xml = unitree_root / "unitree_robots" / "g1" / "g1_29dof.xml"
    g1_scene = unitree_root / "unitree_robots" / "g1" / "scene.xml"
    dds_index = unitree_root / "unitree_robots" / "g1" / "g1_joint_index_dds.md"
    py_sim = unitree_root / "simulate_python" / "unitree_mujoco.py"
    cpp_bridge = unitree_root / "simulate" / "src" / "unitree_sdk2_bridge.h"

    required = [readme, config_yaml, py_config, g1_xml, g1_scene, dds_index, py_sim, cpp_bridge]
    missing = [str(path.relative_to(unitree_root)) for path in required if not path.exists()]
    if missing:
        return {"verdict": "FAIL", "missing": missing}

    xml = parse_g1_xml(g1_xml)
    source_text = "\n".join(
        [
            readme.read_text(encoding="utf-8", errors="replace"),
            config_yaml.read_text(encoding="utf-8", errors="replace"),
            py_config.read_text(encoding="utf-8", errors="replace"),
            dds_index.read_text(encoding="utf-8", errors="replace"),
            py_sim.read_text(encoding="utf-8", errors="replace"),
            cpp_bridge.read_text(encoding="utf-8", errors="replace"),
        ]
    )

    checks = {
        "remote_head": git_head(unitree_root),
        "g1_scene_exists": g1_scene.exists(),
        "g1_29dof_xml_exists": g1_xml.exists(),
        "python_simulator_exists": py_sim.exists(),
        "cpp_bridge_exists": cpp_bridge.exists(),
        "g1_listed_in_cpp_config": 'robot: "go2"  # Robot name, "go2", "b2", "b2w", "h1", "go2w", "g1", "h2"' in source_text,
        "g1_listed_in_python_config": 'ROBOT = "go2" # Robot name, "go2", "b2", "b2w", "h1", "go2w", "g1"' in source_text,
        "uses_unitree_hg_for_g1": "unitree_hg" in source_text,
        "mentions_g1_imu_state": "G1 only" in source_text or "仅 G1" in source_text,
        "has_single_free_joint": xml["free_joints"] == ["floating_base_joint"],
        "has_29_hinge_joints": xml["hinge_joint_count"] == 29,
        "has_29_motors": xml["motor_count"] == 29,
        "has_29_jointpos_sensors": xml["jointpos_sensor_count"] == 29,
        "motor_order_matches_expected_dds_29dof": xml["motor_order"] == EXPECTED_DDS_29DOF,
        "jointpos_order_matches_expected_dds_29dof": xml["normalized_jointpos_order"] == EXPECTED_DDS_29DOF,
    }

    verdict = "PASS" if all(value for key, value in checks.items() if key != "remote_head") else "FAIL"
    return {
        "verdict": verdict,
        "source": "unitreerobotics/unitree_mujoco",
        "unitree_root": str(unitree_root),
        "expected_web_contract": "root pose 7 + G1 29 joint positions = qpos[36]",
        "checks": checks,
        "expected_dds_29dof_order": EXPECTED_DDS_29DOF,
        "xml": xml,
        "bridge_implication": {
            "joint_pos_source": "LowState.motor_state[i].q or jointpos sensors in Unitree G1 29DOF order",
            "root_pose_source": "MuJoCo qpos[0:7] in simulator, or SportModeState/telemetry pose when available",
            "web_qpos_layout": "root_pos[3] + root_quat[4] + joint_pos[29]",
            "status": "ready for real runtime trace export" if verdict == "PASS" else "source layout mismatch",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unitree-root", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    result = inspect_source(args.unitree_root)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
