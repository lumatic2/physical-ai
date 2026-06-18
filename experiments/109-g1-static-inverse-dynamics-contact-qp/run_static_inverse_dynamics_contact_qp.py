"""Static inverse-dynamics contact QP feasibility for G1 visible squat poses."""

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
EXP91_RUNNER = ROOT / "experiments/91-g1-contact-constrained-pose-qfrc-wrapper/run_contact_constrained_pose_qfrc_wrapper.py"
G = 9.81


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP91 = load_module(EXP91_RUNNER, "exp91_contact_qfrc")
EXP62 = EXP91.EXP62


def set_pose(model: mujoco.MjModel, data: mujoco.MjData, spec: dict[str, float]) -> None:
    key = model.keyframe("knees_bent")
    data.qpos[:] = key.qpos
    start = key.qpos.copy()
    data.qpos[2] = float(start[2] - spec["drop"])
    for side in ("left", "right"):
        data.qpos[EXP62.qpos_index(model, f"{side}_knee_joint")] = start[EXP62.qpos_index(model, f"{side}_knee_joint")] + spec["knee"]
        data.qpos[EXP62.qpos_index(model, f"{side}_hip_pitch_joint")] = start[EXP62.qpos_index(model, f"{side}_hip_pitch_joint")] - spec["hip"]
        data.qpos[EXP62.qpos_index(model, f"{side}_ankle_pitch_joint")] = start[EXP62.qpos_index(model, f"{side}_ankle_pitch_joint")] - spec["ankle"]
    data.qvel[:] = 0.0
    data.qacc[:] = 0.0
    mujoco.mj_forward(model, data)


def site_jacobian(model: mujoco.MjModel, data: mujoco.MjData, site_id: int) -> np.ndarray:
    jacp = np.zeros((3, model.nv), dtype=np.float64)
    jacr = np.zeros((3, model.nv), dtype=np.float64)
    mujoco.mj_jacSite(model, data, jacp, jacr, int(site_id))
    return jacp


def inverse_required(model: mujoco.MjModel, data: mujoco.MjData) -> np.ndarray:
    old_qacc = data.qacc.copy()
    old_qvel = data.qvel.copy()
    data.qvel[:] = 0.0
    data.qacc[:] = 0.0
    mujoco.mj_inverse(model, data)
    qfrc = data.qfrc_inverse.copy()
    data.qacc[:] = old_qacc
    data.qvel[:] = old_qvel
    mujoco.mj_forward(model, data)
    return qfrc


def solve_contact_qp(
    *,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    foot_site_ids: np.ndarray,
    mu: float,
    normal_max: float,
    total_normal_max: float,
) -> dict[str, Any]:
    qfrc_req = inverse_required(model, data)
    jac_left = site_jacobian(model, data, int(foot_site_ids[0]))
    jac_right = site_jacobian(model, data, int(foot_site_ids[1]))
    a = np.column_stack([
        jac_left.T @ np.array([1.0, 0.0, 0.0]),
        jac_left.T @ np.array([0.0, 1.0, 0.0]),
        jac_left.T @ np.array([0.0, 0.0, 1.0]),
        jac_right.T @ np.array([1.0, 0.0, 0.0]),
        jac_right.T @ np.array([0.0, 1.0, 0.0]),
        jac_right.T @ np.array([0.0, 0.0, 1.0]),
    ])
    base_a = a[:6, :]
    act_a = a[6:, :]
    mass = float(np.sum(model.body_mass))
    nominal_normal = mass * G / 2.0
    x0 = np.array([0.0, 0.0, nominal_normal, 0.0, 0.0, nominal_normal], dtype=np.float64)
    x0[2] = min(x0[2], normal_max)
    x0[5] = min(x0[5], normal_max, total_normal_max - x0[2])

    def torque_after(x: np.ndarray) -> np.ndarray:
        return qfrc_req[6:] - act_a @ x

    def objective(x: np.ndarray) -> float:
        base_residual = base_a @ x - qfrc_req[:6]
        tau = torque_after(x)
        tangent = x[[0, 1, 3, 4]]
        normal_balance = x[2] - x[5]
        return float(
            80.0 * np.dot(base_residual, base_residual)
            + 0.010 * np.dot(tau, tau)
            + 0.020 * np.dot(tangent, tangent)
            + 0.010 * (x[2] * x[2] + x[5] * x[5])
            + 0.250 * normal_balance * normal_balance
        )

    constraints = [
        {"type": "ineq", "fun": lambda x: mu * x[2] - abs(x[0])},
        {"type": "ineq", "fun": lambda x: mu * x[2] - abs(x[1])},
        {"type": "ineq", "fun": lambda x: mu * x[5] - abs(x[3])},
        {"type": "ineq", "fun": lambda x: mu * x[5] - abs(x[4])},
        {"type": "ineq", "fun": lambda x: total_normal_max - x[2] - x[5]},
    ]
    bounds = [
        (-mu * normal_max, mu * normal_max),
        (-mu * normal_max, mu * normal_max),
        (0.0, normal_max),
        (-mu * normal_max, mu * normal_max),
        (-mu * normal_max, mu * normal_max),
        (0.0, normal_max),
    ]
    opt = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints, options={"maxiter": 200, "ftol": 1e-8, "disp": False})
    x = np.asarray(opt.x if opt.success else x0, dtype=np.float64)
    base_residual = base_a @ x - qfrc_req[:6]
    tau = torque_after(x)
    ratios = [
        float(np.linalg.norm(x[0:2]) / max(1e-9, mu * x[2])),
        float(np.linalg.norm(x[3:5]) / max(1e-9, mu * x[5])),
    ]
    return {
        "success": bool(opt.success),
        "status": str(opt.message),
        "force_solution": {
            "left_fx": float(x[0]),
            "left_fy": float(x[1]),
            "left_fz": float(x[2]),
            "right_fx": float(x[3]),
            "right_fy": float(x[4]),
            "right_fz": float(x[5]),
            "total_normal": float(x[2] + x[5]),
            "max_friction_ratio": float(max(ratios)),
        },
        "base_residual_l2": float(np.linalg.norm(base_residual)),
        "base_residual_linf": float(np.max(np.abs(base_residual))),
        "tau_linf": float(np.max(np.abs(tau))),
        "tau_l2": float(np.linalg.norm(tau)),
        "lower_tau_linf": float(np.max(np.abs(tau[:15]))),
        "qfrc_required_linf": float(np.max(np.abs(qfrc_req))),
        "qfrc_required_base_linf": float(np.max(np.abs(qfrc_req[:6]))),
        "qfrc_required_act_linf": float(np.max(np.abs(qfrc_req[6:]))),
        "objective": float(objective(x)),
    }


def support_metrics(model: mujoco.MjModel, data: mujoco.MjData) -> dict[str, Any]:
    foot_geom_ids = np.asarray([model.geom("left_foot").id, model.geom("right_foot").id])
    support = EXP91.EXP37.support_metrics(model, data, foot_geom_ids)
    com_xy = data.subtree_com[0, :2].copy()
    return {
        "support_margin": float(support["support_margin"]),
        "com_support_margin": float(EXP91.EXP67.EXP60.support_margin_for_point(com_xy, support)),
        "com_xy": [float(v) for v in com_xy],
    }


def pose_specs() -> list[dict[str, Any]]:
    return [
        {"name": "exp108-best-no-fall", "drop": 0.0749, "knee": 0.382, "hip": 0.210, "ankle": 0.14},
        {"name": "exp29-visible-min", "drop": 0.0800, "knee": 0.600, "hip": 0.350, "ankle": 0.25},
        {"name": "visible-soft-pose", "drop": 0.0850, "knee": 0.500, "hip": 0.300, "ankle": 0.22},
        {"name": "visible-full-pose", "drop": 0.0900, "knee": 0.640, "hip": 0.380, "ankle": 0.28},
    ]


def verdict(row: dict[str, Any]) -> str:
    if row["support"]["com_support_margin"] < 0.0:
        return "STATIC_COM_OUTSIDE_SUPPORT"
    if row["qp"]["base_residual_linf"] > 25.0:
        return "BASE_DYNAMICS_RESIDUAL_HIGH"
    if row["qp"]["force_solution"]["max_friction_ratio"] > 1.0:
        return "FRICTION_CONE_BREACH"
    if row["qp"]["lower_tau_linf"] > 120.0:
        return "STATIC_TORQUE_PROXY_HIGH"
    return "STATIC_ID_QP_PLAUSIBLE"


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Static Inverse-Dynamics Contact QP Summary",
        "",
        "| Pose | Verdict | Drop | Knee | Hip | CoM margin | Base residual | Lower tau | Normal | Friction ratio |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["poses"]:
        spec = row["spec"]
        qp = row["qp"]
        force = qp["force_solution"]
        lines.append(
            f"| {spec['name']} | {row['verdict']} | {spec['drop']:.3f}m | {spec['knee']:.3f} | {spec['hip']:.3f} | "
            f"{row['support']['com_support_margin']:.4f}m | {qp['base_residual_linf']:.2f} | "
            f"{qp['lower_tau_linf']:.2f} | {force['total_normal']:.1f}N | {force['max_friction_ratio']:.3f} |"
        )
    lines.extend([
        "",
        f"Best static pose: {result['best_static']}",
        "",
        "This is a static inverse-dynamics feasibility diagnostic, not a native rollout pass.",
    ])
    (out_dir / "static-id-contact-qp-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(result: dict[str, Any]) -> None:
    rows = []
    for row in result["poses"]:
        spec = row["spec"]
        qp = row["qp"]
        rows.append(
            f"| {spec['name']} | {row['verdict']} | {spec['drop']:.3f}m | {spec['knee']:.3f} | {spec['hip']:.3f} | "
            f"{row['support']['com_support_margin']:.4f}m | {qp['base_residual_linf']:.2f} | "
            f"{qp['lower_tau_linf']:.2f} | {qp['force_solution']['max_friction_ratio']:.3f} |"
        )
    readme = f"""# 109-g1-static-inverse-dynamics-contact-qp — G1 static inverse-dynamics contact QP

> `experiments/109-g1-static-inverse-dynamics-contact-qp/README.md` — M19 visible squat target poses를 static inverse-dynamics contact-force QP로 평가해 full ID-QP/retrain 중 어느 쪽으로 가야 하는지 분리한다.

## 1. 가설 (Hypothesis)

Exp108의 QP-lite wrapper는 no-fall/contact/slip을 지키며 7.49cm까지 갔지만 knee/hip pose gate를 넘기지 못했다. 8cm visible target 자체가 static inverse-dynamics contact QP에서 plausible이면 controller/retrain 문제가 더 강하고, static 단계부터 residual/torque가 크면 full ID-QP도 target relaxation이 필요하다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1.
- poses: exp108 best no-fall pose, exp29 visible minimum pose, soft/full visible pose.
- QP 변수: left/right foot contact force `(fx, fy, fz)`.
- 목적: floating-base inverse dynamics residual, actuator torque proxy, tangential force, normal force imbalance를 최소화한다.
- 제약: unilateral normal force, friction cone, total normal force cap.

### 웹 근거
- MuJoCo dynamics identity는 inverse dynamics에서 `tau = M*qacc + c - J^T*f` 형태로 contact force가 generalized force에 들어간다고 설명한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/3.2.2/computation/
- Strict contact-force humanoid tracking은 floating-base humanoid의 6DoF base motion이 contact forces와 friction constraints에 의해 실현된다고 설명한다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf
- Prioritized WBC with contact constraints는 floating-base dynamics와 reaction forces만 포함하는 QP를 효율적 중간 문제로 사용한다. 접근일: 2026-06-18. https://junhyeokahn.github.io/data/kim2018_wbdc.pdf
- Position-controlled robots can struggle to control contact force directly, motivating force-control/admittance layers or policy retraining. 접근일: 2026-06-18. https://arxiv.org/html/2312.16465v3

## 3. 결과 (Results)

### 데이터
| Pose | Verdict | Drop | Knee | Hip | CoM margin | Base residual | Lower tau | Friction ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

Best static pose: `{result['best_static']['spec']['name']}` -> `{result['best_static']['verdict']}`.

### 박제 위치
- `verify/result.json`
- `verify/static-id-contact-qp-summary.md`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Static inverse-dynamics contact QP는 native rollout과 다른 gate다. 여기서 plausible해도 M19는 닫히지 않는다.
- Best static pose는 `{result['best_static']['spec']['name']}`이고 verdict는 `{result['best_static']['verdict']}`이다.
- 이 결과는 다음 구현에서 full ID-QP controller를 만들지, reference-motion retrain으로 넘어갈지 판단하는 중간 증거다.

### 가설은 통과했나?
- [{'x' if result['has_static_plausible_visible'] else ' '}] PASS — visible target 중 static ID-QP plausible 후보가 있다.
- [{' ' if result['has_static_plausible_visible'] else 'x'}] FAIL — visible target이 static ID-QP에서도 바로 plausible하지 않다.

### 정의에 반영
- M19 완료는 여전히 native exp29 visible gate + browser replay다. Static ID-QP는 route selection evidence일 뿐이다.
"""
    (EXP_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mu", type=float, default=0.80)
    parser.add_argument("--normal-max", type=float, default=500.0)
    parser.add_argument("--total-normal-max", type=float, default=900.0)
    args = parser.parse_args()
    out_dir = VERIFY
    out_dir.mkdir(parents=True, exist_ok=True)

    env = EXP91.EXP67.EXP28.ContactAwareSquat(
        stage_height=0.67,
        controller_blend=0.5,
        freeze_phase=True,
        blend_schedule="squat",
        reference_scale=1.0,
        config_overrides={"impl": "jax"},
    )
    model = env.mj_model
    foot_site_ids = np.asarray(env._feet_site_id)
    result = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 adds static inverse-dynamics contact QP feasibility before building a dynamic full ID-QP controller or retraining.",
            "perspectives": {
                "product": "separates target feasibility from controller rollout failure",
                "architecture": "uses MuJoCo inverse dynamics and foot contact Jacobians rather than qfrc wrapper scoring",
                "security": "local simulation only",
                "qa": "raw JSON includes support margins, base residuals, contact force solution, and torque proxy",
                "skeptic": "static feasibility does not prove dynamic rollout or browser replay",
            },
            "dod": [
                "evaluate exp108 and exp29 visible target poses",
                "state whether any visible target is statically plausible under contact-force QP",
            ],
        },
        "web_sources": [
            {"url": "https://mujoco.readthedocs.io/en/3.2.2/computation/", "accessed": "2026-06-18"},
            {"url": "https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf", "accessed": "2026-06-18"},
            {"url": "https://junhyeokahn.github.io/data/kim2018_wbdc.pdf", "accessed": "2026-06-18"},
            {"url": "https://arxiv.org/html/2312.16465v3", "accessed": "2026-06-18"},
        ],
        "solver": {"mu": args.mu, "normal_max": args.normal_max, "total_normal_max": args.total_normal_max},
        "poses": [],
    }
    for spec in pose_specs():
        data = mujoco.MjData(model)
        set_pose(model, data, spec)
        row = {
            "spec": spec,
            "support": support_metrics(model, data),
            "qp": solve_contact_qp(
                model=model,
                data=data,
                foot_site_ids=foot_site_ids,
                mu=args.mu,
                normal_max=args.normal_max,
                total_normal_max=args.total_normal_max,
            ),
        }
        row["verdict"] = verdict(row)
        result["poses"].append(row)
    plausible = [row for row in result["poses"] if row["verdict"] == "STATIC_ID_QP_PLAUSIBLE"]
    visible_plausible = [row for row in plausible if row["spec"]["drop"] >= 0.08 and row["spec"]["knee"] >= 0.50 and row["spec"]["hip"] >= 0.30]
    result["has_static_plausible_visible"] = bool(visible_plausible)
    result["best_static"] = min(
        result["poses"],
        key=lambda row: (
            row["qp"]["base_residual_linf"],
            row["qp"]["lower_tau_linf"],
            -row["spec"]["drop"],
        ),
    )
    result["verdict"] = "STATIC_VISIBLE_PLAUSIBLE" if result["has_static_plausible_visible"] else "STATIC_VISIBLE_NOT_PLAUSIBLE"
    result["browser_replay_attempted"] = False
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_readme(result)
    print(result["verdict"], json.dumps({
        "best_static": {
            "name": result["best_static"]["spec"]["name"],
            "verdict": result["best_static"]["verdict"],
            "base_residual_linf": result["best_static"]["qp"]["base_residual_linf"],
            "lower_tau_linf": result["best_static"]["qp"]["lower_tau_linf"],
        },
        "has_static_plausible_visible": result["has_static_plausible_visible"],
        "browser_replay_attempted": result["browser_replay_attempted"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
