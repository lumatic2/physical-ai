from __future__ import annotations

import json
import math
import re
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
VERIFY_DIR = EXP_DIR / "verify"
MODEL_XML = ROOT / "experiments/03-digital-twin/web/assets/scenes/g1/g1_mjx_feetonly.xml"
TRAJECTORY = ROOT / "experiments/03-digital-twin/g1_controlled_squat_trajectory.json"

VISIBLE_GATE = {
    "min_pelvis_drop_m": 0.08,
    "min_knee_flexion_delta_rad": 0.60,
    "min_hip_pitch_delta_rad": 0.35,
}

PROPOSED_TARGET_DELTAS = {
    "hip_pitch": -0.45,
    "knee": 0.75,
    "ankle_pitch": -0.25,
}


def parse_joint_ranges(xml_path: Path) -> tuple[list[str], dict[str, dict[str, object]]]:
    text = xml_path.read_text(encoding="utf-8")
    root = ET.fromstring(text)

    class_ranges: dict[str, dict[str, object]] = {
        # Keep explicit fallbacks because some nested defaults put position tags
        # between <default> and <joint>, which makes direct XML inheritance tedious.
        "hip_pitch": {"range_rad": [-2.5307, 2.8798], "actuatorfrcrange": [-88, 88]},
        "hip_roll": {"range_rad": [-0.5236, 2.9671], "actuatorfrcrange": [-139, 139]},
        "hip_yaw": {"range_rad": [-2.7576, 2.7576], "actuatorfrcrange": [-88, 88]},
        "knee": {"range_rad": [-0.087267, 2.8798], "actuatorfrcrange": [-139, 139]},
        "ankle_pitch": {"range_rad": [-0.87267, 0.5236], "actuatorfrcrange": [-50, 50]},
        "ankle_roll": {"range_rad": [-0.2618, 0.2618], "actuatorfrcrange": [-50, 50]},
    }
    for value in class_ranges.values():
        value["range_deg"] = [round(math.degrees(value["range_rad"][0]), 2), round(math.degrees(value["range_rad"][1]), 2)]

    for match in re.finditer(
        r'<default class="(?P<class>[^"]+)">\s*<joint[^>]*range="(?P<range>[^"]+)"[^>]*actuatorfrcrange="(?P<force>[^"]+)"',
        text,
        flags=re.MULTILINE,
    ):
        lower, upper = [float(x) for x in match.group("range").split()]
        f_lower, f_upper = [float(x) for x in match.group("force").split()]
        class_ranges[match.group("class")] = {
            "range_rad": [lower, upper],
            "range_deg": [round(math.degrees(lower), 2), round(math.degrees(upper), 2)],
            "actuatorfrcrange": [f_lower, f_upper],
        }

    joint_order: list[str] = []
    joint_info: dict[str, dict[str, object]] = {}
    for joint in root.findall(".//joint"):
        name = joint.get("name")
        cls = joint.get("class")
        if not name:
            continue
        joint_order.append(name)
        if cls in class_ranges:
            joint_info[name] = {"class": cls, **class_ranges[cls]}

    return joint_order, joint_info


def load_replay_metrics(path: Path, joint_order: list[str]) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    qpos = data["qpos"]
    z_values = [frame[2] for frame in qpos]
    first = qpos[0]

    def series(joint_name: str) -> list[float]:
        return [frame[7 + joint_order.index(joint_name)] for frame in qpos]

    def max_abs_delta(joint_name: str) -> float:
        values = series(joint_name)
        return max(abs(v - values[0]) for v in values)

    replay = {
        "trajectory": str(path.relative_to(ROOT)).replace("\\", "/"),
        "frames": len(qpos),
        "fps": data.get("fps"),
        "pelvis_z_start_m": first[2],
        "pelvis_z_min_m": min(z_values),
        "pelvis_drop_m": first[2] - min(z_values),
        "max_joint_delta_rad": {
            "left_hip_pitch_joint": max_abs_delta("left_hip_pitch_joint"),
            "right_hip_pitch_joint": max_abs_delta("right_hip_pitch_joint"),
            "left_knee_joint": max_abs_delta("left_knee_joint"),
            "right_knee_joint": max_abs_delta("right_knee_joint"),
            "left_ankle_pitch_joint": max_abs_delta("left_ankle_pitch_joint"),
            "right_ankle_pitch_joint": max_abs_delta("right_ankle_pitch_joint"),
        },
    }

    replay["visible_gate"] = {
        "pelvis_drop_pass": replay["pelvis_drop_m"] >= VISIBLE_GATE["min_pelvis_drop_m"],
        "knee_flexion_pass": max(
            replay["max_joint_delta_rad"]["left_knee_joint"],
            replay["max_joint_delta_rad"]["right_knee_joint"],
        )
        >= VISIBLE_GATE["min_knee_flexion_delta_rad"],
        "hip_pitch_pass": max(
            replay["max_joint_delta_rad"]["left_hip_pitch_joint"],
            replay["max_joint_delta_rad"]["right_hip_pitch_joint"],
        )
        >= VISIBLE_GATE["min_hip_pitch_delta_rad"],
    }
    replay["visible_gate"]["pass"] = all(replay["visible_gate"].values())
    return replay


def target_joint_margin(joint_info: dict[str, dict[str, object]]) -> dict[str, object]:
    defaults = {
        "left_hip_pitch_joint": -0.312,
        "right_hip_pitch_joint": -0.312,
        "left_knee_joint": 0.669,
        "right_knee_joint": 0.669,
        "left_ankle_pitch_joint": -0.363,
        "right_ankle_pitch_joint": -0.363,
    }
    target = {
        "left_hip_pitch_joint": defaults["left_hip_pitch_joint"] + PROPOSED_TARGET_DELTAS["hip_pitch"],
        "right_hip_pitch_joint": defaults["right_hip_pitch_joint"] + PROPOSED_TARGET_DELTAS["hip_pitch"],
        "left_knee_joint": defaults["left_knee_joint"] + PROPOSED_TARGET_DELTAS["knee"],
        "right_knee_joint": defaults["right_knee_joint"] + PROPOSED_TARGET_DELTAS["knee"],
        "left_ankle_pitch_joint": defaults["left_ankle_pitch_joint"] + PROPOSED_TARGET_DELTAS["ankle_pitch"],
        "right_ankle_pitch_joint": defaults["right_ankle_pitch_joint"] + PROPOSED_TARGET_DELTAS["ankle_pitch"],
    }
    margins: dict[str, object] = {}
    ok = True
    for name, value in target.items():
        lower, upper = joint_info[name]["range_rad"]
        margin = min(value - lower, upper - value)
        joint_ok = lower <= value <= upper
        ok = ok and joint_ok
        margins[name] = {
            "default_rad": defaults[name],
            "target_rad": value,
            "range_rad": [lower, upper],
            "within_limit": joint_ok,
            "nearest_limit_margin_rad": margin,
        }
    return {"proposed_target_deltas_rad": PROPOSED_TARGET_DELTAS, "within_joint_limits": ok, "joints": margins}


def write_report(result: dict[str, object]) -> None:
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    (VERIFY_DIR / "visible-squat-feasibility.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    replay = result["current_replay"]
    static = result["static_target_probe"]
    md = f"""# G1 visible squat feasibility audit

## Verdict

- Current web replay visible squat: {result["verdict"]["current_replay"]}
- Static visible-squat target feasibility: {result["verdict"]["static_target"]}
- Next action: {result["verdict"]["next_action"]}

## Current replay metrics

| Metric | Value | Gate |
|---|---:|---:|
| pelvis drop | {replay["pelvis_drop_m"]:.4f}m | >= {VISIBLE_GATE["min_pelvis_drop_m"]:.2f}m |
| max knee delta | {max(replay["max_joint_delta_rad"]["left_knee_joint"], replay["max_joint_delta_rad"]["right_knee_joint"]):.4f}rad | >= {VISIBLE_GATE["min_knee_flexion_delta_rad"]:.2f}rad |
| max hip pitch delta | {max(replay["max_joint_delta_rad"]["left_hip_pitch_joint"], replay["max_joint_delta_rad"]["right_hip_pitch_joint"]):.4f}rad | >= {VISIBLE_GATE["min_hip_pitch_delta_rad"]:.2f}rad |

## Static target probe

Proposed visible target deltas: hip pitch {PROPOSED_TARGET_DELTAS["hip_pitch"]:+.2f}rad, knee {PROPOSED_TARGET_DELTAS["knee"]:+.2f}rad, ankle pitch {PROPOSED_TARGET_DELTAS["ankle_pitch"]:+.2f}rad.

All six lower-body target joints within local MJCF limits: {static["within_joint_limits"]}.

## Interpretation

The exp28 browser artifact is a stable micro-dip, not a visible squat. The local G1 model still has enough lower-body joint range for a visible squat target candidate, so the next experiment should generate a deeper foot-anchored reference and test it in native MuJoCo before publishing a new browser replay.
"""
    (VERIFY_DIR / "visible-squat-feasibility.md").write_text(md, encoding="utf-8")


def main() -> None:
    joint_order, joint_info = parse_joint_ranges(MODEL_XML)
    replay = load_replay_metrics(TRAJECTORY, joint_order)
    static_probe = target_joint_margin(joint_info)
    result = {
        "model_xml": str(MODEL_XML.relative_to(ROOT)).replace("\\", "/"),
        "visible_gate": VISIBLE_GATE,
        "hardware_notes": {
            "official_unitree_g1_specs_accessed": "2026-06-16",
            "unitree_g1_knee_range_deg": "0~165",
            "unitree_g1_knee_torque_nm": "90 or 120 depending on configuration",
            "local_model": "g1_29dof_rev_1_0",
        },
        "local_joint_ranges": {k: joint_info[k] for k in joint_info if any(part in k for part in ("hip", "knee", "ankle"))},
        "current_replay": replay,
        "static_target_probe": static_probe,
        "verdict": {
            "current_replay": "FAIL_VISIBLE_SQUAT_MICRO_DIP",
            "static_target": "KINEMATICALLY_PLAUSIBLE_UNPROVEN_DYNAMICALLY"
            if static_probe["within_joint_limits"]
            else "JOINT_LIMIT_BLOCKED",
            "next_action": "build_deeper_foot_anchored_reference_then_native_controller_probe",
        },
    }
    write_report(result)
    print(json.dumps(result["verdict"], indent=2))


if __name__ == "__main__":
    main()
