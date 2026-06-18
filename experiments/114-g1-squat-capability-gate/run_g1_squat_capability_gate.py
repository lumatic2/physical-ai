from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
VERIFY_DIR = EXP_DIR / "verify"


PUBLIC_SOURCES = [
    {
        "source": "Unitree G1 controls documentation",
        "url": "https://docs.quadruped.de/projects/g1/html/operation_1.2.html",
        "accessed": "2026-06-18",
        "claim": "G1 has a Squat Mode, but it is described as a slow transition to squat with no balance control.",
        "implication": "stock Squat Mode proves a posture path exists, not an autonomous balanced squat skill.",
    },
    {
        "source": "Unitree G1 overview documentation",
        "url": "https://www.docs.quadruped.de/projects/g1/html/g1_overview.html",
        "accessed": "2026-06-18",
        "claim": "G1 has six degrees of freedom per leg and the basic model has 23 total DoF; EDU can expand with additional DoF.",
        "implication": "leg morphology is not an obvious blocker for squat-like posture control.",
    },
    {
        "source": "IEEE Robots Guide: Unitree G1",
        "url": "https://robotsguide.com/robots/unitree-g1",
        "accessed": "2026-06-18",
        "claim": "The guide shows a Unitree G1 in a deep squat posture and describes high flexibility.",
        "implication": "public visual evidence supports kinematic deep squat feasibility.",
    },
    {
        "source": "G1 Moves dataset",
        "url": "https://huggingface.co/datasets/exptech/g1-moves",
        "accessed": "2026-06-18",
        "claim": "The dataset provides 60 G1 EDU 29-DOF motion clips with retargeted trajectories, RL training data, and ONNX policies.",
        "implication": "learned G1 full-body motion tracking is a practical route, but scene/policy parity matters.",
    },
    {
        "source": "UniTracker paper",
        "url": "https://arxiv.org/html/2507.07356v2",
        "accessed": "2026-06-18",
        "claim": "A 29-DoF Unitree G1 tracks over 8,100 diverse motions with a unified whole-body policy.",
        "implication": "G1-class hardware can track rich whole-body motions when the tracker and dynamics stack are aligned.",
    },
    {
        "source": "Isaac Lab issue #3751",
        "url": "https://github.com/isaac-sim/IsaacLab/issues/3751",
        "accessed": "2026-06-18",
        "claim": "A trained G1 policy can collapse immediately when exported and run against a mismatched MuJoCo model.",
        "implication": "our ONNX/native failures are consistent with model-scene-action mismatch, not proof that squat is impossible.",
    },
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_prior_evidence() -> dict[str, Any]:
    static = read_json(ROOT / "experiments/43-g1-public-squat-feasibility/verify/public-squat-feasibility.json")
    latest = read_json(ROOT / "experiments/113-g1-terminal-stand-idqp-mpc-assist/verify/result.json")
    return {
        "static_feasibility": {
            "verdict": static["verdict"],
            "best_static_probe": max(
                static["static_probes"],
                key=lambda p: (
                    int(p["visible_gate"]["pelvis_drop_pass"])
                    + int(p["visible_gate"]["knee_delta_pass"])
                    + int(p["visible_gate"]["hip_pitch_delta_pass"]),
                    p["drop_m"],
                ),
            ),
        },
        "latest_native": {
            "verdict": latest["verdict"],
            "browser_replay_attempted": latest["browser_replay_attempted"],
            "best_terminal_idqp": latest["best_terminal_idqp"],
            "best_visible_geometry": latest["best_visible_geometry"],
        },
    }


def judge(public_sources: list[dict[str, str]], prior: dict[str, Any]) -> dict[str, Any]:
    posture_supported = any("Squat Mode" in item["claim"] for item in public_sources)
    kinematics_supported = (
        prior["static_feasibility"]["verdict"]["local_static"] == "KINEMATICALLY_PLAUSIBLE"
        and prior["static_feasibility"]["best_static_probe"]["visible_gate"]["pelvis_drop_pass"]
        and prior["static_feasibility"]["best_static_probe"]["visible_gate"]["knee_delta_pass"]
        and prior["static_feasibility"]["best_static_probe"]["visible_gate"]["hip_pitch_delta_pass"]
    )
    tracker_supported = any("ONNX policies" in item["claim"] or "8,100" in item["claim"] for item in public_sources)
    native_pass = prior["latest_native"]["verdict"] == "PASS_VISIBLE_8CM_GATE"

    if posture_supported and kinematics_supported and tracker_supported and not native_pass:
        verdict = "CAPABLE_IN_PRINCIPLE__CURRENT_CONTROLLER_FAILS"
        next_action = "upstream_tracker_scene_parity_first_then_full_order_idqp_mpc"
    elif native_pass:
        verdict = "CAPABLE_AND_CURRENT_CONTROLLER_PASSES"
        next_action = "attempt_browser_replay"
    else:
        verdict = "INSUFFICIENT_CAPABILITY_EVIDENCE"
        next_action = "collect_more_public_and_static_evidence"

    return {
        "posture_supported": posture_supported,
        "kinematics_supported": kinematics_supported,
        "tracker_supported": tracker_supported,
        "native_pass": native_pass,
        "verdict": verdict,
        "next_action": next_action,
    }


def write_summary(result: dict[str, Any]) -> None:
    best_static = result["prior_evidence"]["static_feasibility"]["best_static_probe"]
    best_native = result["prior_evidence"]["latest_native"]["best_terminal_idqp"]
    best_visible = result["prior_evidence"]["latest_native"]["best_visible_geometry"]
    lines = [
        "# G1 squat capability gate summary",
        "",
        f"Verdict: `{result['decision']['verdict']}`",
        f"Next action: `{result['decision']['next_action']}`",
        "",
        "## Public evidence",
    ]
    for source in result["public_sources"]:
        lines.append(f"- {source['source']} ({source['url']}, accessed {source['accessed']}): {source['implication']}")
    lines.extend(
        [
            "",
            "## Local evidence",
            f"- Static best: drop {best_static['drop_m']:.2f}m, foot error {best_static['ik_max_foot_error_m']:.4f}m, knee {best_static['knee_delta_rad']:.3f}rad, hip {best_static['hip_pitch_delta_rad']:.3f}rad.",
            f"- Latest stable native: `{best_native['attempt']}` drop {best_native['visible_drop']:.4f}m, knee {best_native['max_knee_delta_rad']:.3f}rad, hip {best_native['max_hip_pitch_delta_rad']:.3f}rad, contact {best_native['foot_contact_ratio']:.2f}, slip {best_native['foot_slip_distance']:.3f}m, return {best_native['return_to_stand']}.",
            f"- Latest visible native branch: `{best_visible['attempt']}` reached large drop but verdict `{best_visible['visible_verdict']}` with fall at {best_visible['fell_at']}s.",
            "",
            "## Interpretation",
            "- The robot appears capable of squat-like postures and full-body tracking in principle.",
            "- The stock Squat Mode is explicitly not a balanced autonomous squat skill.",
            "- The current M19 controller stack still fails the exp29 native visible gate, so browser replay is intentionally not attempted.",
        ]
    )
    (VERIFY_DIR / "capability-gate-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    prior = load_prior_evidence()
    result = {
        "gate": "g1_squat_capability_before_next_native_experiment",
        "visible_gate": {
            "pelvis_drop_m": 0.08,
            "knee_delta_rad": 0.60,
            "hip_pitch_delta_rad": 0.35,
        },
        "public_sources": PUBLIC_SOURCES,
        "prior_evidence": prior,
    }
    result["decision"] = judge(PUBLIC_SOURCES, prior)
    (VERIFY_DIR / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_summary(result)
    print(json.dumps(result["decision"], indent=2))


if __name__ == "__main__":
    main()
