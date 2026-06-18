"""Contact-force QP-lite wrapper for recent G1 visible squat candidates."""

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
EXP106_RUNNER = ROOT / "experiments/106-g1-friction-cone-wbc-planner/run_friction_cone_wbc_planner.py"
EXP107_RUNNER = ROOT / "experiments/107-g1-contact-force-feasibility-audit/run_contact_force_feasibility_audit.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP91 = load_module(EXP91_RUNNER, "exp91_contact_qfrc")
EXP106 = load_module(EXP106_RUNNER, "exp106_friction_wbc")
EXP107 = load_module(EXP107_RUNNER, "exp107_force_audit")
BASE_CHOOSE = EXP91.multi_step_choose_blend


class ContactForceAudit(EXP107.ContactForceAudit):
    pass


def foot_velocity(model: mujoco.MjModel, data: mujoco.MjData, site_id: int) -> np.ndarray:
    jacp = np.zeros((3, model.nv))
    jacr = np.zeros((3, model.nv))
    mujoco.mj_jacSite(model, data, jacp, jacr, int(site_id))
    return jacp @ data.qvel


def solve_contact_force_qp(
    *,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    foot_site_ids: np.ndarray,
    initial_foot_xyz: np.ndarray,
    variant: dict[str, Any],
    support_health: float,
    zmp_health: float,
    slip_health: float,
) -> dict[str, Any]:
    mu = float(variant["contact_qp_mu"])
    kp_xy = float(variant["contact_qp_kp_xy"])
    kd_xy = float(variant["contact_qp_kd_xy"])
    normal_base = float(variant["contact_qp_normal_base"])
    normal_height_kp = float(variant["contact_qp_normal_height_kp"])
    normal_max = float(variant["contact_qp_normal_max"])
    normal_total_max = float(variant["contact_qp_total_normal_max"])
    health = float(np.clip(min(support_health, zmp_health, slip_health), 0.0, 1.0))

    desired = []
    normals = []
    for idx, site_id in enumerate(foot_site_ids):
        pos = data.site_xpos[int(site_id), :3]
        vel = foot_velocity(model, data, int(site_id))
        xy_err = initial_foot_xyz[idx, :2] - pos[:2]
        force_xy = kp_xy * xy_err - kd_xy * vel[:2]
        height_err = max(0.0, float(pos[2] - initial_foot_xyz[idx, 2]))
        normal = (normal_base + normal_height_kp * height_err) * (0.35 + 0.65 * health)
        desired.extend([float(force_xy[0]), float(force_xy[1]), float(np.clip(normal, 0.0, normal_max))])
        normals.append(normal)
    desired_x = np.asarray(desired, dtype=np.float64)

    def objective(x: np.ndarray) -> float:
        force_err = x - desired_x
        tangent = x[[0, 1, 3, 4]]
        normal = x[[2, 5]]
        balance = x[2] - x[5]
        return float(
            variant["contact_qp_w_track"] * np.dot(force_err, force_err)
            + variant["contact_qp_w_tangent"] * np.dot(tangent, tangent)
            + variant["contact_qp_w_normal"] * np.dot(normal, normal)
            + variant["contact_qp_w_balance"] * balance * balance
        )

    constraints = [
        {"type": "ineq", "fun": lambda x: mu * x[2] - abs(x[0])},
        {"type": "ineq", "fun": lambda x: mu * x[2] - abs(x[1])},
        {"type": "ineq", "fun": lambda x: mu * x[5] - abs(x[3])},
        {"type": "ineq", "fun": lambda x: mu * x[5] - abs(x[4])},
        {"type": "ineq", "fun": lambda x: normal_total_max - x[2] - x[5]},
    ]
    bounds = [
        (-normal_max * mu, normal_max * mu),
        (-normal_max * mu, normal_max * mu),
        (0.0, normal_max),
        (-normal_max * mu, normal_max * mu),
        (-normal_max * mu, normal_max * mu),
        (0.0, normal_max),
    ]
    x0 = np.clip(desired_x, [b[0] for b in bounds], [b[1] for b in bounds])
    if x0[2] + x0[5] > normal_total_max:
        x0[[2, 5]] *= normal_total_max / max(1e-9, x0[2] + x0[5])
    opt = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints, options={"maxiter": 30, "ftol": 1e-5, "disp": False})
    x = np.asarray(opt.x if opt.success else x0, dtype=np.float64)

    qfrc = np.zeros(model.nv, dtype=np.float64)
    ratios = []
    for idx, site_id in enumerate(foot_site_ids):
        jacp = np.zeros((3, model.nv))
        jacr = np.zeros((3, model.nv))
        mujoco.mj_jacSite(model, data, jacp, jacr, int(site_id))
        fx, fy, normal = x[idx * 3 : idx * 3 + 3]
        ratios.append(float(np.linalg.norm([fx, fy]) / max(1e-9, mu * normal)))
        # Robot-side force: horizontal anchoring plus downward preload.
        qfrc += jacp.T @ np.asarray([fx, fy, -normal], dtype=np.float64)
    return {
        "success": bool(opt.success),
        "status": str(opt.message),
        "health": health,
        "desired": desired_x.tolist(),
        "solution": x.tolist(),
        "qfrc": qfrc,
        "max_ratio": float(max(ratios) if ratios else 0.0),
        "normal_sum": float(x[2] + x[5]),
        "objective": float(objective(x)),
    }


def contact_force_qp_choose(**kwargs):
    target, qfrc, chosen = BASE_CHOOSE(**kwargs)
    variant = kwargs["variant"]
    model = kwargs["model"]
    data = kwargs["data"]
    support_now = kwargs["support_now"]
    zmp_now = kwargs["zmp_now"]
    foot_slip_now = kwargs["foot_slip_now"]
    support_health = float(np.clip((support_now["support_margin"] + 0.005) / 0.045, 0.0, 1.0))
    zmp_health = float(np.clip((zmp_now + 0.005) / 0.045, 0.0, 1.0))
    slip_health = float(np.clip(1.0 - foot_slip_now / 0.08, 0.0, 1.0))
    qp = solve_contact_force_qp(
        model=model,
        data=data,
        foot_site_ids=kwargs["foot_site_ids"],
        initial_foot_xyz=kwargs["initial_foot_xyz"],
        variant=variant,
        support_health=support_health,
        zmp_health=zmp_health,
        slip_health=slip_health,
    )
    scale = float(variant["contact_qp_scale"])
    qfrc = qfrc + scale * qp["qfrc"]
    max_ratio = qp["max_ratio"]
    if max_ratio >= variant["contact_qp_ratio_soft_limit"] or not qp["success"]:
        pose_scale = float(variant["contact_qp_pose_backoff"])
        default_pose = variant["default_pose"]
        target = default_pose + pose_scale * (target - default_pose)
        qfrc *= pose_scale
    chosen = dict(chosen)
    chosen.update({
        "contact_qp_success": qp["success"],
        "contact_qp_max_ratio": max_ratio,
        "contact_qp_normal_sum": qp["normal_sum"],
        "contact_qp_objective": qp["objective"],
        "contact_qp_health": qp["health"],
        "qfrc_max": float(np.max(np.abs(qfrc))),
    })
    return target, qfrc, chosen


def qp_variants() -> list[dict[str, Any]]:
    exp91_variants = {v["attempt"]: v for v in EXP91.variants()}
    exp106_variants = {v["attempt"]: v for v in EXP106.friction_variants()}
    common = {
        "contact_qp_mu": 0.80,
        "contact_qp_kp_xy": 720.0,
        "contact_qp_kd_xy": 26.0,
        "contact_qp_normal_base": 34.0,
        "contact_qp_normal_height_kp": 720.0,
        "contact_qp_normal_max": 115.0,
        "contact_qp_total_normal_max": 190.0,
        "contact_qp_scale": 0.62,
        "contact_qp_ratio_soft_limit": 0.97,
        "contact_qp_pose_backoff": 0.82,
        "contact_qp_w_track": 1.0,
        "contact_qp_w_tangent": 0.04,
        "contact_qp_w_normal": 0.01,
        "contact_qp_w_balance": 0.25,
    }
    return [
        {
            **exp91_variants["poseqfrc-braked-8cm"],
            **common,
            "attempt": "qp-lite-braked-8cm-balanced",
            "contact_qp_scale": 0.72,
            "contact_qp_pose_backoff": 0.78,
        },
        {
            **exp91_variants["poseqfrc-braked-knee"],
            **common,
            "attempt": "qp-lite-braked-knee-conservative",
            "contact_qp_kp_xy": 820.0,
            "contact_qp_normal_base": 28.0,
            "contact_qp_scale": 0.58,
            "contact_qp_pose_backoff": 0.70,
        },
        {
            **exp106_variants["friction-knee-minimal-depth"],
            **common,
            "attempt": "qp-lite-friction-minimal-depth-push",
            "max_blend": 0.482,
            "residual_scale": 0.046,
            "contact_qp_normal_base": 42.0,
            "contact_qp_scale": 0.78,
            "contact_qp_pose_backoff": 0.86,
        },
        {
            **exp106_variants["friction-tight-medium"],
            **common,
            "attempt": "qp-lite-friction-medium-braked",
            "contact_qp_kp_xy": 900.0,
            "contact_qp_normal_base": 30.0,
            "contact_qp_scale": 0.52,
            "contact_qp_pose_backoff": 0.66,
        },
        {
            **exp106_variants["friction-tight-medium"],
            **common,
            "attempt": "qp-lite-friction-medium-visible-push",
            "max_blend": 0.505,
            "residual_scale": 0.056,
            "pose_qfrc_scale": 0.78,
            "pose_qfrc_clip": 18.0,
            "contact_qp_kp_xy": 980.0,
            "contact_qp_normal_base": 34.0,
            "contact_qp_scale": 0.50,
            "contact_qp_pose_backoff": 0.74,
        },
        {
            **exp106_variants["friction-tight-medium"],
            **common,
            "attempt": "qp-lite-friction-medium-depth-push",
            "max_blend": 0.520,
            "residual_scale": 0.052,
            "w_height": 98.0,
            "depth_cap": 0.110,
            "pose_qfrc_scale": 0.72,
            "contact_qp_kp_xy": 1040.0,
            "contact_qp_normal_base": 38.0,
            "contact_qp_scale": 0.46,
            "contact_qp_pose_backoff": 0.70,
        },
        {
            **exp91_variants["poseqfrc-braked-knee"],
            **common,
            "attempt": "qp-lite-braked-knee-pose-push",
            "max_blend": 0.500,
            "residual_scale": 0.054,
            "pose_qfrc_scale": 1.02,
            "pose_qfrc_kp": 38.0,
            "pose_qfrc_clip": 22.0,
            "contact_qp_kp_xy": 920.0,
            "contact_qp_normal_base": 32.0,
            "contact_qp_scale": 0.54,
            "contact_qp_pose_backoff": 0.76,
        },
    ]


def visible_score(run: dict[str, Any]) -> float:
    gap = run["visible_gap"]
    score = 0.0
    score += 1000.0 if run["fell_at"] is not None else 0.0
    score += 300.0 * gap["drop_shortfall_m"] / 0.08
    score += 260.0 * gap["knee_shortfall_rad"] / 0.60
    score += 180.0 * gap["hip_shortfall_rad"] / 0.35
    score += 260.0 * gap["slip_excess_m"] / 0.08
    score += 220.0 * max(0.0, 0.90 - run["foot_contact_ratio"])
    score += 160.0 * max(0.0, 0.74 - run["final_height"])
    if run["visible_8cm_gate"]:
        score -= 800.0
    return float(score)


def annotate(run: dict[str, Any]) -> dict[str, Any]:
    run = EXP91.annotate_visible(run)
    run["qp_visible_score"] = visible_score(run)
    return run


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Contact-Force QP-Lite Wrapper Summary",
        "",
        "| Rank | Attempt | Score | Verdict | Drop | Knee | Hip | Contact | Slip | qfrc | Fall |",
        "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, run in enumerate(sorted(result["runs"], key=lambda item: item["qp_visible_score"]), start=1):
        fall = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        lines.append(
            f"| {rank} | {run['attempt']} | {run['qp_visible_score']:.1f} | {run['visible_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | {run['max_qfrc_applied']:.1f} | {fall} |"
        )
    lines.extend([
        "",
        f"Best QP-lite run: {result['best_qp_lite']}",
        f"Best visible run: {result['best_visible']}",
        "",
        "M19 closes only with native exp29 visible gate plus browser replay.",
    ])
    (out_dir / "contact-force-qp-lite-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(result: dict[str, Any]) -> None:
    rows = []
    for run in sorted(result["runs"], key=lambda item: item["qp_visible_score"]):
        fall = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        rows.append(
            f"| {run['attempt']} | {run['visible_verdict']} | {run['visible_drop']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | "
            f"{run['max_qfrc_applied']:.1f} | {fall} |"
        )
    best = result["best_qp_lite"]
    readme = f"""# 108-g1-contact-force-qp-lite-wrapper — G1 contact-force QP-lite wrapper

> `experiments/108-g1-contact-force-qp-lite-wrapper/README.md` — exp91 WBC-lite planner 위에 foot contact-force `(fx, fy, normal)` decision variable을 둔 QP-lite wrapper를 얹어 M19 visible squat gate를 다시 검증한다.

## 1. 가설 (Hypothesis)

Exp107은 no-fall 후보도 shallow 상태에서 friction limit에 붙고, visible 후보는 late fall/slip으로 무너진다는 것을 contact-force audit으로 보였다. 각 foot의 anchoring force와 normal preload를 QP로 풀어 qfrc에 더하면 WBC-lite score tuning보다 contact/slip을 직접 제한하면서 visible pose를 더 밀 수 있을 것이다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 + exp91 contact-constrained pose qfrc planner.
- wrapper: 매 control step에서 각 foot의 `(fx, fy, normal)`을 SLSQP QP-lite로 풀고 `Jacobian.T @ force`를 qfrc에 더했다.
- 비교 후보: exp91 visible-depth 계열 3개, exp106 friction 계열 4개.
- 판정: exp29 native visible gate가 통과할 때만 browser replay를 시도한다.

### 웹 근거
- Heavy-limb humanoid WBC는 generalized acceleration과 contact force를 함께 최적화하고 friction cone 제약을 둔다. 접근일: 2026-06-18. https://arxiv.org/html/2506.14278v1
- MuJoCo API는 `mj_contactForce`가 contact frame의 6D force/torque를 반환하고 `mj_applyFT`/Jacobian 방식으로 Cartesian force를 generalized force에 매핑할 수 있음을 제공한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html
- Strict contact force constrained tracking은 floating-base humanoid에서 contact forces와 joint torques를 제약 하에 계산해야 함을 보인다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf
- Prioritized WBC with contact constraints는 floating-base dynamics와 reaction forces만 포함하는 QP로 효율성과 friction-cone robustness를 얻는다고 설명한다. 접근일: 2026-06-18. https://junhyeokahn.github.io/data/kim2018_wbdc.pdf

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | qfrc | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(rows)}

Best QP-lite run: `{best['attempt']}` -> `{best['visible_verdict']}`.

### 박제 위치
- `verify/result.json`
- `verify/contact-force-qp-lite-summary.md`
- `verify/<attempt>/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Contact-force decision variable을 qfrc wrapper로 넣어도 native exp29 gate는 닫히지 않았다.
- Best run은 drop `{best['visible_drop']:.4f}m`, knee `{best['max_knee_delta_rad']:.3f}rad`, hip `{best['max_hip_pitch_delta_rad']:.3f}rad`, contact `{best['foot_contact_ratio']:.2f}`, slip `{best['foot_slip_distance']:.3f}m`이다.
- 이 실험은 full inverse-dynamics QP가 아니라 foot-force wrapper이므로, 실패 원인은 QP route 전체 폐기가 아니라 wrapper 수준의 한계로 해석한다.

### 가설은 통과했나?
- [{'x' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else ' '}] PASS — native exp29 visible gate를 통과했다.
- [{' ' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else 'x'}] FAIL — foot-force QP-lite wrapper만으로 native exp29 visible gate를 닫지 못했다.

### 정의에 반영
- 다음 단계는 qfrc wrapper가 아니라 floating-base dynamics equality, torque limits, contact forces를 함께 푸는 full inverse-dynamics QP이거나, reference-motion policy retrain이다.
"""
    (EXP_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY
    out_dir.mkdir(parents=True, exist_ok=True)
    original_choose = EXP91.EXP67.choose_blend
    original_wrench = EXP91.EXP67.EXP42.contact_wrench_summary
    auditor = ContactForceAudit(original_wrench)
    EXP91.EXP67.choose_blend = contact_force_qp_choose
    EXP91.EXP67.EXP42.contact_wrench_summary = auditor
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 tests contact-force decision variables via a foot-force QP-lite wrapper before full inverse-dynamics QP/retrain.",
            "perspectives": {
                "product": "attempts to turn exp107 force audit into an actual controller intervention",
                "architecture": "wraps exp91 planner and adds per-foot force QP output through site Jacobians",
                "security": "local MuJoCo simulation only",
                "qa": "native exp29 visible gate and raw JSON per variant; browser replay only if native passes",
                "skeptic": "foot-force qfrc wrapper is not full floating-base inverse-dynamics QP",
            },
            "dod": [
                "native JSON per QP-lite variant",
                "summary states whether any variant passes exp29 visible gate",
            ],
        },
        "web_sources": [
            {"url": "https://arxiv.org/html/2506.14278v1", "accessed": "2026-06-18"},
            {"url": "https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html", "accessed": "2026-06-18"},
            {"url": "https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf", "accessed": "2026-06-18"},
            {"url": "https://junhyeokahn.github.io/data/kim2018_wbdc.pdf", "accessed": "2026-06-18"},
        ],
        "runs": [],
    }
    try:
        for variant in qp_variants():
            auditor.begin(variant["attempt"])
            run = EXP91.EXP67.native_eval(
                variant=variant,
                seconds=args.seconds,
                out_dir=out_dir / variant["attempt"],
            )
            run = annotate(run)
            run["contact_force_audit"] = auditor.summarize()
            result["runs"].append(run)
    finally:
        EXP91.EXP67.choose_blend = original_choose
        EXP91.EXP67.EXP42.contact_wrench_summary = original_wrench

    visible = [run for run in result["runs"] if run["visible_8cm_gate"]]
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_qp = min(result["runs"], key=lambda run: run["qp_visible_score"])
    best_visible = max(result["runs"], key=lambda run: run["visible_drop"])
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    result["best_qp_lite"] = {
        "attempt": best_qp["attempt"],
        "visible_drop": best_qp["visible_drop"],
        "max_knee_delta_rad": best_qp["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_qp["max_hip_pitch_delta_rad"],
        "foot_contact_ratio": best_qp["foot_contact_ratio"],
        "foot_slip_distance": best_qp["foot_slip_distance"],
        "visible_verdict": best_qp["visible_verdict"],
        "fell_at": best_qp["fell_at"],
    }
    result["best_visible"] = {
        "attempt": best_visible["attempt"],
        "visible_drop": best_visible["visible_drop"],
        "max_knee_delta_rad": best_visible["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_visible["max_hip_pitch_delta_rad"],
        "visible_verdict": best_visible["visible_verdict"],
        "fell_at": best_visible["fell_at"],
    }
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "visible_drop": best_no_fall["visible_drop"],
        "max_knee_delta_rad": best_no_fall["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_no_fall["max_hip_pitch_delta_rad"],
        "visible_verdict": best_no_fall["visible_verdict"],
    }
    result["verdict"] = "PASS_VISIBLE_8CM_GATE" if visible else "FAIL_VISIBLE_8CM_GATE"
    result["browser_replay_attempted"] = bool(visible)
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_readme(result)
    print(result["verdict"], json.dumps({
        "best_qp_lite": result["best_qp_lite"],
        "best_visible": result["best_visible"],
        "best_no_fall": result["best_no_fall"],
        "browser_replay_attempted": result["browser_replay_attempted"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
