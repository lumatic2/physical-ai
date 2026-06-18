"""Full-order ID-QP/MPC formulation smoke for the G1 visible squat gate."""

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
EXP110_PATH = ROOT / "experiments/110-g1-dynamic-idqp-tracking-smoke/run_dynamic_idqp_tracking_smoke.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP110 = load_module(EXP110_PATH, "exp110_dynamic_idqp")
EXP91 = EXP110.EXP91
EXP67 = EXP110.EXP67
EXP62 = EXP110.EXP62
EXP37 = EXP91.EXP37


def pose_delta(model: mujoco.MjModel, data: mujoco.MjData) -> dict[str, float]:
    start = model.keyframe("knees_bent").qpos
    left_knee = EXP62.qpos_index(model, "left_knee_joint")
    right_knee = EXP62.qpos_index(model, "right_knee_joint")
    left_hip = EXP62.qpos_index(model, "left_hip_pitch_joint")
    right_hip = EXP62.qpos_index(model, "right_hip_pitch_joint")
    return {
        "knee": max(abs(float(data.qpos[left_knee] - start[left_knee])), abs(float(data.qpos[right_knee] - start[right_knee]))),
        "hip": max(abs(float(data.qpos[left_hip] - start[left_hip])), abs(float(data.qpos[right_hip] - start[right_hip]))),
    }


def full_order_terms(
    *,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    target: np.ndarray,
    qfrc: np.ndarray,
    contact_qfrc: np.ndarray,
    variant: dict[str, Any],
) -> dict[str, float]:
    qacc_des = np.zeros(model.nv, dtype=np.float64)
    for name, _, _ in EXP110.LOWER_JOINTS:
        qidx = EXP62.qpos_index(model, name)
        didx = EXP62.dof_index(model, name)
        ctrl_idx = qidx - 7
        qacc_des[didx] = np.clip(
            variant["id_acc_kp"] * (float(target[ctrl_idx]) - float(data.qpos[qidx]))
            - variant["id_acc_kd"] * float(data.qvel[didx]),
            -variant["id_acc_clip"],
            variant["id_acc_clip"],
        )
    mass_matrix = np.zeros((model.nv, model.nv), dtype=np.float64)
    mujoco.mj_fullM(model, mass_matrix, data.qM)
    dyn_required = mass_matrix @ qacc_des + data.qfrc_bias.copy()
    base_residual = dyn_required[:6] - contact_qfrc[:6]
    act_residual = dyn_required[6:] - qfrc[6:]
    return {
        "base_residual_l2": float(np.linalg.norm(base_residual)),
        "base_residual_linf": float(np.max(np.abs(base_residual))),
        "act_residual_l2": float(np.linalg.norm(act_residual)),
        "act_residual_linf": float(np.max(np.abs(act_residual))),
        "desired_qacc_linf": float(np.max(np.abs(qacc_des))),
    }


def horizon_score(
    *,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    target: np.ndarray,
    qfrc: np.ndarray,
    kwargs: dict[str, Any],
    variant: dict[str, Any],
    fraction: float,
    id_terms: dict[str, float],
) -> dict[str, Any]:
    cand = EXP67.clone_data(model, data)
    cand.ctrl[:] = target
    cand.qfrc_applied[:] = qfrc
    min_support = float("inf")
    min_zmp = float("inf")
    max_slip = 0.0
    contact_loss = 0
    prev_com_xy = kwargs["prev_com_xy"].copy()
    prev_com_vel = kwargs["prev_com_vel"].copy()
    min_height = float(cand.qpos[2])
    max_knee = 0.0
    max_hip = 0.0
    for _ in range(int(variant["horizon_steps"])):
        for _ in range(kwargs["n_substeps"]):
            mujoco.mj_step(model, cand)
        support = EXP37.support_metrics(model, cand, kwargs["foot_geom_ids"])
        com_xy, com_vel, zmp = EXP67.zmp_margin(
            model=model,
            data=cand,
            support=support,
            prev_com_xy=prev_com_xy,
            prev_com_vel=prev_com_vel,
            ctrl_dt=kwargs["ctrl_dt"],
        )
        foot_slip = float(np.max(np.linalg.norm(
            cand.site_xpos[kwargs["foot_site_ids"], :2] - kwargs["initial_foot_xyz"][:, :2],
            axis=1,
        )))
        contacts = [
            float(cand.sensordata[model.sensor_adr[sensor_id]]) > 0.0
            for sensor_id in kwargs["foot_contact_sensor_ids"]
        ]
        pose = pose_delta(model, cand)
        min_support = min(min_support, float(support["support_margin"]))
        min_zmp = min(min_zmp, float(zmp))
        max_slip = max(max_slip, foot_slip)
        contact_loss += 0 if all(contacts) else 1
        min_height = min(min_height, float(cand.qpos[2]))
        max_knee = max(max_knee, pose["knee"])
        max_hip = max(max_hip, pose["hip"])
        prev_com_xy = com_xy.copy()
        prev_com_vel = com_vel.copy()
    cand.qfrc_applied[:] = 0.0
    target_drop = float(variant["drop"]) * max(0.0, fraction)
    achieved_drop = max(0.0, float(kwargs["start_height"]) - min_height)
    knee_target = float(variant["target_knee"]) * max(0.0, fraction)
    hip_target = float(variant["target_hip"]) * max(0.0, fraction)
    score = (
        variant["w_drop"] * max(0.0, target_drop - achieved_drop) ** 2
        + variant["w_knee"] * max(0.0, knee_target - max_knee) ** 2
        + variant["w_hip"] * max(0.0, hip_target - max_hip) ** 2
        + variant["w_support"] * max(0.0, variant["support_floor"] - min_support) ** 2
        + variant["w_zmp"] * max(0.0, variant["zmp_floor"] - min_zmp) ** 2
        + variant["w_slip"] * max(0.0, max_slip - variant["slip_floor"]) ** 2
        + variant["w_contact"] * contact_loss
        + variant["w_qfrc"] * max(0.0, float(np.max(np.abs(qfrc))) - variant["qfrc_soft_cap"]) ** 2
        + variant["w_base_residual"] * id_terms["base_residual_linf"] ** 2
        + variant["w_act_residual"] * id_terms["act_residual_linf"] ** 2
    )
    return {
        "score": float(score),
        "horizon_min_support": min_support,
        "horizon_min_zmp": min_zmp,
        "horizon_max_slip": max_slip,
        "horizon_contact_loss_count": contact_loss,
        "horizon_drop": achieved_drop,
        "horizon_knee_delta": max_knee,
        "horizon_hip_delta": max_hip,
        "horizon_min_height": min_height,
    }


def choose_full_order_idqp_mpc(**kwargs):
    model = kwargs["model"]
    data = kwargs["data"]
    variant = kwargs["variant"]
    phase_fraction, return_phase, phase = EXP110.phase_target_fraction(float(data.time), variant)
    support_now = kwargs["support_now"]
    zmp_now = float(kwargs["zmp_now"])
    foot_slip_now = float(kwargs["foot_slip_now"])
    support_health = float(np.clip((support_now["support_margin"] + 0.005) / 0.050, 0.0, 1.0))
    zmp_health = float(np.clip((zmp_now + 0.010) / 0.060, 0.0, 1.0))
    slip_health = float(np.clip(1.0 - foot_slip_now / 0.080, 0.0, 1.0))
    health = min(support_health, zmp_health, slip_health)
    if phase == "return":
        raw = np.array([
            0.0,
            max(0.0, kwargs["prev_blend"] - variant["fast_release"]),
            max(0.0, kwargs["prev_blend"] - variant["slow_release"]),
            max(0.0, phase_fraction - variant["return_bias"]),
            phase_fraction,
        ])
    else:
        raw = phase_fraction + np.asarray(variant["fraction_offsets"], dtype=np.float64)
        raw = np.append(raw, min(phase_fraction, kwargs["prev_blend"] + variant["descend_rate"]))
    fractions = np.unique(np.round(np.clip(raw, 0.0, 1.0), 5))
    best: dict[str, Any] | None = None
    for fraction in fractions:
        target = EXP110.make_target(model, variant, float(fraction))
        joint_qfrc, joint_tau_max = EXP110.lower_joint_pd_qfrc(
            model=model,
            data=data,
            target=target,
            variant=variant,
            health=health,
        )
        contact_qp = EXP110.solve_contact_force_qp(
            model=model,
            data=data,
            foot_site_ids=kwargs["foot_site_ids"],
            initial_foot_xyz=kwargs["initial_foot_xyz"],
            variant=variant,
            health=health,
        )
        contact_qfrc = variant["contact_qfrc_scale"] * contact_qp["qfrc"]
        qfrc = joint_qfrc + contact_qfrc
        if phase == "return":
            qfrc *= max(variant["return_qfrc_floor"], 1.0 - variant["return_qfrc_decay"] * return_phase)
        qfrc_max = float(np.max(np.abs(qfrc)))
        if qfrc_max > variant["qfrc_clip"]:
            qfrc *= variant["qfrc_clip"] / qfrc_max
            qfrc_max = float(np.max(np.abs(qfrc)))
        id_terms = full_order_terms(
            model=model,
            data=data,
            target=target,
            qfrc=qfrc,
            contact_qfrc=contact_qfrc,
            variant=variant,
        )
        horizon = horizon_score(
            model=model,
            data=data,
            target=target,
            qfrc=qfrc,
            kwargs=kwargs,
            variant=variant,
            fraction=float(fraction),
            id_terms=id_terms,
        )
        row = {
            "target": target,
            "qfrc": qfrc,
            "blend": float(fraction),
            "cost": horizon["score"],
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
            **id_terms,
            **horizon,
        }
        if best is None or row["cost"] < best["cost"]:
            best = row
    assert best is not None
    chosen = {k: v for k, v in best.items() if k not in {"target", "qfrc"}}
    return best["target"], best["qfrc"], chosen


def visible_score(run: dict[str, Any]) -> float:
    gap = run["visible_gap"]
    score = 0.0
    score += 1000.0 if run["fell_at"] is not None else 0.0
    score += 360.0 * gap["drop_shortfall_m"] / 0.08
    score += 300.0 * gap["knee_shortfall_rad"] / 0.60
    score += 260.0 * gap["hip_shortfall_rad"] / 0.35
    score += 260.0 * gap["slip_excess_m"] / 0.08
    score += 220.0 * max(0.0, 0.90 - run["foot_contact_ratio"])
    score += 220.0 * max(0.0, 0.74 - run["final_height"])
    if not run["return_to_stand"]:
        score += 160.0
    if run["visible_8cm_gate"]:
        score -= 1000.0
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
        "return_to_stand": run["return_to_stand"],
        "fell_at": run["fell_at"],
        "full_order_mpc_score": run["full_order_mpc_score"],
    }


def variants() -> list[dict[str, Any]]:
    common = {
        "policy_weight": 0.0,
        "max_blend": 1.0,
        "drop": 0.09,
        "descend_s": 2.8,
        "hold_s": 0.6,
        "return_s": 2.6,
        "target_knee": 0.64,
        "target_hip": 0.38,
        "target_ankle": 0.28,
        "joint_kp": 38.0,
        "joint_kd": 2.4,
        "joint_qfrc_scale": 0.55,
        "joint_tau_clip": 24.0,
        "qfrc_clip": 78.0,
        "mu": 0.80,
        "normal_base": 36.0,
        "normal_height_kp": 680.0,
        "normal_max": 125.0,
        "total_normal_max": 210.0,
        "foot_kp_xy": 850.0,
        "foot_kd_xy": 28.0,
        "contact_qfrc_scale": 0.54,
        "w_tangent": 0.04,
        "w_balance": 0.25,
        "w_normal": 0.01,
        "id_acc_kp": 36.0,
        "id_acc_kd": 2.6,
        "id_acc_clip": 24.0,
        "fraction_offsets": [-0.24, -0.12, 0.0, 0.08],
        "descend_rate": 0.045,
        "slow_release": 0.035,
        "fast_release": 0.105,
        "return_bias": 0.08,
        "return_qfrc_floor": 0.25,
        "return_qfrc_decay": 0.65,
        "horizon_steps": 6,
        "support_floor": 0.004,
        "zmp_floor": -0.018,
        "slip_floor": 0.060,
        "qfrc_soft_cap": 54.0,
        "w_drop": 1700.0,
        "w_knee": 620.0,
        "w_hip": 520.0,
        "w_support": 14500.0,
        "w_zmp": 9000.0,
        "w_slip": 22000.0,
        "w_contact": 1150.0,
        "w_qfrc": 0.10,
        "w_base_residual": 0.015,
        "w_act_residual": 0.0015,
    }
    return [
        {**common, "attempt": "full-order-balanced-visible"},
        {
            **common,
            "attempt": "full-order-safety-first",
            "fraction_offsets": [-0.32, -0.18, -0.08, 0.0],
            "contact_qfrc_scale": 0.62,
            "w_support": 22000.0,
            "w_slip": 34000.0,
            "w_contact": 1550.0,
            "qfrc_clip": 70.0,
            "horizon_steps": 8,
        },
        {
            **common,
            "attempt": "full-order-pose-push",
            "target_knee": 0.68,
            "target_hip": 0.40,
            "joint_kp": 46.0,
            "joint_qfrc_scale": 0.68,
            "joint_tau_clip": 30.0,
            "w_knee": 900.0,
            "w_hip": 760.0,
            "qfrc_clip": 92.0,
        },
    ]


def write_summary(result: dict[str, Any]) -> None:
    lines = [
        "# G1 Full-Order ID-QP/MPC Smoke Summary",
        "",
        "| Rank | Attempt | Score | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fall |",
        "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, run in enumerate(sorted(result["runs"], key=lambda item: item["full_order_mpc_score"]), start=1):
        fall = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {rank} | {run['attempt']} | {run['full_order_mpc_score']:.1f} | {run['visible_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | {run['final_height']:.4f}m | {fall} |"
        )
    lines.extend([
        "",
        f"Best full-order MPC smoke run: {result['best_full_order_mpc']}",
        f"Best no-fall run: {result['best_no_fall']}",
        "",
        "Browser replay is attempted only after native exp29 visible gate passes.",
    ])
    (VERIFY / "full-order-idqp-mpc-smoke-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(result: dict[str, Any]) -> None:
    rows = []
    for run in sorted(result["runs"], key=lambda item: item["full_order_mpc_score"]):
        fall = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        rows.append(
            f"| {run['attempt']} | {run['visible_verdict']} | {run['visible_drop']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | "
            f"{run['final_height']:.4f}m | {run['return_to_stand']} | {fall} |"
        )
    best = result["best_full_order_mpc"]
    readme = f"""# 117-g1-full-order-idqp-mpc-smoke — G1 full-order ID-QP/MPC formulation smoke

## 1. 가설 (Hypothesis)

Exp109는 exp29 visible target이 static inverse-dynamics contact QP에서는 plausible하다고 보였지만, exp110/112/113/116은 direct dynamic tracking, primitive MPC, terminal assist, short retrain이 모두 실패했다. 이번에는 `M*qacc + bias` residual, foot contact-force generalized force, short-horizon support/slip/pose score를 한 chooser 안에 같이 넣으면 qfrc wrapper보다 exp29 native visible gate에 가까워질 수 있다.

## 2. 방법 (Method)

- 기반: exp67 native evaluator, exp110 lower-body target/contact-force QP helpers.
- controller: 각 tick마다 fraction 후보를 만들고 lower-body target, joint qfrc, foot contact-force qfrc를 계산했다.
- full-order term: MuJoCo `mj_fullM`으로 mass matrix를 얻고 desired lower-body acceleration에 대해 floating-base residual과 actuated residual을 계산해 horizon score에 넣었다.
- MPC term: 각 후보를 MuJoCo clone에서 짧게 rollout하고 support, ZMP, slip, contact loss, drop, knee, hip을 함께 점수화했다.
- 판정: native exp29 visible gate가 통과할 때만 browser replay를 시도한다.

### 웹 근거

- MuJoCo computation docs는 forward/inverse dynamics와 mass matrix/contact generalized force 계산의 근거를 제공한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/stable/computation/index.html
- Strict contact-force humanoid tracking은 floating-base humanoid tracking에서 contact force constraints가 핵심임을 보인다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf
- Whole-body humanoid locomotion on Unitree G1은 G1 계열 whole-body tracking에서 정책과 dynamics-aware stabilization이 함께 필요함을 보인다. 접근일: 2026-06-18. https://arxiv.org/html/2604.17335v1
- Squat motion TP-MPC/WBC 연구는 squat가 CoM/ZMP/contact를 함께 다루는 전신 제어 문제임을 뒷받침한다. 접근일: 2026-06-18. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/

## 3. 결과 (Results)

| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Return | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
{chr(10).join(rows)}

Best full-order MPC smoke run: `{best['attempt']}` -> `{best['visible_verdict']}`.

박제:
- `verify/result.json`
- `verify/full-order-idqp-mpc-smoke-summary.md`
- `verify/<attempt>/native-eval.json`

## 4. 통찰 (Insights)

- Native verdict: `{result['verdict']}`.
- Browser replay attempted: `{result['browser_replay_attempted']}`.
- Best run은 drop `{best['visible_drop']:.4f}m`, knee `{best['max_knee_delta_rad']:.3f}rad`, hip `{best['max_hip_pitch_delta_rad']:.3f}rad`, contact `{best['foot_contact_ratio']:.2f}`, slip `{best['foot_slip_distance']:.3f}m`이다.
- 이 실험은 deployable WBC가 아니라 full-order formulation smoke다. 다만 이전 direct qfrc/primitive selector보다 명시적으로 floating-base residual, contact force, short-horizon gate를 같은 목적함수에 넣었다.

### 가설은 통과했나?

- [{'x' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else ' '}] PASS — native exp29 visible gate를 통과했다.
- [{' ' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else 'x'}] FAIL — full-order ID-QP/MPC formulation smoke만으로 native exp29 visible gate를 닫지 못했다.

### 정의에 반영

- M19 완료 조건은 그대로 native exp29 visible gate + browser replay다. 본 실험이 실패하면 다음은 더 많은 hand adapter sweep이 아니라 deployable whole-body controller 또는 장기 tracker training으로 넘어가야 한다.
"""
    (EXP_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    VERIFY.mkdir(parents=True, exist_ok=True)
    original_choose = EXP67.choose_blend
    EXP67.choose_blend = choose_full_order_idqp_mpc
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 tests a full-order ID-QP/MPC formulation smoke before another tracker retrain or hand adapter sweep.",
            "perspectives": {
                "product": "directly targets the showable native/browser visible squat gate",
                "architecture": "adds mass-matrix residual and contact generalized forces to short-horizon candidate selection",
                "security": "local MuJoCo simulation only; no credentials",
                "qa": "native JSON per variant, summary table, browser replay attempted only if native visible gate passes",
                "skeptic": "still a qfrc_applied formulation smoke, not a deployable real-time WBC stack",
            },
            "dod": [
                "run 6s native rollout variants",
                "state exp29 visible gate verdict and browser replay attempt flag",
            ],
        },
        "web_sources": [
            {"url": "https://mujoco.readthedocs.io/en/stable/computation/index.html", "accessed": "2026-06-18"},
            {"url": "https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf", "accessed": "2026-06-18"},
            {"url": "https://arxiv.org/html/2604.17335v1", "accessed": "2026-06-18"},
            {"url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/", "accessed": "2026-06-18"},
        ],
        "runs": [],
    }
    try:
        for variant in variants():
            run = EXP67.native_eval(variant=variant, seconds=args.seconds, out_dir=VERIFY / variant["attempt"])
            run = EXP91.annotate_visible(run)
            run["full_order_mpc_score"] = visible_score(run)
            result["runs"].append(run)
    finally:
        EXP67.choose_blend = original_choose
    visible = [run for run in result["runs"] if run["visible_8cm_gate"]]
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best = min(result["runs"], key=lambda run: run["full_order_mpc_score"])
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    result["best_full_order_mpc"] = compact_run(best)
    result["best_no_fall"] = None if best_no_fall is None else compact_run(best_no_fall)
    result["verdict"] = "PASS_VISIBLE_8CM_GATE" if visible else "FAIL_VISIBLE_8CM_GATE"
    result["browser_replay_attempted"] = bool(visible)
    write_summary(result)
    (VERIFY / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_readme(result)
    print(json.dumps({
        "verdict": result["verdict"],
        "browser_replay_attempted": result["browser_replay_attempted"],
        "best_full_order_mpc": result["best_full_order_mpc"],
        "best_no_fall": result["best_no_fall"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
