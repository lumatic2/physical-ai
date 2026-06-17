#!/usr/bin/env python3
"""Inspect official unitree_sdk2_python files used by the capture template."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


REQUIRED_FILES = {
    "g1_low_level_example": "example/g1/low_level/g1_low_level_example.py",
    "hg_lowcmd_idl": "unitree_sdk2py/idl/unitree_hg/msg/dds_/_LowCmd_.py",
    "hg_lowstate_idl": "unitree_sdk2py/idl/unitree_hg/msg/dds_/_LowState_.py",
    "go_sportmode_idl": "unitree_sdk2py/idl/unitree_go/msg/dds_/_SportModeState_.py",
}


def git_head(path: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    checks: dict[str, bool] = {}
    snippets: dict[str, str] = {}
    for key, rel in REQUIRED_FILES.items():
        path = args.source / rel
        checks[f"{key}_exists"] = path.exists()
        if path.exists():
            snippets[key] = read(path)

    g1_example = snippets.get("g1_low_level_example", "")
    hg_lowcmd = snippets.get("hg_lowcmd_idl", "")
    hg_lowstate = snippets.get("hg_lowstate_idl", "")
    sportmode = snippets.get("go_sportmode_idl", "")

    checks.update(
        {
            "g1_imports_hg_lowstate": "from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_" in g1_example,
            "g1_imports_hg_lowcmd": "from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_" in g1_example,
            "g1_subscribes_rt_lowstate": 'ChannelSubscriber("rt/lowstate", LowState_)' in g1_example,
            "g1_publishes_rt_lowcmd": 'ChannelPublisher("rt/lowcmd", LowCmd_)' in g1_example,
            "hg_lowcmd_has_35_motors": "motor_cmd: types.array" in hg_lowcmd and "35]" in hg_lowcmd,
            "hg_lowstate_has_35_motors": "motor_state: types.array" in hg_lowstate and "35]" in hg_lowstate,
            "hg_lowstate_has_imu_state": "imu_state:" in hg_lowstate,
            "sportmode_has_position_3": "position: types.array" in sportmode and "3]" in sportmode,
        }
    )

    summary = {
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "contract": "physical-ai-unitree-sdk2-python-capture-source-v0",
        "source": str(args.source),
        "git_head": git_head(args.source),
        "checks": checks,
        "capture_template_implication": {
            "lowstate_import": "unitree_sdk2py.idl.unitree_hg.msg.dds_.LowState_",
            "lowstate_topic": "rt/lowstate",
            "lowcmd_import": "unitree_sdk2py.idl.unitree_hg.msg.dds_.LowCmd_",
            "lowcmd_topic": "rt/lowcmd",
            "joint_count_for_g1_29dof": 29,
            "available_motor_state_slots": 35,
            "optional_root_position_topic": "rt/sportmodestate",
            "root_orientation_source": "LowState_.imu_state.quaternion",
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
