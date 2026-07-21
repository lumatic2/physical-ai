#!/usr/bin/env python3
"""Verify the explicit OpenVLA/π0.5 adapter boundary before paired rollouts."""

from __future__ import annotations

import argparse
from collections import Counter
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
GEN1_DIR = REPO_ROOT / "experiments" / "150-multitask-evaluation-contract"
GEN2_REPORT = REPO_ROOT / "experiments" / "151-openvla-multitask-baseline" / "verify" / "baseline-report.json"
DEFAULT_CONTRACT = HERE / "shared-adapter-contract.json"
DEFAULT_OUTPUT = HERE / "verify" / "adapter-parity-report.json"
REPORT_VERSION = "physical-ai-gen3-adapter-parity-report-v1"
POLICY_IDS = ("openvla-libero", "pi05-libero")


class AdapterParityError(ValueError):
    """Raised when a policy difference is hidden or relabeled."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def adapter_revision(policy: dict[str, Any]) -> str:
    return canonical_hash(
        {"implementation": policy["implementation"], "inputs": policy["inputs"], "outputs": policy["outputs"]}
    )


def policies_by_id(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    policies = {policy.get("policy_id"): policy for policy in registry.get("policies", [])}
    if set(policies) != set(POLICY_IDS):
        raise AdapterParityError(f"policy set mismatch: {sorted(policies)}")
    return policies


def model_input_roles(policy: dict[str, Any]) -> tuple[list[str], list[str]]:
    inputs = policy["inputs"]
    mapping = {
        "instruction": inputs["instruction"].get("model_input") is True,
        "main_camera": inputs["main_camera"].get("model_input") is True,
        "wrist_camera": inputs["wrist_camera"].get("model_input") is True,
        "robot_state_8d": inputs["robot_state"].get("model_input") is True,
    }
    model_inputs = sorted(role for role, used in mapping.items() if used)
    observer_only = sorted(role for role, used in mapping.items() if not used)
    return model_inputs, observer_only


def validate_denominator(denominator: dict[str, Any]) -> dict[str, Any]:
    groups: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    for run in denominator.get("runs", []):
        key = (str(run.get("suite")), str(run.get("task_key")), int(run.get("state_index", -1)))
        groups[key].add(str(run.get("policy", {}).get("policy_id")))
    errors = []
    for key, policies in groups.items():
        if policies != set(POLICY_IDS):
            errors.append(f"unpaired denominator key: {key}")
    if len(groups) != 60 or len(denominator.get("runs", [])) != 120:
        errors.append(f"expected 60 pairs/120 runs, got {len(groups)}/{len(denominator.get('runs', []))}")
    if errors:
        raise AdapterParityError("; ".join(errors))
    return {
        "paired_keys": len(groups),
        "runs": len(denominator["runs"]),
        "suite_pairs": dict(Counter(key[0] for key in groups)),
    }


def validate_adapter_contract(
    contract: dict[str, Any], registry: dict[str, Any], denominator: dict[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []
    if contract.get("schema_version") != "physical-ai-gen3-shared-policy-adapter-v1":
        errors.append("adapter contract schema mismatch")
    common_observation = contract.get("common_observation", {})
    if common_observation.get("captured_fields") != [
        "main_camera",
        "wrist_camera",
        "robot_state_8d",
        "instruction",
    ]:
        errors.append("common observation fields changed")
    if common_observation.get("camera_roles") != {
        "main_camera": "agentview_image",
        "wrist_camera": "robot0_eye_in_hand_image",
    }:
        errors.append("camera source relabel")
    common_result = contract.get("common_result", {})
    if common_result.get("environment_action_semantics") != registry.get("common_result_contract", {}).get(
        "action_semantics"
    ):
        errors.append("environment action semantics drift")
    if common_result.get("executed_action_dim") != 7:
        errors.append("executed action dimension drift")
    if common_result.get("timing_fields") != [
        "request_count",
        "request_total_ms",
        "request_minimum_ms",
        "request_maximum_ms",
    ]:
        errors.append("timing fields incomplete")

    policies = policies_by_id(registry)
    expected_transforms = {
        "openvla-libero": {
            "input": ["main_camera:AutoProcessor"],
            "controller": ["gripper:normalize_0_1_to_sign", "gripper:invert_for_LIBERO"],
            "raw_shape": [7],
            "executed_shape": [1, 7],
            "replan": 1,
        },
        "pi05-libero": {
            "input": [
                "main_camera:rotate_180",
                "main_camera:resize_with_pad_224",
                "wrist_camera:rotate_180",
                "wrist_camera:resize_with_pad_224",
                "robot_state_8d:pad_to_model_dim_32",
            ],
            "controller": ["action:take_first_7_dimensions"],
            "raw_shape": [10, 32],
            "executed_shape": [10, 7],
            "replan": 5,
        },
    }
    rows = []
    for policy_id in POLICY_IDS:
        policy = policies[policy_id]
        spec = contract.get("policies", {}).get(policy_id, {})
        model_inputs, observer_only = model_input_roles(policy)
        if sorted(spec.get("model_inputs", [])) != model_inputs:
            errors.append(f"{policy_id}: model input relabel")
        if sorted(spec.get("observer_only", [])) != observer_only:
            errors.append(f"{policy_id}: observer-only relabel")
        expected = expected_transforms[policy_id]
        if spec.get("input_transforms") != expected["input"]:
            errors.append(f"{policy_id}: hidden input transform or transform order drift")
        if spec.get("controller_transforms") != expected["controller"]:
            errors.append(f"{policy_id}: sign/scale or controller transform drift")
        if spec.get("raw_output", {}).get("shape") != expected["raw_shape"]:
            errors.append(f"{policy_id}: raw action shape drift")
        if spec.get("executed_chunk_shape") != expected["executed_shape"]:
            errors.append(f"{policy_id}: executed action shape drift")
        if spec.get("replan_steps") != expected["replan"]:
            errors.append(f"{policy_id}: replanning cadence drift")
        rows.append(
            {
                "policy_id": policy_id,
                "adapter_revision": adapter_revision(policy),
                "model_inputs": model_inputs,
                "observer_only": observer_only,
                "input_transforms": spec.get("input_transforms"),
                "controller_transforms": spec.get("controller_transforms"),
                "raw_output_shape": spec.get("raw_output", {}).get("shape"),
                "executed_chunk_shape": spec.get("executed_chunk_shape"),
                "replan_steps": spec.get("replan_steps"),
            }
        )
    if errors:
        raise AdapterParityError("; ".join(dict.fromkeys(errors)))
    denominator_report = validate_denominator(denominator)
    return {
        "contract_sha256": canonical_hash(contract),
        "environment_revision": registry["environment"]["revision"],
        "denominator": denominator_report,
        "adapters": rows,
    }


def build_report() -> dict[str, Any]:
    contract = load_json(DEFAULT_CONTRACT)
    registry = load_json(GEN1_DIR / "policy-registry.json")
    denominator = load_json(GEN1_DIR / "run-denominator.json")
    parity = validate_adapter_contract(contract, registry, denominator)
    baseline = load_json(GEN2_REPORT)
    pi05_probe = load_json(HERE / "verify" / "pi05-probe-report.json")
    if baseline.get("overall", {}).get("denominator") != 60:
        raise AdapterParityError("GEN2 OpenVLA baseline denominator is not 60")
    if not pi05_probe.get("pass") or pi05_probe.get("output", {}).get("shape") != [10, 7]:
        raise AdapterParityError("π0.5 actual compatibility evidence missing")
    return {
        "schema_version": REPORT_VERSION,
        "pass": True,
        **parity,
        "actual_evidence": {
            "openvla": {
                "terminal_rollouts": 60,
                "report": "../151-openvla-multitask-baseline/verify/baseline-report.json",
            },
            "pi05": {"compatibility_probes": 1, "report": "verify/pi05-probe-report.json"},
        },
        "held_constant": contract["fairness_boundary"]["held_constant"],
        "policy_specific_and_exposed": contract["fairness_boundary"]["policy_specific_and_exposed"],
        "claim_boundary": contract["claim_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="GEN3 shared policy adapter parity gate")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = build_report()
    except (AdapterParityError, FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        print(f"adapter parity: FAIL — {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "adapter parity: PASS "
        f"({report['denominator']['paired_keys']} pairs, {len(report['adapters'])} explicit adapters)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
