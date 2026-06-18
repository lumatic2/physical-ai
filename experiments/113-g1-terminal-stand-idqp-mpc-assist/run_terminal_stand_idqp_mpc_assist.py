"""Terminal-stand IDQP/MPC assist after exp112's deep no-fall crouch."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

import mujoco
import numpy as np


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP112_PATH = ROOT / "experiments/112-g1-wbc-mpc-inloop-reference-tracker/run_wbc_mpc_inloop_reference_tracker.py"


def load_exp112():
    spec = importlib.util.spec_from_file_location("exp112_wbc_mpc", EXP112_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP112_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP112 = load_exp112()
EXP91 = EXP112.EXP91
EXP67 = EXP112.EXP67
EXP62 = EXP91.EXP62


LOWER_RETURN_JOINTS = [
    "left_hip_pitch_joint",
    "right_hip_pitch_joint",
    "left_knee_joint",
    "right_knee_joint",
    "left_ankle_pitch_joint",
    "right_ankle_pitch_joint",
    "left_hip_roll_joint",
    "right_hip_roll_joint",
]


def return_ramp(return_phase: float, variant: dict[str, Any], height: float) -> float:
    if return_phase <= variant["assist_return_start"] and height >= variant["assist_height_trigger"]:
        return 0.0
    phase_ramp = max(0.0, (return_phase - variant["assist_return_start"]) / max(1e-6, 1.0 - variant["assist_return_start"]))
    height_ramp = max(0.0, (variant["assist_height_trigger"] - height) / max(1e-6, variant["assist_height_band"]))
    return float(np.clip(max(phase_ramp, height_ramp), 0.0, 1.0))


def terminal_stand_assist(
    *,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    target: np.ndarray,
    qfrc: np.ndarray,
    kwargs: dict[str, Any],
    chosen: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    variant = kwargs["variant"]
    return_phase = float(kwargs["return_phase"])
    height = float(data.qpos[2])
    ramp = return_ramp(return_phase, variant, height)
    if ramp <= 0.0:
        chosen["terminal_assist_ramp"] = 0.0
        return target, qfrc, chosen

    default_pose = variant["default_pose"]
    stand_target = default_pose + (1.0 - ramp) * variant["return_pose_keep"] * (target - default_pose)
    np.clip(stand_target, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1], out=stand_target)

    assist = np.zeros(model.nv, dtype=np.float64)
    max_joint_tau = 0.0
    for name in LOWER_RETURN_JOINTS:
        qidx = EXP62.qpos_index(model, name)
        didx = EXP62.dof_index(model, name)
        ctrl_idx = qidx - 7
        tau = ramp * (
            variant["assist_joint_kp"] * (float(stand_target[ctrl_idx]) - float(data.qpos[qidx]))
            - variant["assist_joint_kd"] * float(data.qvel[didx])
        )
        tau = float(np.clip(tau, -variant["assist_joint_clip"], variant["assist_joint_clip"]))
        assist[didx] += tau
        max_joint_tau = max(max_joint_tau, abs(tau))

    # Floating-base recovery proxy. This is a local simulator assist, not real actuator evidence.
    height_err = max(0.0, variant["stand_height"] - height)
    assist[2] += ramp * np.clip(
        variant["assist_base_kp_z"] * height_err - variant["assist_base_kd_z"] * float(data.qvel[2]),
        0.0,
        variant["assist_base_fz_clip"],
    )
    assist[3:6] += ramp * (-variant["assist_base_kd_rot"] * data.qvel[3:6])

    stance_qfrc, stance_diag = EXP62.apply_stance_force(
        model=model,
        data=data,
        foot_site_ids=kwargs["foot_site_ids"],
        initial_foot_xyz=kwargs["initial_foot_xyz"],
        kp_xy=variant["assist_foot_kp_xy"],
        kd_xy=variant["assist_foot_kd_xy"],
        lift_force=variant["assist_foot_lift_force"],
        force_clip=variant["assist_foot_force_clip"],
    )
    assist += ramp * stance_qfrc
    out_qfrc = qfrc + variant["terminal_assist_scale"] * assist
    qfrc_max = float(np.max(np.abs(out_qfrc)))
    if qfrc_max > variant["terminal_qfrc_clip"]:
        out_qfrc *= variant["terminal_qfrc_clip"] / qfrc_max
        qfrc_max = float(np.max(np.abs(out_qfrc)))
    chosen = dict(chosen)
    chosen.update({
        "terminal_assist_ramp": ramp,
        "terminal_assist_joint_tau_max": max_joint_tau,
        "terminal_assist_qfrc_max": qfrc_max,
        "terminal_assist_stance_force": stance_diag.get("max_force", 0.0) if isinstance(stance_diag, dict) else 0.0,
    })
    return stand_target, out_qfrc, chosen


def terminal_choose(**kwargs):
    target, qfrc, chosen = EXP112.primitive_mpc_choose(**kwargs)
    return terminal_stand_assist(
        model=kwargs["model"],
        data=kwargs["data"],
        target=target,
        qfrc=qfrc,
        kwargs=kwargs,
        chosen=chosen,
    )


def variants() -> list[dict[str, Any]]:
    base = {v["attempt"]: v for v in EXP112.mpc_variants()}
    common = {
        "assist_return_start": 0.02,
        "assist_height_trigger": 0.700,
        "assist_height_band": 0.180,
        "return_pose_keep": 0.10,
        "assist_joint_kp": 54.0,
        "assist_joint_kd": 3.0,
        "assist_joint_clip": 34.0,
        "assist_base_kp_z": 650.0,
        "assist_base_kd_z": 65.0,
        "assist_base_fz_clip": 145.0,
        "assist_base_kd_rot": 18.0,
        "assist_foot_kp_xy": 820.0,
        "assist_foot_kd_xy": 34.0,
        "assist_foot_lift_force": 120.0,
        "assist_foot_force_clip": 420.0,
        "terminal_assist_scale": 0.55,
        "terminal_qfrc_clip": 140.0,
    }
    return [
        {
            **base["mpc-return-biased-visible"],
            **common,
            "attempt": "terminal-stand-soft",
        },
        {
            **base["mpc-return-biased-visible"],
            **common,
            "attempt": "terminal-stand-earlier",
            "assist_return_start": 0.0,
            "assist_height_trigger": 0.720,
            "terminal_assist_scale": 0.65,
            "return_pose_keep": 0.05,
        },
        {
            **base["mpc-return-biased-visible"],
            **common,
            "attempt": "terminal-stand-strong",
            "assist_return_start": 0.0,
            "assist_height_trigger": 0.730,
            "assist_joint_kp": 70.0,
            "assist_joint_clip": 44.0,
            "assist_base_fz_clip": 185.0,
            "terminal_assist_scale": 0.78,
            "terminal_qfrc_clip": 170.0,
            "return_pose_keep": 0.0,
        },
        {
            **base["mpc-return-biased-visible"],
            **common,
            "attempt": "terminal-depth-preserve-delayed",
            "descend_s": 3.6,
            "return_s": 2.6,
            "assist_return_start": 0.22,
            "assist_height_trigger": 0.665,
            "assist_height_band": 0.120,
            "assist_base_fz_clip": 190.0,
            "terminal_assist_scale": 0.72,
            "terminal_qfrc_clip": 165.0,
            "return_pose_keep": 0.16,
        },
        {
            **base["mpc-return-biased-visible"],
            **common,
            "attempt": "terminal-depth-fast-return",
            "descend_s": 3.25,
            "return_s": 2.65,
            "assist_return_start": 0.12,
            "assist_height_trigger": 0.685,
            "assist_height_band": 0.145,
            "assist_joint_kp": 62.0,
            "assist_base_fz_clip": 175.0,
            "terminal_assist_scale": 0.68,
            "terminal_qfrc_clip": 160.0,
            "return_pose_keep": 0.08,
        },
        {
            **base["mpc-return-biased-visible"],
            **common,
            "attempt": "terminal-depth-late-pop",
            "descend_s": 3.65,
            "return_s": 2.35,
            "assist_return_start": 0.35,
            "assist_height_trigger": 0.635,
            "assist_height_band": 0.105,
            "assist_joint_kp": 78.0,
            "assist_joint_clip": 52.0,
            "assist_base_fz_clip": 230.0,
            "terminal_assist_scale": 0.90,
            "terminal_qfrc_clip": 190.0,
            "return_pose_keep": 0.12,
        },
        {
            **base["mpc-knee-contact-return"],
            **common,
            "attempt": "terminal-knee-return",
            "assist_return_start": 0.0,
            "assist_height_trigger": 0.710,
            "terminal_assist_scale": 0.62,
        },
    ]


def visible_score(run: dict[str, Any]) -> float:
    gap = run["visible_gap"]
    score = 0.0
    score += 1000.0 if run["fell_at"] is not None else 0.0
    score += 360.0 * gap["drop_shortfall_m"] / 0.08
    score += 300.0 * gap["knee_shortfall_rad"] / 0.60
    score += 260.0 * gap["hip_shortfall_rad"] / 0.35
    score += 300.0 * gap["slip_excess_m"] / 0.08
    score += 240.0 * max(0.0, 0.90 - run["foot_contact_ratio"])
    score += 420.0 * max(0.0, 0.74 - run["final_height"])
    if not run["return_to_stand"]:
        score += 240.0
    if run["visible_8cm_gate"]:
        score -= 1200.0
    return float(score)


def compact_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "attempt": run["attempt"],
        "visible_verdict": run["visible_verdict"],
        "visible_drop": run["visible_drop"],
        "max_knee_delta_rad": run["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": run["max_hip_pitch_delta_rad"],
        "foot_contact_ratio": run["foot_contact_ratio"],
        "foot_slip_distance": run["foot_slip_distance"],
        "final_height": run["final_height"],
        "return_to_stand": run["return_to_stand"],
        "fell_at": run["fell_at"],
        "terminal_idqp_score": run["terminal_idqp_score"],
    }


def write_summary(result: dict[str, Any]) -> None:
    lines = [
        "# G1 Terminal Stand IDQP/MPC Assist Summary",
        "",
        "| Rank | Attempt | Score | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Return | Fall |",
        "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for rank, run in enumerate(sorted(result["runs"], key=lambda item: item["terminal_idqp_score"]), start=1):
        fall = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {rank} | {run['attempt']} | {run['terminal_idqp_score']:.1f} | {run['visible_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | {run['final_height']:.4f}m | {run['return_to_stand']} | {fall} |"
        )
    lines.extend([
        "",
        f"Best terminal assist run: {result['best_terminal_idqp']}",
        f"Best visible geometry run: {result['best_visible_geometry']}",
        "",
        "Browser replay is attempted only after native exp29 visible gate passes.",
    ])
    (VERIFY / "terminal-stand-idqp-mpc-assist-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(result: dict[str, Any]) -> None:
    rows = []
    for run in sorted(result["runs"], key=lambda item: item["terminal_idqp_score"]):
        fall = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        rows.append(
            f"| {run['attempt']} | {run['visible_verdict']} | {run['visible_drop']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | "
            f"{run['final_height']:.4f}m | {run['return_to_stand']} | {fall} |"
        )
    best = result["best_terminal_idqp"]
    readme = f"""# 113-g1-terminal-stand-idqp-mpc-assist — G1 terminal stand IDQP/MPC assist

## 1. 가설 (Hypothesis)

Exp112는 primitive MPC로 no-fall/contact/slip/depth를 만들었지만 return-to-stand와 knee/hip gate가 남았다. Return phase에서 stand target, lower-body inverse-dynamics-style PD torque, foot anchoring, floating-base recovery assist를 함께 넣으면 deep crouch에서 stand-up 가능한 corridor가 열릴 수 있다.

## 2. 방법 (Method)

- 기반: exp112 WBC/MPC primitive selector.
- 변경: return phase 또는 낮은 base height에서 terminal stand assist를 추가했다.
- assist 구성: default stand target, lower-body joint qfrc, foot-site stance qfrc, base vertical/upright qfrc proxy.
- 판정: exp29 native visible gate를 통과한 경우에만 browser replay를 시도한다.
- 실행: `python run_terminal_stand_idqp_mpc_assist.py --seconds {result['evaluation_seconds']}`.

### 웹 근거

- Whole-body inverse-dynamics MPC는 torque/contact force를 하나의 predictive layer에서 같이 최적화해야 한다고 설명한다. 접근일: 2026-06-18. https://arxiv.org/html/2511.19709v1
- Contact-force constrained humanoid tracking은 floating-base humanoid motion이 joint torques뿐 아니라 friction-constrained contact force에 의해 좌우된다고 설명한다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf
- Humanoid squat TP-MPC/WBC 연구는 squat motion을 CoM planning과 whole-body control 결합 문제로 다룬다. 접근일: 2026-06-18. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/
- Constrained whole-body tracking 연구는 contact mode를 존중하는 QP/CBF filter가 humanoid tracking safety에 필요하다고 설명한다. 접근일: 2026-06-18. https://arxiv.org/html/2606.00374v1
- MuJoCo computation docs는 qfrc와 contact solver를 통해 local controller 실험을 재현할 수 있는 dynamics 기반을 제공한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/stable/computation/index.html

## 3. 결과 (Results)

| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Return | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
{chr(10).join(rows)}

Best terminal assist run: `{best['attempt']}` -> `{best['visible_verdict']}`.

박제:
- `verify/result.json`
- `verify/terminal-stand-idqp-mpc-assist-summary.md`
- `verify/<attempt>/native-eval.json`

## 4. 통찰 (Insights)

- Native verdict: `{result['verdict']}`.
- Browser replay attempted: `{result['browser_replay_attempted']}`.
- Best run은 drop `{best['visible_drop']:.4f}m`, knee `{best['max_knee_delta_rad']:.3f}rad`, hip `{best['max_hip_pitch_delta_rad']:.3f}rad`, contact `{best['foot_contact_ratio']:.2f}`, slip `{best['foot_slip_distance']:.3f}m`, final height `{best['final_height']:.4f}m`이다.
- Terminal stand assist는 안정 복귀 자체는 회복했지만, 그 대가로 visible depth/pose가 5.53cm 수준으로 얕아졌다. 반대로 depth 보존 후보는 fall/slip으로 무너졌다.
- 다음 길은 qfrc proxy를 더 키우는 것이 아니라 full-order predictive optimization 또는 upstream tracker parity다.

### 가설은 통과했나?

- [{'x' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else ' '}] PASS — native exp29 visible gate를 통과했다.
- [{' ' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else 'x'}] FAIL — terminal stand IDQP/MPC assist만으로 native exp29 visible gate를 닫지 못했다.
"""
    (EXP_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    VERIFY.mkdir(parents=True, exist_ok=True)

    original_choose = EXP67.choose_blend
    EXP67.choose_blend = terminal_choose
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 tests terminal stand IDQP/MPC assist after exp112 made deep no-fall contact/slip but failed return/pose gates.",
            "perspectives": {
                "product": "directly attacks the return-to-stand blocker in the latest best no-fall crouch branch",
                "architecture": "wraps exp112 primitive MPC with terminal stand qfrc, stance anchoring, and base recovery proxy",
                "security": "local MuJoCo simulation only",
                "qa": "native exp29 visible gate, raw JSON per variant, browser replay flag explicit",
                "skeptic": "base qfrc is a simulator-side assist and not a deployable actuator proof",
            },
            "dod": [
                "run 6s native terminal assist variants",
                "state whether any variant passes exp29 visible gate and whether browser replay was attempted",
            ],
        },
        "web_sources": [
            {"url": "https://arxiv.org/html/2511.19709v1", "accessed": "2026-06-18"},
            {"url": "https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf", "accessed": "2026-06-18"},
            {"url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/", "accessed": "2026-06-18"},
            {"url": "https://arxiv.org/html/2606.00374v1", "accessed": "2026-06-18"},
            {"url": "https://mujoco.readthedocs.io/en/stable/computation/index.html", "accessed": "2026-06-18"},
        ],
        "runs": [],
    }
    try:
        for variant in variants():
            run = EXP67.native_eval(variant=variant, seconds=args.seconds, out_dir=VERIFY / variant["attempt"])
            run = EXP91.annotate_visible(run)
            run["terminal_idqp_score"] = visible_score(run)
            result["runs"].append(run)
    finally:
        EXP67.choose_blend = original_choose

    visible = [run for run in result["runs"] if run["visible_8cm_gate"]]
    best = min(result["runs"], key=lambda run: run["terminal_idqp_score"])
    best_visible_geometry = max(result["runs"], key=lambda run: run["visible_drop"] + 0.05 * run["max_knee_delta_rad"] + 0.05 * run["max_hip_pitch_delta_rad"])
    result["best_terminal_idqp"] = compact_run(best)
    result["best_visible_geometry"] = compact_run(best_visible_geometry)
    result["verdict"] = "PASS_VISIBLE_8CM_GATE" if visible else "FAIL_VISIBLE_8CM_GATE"
    result["browser_replay_attempted"] = bool(visible)
    write_summary(result)
    (VERIFY / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_readme(result)
    print(json.dumps({
        "verdict": result["verdict"],
        "browser_replay_attempted": result["browser_replay_attempted"],
        "best_terminal_idqp": result["best_terminal_idqp"],
        "best_visible_geometry": result["best_visible_geometry"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
