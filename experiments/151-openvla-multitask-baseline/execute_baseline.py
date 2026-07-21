#!/usr/bin/env python3
"""Execute pending GEN2 cells with one OpenVLA server load per LIBERO suite."""

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

from episode_export import EpisodeExportError, atomic_write_manifest, build_sealed_manifest
from run_baseline import DEFAULT_REPO_ROOT, load_runner_contract
from run_ledger import LedgerContractError, RunLedger
from direct_vla import emit_direct_vla_trace


EXP01 = DEFAULT_REPO_ROOT / "experiments" / "01-vla-local-eval"


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


def server_command(cell: dict[str, Any], python: str, port: int) -> list[str]:
    return [
        python,
        "-u",
        str(EXP01 / "server.py"),
        "--policy",
        "openvla",
        "--suite",
        cell["suite"],
        "--ckpt",
        cell["checkpoint_repo"],
        "--ckpt-revision",
        cell["checkpoint_revision"],
        "--port",
        str(port),
    ]


def client_command(
    cell: dict[str, Any], contract: dict[str, Any], attempt_root: Path, python: str, port: int
) -> list[str]:
    config = contract["config"]
    return [
        python,
        "-u",
        str(EXP01 / "client.py"),
        "--suite",
        cell["suite"],
        "--tasks",
        "1",
        "--task-offset",
        str(cell["task_id"]),
        "--trials",
        "1",
        "--trial-offset",
        str(cell["state_index"]),
        "--seed",
        str(config["seed"]),
        "--max-policy-steps",
        str(config["max_policy_steps"][cell["suite"]]),
        "--port",
        str(port),
        "--record-root",
        str(attempt_root / "dataset"),
        "--record-repo-id",
        f"physical-ai/gen2-{cell_slug(cell)}",
        "--dataset-revision",
        dataset_revision(cell["run_key"]),
        "--environment-revision",
        cell["environment_revision"],
        "--policy-revision",
        cell["checkpoint_revision"],
    ]


def write_error(root: Path, cell: dict[str, Any], attempt_id: str, kind: str, detail: str) -> str:
    relative = Path("errors") / cell_slug(cell) / f"attempt-{attempt_id}.json"
    path = root / relative
    payload = {
        "schema_version": "physical-ai-gen2-infrastructure-error-v1",
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
    python: str,
    port: int,
    *,
    recover_active: bool,
) -> bool:
    attempt = ledger.begin_attempt(cell["run_key"], recover_active=recover_active)
    attempt_id = attempt["attempt_id"]
    relative = Path("episodes") / cell_slug(cell) / f"attempt-{attempt_id}"
    attempt_root = artifact_root / relative
    attempt_root.mkdir(parents=True, exist_ok=False)
    command = client_command(cell, contract, attempt_root, python, port)
    started = time.monotonic()
    try:
        completed = subprocess.run(command, cwd=DEFAULT_REPO_ROOT, env=os.environ, text=True, capture_output=True, timeout=1800)
    except subprocess.TimeoutExpired as exc:
        error_ref = write_error(artifact_root, cell, attempt_id, "client-timeout", str(exc))
        ledger.record_infrastructure_error(cell["run_key"], attempt_id, error_ref)
        return False
    log = completed.stdout + completed.stderr
    (attempt_root / "client.log").write_text(log, encoding="utf-8")
    if completed.returncode:
        error_ref = write_error(artifact_root, cell, attempt_id, "client-exit", log)
        ledger.record_infrastructure_error(cell["run_key"], attempt_id, error_ref)
        return False
    try:
        sidecars = sorted((attempt_root / "dataset/meta/lab_provenance").glob("episode_*.json"))
        if len(sidecars) != 1:
            raise EpisodeExportError(f"expected one sidecar file, got {len(sidecars)}")
        events_path = attempt_root / "events" / sidecars[0].name
        emit_direct_vla_trace(attempt_root / "dataset", sidecars[0], events_path)
        manifest, report = build_sealed_manifest(
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
            f"CELL_COMPLETE {cell_slug(cell)} status={report['result_status']} frames={report['frames']} "
            f"wall_s={manifest['timing']['wall_seconds']}",
            flush=True,
        )
        return True
    except (EpisodeExportError, OSError, ValueError) as exc:
        error_ref = write_error(artifact_root, cell, attempt_id, "episode-export", str(exc))
        ledger.record_infrastructure_error(cell["run_key"], attempt_id, error_ref)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--suite", choices=("libero_spatial", "libero_object", "libero_goal"))
    parser.add_argument("--max-cells", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and os.environ.get("MUJOCO_GL") != "egl":
        parser.error("execution requires MUJOCO_GL=egl")
    contract = load_runner_contract()
    all_cells = contract["cells"]
    ledger = RunLedger(args.ledger, [cell["run_key"] for cell in all_cells])
    ledger.initialize()
    state = ledger.state()
    pending = [cell for cell in all_cells if cell["run_key"] not in state.completed]
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
                "suites": list(dict.fromkeys(cell["suite"] for cell in pending)),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    if args.dry_run or not pending:
        return 0
    failures = 0
    for suite in dict.fromkeys(cell["suite"] for cell in pending):
        suite_cells = [cell for cell in pending if cell["suite"] == suite]
        server_log_path = args.artifact_root / "logs" / f"{suite}-server.log"
        server_log_path.parent.mkdir(parents=True, exist_ok=True)
        with server_log_path.open("a", encoding="utf-8") as server_log:
            server = subprocess.Popen(
                server_command(suite_cells[0], args.python, args.port),
                cwd=DEFAULT_REPO_ROOT,
                env=os.environ,
                stdout=server_log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                print(f"SERVER_LOADING suite={suite}", flush=True)
                if not wait_port(args.port, 900, server):
                    failures += len(suite_cells)
                    print(f"SERVER_FAILED suite={suite}", flush=True)
                    continue
                print(f"SERVER_READY suite={suite}", flush=True)
                for cell in suite_cells:
                    recover = cell["run_key"] in ledger.state().active
                    try:
                        if not execute_cell(
                            cell,
                            contract,
                            ledger,
                            args.artifact_root,
                            args.python,
                            args.port,
                            recover_active=recover,
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
                print(f"SERVER_STOPPED suite={suite}", flush=True)
    summary = ledger.resume_summary()
    print(
        f"EXECUTION_SUMMARY completed={summary['completed_skipped']} pending={len(summary['pending'])} "
        f"infra_attempts={summary['infrastructure_error_attempts']} failures_this_run={failures}",
        flush=True,
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
