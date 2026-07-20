#!/usr/bin/env python3
"""Run a pinned local VLM and validate bounded scene/skill JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


ALLOWED_OBJECTS = {"black_bowl", "ramekin", "plate", "robot_gripper", "unknown"}
ALLOWED_SKILLS = {"pick_and_place", "stop"}
ROOT_FIELDS = {"scene", "selected_skill", "confidence"}
SCENE_FIELDS = {"visible_objects", "target", "destination", "spatial_summary"}
SKILL_FIELDS = {"name", "target", "destination"}


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def parse_structured_output(raw_output: str) -> dict[str, Any]:
    text = raw_output.strip()
    if not text.startswith("{") or not text.endswith("}"):
        raise ValueError("model output must be one bare JSON object")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError("model output must decode to an object")
    return value


def validate_vlm_decision(value: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return {"valid": False, "errors": ["decision_not_object"]}
    if set(value) != ROOT_FIELDS:
        errors.append("invalid_root_fields")
    scene = value.get("scene")
    skill = value.get("selected_skill")
    confidence = value.get("confidence")
    if not isinstance(scene, dict) or set(scene) != SCENE_FIELDS:
        errors.append("invalid_scene_fields")
    else:
        visible = scene.get("visible_objects")
        if not isinstance(visible, list) or not visible or any(item not in ALLOWED_OBJECTS for item in visible):
            errors.append("unknown_visible_object")
        if scene.get("target") not in ALLOWED_OBJECTS:
            errors.append("unknown_scene_target")
        if scene.get("destination") not in ALLOWED_OBJECTS:
            errors.append("unknown_scene_destination")
        if not isinstance(scene.get("spatial_summary"), str) or not scene["spatial_summary"].strip():
            errors.append("missing_spatial_summary")
    if not isinstance(skill, dict) or set(skill) != SKILL_FIELDS:
        errors.append("invalid_skill_fields")
    else:
        if skill.get("name") not in ALLOWED_SKILLS:
            errors.append("skill_not_allowlisted")
        if skill.get("target") not in ALLOWED_OBJECTS:
            errors.append("unknown_skill_target")
        if skill.get("destination") not in ALLOWED_OBJECTS:
            errors.append("unknown_skill_destination")
        if skill.get("name") == "pick_and_place":
            if skill.get("target") in {"unknown", skill.get("destination")}:
                errors.append("invalid_pick_target")
            if skill.get("destination") == "unknown":
                errors.append("invalid_pick_destination")
        if skill.get("name") == "stop" and {skill.get("target"), skill.get("destination")} != {"unknown"}:
            errors.append("stop_requires_unknown_objects")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        errors.append("invalid_confidence")
    if isinstance(scene, dict) and isinstance(skill, dict):
        if scene.get("target") != skill.get("target") or scene.get("destination") != skill.get("destination"):
            errors.append("scene_skill_object_mismatch")
    return {"valid": not errors, "errors": errors}


def run_local_vlm(
    *, model_id: str, revision: str, image_path: Path, instruction: str, prompt_path: Path
) -> dict[str, Any]:
    import torch
    from PIL import Image
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    prompt_template = prompt_path.read_text(encoding="utf-8")
    prompt = prompt_template.replace("{instruction}", instruction)
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_id,
        revision=revision,
        dtype=torch.bfloat16,
        device_map="cuda",
    ).eval()
    processor = AutoProcessor.from_pretrained(model_id, revision=revision)
    image = Image.open(image_path).convert("RGB")
    messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}]}]
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=256, do_sample=False)
    latency_ms = (time.perf_counter() - started) * 1000.0
    trimmed = generated[:, inputs["input_ids"].shape[1] :]
    raw_output = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
    decision = parse_structured_output(raw_output)
    validation = validate_vlm_decision(decision)
    if not validation["valid"]:
        raise ValueError(f"structured decision failed validation: {validation['errors']}")
    loaded_revision = getattr(model.config, "_commit_hash", None)
    if loaded_revision != revision:
        raise ValueError(f"loaded revision drift: {loaded_revision!r} != {revision!r}")
    return {
        "schema_version": "physical-ai-vlm-decision-v1",
        "model": {"name": model_id, "revision": revision, "license": "apache-2.0"},
        "input": {
            "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
            "instruction": instruction,
            "prompt_sha256": prompt_sha256(prompt),
        },
        "generation": {
            "raw_output": raw_output,
            "latency_ms": round(latency_ms, 3),
            "peak_gpu_memory_bytes": int(torch.cuda.max_memory_allocated()),
            "do_sample": False,
            "max_new_tokens": 256,
        },
        "decision": decision,
        "validation": validation,
        "claim_boundary": "local auxiliary VLM scene/skill output; not OpenVLA hidden reasoning or robot action",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--prompt", type=Path, default=Path(__file__).with_name("vlm-prompt.txt"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_local_vlm(
        model_id=args.model,
        revision=args.revision,
        image_path=args.image,
        instruction=args.instruction,
        prompt_path=args.prompt,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, "decision": result["decision"], "latency_ms": result["generation"]["latency_ms"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
