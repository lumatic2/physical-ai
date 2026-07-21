#!/usr/bin/env python3
"""Join both canonical policies on the frozen 60-key denominator."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
GEN1_DENOMINATOR = REPO_ROOT / "experiments" / "150-multitask-evaluation-contract" / "run-denominator.json"
OPENVLA_MANIFEST = (
    REPO_ROOT / "experiments" / "151-openvla-multitask-baseline" / "verify" / "canonical" / "manifest.json"
)
PI05_MANIFEST = HERE / "verify" / "canonical" / "pi05-manifest.json"
OUTPUT = HERE / "verify" / "paired-report.json"

REPORT_VERSION = "physical-ai-gen3-paired-statistics-v1"
POLICIES = ("openvla-libero", "pi05-libero")
SUITES = ("libero_spatial", "libero_object", "libero_goal")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class PairingError(ValueError):
    """Raised when a comparison can hide denominator or evidence drift."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def task_id(task_key: str) -> int:
    return int(task_key.rsplit("task-", 1)[1])


def pair_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return row["suite"], int(row["task_id"]), int(row["state_index"])


def pair_key_text(key: tuple[str, int, int]) -> str:
    suite, task, state = key
    return f"{suite}:task-{task:02d}:state-{state:02d}"


def expected_runs(denominator: dict[str, Any]) -> tuple[dict[str, set[str]], set[tuple[str, int, int]]]:
    if denominator.get("planned_run_count") != 120:
        raise PairingError("GEN1 denominator must contain 120 runs")
    by_policy = {policy: set() for policy in POLICIES}
    paired_keys: set[tuple[str, int, int]] = set()
    for run in denominator.get("runs", []):
        policy_id = run.get("policy", {}).get("policy_id")
        if policy_id not in by_policy:
            raise PairingError(f"unexpected denominator policy: {policy_id}")
        by_policy[policy_id].add(run["run_key"])
        paired_keys.add((run["suite"], task_id(run["task_key"]), int(run["state_index"])))
    if any(len(values) != 60 for values in by_policy.values()) or len(paired_keys) != 60:
        raise PairingError("GEN1 denominator is not 60 paired keys")
    return by_policy, paired_keys


def index_manifest(
    rows: list[dict[str, Any]], *, policy_id: str, outcome_field: str, expected_run_keys: set[str]
) -> dict[tuple[str, int, int], dict[str, Any]]:
    if len(rows) == 0:
        raise PairingError("zero denominator")
    if len(rows) != 60:
        raise PairingError(f"{policy_id} missing canonical cells: {60 - len(rows)}")
    run_keys = {row.get("run_key") for row in rows}
    if run_keys != expected_run_keys:
        raise PairingError(f"{policy_id} canonical run keys do not match GEN1")
    indexed: dict[tuple[str, int, int], dict[str, Any]] = {}
    for row in rows:
        key = pair_key(row)
        if key in indexed:
            raise PairingError(f"duplicate paired cell: {pair_key_text(key)}")
        outcome = row.get(outcome_field)
        if outcome not in {"success", "timeout"}:
            raise PairingError(f"invalid policy outcome: {pair_key_text(key)}")
        artifact_ref = row.get("artifact_ref")
        if not isinstance(artifact_ref, str) or Path(artifact_ref).is_absolute() or ".." in Path(artifact_ref).parts:
            raise PairingError(f"invalid canonical episode ref: {pair_key_text(key)}")
        if not HEX64.fullmatch(str(row.get("manifest_sha256", ""))):
            raise PairingError(f"invalid canonical manifest hash: {pair_key_text(key)}")
        indexed[key] = {
            "policy_id": policy_id,
            "outcome": outcome,
            "run_key": row["run_key"],
            "artifact_ref": artifact_ref,
            "manifest_sha256": row["manifest_sha256"],
        }
    return indexed


def percentile(values: list[float], probability: float) -> float:
    if not values:
        raise PairingError("zero denominator")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def bootstrap_interval(
    differences: list[int], *, seed: int = 20260721, resamples: int = 10_000
) -> dict[str, Any]:
    if not differences:
        raise PairingError("zero denominator")
    if resamples < 1_000:
        raise PairingError("bootstrap requires at least 1000 resamples")
    rng = random.Random(seed)
    count = len(differences)
    estimates = [
        sum(differences[rng.randrange(count)] for _ in range(count)) / count
        for _ in range(resamples)
    ]
    return {
        "method": "paired-nonparametric-bootstrap-percentile-type7",
        "confidence": 0.95,
        "seed": seed,
        "resamples": resamples,
        "lower": percentile(estimates, 0.025),
        "upper": percentile(estimates, 0.975),
    }


def count_block(rows: list[dict[str, Any]]) -> dict[str, Any]:
    denominator = len(rows)
    if denominator == 0:
        raise PairingError("zero denominator")
    open_success = sum(row["openvla"]["outcome"] == "success" for row in rows)
    pi_success = sum(row["pi05"]["outcome"] == "success" for row in rows)
    return {
        "denominator": denominator,
        "openvla_successes": open_success,
        "pi05_successes": pi_success,
        "difference_successes": pi_success - open_success,
        "openvla_success_rate": open_success / denominator,
        "pi05_success_rate": pi_success / denominator,
        "difference_rate": (pi_success - open_success) / denominator,
    }


def breakdown(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row)
    result = []
    for key in sorted(groups):
        identity = dict(zip(fields, key, strict=True))
        result.append({**identity, **count_block(groups[key])})
    return result


def contingency_block(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(
        (
            "openvla_success" if row["openvla"]["outcome"] == "success" else "openvla_non_success",
            "pi05_success" if row["pi05"]["outcome"] == "success" else "pi05_non_success",
        )
        for row in rows
    )
    return {
        "both_success": counts[("openvla_success", "pi05_success")],
        "pi05_only_success": counts[("openvla_non_success", "pi05_success")],
        "openvla_only_success": counts[("openvla_success", "pi05_non_success")],
        "both_non_success": counts[("openvla_non_success", "pi05_non_success")],
    }


def build_report(
    denominator: dict[str, Any], openvla_manifest: dict[str, Any], pi05_manifest: dict[str, Any]
) -> dict[str, Any]:
    expected_by_policy, expected_keys = expected_runs(denominator)
    open_index = index_manifest(
        openvla_manifest.get("cells", []),
        policy_id=POLICIES[0],
        outcome_field="outcome",
        expected_run_keys=expected_by_policy[POLICIES[0]],
    )
    pi_index = index_manifest(
        pi05_manifest.get("cells", []),
        policy_id=POLICIES[1],
        outcome_field="status",
        expected_run_keys=expected_by_policy[POLICIES[1]],
    )
    if set(open_index) != expected_keys or set(pi_index) != expected_keys:
        raise PairingError("unpaired canonical cell")
    pairs = []
    for key in sorted(expected_keys):
        suite, task, state = key
        pairs.append(
            {
                "paired_key": pair_key_text(key),
                "suite": suite,
                "task_id": task,
                "state_index": state,
                "openvla": open_index[key],
                "pi05": pi_index[key],
            }
        )
    overall = count_block(pairs)
    differences = [
        int(row["pi05"]["outcome"] == "success")
        - int(row["openvla"]["outcome"] == "success")
        for row in pairs
    ]
    return {
        "schema_version": REPORT_VERSION,
        "pass": True,
        "denominator": {
            "paired_keys": len(pairs),
            "suites": list(SUITES),
            "task_groups": 12,
            "source_sha256": hashlib.sha256(
                json.dumps(denominator, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        },
        "overall": overall,
        "paired_difference": {
            "direction": "pi05-libero minus openvla-libero",
            "success_numerator": overall["difference_successes"],
            "denominator": overall["denominator"],
            "rate": overall["difference_rate"],
            "bootstrap_95": bootstrap_interval(differences),
        },
        "contingency": contingency_block(pairs),
        "suites": breakdown(pairs, ("suite",)),
        "tasks": breakdown(pairs, ("suite", "task_id")),
        "pairs": pairs,
        "claim_boundary": (
            "Observed paired difference on the frozen 12-task, 5-state LIBERO slice; "
            "not a general policy winner, training effect, or real-robot claim."
        ),
    }


def validate_report(report: dict[str, Any]) -> None:
    if report.get("schema_version") != REPORT_VERSION or report.get("pass") is not True:
        raise PairingError("report identity drift")
    pairs = report.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise PairingError("zero denominator")
    if len(pairs) != 60 or len({row.get("paired_key") for row in pairs}) != 60:
        raise PairingError("unpaired or duplicate report rows")
    if {row.get("suite") for row in pairs} != set(SUITES):
        raise PairingError("Simpson-style suite omission")
    denominator = report.get("denominator", {})
    if (
        denominator.get("paired_keys") != 60
        or set(denominator.get("suites", [])) != set(SUITES)
        or denominator.get("task_groups") != 12
    ):
        raise PairingError("denominator summary drift")
    for row in pairs:
        for policy, expected_policy_id in (("openvla", POLICIES[0]), ("pi05", POLICIES[1])):
            evidence = row.get(policy, {})
            if evidence.get("policy_id") != expected_policy_id:
                raise PairingError("policy/source relabel")
            if evidence.get("outcome") not in {"success", "timeout"}:
                raise PairingError("invalid paired outcome")
            ref = evidence.get("artifact_ref")
            if not isinstance(ref, str) or Path(ref).is_absolute() or ".." in Path(ref).parts:
                raise PairingError("invalid paired episode ref")
            if not HEX64.fullmatch(str(evidence.get("manifest_sha256", ""))):
                raise PairingError("invalid paired manifest hash")
    expected_overall = count_block(pairs)
    if report.get("overall") != expected_overall:
        raise PairingError("overall raw counts are not recomputable")
    if report.get("contingency") != contingency_block(pairs):
        raise PairingError("paired contingency drift")
    difference = report.get("paired_difference", {})
    raw_fields = ("success_numerator", "denominator", "rate")
    if any(field not in difference for field in raw_fields):
        raise PairingError("rounded-only metric")
    if (
        difference["success_numerator"] != expected_overall["difference_successes"]
        or difference["denominator"] != expected_overall["denominator"]
        or difference["rate"] != expected_overall["difference_rate"]
    ):
        raise PairingError("paired difference drift")
    if report.get("suites") != breakdown(pairs, ("suite",)):
        raise PairingError("Simpson-style suite omission")
    if report.get("tasks") != breakdown(pairs, ("suite", "task_id")):
        raise PairingError("task breakdown omission")
    interval = difference.get("bootstrap_95", {})
    expected_interval = bootstrap_interval(
        [
            int(row["pi05"]["outcome"] == "success")
            - int(row["openvla"]["outcome"] == "success")
            for row in pairs
        ],
        seed=interval.get("seed", 20260721),
        resamples=interval.get("resamples", 10_000),
    )
    if interval != expected_interval:
        raise PairingError("bootstrap interval drift")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--denominator", type=Path, default=GEN1_DENOMINATOR)
    parser.add_argument("--openvla", type=Path, default=OPENVLA_MANIFEST)
    parser.add_argument("--pi05", type=Path, default=PI05_MANIFEST)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        report = build_report(load_json(args.denominator), load_json(args.openvla), load_json(args.pi05))
        validate_report(report)
    except (PairingError, FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        print(f"paired statistics gate: FAIL — {exc}")
        return 2
    report["sources"] = {
        "denominator": {"ref": str(args.denominator.relative_to(REPO_ROOT)).replace("\\", "/"), "sha256": sha256_file(args.denominator)},
        "openvla": {"ref": str(args.openvla.relative_to(REPO_ROOT)).replace("\\", "/"), "sha256": sha256_file(args.openvla)},
        "pi05": {"ref": str(args.pi05.relative_to(REPO_ROOT)).replace("\\", "/"), "sha256": sha256_file(args.pi05)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "paired statistics gate: PASS "
        f"(pairs={report['overall']['denominator']}, openvla={report['overall']['openvla_successes']}, "
        f"pi05={report['overall']['pi05_successes']}, difference={report['paired_difference']['rate']:.6f})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
