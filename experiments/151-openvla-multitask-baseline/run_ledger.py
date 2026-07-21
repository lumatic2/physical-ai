#!/usr/bin/env python3
"""Append-only, fsync-backed attempt ledger for the GEN2 OpenVLA baseline."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

EVENT_VERSION = "physical-ai-run-ledger-event-v1"
HEX32 = re.compile(r"^[0-9a-f]{32}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class LedgerContractError(ValueError):
    """Raised when an append or replay would hide or rewrite execution history."""


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class LedgerState:
    initialized: bool = False
    attempts: dict[str, dict[str, Any]] = field(default_factory=dict)
    run_attempts: dict[str, list[str]] = field(default_factory=dict)
    active: dict[str, str] = field(default_factory=dict)
    completed: dict[str, str] = field(default_factory=dict)
    infrastructure_errors: dict[str, list[str]] = field(default_factory=dict)


def _require_keys(event: dict[str, Any], keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if key not in event]
    if missing:
        raise LedgerContractError(f"{event.get('event')} missing fields: {', '.join(missing)}")


def replay_events(
    events: list[dict[str, Any]], run_keys: list[str], policy_id: str = "openvla-libero"
) -> LedgerState:
    state = LedgerState()
    allowed = set(run_keys)
    expected_contract_hash = canonical_hash(run_keys)
    for offset, event in enumerate(events):
        if event.get("schema_version") != EVENT_VERSION:
            raise LedgerContractError(f"event {offset} schema mismatch")
        kind = event.get("event")
        if kind == "ledger_initialized":
            if offset != 0 or state.initialized:
                raise LedgerContractError("ledger_initialized must be the unique first event")
            _require_keys(event, ("contract",))
            contract = event["contract"]
            if contract.get("policy_id") != policy_id:
                raise LedgerContractError("ledger policy mismatch")
            if contract.get("cell_count") != len(run_keys):
                raise LedgerContractError("ledger cell count mismatch")
            if contract.get("ordered_run_keys_sha256") != expected_contract_hash:
                raise LedgerContractError("ledger ordered run-key contract mismatch")
            state.initialized = True
            continue
        if not state.initialized:
            raise LedgerContractError("ledger event before initialization")
        _require_keys(event, ("run_key", "attempt_id"))
        run_key = event["run_key"]
        attempt_id = event["attempt_id"]
        if not HEX32.fullmatch(str(attempt_id)):
            raise LedgerContractError(f"invalid attempt id: {attempt_id}")
        if run_key not in allowed:
            raise LedgerContractError(f"run key outside frozen contract: {run_key}")
        if kind == "attempt_started":
            _require_keys(event, ("attempt_index", "retry_of"))
            if attempt_id in state.attempts:
                raise LedgerContractError(f"duplicate attempt id: {attempt_id}")
            if run_key in state.completed:
                raise LedgerContractError(f"hidden retry after valid policy result: {run_key}")
            if run_key in state.active:
                raise LedgerContractError(f"new attempt hides active partial attempt: {run_key}")
            prior = state.run_attempts.get(run_key, [])
            if event["attempt_index"] != len(prior):
                raise LedgerContractError(f"non-sequential attempt index: {run_key}")
            expected_retry = prior[-1] if prior else None
            if event["retry_of"] != expected_retry:
                raise LedgerContractError(f"retry linkage mismatch: {run_key}")
            state.attempts[attempt_id] = {"status": "active", **event}
            state.run_attempts.setdefault(run_key, []).append(attempt_id)
            state.active[run_key] = attempt_id
        elif kind == "attempt_interrupted":
            _require_keys(event, ("reason",))
            if state.active.get(run_key) != attempt_id:
                raise LedgerContractError(f"interruption does not match active attempt: {run_key}")
            state.attempts[attempt_id]["status"] = "interrupted"
            state.attempts[attempt_id]["reason"] = event["reason"]
            del state.active[run_key]
        elif kind == "attempt_terminal":
            _require_keys(event, ("result_class", "result_status"))
            if state.active.get(run_key) != attempt_id:
                raise LedgerContractError(f"duplicate or non-active terminal event: {run_key}")
            result_class = event["result_class"]
            result_status = event["result_status"]
            artifact = event.get("artifact")
            if result_class == "policy":
                if result_status not in {"success", "timeout"}:
                    raise LedgerContractError("policy terminal status must be success or timeout")
                if not isinstance(artifact, dict) or artifact.get("status") != "sealed":
                    raise LedgerContractError("policy terminal requires a sealed artifact")
                if not artifact.get("ref") or not HEX64.fullmatch(str(artifact.get("sha256", ""))):
                    raise LedgerContractError("sealed artifact requires ref and sha256")
                state.completed[run_key] = attempt_id
            elif result_class == "infrastructure":
                if result_status != "error" or not event.get("error_ref"):
                    raise LedgerContractError("infrastructure terminal requires error status and error_ref")
                if artifact is not None:
                    raise LedgerContractError("infrastructure error cannot promote an artifact")
                state.infrastructure_errors.setdefault(run_key, []).append(attempt_id)
            else:
                raise LedgerContractError(f"unknown result class: {result_class}")
            state.attempts[attempt_id].update(event)
            state.attempts[attempt_id]["status"] = "terminal"
            del state.active[run_key]
        else:
            raise LedgerContractError(f"unknown ledger event: {kind}")
    if not state.initialized:
        raise LedgerContractError("ledger is missing initialization")
    return state


class RunLedger:
    def __init__(self, path: Path, run_keys: list[str], *, policy_id: str = "openvla-libero") -> None:
        if len(run_keys) != len(set(run_keys)):
            raise LedgerContractError("run-key contract contains duplicates")
        self.path = path
        self.run_keys = list(run_keys)
        self.policy_id = policy_id
        self.lock_path = path.with_suffix(path.suffix + ".lock")

    @contextmanager
    def _lock(self, timeout_s: float = 5.0) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + timeout_s
        descriptor = None
        while descriptor is None:
            try:
                descriptor = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise LedgerContractError(f"ledger lock timeout: {self.lock_path.name}")
                time.sleep(0.05)
        try:
            os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
            os.fsync(descriptor)
            yield
        finally:
            os.close(descriptor)
            self.lock_path.unlink(missing_ok=True)

    def _events_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events = []
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                raise LedgerContractError(f"blank ledger line: {line_number}")
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise LedgerContractError(f"invalid JSON ledger line: {line_number}") from exc
        return events

    def _write_event_unlocked(self, event: dict[str, Any]) -> None:
        encoded = (json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            written = os.write(descriptor, encoded)
            if written != len(encoded):
                raise OSError("short append to run ledger")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def initialize(self) -> LedgerState:
        with self._lock():
            events = self._events_unlocked()
            if not events:
                self._write_event_unlocked(
                    {
                        "schema_version": EVENT_VERSION,
                        "event": "ledger_initialized",
                        "recorded_at": now_utc(),
                        "contract": {
                            "policy_id": self.policy_id,
                            "cell_count": len(self.run_keys),
                            "ordered_run_keys_sha256": canonical_hash(self.run_keys),
                        },
                    }
                )
                events = self._events_unlocked()
            return replay_events(events, self.run_keys, self.policy_id)

    def state(self) -> LedgerState:
        with self._lock():
            return replay_events(self._events_unlocked(), self.run_keys, self.policy_id)

    def _append(self, event: dict[str, Any]) -> LedgerState:
        with self._lock():
            events = self._events_unlocked()
            replay_events(events + [event], self.run_keys, self.policy_id)
            self._write_event_unlocked(event)
            return replay_events(events + [event], self.run_keys, self.policy_id)

    def begin_attempt(self, run_key: str, *, recover_active: bool = False) -> dict[str, Any]:
        state = self.state()
        if run_key in state.active:
            if not recover_active:
                raise LedgerContractError(f"active partial attempt requires explicit recovery: {run_key}")
            prior_id = state.active[run_key]
            self._append(
                {
                    "schema_version": EVENT_VERSION,
                    "event": "attempt_interrupted",
                    "recorded_at": now_utc(),
                    "run_key": run_key,
                    "attempt_id": prior_id,
                    "reason": "resume_after_interruption",
                }
            )
            state = self.state()
        prior = state.run_attempts.get(run_key, [])
        event = {
            "schema_version": EVENT_VERSION,
            "event": "attempt_started",
            "recorded_at": now_utc(),
            "run_key": run_key,
            "attempt_id": uuid.uuid4().hex,
            "attempt_index": len(prior),
            "retry_of": prior[-1] if prior else None,
        }
        self._append(event)
        return event

    def record_policy_terminal(
        self, run_key: str, attempt_id: str, result_status: str, artifact_ref: str, artifact_sha256: str
    ) -> LedgerState:
        return self._append(
            {
                "schema_version": EVENT_VERSION,
                "event": "attempt_terminal",
                "recorded_at": now_utc(),
                "run_key": run_key,
                "attempt_id": attempt_id,
                "result_class": "policy",
                "result_status": result_status,
                "artifact": {"status": "sealed", "ref": artifact_ref, "sha256": artifact_sha256},
            }
        )

    def record_infrastructure_error(self, run_key: str, attempt_id: str, error_ref: str) -> LedgerState:
        return self._append(
            {
                "schema_version": EVENT_VERSION,
                "event": "attempt_terminal",
                "recorded_at": now_utc(),
                "run_key": run_key,
                "attempt_id": attempt_id,
                "result_class": "infrastructure",
                "result_status": "error",
                "error_ref": error_ref,
            }
        )

    def pending_run_keys(self) -> list[str]:
        state = self.state()
        return [run_key for run_key in self.run_keys if run_key not in state.completed]

    def resume_summary(self) -> dict[str, Any]:
        state = self.state()
        return {
            "total": len(self.run_keys),
            "completed_skipped": len(state.completed),
            "active_partial": [run_key for run_key in self.run_keys if run_key in state.active],
            "pending": self.pending_run_keys(),
            "infrastructure_error_attempts": sum(len(items) for items in state.infrastructure_errors.values()),
        }
