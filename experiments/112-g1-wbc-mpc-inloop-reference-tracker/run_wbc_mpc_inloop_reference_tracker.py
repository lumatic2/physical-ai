"""WBC/MPC-in-loop primitive selector for the G1 visible squat gate."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP91_PATH = ROOT / "experiments/91-g1-contact-constrained-pose-qfrc-wrapper/run_contact_constrained_pose_qfrc_wrapper.py"


def load_exp91():
    spec = importlib.util.spec_from_file_location("exp91_contact_pose_qfrc", EXP91_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP91_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP91 = load_exp91()
EXP67 = EXP91.EXP67
BASE_CHOOSE = EXP91.multi_step_choose_blend


def visible_score_from_chosen(chosen: dict[str, Any], kwargs: dict[str, Any], local_variant: dict[str, Any]) -> float:
    """Score one primitive's short-horizon candidate with exp29-oriented terms."""
    desired_fraction = float(kwargs["desired_fraction"])
    return_phase = float(kwargs["return_phase"])
    start_height = float(kwargs["start_height"])
    target_drop = float(local_variant["drop"]) * max(0.0, desired_fraction - 0.25 * return_phase)
    achieved_drop = max(0.0, start_height - float(chosen["height"]))
    drop_shortfall = max(0.0, target_drop - achieved_drop)
    knee_target = float(local_variant["target_knee_delta"]) * max(0.0, desired_fraction)
    hip_target = float(local_variant["target_hip_delta"]) * max(0.0, desired_fraction)
    knee_shortfall = max(0.0, knee_target - float(chosen.get("horizon_knee_delta", 0.0)))
    hip_shortfall = max(0.0, hip_target - float(chosen.get("horizon_hip_delta", 0.0)))
    support_shortfall = max(0.0, float(local_variant["support_floor"]) - float(chosen["horizon_min_support"]))
    zmp_shortfall = max(0.0, float(local_variant["zmp_floor"]) - float(chosen["horizon_min_zmp"]))
    slip_excess = max(0.0, float(chosen["horizon_max_slip"]) - float(local_variant["slip_floor"]))
    contact_loss = float(chosen["horizon_contact_loss_count"])
    qfrc_excess = max(0.0, float(chosen["qfrc_max"]) - float(local_variant["qfrc_soft_cap"]))
    stand_shortfall = max(0.0, float(local_variant["stand_height"]) - float(chosen["height"])) * max(0.0, return_phase)
    return (
        float(chosen["cost"])
        + float(local_variant["mpc_w_drop"]) * drop_shortfall * drop_shortfall
        + float(local_variant["mpc_w_knee"]) * knee_shortfall * knee_shortfall
        + float(local_variant["mpc_w_hip"]) * hip_shortfall * hip_shortfall
        + float(local_variant["mpc_w_support"]) * support_shortfall * support_shortfall
        + float(local_variant["mpc_w_zmp"]) * zmp_shortfall * zmp_shortfall
        + float(local_variant["mpc_w_slip"]) * slip_excess * slip_excess
        + float(local_variant["mpc_w_contact"]) * contact_loss
        + float(local_variant["mpc_w_qfrc"]) * qfrc_excess * qfrc_excess
        + float(local_variant["mpc_w_stand"]) * stand_shortfall * stand_shortfall
    )


def primitive_mpc_choose(**kwargs):
    variant = kwargs["variant"]
    best: dict[str, Any] | None = None
    for primitive in variant["mpc_primitives"]:
        local_variant = {**variant, **primitive}
        local_variant.pop("mpc_primitives", None)
        target, qfrc, chosen = BASE_CHOOSE(**{**kwargs, "variant": local_variant})
        score = visible_score_from_chosen(chosen, kwargs, local_variant)
        row = {
            "score": score,
            "target": target,
            "qfrc": qfrc,
            "chosen": {
                **chosen,
                "mpc_primitive": primitive["name"],
                "mpc_score": score,
                "mpc_mode": "primitive_short_horizon",
            },
        }
        if best is None or score < best["score"]:
            best = row
    assert best is not None
    return best["target"], best["qfrc"], best["chosen"]


def mpc_variants() -> list[dict[str, Any]]:
    base = {run["attempt"]: run for run in EXP91.variants()}
    common = {
        "mpc_w_drop": 220.0,
        "mpc_w_knee": 120.0,
        "mpc_w_hip": 95.0,
        "mpc_w_support": 12500.0,
        "mpc_w_zmp": 8000.0,
        "mpc_w_slip": 18000.0,
        "mpc_w_contact": 1100.0,
        "mpc_w_qfrc": 0.08,
        "mpc_w_stand": 4200.0,
    }
    return [
        {
            **base["poseqfrc-braked-8cm"],
            **common,
            "attempt": "mpc-braked-8cm-three-primitive",
            "horizon_steps": 9,
            "mpc_primitives": [
                {"name": "safety-hold", "max_blend": 0.465, "residual_scale": 0.046, "depth_cap": 0.085, "w_slip": 26000.0, "w_contact": 1400.0, "pose_qfrc_scale": 0.45, "pose_qfrc_clip": 12.0},
                {"name": "visible-push", "max_blend": 0.505, "residual_scale": 0.056, "depth_cap": 0.115, "w_knee": 360.0, "w_hip": 360.0, "pose_qfrc_scale": 0.95, "pose_qfrc_clip": 20.0},
                {"name": "return-guard", "max_blend": 0.475, "residual_scale": 0.046, "return_joint_kp": 54.0, "return_torque_clip": 74.0, "w_stand": 1800.0, "return_s": 3.2, "recapture_s": 2.1},
            ],
        },
        {
            **base["poseqfrc-braked-knee"],
            **common,
            "attempt": "mpc-knee-contact-return",
            "horizon_steps": 8,
            "mpc_w_knee": 180.0,
            "mpc_primitives": [
                {"name": "contact-tight", "max_blend": 0.470, "residual_scale": 0.046, "foot_kp_xy": 680.0, "foot_force_clip": 520.0, "w_slip": 30000.0, "pose_qfrc_scale": 0.60},
                {"name": "knee-overtarget", "max_blend": 0.500, "residual_scale": 0.052, "target_knee_delta": 0.68, "target_hip_delta": 0.38, "w_knee": 460.0, "pose_qfrc_scale": 1.05, "pose_qfrc_clip": 22.0},
                {"name": "early-recapture", "max_blend": 0.480, "residual_scale": 0.048, "recapture_s": 2.25, "return_s": 3.35, "recapture_drop": 0.085, "w_recapture_height": 16000.0},
            ],
        },
        {
            **base["poseqfrc-braked-return"],
            **common,
            "attempt": "mpc-return-biased-visible",
            "horizon_steps": 10,
            "mpc_w_stand": 5600.0,
            "mpc_primitives": [
                {"name": "minimal-slip", "max_blend": 0.455, "residual_scale": 0.044, "depth_cap": 0.080, "w_slip": 34000.0, "w_contact": 1600.0, "pose_qfrc_scale": 0.45},
                {"name": "hip-visible", "max_blend": 0.495, "residual_scale": 0.052, "knee_amp": 0.11, "hip_bias": 0.22, "w_hip": 460.0, "pose_qfrc_scale": 0.82},
                {"name": "standup", "max_blend": 0.465, "residual_scale": 0.042, "return_joint_kp": 62.0, "return_torque_clip": 82.0, "return_s": 3.5, "recapture_s": 2.4, "w_stand": 2400.0},
            ],
        },
    ]


def visible_score(run: dict[str, Any]) -> float:
    gap = run["visible_gap"]
    return float(
        (1000.0 if run["fell_at"] is not None else 0.0)
        + 360.0 * gap["drop_shortfall_m"] / 0.08
        + 280.0 * gap["knee_shortfall_rad"] / 0.60
        + 220.0 * gap["hip_shortfall_rad"] / 0.35
        + 300.0 * gap["slip_excess_m"] / 0.08
        + 240.0 * max(0.0, 0.90 - run["foot_contact_ratio"])
        + 180.0 * max(0.0, 0.74 - run["final_height"])
        - (900.0 if run["visible_8cm_gate"] else 0.0)
    )


def write_summary(result: dict[str, Any]) -> None:
    lines = [
        "# G1 WBC/MPC In-Loop Reference Tracker Summary",
        "",
        "| Rank | Attempt | Score | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fall |",
        "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, run in enumerate(sorted(result["runs"], key=lambda item: item["mpc_visible_score"]), start=1):
        fall = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {rank} | {run['attempt']} | {run['mpc_visible_score']:.1f} | {run['visible_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | {run['final_height']:.4f}m | {fall} |"
        )
    lines.extend([
        "",
        f"Best MPC run: {result['best_mpc']}",
        f"Best visible run: {result['best_visible']}",
        "",
        "Browser replay is attempted only after native exp29 visible gate passes.",
    ])
    (VERIFY / "wbc-mpc-inloop-reference-tracker-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(result: dict[str, Any]) -> None:
    rows = []
    for run in sorted(result["runs"], key=lambda item: item["mpc_visible_score"]):
        fall = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        rows.append(
            f"| {run['attempt']} | {run['visible_verdict']} | {run['visible_drop']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | "
            f"{run['final_height']:.4f}m | {run['return_to_stand']} | {fall} |"
        )
    best = result["best_mpc"]
    readme = f"""# 112-g1-wbc-mpc-inloop-reference-tracker — G1 WBC/MPC-in-loop reference tracker

## 1. 가설 (Hypothesis)

G1은 공개 자료와 연구 사례상 스쿼트 형태 자체는 가능하지만, 우리 local M19 실패는 자세 target 불가능성이 아니라 contact/slip/return을 동시에 보는 동적 controller 부재일 가능성이 크다. 매 control tick에서 여러 WBC primitive를 짧은 MuJoCo horizon으로 비교해 고르면 reward retrain이나 one-shot qfrc wrapper보다 exp29 visible gate에 가까워질 것이다.

## 2. 방법 (Method)

- 기반: exp91 contact-constrained pose qfrc wrapper와 exp67 native evaluator.
- 변경: `choose_blend`를 primitive MPC wrapper로 monkeypatch했다. 각 tick마다 safety-hold, visible-push, return-guard 계열 primitive를 각각 short-horizon으로 rollout하고, drop/knee/hip/support/ZMP/contact/slip/stand 비용으로 다시 고른다.
- 판정: exp29 native visible gate를 통과한 경우에만 browser replay를 시도한다.
- 실행: `python run_wbc_mpc_inloop_reference_tracker.py --seconds {result['evaluation_seconds']}`.

### 웹 근거

- Unitree 공식 G1 설명은 큰 관절 가동 범위와 imitation/RL driven 특성을 내세운다. 접근일: 2026-06-18. https://www.unitree.com/g1
- Quadruped G1 operation docs에는 `Squat Mode`가 명시되어 있으며, 단 balance control 없는 slow transition이라고 설명한다. 접근일: 2026-06-18. https://docs.quadruped.de/projects/g1/html/operation_1.2.html
- IEEE Robots Guide의 Unitree G1 항목은 G1이 torso가 legs에 붙는 깊은 squat-like pose를 보인다고 설명한다. 접근일: 2026-06-18. https://robotsguide.com/robots/unitree-g1
- UniTracker는 Unitree G1 29-DoF에서 squat를 포함한 whole-body motion tracking을 다루며, future reference와 adaptation이 중요하다고 설명한다. 접근일: 2026-06-18. https://arxiv.org/html/2507.07356v3
- MuJoCo computation docs는 forward/inverse dynamics와 contact solver가 qfrc 기반 controller 실험의 물리 계산 근거임을 제공한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/stable/computation/index.html
- Floating-base humanoid motion tracking에서 strict contact force constraints가 필요하다는 연구는 contact force/torque를 함께 제한해야 함을 보인다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf

## 3. 결과 (Results)

| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Return | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
{chr(10).join(rows)}

Best MPC run: `{best['attempt']}` -> `{best['visible_verdict']}`.

박제:
- `verify/result.json`
- `verify/wbc-mpc-inloop-reference-tracker-summary.md`
- `verify/<attempt>/native-eval.json`

## 4. 통찰 (Insights)

- Native verdict: `{result['verdict']}`.
- Browser replay attempted: `{result['browser_replay_attempted']}`.
- Best run은 drop `{best['visible_drop']:.4f}m`, knee `{best['max_knee_delta_rad']:.3f}rad`, hip `{best['max_hip_pitch_delta_rad']:.3f}rad`, contact `{best['foot_contact_ratio']:.2f}`, slip `{best['foot_slip_distance']:.3f}m`이지만 return-to-stand는 실패했다.
- 공개 근거상 “G1이 스쿼트 자세를 취할 수 있나”의 답은 yes에 가깝다. 다만 우리 local M19 기준은 balance/contact/slip/return까지 포함한 dynamic visible squat라서, 내장 Squat Mode나 사진 evidence와 동일하지 않다.
- 이번 in-loop primitive MPC도 실패하면 다음은 primitive selector가 아니라 horizon-level full inverse-dynamics QP/MPC 또는 real reference tracker stack parity로 가야 한다.

### 가설은 통과했나?

- [{'x' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else ' '}] PASS — native exp29 visible gate를 통과했다.
- [{' ' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else 'x'}] FAIL — WBC/MPC-in-loop primitive selector만으로 native exp29 visible gate를 닫지 못했다.
"""
    (EXP_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    VERIFY.mkdir(parents=True, exist_ok=True)
    original_choose = EXP67.choose_blend
    EXP67.choose_blend = primitive_mpc_choose
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 tests an in-loop WBC/MPC primitive selector after static ID-QP plausibility and dynamic/retrain failures.",
            "perspectives": {
                "product": "answers whether the G1 squat route can progress through controller search before another retrain",
                "architecture": "wraps exp91 WBC-lite primitives with per-tick short-horizon primitive selection",
                "security": "local MuJoCo simulation only; no credentials",
                "qa": "native exp29 visible gate; browser replay only if native passes",
                "skeptic": "primitive-level MPC may still be too weak compared with full floating-base inverse-dynamics QP/MPC",
            },
            "dod": [
                "native JSON per primitive-MPC variant",
                "summary states native exp29 gate and browser replay attempt flag",
            ],
        },
        "web_sources": [
            {"url": "https://www.unitree.com/g1", "accessed": "2026-06-18"},
            {"url": "https://docs.quadruped.de/projects/g1/html/operation_1.2.html", "accessed": "2026-06-18"},
            {"url": "https://robotsguide.com/robots/unitree-g1", "accessed": "2026-06-18"},
            {"url": "https://arxiv.org/html/2507.07356v3", "accessed": "2026-06-18"},
            {"url": "https://mujoco.readthedocs.io/en/stable/computation/index.html", "accessed": "2026-06-18"},
            {"url": "https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf", "accessed": "2026-06-18"},
        ],
        "runs": [],
    }
    try:
        for variant in mpc_variants():
            run = EXP67.native_eval(variant=variant, seconds=args.seconds, out_dir=VERIFY / variant["attempt"])
            run = EXP91.annotate_visible(run)
            run["mpc_visible_score"] = visible_score(run)
            result["runs"].append(run)
    finally:
        EXP67.choose_blend = original_choose

    visible = [run for run in result["runs"] if run["visible_8cm_gate"]]
    best_mpc = min(result["runs"], key=lambda run: run["mpc_visible_score"])
    best_visible = max(result["runs"], key=lambda run: run["visible_drop"])
    result["best_mpc"] = {
        "attempt": best_mpc["attempt"],
        "mpc_visible_score": best_mpc["mpc_visible_score"],
        "visible_drop": best_mpc["visible_drop"],
        "max_knee_delta_rad": best_mpc["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_mpc["max_hip_pitch_delta_rad"],
        "foot_contact_ratio": best_mpc["foot_contact_ratio"],
        "foot_slip_distance": best_mpc["foot_slip_distance"],
        "visible_verdict": best_mpc["visible_verdict"],
        "fell_at": best_mpc["fell_at"],
    }
    result["best_visible"] = {
        "attempt": best_visible["attempt"],
        "visible_drop": best_visible["visible_drop"],
        "max_knee_delta_rad": best_visible["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_visible["max_hip_pitch_delta_rad"],
        "foot_contact_ratio": best_visible["foot_contact_ratio"],
        "foot_slip_distance": best_visible["foot_slip_distance"],
        "visible_verdict": best_visible["visible_verdict"],
        "fell_at": best_visible["fell_at"],
    }
    result["verdict"] = "PASS_VISIBLE_8CM_GATE" if visible else "FAIL_VISIBLE_8CM_GATE"
    result["browser_replay_attempted"] = bool(visible)
    write_summary(result)
    (VERIFY / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_readme(result)
    print(json.dumps({
        "verdict": result["verdict"],
        "browser_replay_attempted": result["browser_replay_attempted"],
        "best_mpc": result["best_mpc"],
        "best_visible": result["best_visible"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
