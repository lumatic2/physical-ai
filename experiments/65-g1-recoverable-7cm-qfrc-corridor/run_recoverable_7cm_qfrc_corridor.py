"""Probe whether the exp64 qfrc corridor extends from 6cm to 7cm."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP62_PATH = ROOT / "experiments/62-g1-actuator-contact-wbc-probe/run_actuator_contact_wbc_probe.py"


def load_exp62():
    spec = importlib.util.spec_from_file_location("exp62_actuator_contact", EXP62_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP62_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP62 = load_exp62()


def recoverable_7cm_gate(run: dict[str, Any]) -> bool:
    return (
        run["fell_at"] is None
        and run["visible_drop"] >= 0.07
        and run["return_to_stand"]
        and run["foot_contact_ratio"] >= 0.90
        and run["foot_slip_distance"] <= 0.08
        and run["max_joint_limit_violation"] <= 0.05
    )


def annotate(run: dict[str, Any]) -> dict[str, Any]:
    run["recoverable_7cm_gate"] = recoverable_7cm_gate(run)
    if run["recoverable_7cm_gate"]:
        run["transition_verdict"] = "PASS_RECOVERABLE_7CM_GATE"
    elif run["fell_at"] is not None:
        run["transition_verdict"] = "FAIL_FALL"
    elif run["visible_drop"] < 0.07:
        run["transition_verdict"] = "DEPTH_PENDING_7CM"
    elif not run["return_to_stand"]:
        run["transition_verdict"] = "RETURN_PENDING"
    elif run["foot_contact_ratio"] < 0.90:
        run["transition_verdict"] = "CONTACT_PENDING"
    elif run["foot_slip_distance"] > 0.08:
        run["transition_verdict"] = "STANCE_SLIP_PENDING"
    else:
        run["transition_verdict"] = "GATE_PENDING"
    return run


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Recoverable 7cm QFRC Corridor Summary",
        "",
        "| Attempt | 7cm gate | Verdict | Drop | Knee | Hip | Contact | Slip | CoM min | ZMP min | Final h | Fell |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate = "PASS" if run["recoverable_7cm_gate"] else "FAIL"
        lines.append(
            f"| {run['attempt']} | {gate} | {run['transition_verdict']} | "
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
        "This remains an intermediate corridor gate. M19 still requires exp29 8cm visible depth, knee/hip pose, native no-fall, browser replay, contact, stance, and return together.",
    ])
    (out_dir / "recoverable-7cm-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY / "recoverable-7cm"
    out_dir.mkdir(parents=True, exist_ok=True)

    common = {
        "policy_weight": 1.0,
        "joint_kd": 1.2,
        "foot_kp_xy": 0.0,
        "foot_force_clip": 0.0,
        "foot_kd_xy": 12.0,
        "foot_lift_force": 120.0,
    }
    variants = [
        {"attempt": "qfrc-8cm-r0p065-t24-baseline", "drop": 0.08, "max_blend": 0.51, "residual_scale": 0.065, "joint_kp": 20.0, "torque_clip": 24.0, "descend_s": 4.2, "return_s": 2.0, **common},
        {"attempt": "qfrc-8cm-r0p070-t24", "drop": 0.08, "max_blend": 0.52, "residual_scale": 0.070, "joint_kp": 20.0, "torque_clip": 24.0, "descend_s": 4.2, "return_s": 2.0, **common},
        {"attempt": "qfrc-8cm-r0p070-t28", "drop": 0.08, "max_blend": 0.52, "residual_scale": 0.070, "joint_kp": 22.0, "torque_clip": 28.0, "descend_s": 4.3, "return_s": 2.0, **common},
        {"attempt": "qfrc-8p2cm-r0p068-t26", "drop": 0.082, "max_blend": 0.52, "residual_scale": 0.068, "joint_kp": 21.0, "torque_clip": 26.0, "descend_s": 4.3, "return_s": 2.0, **common},
        {"attempt": "qfrc-8p5cm-r0p068-t26", "drop": 0.085, "max_blend": 0.52, "residual_scale": 0.068, "joint_kp": 21.0, "torque_clip": 26.0, "descend_s": 4.5, "return_s": 2.0, **common},
        {"attempt": "qfrc-8p5cm-r0p070-t28", "drop": 0.085, "max_blend": 0.53, "residual_scale": 0.070, "joint_kp": 22.0, "torque_clip": 28.0, "descend_s": 4.6, "return_s": 2.0, **common},
        {"attempt": "qfrc-9cm-r0p068-t26-slow", "drop": 0.09, "max_blend": 0.52, "residual_scale": 0.068, "joint_kp": 21.0, "torque_clip": 26.0, "descend_s": 4.8, "return_s": 2.2, **common},
        {"attempt": "qfrc-8p5cm-r0p068-t26-early-return", "drop": 0.085, "max_blend": 0.52, "residual_scale": 0.068, "joint_kp": 21.0, "torque_clip": 26.0, "descend_s": 4.1, "return_s": 1.3, **common},
        {"attempt": "qfrc-8p5cm-r0p070-t28-early-return", "drop": 0.085, "max_blend": 0.53, "residual_scale": 0.070, "joint_kp": 22.0, "torque_clip": 28.0, "descend_s": 4.2, "return_s": 1.3, **common},
        {"attempt": "qfrc-8p3cm-r0p070-t28-early-return", "drop": 0.083, "max_blend": 0.53, "residual_scale": 0.070, "joint_kp": 22.0, "torque_clip": 28.0, "descend_s": 4.0, "return_s": 1.4, **common},
    ]

    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 extends the exp64 qfrc recoverable corridor from a 6cm intermediate gate toward 7cm before reattempting exp29 8cm/browser replay.",
            "perspectives": {
                "product": "turns the 6cm transition into a stronger stepping stone toward visible squat",
                "architecture": "keeps shared controllers fixed and sweeps only exp62 qfrc target/blend/residual/torque parameters",
                "security": "no credentials or external side effects",
                "qa": "native sweep records 7cm depth, no-fall, contact, slip, return, support/ZMP, pose metrics",
                "skeptic": "7cm may sit past the current qfrc stability cliff and still not prove M19",
            },
            "dod": [
                "raw native JSON for qfrc variants",
                "summary states whether any variant passes recoverable_7cm_gate",
            ],
        },
        "runs": [],
    }
    for variant in variants:
        result["runs"].append(annotate(EXP62.native_eval(
            variant=variant,
            seconds=args.seconds,
            out_dir=out_dir / variant["attempt"],
        )))

    recoverable = [run for run in result["runs"] if run["recoverable_7cm_gate"]]
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
    result["verdict"] = "PASS_RECOVERABLE_7CM_GATE" if recoverable else "FAIL_RECOVERABLE_7CM_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({
        "best_recoverable": result["best_recoverable"],
        "best_no_fall": result["best_no_fall"],
        "best_depth": result["best_depth"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
