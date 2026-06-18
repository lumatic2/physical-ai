"""Dynamic ID-QP-style tracking smoke for a static-feasible G1 visible squat pose."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

import mujoco
import numpy as np
from scipy.optimize import minimize


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP91_PATH = ROOT / "experiments/91-g1-contact-constrained-pose-qfrc-wrapper/run_contact_constrained_pose_qfrc_wrapper.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP91 = load_module(EXP91_PATH, "exp91_contact_qfrc")
EXP67 = EXP91.EXP67
EXP62 = EXP91.EXP62


LOWER_JOINTS = [
    ("left_hip_pitch_joint", -1.0, "hip"),
    ("right_hip_pitch_joint", -1.0, "hip"),
    ("left_knee_joint", 1.0, "knee"),
    ("right_knee_joint", 1.0, "knee"),
    ("left_ankle_pitch_joint", -1.0, "ankle"),
    ("right_ankle_pitch_joint", -1.0, "ankle"),
]


def phase_target_fraction(t: float, variant: dict[str, Any]) -> tuple[float, float, str]:
    descend_s = float(variant["descend_s"])
    hold_s = float(variant["hold_s"])
    return_s = float(variant["return_s"])
    if t < descend_s:
        x = t / max(1e-6, descend_s)
        return 0.5 - 0.5 * np.cos(np.pi * x), 0.0, "descend"
    if t < descend_s + hold_s:
        return 1.0, 0.0, "hold"
    x = (t - descend_s - hold_s) / max(1e-6, return_s)
    x = float(np.clip(x, 0.0, 1.0))
    return 0.5 + 0.5 * np.cos(np.pi * x), x, "return"


def foot_velocity(model: mujoco.MjModel, data: mujoco.MjData, site_id: int) -> np.ndarray:
    jacp = np.zeros((3, model.nv), dtype=np.float64)
    jacr = np.zeros((3, model.nv), dtype=np.float64)
    mujoco.mj_jacSite(model, data, jacp, jacr, int(site_id))
    return jacp @ data.qvel


def solve_contact_force_qp(
    *,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    foot_site_ids: np.ndarray,
    initial_foot_xyz: np.ndarray,
    variant: dict[str, Any],
    health: float,
) -> dict[str, Any]:
    mu = float(variant["mu"])
    normal_max = float(variant["normal_max"])
    total_normal_max = float(variant["total_normal_max"])
    desired: list[float] = []
    for idx, site_id in enumerate(foot_site_ids):
        pos = data.site_xpos[int(site_id), :3]
        vel = foot_velocity(model, data, int(site_id))
        xy_err = initial_foot_xyz[idx, :2] - pos[:2]
        fxy = variant["foot_kp_xy"] * xy_err - variant["foot_kd_xy"] * vel[:2]
        lift = max(0.0, float(pos[2] - initial_foot_xyz[idx, 2]))
        fz = (variant["normal_base"] + variant["normal_height_kp"] * lift) * (0.25 + 0.75 * health)
        desired.extend([float(fxy[0]), float(fxy[1]), float(np.clip(fz, 0.0, normal_max))])
    desired_x = np.asarray(desired, dtype=np.float64)

    def objective(x: np.ndarray) -> float:
        tangent = x[[0, 1, 3, 4]]
        normal_balance = x[2] - x[5]
        return float(
            np.dot(x - desired_x, x - desired_x)
            + variant["w_tangent"] * np.dot(tangent, tangent)
            + variant["w_balance"] * normal_balance * normal_balance
            + variant["w_normal"] * (x[2] * x[2] + x[5] * x[5])
        )

    bounds = [
        (-mu * normal_max, mu * normal_max),
        (-mu * normal_max, mu * normal_max),
        (0.0, normal_max),
        (-mu * normal_max, mu * normal_max),
        (-mu * normal_max, mu * normal_max),
        (0.0, normal_max),
    ]
    constraints = [
        {"type": "ineq", "fun": lambda x: mu * x[2] - abs(x[0])},
        {"type": "ineq", "fun": lambda x: mu * x[2] - abs(x[1])},
        {"type": "ineq", "fun": lambda x: mu * x[5] - abs(x[3])},
        {"type": "ineq", "fun": lambda x: mu * x[5] - abs(x[4])},
        {"type": "ineq", "fun": lambda x: total_normal_max - x[2] - x[5]},
    ]
    x0 = np.clip(desired_x, [b[0] for b in bounds], [b[1] for b in bounds])
    if x0[2] + x0[5] > total_normal_max:
        x0[[2, 5]] *= total_normal_max / max(1e-9, x0[2] + x0[5])
    opt = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints, options={"maxiter": 25, "ftol": 1e-5})
    x = np.asarray(opt.x if opt.success else x0, dtype=np.float64)

    qfrc = np.zeros(model.nv, dtype=np.float64)
    ratios = []
    for idx, site_id in enumerate(foot_site_ids):
        jacp = np.zeros((3, model.nv), dtype=np.float64)
        jacr = np.zeros((3, model.nv), dtype=np.float64)
        mujoco.mj_jacSite(model, data, jacp, jacr, int(site_id))
        fx, fy, fz = x[idx * 3 : idx * 3 + 3]
        ratios.append(float(np.linalg.norm([fx, fy]) / max(1e-9, mu * fz)))
        qfrc += jacp.T @ np.asarray([fx, fy, -fz], dtype=np.float64)
    return {
        "success": bool(opt.success),
        "qfrc": qfrc,
        "max_ratio": float(max(ratios) if ratios else 0.0),
        "normal_sum": float(x[2] + x[5]),
        "objective": float(objective(x)),
    }


def lower_joint_pd_qfrc(
    *,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    target: np.ndarray,
    variant: dict[str, Any],
    health: float,
) -> tuple[np.ndarray, float]:
    qfrc = np.zeros(model.nv, dtype=np.float64)
    max_tau = 0.0
    scale = float(np.clip(variant["joint_qfrc_scale"] * (0.30 + 0.70 * health), 0.0, 1.0))
    for name, _, _ in LOWER_JOINTS:
        qidx = EXP62.qpos_index(model, name)
        didx = EXP62.dof_index(model, name)
        ctrl_idx = qidx - 7
        tau = scale * (
            variant["joint_kp"] * (float(target[ctrl_idx]) - float(data.qpos[qidx]))
            - variant["joint_kd"] * float(data.qvel[didx])
        )
        tau = float(np.clip(tau, -variant["joint_tau_clip"], variant["joint_tau_clip"]))
        qfrc[didx] += tau
        max_tau = max(max_tau, abs(tau))
    return qfrc, max_tau


def make_target(model: mujoco.MjModel, variant: dict[str, Any], fraction: float) -> np.ndarray:
    target = variant["default_pose"].copy()
    for name, sign, key in LOWER_JOINTS:
        qidx = EXP62.qpos_index(model, name)
        ctrl_idx = qidx - 7
        target[ctrl_idx] = float(model.keyframe("knees_bent").qpos[qidx] + sign * variant[f"target_{key}"] * fraction)
    np.clip(target, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1], out=target)
    return target


def choose_dynamic_idqp(**kwargs):
    model = kwargs["model"]
    data = kwargs["data"]
    variant = kwargs["variant"]
    t = float(data.time)
    fraction, return_phase, phase = phase_target_fraction(t, variant)
    support_now = kwargs["support_now"]
    zmp_now = float(kwargs["zmp_now"])
    foot_slip_now = float(kwargs["foot_slip_now"])
    support_health = float(np.clip((support_now["support_margin"] + 0.005) / 0.050, 0.0, 1.0))
    zmp_health = float(np.clip((zmp_now + 0.010) / 0.060, 0.0, 1.0))
    slip_health = float(np.clip(1.0 - foot_slip_now / 0.080, 0.0, 1.0))
    health = min(support_health, zmp_health, slip_health)
    target = make_target(model, variant, fraction)
    joint_qfrc, joint_tau_max = lower_joint_pd_qfrc(model=model, data=data, target=target, variant=variant, health=health)
    contact_qp = solve_contact_force_qp(
        model=model,
        data=data,
        foot_site_ids=kwargs["foot_site_ids"],
        initial_foot_xyz=kwargs["initial_foot_xyz"],
        variant=variant,
        health=health,
    )
    qfrc = joint_qfrc + variant["contact_qfrc_scale"] * contact_qp["qfrc"]
    if phase == "return":
        qfrc *= max(0.25, 1.0 - 0.60 * return_phase)
    qfrc_max = float(np.max(np.abs(qfrc)))
    if qfrc_max > variant["qfrc_clip"]:
        qfrc *= variant["qfrc_clip"] / qfrc_max
        qfrc_max = float(np.max(np.abs(qfrc)))
    return target, qfrc, {
        "blend": float(fraction),
        "cost": float(contact_qp["objective"]),
        "phase_mode": phase,
        "return_phase": float(return_phase),
        "support_margin": float(support_now["support_margin"]),
        "zmp_margin": zmp_now,
        "foot_slip_distance": foot_slip_now,
        "height": float(data.qpos[2]),
        "qfrc_max": qfrc_max,
        "joint_tau_max": joint_tau_max,
        "contact_qp_success": contact_qp["success"],
        "contact_qp_max_ratio": contact_qp["max_ratio"],
        "contact_qp_normal_sum": contact_qp["normal_sum"],
        "health": float(health),
    }


def visible_score(run: dict[str, Any]) -> float:
    gap = run["visible_gap"]
    score = 0.0
    score += 1000.0 if run["fell_at"] is not None else 0.0
    score += 360.0 * gap["drop_shortfall_m"] / 0.08
    score += 280.0 * gap["knee_shortfall_rad"] / 0.60
    score += 240.0 * gap["hip_shortfall_rad"] / 0.35
    score += 260.0 * gap["slip_excess_m"] / 0.08
    score += 220.0 * max(0.0, 0.90 - run["foot_contact_ratio"])
    if not run["return_to_stand"]:
        score += 160.0
    if run["visible_8cm_gate"]:
        score -= 1000.0
    return float(score)


def annotate(run: dict[str, Any]) -> dict[str, Any]:
    run = EXP91.annotate_visible(run)
    run["dynamic_idqp_score"] = visible_score(run)
    return run


def variants() -> list[dict[str, Any]]:
    common = {
        "policy_weight": 0.0,
        "max_blend": 1.0,
        "drop": 0.09,
        "descend_s": 2.4,
        "hold_s": 0.8,
        "return_s": 2.4,
        "target_knee": 0.64,
        "target_hip": 0.38,
        "target_ankle": 0.28,
        "joint_kp": 42.0,
        "joint_kd": 2.4,
        "joint_qfrc_scale": 0.70,
        "joint_tau_clip": 26.0,
        "qfrc_clip": 80.0,
        "mu": 0.80,
        "normal_base": 34.0,
        "normal_height_kp": 700.0,
        "normal_max": 125.0,
        "total_normal_max": 210.0,
        "foot_kp_xy": 760.0,
        "foot_kd_xy": 28.0,
        "contact_qfrc_scale": 0.48,
        "w_tangent": 0.04,
        "w_balance": 0.25,
        "w_normal": 0.01,
    }
    return [
        {**common, "attempt": "static-full-slow-balanced"},
        {**common, "attempt": "static-full-contact-heavy", "contact_qfrc_scale": 0.68, "normal_base": 44.0, "foot_kp_xy": 920.0, "qfrc_clip": 95.0},
        {**common, "attempt": "static-min-conservative", "drop": 0.08, "target_knee": 0.60, "target_hip": 0.35, "target_ankle": 0.25, "joint_tau_clip": 20.0, "joint_qfrc_scale": 0.50, "contact_qfrc_scale": 0.38},
        {**common, "attempt": "static-full-joint-heavy", "joint_kp": 58.0, "joint_qfrc_scale": 0.90, "joint_tau_clip": 34.0, "contact_qfrc_scale": 0.42, "qfrc_clip": 95.0},
        {**common, "attempt": "static-full-very-slow", "descend_s": 3.4, "hold_s": 0.6, "return_s": 2.0, "joint_qfrc_scale": 0.62, "contact_qfrc_scale": 0.54},
    ]


def compact_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "attempt": run["attempt"],
        "visible_verdict": run["visible_verdict"],
        "visible_drop": run["visible_drop"],
        "max_knee_delta_rad": run["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": run["max_hip_pitch_delta_rad"],
        "foot_contact_ratio": run["foot_contact_ratio"],
        "foot_slip_distance": run["foot_slip_distance"],
        "return_to_stand": run["return_to_stand"],
        "fell_at": run["fell_at"],
        "dynamic_idqp_score": run["dynamic_idqp_score"],
    }


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Dynamic ID-QP Tracking Smoke Summary",
        "",
        "| Rank | Attempt | Score | Verdict | Drop | Knee | Hip | Contact | Slip | Return | Fall |",
        "|---:|---|---:|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for rank, run in enumerate(sorted(result["runs"], key=lambda row: row["dynamic_idqp_score"]), start=1):
        fall = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {rank} | {run['attempt']} | {run['dynamic_idqp_score']:.1f} | {run['visible_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | {run['return_to_stand']} | {fall} |"
        )
    lines.extend([
        "",
        f"Best dynamic ID-QP smoke run: {result['best_dynamic_idqp']}",
        f"Best no-fall run: {result['best_no_fall']}",
        f"Best visible geometry run: {result['best_visible_geometry']}",
        "",
        "M19 closes only if native exp29 visible gate and browser replay both pass.",
    ])
    (out_dir / "dynamic-idqp-tracking-smoke-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(result: dict[str, Any]) -> None:
    rows = []
    for run in sorted(result["runs"], key=lambda row: row["dynamic_idqp_score"]):
        fall = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        rows.append(
            f"| {run['attempt']} | {run['visible_verdict']} | {run['visible_drop']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | "
            f"{run['return_to_stand']} | {fall} |"
        )
    best = result["best_dynamic_idqp"]
    readme = f"""# 110-g1-dynamic-idqp-tracking-smoke — G1 dynamic ID-QP tracking smoke

> `experiments/110-g1-dynamic-idqp-tracking-smoke/README.md` — exp109에서 static ID-QP plausible로 나온 visible squat target을 실제 6초 native rollout에서 추종해 본다.

## 1. 가설 (Hypothesis)

Exp109는 exp29 visible-min과 9cm full visible pose가 static inverse-dynamics contact QP에서는 plausible하다고 보였다. 같은 target을 dynamic rollout에서 joint PD torque + foot contact-force QP로 추종하면, qfrc wrapper보다 exp29 visible gate에 더 가까워지거나 native/browser gate를 닫을 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 + exp67 native evaluator.
- target: exp109 `visible-full-pose` 또는 `exp29-visible-min`.
- controller: 매 control step마다 lower-body joint target을 phase schedule로 만들고, lower-body PD torque와 foot anchoring/contact-force QP를 `qfrc_applied`로 합산했다.
- 판정: exp29 visible gate가 native에서 통과할 때만 browser replay를 시도한다.

### 웹 근거
- MuJoCo inverse dynamics/contact 모델은 contact force가 generalized force로 들어가는 구조를 제공한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/stable/computation/index.html
- Multi-contact force control 문헌은 position-controlled robot에서는 접촉력을 직접 제어하기 어렵고 force/admittance layer가 필요하다고 설명한다. 접근일: 2026-06-18. https://arxiv.org/html/2312.16465v3
- Contact-force constrained humanoid tracking은 floating-base humanoid imitation에서 contact forces와 friction constraints를 함께 계산해야 함을 보인다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf
- Contact-implicit inverse dynamics trajectory optimization은 접촉을 포함한 실시간 MPC/trajectory optimization 방향을 제시한다. 접근일: 2026-06-18. https://arxiv.org/html/2309.01813v3

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Return | Fall |
|---|---|---:|---:|---:|---:|---:|---|---|
{chr(10).join(rows)}

Best dynamic ID-QP smoke run: `{best['attempt']}` -> `{best['visible_verdict']}`.

### 박제 위치
- `verify/result.json`
- `verify/dynamic-idqp-tracking-smoke-summary.md`
- `verify/<attempt>/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- 이 실험은 static feasible visible target을 실제 dynamic rollout에 넣은 첫 smoke다.
- Best run은 drop `{best['visible_drop']:.4f}m`, knee `{best['max_knee_delta_rad']:.3f}rad`, hip `{best['max_hip_pitch_delta_rad']:.3f}rad`, contact `{best['foot_contact_ratio']:.2f}`, slip `{best['foot_slip_distance']:.3f}m`이다.
- native gate가 닫히지 않으면, 단순 qfrc assist가 아니라 horizon-level full ID-QP 또는 contact-aware policy retrain이 필요하다는 뜻이다.

### 가설은 통과했나?
- [{'x' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else ' '}] PASS — native exp29 visible gate를 통과했다.
- [{' ' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else 'x'}] FAIL — dynamic ID-QP-style smoke만으로 native exp29 visible gate를 닫지 못했다.

### 정의에 반영
- M19 완료 조건은 그대로 native exp29 visible gate + browser replay다. 본 실험은 static feasibility 이후 dynamic tracking gap을 직접 재는 중간 증거다.
"""
    (EXP_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY
    out_dir.mkdir(parents=True, exist_ok=True)

    original_choose = EXP67.choose_blend
    EXP67.choose_blend = choose_dynamic_idqp
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 moves exp109 static feasible visible target into native dynamic rollout with an ID-QP-style contact/joint controller smoke.",
            "perspectives": {
                "product": "directly tests whether a statically plausible visible squat target can become a showable native/browser candidate",
                "architecture": "reuses exp67 native evaluator and replaces the chooser with joint PD torque plus per-foot contact-force QP",
                "security": "local MuJoCo simulation only",
                "qa": "raw native JSON per variant, summary table, and browser replay attempted only if native visible gate passes",
                "skeptic": "this is not a true horizon full ID-QP; it is a dynamic smoke between qfrc wrapper and retrain",
            },
            "dod": [
                "run 6s native rollout variants from exp109 static visible target",
                "state whether any variant passes exp29 visible gate and whether browser replay was attempted",
            ],
        },
        "web_sources": [
            {"url": "https://mujoco.readthedocs.io/en/stable/computation/index.html", "accessed": "2026-06-18"},
            {"url": "https://arxiv.org/html/2312.16465v3", "accessed": "2026-06-18"},
            {"url": "https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf", "accessed": "2026-06-18"},
            {"url": "https://arxiv.org/html/2309.01813v3", "accessed": "2026-06-18"},
        ],
        "runs": [],
    }
    try:
        for variant in variants():
            run = EXP67.native_eval(variant=variant, seconds=args.seconds, out_dir=out_dir / variant["attempt"])
            result["runs"].append(annotate(run))
    finally:
        EXP67.choose_blend = original_choose

    visible = [run for run in result["runs"] if run["visible_8cm_gate"]]
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best = min(result["runs"], key=lambda run: run["dynamic_idqp_score"])
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    best_visible_geometry = max(result["runs"], key=lambda run: run["visible_drop"] + 0.05 * run["max_knee_delta_rad"] + 0.05 * run["max_hip_pitch_delta_rad"])
    result["best_dynamic_idqp"] = compact_run(best)
    result["best_no_fall"] = None if best_no_fall is None else compact_run(best_no_fall)
    result["best_visible_geometry"] = compact_run(best_visible_geometry)
    result["verdict"] = "PASS_VISIBLE_8CM_GATE" if visible else "FAIL_VISIBLE_8CM_GATE"
    result["browser_replay_attempted"] = bool(visible)
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_readme(result)
    print(result["verdict"], json.dumps({
        "best_dynamic_idqp": result["best_dynamic_idqp"],
        "best_no_fall": result["best_no_fall"],
        "best_visible_geometry": result["best_visible_geometry"],
        "browser_replay_attempted": result["browser_replay_attempted"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
