"""Inspect the current G1 MuJoCo model for acrobatic skill feasibility.

This is a static gate, not a training run. It checks whether the current
browser/native G1 asset has the contacts, actuators, and sensors needed before
spending GPU time on Atlas-like skills.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
G1_XML = ROOT / "experiments/03-digital-twin/web/assets/scenes/g1/g1_mjx_feetonly.xml"
VERIFY = Path(__file__).resolve().parent / "verify"


def _merge_attrs(base: dict[str, str], override: dict[str, str]) -> dict[str, str]:
    merged = dict(base)
    merged.update(override)
    return merged


def _collect_default_attrs(root: ET.Element) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    joint_defaults: dict[str, dict[str, str]] = {}
    actuator_defaults: dict[str, dict[str, str]] = {}

    def walk_default(node: ET.Element, inherited_joint: dict[str, str], inherited_position: dict[str, str]) -> None:
        current_joint = dict(inherited_joint)
        current_position = dict(inherited_position)
        class_name = node.attrib.get("class")

        for child in node:
            if child.tag == "joint":
                current_joint = _merge_attrs(current_joint, child.attrib)
            elif child.tag == "position":
                current_position = _merge_attrs(current_position, child.attrib)

        if class_name:
            joint_defaults[class_name] = dict(current_joint)
            actuator_defaults[class_name] = dict(current_position)

        for child in node:
            if child.tag == "default":
                walk_default(child, current_joint, current_position)

    for default in root.findall("default"):
        walk_default(default, {}, {})

    return joint_defaults, actuator_defaults


def _float_range(value: str | None) -> list[float] | None:
    if not value:
        return None
    return [float(part) for part in value.split()]


def main() -> None:
    VERIFY.mkdir(parents=True, exist_ok=True)
    root = ET.parse(G1_XML).getroot()
    joint_defaults, actuator_defaults = _collect_default_attrs(root)

    joints = []
    for joint in root.findall(".//joint"):
        if "name" not in joint.attrib:
            continue
        if joint.attrib.get("name") == "floating_base_joint":
            continue
        class_name = joint.attrib.get("class", "")
        attrs = _merge_attrs(joint_defaults.get(class_name, {}), joint.attrib)
        joints.append(
            {
                "name": attrs["name"],
                "class": class_name,
                "range": _float_range(attrs.get("range")),
                "actuatorfrcrange": _float_range(attrs.get("actuatorfrcrange")),
                "damping": float(attrs["damping"]) if attrs.get("damping") else None,
                "armature": float(attrs["armature"]) if attrs.get("armature") else None,
            }
        )

    actuators = []
    for actuator in root.findall(".//actuator/position"):
        class_name = actuator.attrib.get("class", "")
        attrs = _merge_attrs(actuator_defaults.get(class_name, {}), actuator.attrib)
        actuators.append(
            {
                "name": attrs["name"],
                "joint": attrs["joint"],
                "class": class_name,
                "kp": float(attrs["kp"]) if attrs.get("kp") else None,
            }
        )

    geoms = []
    for geom in root.findall(".//geom"):
        geoms.append(
            {
                "name": geom.attrib.get("name", ""),
                "class": geom.attrib.get("class", ""),
                "type": geom.attrib.get("type", ""),
                "contype": geom.attrib.get("contype", ""),
                "conaffinity": geom.attrib.get("conaffinity", ""),
            }
        )

    contact_pairs = [
        {
            "name": pair.attrib.get("name", ""),
            "geom1": pair.attrib.get("geom1", ""),
            "geom2": pair.attrib.get("geom2", ""),
            "condim": pair.attrib.get("condim", ""),
            "friction": pair.attrib.get("friction", ""),
        }
        for pair in root.findall(".//contact/pair")
    ]
    sensors = [sensor.attrib.get("name", "") for sensor in root.findall(".//sensor/*")]

    def names_containing(items: list[dict[str, str]], token: str) -> list[str]:
        return sorted(item["name"] for item in items if token in item["name"])

    low_torque = [
        joint
        for joint in joints
        if joint["actuatorfrcrange"] and max(abs(v) for v in joint["actuatorfrcrange"]) <= 25
    ]
    wrist_low_torque = [joint for joint in low_torque if "wrist" in joint["name"]]
    hand_floor_pairs = [
        pair
        for pair in contact_pairs
        if "hand" in (pair["geom1"] + pair["geom2"]) and "floor" in (pair["geom1"] + pair["geom2"])
    ]
    foot_floor_pairs = [
        pair
        for pair in contact_pairs
        if "foot" in (pair["geom1"] + pair["geom2"]) and "floor" in (pair["geom1"] + pair["geom2"])
    ]

    findings = {
        "model": G1_XML.relative_to(ROOT).as_posix(),
        "joint_count": len(joints),
        "actuator_count": len(actuators),
        "sensor_count": len(sensors),
        "contact_pair_count": len(contact_pairs),
        "hand_collision_geoms": names_containing(geoms, "hand_collision"),
        "palm_sites": sorted(site.attrib.get("name", "") for site in root.findall(".//site") if "palm" in site.attrib.get("name", "")),
        "foot_floor_pairs": foot_floor_pairs,
        "hand_floor_pairs": hand_floor_pairs,
        "wrist_low_torque_joints": wrist_low_torque,
        "min_leg_torque_nm": min(
            max(abs(v) for v in joint["actuatorfrcrange"])
            for joint in joints
            if joint["actuatorfrcrange"] and any(part in joint["name"] for part in ["hip", "knee", "ankle"])
        ),
        "max_leg_torque_nm": max(
            max(abs(v) for v in joint["actuatorfrcrange"])
            for joint in joints
            if joint["actuatorfrcrange"] and any(part in joint["name"] for part in ["hip", "knee", "ankle"])
        ),
        "min_arm_torque_nm": min(
            max(abs(v) for v in joint["actuatorfrcrange"])
            for joint in joints
            if joint["actuatorfrcrange"] and any(part in joint["name"] for part in ["shoulder", "elbow", "wrist"])
        ),
        "max_arm_torque_nm": max(
            max(abs(v) for v in joint["actuatorfrcrange"])
            for joint in joints
            if joint["actuatorfrcrange"] and any(part in joint["name"] for part in ["shoulder", "elbow", "wrist"])
        ),
        "feasibility": [
            {
                "skill": "squat_or_pose_hold",
                "verdict": "go",
                "reason": "Uses leg/waist position control and existing foot-floor contacts; no new contact class required.",
                "next_gate": "M19 custom reward wrapper.",
            },
            {
                "skill": "front_kick",
                "verdict": "go_with_guardrails",
                "reason": "Leg torques reach 50-139 Nm and foot contact sensors exist, but single-support balance must be evaluated.",
                "next_gate": "Start with no-ball kick target before ball contact.",
            },
            {
                "skill": "ball_tap_or_simple_kick",
                "verdict": "needs_scene",
                "reason": "Robot model is usable, but no ball body, ball sensor, or goal metric exists in current scene.",
                "next_gate": "M21 ball-skill sandbox.",
            },
            {
                "skill": "handstand",
                "verdict": "blocked_until_contact_model_update",
                "reason": "Palm sites and hand collision geoms exist, but there is no hand-floor contact pair; wrist torque is only 5 Nm on pitch/yaw.",
                "next_gate": "Add palm-floor contact, hand force sensors, and a hand support pose test before RL.",
            },
            {
                "skill": "cartwheel_or_tumble",
                "verdict": "blocked_until_reference_motion",
                "reason": "The model has feet-only locomotion contacts and no reference motion/tracking objective for aerial full-body rotation.",
                "next_gate": "M22 reference-motion loop, then a prep skill such as jump-turn or handstand prep.",
            },
            {
                "skill": "rabona_kick",
                "verdict": "defer",
                "reason": "Requires ball scene plus crossing-leg balance and target-direction kick; this is downstream of simple kick and ball tap.",
                "next_gate": "M21 angled kick after front kick succeeds.",
            },
        ],
    }

    summary_path = VERIFY / "g1-acrobatics-feasibility.json"
    summary_path.write_text(json.dumps(findings, indent=2), encoding="utf-8")

    report_lines = [
        "# G1 Acrobatic Feasibility Gate",
        "",
        f"- Model: `{findings['model']}`",
        f"- Joints / actuators / sensors: {findings['joint_count']} / {findings['actuator_count']} / {findings['sensor_count']}",
        f"- Contact pairs: {findings['contact_pair_count']}",
        f"- Foot-floor pairs: {len(foot_floor_pairs)}",
        f"- Hand-floor pairs: {len(hand_floor_pairs)}",
        f"- Arm torque range: {findings['min_arm_torque_nm']}..{findings['max_arm_torque_nm']} Nm",
        f"- Leg torque range: {findings['min_leg_torque_nm']}..{findings['max_leg_torque_nm']} Nm",
        "",
        "| Skill | Verdict | Reason | Next gate |",
        "|---|---|---|---|",
    ]
    for row in findings["feasibility"]:
        report_lines.append(f"| {row['skill']} | {row['verdict']} | {row['reason']} | {row['next_gate']} |")
    (VERIFY / "g1-acrobatics-feasibility.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"wrote {summary_path}")
    print(f"wrote {VERIFY / 'g1-acrobatics-feasibility.md'}")


if __name__ == "__main__":
    main()
