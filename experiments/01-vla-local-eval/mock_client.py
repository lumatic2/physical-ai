"""
mock_client.py — mock_server 의 `/act` 에 더미 이미지 + 지시를 POST 하고 action 을 검증.

목적 (M1): deploy.py 클라이언트 사용법(json-numpy 직렬화)이 round-trip 으로 안 깨지는지 + 7-dim action 회수 확인.
사용법 출처: references/openvla-openvla/vla-scripts/deploy.py:13-27 (접근 2026-06-09)

deps: pip install requests json-numpy numpy
run:  python mock_client.py   (서버가 0.0.0.0:8000 에 떠 있어야 함)
"""

import json_numpy

json_numpy.patch()
import sys

import numpy as np
import requests

URL = "http://0.0.0.0:8000/act"


def main() -> int:
    image = np.zeros((256, 256, 3), dtype=np.uint8)
    instruction = "pick up the red block"

    resp = requests.post(URL, json={"image": image, "instruction": instruction}, timeout=10)
    action = resp.json()

    print(f"[client] status={resp.status_code}")
    print(f"[client] action={action!r}  type={type(action)}")

    # 계약 검증: ndarray, shape (7,)
    ok = isinstance(action, np.ndarray) and action.shape == (7,)
    print(f"[client] round-trip {'PASS' if ok else 'FAIL'} — expected ndarray shape (7,)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
