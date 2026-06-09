"""
mock_server.py — OpenVLA deploy.py `/act` 계약을 모델 없이 모사하는 stub 서버.

목적 (M1): REST round-trip + json-numpy ndarray 직렬화를 OpenVLA 7B 로딩과 격리해 검증.
계약 출처: references/openvla-openvla/vla-scripts/deploy.py:65-123 (접근 2026-06-09)
    POST /act <- {"image": ndarray, "instruction": str, "unnorm_key": Optional[str]}
             -> {"action": ndarray}  (OpenVLA 는 7-DoF: x,y,z,roll,pitch,yaw,gripper)

deps: pip install uvicorn fastapi json-numpy numpy
run:  python mock_server.py   (0.0.0.0:8000)
"""

import json_numpy

json_numpy.patch()
import logging
import traceback
from typing import Any, Dict

import numpy as np
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse


class MockVLAServer:
    """deploy.py OpenVLAServer 와 동일한 인터페이스, 단 모델 대신 고정 action 반환."""

    def predict_action(self, payload: Dict[str, Any]):
        try:
            image, instruction = payload["image"], payload["instruction"]
            # 계약 검증: image 는 ndarray, instruction 은 str 이어야 함
            assert isinstance(image, np.ndarray), f"image must be ndarray, got {type(image)}"
            assert isinstance(instruction, str), f"instruction must be str, got {type(instruction)}"
            # OpenVLA 7-DoF action 모사 — 고정 벡터 (gripper open=1.0)
            action = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float32)
            return JSONResponse(action)
        except Exception:  # noqa: BLE001
            logging.error(traceback.format_exc())
            return "error"

    def run(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        self.app = FastAPI()
        self.app.post("/act")(self.predict_action)
        uvicorn.run(self.app, host=host, port=port)


if __name__ == "__main__":
    MockVLAServer().run()
