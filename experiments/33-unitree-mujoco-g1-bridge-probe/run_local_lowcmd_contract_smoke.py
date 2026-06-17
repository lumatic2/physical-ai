#!/usr/bin/env python3
"""Publish and receive Unitree G1 HG LowCmd on local DDS.

This is a command-path contract smoke. It proves that the project can emit a
G1-compatible low-level command message onto DDS, but it does not claim that the
command is safe for hardware deployment or that a controller is stable.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import threading
import time
from pathlib import Path
from typing import Any


G1_NUM_MOTOR = 29
HG_MOTOR_SLOTS = 35
DEFAULT_KP = [
    60,
    60,
    60,
    100,
    40,
    40,
    60,
    60,
    60,
    100,
    40,
    40,
    60,
    40,
    40,
    40,
    40,
    40,
    40,
    40,
    40,
    40,
    40,
    40,
    40,
    40,
    40,
    40,
    40,
]
DEFAULT_KD = [
    1,
    1,
    1,
    2,
    1,
    1,
    1,
    1,
    1,
    2,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
]


def finite(values: list[float]) -> bool:
    return all(math.isfinite(v) for v in values)


def msg_summary(msg: Any) -> dict[str, Any]:
    motors = list(msg.motor_cmd)
    first_29 = motors[:G1_NUM_MOTOR]
    return {
        "mode_pr": int(msg.mode_pr),
        "mode_machine": int(msg.mode_machine),
        "crc": int(msg.crc),
        "motor_slots": len(motors),
        "enabled_count_first_29": sum(1 for cmd in first_29 if int(cmd.mode) == 1),
        "max_abs_q_first_29": max(abs(float(cmd.q)) for cmd in first_29),
        "max_abs_dq_first_29": max(abs(float(cmd.dq)) for cmd in first_29),
        "max_abs_tau_first_29": max(abs(float(cmd.tau)) for cmd in first_29),
        "kp_first_29": [float(cmd.kp) for cmd in first_29],
        "kd_first_29": [float(cmd.kd) for cmd in first_29],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk-path", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--domain-id", type=int, default=61)
    parser.add_argument("--interface", default=None)
    parser.add_argument("--topic", default="rt/lowcmd")
    parser.add_argument("--unitree-root", type=Path)
    parser.add_argument("--hold-initial-q", action="store_true")
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--kp-scale", type=float, default=1.0)
    parser.add_argument("--kd-scale", type=float, default=1.0)
    parser.add_argument("--mode-pr", type=int, default=0)
    parser.add_argument("--mode-machine", type=int, default=0)
    parser.add_argument("--receive-timeout-s", type=float, default=5.0)
    args = parser.parse_args()

    sys.path.insert(0, str(args.sdk_path))
    target_q = [0.0 for _ in range(G1_NUM_MOTOR)]
    if args.hold_initial_q:
        if not args.unitree_root:
            parser.error("--hold-initial-q requires --unitree-root")
        import mujoco

        xml_path = args.unitree_root / "unitree_robots" / "g1" / "scene.xml"
        model = mujoco.MjModel.from_xml_path(str(xml_path))
        if model.nq < 7 + G1_NUM_MOTOR:
            raise ValueError(f"expected at least {7 + G1_NUM_MOTOR} qpos values, got {model.nq}")
        target_q = [float(v) for v in model.qpos0[7 : 7 + G1_NUM_MOTOR]]

    from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelPublisher, ChannelSubscriber
    from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
    from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_
    from unitree_sdk2py.utils.crc import CRC

    lock = threading.Lock()
    received: list[dict[str, Any]] = []

    def on_lowcmd(msg: Any) -> None:
        with lock:
            received.append(msg_summary(msg))

    ChannelFactoryInitialize(args.domain_id, args.interface)
    subscriber = ChannelSubscriber(args.topic, LowCmd_)
    subscriber.Init(on_lowcmd, 10)
    publisher = ChannelPublisher(args.topic, LowCmd_)
    publisher.Init()
    crc = CRC()
    time.sleep(0.25)

    interval = 1.0 / args.fps
    published: list[dict[str, Any]] = []
    started = time.perf_counter()
    for _ in range(args.frames):
        cmd = unitree_hg_msg_dds__LowCmd_()
        cmd.mode_pr = args.mode_pr
        cmd.mode_machine = args.mode_machine
        for i in range(G1_NUM_MOTOR):
            cmd.motor_cmd[i].mode = 1
            cmd.motor_cmd[i].tau = 0.0
            cmd.motor_cmd[i].q = target_q[i]
            cmd.motor_cmd[i].dq = 0.0
            cmd.motor_cmd[i].kp = DEFAULT_KP[i] * args.kp_scale
            cmd.motor_cmd[i].kd = DEFAULT_KD[i] * args.kd_scale
        cmd.crc = crc.Crc(cmd)
        publisher.Write(cmd)
        published.append(msg_summary(cmd))
        target = started + len(published) * interval
        sleep_s = target - time.perf_counter()
        if sleep_s > 0:
            time.sleep(sleep_s)

    deadline = time.perf_counter() + args.receive_timeout_s
    while time.perf_counter() < deadline:
        with lock:
            if len(received) >= min(args.frames, 3):
                break
        time.sleep(0.05)

    with lock:
        received_snapshot = list(received)
    last = received_snapshot[-1] if received_snapshot else None
    checks = {
        "published_frames_pass": len(published) == args.frames,
        "received_any_pass": len(received_snapshot) > 0,
        "hg_slots_pass": bool(last and last["motor_slots"] == HG_MOTOR_SLOTS),
        "g1_enabled_count_pass": bool(last and last["enabled_count_first_29"] == G1_NUM_MOTOR),
        "target_hold_pass": bool(
            last
            and last["max_abs_dq_first_29"] == 0.0
            and last["max_abs_tau_first_29"] == 0.0
        ),
        "gains_finite_pass": bool(last and finite(last["kp_first_29"]) and finite(last["kd_first_29"])),
        "crc_nonzero_pass": bool(last and last["crc"] != 0),
    }
    summary = {
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "contract": "physical-ai-unitree-g1-lowcmd-contract-smoke-v0",
        "interpretation": (
            "DDS command path can emit and receive G1 HG LowCmd target-hold messages. "
            "This is not a stable controller or hardware safety claim."
        ),
        "domain_id": args.domain_id,
        "interface": args.interface or "auto",
        "topic": args.topic,
        "target": "unitree-g1-initial-qpos" if args.hold_initial_q else "zero-q",
        "kp_scale": args.kp_scale,
        "kd_scale": args.kd_scale,
        "frames_requested": args.frames,
        "frames_published": len(published),
        "frames_received": len(received_snapshot),
        "checks": checks,
        "last_published": published[-1] if published else None,
        "last_received": last,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
