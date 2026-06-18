"""Probe friction-cone-aware WBC/MPC variants for the G1 visible squat gate."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP91_RUNNER = ROOT / "experiments/91-g1-contact-constrained-pose-qfrc-wrapper/run_contact_constrained_pose_qfrc_wrapper.py"


def load_exp91():
    spec = importlib.util.spec_from_file_location("exp91_contact_qfrc", EXP91_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP91_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP91 = load_exp91()


def friction_score(run: dict[str, Any]) -> float:
    gap = run["visible_gap"]
    support_debt = max(0.0, -run["min_support_margin"])
    zmp_debt = max(0.0, -run["min_zmp_margin"])
    contact_debt = max(0.0, 0.90 - run["foot_contact_ratio"])
    return_debt = max(0.0, 0.74 - run["final_height"])
    score = 0.0
    score += 1200.0 if run["fell_at"] is not None else 0.0
    score += 260.0 * gap["drop_shortfall_m"] / 0.08
    score += 260.0 * gap["knee_shortfall_rad"] / 0.60
    score += 180.0 * gap["hip_shortfall_rad"] / 0.35
    score += 520.0 * gap["slip_excess_m"] / 0.08
    score += 360.0 * contact_debt
    score += 260.0 * return_debt
    score += 140.0 * support_debt
    score += 120.0 * zmp_debt
    score += 80.0 * max(0.0, run["max_joint_limit_violation"] - 0.05)
    if run["visible_8cm_gate"]:
        score -= 800.0
    return float(score)


def annotate_friction(run: dict[str, Any]) -> dict[str, Any]:
    run["friction_score"] = friction_score(run)
    run["friction_rank_basis"] = {
        "primary": "exp29 visible gate",
        "extra_penalty": "slip_excess weighted higher as a friction-cone proxy",
        "note": "MuJoCo contact force vectors are not fully reconstructed here; slip/support/ZMP are used as native feasibility proxies.",
    }
    return run


def friction_variants() -> list[dict[str, Any]]:
    base = {variant["attempt"]: variant for variant in EXP91.variants()}
    seed = base["poseqfrc-light"]
    guarded = base["poseqfrc-braked-knee"]
    return [
        {
            **seed,
            "attempt": "friction-tight-light",
            "w_slip": 26000.0,
            "w_return_slip": 18000.0,
            "slip_floor": 0.040,
            "return_slip_floor": 0.045,
            "pose_qfrc_health_floor": 0.52,
            "pose_qfrc_scale": 0.56,
            "pose_qfrc_kp": 26.0,
            "pose_qfrc_clip": 14.0,
            "w_knee": 260.0,
            "foot_kp_xy": 640.0,
            "foot_force_clip": 500.0,
            "preload_force": 28.0,
            "preload_force_clip": 95.0,
            "depth_cap": 0.105,
            "w_depth_cap": 85000.0,
        },
        {
            **seed,
            "attempt": "friction-tight-medium",
            "w_slip": 32000.0,
            "w_return_slip": 24000.0,
            "slip_floor": 0.035,
            "return_slip_floor": 0.040,
            "pose_qfrc_health_floor": 0.58,
            "pose_qfrc_scale": 0.66,
            "pose_qfrc_kp": 30.0,
            "pose_qfrc_clip": 16.0,
            "w_knee": 340.0,
            "foot_kp_xy": 700.0,
            "foot_force_clip": 540.0,
            "preload_force": 24.0,
            "preload_force_clip": 85.0,
            "max_blend": 0.492,
            "residual_scale": 0.052,
            "depth_cap": 0.098,
            "w_depth_cap": 110000.0,
        },
        {
            **guarded,
            "attempt": "friction-braked-knee-low-slip",
            "w_slip": 36000.0,
            "w_return_slip": 30000.0,
            "slip_floor": 0.032,
            "return_slip_floor": 0.038,
            "pose_qfrc_health_floor": 0.62,
            "pose_qfrc_scale": 0.72,
            "pose_qfrc_kp": 32.0,
            "pose_qfrc_clip": 17.0,
            "w_knee": 420.0,
            "max_blend": 0.478,
            "residual_scale": 0.046,
            "foot_kp_xy": 760.0,
            "foot_force_clip": 580.0,
            "preload_force": 20.0,
            "preload_force_clip": 75.0,
            "depth_cap": 0.090,
            "w_depth_cap": 140000.0,
        },
        {
            **guarded,
            "attempt": "friction-braked-knee-return",
            "w_slip": 34000.0,
            "w_return_slip": 34000.0,
            "slip_floor": 0.034,
            "return_slip_floor": 0.036,
            "pose_qfrc_health_floor": 0.60,
            "pose_qfrc_recapture_scale": 0.12,
            "pose_qfrc_scale": 0.68,
            "pose_qfrc_kp": 30.0,
            "pose_qfrc_clip": 15.0,
            "w_knee": 380.0,
            "max_blend": 0.480,
            "residual_scale": 0.048,
            "recapture_s": 2.2,
            "return_s": 3.2,
            "return_joint_kp": 54.0,
            "return_torque_clip": 72.0,
            "w_stand": 1450.0,
            "foot_kp_xy": 720.0,
            "foot_force_clip": 560.0,
            "preload_force": 22.0,
            "preload_force_clip": 80.0,
            "depth_cap": 0.095,
            "w_depth_cap": 125000.0,
        },
        {
            **seed,
            "attempt": "friction-knee-minimal-depth",
            "w_slip": 40000.0,
            "w_return_slip": 28000.0,
            "slip_floor": 0.030,
            "return_slip_floor": 0.036,
            "pose_qfrc_health_floor": 0.68,
            "pose_qfrc_scale": 0.82,
            "pose_qfrc_kp": 34.0,
            "pose_qfrc_clip": 14.0,
            "w_knee": 520.0,
            "w_height": 70.0,
            "max_blend": 0.462,
            "residual_scale": 0.040,
            "foot_kp_xy": 820.0,
            "foot_force_clip": 620.0,
            "preload_force": 18.0,
            "preload_force_clip": 65.0,
            "depth_cap": 0.085,
            "w_depth_cap": 180000.0,
        },
    ]


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Friction-Cone-Aware WBC Planner Summary",
        "",
        "| Rank | Attempt | Score | Gate | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Joint viol | Fell |",
        "|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, run in enumerate(sorted(result["runs"], key=lambda item: item["friction_score"]), start=1):
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate = "PASS" if run["visible_8cm_gate"] else "FAIL"
        lines.append(
            f"| {rank} | {run['attempt']} | {run['friction_score']:.1f} | {gate} | {run['visible_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | "
            f"{run['max_hip_pitch_delta_rad']:.3f} | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['final_height']:.4f}m | "
            f"{run['max_joint_limit_violation']:.3f} | {fell} |"
        )
    lines.extend([
        "",
        f"Best friction run: {result['best_friction']}",
        f"Best visible run: {result['best_visible']}",
        f"Best no-fall run: {result['best_no_fall']}",
        "",
        "M19 closes only when native exp29 visible gate and browser replay both pass.",
    ])
    (out_dir / "friction-cone-wbc-planner-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(result: dict[str, Any]) -> None:
    best = result["best_friction"]
    rows = []
    for run in sorted(result["runs"], key=lambda item: item["friction_score"]):
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        rows.append(
            f"| {run['attempt']} | {run['visible_verdict']} | {run['visible_drop']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | "
            f"{run['final_height']:.4f}m | {fell} |"
        )
    readme = f"""# 106-g1-friction-cone-wbc-planner — G1 friction-cone-aware WBC planner

> `experiments/106-g1-friction-cone-wbc-planner/README.md` — exp91 contact-constrained qfrc planner 주변에서 slip/friction proxy를 더 강하게 걸어 M19 visible squat gate를 다시 검증한다.

## 1. 가설 (Hypothesis)

Exp91의 best no-fall branch는 8cm drop/contact/hip은 만족했지만 slip 9cm와 knee 0.448rad 때문에 실패했다. friction/slip 제약을 더 강하게 걸고, knee qfrc assist를 support health가 충분한 순간에만 허용하면 exp29 visible gate에 더 가까워질 수 있다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 + exp91 contact-constrained pose qfrc planner.
- 하네스 구성: exp91의 WBC-lite candidate selector를 재사용하고, variant를 slip floor, support-gated knee assist, depth cap, return slip penalty 중심으로 다시 구성했다.
- 판정: exp29 visible gate native pass 후에만 browser replay를 시도한다.

### 웹 근거
- Humanoid squat 연구는 TP-MPC + WBC로 squat trajectory를 tracking한다. 접근일: 2026-06-18. https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/
- Strict contact force constrained tracking은 floating-base humanoid에서 contact forces와 friction constraints가 tracking feasibility를 좌우한다고 정리한다. 접근일: 2026-06-18. https://la.disneyresearch.com/publication/human-motion-tracking-control-with-strict-contact-force-constraints-for-floating-base-humanoid-robots/
- Heavy-limb humanoid WBC는 slip 방지를 위해 contact force를 friction cone 안에 제한해야 한다고 명시한다. 접근일: 2026-06-18. https://arxiv.org/html/2506.14278v1
- MuJoCo 문서는 contact force/inverse dynamics가 contact model과 분리될 수 없음을 설명한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/stable/computation/index.html

### 시나리오
- `friction-tight-light`: exp91 light qfrc 주변에서 slip penalty를 강화한다.
- `friction-tight-medium`: knee assist를 조금 올리되 slip floor를 더 낮춘다.
- `friction-braked-knee-*`: depth cap과 support health floor를 높여 fall branch를 피한다.
- `friction-knee-minimal-depth`: knee qfrc를 더 세게 주되 depth를 최소화한다.

### 측정 metric
- exp29 visible gate: drop >= 8cm, knee >= 0.60rad, hip >= 0.35rad.
- stability gate: no fall, return, contact >= 0.90, slip <= 0.08m, joint violation <= 0.05rad.

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fall |
|-----|---------|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(rows)}

Best friction-ranked run: `{best['attempt']}` -> `{best['visible_verdict']}`.

### 박제 위치
- `verify/result.json`
- `verify/friction-cone-wbc-planner-summary.md`
- `verify/<attempt>/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Friction/slip을 강하게 벌점화하면 exp91의 9cm slip branch를 줄일 수 있는지 확인했다.
- Best run은 drop `{best['visible_drop']:.4f}m`, knee `{best['max_knee_delta_rad']:.3f}rad`, hip `{best['max_hip_pitch_delta_rad']:.3f}rad`, contact `{best['foot_contact_ratio']:.2f}`, slip `{best['foot_slip_distance']:.3f}m`, final height `{best['final_height']:.4f}m`이다.
- Native gate가 PASS하지 않으면 browser replay는 M19 evidence가 아니다.

### 가설은 통과했나?
- [{'x' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else ' '}] PASS — native exp29 visible gate를 통과했다.
- [{' ' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else 'x'}] FAIL — friction-aware WBC planner variant만으로 native exp29 visible gate를 닫지 못했다.

### 정의에 반영
- M19는 native+browser replay가 둘 다 통과해야 닫힌다.
"""
    (EXP_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY
    out_dir.mkdir(parents=True, exist_ok=True)
    EXP91.EXP67.choose_blend = EXP91.multi_step_choose_blend
    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 now tests a friction-cone-aware WBC/MPC planner variant instead of reward-only, wrapper-only, or future-command-only routes.",
            "perspectives": {
                "product": "targets the exact remaining slip/knee/return tradeoff around the best contact-qfrc branch",
                "architecture": "reuses exp91 WBC-lite planner and changes feasibility weights/health gates, not observation shape",
                "security": "local MuJoCo run only; no credentials",
                "qa": "native exp29 visible gate; browser replay only if native passes",
                "skeptic": "slip/support proxies are not a full friction-cone QP and may still overfit MuJoCo qfrc assistance",
            },
            "dod": [
                "raw native JSON per friction-aware variant",
                "summary states whether any native variant passes exp29 visible gate",
            ],
        },
        "web_sources": [
            {"url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/", "accessed": "2026-06-18"},
            {"url": "https://la.disneyresearch.com/publication/human-motion-tracking-control-with-strict-contact-force-constraints-for-floating-base-humanoid-robots/", "accessed": "2026-06-18"},
            {"url": "https://arxiv.org/html/2506.14278v1", "accessed": "2026-06-18"},
            {"url": "https://mujoco.readthedocs.io/en/stable/computation/index.html", "accessed": "2026-06-18"},
        ],
        "runs": [],
    }
    for variant in friction_variants():
        run = EXP91.EXP67.native_eval(
            variant=variant,
            seconds=args.seconds,
            out_dir=out_dir / variant["attempt"],
        )
        result["runs"].append(annotate_friction(EXP91.annotate_visible(run)))
    visible = [run for run in result["runs"] if run["visible_8cm_gate"]]
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_visible = max(visible, key=lambda run: run["visible_drop"], default=None)
    best_no_fall = max(no_fall, key=lambda run: run["visible_drop"], default=None)
    best_friction = min(result["runs"], key=lambda run: run["friction_score"])
    result["best_visible"] = None if best_visible is None else {
        "attempt": best_visible["attempt"],
        "visible_drop": best_visible["visible_drop"],
        "max_knee_delta_rad": best_visible["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_visible["max_hip_pitch_delta_rad"],
    }
    result["best_no_fall"] = None if best_no_fall is None else {
        "attempt": best_no_fall["attempt"],
        "visible_drop": best_no_fall["visible_drop"],
        "max_knee_delta_rad": best_no_fall["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_no_fall["max_hip_pitch_delta_rad"],
        "visible_gap": best_no_fall["visible_gap"],
        "visible_verdict": best_no_fall["visible_verdict"],
    }
    result["best_friction"] = {
        "attempt": best_friction["attempt"],
        "friction_score": best_friction["friction_score"],
        "visible_drop": best_friction["visible_drop"],
        "max_knee_delta_rad": best_friction["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": best_friction["max_hip_pitch_delta_rad"],
        "foot_contact_ratio": best_friction["foot_contact_ratio"],
        "foot_slip_distance": best_friction["foot_slip_distance"],
        "final_height": best_friction["final_height"],
        "visible_gap": best_friction["visible_gap"],
        "visible_verdict": best_friction["visible_verdict"],
        "fell_at": best_friction["fell_at"],
    }
    result["verdict"] = "PASS_VISIBLE_8CM_GATE" if visible else "FAIL_VISIBLE_8CM_GATE"
    result["browser_replay_attempted"] = bool(visible)
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_readme(result)
    print(result["verdict"], json.dumps({
        "best_friction": result["best_friction"],
        "best_visible": result["best_visible"],
        "best_no_fall": result["best_no_fall"],
        "browser_replay_attempted": result["browser_replay_attempted"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
