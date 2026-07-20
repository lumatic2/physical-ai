#!/usr/bin/env python3
"""Inspect a running LeRobot Foxglove server without requiring the desktop app."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import websockets


REQUIRED_TOPICS = {
    "/observation/images/image",
    "/observation/images/image2",
    "/observation/state",
    "/action/state",
}


async def inspect(url: str) -> dict:
    server_info = None
    channels = []
    async with websockets.connect(url, subprotocols=["foxglove.sdk.v1"]) as socket:
        for _ in range(8):
            try:
                message = await asyncio.wait_for(socket.recv(), timeout=3)
            except TimeoutError:
                break
            if not isinstance(message, str):
                continue
            payload = json.loads(message)
            if payload.get("op") == "serverInfo":
                server_info = payload
            elif payload.get("op") == "advertise":
                channels.extend(payload.get("channels", []))
            if server_info is not None and channels:
                break

        topics = {channel["topic"] for channel in channels}
        missing_topics = sorted(REQUIRED_TOPICS - topics)
        capabilities = set((server_info or {}).get("capabilities", []))
        missing_capabilities = sorted({"playbackControl", "time"} - capabilities)
        return {
            "url": url,
            "subprotocol": socket.subprotocol,
            "server_info": server_info,
            "channels": [
                {
                    "id": channel.get("id"),
                    "topic": channel.get("topic"),
                    "encoding": channel.get("encoding"),
                    "schema_name": channel.get("schemaName"),
                }
                for channel in sorted(channels, key=lambda item: item["topic"])
            ],
            "required_topics": sorted(REQUIRED_TOPICS),
            "missing_topics": missing_topics,
            "missing_capabilities": missing_capabilities,
            "reusable": bool(server_info and not missing_topics and not missing_capabilities),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="ws://127.0.0.1:8765")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = asyncio.run(inspect(args.url))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["reusable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
