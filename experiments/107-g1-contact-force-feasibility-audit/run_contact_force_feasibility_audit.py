"""Audit MuJoCo contact-force feasibility for recent G1 squat candidates."""

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
EXP91_RUNNER = ROOT / "experiments/91-g1-contact-constrained-pose-qfrc-wrapper/run_contact_constrained_pose_qfrc_wrapper.py"
EXP106_RUNNER = ROOT / "experiments/106-g1-friction-cone-wbc-planner/run_friction_cone_wbc_planner.py"
G = 9.81


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXP91 = load_module(EXP91_RUNNER, "exp91_contact_qfrc")
EXP106 = load_module(EXP106_RUNNER, "exp106_friction_wbc")


class ContactForceAudit:
    def __init__(self, original):
        self.original = original
        self.run_id: str | None = None
        self.records: list[dict[str, Any]] = []
        self.start_height: float | None = None

    def begin(self, run_id: str) -> None:
        self.run_id = run_id
        self.records = []
        self.start_height = None

    def __call__(self, model: mujoco.MjModel, data: mujoco.MjData) -> dict[str, Any]:
        base = self.original(model, data)
        detail = contact_force_detail(model, data, self.start_height)
        if self.start_height is None:
            self.start_height = float(data.qpos[2])
        detail["run_id"] = self.run_id
        detail["t"] = float(data.time)
        self.records.append(detail)
        merged = dict(base)
        merged.update({
            "max_friction_ratio": detail["max_friction_ratio"],
            "min_friction_margin": detail["min_friction_margin"],
            "cop_support_margin": detail["cop_support_margin"],
            "total_foot_normal": detail["total_foot_normal"],
        })
        return merged

    def summarize(self) -> dict[str, Any]:
        if not self.records:
            return {
                "frames": 0,
                "max_friction_ratio": 0.0,
                "min_friction_margin": 0.0,
                "min_cop_support_margin": 0.0,
                "friction_violation_frames": 0,
                "cop_breach_frames": 0,
                "no_foot_normal_frames": 0,
                "max_total_foot_normal": 0.0,
                "mean_total_foot_normal": 0.0,
                "max_lr_normal_imbalance": 0.0,
                "max_visible_drop_at_violation": 0.0,
            }
        ratios = [r["max_friction_ratio"] for r in self.records]
        margins = [r["min_friction_margin"] for r in self.records]
        cop_margins = [r["cop_support_margin"] for r in self.records if r["cop_support_margin"] is not None]
        normals = [r["total_foot_normal"] for r in self.records]
        violations = [r for r in self.records if r["max_friction_ratio"] > 1.0]
        return {
            "frames": len(self.records),
            "max_friction_ratio": float(max(ratios)),
            "min_friction_margin": float(min(margins)),
            "min_cop_support_margin": None if not cop_margins else float(min(cop_margins)),
            "friction_violation_frames": len(violations),
            "friction_saturation_frames": sum(1 for r in self.records if r["max_friction_ratio"] >= 0.98 and r["total_foot_tangent"] > 1e-6),
            "cop_breach_frames": sum(1 for r in self.records if r["cop_support_margin"] is not None and r["cop_support_margin"] < 0.0),
            "no_foot_normal_frames": sum(1 for r in self.records if r["total_foot_normal"] <= 1e-6),
            "max_total_foot_normal": float(max(normals)),
            "mean_total_foot_normal": float(np.mean(normals)),
            "max_lr_normal_imbalance": float(max(r["lr_normal_imbalance"] for r in self.records)),
            "max_visible_drop_at_violation": float(max((r["visible_drop"] for r in violations), default=0.0)),
        }


def contact_force_detail(model: mujoco.MjModel, data: mujoco.MjData, start_height: float | None) -> dict[str, Any]:
    foot_geom_ids = {
        "left": int(model.geom("left_foot").id),
        "right": int(model.geom("right_foot").id),
    }
    support = EXP91.EXP37.support_metrics(model, data, np.asarray(list(foot_geom_ids.values())))
    totals = {
        "left": {"normal": 0.0, "tangent": 0.0, "contacts": 0},
        "right": {"normal": 0.0, "tangent": 0.0, "contacts": 0},
        "other": {"normal": 0.0, "tangent": 0.0, "contacts": 0},
    }
    min_margin = float("inf")
    max_ratio = 0.0
    violation_count = 0
    weighted_pos = np.zeros(2, dtype=np.float64)
    total_weight = 0.0
    for idx in range(data.ncon):
        contact = data.contact[idx]
        pair = {int(contact.geom1), int(contact.geom2)}
        side = "other"
        if foot_geom_ids["left"] in pair:
            side = "left"
        elif foot_geom_ids["right"] in pair:
            side = "right"
        wrench = np.zeros(6, dtype=np.float64)
        mujoco.mj_contactForce(model, data, idx, wrench)
        normal = max(0.0, abs(float(wrench[0])))
        tangent = float(np.linalg.norm(wrench[1:3]))
        mu = max(float(contact.friction[0]), 1e-9)
        if side in {"left", "right"}:
            ratio = 0.0 if normal <= 1e-9 else tangent / (mu * normal)
            margin = mu * normal - tangent
            min_margin = min(min_margin, margin)
            max_ratio = max(max_ratio, ratio)
            violation_count += int(ratio > 1.0)
            weighted_pos += normal * np.asarray(contact.pos[:2], dtype=np.float64)
            total_weight += normal
        totals[side]["normal"] += normal
        totals[side]["tangent"] += tangent
        totals[side]["contacts"] += 1
    foot_normal = totals["left"]["normal"] + totals["right"]["normal"]
    foot_tangent = totals["left"]["tangent"] + totals["right"]["tangent"]
    lr_imbalance = 0.0 if foot_normal <= 1e-9 else abs(totals["left"]["normal"] - totals["right"]["normal"]) / foot_normal
    cop_xy = None
    cop_margin = None
    if total_weight > 1e-9:
        cop = weighted_pos / total_weight
        cop_xy = [float(cop[0]), float(cop[1])]
        cop_margin = float(EXP91.EXP67.EXP60.support_margin_for_point(cop, support))
    mass = float(np.sum(model.body_mass))
    return {
        "height": float(data.qpos[2]),
        "visible_drop": 0.0 if start_height is None else float(start_height - data.qpos[2]),
        "total_foot_normal": float(foot_normal),
        "total_foot_tangent": float(foot_tangent),
        "normal_load_ratio": float(foot_normal / max(1e-9, mass * G)),
        "max_friction_ratio": float(max_ratio),
        "min_friction_margin": 0.0 if min_margin == float("inf") else float(min_margin),
        "friction_violation_contacts": int(violation_count),
        "cop_xy": cop_xy,
        "cop_support_margin": cop_margin,
        "support_margin": float(support["support_margin"]),
        "lr_normal_imbalance": float(lr_imbalance),
        "left_normal": float(totals["left"]["normal"]),
        "right_normal": float(totals["right"]["normal"]),
        "left_contacts": int(totals["left"]["contacts"]),
        "right_contacts": int(totals["right"]["contacts"]),
        "other_contacts": int(totals["other"]["contacts"]),
    }


def select_variants() -> list[tuple[str, dict[str, Any]]]:
    exp91_variants = {v["attempt"]: v for v in EXP91.variants()}
    exp106_variants = {v["attempt"]: v for v in EXP106.friction_variants()}
    return [
        ("exp91-poseqfrc-braked-8cm", exp91_variants["poseqfrc-braked-8cm"]),
        ("exp91-poseqfrc-braked-knee", exp91_variants["poseqfrc-braked-knee"]),
        ("exp106-friction-knee-minimal-depth", exp106_variants["friction-knee-minimal-depth"]),
        ("exp106-friction-tight-medium", exp106_variants["friction-tight-medium"]),
    ]


def force_feasibility_verdict(run: dict[str, Any], audit: dict[str, Any]) -> str:
    if run["fell_at"] is not None:
        return "FAIL_FALL"
    if audit["friction_violation_frames"] > 0:
        return "FRICTION_CONE_BREACH"
    if audit["friction_saturation_frames"] > 20:
        if run["visible_drop"] < 0.08:
            return "FRICTION_LIMITED_SHALLOW"
        return "FRICTION_LIMIT_VISIBLE_UNSTABLE"
    if audit["cop_breach_frames"] > 0:
        return "COP_SUPPORT_BREACH"
    if run["visible_drop"] < 0.08:
        return "FORCE_FEASIBLE_BUT_SHALLOW"
    if run["max_knee_delta_rad"] < 0.60 or run["max_hip_pitch_delta_rad"] < 0.35:
        return "FORCE_FEASIBLE_BUT_POSE_SHORT"
    return "FORCE_FEASIBLE_VISIBLE_CANDIDATE"


def write_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# G1 Contact Force Feasibility Audit Summary",
        "",
        "| Attempt | Verdict | Drop | Knee | Hip | Contact | Slip | Max friction ratio | Saturated frames | Min CoP margin | Force frames | Fall |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in result["runs"]:
        run = item["native"]
        audit = item["force_audit"]
        fall = "never" if run["fell_at"] is None else f"{run['fell_at']:.2f}s"
        cop_margin = audit["min_cop_support_margin"]
        lines.append(
            f"| {item['attempt']} | {item['force_verdict']} | {run['visible_drop']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{run['foot_contact_ratio']:.2f} | {run['foot_slip_distance']:.3f}m | "
            f"{audit['max_friction_ratio']:.3f} | {audit['friction_saturation_frames']} | "
            f"{'n/a' if cop_margin is None else f'{cop_margin:.4f}m'} | {audit['frames']} | {fall} |"
        )
    lines.extend([
        "",
        f"Best no-fall force-audited: {result['best_force_feasible_no_fall']}",
        f"Best visible candidate: {result['best_visible_candidate']}",
        "",
        "M19 still requires native exp29 visible gate plus browser replay.",
    ])
    (out_dir / "contact-force-feasibility-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(result: dict[str, Any]) -> None:
    rows = []
    for item in result["runs"]:
        run = item["native"]
        audit = item["force_audit"]
        rows.append(
            f"| {item['attempt']} | {item['force_verdict']} | {run['visible_drop']:.4f}m | "
            f"{run['max_knee_delta_rad']:.3f} | {run['max_hip_pitch_delta_rad']:.3f} | "
            f"{audit['max_friction_ratio']:.3f} | {audit['min_friction_margin']:.2f}N | "
            f"{audit['friction_violation_frames']} / {audit['friction_saturation_frames']} | {audit['cop_breach_frames']} | "
            f"{run['foot_slip_distance']:.3f}m | {'never' if run['fell_at'] is None else f'{run['fell_at']:.2f}s'} |"
        )
    readme = f"""# 107-g1-contact-force-feasibility-audit — G1 contact-force feasibility audit

> `experiments/107-g1-contact-force-feasibility-audit/README.md` — exp91/106의 대표 G1 squat 후보를 MuJoCo `mj_contactForce`로 다시 재생해 friction cone, CoP support margin, normal force imbalance를 직접 박제한다.

## 1. 가설 (Hypothesis)

Exp106까지의 WBC-lite/qfrc sweep은 slip proxy를 조이면 자세가 얕아지고, 자세를 밀면 fall/slip이 커졌다. 실제 contact force audit을 붙이면 M19의 다음 작업이 단순 qfrc sweep이 아니라 full contact-force QP 또는 reference-motion policy retrain이어야 하는지 더 명확해질 것이다.

## 2. 방법 (Method)

### 셋업
- 모델: local MuJoCo G1 + exp91 contact-constrained WBC-lite path.
- 비교 후보: exp91 visible-depth 계열 2개와 exp106 friction-tight 계열 2개.
- 계측: 기존 `EXP42.contact_wrench_summary` 호출 지점에 auditor를 주입해 각 control step의 `mj_contactForce` 값을 수집했다.
- 판정: native exp29 gate는 그대로 유지하고, 별도로 max friction ratio, min friction margin, CoP support margin, 좌우 normal imbalance를 박제했다.

### 웹 근거
- Heavy-limb humanoid WBC는 contact force와 generalized acceleration을 함께 최적화하고, slip 방지를 위해 friction cone 제약을 둔다. 접근일: 2026-06-18. https://arxiv.org/html/2506.14278v1
- MuJoCo 문서는 contact force가 contact frame의 normal/tangent friction cone으로 표현되며 solver 설정에 따라 elliptic/pyramidal cone을 쓴다고 설명한다. 접근일: 2026-06-18. https://mujoco.readthedocs.io/en/3.6.0/computation/
- Strict contact force constrained tracking 논문은 floating-base humanoid에서 base motion은 contact force와 friction constraints에 의해 실현 가능성이 결정된다고 설명한다. 접근일: 2026-06-18. https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf
- Unitree 공식 open-source 페이지는 `unitree_mujoco`와 G1 지원 RL 구현을 공개 경로로 제시한다. 접근일: 2026-06-18. https://www.unitree.com/mobile/opensource/

## 3. 결과 (Results)

### 데이터
| Run | Force verdict | Drop | Knee | Hip | Max friction ratio | Min friction margin | Friction breach / saturation frames | CoP breach frames | Slip | Fall |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(rows)}

### 박제 위치
- `verify/result.json`
- `verify/contact-force-feasibility-summary.md`
- `verify/<attempt>/native-eval.json`
- `verify/<attempt>/contact-force-audit.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- Contact force 자체는 이제 direct metric으로 남는다. 이후 실험은 slip proxy가 아니라 friction ratio / CoP margin / native pose gate를 같이 볼 수 있다.
- Best no-fall force-audited 후보: `{result['best_force_feasible_no_fall']}`.
- Best visible 후보: `{result['best_visible_candidate']}`.
- Native exp29 gate가 PASS하지 않았으므로 browser replay는 M19 완료 증거가 아니다.

### 가설은 통과했나?
- [{'x' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else ' '}] PASS — native exp29 visible gate와 force audit을 동시에 통과했다.
- [{' ' if result['verdict'] == 'PASS_VISIBLE_8CM_GATE' else 'x'}] FAIL — force audit은 다음 병목을 좁혔지만 M19 native/browser gate를 닫지 못했다.

### 정의에 반영
- M19의 다음 구현은 WBC-lite score tuning이 아니라 contact-force decision variable을 가진 QP, 또는 contact-aware reference-motion policy retrain이어야 한다.
"""
    (EXP_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    out_dir = VERIFY
    out_dir.mkdir(parents=True, exist_ok=True)

    original = EXP91.EXP67.EXP42.contact_wrench_summary
    auditor = ContactForceAudit(original)
    EXP91.EXP67.EXP42.contact_wrench_summary = auditor
    EXP91.EXP67.choose_blend = EXP91.multi_step_choose_blend

    result = {
        "evaluation_seconds": args.seconds,
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 adds direct MuJoCo contact-force audit before attempting full contact-force QP or retrain.",
            "perspectives": {
                "product": "turns the remaining squat blocker into a readable force-feasibility table",
                "architecture": "instruments existing native rollout instead of changing the policy/controller path",
                "security": "local simulation only; no credentials or external side effects",
                "qa": "raw native JSON plus contact-force audit JSON per candidate",
                "skeptic": "audit is diagnostic; it does not yet solve the constrained control problem",
            },
            "dod": [
                "representative exp91/exp106 candidates rerun with contact-force audit",
                "summary states whether any candidate passes native visible gate",
            ],
        },
        "web_sources": [
            {"url": "https://arxiv.org/html/2506.14278v1", "accessed": "2026-06-18"},
            {"url": "https://mujoco.readthedocs.io/en/3.6.0/computation/", "accessed": "2026-06-18"},
            {"url": "https://la.disneyresearch.com/wp-content/uploads/PROJECT_Humanoids-mocap_IEEE-RAS-ICHR-2013_PAPER1.pdf", "accessed": "2026-06-18"},
            {"url": "https://www.unitree.com/mobile/opensource/", "accessed": "2026-06-18"},
        ],
        "runs": [],
    }

    try:
        for attempt, variant in select_variants():
            auditor.begin(attempt)
            run = EXP91.EXP67.native_eval(
                variant={**variant, "attempt": attempt},
                seconds=args.seconds,
                out_dir=out_dir / attempt,
            )
            run = EXP91.annotate_visible(run)
            audit = auditor.summarize()
            item = {
                "attempt": attempt,
                "native": run,
                "force_audit": audit,
                "force_verdict": force_feasibility_verdict(run, audit),
            }
            result["runs"].append(item)
            (out_dir / attempt / "contact-force-audit.json").write_text(
                json.dumps({"summary": audit, "frames": auditor.records}, indent=2),
                encoding="utf-8",
            )
    finally:
        EXP91.EXP67.EXP42.contact_wrench_summary = original

    visible = [item for item in result["runs"] if item["native"]["visible_8cm_gate"]]
    no_fall = [item for item in result["runs"] if item["native"]["fell_at"] is None]
    force_feasible_no_fall = [
        item for item in no_fall
        if item["force_audit"]["friction_violation_frames"] == 0 and item["force_audit"]["cop_breach_frames"] == 0
    ]
    best_force = max(force_feasible_no_fall, key=lambda item: item["native"]["visible_drop"], default=None)
    best_visible = max(result["runs"], key=lambda item: item["native"]["visible_drop"])
    result["best_force_feasible_no_fall"] = None if best_force is None else {
        "attempt": best_force["attempt"],
        "visible_drop": best_force["native"]["visible_drop"],
        "knee": best_force["native"]["max_knee_delta_rad"],
        "hip": best_force["native"]["max_hip_pitch_delta_rad"],
        "max_friction_ratio": best_force["force_audit"]["max_friction_ratio"],
        "min_cop_support_margin": best_force["force_audit"]["min_cop_support_margin"],
        "force_verdict": best_force["force_verdict"],
    }
    result["best_visible_candidate"] = {
        "attempt": best_visible["attempt"],
        "visible_drop": best_visible["native"]["visible_drop"],
        "knee": best_visible["native"]["max_knee_delta_rad"],
        "hip": best_visible["native"]["max_hip_pitch_delta_rad"],
        "fell_at": best_visible["native"]["fell_at"],
        "force_verdict": best_visible["force_verdict"],
    }
    result["verdict"] = "PASS_VISIBLE_8CM_GATE" if visible else "FAIL_VISIBLE_8CM_GATE"
    result["browser_replay_attempted"] = bool(visible)
    write_summary(result, out_dir)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_readme(result)
    print(result["verdict"], json.dumps({
        "best_force_feasible_no_fall": result["best_force_feasible_no_fall"],
        "best_visible_candidate": result["best_visible_candidate"],
        "browser_replay_attempted": result["browser_replay_attempted"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
