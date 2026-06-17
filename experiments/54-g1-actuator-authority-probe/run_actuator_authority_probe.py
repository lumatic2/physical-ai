"""Probe whether extra simulated actuator authority deepens the G1 squat."""

from __future__ import annotations

import argparse
import importlib.util
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP52_PATH = ROOT / "experiments/52-g1-foot-contact-aware-height-controller/run_contact_height_controller.py"


def load_exp52():
    spec = importlib.util.spec_from_file_location("exp52_contact_height", EXP52_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP52_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP52 = load_exp52()


LOWER_BODY = (
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
)
ANKLES = (
    "left_ankle_pitch_joint",
    "left_ankle_roll_joint",
    "right_ankle_pitch_joint",
    "right_ankle_roll_joint",
)


def scale_actuators(model: Any, *, lower_scale: float, ankle_scale: float) -> dict[str, Any]:
    snapshot = {}
    for actuator_id in range(model.nu):
        name = model.actuator(actuator_id).name
        scale = lower_scale if name in LOWER_BODY else 1.0
        if name in ANKLES:
            scale *= ankle_scale
        before = {
            "gain": float(model.actuator_gainprm[actuator_id, 0]),
            "bias_q": float(model.actuator_biasprm[actuator_id, 1]),
        }
        if scale != 1.0:
            model.actuator_gainprm[actuator_id, 0] *= scale
            model.actuator_biasprm[actuator_id, 1] *= scale
        after = {
            "gain": float(model.actuator_gainprm[actuator_id, 0]),
            "bias_q": float(model.actuator_biasprm[actuator_id, 1]),
            "scale": scale,
        }
        snapshot[name] = {"before": before, "after": after}
    return snapshot


@contextmanager
def scaled_contact_env(lower_scale: float, ankle_scale: float) -> Iterator[dict[str, Any]]:
    original_cls = EXP52.EXP28.ContactAwareSquat
    holder: dict[str, Any] = {}

    def factory(*args: Any, **kwargs: Any) -> Any:
        env = original_cls(*args, **kwargs)
        holder["actuator_scaling"] = scale_actuators(
            env.mj_model,
            lower_scale=lower_scale,
            ankle_scale=ankle_scale,
        )
        return env

    EXP52.EXP28.ContactAwareSquat = factory
    try:
        yield holder
    finally:
        EXP52.EXP28.ContactAwareSquat = original_cls


def stance_pass(run: dict[str, Any]) -> bool:
    return (
        run["fell_at"] is None
        and run["return_to_stand"]
        and run["foot_contact_ratio"] >= 0.90
        and run["foot_slip_distance"] <= 0.15
        and run["max_joint_limit_violation"] <= 0.05
    )


def pose_pass(run: dict[str, Any]) -> bool:
    return (
        run["visible_drop"] >= 0.08
        and run["max_knee_delta_rad"] >= 0.60
        and run["max_hip_pitch_delta_rad"] >= 0.35
    )


def authority_verdict(run: dict[str, Any]) -> str:
    if stance_pass(run) and pose_pass(run):
        return "PASS_NATIVE_VISIBLE_GATE"
    if not stance_pass(run):
        return "STANCE_ENVELOPE_BROKEN"
    if run["visible_drop"] < 0.08:
        return "STABLE_BUT_SHALLOW"
    return "POSE_OR_RETURN_PENDING"


def run_variant(variant: dict[str, Any], out_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    with scaled_contact_env(variant["lower_scale"], variant["ankle_scale"]) as holder:
        run = EXP52.native_eval(
            attempt=variant["attempt"],
            drop=variant["drop"],
            max_blend=variant["max_blend"],
            policy_weight=1.0,
            adapt_gain=variant["adapt_gain"],
            descend_s=2.6,
            hold_s=0.4,
            return_s=1.4,
            seconds=args.seconds,
            support_floor=args.support_floor,
            slip_limit=args.slip_limit,
            out_dir=out_dir / variant["attempt"],
        )
    run["lower_actuator_scale"] = variant["lower_scale"]
    run["ankle_extra_scale"] = variant["ankle_scale"]
    run["authority_verdict"] = authority_verdict(run)
    run["actuator_scaling"] = holder.get("actuator_scaling", {})
    return run


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Actuator Authority Probe Summary",
        "",
        "| Attempt | Verdict | Lower x | Ankle extra x | Drop | Knee | Hip | Contact | Slip | Final h | Fell |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {run['attempt']} | {run['authority_verdict']} | {run['lower_actuator_scale']:.2f} | "
            f"{run['ankle_extra_scale']:.2f} | {run['visible_drop']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | "
            f"{run['final_height']:.4f}m | {fell} |"
        )
    lines.extend(
        [
            "",
            f"Best no-fall run: {result['best_no_fall']}",
            f"Best depth run: {result['best_depth']}",
            "",
            "This is a simulation authority diagnostic only. It does not prove that the physical G1 can safely execute the same controller.",
        ]
    )
    (out_dir / "authority-probe-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--support-floor", type=float, default=-0.005)
    parser.add_argument("--slip-limit", type=float, default=0.08)
    args = parser.parse_args()

    out_dir = VERIFY / "actuator-authority"
    out_dir.mkdir(parents=True, exist_ok=True)
    variants = [
        {"attempt": "baseline-gain1p0", "drop": 0.08, "max_blend": 0.38, "adapt_gain": 0.11, "lower_scale": 1.0, "ankle_scale": 1.0},
        {"attempt": "lower-gain1p5", "drop": 0.08, "max_blend": 0.38, "adapt_gain": 0.11, "lower_scale": 1.5, "ankle_scale": 1.0},
        {"attempt": "lower-gain2p0", "drop": 0.08, "max_blend": 0.38, "adapt_gain": 0.11, "lower_scale": 2.0, "ankle_scale": 1.0},
        {"attempt": "lower-gain1p5-ankle3p0", "drop": 0.08, "max_blend": 0.38, "adapt_gain": 0.11, "lower_scale": 1.5, "ankle_scale": 3.0},
        {"attempt": "lower-gain2p0-ankle3p0", "drop": 0.08, "max_blend": 0.38, "adapt_gain": 0.11, "lower_scale": 2.0, "ankle_scale": 3.0},
    ]
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 probes whether simulated actuator authority, not joint range alone, is blocking visible squat depth.",
            "perspectives": {
                "product": "answers whether the robot-class can plausibly squat before more PPO work",
                "architecture": "wraps exp52 native gate and only scales MuJoCo position actuator gain/bias",
                "security": "no credentials or external side effects",
                "qa": "native sweep logs stance, pose, return, contact, slip, fall",
                "skeptic": "gain scaling may create a non-physical simulator success or simply destabilize contact",
            },
            "dod": [
                "official/public G1 capability evidence captured in README",
                "native JSON per authority variant",
                "summary identifies whether authority helps or the stance cliff remains",
            ],
        },
        "runs": [],
    }
    for variant in variants:
        result["runs"].append(run_variant(variant, out_dir, args))

    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    best_depth = max(result["runs"], key=lambda run: run["visible_drop"])
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "visible_drop": best_no_fall["visible_drop"],
        "foot_slip_distance": best_no_fall["foot_slip_distance"],
        "return_to_stand": best_no_fall["return_to_stand"],
    }
    result["best_depth"] = {
        "attempt": best_depth["attempt"],
        "visible_drop": best_depth["visible_drop"],
        "fell_at": best_depth["fell_at"],
        "foot_slip_distance": best_depth["foot_slip_distance"],
    }
    result["verdict"] = (
        "PASS_M19_NATIVE_ONLY"
        if any(run["authority_verdict"] == "PASS_NATIVE_VISIBLE_GATE" for run in result["runs"])
        else "FAIL_M19_NATIVE_GATE"
    )
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["verdict"], json.dumps({"best_no_fall": result["best_no_fall"], "best_depth": result["best_depth"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
