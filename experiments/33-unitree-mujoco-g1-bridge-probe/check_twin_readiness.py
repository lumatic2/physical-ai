#!/usr/bin/env python3
"""Summarize whether the current G1 twin evidence is demo-ready or complete."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else None


def verdict_at(data: dict[str, Any] | None, *keys: str) -> str | None:
    if data is None:
        return None
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return str(cur) if cur is not None else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    root = args.repo_root
    exp33 = root / "experiments" / "33-unitree-mujoco-g1-bridge-probe"
    webqa = root / "experiments" / "03-digital-twin" / "web" / "qa" / "out"

    evidence_paths = {
        "sdk_capture_contract": exp33 / "verify" / "unitree-sdk2-python-capture-contract.json",
        "dds_preflight": exp33 / "verify" / "live-dds-capture-preflight.json",
        "local_dds_capture": exp33 / "verify" / "local-dds-capture-smoke" / "local_dds_capture_smoke_summary.json",
        "local_lowcmd_contract": exp33 / "verify" / "local-lowcmd-contract-smoke.json",
        "mujoco_lowcmd_closed_loop": exp33 / "verify" / "unitree-mujoco-lowcmd-closed-loop-smoke" / "unitree_mujoco_lowcmd_closed_loop_smoke_summary.json",
        "browser_lowcmd_closed_loop": exp33 / "verify" / "lowcmd-browser-closed-loop-smoke" / "lowcmd_browser_closed_loop_smoke_summary.json",
        "browser_lowcmd_unassisted": exp33 / "verify" / "lowcmd-browser-unassisted-smoke" / "lowcmd_browser_closed_loop_smoke_summary.json",
        "unassisted_lowcmd_gain_sweep": exp33 / "verify" / "unassisted-lowcmd-gain-sweep" / "unassisted_lowcmd_gain_sweep_summary.json",
        "mujoco_dds_capture_assisted": exp33 / "verify" / "unitree-mujoco-dds-elastic-smoke" / "unitree_mujoco_dds_capture_smoke_summary.json",
        "mujoco_dds_capture_collapse": exp33 / "verify" / "unitree-mujoco-dds-collapse-smoke" / "unitree_mujoco_dds_capture_smoke_summary.json",
        "mujoco_dds_websocket_assisted": exp33 / "verify" / "unitree-mujoco-dds-websocket-elastic-smoke" / "unitree_mujoco_dds_websocket_smoke_summary.json",
        "mujoco_dds_websocket_collapse": exp33 / "verify" / "unitree-mujoco-dds-websocket-collapse-smoke" / "unitree_mujoco_dds_websocket_smoke_summary.json",
        "browser_dds_assisted": webqa / "unitree-g1-elastic-stand_elastic_dds_stream_summary.json",
        "browser_dds_collapse": webqa / "unitree-g1-elastic-stand_collapse_dds_stream_summary.json",
        "real_robot_candidate": exp33 / "verify" / "real-robot-dds-candidate" / "candidate_gate_summary.json",
        "unassisted_controller_candidate": exp33 / "verify" / "unassisted-controller-candidate" / "candidate_gate_summary.json",
    }
    evidence = {name: load_json(path) for name, path in evidence_paths.items()}

    checks = {
        "sdk_capture_contract_pass": verdict_at(evidence["sdk_capture_contract"], "verdict") == "PASS",
        "dds_preflight_pass": verdict_at(evidence["dds_preflight"], "verdict") == "PASS",
        "local_dds_capture_pass": verdict_at(evidence["local_dds_capture"], "verdict") == "PASS",
        "local_lowcmd_contract_pass": verdict_at(evidence["local_lowcmd_contract"], "verdict") == "PASS",
        "mujoco_lowcmd_closed_loop_pass": verdict_at(evidence["mujoco_lowcmd_closed_loop"], "verdict") == "PASS",
        "browser_lowcmd_closed_loop_pass": verdict_at(evidence["browser_lowcmd_closed_loop"], "verdict") == "PASS",
        "browser_lowcmd_unassisted_rejected": verdict_at(evidence["browser_lowcmd_unassisted"], "verdict") == "FAIL",
        "unassisted_lowcmd_gain_sweep_rejected": verdict_at(evidence["unassisted_lowcmd_gain_sweep"], "verdict") == "FAIL_EXPECTED",
        "mujoco_dds_capture_assisted_pass": verdict_at(evidence["mujoco_dds_capture_assisted"], "verdict") == "PASS",
        "mujoco_dds_capture_collapse_rejected": verdict_at(evidence["mujoco_dds_capture_collapse"], "candidate_gate", "verdict") == "FAIL",
        "mujoco_dds_websocket_assisted_pass": verdict_at(evidence["mujoco_dds_websocket_assisted"], "verdict") == "PASS",
        "mujoco_dds_websocket_collapse_rejected": verdict_at(evidence["mujoco_dds_websocket_collapse"], "verdict") == "FAIL",
        "browser_dds_assisted_pass": verdict_at(evidence["browser_dds_assisted"], "verdict") == "PASS",
        "browser_dds_collapse_rejected": verdict_at(evidence["browser_dds_collapse"], "verdict") == "FAIL",
        "real_robot_candidate_pass": verdict_at(evidence["real_robot_candidate"], "verdict") == "PASS",
        "unassisted_controller_candidate_pass": verdict_at(evidence["unassisted_controller_candidate"], "verdict") == "PASS",
    }

    demo_ready = all(
        checks[key]
        for key in [
            "sdk_capture_contract_pass",
            "dds_preflight_pass",
            "local_dds_capture_pass",
            "local_lowcmd_contract_pass",
            "mujoco_lowcmd_closed_loop_pass",
            "browser_lowcmd_closed_loop_pass",
            "browser_lowcmd_unassisted_rejected",
            "unassisted_lowcmd_gain_sweep_rejected",
            "mujoco_dds_capture_assisted_pass",
            "mujoco_dds_capture_collapse_rejected",
            "mujoco_dds_websocket_assisted_pass",
            "mujoco_dds_websocket_collapse_rejected",
            "browser_dds_assisted_pass",
            "browser_dds_collapse_rejected",
        ]
    )
    complete = demo_ready and (checks["real_robot_candidate_pass"] or checks["unassisted_controller_candidate_pass"])

    missing_completion_evidence = []
    if not checks["real_robot_candidate_pass"]:
        missing_completion_evidence.append(str(evidence_paths["real_robot_candidate"]))
    if not checks["unassisted_controller_candidate_pass"]:
        missing_completion_evidence.append(str(evidence_paths["unassisted_controller_candidate"]))

    if complete:
        interpretation = (
            "Browser-consumable DDS state path, assisted LowCmd-to-MuJoCo-to-browser command path, and an unassisted "
            "Unitree RL Lab G1-29DOF policy browser candidate all pass. Real robot telemetry remains separate future evidence, "
            "but the simulated controller-backed G1 digital twin gate is complete."
        )
    else:
        interpretation = (
            "Browser-consumable DDS state path and LowCmd-to-MuJoCo-to-browser closed-loop command path are demo-ready with assisted Unitree MJCF evidence, "
            "but full completion still requires real robot telemetry or unassisted stable controller telemetry."
        )

    summary = {
        "verdict": "COMPLETE" if complete else ("PARTIAL_ASSISTED" if demo_ready else "NOT_READY"),
        "contract": "physical-ai-g1-digital-twin-readiness-v0",
        "demo_ready": demo_ready,
        "complete": complete,
        "checks": checks,
        "evidence_paths": {name: str(path) for name, path in evidence_paths.items()},
        "missing_completion_evidence": [] if complete else missing_completion_evidence,
        "interpretation": interpretation,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if demo_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
