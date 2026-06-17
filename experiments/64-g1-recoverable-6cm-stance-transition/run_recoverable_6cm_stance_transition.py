"""Probe a recoverable 6cm stance transition before reattempting 8cm M19.

exp63 showed that static 8cm targets are solvable but dynamic rollout still
splits into shallow no-fall or support/ZMP collapse. This experiment narrows
the next gate to a 6cm recoverable transition with contact, stance, and return.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP60_PATH = ROOT / "experiments/60-g1-safe-combo-curriculum-probe/run_safe_combo_curriculum_probe.py"
EXP62_PATH = ROOT / "experiments/62-g1-actuator-contact-wbc-probe/run_actuator_contact_wbc_probe.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP60 = load_module("exp60_safe_combo", EXP60_PATH)
EXP62 = load_module("exp62_actuator_contact", EXP62_PATH)


def recoverable_6cm_gate(run: dict[str, Any]) -> bool:
    return (
        run["fell_at"] is None
        and run["visible_drop"] >= 0.06
        and run["return_to_stand"]
        and run["foot_contact_ratio"] >= 0.90
        and run["foot_slip_distance"] <= 0.08
        and run["max_joint_limit_violation"] <= 0.05
    )


def annotate(run: dict[str, Any], family: str) -> dict[str, Any]:
    run["family"] = family
    run["recoverable_6cm_gate"] = recoverable_6cm_gate(run)
    if run["recoverable_6cm_gate"]:
        run["transition_verdict"] = "PASS_RECOVERABLE_6CM_GATE"
    elif run["fell_at"] is not None:
        run["transition_verdict"] = "FAIL_FALL"
    elif run["visible_drop"] < 0.06:
        run["transition_verdict"] = "DEPTH_PENDING_6CM"
    elif not run["return_to_stand"]:
        run["transition_verdict"] = "RETURN_PENDING"
    elif run["foot_contact_ratio"] < 0.90:
        run["transition_verdict"] = "CONTACT_PENDING"
    elif run["foot_slip_distance"] > 0.08:
        run["transition_verdict"] = "STANCE_SLIP_PENDING"
    else:
        run["transition_verdict"] = "GATE_PENDING"
    return run


def safe_combo_run(variant: dict[str, Any], seconds: float, out_dir: Path) -> dict[str, Any]:
    base_gains = {
        "pitch": 2.0,
        "ankle_pitch": -1.4,
        "roll": 1.6,
        "ankle_roll": -1.0,
        "clip_pitch": 0.16,
        "clip_roll": 0.08,
    }
    signs = {"pitch": 1.0, "ankle_pitch": 1.0, "roll": 1.0, "ankle_roll": 1.0}
    run = EXP60.native_eval(
        attempt=variant["attempt"],
        drop=variant["drop"],
        max_blend=variant["max_blend"],
        policy_weight=1.0,
        adapt_gain=variant["adapt_gain"],
        descend_s=variant["descend_s"],
        hold_s=variant["hold_s"],
        return_s=variant["return_s"],
        seconds=seconds,
        support_floor=variant["support_floor"],
        slip_limit=variant["slip_limit"],
        gains=base_gains,
        signs=signs,
        feedback_source="com",
        residual_pattern=variant["pattern"],
        residual_scale=variant["scale"],
        filter_mode=variant["filter"],
        out_dir=out_dir,
    )
    return annotate(run, "safe_combo")


def torque_run(variant: dict[str, Any], seconds: float, out_dir: Path) -> dict[str, Any]:
    run = EXP62.native_eval(variant=variant, seconds=seconds, out_dir=out_dir)
    return annotate(run, "actuator_qfrc")


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Recoverable 6cm Stance Transition Summary",
        "",
        "| Attempt | Family | 6cm gate | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate = "PASS" if run["recoverable_6cm_gate"] else "FAIL"
        lines.append(
            f"| {run['attempt']} | {run['family']} | {gate} | {run['transition_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | "
            f"{run['max_hip_pitch_delta_rad']:.3f} | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['min_support_margin']:.4f}m | "
            f"{run['min_zmp_margin']:.4f}m | {run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        f"Best recoverable run: {result['best_recoverable']}",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best depth run: {result['best_depth']}",
        "",
        "This is an intermediate gate. M19 still requires exp29 8cm visible depth, knee/hip pose, native no-fall, browser replay, contact, stance, and return together.",
    ])
    (out_dir / "recoverable-6cm-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY / "recoverable-6cm"
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_variants = [
        {"attempt": "safe-6cm-r0p060", "drop": 0.06, "max_blend": 0.50, "adapt_gain": 0.14, "descend_s": 3.0, "hold_s": 0.5, "return_s": 1.6, "support_floor": -0.005, "slip_limit": 0.08, "pattern": "safe_combo", "scale": 0.060, "filter": "none"},
        {"attempt": "safe-6cm-r0p070", "drop": 0.06, "max_blend": 0.50, "adapt_gain": 0.14, "descend_s": 3.1, "hold_s": 0.5, "return_s": 1.7, "support_floor": -0.005, "slip_limit": 0.08, "pattern": "safe_combo", "scale": 0.070, "filter": "none"},
        {"attempt": "safe-6p5cm-r0p060", "drop": 0.065, "max_blend": 0.51, "adapt_gain": 0.13, "descend_s": 3.2, "hold_s": 0.5, "return_s": 1.8, "support_floor": -0.005, "slip_limit": 0.08, "pattern": "safe_combo", "scale": 0.060, "filter": "none"},
        {"attempt": "soft-6p5cm-r0p075", "drop": 0.065, "max_blend": 0.51, "adapt_gain": 0.13, "descend_s": 3.2, "hold_s": 0.5, "return_s": 1.8, "support_floor": -0.005, "slip_limit": 0.08, "pattern": "safe_combo", "scale": 0.075, "filter": "soft"},
        {"attempt": "safe-8cm-r0p060-6gate", "drop": 0.08, "max_blend": 0.50, "adapt_gain": 0.14, "descend_s": 3.0, "hold_s": 0.5, "return_s": 1.6, "support_floor": -0.005, "slip_limit": 0.08, "pattern": "safe_combo", "scale": 0.060, "filter": "none"},
        {"attempt": "safe-8cm-r0p075-6gate", "drop": 0.08, "max_blend": 0.52, "adapt_gain": 0.13, "descend_s": 3.4, "hold_s": 0.5, "return_s": 1.8, "support_floor": -0.010, "slip_limit": 0.08, "pattern": "safe_combo", "scale": 0.075, "filter": "none"},
        {"attempt": "soft-8cm-r0p080-6gate", "drop": 0.08, "max_blend": 0.52, "adapt_gain": 0.13, "descend_s": 3.4, "hold_s": 0.5, "return_s": 1.8, "support_floor": -0.010, "slip_limit": 0.08, "pattern": "safe_combo", "scale": 0.080, "filter": "soft"},
    ]
    torque_common = {
        "hold_s": 0.5,
        "support_floor": -0.005,
        "zmp_floor": -0.030,
        "slip_limit": 0.08,
        "policy_weight": 1.0,
        "joint_kd": 1.2,
        "foot_kd_xy": 12.0,
        "foot_lift_force": 120.0,
    }
    torque_variants = [
        {"attempt": "torque-6cm-r0p060-t20", "drop": 0.06, "max_blend": 0.50, "residual_scale": 0.060, "joint_kp": 18.0, "torque_clip": 20.0, "foot_kp_xy": 0.0, "foot_force_clip": 0.0, "descend_s": 3.6, "return_s": 1.8, **torque_common},
        {"attempt": "torque-6p5cm-r0p060-t20", "drop": 0.065, "max_blend": 0.51, "residual_scale": 0.060, "joint_kp": 18.0, "torque_clip": 20.0, "foot_kp_xy": 0.0, "foot_force_clip": 0.0, "descend_s": 3.8, "return_s": 1.9, **torque_common},
        {"attempt": "torque-6cm-r0p070-t30", "drop": 0.06, "max_blend": 0.50, "residual_scale": 0.070, "joint_kp": 22.0, "torque_clip": 30.0, "foot_kp_xy": 0.0, "foot_force_clip": 0.0, "descend_s": 3.8, "return_s": 1.9, **torque_common},
        {"attempt": "torque-8cm-r0p060-t20-6gate", "drop": 0.08, "max_blend": 0.50, "residual_scale": 0.060, "joint_kp": 18.0, "torque_clip": 20.0, "foot_kp_xy": 0.0, "foot_force_clip": 0.0, "descend_s": 4.0, "return_s": 2.0, **torque_common},
        {"attempt": "torque-8cm-r0p065-t24-6gate", "drop": 0.08, "max_blend": 0.51, "residual_scale": 0.065, "joint_kp": 20.0, "torque_clip": 24.0, "foot_kp_xy": 0.0, "foot_force_clip": 0.0, "descend_s": 4.2, "return_s": 2.0, **torque_common},
        {"attempt": "torque-8p5cm-r0p065-t24-6gate", "drop": 0.085, "max_blend": 0.52, "residual_scale": 0.065, "joint_kp": 20.0, "torque_clip": 24.0, "foot_kp_xy": 0.0, "foot_force_clip": 0.0, "descend_s": 4.4, "return_s": 2.0, **torque_common},
    ]

    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 adds an explicit recoverable 6cm stance-transition intermediate gate before another 8cm visible-gate attempt.",
            "perspectives": {
                "product": "creates a smaller showable transition gate on the path to visible squat",
                "architecture": "reuses exp60 safe_combo and exp62 actuator qfrc controllers without changing shared code",
                "security": "no credentials or external side effects",
                "qa": "native sweep records 6cm depth, no-fall, contact, slip, return, support/ZMP, pose metrics",
                "skeptic": "a 6cm pass is not M19; it only proves a recoverable intermediate corridor",
            },
            "dod": [
                "raw native JSON for safe_combo and qfrc variants",
                "summary states whether any variant passes recoverable_6cm_gate",
            ],
        },
        "runs": [],
    }
    for variant in safe_variants:
        result["runs"].append(safe_combo_run(variant, args.seconds, out_dir / variant["attempt"]))
    for variant in torque_variants:
        result["runs"].append(torque_run(variant, args.seconds, out_dir / variant["attempt"]))

    recoverable = [run for run in result["runs"] if run["recoverable_6cm_gate"]]
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_recoverable = max(recoverable, key=lambda run: run["visible_drop"], default=None)
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    best_depth = max(result["runs"], key=lambda run: run["visible_drop"])
    result["best_recoverable"] = None if best_recoverable is None else {
        "attempt": best_recoverable["attempt"],
        "visible_drop": best_recoverable["visible_drop"],
        "foot_contact_ratio": best_recoverable["foot_contact_ratio"],
        "foot_slip_distance": best_recoverable["foot_slip_distance"],
        "return_to_stand": best_recoverable["return_to_stand"],
    }
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "visible_drop": best_no_fall["visible_drop"],
        "transition_verdict": best_no_fall["transition_verdict"],
    }
    result["best_depth"] = {
        "attempt": best_depth["attempt"],
        "visible_drop": best_depth["visible_drop"],
        "fell_at": best_depth["fell_at"],
        "transition_verdict": best_depth["transition_verdict"],
    }
    result["verdict"] = "PASS_RECOVERABLE_6CM_GATE" if recoverable else "FAIL_RECOVERABLE_6CM_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({
        "best_recoverable": result["best_recoverable"],
        "best_no_fall": result["best_no_fall"],
        "best_depth": result["best_depth"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
