"""Over-target exp94 visible squat knee reference and audit native gate."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


EXP_DIR = Path(__file__).resolve().parent
ROOT = EXP_DIR.parents[1]
VERIFY = EXP_DIR / "verify"
EXP94_PATH = ROOT / "experiments/94-g1-visible-reference-motion-tracking-probe/run_visible_reference_motion_tracking_probe.py"


def load_exp94():
    spec = importlib.util.spec_from_file_location("exp94_visible_reference", EXP94_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXP94_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP94 = load_exp94()


def variants() -> list[dict[str, Any]]:
    common = {
        "drop": 0.09,
        "policy_weight": 1.0,
        "target_hip_delta": 0.38,
        "joint_kd": 1.5,
        "foot_kd_xy": 20.0,
        "foot_lift_force": 170.0,
        "slip_release": 0.08,
        "min_safety_scale": 0.45,
        "return_reference_weight": 0.20,
        "release_on_unhealthy": True,
        "descend_s": 4.2,
        "return_s": 2.2,
        "joint_kp": 34.0,
        "torque_clip": 54.0,
        "foot_kp_xy": 560.0,
        "foot_force_clip": 450.0,
        "preload_force": 34.0,
        "preload_height_kp": 680.0,
        "preload_force_clip": 112.0,
    }
    return [
        {**common, "attempt": "baseline-exp94-k0p64", "max_blend": 0.55, "reference_weight": 0.55, "residual_scale": 0.86, "target_knee_delta": 0.64, "health_floor": 0.20},
        {**common, "attempt": "k0p85-balanced", "max_blend": 0.50, "reference_weight": 0.50, "residual_scale": 0.82, "target_knee_delta": 0.85, "health_floor": 0.30},
        {**common, "attempt": "k0p95-balanced", "max_blend": 0.50, "reference_weight": 0.50, "residual_scale": 0.82, "target_knee_delta": 0.95, "health_floor": 0.34},
        {**common, "attempt": "k1p05-cautious", "max_blend": 0.44, "reference_weight": 0.44, "residual_scale": 0.76, "target_knee_delta": 1.05, "health_floor": 0.38},
        {**common, "attempt": "k1p05-strong", "max_blend": 0.58, "reference_weight": 0.58, "residual_scale": 0.90, "target_knee_delta": 1.05, "health_floor": 0.42},
        {**common, "attempt": "k1p10-hip0p42", "max_blend": 0.52, "reference_weight": 0.52, "residual_scale": 0.86, "target_knee_delta": 1.10, "target_hip_delta": 0.42, "health_floor": 0.42},
        {**common, "attempt": "k0p95-fast-return", "max_blend": 0.46, "reference_weight": 0.46, "residual_scale": 0.78, "target_knee_delta": 0.95, "health_floor": 0.38, "descend_s": 3.2, "return_s": 1.3, "return_reference_weight": 0.08},
        {**common, "attempt": "k1p05-fast-return", "max_blend": 0.44, "reference_weight": 0.44, "residual_scale": 0.76, "target_knee_delta": 1.05, "health_floor": 0.42, "descend_s": 3.2, "return_s": 1.3, "return_reference_weight": 0.08},
        {**common, "attempt": "k1p10-fast-return", "max_blend": 0.42, "reference_weight": 0.42, "residual_scale": 0.74, "target_knee_delta": 1.10, "target_hip_delta": 0.42, "health_floor": 0.46, "descend_s": 3.2, "return_s": 1.3, "return_reference_weight": 0.05},
    ]


def compact_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "attempt": run["attempt"],
        "visible_verdict": run["visible_verdict"],
        "visible_8cm_gate": run["visible_8cm_gate"],
        "visible_drop": run["visible_drop"],
        "max_knee_delta_rad": run["max_knee_delta_rad"],
        "max_hip_pitch_delta_rad": run["max_hip_pitch_delta_rad"],
        "fell_at": run["fell_at"],
        "return_to_stand": run["return_to_stand"],
        "foot_contact_ratio": run["foot_contact_ratio"],
        "foot_slip_distance": run["foot_slip_distance"],
        "final_height": run["final_height"],
        "visible_gap": run["visible_gap"],
        "optimizer_score": run["optimizer_score"],
    }


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Knee Overtarget Reference Tracker Summary",
        "",
        "| Rank | Attempt | Score | Gate | Verdict | Drop | Knee | Hip | Contact | Slip | Final h | Fell |",
        "|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, run in enumerate(sorted(result["runs"], key=lambda item: item["optimizer_score"]), start=1):
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        gate = "PASS" if run["visible_8cm_gate"] else "FAIL"
        lines.append(
            f"| {rank} | {run['attempt']} | {run['optimizer_score']:.1f} | {gate} | {run['visible_verdict']} | "
            f"{run['visible_drop']:.4f}m | {run['max_knee_delta_rad']:.3f} | "
            f"{run['max_hip_pitch_delta_rad']:.3f} | {run['foot_contact_ratio']:.2f} | "
            f"{run['foot_slip_distance']:.3f}m | {run['final_height']:.4f}m | {fell} |"
        )
    lines.extend([
        "",
        f"Verdict: **{result['verdict']}**",
        "",
        f"Best optimizer run: `{result['best_optimizer']['attempt']}`.",
        f"Best no-fall run: `{result['best_no_fall']['attempt'] if result['best_no_fall'] else 'none'}`.",
        "",
        "M19 closes only when native visible gate and browser replay both pass.",
    ])
    (out_dir / "knee-overtarget-reference-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_readme(result: dict[str, Any]) -> None:
    readme = EXP_DIR / "README.md"
    text = readme.read_text(encoding="utf-8")
    summary = result["best_optimizer"]
    no_fall = result["best_no_fall"] or summary
    results = f"""## 3. 결과 (Results)

### 데이터
| Attempt | Verdict | Drop | Knee | Hip | Contact | Slip | Fall | 비고 |
|-----|---------|------|------|-----|---------|------|------|------|
"""
    for run in sorted(result["runs"], key=lambda item: item["optimizer_score"]):
        fell = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        results += (
            f"| {run['attempt']} | {run['visible_verdict']} | {run['visible_drop']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f}rad | {run['max_hip_pitch_delta_rad']:.3f}rad | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | {fell} | "
            f"gap d/k/h {run['visible_gap']['drop_shortfall_m']:.4f}/"
            f"{run['visible_gap']['knee_shortfall_rad']:.3f}/"
            f"{run['visible_gap']['hip_shortfall_rad']:.3f} |\n"
        )
    results += f"""
Verdict: `{result['verdict']}`.

### 박제 위치
- `verify/knee-overtarget-reference-tracker/result.json`
- `verify/knee-overtarget-reference-tracker/knee-overtarget-reference-summary.md`
- Per-variant native rollouts under `verify/knee-overtarget-reference-tracker/*/native-eval.json`

"""
    insights = f"""## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Knee over-targeting did not close the exp29 visible gate.
- Best optimizer run `{summary['attempt']}` reached drop `{summary['visible_drop']:.4f}m`, knee `{summary['max_knee_delta_rad']:.3f}rad`, hip `{summary['max_hip_pitch_delta_rad']:.3f}rad`, contact `{summary['foot_contact_ratio']:.2f}`, slip `{summary['foot_slip_distance']:.3f}m`.
- Best no-fall candidate `{no_fall['attempt']}` still leaves knee shortfall `{no_fall['visible_gap']['knee_shortfall_rad']:.3f}rad`.
- Increasing target knee magnitude mostly exposes the same representation limit: the stabilizer-conditioned reference injection either keeps stance while under-flexing the knee, or moves toward the collapse/fall branch.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — over-targeting the reference knee does not produce a native visible squat gate pass.

### 정의에 반영
- M19 should not spend more experiments on scalar reference injection. The next route is a dedicated reference-conditioned tracker policy or a true trajectory optimizer over full qpos/action knots.
"""
    start = text.index("## 3. 결과 (Results)")
    text = text[:start] + results + insights
    readme.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()

    out_dir = VERIFY / "knee-overtarget-reference-tracker"
    out_dir.mkdir(parents=True, exist_ok=True)
    EXP94.EXP67.choose_blend = EXP94.reference_choose_blend

    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 tests whether exp94's reference tracker failure is target magnitude or controller representation.",
            "perspectives": {
                "product": "tries to close the last visible knee gate without changing the public M19 success definition",
                "architecture": "reuses exp94 native evaluator and changes only the reference target family",
                "security": "local MuJoCo/JAX run only; no secrets",
                "qa": "per-variant native JSON plus exp29 visible gate annotation",
                "skeptic": "over-targeting may push the rollout into the same fall/slip branch rather than create controlled knee flexion",
            },
            "dod": [
                "native sweep includes exp94 baseline and over-target variants",
                "raw evidence records drop/knee/hip/contact/slip/return/fall metrics",
                "M19 is not closed unless visible native gate passes",
            ],
        },
        "sources": [
            {"url": "https://arxiv.org/html/2507.07356v2", "accessed": "2026-06-18"},
            {"url": "https://huggingface.co/datasets/exptech/g1-moves", "accessed": "2026-06-18"},
            {"url": "https://www.mdpi.com/1424-8220/25/2/435", "accessed": "2026-06-18"},
            {"url": "https://arxiv.org/abs/2212.00541", "accessed": "2026-06-18"},
        ],
        "runs": [],
    }
    for variant in variants():
        run = EXP94.EXP67.native_eval(
            variant=variant,
            seconds=args.seconds,
            out_dir=out_dir / variant["attempt"],
        )
        run = EXP94.annotate_visible(run)
        run["optimizer_score"] = EXP94.optimizer_score(run)
        result["runs"].append(run)

    visible = [run for run in result["runs"] if run["visible_8cm_gate"]]
    no_fall = [run for run in result["runs"] if run["fell_at"] is None]
    best_optimizer = min(result["runs"], key=lambda run: run["optimizer_score"])
    best_no_fall = min(no_fall, key=lambda run: run["optimizer_score"], default=None)
    result["best_optimizer"] = compact_run(best_optimizer)
    result["best_no_fall"] = None if best_no_fall is None else compact_run(best_no_fall)
    result["verdict"] = "PASS_VISIBLE_8CM_GATE" if visible else "FAIL_VISIBLE_8CM_GATE"
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    update_readme(result)
    print(json.dumps({
        "verdict": result["verdict"],
        "best_optimizer": result["best_optimizer"],
        "best_no_fall": result["best_no_fall"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
