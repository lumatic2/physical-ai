from __future__ import annotations

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
VERIFY_DIR = EXP_DIR / "verify"
LOCAL_SCENE = ROOT / "experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_policy.xml"
LOCAL_BASE = ROOT / "experiments/03-digital-twin/web/assets/scenes/g1/g1_mjx_feetonly.xml"


URLS = {
    "g1_moves_github_tree": "https://api.github.com/repos/experientialtech/g1-moves/git/trees/main?recursive=1",
    "g1_moves_hf_tree": "https://huggingface.co/api/datasets/exptech/g1-moves/tree/main?recursive=1",
    "g1_moves_run_policy": "https://raw.githubusercontent.com/experientialtech/g1-moves/main/run_policy.py",
    "g1_moves_readme": "https://raw.githubusercontent.com/experientialtech/g1-moves/main/README.md",
    "g1_moves_hf_claude": "https://huggingface.co/datasets/exptech/g1-moves/resolve/main/CLAUDE.md",
    "g1_moves_hf_claude_blob": "https://huggingface.co/datasets/exptech/g1-moves/blob/fce747a1677d5e6ffbc45e04f9fbdc0252b276f5/CLAUDE.md",
    "mjlab_g1_constants": "https://raw.githubusercontent.com/mujocolab/mjlab/main/src/mjlab/asset_zoo/robots/unitree_g1/g1_constants.py",
    "mjlab_g1_env_cfg": "https://raw.githubusercontent.com/mujocolab/mjlab/main/src/mjlab/tasks/tracking/config/g1/env_cfgs.py",
}

DIRECT_XML_PROBES = [
    "https://huggingface.co/datasets/exptech/g1-moves/resolve/main/g1_mode15_square.xml",
    "https://huggingface.co/datasets/exptech/g1-moves/resolve/main/assets/g1_mode15_square.xml",
    "https://huggingface.co/datasets/exptech/g1-moves/resolve/main/mujoco/g1_mode15_square.xml",
    "https://huggingface.co/datasets/exptech/g1-moves/resolve/main/scene/g1_mode15_square.xml",
    "https://raw.githubusercontent.com/experientialtech/g1-moves/main/g1_mode15_square.xml",
    "https://raw.githubusercontent.com/experientialtech/g1-moves/main/assets/g1_mode15_square.xml",
    "https://raw.githubusercontent.com/experientialtech/g1-moves/main/mujoco/g1_mode15_square.xml",
]


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "physical-ai-exp115"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read()


def fetch_text(url: str) -> str:
    return fetch_bytes(url).decode("utf-8", errors="replace")


def fetch_text_with_fallback(urls: list[str]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    for url in urls:
        try:
            return {"url": url, "text": fetch_text(url), "errors": errors}
        except Exception as exc:  # pragma: no cover - network evidence path
            errors.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})
    return {"url": None, "text": "", "errors": errors}


def safe_fetch_json(url: str) -> dict[str, Any] | list[dict[str, Any]]:
    return json.loads(fetch_text(url))


def probe_url(url: str) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "physical-ai-exp115"})
        with urllib.request.urlopen(req, timeout=15) as res:
            return {"url": url, "status": int(res.status), "content_length": res.headers.get("content-length")}
    except Exception as exc:  # pragma: no cover - network evidence path
        return {"url": url, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}



def tree_paths(tree: dict[str, Any] | list[dict[str, Any]], kind: str) -> list[str]:
    if kind == "github":
        return [item.get("path", "") for item in tree.get("tree", []) if item.get("path")]
    return [item.get("path", "") for item in tree if item.get("path")]


def grep_lines(text: str, patterns: list[str]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if any(pattern.lower() in low for pattern in patterns):
            hits.append({"line": i, "text": line.strip()[:240]})
    return hits


def extract_assignment(text: str, name: str) -> str | None:
    match = re.search(rf"^{re.escape(name)}\s*=\s*(.+?)(?:\n\n|\Z)", text, re.M | re.S)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()[:1000]


def inspect_xml(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    actuator_tags: dict[str, int] = {}
    actuator_names: list[str] = []
    for parent in root.findall(".//actuator"):
        for child in list(parent):
            actuator_tags[child.tag] = actuator_tags.get(child.tag, 0) + 1
            actuator_names.append(child.attrib.get("name", child.attrib.get("joint", child.tag)))
    sensor_tags: dict[str, int] = {}
    sensor_names: list[str] = []
    for parent in root.findall(".//sensor"):
        for child in list(parent):
            sensor_tags[child.tag] = sensor_tags.get(child.tag, 0) + 1
            sensor_names.append(child.attrib.get("name", child.tag))
    include_files = [node.attrib.get("file") for node in root.findall(".//include")]
    keyframes = [node.attrib.get("name") for node in root.findall(".//keyframe/key")]
    return {
        "path": str(path.relative_to(ROOT)),
        "include_files": include_files,
        "actuator_tags": actuator_tags,
        "actuator_count": sum(actuator_tags.values()),
        "actuator_names_first10": actuator_names[:10],
        "sensor_tags": sensor_tags,
        "sensor_count": sum(sensor_tags.values()),
        "sensor_names": sensor_names,
        "keyframes": keyframes,
    }


def inspect_compiled_scene(path: Path) -> dict[str, Any]:
    try:
        import mujoco

        model = mujoco.MjModel.from_xml_path(str(path))
        return {
            "compile": "PASS",
            "nq": int(model.nq),
            "nv": int(model.nv),
            "nu": int(model.nu),
            "nsensor": int(model.nsensor),
            "nkey": int(model.nkey),
            "timestep": float(model.opt.timestep),
        }
    except Exception as exc:  # pragma: no cover - evidence capture path
        return {"compile": "FAIL", "error": f"{type(exc).__name__}: {exc}"}


def load_prior_result(path: str) -> dict[str, Any]:
    data = json.loads((ROOT / path).read_text(encoding="utf-8"))
    return {
        "verdict": data.get("verdict"),
        "best": data.get("best") or data.get("best_candidate") or data.get("best_attempt"),
        "runs_count": len(data.get("runs", data.get("candidates", []))),
    }


def summarize_paths(paths: list[str]) -> dict[str, Any]:
    lower = [p.lower() for p in paths]
    return {
        "path_count": len(paths),
        "contains_g1_mode15_square_xml": any("g1_mode15_square.xml" in p for p in lower),
        "xml_paths": [p for p in paths if p.lower().endswith(".xml")][:50],
        "mode15_paths": [p for p in paths if "mode15" in p.lower()][:50],
        "policy_paths": [p for p in paths if p.lower().endswith(".onnx")][:20],
        "npz_paths": [p for p in paths if p.lower().endswith(".npz")][:20],
        "yaml_paths": [p for p in paths if p.lower().endswith((".yaml", ".yml"))][:20],
    }


def decide(result: dict[str, Any]) -> dict[str, Any]:
    hf_has_xml = result["remote_tree"]["huggingface"]["contains_g1_mode15_square_xml"]
    gh_has_xml = result["remote_tree"]["github"]["contains_g1_mode15_square_xml"]
    direct_has_xml = any(item.get("status") == 200 for item in result["direct_xml_probes"])
    local_position_actuators = result["local_scene"]["base_xml"]["actuator_tags"].get("position", 0)
    local_sensor_count = result["local_scene"]["compiled"]["nsensor"]
    run_policy_mentions_xml = bool(result["remote_contract"]["run_policy"]["g1_mode15_square_hits"])
    prior_failed = all(
        item["verdict"] and item["verdict"].startswith("FAIL")
        for item in result["prior_native_failures"].values()
    )

    blockers: list[str] = []
    if not (hf_has_xml or gh_has_xml or direct_has_xml):
        blockers.append("exact_g1_mode15_square_xml_not_present_in_public_trees_or_direct_probes")
    if local_position_actuators:
        blockers.append("local_scene_uses_position_actuators_not_upstream_motor_pd_scene")
    if local_sensor_count < 10:
        blockers.append("local_scene_sensor_contract_too_thin_for_upstream_runner")
    if prior_failed:
        blockers.append("previous_adapter_public_xml_mjlab_rollouts_all_failed_native_gate")

    if run_policy_mentions_xml and blockers:
        verdict = "PARITY_BLOCKED_EXACT_SCENE_NOT_PUBLIC"
        next_action = "stop_hand_adapter_sweeps_and_start_local_scene_tracker_retrain_or_full_order_idqp_mpc"
    elif not blockers:
        verdict = "PARITY_READY_FOR_NATIVE_ONNX_RETRY"
        next_action = "run_native_onnx_with_exact_scene"
    else:
        verdict = "PARITY_INCONCLUSIVE"
        next_action = "collect_missing_contract_files"

    return {"verdict": verdict, "blockers": blockers, "next_action": next_action}


def write_summary(result: dict[str, Any]) -> None:
    decision = result["decision"]
    lines = [
        "# G1 Moves upstream scene parity audit",
        "",
        f"Verdict: `{decision['verdict']}`",
        f"Next action: `{decision['next_action']}`",
        "",
        "## Remote tree",
        f"- GitHub paths: {result['remote_tree']['github']['path_count']}; g1_mode15_square.xml present: {result['remote_tree']['github']['contains_g1_mode15_square_xml']}",
        f"- Hugging Face paths: {result['remote_tree']['huggingface']['path_count']}; g1_mode15_square.xml present: {result['remote_tree']['huggingface']['contains_g1_mode15_square_xml']}",
        f"- Direct XML probes with HTTP 200: {sum(1 for item in result['direct_xml_probes'] if item.get('status') == 200)}",
        "",
        "## Contract hits",
        f"- run_policy.py g1_mode15_square hits: {len(result['remote_contract']['run_policy']['g1_mode15_square_hits'])}",
        f"- run_policy.py observation/action hits: {len(result['remote_contract']['run_policy']['obs_action_hits'])}",
        f"- HF CLAUDE exact XML hits: {len(result['remote_contract']['hf_claude']['g1_mode15_square_hits'])}",
        "",
        "## Local scene",
        f"- include: {result['local_scene']['scene_xml']['include_files']}",
        f"- base actuators: {result['local_scene']['base_xml']['actuator_tags']}",
        f"- compiled: {result['local_scene']['compiled']}",
        "",
        "## Blockers",
    ]
    for blocker in decision["blockers"]:
        lines.append(f"- {blocker}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "- The public G1 Moves policy route still lacks exact training-scene parity in this repo.",
            "- Previous native adapter/public XML/mjlab attempts already failed, so another hand-written adapter sweep is low value.",
            "- M19 should continue with local-scene tracker retraining or full-order ID-QP/MPC unless the exact upstream XML is obtained.",
        ]
    )
    (VERIFY_DIR / "upstream-scene-parity-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)

    github_tree = safe_fetch_json(URLS["g1_moves_github_tree"])
    hf_tree = safe_fetch_json(URLS["g1_moves_hf_tree"])
    github_paths = tree_paths(github_tree, "github")
    hf_paths = tree_paths(hf_tree, "hf")

    run_policy = fetch_text(URLS["g1_moves_run_policy"])
    readme = fetch_text(URLS["g1_moves_readme"])
    hf_claude_result = fetch_text_with_fallback([URLS["g1_moves_hf_claude"], URLS["g1_moves_hf_claude_blob"]])
    hf_claude = hf_claude_result["text"]
    constants = fetch_text(URLS["mjlab_g1_constants"])
    env_cfg = fetch_text(URLS["mjlab_g1_env_cfg"])

    result: dict[str, Any] = {
        "planning_gate": {
            "team_validation_mode": "manual-pass",
            "spec_delta": "M19 upstream tracker route now requires exact G1 Moves scene/action/observation parity before another native ONNX retry.",
            "perspectives": {
                "product": "prevents more opaque native failures and keeps visible squat gate honest",
                "architecture": "separates policy artifact validity from model/scene/sensor parity",
                "security": "public unauthenticated GitHub/Hugging Face raw reads only; no secrets",
                "qa": "remote tree audit, local XML/compile audit, prior native failure evidence, raw JSON",
                "skeptic": "absence from public tree is not proof the XML cannot be acquired privately",
            },
            "dod": [
                "fetch public G1 Moves GitHub and Hugging Face trees",
                "inspect local G1 scene actuator/sensor contract",
                "produce machine-readable next action for M19",
            ],
        },
        "web_sources": [
            {"url": value, "accessed": "2026-06-18"} for value in URLS.values()
        ],
        "remote_tree": {
            "github": summarize_paths(github_paths),
            "huggingface": summarize_paths(hf_paths),
        },
        "direct_xml_probes": [probe_url(url) for url in DIRECT_XML_PROBES],
        "remote_contract": {
            "run_policy": {
                "g1_mode15_square_hits": grep_lines(run_policy, ["g1_mode15_square"]),
                "obs_action_hits": grep_lines(run_policy, ["obs", "action", "policy", "time_step", "ctrl", "sensordata"])[:80],
            },
            "readme": {
                "observation_hits": grep_lines(readme, ["160", "154", "29", "50hz", "dof", "mode 15", "policy"])[:80],
            },
            "hf_claude": {
                "source_url": hf_claude_result["url"],
                "fetch_errors": hf_claude_result["errors"],
                "g1_mode15_square_hits": grep_lines(hf_claude, ["g1_mode15_square", "xml", "mujoco", "mode15"])[:80],
            },
            "mjlab_constants": {
                "g1_action_scale": extract_assignment(constants, "G1_ACTION_SCALE"),
                "joint_name_hits": grep_lines(constants, ["JOINT", "ACTION_SCALE", "KNEES_BENT", "29"])[:80],
            },
            "mjlab_env_cfg": {
                "tracking_hits": grep_lines(env_cfg, ["G1", "Tracking", "policy", "action", "observation"])[:80],
            },
        },
        "local_scene": {
            "scene_xml": inspect_xml(LOCAL_SCENE),
            "base_xml": inspect_xml(LOCAL_BASE),
            "compiled": inspect_compiled_scene(LOCAL_SCENE),
        },
        "prior_native_failures": {
            "exp99_upstream_adapter": load_prior_result(
                "experiments/99-g1-moves-upstream-policy-adapter-parity-probe/verify/g1-moves-upstream-policy-adapter-parity-probe/result.json"
            ),
            "exp100_public_motor_xml": load_prior_result(
                "experiments/100-g1-upstream-motor-xml-squat-policy-probe/verify/g1-upstream-motor-xml-squat-policy-probe/result.json"
            ),
            "exp101_mjlab_contract": load_prior_result(
                "experiments/101-g1-mjlab-action-observation-contract-probe/verify/g1-mjlab-action-observation-contract-probe/result.json"
            ),
        },
    }
    result["decision"] = decide(result)
    (VERIFY_DIR / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_summary(result)
    print(json.dumps(result["decision"], indent=2))


if __name__ == "__main__":
    main()
