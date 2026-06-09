"""
server.py — REST 서버: VLA 정책(GPU)을 /act 로 노출. 기본 어댑터 = OpenVLA LIBERO finetuned.

tensorflow 전처리(rotate180 + lanczos resize 224 + center_crop 0.9)를 *서버에만* 둔다.
robosuite/EGL 은 import 하지 않음 → tf↔robosuite-EGL in-process 세그폴트를 프로세스 분리로 회피.
이것이 experiment #1 의 본래 설계(deploy.py REST 서버 + 시뮬 클라이언트)이며, 세그폴트의 구조적 해법.

근거: tensorflow import 후 robosuite OffScreenRenderEnv 생성이 egl_context.py:136 에서 세그폴트
      (torch import 은 안전 — verify/m4-segfault.txt + 격리 테스트로 확정, 2026-06-09).
전처리/추론 출처: references/openvla-openvla/experiments/robot/{libero/libero_utils.py, openvla_utils.py}
deps: uvicorn fastapi json-numpy tensorflow torch transformers
run: python server.py --policy openvla --suite libero_spatial --port 8000
"""

import argparse
import json

import json_numpy  # 전역 patch 안 씀 — REST 경계에서만 명시적 loads/dumps (전역 patch 는 lib json 파싱을 깸)

import tensorflow as tf
import torch
import uvicorn
from fastapi import FastAPI, Request, Response
from PIL import Image
from transformers import AutoModelForVision2Seq, AutoProcessor

RESIZE = 224
DEV = torch.device("cuda:0")

# 모듈 글로벌 — load() 에서 채움 (정책 어댑터가 세팅).
processor = None
vla = None
TASK_SUITE = None


def resize_image(img, size):  # libero_utils:33-47
    img = tf.image.encode_jpeg(img)
    img = tf.io.decode_image(img, expand_animations=False, dtype=tf.uint8)
    img = tf.image.resize(img, size, method="lanczos3", antialias=True)
    return tf.cast(tf.clip_by_value(tf.round(img), 0, 255), tf.uint8).numpy()


def crop_and_resize(image, crop_scale, batch_size):  # openvla_utils:81-124
    if image.shape.ndims == 3:
        image = tf.expand_dims(image, axis=0)
        expanded = True
    else:
        expanded = False
    new_h = tf.reshape(tf.clip_by_value(tf.sqrt(crop_scale), 0, 1), shape=(batch_size,))
    new_w = tf.reshape(tf.clip_by_value(tf.sqrt(crop_scale), 0, 1), shape=(batch_size,))
    h_off, w_off = (1 - new_h) / 2, (1 - new_w) / 2
    boxes = tf.stack([h_off, w_off, h_off + new_h, w_off + new_w], axis=1)
    image = tf.image.crop_and_resize(image, boxes, tf.range(batch_size), (224, 224))
    return image[0] if expanded else image


def load(policy, suite, ckpt):
    """정책 어댑터 로딩. 2번째 정책(π0/ACT)은 여기 분기를 추가하고 predict() 계약만 맞추면 된다."""
    global processor, vla, TASK_SUITE
    if policy != "openvla":
        raise ValueError(f"unsupported policy '{policy}' — server.py 에 어댑터 추가 필요")
    TASK_SUITE = suite  # unnorm_key + norm_stats 키 (underscore 형식)
    if not ckpt:
        ckpt = f"openvla/openvla-7b-finetuned-{suite.replace('_', '-')}"
    print(f"[server] loading {ckpt} (sdpa)")
    processor = AutoProcessor.from_pretrained(ckpt, trust_remote_code=True)
    vla = AutoModelForVision2Seq.from_pretrained(
        ckpt, attn_implementation="sdpa", torch_dtype=torch.bfloat16, low_cpu_mem_usage=True, trust_remote_code=True,
    ).to(DEV)
    if TASK_SUITE not in getattr(vla, "norm_stats", {}):
        from huggingface_hub import hf_hub_download

        with open(hf_hub_download(repo_id=ckpt, filename="dataset_statistics.json")) as f:
            vla.norm_stats = json.load(f)
    assert TASK_SUITE in vla.norm_stats, f"{TASK_SUITE} not in {list(vla.norm_stats.keys())}"
    print(f"[server] norm_stats keys: {list(vla.norm_stats.keys())}")


app = FastAPI()


@app.post("/act")
async def predict_action(request: Request):
    payload = json_numpy.loads(await request.body())  # 경계에서만 명시적 디코드
    # 클라이언트가 보낸 raw agentview (256x256x3 uint8) — 전처리는 전부 서버에서.
    image, instruction = payload["image"], payload["instruction"]
    img = image[::-1, ::-1]  # get_libero_image: rotate 180
    img = resize_image(img, (RESIZE, RESIZE))  # lanczos resize -> 224
    # get_vla_action: center_crop 0.9 (image_aug finetuned 체크포인트)
    t = tf.convert_to_tensor(img)
    od = t.dtype
    t = tf.image.convert_image_dtype(t, tf.float32)
    t = crop_and_resize(t, 0.9, 1)
    t = tf.clip_by_value(t, 0, 1)
    t = tf.image.convert_image_dtype(t, od, saturate=True)
    pil = Image.fromarray(t.numpy()).convert("RGB")
    prompt = f"In: What action should the robot take to {instruction.lower()}?\nOut:"
    inputs = processor(prompt, pil).to(DEV, dtype=torch.bfloat16)
    action = vla.predict_action(**inputs, unnorm_key=TASK_SUITE, do_sample=False)
    return Response(content=json_numpy.dumps(action), media_type="application/json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="openvla", choices=["openvla"])
    ap.add_argument("--suite", default="libero_spatial")
    ap.add_argument("--ckpt", default="", help="비우면 openvla/openvla-7b-finetuned-<suite>")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    load(a.policy, a.suite, a.ckpt)
    uvicorn.run(app, host="0.0.0.0", port=a.port)
