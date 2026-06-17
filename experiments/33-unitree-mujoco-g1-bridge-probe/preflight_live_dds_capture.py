#!/usr/bin/env python3
"""Preflight the local environment for Unitree SDK2 DDS capture."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def try_import(name: str) -> dict[str, Any]:
    try:
        importlib.import_module(name)
        return {"ok": True, "error": None}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def scene_path(unitree_mujoco_path: Path | None, robot: str) -> Path | None:
    if unitree_mujoco_path is None:
        return None
    return unitree_mujoco_path / "unitree_robots" / robot / "scene.xml"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk-path", type=Path, help="Local unitree_sdk2_python checkout to add to PYTHONPATH for preflight")
    parser.add_argument("--unitree-mujoco-path", type=Path, help="Local unitree_mujoco checkout")
    parser.add_argument("--robot", default="g1")
    parser.add_argument("--domain-id", type=int, default=1)
    parser.add_argument("--interface", default=None)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    if args.sdk_path:
        sys.path.insert(0, str(args.sdk_path))

    modules = {
        "mujoco": module_available("mujoco"),
        "glfw": module_available("glfw"),
        "pygame": module_available("pygame"),
        "cyclonedds": module_available("cyclonedds"),
        "unitree_sdk2py": module_available("unitree_sdk2py"),
    }

    imports = {
        "unitree_sdk2py.core.channel": try_import("unitree_sdk2py.core.channel"),
        "unitree_sdk2py.idl.unitree_hg.msg.dds_": try_import("unitree_sdk2py.idl.unitree_hg.msg.dds_"),
        "unitree_sdk2py.idl.unitree_go.msg.dds_": try_import("unitree_sdk2py.idl.unitree_go.msg.dds_"),
    }

    unitree_mujoco_checks: dict[str, Any] = {"provided": args.unitree_mujoco_path is not None}
    if args.unitree_mujoco_path:
        sim_dir = args.unitree_mujoco_path / "simulate_python"
        unitree_mujoco_checks.update(
            {
                "simulate_python_exists": sim_dir.exists(),
                "bridge_exists": (sim_dir / "unitree_sdk2py_bridge.py").exists(),
                "simulator_exists": (sim_dir / "unitree_mujoco.py").exists(),
                "config_exists": (sim_dir / "config.py").exists(),
                "robot_scene": str(scene_path(args.unitree_mujoco_path, args.robot)),
                "robot_scene_exists": scene_path(args.unitree_mujoco_path, args.robot).exists(),
            }
        )

    capture_contract = {
        "lowstate_topic": "rt/lowstate",
        "sportmode_topic": "rt/sportmodestate",
        "domain_id": args.domain_id,
        "interface": args.interface or "auto",
        "robot": args.robot,
        "capture_command_shape": (
            "python capture_live_lowstate_jsonl.py --output capture.jsonl "
            "--root-pose-source sportmode --domain-id {domain_id}{interface_arg}"
        ).format(
            domain_id=args.domain_id,
            interface_arg=f" --interface {args.interface}" if args.interface else "",
        ),
    }

    required_bools = [
        modules["mujoco"],
        modules["cyclonedds"],
        modules["unitree_sdk2py"],
        imports["unitree_sdk2py.core.channel"]["ok"],
        imports["unitree_sdk2py.idl.unitree_hg.msg.dds_"]["ok"],
        imports["unitree_sdk2py.idl.unitree_go.msg.dds_"]["ok"],
    ]
    if args.unitree_mujoco_path:
        required_bools.extend(
            [
                unitree_mujoco_checks.get("bridge_exists", False),
                unitree_mujoco_checks.get("simulator_exists", False),
                unitree_mujoco_checks.get("robot_scene_exists", False),
            ]
        )

    missing_next_steps = []
    if not modules["cyclonedds"]:
        missing_next_steps.append("Install/activate cyclonedds Python bindings required by unitree_sdk2py DDS channels.")
    if not modules["unitree_sdk2py"]:
        missing_next_steps.append("Install unitree_sdk2_python or pass --sdk-path to a checkout with its dependencies available.")
    if args.unitree_mujoco_path and not unitree_mujoco_checks.get("robot_scene_exists", False):
        missing_next_steps.append(f"Provide a unitree_mujoco checkout containing unitree_robots/{args.robot}/scene.xml.")

    summary = {
        "verdict": "PASS" if all(required_bools) else "FAIL_ENV",
        "contract": "physical-ai-live-dds-capture-preflight-v0",
        "modules": modules,
        "imports": imports,
        "unitree_mujoco": unitree_mujoco_checks,
        "capture_contract": capture_contract,
        "missing_next_steps": missing_next_steps,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
