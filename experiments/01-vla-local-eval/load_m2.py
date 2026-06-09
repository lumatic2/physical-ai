"""
load_m2.py — M2: real OpenVLA 7B 로딩 + VRAM 측정 (H1 검증).

deploy.py:76-84 의 로딩 경로를 그대로 따르되, attn_implementation 을 인자로 분리:
flash-attn 빌드 마찰을 모델 로딩 마찰과 격리하기 위해 기본 'sdpa' (flash-attn 불필요).
필요 시 --attn flash_attention_2 로 전환.

목적: openvla/openvla-7b 가 RTX 5090 32GB 안에 적재되는지(OOM 없이) + 실제 VRAM 사용량.
run: ~/.venvs/vla-eval/bin/python load_m2.py [--attn sdpa|eager|flash_attention_2]
계약 출처: references/openvla-openvla/vla-scripts/deploy.py (접근 2026-06-09)
"""

import argparse
import json
import pathlib
import time

HERE = pathlib.Path(__file__).resolve().parent
VERIFY = HERE / "verify"
VERIFY.mkdir(exist_ok=True)

MODEL = "openvla/openvla-7b"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--attn", default="sdpa", choices=["sdpa", "eager", "flash_attention_2"])
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForVision2Seq, AutoProcessor

    print(f"[m2] torch={torch.__version__} cuda_avail={torch.cuda.is_available()}")
    assert torch.cuda.is_available(), "CUDA not available — abort"
    dev = torch.device("cuda:0")
    print(f"[m2] gpu={torch.cuda.get_device_name(0)}")
    torch.cuda.reset_peak_memory_stats()

    t0 = time.time()
    processor = AutoProcessor.from_pretrained(MODEL, trust_remote_code=True)
    vla = AutoModelForVision2Seq.from_pretrained(
        MODEL,
        attn_implementation=args.attn,
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    ).to(dev)
    load_s = time.time() - t0

    alloc_gb = torch.cuda.memory_allocated(dev) / 1e9
    peak_gb = torch.cuda.max_memory_allocated(dev) / 1e9
    result = {
        "model": MODEL,
        "attn_implementation": args.attn,
        "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(0),
        "load_seconds": round(load_s, 1),
        "vram_allocated_gb": round(alloc_gb, 2),
        "vram_peak_gb": round(peak_gb, 2),
        "oom": False,
    }
    print("[m2] RESULT", json.dumps(result, ensure_ascii=False))
    (VERIFY / "m2-load.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
