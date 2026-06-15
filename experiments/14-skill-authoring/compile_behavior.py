"""Compile behavior specs into lightweight train/eval config stubs.

The compiler intentionally does not create a full RL environment. It turns a
versioned behavior spec into a deterministic contract that later M19/M21/M22
experiments can consume.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "behavior_spec.schema.json"
EXAMPLES = ROOT / "examples"
VERIFY = ROOT / "verify"


REQUIRED = ["schema_version", "id", "embodiment", "skill", "objective", "target", "constraints", "metrics"]
ALLOWED_EMBODIMENTS = {"g1", "go1", "spot", "barkour"}
ALLOWED_OBJECTIVE_TYPES = {"hold_pose", "transition_pose", "strike_target", "move_object", "track_reference"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED:
        if key not in spec:
            errors.append(f"missing required key: {key}")
    if spec.get("schema_version") != "0.1":
        errors.append("schema_version must be 0.1")
    if spec.get("embodiment") not in ALLOWED_EMBODIMENTS:
        errors.append(f"unsupported embodiment: {spec.get('embodiment')}")
    objective = spec.get("objective", {})
    if not isinstance(objective, dict) or objective.get("type") not in ALLOWED_OBJECTIVE_TYPES:
        errors.append(f"unsupported objective.type: {objective.get('type') if isinstance(objective, dict) else objective}")
    constraints = spec.get("constraints", {})
    if not isinstance(constraints, dict):
        errors.append("constraints must be an object")
    else:
        if constraints.get("no_fall") is not True:
            errors.append("constraints.no_fall must be true for skill-lab specs")
        if float(constraints.get("max_time_s", 0)) <= 0:
            errors.append("constraints.max_time_s must be > 0")
    metrics = spec.get("metrics", [])
    if not isinstance(metrics, list) or not metrics:
        errors.append("metrics must be a non-empty list")
    return errors


def compile_spec(spec: dict[str, Any]) -> dict[str, Any]:
    objective_type = spec["objective"]["type"]
    reward_terms = spec.get("training", {}).get("reward_terms", [])
    preferred_method = spec.get("training", {}).get("preferred_method", "rl")
    return {
        "compiled_schema_version": "0.1",
        "source_behavior_id": spec["id"],
        "embodiment": spec["embodiment"],
        "skill": spec["skill"],
        "objective_type": objective_type,
        "preferred_method": preferred_method,
        "scene_requirements": scene_requirements(spec),
        "reward_terms": reward_terms,
        "eval_metrics": spec["metrics"],
        "done_conditions": {
            "max_time_s": spec["constraints"]["max_time_s"],
            "fall_terminates": spec["constraints"]["no_fall"],
            "min_base_height_m": spec["constraints"].get("min_base_height_m")
        },
        "raw_target": spec["target"]
    }


def scene_requirements(spec: dict[str, Any]) -> list[str]:
    requirements = ["g1_mjx_feetonly.xml" if spec["embodiment"] == "g1" else "existing_policy_scene"]
    if spec["objective"]["type"] == "move_object":
        requirements.extend(["ball_body", "ball_velocity_sensor", "goal_direction_metric"])
    if spec["skill"] == "handstand_prep":
        requirements.extend(["palm_floor_contact_pair", "hand_force_sensor"])
    if spec["objective"]["type"] == "track_reference":
        requirements.append("reference_motion_file")
    return requirements


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("specs", nargs="*", type=Path, help="Spec files to compile. Defaults to examples/*.json")
    parser.add_argument("--out", type=Path, default=VERIFY)
    args = parser.parse_args()

    schema = load_json(SCHEMA_PATH)
    specs = args.specs or sorted(EXAMPLES.glob("*.json"))
    args.out.mkdir(parents=True, exist_ok=True)

    summary = {
        "schema": str(SCHEMA_PATH.relative_to(ROOT)),
        "schema_title": schema.get("title"),
        "compiled": [],
        "failed": []
    }
    for path in specs:
        spec = load_json(path)
        errors = validate_spec(spec)
        if errors:
            summary["failed"].append({"path": str(path), "errors": errors})
            continue
        compiled = compile_spec(spec)
        out_path = args.out / f"{spec['id']}.compiled.json"
        out_path.write_text(json.dumps(compiled, indent=2), encoding="utf-8")
        summary["compiled"].append({"path": rel(path), "out": rel(out_path), "id": spec["id"]})

    summary_path = args.out / "compile-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"compiled={len(summary['compiled'])} failed={len(summary['failed'])}")
    print(f"wrote {summary_path}")
    if summary["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
