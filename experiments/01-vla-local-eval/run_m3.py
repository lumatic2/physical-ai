"""
run_m3.py — M3: real OpenVLA 7B `/act` 추론 latency 측정 (H2).

deploy.py:102-105 의 추론 경로를 그대로 재현:
  prompt = get_openvla_prompt(instruction)
  inputs = processor(prompt, image).to(device, bf16)
  action = vla.predict_action(**inputs, unnorm_key=..., do_sample=False)

warmup 후 N회 반복 → latency p50/p95. cuda.synchronize 로 정확 측정.
run: ~/.venvs/vla-eval/bin/python run_m3.py [--n 20] [--unnorm-key bridge_orig]
계약 출처: references/openvla-openvla/vla-scripts/deploy.py (접근 2026-06-09)
"""

import argparse
import json
import pathlib
import statistics
import time

HERE = pathlib.Path(__file__).resolve().parent
VERIFY = HERE / "verify"
VERIFY.mkdir(exist_ok=True)
MODEL = "openvla/openvla-7b"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--unnorm-key", default="bridge_orig")
    args = ap.parse_args()

    import numpy as np
    import torch
    from PIL import Image
    from transformers import AutoModelForVision2Seq, AutoProcessor

    dev = torch.device("cuda:0")
    processor = AutoProcessor.from_pretrained(MODEL, trust_remote_code=True)
    vla = AutoModelForVision2Seq.from_pretrained(
        MODEL, attn_implementation="sdpa", torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True, trust_remote_code=True,
    ).to(dev)

    # norm_stats 키 확인 — unnorm_key 가 없으면 사용 가능 키 출력 후 첫 키 사용
    keys = list(getattr(vla, "norm_stats", {}).keys())
    unnorm_key = args.unnorm_key
    if unnorm_key not in keys:
        print(f"[m3] unnorm_key '{unnorm_key}' not in norm_stats; available={keys}")
        unnorm_key = keys[0] if keys else None
    print(f"[m3] using unnorm_key={unnorm_key}")

    image = np.zeros((256, 256, 3), dtype=np.uint8)
    instruction = "pick up the red block"
    prompt = f"In: What action should the robot take to {instruction.lower()}?\nOut:"

    def one():
        inputs = processor(prompt, Image.fromarray(image).convert("RGB")).to(dev, dtype=torch.bfloat16)
        torch.cuda.synchronize()
        t0 = time.time()
        action = vla.predict_action(**inputs, unnorm_key=unnorm_key, do_sample=False)
        torch.cuda.synchronize()
        return (time.time() - t0) * 1000.0, action

    for _ in range(args.warmup):
        one()

    lat = []
    last_action = None
    for _ in range(args.n):
        ms, last_action = one()
        lat.append(ms)

    lat.sort()
    p50 = statistics.median(lat)
    p95 = lat[min(len(lat) - 1, int(0.95 * len(lat)))]
    result = {
        "model": MODEL, "attn_implementation": "sdpa", "unnorm_key": unnorm_key,
        "n": args.n, "warmup": args.warmup,
        "latency_ms_p50": round(p50, 1), "latency_ms_p95": round(p95, 1),
        "latency_ms_min": round(min(lat), 1), "latency_ms_max": round(max(lat), 1),
        "action_shape": list(getattr(last_action, "shape", [])),
        "action_sample": [round(float(x), 4) for x in (last_action.tolist() if last_action is not None else [])],
    }
    print("[m3] RESULT", json.dumps(result, ensure_ascii=False))
    (VERIFY / "m3-latency.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
