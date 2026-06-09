"""dl_ckpt.py — M4: LIBERO-spatial finetuned OpenVLA 체크포인트 사전 다운로드 (~14GB).
repo id 출처: references/openvla-openvla/README.md:546 (접근 2026-06-09)"""
from huggingface_hub import snapshot_download

REPO = "openvla/openvla-7b-finetuned-libero-spatial"
path = snapshot_download(repo_id=REPO)
print("[dl] downloaded to", path)
