#!/usr/bin/env python3
"""Verify a same-contract OpenVLA/LIBERO PASS and FAIL evidence pair."""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

from verify_bounded_evidence import evaluate_evidence, run_rerun


SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMON_ROLLOUT_FIELDS = ("suite", "task_id", "environment_seed", "max_policy_steps")


def _action_links_valid(sidecar: dict[str, Any]) -> bool:
    events = sidecar.get("action_events")
    if not isinstance(events, list) or not events:
        return False
    for event in events:
        if not isinstance(event, dict):
            return False
        raw = event.get("raw_policy_action")
        if not isinstance(raw, list) or len(raw) != 7:
            return False
        action_hash = event.get("executed_action_sha256")
        if not isinstance(action_hash, str) or not SHA256.fullmatch(action_hash):
            return False
    return True


def evaluate_pair(
    *,
    pass_sidecar: dict[str, Any],
    fail_sidecar: dict[str, Any],
    pass_evidence: dict[str, Any],
    fail_evidence: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    for label, evidence in (("pass", pass_evidence), ("fail", fail_evidence)):
        if not evidence.get("pass") or not evidence.get("producer_claim_ready"):
            errors.append(f"{label} individual evidence gate failed")

    pass_outcome = pass_sidecar.get("outcome", {})
    fail_outcome = fail_sidecar.get("outcome", {})
    if pass_outcome.get("success") is not True or pass_outcome.get("termination") != "success":
        errors.append("PASS outcome must be success=true and termination=success")
    if fail_outcome.get("success") is not False or fail_outcome.get("termination") != "timeout":
        errors.append("FAIL outcome must be success=false and termination=timeout")

    pass_rollout = pass_sidecar.get("rollout", {})
    fail_rollout = fail_sidecar.get("rollout", {})
    if not isinstance(pass_rollout, dict) or not isinstance(fail_rollout, dict):
        errors.append("both episodes require rollout provenance")
        pass_rollout, fail_rollout = {}, {}
    for field in COMMON_ROLLOUT_FIELDS:
        if pass_rollout.get(field) != fail_rollout.get(field):
            errors.append(f"rollout contract mismatch: {field}")
    if pass_rollout.get("init_state_index") == fail_rollout.get("init_state_index"):
        errors.append("PASS and FAIL must identify different init-state indexes")

    pass_producer = pass_sidecar.get("producer")
    fail_producer = fail_sidecar.get("producer")
    if pass_producer != fail_producer:
        errors.append("producer revision contract mismatch")
    if pass_sidecar.get("episode", {}).get("revision") != fail_sidecar.get("episode", {}).get("revision"):
        errors.append("dataset revision contract mismatch")

    max_policy_steps = fail_rollout.get("max_policy_steps")
    fail_action_count = len(fail_sidecar.get("action_events", []))
    if not isinstance(max_policy_steps, int) or max_policy_steps < 1:
        errors.append("max_policy_steps must be a positive integer")
    elif fail_action_count != max_policy_steps:
        errors.append("FAIL must consume the full policy horizon")

    if not _action_links_valid(pass_sidecar):
        errors.append("PASS raw-to-executed action links are incomplete")
    if not _action_links_valid(fail_sidecar):
        errors.append("FAIL raw-to-executed action links are incomplete")

    return {
        "pass": not errors,
        "contract": {
            "rollout": {field: pass_rollout.get(field) for field in COMMON_ROLLOUT_FIELDS},
            "pass_init_state_index": pass_rollout.get("init_state_index"),
            "fail_init_state_index": fail_rollout.get("init_state_index"),
            "producer": copy.deepcopy(pass_producer),
            "dataset_revision": pass_sidecar.get("episode", {}).get("revision"),
        },
        "outcomes": {"pass": pass_outcome, "fail": fail_outcome},
        "frames": {
            "pass": len(pass_sidecar.get("action_events", [])),
            "fail": fail_action_count,
        },
        "hashes": {
            "pass": copy.deepcopy(pass_evidence.get("hashes", {})),
            "fail": copy.deepcopy(fail_evidence.get("hashes", {})),
        },
        "individual_gates": {
            "pass": bool(pass_evidence.get("pass")),
            "fail": bool(fail_evidence.get("pass")),
        },
        "claim_boundary": "recorded OpenVLA inference in LIBERO simulation; not real or live telemetry",
        "errors": errors,
    }


def _individual_evidence(
    *,
    dataset_root: Path,
    sidecar_path: Path,
    rrd_path: Path,
    rerun_cli: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    expected_frames = len(sidecar.get("action_events", []))
    rrd_verified, rrd_stats = run_rerun(rrd_path, rerun_cli)
    evidence = evaluate_evidence(
        dataset_root=dataset_root,
        sidecar_path=sidecar_path,
        rrd_path=rrd_path,
        expected_frames=expected_frames,
        producer_kind="openvla-libero",
        rrd_verified=rrd_verified,
        rrd_stats=rrd_stats,
    )
    return sidecar, evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for label in ("pass", "fail"):
        parser.add_argument(f"--{label}-dataset-root", type=Path, required=True)
        parser.add_argument(f"--{label}-sidecar", type=Path, required=True)
        parser.add_argument(f"--{label}-rrd", type=Path, required=True)
    parser.add_argument("--rerun-cli", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    pass_sidecar, pass_evidence = _individual_evidence(
        dataset_root=args.pass_dataset_root,
        sidecar_path=args.pass_sidecar,
        rrd_path=args.pass_rrd,
        rerun_cli=args.rerun_cli,
    )
    fail_sidecar, fail_evidence = _individual_evidence(
        dataset_root=args.fail_dataset_root,
        sidecar_path=args.fail_sidecar,
        rrd_path=args.fail_rrd,
        rerun_cli=args.rerun_cli,
    )
    report = evaluate_pair(
        pass_sidecar=pass_sidecar,
        fail_sidecar=fail_sidecar,
        pass_evidence=pass_evidence,
        fail_evidence=fail_evidence,
    )
    report["episodes"] = {"pass": pass_evidence, "fail": fail_evidence}
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
