#!/usr/bin/env python3
"""Execute the frozen 60-cell π0.5 denominator with one persistent policy server."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
GEN1_DIR = REPO_ROOT / "experiments" / "150-multitask-evaluation-contract"
GEN2_DIR = REPO_ROOT / "experiments" / "151-openvla-multitask-baseline"
for dependency in (GEN2_DIR,):
    if str(dependency) not in sys.path:
        sys.path.insert(0, str(dependency))

from pi05_evidence import (  # noqa: E402
    Pi05EvidenceError,
    atomic_write_manifest,
    seal_pi05_episode,
)
from run_ledger import (  # noqa: E402
    LedgerContractError,
    RunLedger,
)
from verify_adapter_parity import adapter_revision  # noqa: E402

POLICY_ID = "pi05-libero"
PI05_REVISION = "11e0f560ebc9ca0f65d26241dd08e2ac07c22ee91455f1789afc2fc5c0378d7b"
SUITE_ORDER = ("libero_spatial", "libero_object", "libero_goal")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def task_id_from_key(task_key: str) -> int:
    try:
        return int(task_key.rsplit("task-", 1)[1])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"invalid task key: {task_key}") from exc


def load_pi05_contract() -> dict[str, Any]:
    registry = load_json(GEN1_DIR / "policy-registry.json")
    denominator = load_json(GEN1_DIR / "run-denominator.json")
    manifest = load_json(GEN1_DIR / "benchmark-manifest.json")
    runner = load_json(GEN2_DIR / "runner-config.json")
    policy = next(item for item in registry["policies"] if item["policy_id"] == POLICY_ID)
    expected_adapter = adapter_revision(policy)
    tasks = {(task["suite"], int(task["task_id"])): task for task in manifest["tasks"]}
    suite_rank = {suite: index for index, suite in enumerate(SUITE_ORDER)}
    cells = []
    errors = []
    for run in denominator["runs"]:
        if run["policy"]["policy_id"] != POLICY_ID:
            continue
        task_id = task_id_from_key(run["task_key"])
        key = (run["suite"], task_id)
        if key not in tasks:
            errors.append(f"task outside GEN1 manifest: {key}")
        if run["policy"]["artifact_revision"] != PI05_REVISION:
            errors.append(f"checkpoint drift: {run['run_key']}")
        if run["policy"]["adapter_revision"] != expected_adapter:
            errors.append(f"adapter drift: {run['run_key']}")
        cells.append(
            {
                "run_key": run["run_key"],
                "suite": run["suite"],
                "task_id": task_id,
                "state_index": int(run["state_index"]),
                "instruction": tasks.get(key, {}).get("language_instruction"),
                "environment_revision": run["environment_revision"],
                "checkpoint_revision": PI05_REVISION,
                "adapter_revision": expected_adapter,
            }
        )
    cells.sort(key=lambda cell: (suite_rank[cell["suite"]], cell["task_id"], cell["state_index"]))
    if len(cells) != 60 or len({cell["run_key"] for cell in cells}) != 60:
        errors.append(f"expected 60 unique π0.5 cells, got {len(cells)}")
    if any(not cell["instruction"] for cell in cells):
        errors.append("cell instruction missing")
    if errors:
        raise ValueError("; ".join(errors))
    return {"cells": cells, "max_policy_steps": runner["max_policy_steps"], "seed": int(runner["seed"])}


def wait_port(port: int, timeout_s: float, process: subprocess.Popen[Any]) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            connection.settimeout(0.5)
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(1.0)
    return False


def cell_slug(cell: dict[str, Any]) -> str:
    return f"{cell['suite']}-task-{cell['task_id']:02d}-state-{cell['state_index']:02d}"


def dataset_revision(run_key: str) -> str:
    return hashlib.sha256(run_key.encode("utf-8")).hexdigest()


def client_command(
    cell: dict[str, Any], contract: dict[str, Any], attempt_root: Path, python: str, port: int
) -> list[str]:
    return [
        python,
        "-u",
        str(HERE / "pi05_client.py"),
        "--suite",
        cell["suite"],
        "--task-id",
        str(cell["task_id"]),
        "--state-index",
        str(cell["state_index"]),
        "--seed",
        str(contract["seed"]),
        "--max-policy-steps",
        str(contract["max_policy_steps"][cell["suite"]]),
        "--port",
        str(port),
        "--record-root",
        str(attempt_root / "dataset"),
        "--record-repo-id",
        f"physical-ai/gen3-{cell_slug(cell)}",
        "--dataset-revision",
        dataset_revision(cell["run_key"]),
        "--environment-revision",
        cell["environment_revision"],
    ]


def write_error(root: Path, cell: dict[str, Any], attempt_id: str, kind: str, detail: str) -> str:
    relative = Path("errors") / cell_slug(cell) / f"attempt-{attempt_id}.json"
    path = root / relative
    payload = {
        "schema_version": "physical-ai-gen3-infrastructure-error-v1",
        "run_key": cell["run_key"],
        "attempt_id": attempt_id,
        "kind": kind,
        "detail": detail[-4000:],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return relative.as_posix()


def execute_cell(
    cell: dict[str, Any],
    contract: dict[str, Any],
    ledger: RunLedger,
    artifact_root: Path,
    client_python: str,
    client_env: dict[str, str],
    port: int,
) -> bool:
    recover = cell["run_key"] in ledger.state().active
    attempt = ledger.begin_attempt(cell["run_key"], recover_active=recover)
    attempt_id = attempt["attempt_id"]
    relative = Path("episodes") / cell_slug(cell) / f"attempt-{attempt_id}"
    attempt_root = artifact_root / relative
    attempt_root.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            client_command(cell, contract, attempt_root, client_python, port),
            cwd=REPO_ROOT,
            env=client_env,
            text=True,
            capture_output=True,
            timeout=1800,
        )
    except subprocess.TimeoutExpired as exc:
        error_ref = write_error(artifact_root, cell, attempt_id, "client-timeout", str(exc))
        ledger.record_infrastructure_error(cell["run_key"], attempt_id, error_ref)
        return False
    log = completed.stdout + completed.stderr
    (attempt_root / "client.log").write_text(log, encoding="utf-8")
    if completed.returncode:
        error_ref = write_error(artifact_root, cell, attempt_id, "client-exit", log)
        ledger.record_infrastructure_error(cell["run_key"], attempt_id, error_ref)
        print(f"CELL_FAILED {cell_slug(cell)} client-exit", flush=True)
        return False
    try:
        sidecars = sorted((attempt_root / "dataset" / "meta" / "lab_provenance").glob("episode_*.json"))
        if len(sidecars) != 1:
            raise Pi05EvidenceError(f"expected one sidecar, got {len(sidecars)}")
        events_path = attempt_root / "events" / sidecars[0].name
        manifest, report = seal_pi05_episode(
            cell=cell,
            dataset_root=attempt_root / "dataset",
            sidecar_path=sidecars[0],
            events_path=events_path,
            artifact_ref=relative.as_posix(),
        )
        manifest["timing"] = {"wall_seconds": round(time.monotonic() - started, 3)}
        manifest_sha = atomic_write_manifest(attempt_root / "episode-manifest.json", manifest)
        ledger.record_policy_terminal(
            cell["run_key"], attempt_id, report["result_status"], relative.as_posix(), manifest_sha
        )
        print(
            f"CELL_COMPLETE {cell_slug(cell)} status={report['result_status']} "
            f"frames={report['frames']} requests={report['request_count']} "
            f"wall_s={manifest['timing']['wall_seconds']}",
            flush=True,
        )
        return True
    except (Pi05EvidenceError, OSError, TypeError, ValueError) as exc:
        error_ref = write_error(artifact_root, cell, attempt_id, "episode-export", str(exc))
        ledger.record_infrastructure_error(cell["run_key"], attempt_id, error_ref)
        print(f"CELL_FAILED {cell_slug(cell)} episode-export {exc}", flush=True)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--client-python", default=sys.executable)
    parser.add_argument("--server-python", required=True)
    parser.add_argument("--server-root", type=Path, required=True)
    parser.add_argument("--libero-root", type=Path, required=True)
    parser.add_argument("--openpi-data-home", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--suite", choices=SUITE_ORDER)
    parser.add_argument("--max-cells", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and os.environ.get("MUJOCO_GL") != "egl":
        parser.error("execution requires MUJOCO_GL=egl")
    contract = load_pi05_contract()
    cells = contract["cells"]
    ledger = RunLedger(args.ledger, [cell["run_key"] for cell in cells], policy_id=POLICY_ID)
    ledger.initialize()
    state = ledger.state()
    pending = [cell for cell in cells if cell["run_key"] not in state.completed]
    if args.suite:
        pending = [cell for cell in pending if cell["suite"] == args.suite]
    if args.max_cells is not None:
        if args.max_cells < 1:
            parser.error("--max-cells must be at least 1")
        pending = pending[: args.max_cells]
    print(
        json.dumps(
            {
                "pending_selected": len(pending),
                "completed_skipped": len(state.completed),
                "active_partial": len(state.active),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    if args.dry_run or not pending:
        return 0

    args.artifact_root.mkdir(parents=True, exist_ok=True)
    server_log_path = args.artifact_root / "logs" / "pi05-server.log"
    server_log_path.parent.mkdir(parents=True, exist_ok=True)
    server_env = os.environ.copy()
    server_env["OPENPI_DATA_HOME"] = str(args.openpi_data_home)
    client_env = os.environ.copy()
    existing_pythonpath = client_env.get("PYTHONPATH")
    client_env["PYTHONPATH"] = os.pathsep.join(
        item for item in (str(args.libero_root), existing_pythonpath) if item
    )
    failures = 0
    with server_log_path.open("a", encoding="utf-8") as server_log:
        server = subprocess.Popen(
            [args.server_python, "-u", "scripts/serve_policy.py", "--env", "LIBERO", "--port", str(args.port)],
            cwd=args.server_root,
            env=server_env,
            stdout=server_log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            print("SERVER_LOADING policy=pi05-libero", flush=True)
            if not wait_port(args.port, 900, server):
                print("SERVER_FAILED policy=pi05-libero", flush=True)
                return 2
            print("SERVER_READY policy=pi05-libero", flush=True)
            for cell in pending:
                try:
                    if not execute_cell(
                        cell,
                        contract,
                        ledger,
                        args.artifact_root,
                        args.client_python,
                        client_env,
                        args.port,
                    ):
                        failures += 1
                except LedgerContractError as exc:
                    failures += 1
                    print(f"LEDGER_ERROR {cell_slug(cell)} {exc}", flush=True)
        finally:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=15)
            print("SERVER_STOPPED policy=pi05-libero", flush=True)
    summary = ledger.resume_summary()
    print(
        f"EXECUTION_SUMMARY completed={summary['completed_skipped']} pending={len(summary['pending'])} "
        f"infra_attempts={summary['infrastructure_error_attempts']} failures_this_run={failures}",
        flush=True,
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
