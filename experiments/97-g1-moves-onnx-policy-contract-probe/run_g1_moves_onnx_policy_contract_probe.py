#!/usr/bin/env python3
"""Probe G1 Moves ONNX policy contracts for the M19 motion-tracking route.

This experiment deliberately does not commit downloaded ONNX binaries. It
downloads the public Hugging Face artifacts into a temporary directory, records
hashes/metadata/shape checks, runs deterministic inference smoke tests, and
then writes small JSON evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


BASE = "https://huggingface.co/datasets/exptech/g1-moves/resolve/main"
API_TREE = "https://huggingface.co/api/datasets/exptech/g1-moves/tree/main"
CLIP_DIR = "dance/J_Dance4_Broadway"
ACCESS_DATE = "2026-06-18"
DEFAULT_OUT = (
    Path(__file__).resolve().parent
    / "verify"
    / "g1-moves-onnx-policy-contract-probe"
)


@dataclass(frozen=True)
class Artifact:
    relpath: str
    kind: str

    @property
    def url(self) -> str:
        return f"{BASE}/{self.relpath}"


ARTIFACTS = [
    Artifact(f"{CLIP_DIR}/policy/J_Dance4_Broadway.onnx", "onnx"),
    Artifact(f"{CLIP_DIR}/policy/J_Dance4_Broadway_policy.onnx", "onnx"),
    Artifact(f"{CLIP_DIR}/policy_154/J_Dance4_Broadway_policy.onnx", "onnx"),
    Artifact(f"{CLIP_DIR}/README.md", "text"),
    Artifact(f"{CLIP_DIR}/policy/agent.yaml", "text"),
    Artifact(f"{CLIP_DIR}/policy/env.yaml", "text"),
    Artifact(f"{CLIP_DIR}/policy_154/agent.yaml", "text"),
    Artifact(f"{CLIP_DIR}/policy_154/env.yaml", "text"),
    Artifact(f"{CLIP_DIR}/policy_154/deployment_metadata_154.json", "json"),
    Artifact(f"{CLIP_DIR}/training/J_Dance4_Broadway.npz", "npz"),
]


KNOWN_TERM_DIMS = {
    "motion_anchor_pos_b": 3,
    "motion_anchor_ori_b": 6,
    "base_lin_vel": 3,
    "base_ang_vel": 3,
    "joint_pos": 29,
    "joint_vel": 29,
    "actions": 29,
}


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "physical-ai-exp97/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_tree_listing() -> list[dict[str, Any]]:
    url = f"{API_TREE}/{CLIP_DIR}?recursive=true&expand=true"
    return json.loads(fetch_bytes(url).decode("utf-8"))


def actor_terms_from_env_yaml(text: str) -> list[str]:
    marker = "observations:\n  actor:\n    terms:\n"
    start = text.find(marker)
    if start < 0:
        return []
    end = text.find("\n  critic:", start)
    block = text[start:end if end >= 0 else len(text)]
    terms = []
    for match in re.finditer(r"^      ([A-Za-z0-9_]+):\n", block, flags=re.MULTILINE):
        name = match.group(1)
        if name not in ["terms"]:
            terms.append(name)
    return terms


def infer_term_dims(input_dim: int, terms: list[str]) -> dict[str, int | str]:
    dims: dict[str, int | str] = {}
    unknown = []
    known_total = 0
    for term in terms:
        if term == "command":
            unknown.append(term)
            continue
        dim = KNOWN_TERM_DIMS.get(term)
        if dim is None:
            unknown.append(term)
        else:
            dims[term] = dim
            known_total += dim
    remaining = input_dim - known_total
    if len(unknown) == 1:
        dims[unknown[0]] = remaining
    elif unknown:
        each = remaining / len(unknown)
        for term in unknown:
            dims[term] = f"unresolved_share({each})"
    return dims


def inspect_onnx(path: Path) -> dict[str, Any]:
    import onnx
    import onnxruntime as ort

    model = onnx.load(path)
    onnx.checker.check_model(model)
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    inputs = sess.get_inputs()
    outputs = sess.get_outputs()
    input_meta = [
        {"name": i.name, "shape": list(i.shape), "type": i.type}
        for i in inputs
    ]
    output_meta = [
        {"name": o.name, "shape": list(o.shape), "type": o.type}
        for o in outputs
    ]
    obs_input = next((i for i in inputs if i.name == "obs"), None)
    time_input = next((i for i in inputs if i.name == "time_step"), None)
    action_output = next((o for o in outputs if o.name == "actions"), outputs[0] if outputs else None)
    if obs_input is None or action_output is None:
        smoke = {"ok": False, "reason": "missing obs input or actions output"}
    else:
        dim = int(obs_input.shape[-1])
        samples = {
            "zeros": np.zeros((1, dim), dtype=np.float32),
            "small_ramp": np.linspace(-0.2, 0.2, dim, dtype=np.float32)[None, :],
            "unit_ramp": np.linspace(-1.0, 1.0, dim, dtype=np.float32)[None, :],
        }
        runs: dict[str, Any] = {}
        for name, arr in samples.items():
            feed = {obs_input.name: arr}
            if time_input is not None:
                feed[time_input.name] = np.zeros(tuple(int(v) for v in time_input.shape), dtype=np.float32)
            raw_outputs = sess.run(None, feed)
            action_index = [o.name for o in outputs].index(action_output.name)
            out = raw_outputs[action_index]
            runs[name] = {
                "shape": list(out.shape),
                "finite": bool(np.isfinite(out).all()),
                "min": float(np.min(out)),
                "max": float(np.max(out)),
                "mean": float(np.mean(out)),
                "std": float(np.std(out)),
                "first8": [float(v) for v in out.reshape(-1)[:8]],
            }
        repeat_feed = {obs_input.name: samples["small_ramp"]}
        if time_input is not None:
            repeat_feed[time_input.name] = np.zeros(tuple(int(v) for v in time_input.shape), dtype=np.float32)
        repeat_a = sess.run(None, repeat_feed)[[o.name for o in outputs].index(action_output.name)]
        repeat_b = sess.run(None, repeat_feed)[[o.name for o in outputs].index(action_output.name)]
        smoke = {
            "ok": True,
            "obs_input": obs_input.name,
            "action_output": action_output.name,
            "requires_time_step": time_input is not None,
            "deterministic_max_abs_diff": float(np.max(np.abs(repeat_a - repeat_b))),
            "runs": runs,
        }
    return {
        "checker_pass": True,
        "ir_version": int(model.ir_version),
        "opsets": [{"domain": o.domain, "version": int(o.version)} for o in model.opset_import],
        "inputs": input_meta,
        "outputs": output_meta,
        "smoke": smoke,
    }


def inspect_npz(path: Path) -> dict[str, Any]:
    data = np.load(path)
    result = {}
    for key in sorted(data.files):
        arr = data[key]
        flat = arr.reshape(-1)
        result[key] = {
            "shape": list(arr.shape),
            "dtype": str(arr.dtype),
            "finite": bool(np.isfinite(arr).all()),
            "min": float(np.min(flat)) if flat.size else None,
            "max": float(np.max(flat)) if flat.size else None,
            "mean": float(np.mean(flat)) if flat.size else None,
        }
    return result


def write_summary_md(result: dict[str, Any], path: Path) -> None:
    rows = []
    for rel, info in result["artifacts"].items():
        if info["kind"] != "onnx":
            continue
        onnx_info = info["onnx"]
        inp = next(i for i in onnx_info["inputs"] if i["name"] == "obs")
        out = next(o for o in onnx_info["outputs"] if o["name"] == "actions")
        rows.append(
            "| {name} | {size} | {inp} | {out} | {ok} | {minv:.3f}..{maxv:.3f} |".format(
                name=Path(rel).name,
                size=info["size_bytes"],
                inp=inp["shape"],
                out=out["shape"],
                ok=onnx_info["smoke"]["ok"],
                minv=onnx_info["smoke"]["runs"]["unit_ramp"]["min"],
                maxv=onnx_info["smoke"]["runs"]["unit_ramp"]["max"],
            )
        )
    text = "\n".join(
        [
            "# G1 Moves ONNX Policy Contract Probe Summary",
            "",
            "| ONNX | Bytes | Input | Output | Smoke | Unit-ramp action range |",
            "|---|---:|---|---|---|---|",
            *rows,
            "",
            f"Verdict: **{result['verdict']}**",
            "",
            "Key finding: the public artifacts provide finite ONNX actor policies, but the actor observation is a motion-command tracking vector, not the local exp05 103-d G1 walking observation.",
            "",
            "M19 closes only after this contract is converted into a native rollout and the browser replay also passes the visible gate.",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 route moves from raw reference playback to public G1 Moves ONNX policy contract validation.",
            "perspectives": {
                "product": "checks whether a public learned tracker can plausibly become the showable squat policy path",
                "architecture": "keeps external binaries out of git while preserving hashes and shape contracts",
                "security": "downloads public Hugging Face dataset artifacts only; no credentials or secrets",
                "qa": "requires tree listing, hashes, ONNX checker, onnxruntime finite inference, and sidecar obs term inference",
                "skeptic": "a valid ONNX actor is not enough if its motion-command observation cannot be reconstructed in local MuJoCo",
            },
            "dod": [
                "download and hash public G1 Moves policy artifacts",
                "prove ONNX input/output contracts with onnxruntime smoke",
                "identify whether native rollout can be attempted without the upstream mjlab observation builder",
            ],
        },
        "sources": [
            {
                "url": "https://huggingface.co/datasets/exptech/g1-moves",
                "accessed": ACCESS_DATE,
            },
            {
                "url": "https://huggingface.co/spaces/exptech/g1-moves",
                "accessed": ACCESS_DATE,
            },
        ],
        "clip": CLIP_DIR,
        "artifacts": {},
    }

    result["tree"] = [
        {
            "type": item.get("type"),
            "path": item.get("path"),
            "size": item.get("size"),
        }
        for item in download_tree_listing()
    ]

    with tempfile.TemporaryDirectory(prefix="g1_moves_onnx_") as tmp_name:
        tmp = Path(tmp_name)
        env_text_by_rel: dict[str, str] = {}
        for artifact in ARTIFACTS:
            blob = fetch_bytes(artifact.url)
            info: dict[str, Any] = {
                "kind": artifact.kind,
                "url": artifact.url,
                "accessed": ACCESS_DATE,
                "size_bytes": len(blob),
                "sha256": sha256(blob),
            }
            local_path = tmp / artifact.relpath.replace("/", "__")
            local_path.write_bytes(blob)
            if artifact.kind == "text":
                text = blob.decode("utf-8", errors="replace")
                info["text_excerpt"] = text[:1200]
                if artifact.relpath.endswith("env.yaml"):
                    terms = actor_terms_from_env_yaml(text)
                    info["actor_terms"] = terms
                    env_text_by_rel[artifact.relpath] = text
            elif artifact.kind == "json":
                info["json"] = json.loads(blob.decode("utf-8"))
            elif artifact.kind == "npz":
                info["npz"] = inspect_npz(local_path)
            elif artifact.kind == "onnx":
                info["onnx"] = inspect_onnx(local_path)
            result["artifacts"][artifact.relpath] = info

    # Connect ONNX input sizes to the sidecar env observation terms.
    for rel, info in result["artifacts"].items():
        if info["kind"] != "onnx":
            continue
        obs_input = next(i for i in info["onnx"]["inputs"] if i["name"] == "obs")
        input_dim = int(obs_input["shape"][-1])
        sidecar = f"{CLIP_DIR}/policy_154/env.yaml" if input_dim == 154 else f"{CLIP_DIR}/policy/env.yaml"
        terms = result["artifacts"].get(sidecar, {}).get("actor_terms", [])
        info["matched_env_sidecar"] = sidecar
        info["inferred_actor_term_dims"] = infer_term_dims(input_dim, terms)

    onnx_infos = [v for v in result["artifacts"].values() if v["kind"] == "onnx"]
    shape_checks = []
    for info in onnx_infos:
        inp = next(i for i in info["onnx"]["inputs"] if i["name"] == "obs")["shape"]
        out = next(o for o in info["onnx"]["outputs"] if o["name"] == "actions")["shape"]
        smoke = info["onnx"]["smoke"]
        shape_checks.append(
            bool(
                inp[-1] in [154, 160]
                and out[-1] == 29
                and smoke["ok"]
                and smoke["deterministic_max_abs_diff"] == 0.0
                and all(run["finite"] for run in smoke["runs"].values())
            )
        )
    result["checks"] = {
        "onnx_candidates_present": len(onnx_infos) == 3,
        "all_onnx_shape_smoke_pass": all(shape_checks),
        "policy_154_metadata_present": f"{CLIP_DIR}/policy_154/deployment_metadata_154.json" in result["artifacts"],
        "training_npz_present": f"{CLIP_DIR}/training/J_Dance4_Broadway.npz" in result["artifacts"],
        "local_native_adapter_ready": False,
    }
    result["adapter_gap"] = {
        "reason": "The ONNX actor observes a 58-d generated motion command plus motion-anchor/body-state terms from mjlab, while the local exp05 G1 policy path observes a 103-d locomotion vector. A native rollout requires reconstructing or importing the mjlab motion-command observation builder, not just feeding qpos/qvel.",
        "required_next": [
            "derive the 58-d motion command from the training NPZ and local MuJoCo body set, or import upstream mjlab tracking observation code",
            "map the actor action to local G1 29-DOF ctrl order and action scale",
            "run native visible gate before browser replay",
        ],
    }
    result["verdict"] = (
        "PASS_ONNX_CONTRACT__NATIVE_ADAPTER_PENDING"
        if all(v for k, v in result["checks"].items() if k != "local_native_adapter_ready")
        else "FAIL_ONNX_CONTRACT"
    )

    result_path = args.out_dir / "result.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_summary_md(result, args.out_dir / "g1-moves-onnx-policy-contract-summary.md")
    print(json.dumps({"verdict": result["verdict"], "checks": result["checks"]}, indent=2))
    return 0 if result["verdict"].startswith("PASS_ONNX_CONTRACT") else 1


if __name__ == "__main__":
    raise SystemExit(main())
