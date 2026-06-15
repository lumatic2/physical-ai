"""Sanity-check policy experiment bundles before deploy.

This catches the class of failures where a scene compiles in an isolated script
but the web app cannot load it because registry, copied assets, or manifest
entries are incomplete.
"""
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
WEB = HERE / "web"
SCENES = WEB / "assets" / "scenes"


def fail(errors, msg):
    errors.append(msg)
    print(f"FAIL {msg}")


def main():
    registry = json.loads((HERE / "experiments.json").read_text(encoding="utf-8"))
    web_registry = json.loads((WEB / "experiments.json").read_text(encoding="utf-8"))
    manifest = set(json.loads((SCENES / "manifest.json").read_text(encoding="utf-8")))
    errors = []
    checked = 0

    if registry != web_registry:
        fail(errors, "web/experiments.json is stale; run sync_web.py")

    for exp_name, exp in registry["experiments"].items():
        policy = exp.get("policy")
        if not policy:
            continue
        checked += 1
        scene_rel = exp["scene"]
        scene_dir = scene_rel.split("/")[0]
        scene_path = SCENES / scene_rel
        if not scene_path.exists():
            fail(errors, f"{exp_name}: missing scene {scene_rel}")
        if scene_rel not in manifest:
            fail(errors, f"{exp_name}: scene missing from manifest {scene_rel}")

        for key in ["onnx", "golden"]:
            rel = f"{scene_dir}/{policy[key]}"
            if not (SCENES / rel).exists():
                fail(errors, f"{exp_name}: missing {key} {rel}")

        obs_spec_rel = f"{scene_dir}/obs_spec.json"
        if not (SCENES / obs_spec_rel).exists():
            print(f"WARN {exp_name}: missing optional web obs_spec.json")

        for field in ["obs_dim", "act_dim", "action_scale", "n_substeps", "command", "indices"]:
            if field not in policy:
                fail(errors, f"{exp_name}: missing policy.{field}")

        indices = policy.get("indices", {})
        if len(indices.get("default_pose", [])) != policy.get("act_dim"):
            fail(errors, f"{exp_name}: default_pose length != act_dim")
        if "lowers" in indices and len(indices["lowers"]) != policy.get("act_dim"):
            fail(errors, f"{exp_name}: lowers length != act_dim")
        if "uppers" in indices and len(indices["uppers"]) != policy.get("act_dim"):
            fail(errors, f"{exp_name}: uppers length != act_dim")
        if policy.get("obs_history"):
            frames = policy["obs_history"].get("frames")
            cur = policy["obs_history"].get("current_dim")
            if frames * cur != policy.get("obs_dim"):
                fail(errors, f"{exp_name}: obs_history frames*current_dim != obs_dim")
            if "command_transform" not in policy or "command_scale" not in policy:
                fail(errors, f"{exp_name}: history policy missing command_transform/command_scale")

        for asset in sorted((SCENES / scene_dir).rglob("*")):
            if not asset.is_file():
                continue
            rel = asset.relative_to(SCENES).as_posix()
            if rel.endswith((".xml", ".stl", ".STL", ".obj", ".skn", ".png")) and rel not in manifest:
                fail(errors, f"{exp_name}: scene asset missing from manifest {rel}")

        print(f"OK {exp_name}: scene={scene_rel} obs={policy.get('obs_dim')} act={policy.get('act_dim')}")

    print(f"checked {checked} policy experiments")
    if errors:
        print(f"policy bundle check FAIL: {len(errors)} errors")
        return 1
    print("policy bundle check PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
